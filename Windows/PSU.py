from datetime import datetime


from serial import SerialException


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceISEGWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, SpinBox, ComboBox, ReadingAgeLabel
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox
from Utility.ChannelRows import VoltageChannelRow, CurrentLimitRow

from Connection.USBPorts import getComports
from Connection.ISEG import ISEGConnection
from Connection.Threaded import ThreadedISEGConnection, ThreadedDummyConnection


class PSUVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.ramp_timer = QTimer()
        self.ramp_timer.timeout.connect(self.updateRamp)
        self.ramp_timer.setInterval(DefaultParams.ramp_timer_time)
        self.ramp_start_time = datetime.now()
        self.ramp_channel = 0
        self.ramp_start_voltage = 0

        self.active_message_box = False

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('PSU', self.reconnect)

        self.device_wrapper = DeviceISEGWrapper()
        self.connection: None | ISEGConnection = None
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()

        self.voltage_deviation = DefaultParams.psu_voltage_deviation
        self.voltage_maximum = DefaultParams.psu_voltage_maximum
        self.current_maximum = DefaultParams.psu_current_maximum
        self.time_ramp_default = DefaultParams.psu_time_ramp_default

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection')
        self.addWidget(self.connection_group_box)

        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_group_box.setLayout(self.connection_hbox)

        self.connection_grid = InsertingGridLayout()
        self.connection_hbox.addLayout(self.connection_grid)

        # Connection
        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
        self.indicator_connection.setToolTip('Green if the device is connected')
        self.status_connection = QLabel('Not connected')
        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('Port of the device (refresh the list with the button on the right)')
        self.button_connection = QPushButton('Connect')
        self.button_connection.setToolTip('Connect to / disconnect from the selected port')
        self.button_connection.pressed.connect(self.manualConnect)
        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(QIcon('icons/refresh.svg'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.status_reading_age = ReadingAgeLabel()
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2),
            self.combobox_connection,
            self.button_connection,
            self.button_connection_refresh,
            self.status_reading_age
        )

        # Control Group Box
        self.control_group_box = QGroupBox('Voltages')
        self.addWidget(self.control_group_box)

        self.control_hbox = QHBoxLayout()
        self.control_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.control_group_box.setLayout(self.control_hbox)

        self.control_grid = InsertingGridLayout()
        self.control_hbox.addLayout(self.control_grid)

        # Labels
        self.control_grid.addWidgets(
            None,
            QLabel('Polarity'),
            QLabel('Set [V]'),
            QLabel('Voltage'),
            QLabel('Current'),
            (QLabel('High Voltage'), 2)
        )

        # one row per channel
        self.channel_names = ['MCP Front/Back', 'Anode', 'Cathode LSD', 'Focus LSD']
        self.channel_rows = [
            VoltageChannelRow(
                self.control_grid,
                name,
                channel,
                set_voltage=self.setVoltage,
                set_output=self.setOutput,
                set_polarity=self.setPolarity,
                voltage_maximum=self.voltage_maximum,
                voltage_deviation=self.voltage_deviation,
                current_maximum=self.current_maximum,
                voltage_decimals=DefaultParams.psu_voltage_decimals,
                voltage_step=10 ** -DefaultParams.psu_voltage_decimals
            )
            for channel, name in enumerate(self.channel_names)
        ]

        # Limits Group Box
        self.limits_group_box = QGroupBox('Limits')
        self.addWidget(self.limits_group_box)

        self.limits_hbox = QHBoxLayout()
        self.limits_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.limits_group_box.setLayout(self.limits_hbox)

        self.limits_grid = InsertingGridLayout()
        self.limits_hbox.addLayout(self.limits_grid)

        # Labels
        self.limits_grid.addWidgets(
            None,
            QLabel('Current [mA]'),
            QLabel('Reached')
        )

        self.limit_rows = [
            CurrentLimitRow(self.limits_grid, name, channel, self.setCurrentLimit, input_range=(DefaultParams.psu_current_limit_minimum, DefaultParams.psu_current_limit_maximum))
            for channel, name in enumerate(self.channel_names)
        ]

        # Advanced Settings Group Box
        self.advanced_settings_group_box = QGroupBox('Advanced Settings')
        self.addWidget(self.advanced_settings_group_box)

        self.advanced_settings_hbox = QHBoxLayout()
        self.advanced_settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.advanced_settings_group_box.setLayout(self.advanced_settings_hbox)

        self.advanced_settings_grid = InsertingGridLayout()
        self.advanced_settings_hbox.addLayout(self.advanced_settings_grid)

        # Speed (:CONF:RAMP:VOLT of the ISEG crate in % of the nominal voltage per second, e.g. 1 %/s = 60 V/s for 6 kV)
        self.label_advanced_settings_ramp = QLabel('Ramp speed [%/s]')
        self.spinbox_advanced_settings_ramp = DoubleSpinBox(default=0, step_size=0.01, input_range=(0, DefaultParams.psu_ramp_speed_maximum), decimals=3, buttons=False)
        self.spinbox_advanced_settings_ramp.setToolTip(
            'Voltage ramp speed of the ISEG crate in % of the nominal voltage per second (applies to all channels, press enter to apply),\n'
            f'e.g. 1 %/s = 10 V/s for a 1 kV channel (range 0 ... {DefaultParams.psu_ramp_speed_maximum:g} %/s)'
        )
        self.spinbox_advanced_settings_ramp.editingFinished.connect(lambda: self.setRampSpeed(self.spinbox_advanced_settings_ramp.value()))
        self.advanced_settings_grid.addWidgets(
            self.label_advanced_settings_ramp,
            self.spinbox_advanced_settings_ramp
        )

        # Ramp Group Box
        self.ramp_group_box = QGroupBox('Ramp')
        self.addWidget(self.ramp_group_box)

        self.ramp_hbox = QHBoxLayout()
        self.ramp_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.ramp_group_box.setLayout(self.ramp_hbox)

        self.ramp_grid = InsertingGridLayout()
        self.ramp_hbox.addLayout(self.ramp_grid)

        # Time
        self.label_ramp_time = QLabel('Time [min]')
        self.spinbox_ramp_time = SpinBox(default=self.time_ramp_default, step_size=1, input_range=(0, DefaultParams.psu_time_ramp_maximum), buttons=False)
        self.spinbox_ramp_time.setToolTip('Duration of the software voltage ramp in minutes')
        self.ramp_grid.addWidgets(
            self.label_ramp_time,
            self.spinbox_ramp_time
        )

        # Final Value
        self.label_ramp_final = QLabel('Target Voltage [V]')
        self.spinbox_ramp_voltage = DoubleSpinBox(
            default=0,
            step_size=10 ** -DefaultParams.psu_voltage_decimals,
            input_range=(0, self.voltage_maximum),
            decimals=DefaultParams.psu_voltage_decimals,
            buttons=False
        )
        self.spinbox_ramp_voltage.setToolTip('Final voltage of the software voltage ramp')
        self.ramp_grid.addWidgets(
            self.label_ramp_final,
            self.spinbox_ramp_voltage
        )

        # Channel
        self.label_ramp_channel = QLabel('Channel')
        self.combobox_ramp_channel = ComboBox(default=0, entries=[row.name for row in self.channel_rows])
        self.combobox_ramp_channel.setToolTip('Channel that is ramped')
        self.ramp_grid.addWidgets(
            self.label_ramp_channel,
            self.combobox_ramp_channel
        )

        # Start
        self.status_ramp = QLabel('Remaining time:')
        self.status_remaining_ramp = DisplayLabel(value=0, target_value=0, deviation=1, unit='min')
        self.status_remaining_ramp.setToolTip('Remaining time of the voltage ramp')
        self.indicator_ramp = IndicatorLed()
        self.indicator_ramp.setToolTip('Green while a voltage ramp is running')
        self.button_ramp = QPushButton('Start ramp')
        self.button_ramp.setToolTip('Start/stop the slow voltage ramp of the selected channel (voltage is changed step by step)')
        self.button_ramp.clicked.connect(self.startRampVoltage)
        self.ramp_grid.addWidgets(
            self.status_ramp,
            self.status_remaining_ramp,
            self.indicator_ramp,
            self.button_ramp
        )

        # grouped items (the device callbacks work with these lists)
        self.all_channels_selector = '0-3'
        self.indicators = [row.indicator for row in self.channel_rows]
        self.buttons = [row.button_enable for row in self.channel_rows]
        self.status_voltages = [row.status_voltage for row in self.channel_rows]
        self.status_currents = [row.status_current for row in self.channel_rows]
        self.button_polarities = [row.button_polarity for row in self.channel_rows]
        self.spinbox_voltages = [row.spinbox_voltage for row in self.channel_rows]
        self.indicator_limits = [row.indicator_limit for row in self.limit_rows]
        self.spinbox_limit_currents = [row.spinbox_limit for row in self.limit_rows]

        self.reset()

        last_connection = GlobalConf.getConnection('psu')
        if last_connection:
            self.connect(last_connection, False)

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

        self.status_reading_age.setAge(self.device_wrapper.threaded_connection.secondsSinceLastResult(), self.indicator_connection.value())

        if not self.checkConnection(False):
            return

        def checkVoltageOn(states: list[float]):
            if len(states) != len(self.indicators) != len(self.buttons) != len(self.status_voltages):
                GlobalConf.logger.error(f'High voltage indicators cannot be set, non matching length: expected len = {len(self.indicators)}, got len = {len(states)}')
                return

            for indicator, status_voltage, state, button in zip(self.indicators, self.status_voltages, states, self.buttons):
                state = bool(state)
                indicator.setValue(state)
                button.setText('Disable' if state else 'Enable')

                if not state:
                    status_voltage.setTargetValue(0)

        self.device_wrapper.threaded_connection.callback(
            checkVoltageOn,
            self.device_wrapper.threaded_connection.readVoltageOn(self.all_channels_selector)
        )

        def measureVoltage(voltages: list[float]):
            if len(voltages) != len(self.status_voltages):
                GlobalConf.logger.error(f'Measured voltages cannot be set, non matching length: expected len = {len(self.status_voltages)}, got len = {len(voltages)}')
                return

            if any([0 if isinstance(voltage, float) else 1 for voltage in voltages]):
                GlobalConf.logger.error(f'Measured voltages cannot be set, types of currents are: {[type(voltage) for voltage in voltages]}, expected only <float>s')
                return

            for status_voltage, voltage in zip(self.status_voltages, voltages):
                status_voltage.setValue(voltage)

        self.device_wrapper.threaded_connection.callback(
            measureVoltage,
            self.device_wrapper.threaded_connection.measureVoltage(self.all_channels_selector)
        )

        def measureCurrent(currents: list[float]):
            if len(currents) != len(self.status_currents) != len(self.indicator_limits) != len(self.spinbox_limit_currents):
                GlobalConf.logger.error(f'Measured currents cannot be set, non matching length: expected len = {len(self.status_currents)}, got len = {len(currents)}')
                return

            if any([0 if isinstance(current, float) else 1 for current in currents]):
                GlobalConf.logger.error(f'Measured currents cannot be set, types of currents are: {[type(current) for current in currents]}, expected only <float>s')
                return

            for status_current, indicator_limit, spinbox_limit_current, current in zip(self.status_currents, self.indicator_limits, self.spinbox_limit_currents, currents):
                status_current.setValue(current)
                indicator_limit.setValue(current >= spinbox_limit_current.value() / 1000)

        self.device_wrapper.threaded_connection.callback(
            measureCurrent,
            self.device_wrapper.threaded_connection.measureCurrent(self.all_channels_selector)
        )

        def checkPolarity(polarities: list[bool]):
            if len(polarities) != len(self.button_polarities):
                GlobalConf.logger.error(f'Measured polarities cannot be set, non matching length: expected len = {len(self.button_polarities)}, got len = {len(polarities)}')
                return

            for button_polarity, polarity in zip(self.button_polarities, polarities):
                button_polarity.polarityChange(polarity)

        self.device_wrapper.threaded_connection.callback(
            checkPolarity,
            self.device_wrapper.threaded_connection.configureOutputPolarityGet(self.all_channels_selector)
        )

    def updateAllValues(self):
        """Updates all values"""

        if not self.checkConnection(False):
            return

        self.updateLoop()

        def readVoltage(voltages: list[float]):
            if len(voltages) != len(self.spinbox_voltages) != len(self.status_voltages):
                GlobalConf.logger.error(f'Set voltages cannot be set, non matching length: expected len = {len(self.spinbox_voltages)}, got len = {len(voltages)}')
                return

            for spinbox_voltage, status_voltage, voltage in zip(self.spinbox_voltages, self.status_voltages, voltages):
                voltage = abs(voltage)
                spinbox_voltage.setValue(voltage)
                status_voltage.setTargetValue(voltage)

        self.device_wrapper.threaded_connection.callback(
            readVoltage,
            self.device_wrapper.threaded_connection.readVoltage(self.all_channels_selector)
        )

        def readCurrentLimit(currents: list[float]):
            if len(currents) != len(self.spinbox_limit_currents):
                GlobalConf.logger.error(f'Set currents cannot be set, non matching length: expected len = {len(self.spinbox_limit_currents)}, got len = {len(currents)}')
                return

            for (spinbox_limit_current, current) in zip(self.spinbox_limit_currents, currents):
                spinbox_limit_current.setValue(current * 1000)

        self.device_wrapper.threaded_connection.callback(
            readCurrentLimit,
            self.device_wrapper.threaded_connection.readCurrent(self.all_channels_selector)
        )

        self.device_wrapper.threaded_connection.callback(
            self.spinbox_advanced_settings_ramp.setValue,
            self.device_wrapper.threaded_connection.configureRampVoltageGet()
        )

    def setVoltage(self, channel: int, voltage: float):
        """
        Sets voltage to specified channel

        :param channel: channel to be set
        :param voltage: voltage to be set
        """

        if not self.checkConnection():
            return

        self.status_voltages[channel].setTargetValue(voltage)
        self.device_wrapper.threaded_connection.voltageSet(channel, voltage)

    def setCurrentLimit(self, channel: int, current: float):
        """
        Sets current limit to specified channel

        :param channel: channel to be set
        :param current: current to be set
        """

        if not self.checkConnection():
            return

        self.device_wrapper.threaded_connection.currentSet(channel, current / 1000)

    def setOutput(self, channel: int, state: bool):
        """
        Sets output state to specified channel

        :param channel: channel to be set
        :param state: state of output to be set
        """

        if not self.checkConnection():
            return

        if state:
            self.device_wrapper.threaded_connection.voltageOn(channel)
            self.status_voltages[channel].setTargetValue(self.spinbox_voltages[channel].value())
        else:
            self.device_wrapper.threaded_connection.voltageOff(channel)
            self.status_voltages[channel].setTargetValue(0)

    def setRampSpeed(self, speed: float):
        """
        Sets the voltage ramp speed of the crate (all channels)

        :param speed: ramp speed in % of the nominal voltage per second
        """

        if not self.checkConnection():
            return

        self.device_wrapper.threaded_connection.configureRampVoltageSet(speed)

    def setPolarity(self, channel: int, polarity: bool):
        """
        Sets output state to specified channel

        :param channel: channel to be set
        :param polarity: polarity (True: positive, False: negative) to be set
        """

        if not self.checkConnection():
            return

        if self.button_polarities[channel].state == polarity:
            return

        if self.indicators[channel].value() and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(
                None,
                QMessageBox.Icon.Information,
                'Polarity switch',
                'Polarity can only be switched if high voltage of the same channel is turned off'
            )
            self.active_message_box = False
            return

        self.device_wrapper.threaded_connection.configureOutputPolaritySet(channel, polarity)

        # TODO: set all other channels on again - do we need to do this??

    def checkConnection(self, messagebox: bool = True) -> bool:
        """
        Checks if connection is established and pops up messagebox if it does not

        :param messagebox: enable popup of infobox
        """

        if self.indicator_connection.value():
            return True

        if messagebox and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'Connection warning!',
                'ISEG crate power supply is not connected, please connect first!'
            )
            self.active_message_box = False

        return False

    def connect(self, comport: str = '', messagebox: bool = True):
        """
        Connect to given comport. If no comport is given, the current selected comport will be connected to

        :param comport: comport to connect to
        :param messagebox: show messagebox if failed
        """

        if not comport:
            comport = self.combobox_connection.getValue(text=True)
        self.setComport(comport)

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if connect:
            self.connection = ISEGConnection(
                comport,
                echo=ISEGConnection.EchoMode.ECHO_AUTO,
                cleaning=True,
                strict='iseg Spezialelektronik GmbH,NR040060r4050000200,8200005,1.74'
            )
            try:
                self.connection.open()
                self.device_wrapper.threaded_connection = ThreadedISEGConnection(
                    self.connection,
                    self.connectionLost
                )
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
                self.last_port = comport
                self.combobox_connection.setEnabled(False)
                self.button_connection_refresh.setEnabled(False)
                self.button_connection.setText('Disconnect')

            except (SerialException, ConnectionError) as error:
                try:
                    self.connection.close()
                except ConnectionError:
                    pass
                self.connection = None
                self.reset()

                GlobalConf.logger.info(f'Connection error! Could not connect to ISEG crate power supply on port "{comport}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to ISEG crate power supply on port "{comport}"!',
                        f'<strong>Encountered Error:</strong><br>{error}',
                        expand_details=False
                    )
        else:
            self.combobox_connection.setEnabled(True)
            self.button_connection_refresh.setEnabled(True)
            self.button_connection.setText('Connect')

        self.updateAllValues()

    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection to the device was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('PSU: Connection lost')
        self.unconnect()
        if self.last_port:
            self.auto_reconnect.start()

    def reconnect(self) -> bool:
        """Tries to reconnect silently to the last port, returns True if connected"""

        if not self.device_wrapper.threaded_connection.isDummy():
            return True
        self.connect(self.last_port, False)
        return self.indicator_connection.value()

    def unconnect(self):
        """Disconnect from any port"""

        self.device_wrapper.threaded_connection.close()
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        comport = self.combobox_connection.getValue(text=True)
        self.reset()
        self.setComport(comport)

    def setComport(self, comport: str):
        """
        Selects the comport in the list of comports

        :param comport: comport to be selected
        """

        comport = comport.lower()

        entries = {port.lower(): i for i, port in enumerate(self.combobox_connection.entries)}
        if comport in entries.keys():
            self.combobox_connection.setCurrentIndex(entries[comport])

    def startRampVoltage(self):
        """Starts the voltage ramp with defined parameters"""

        if self.ramp_timer.isActive():
            self.stopRampVoltage()
            return

        self.ramp_timer.start()
        self.ramp_start_time = datetime.now()
        self.ramp_channel = self.combobox_ramp_channel.currentIndex()
        self.ramp_start_voltage = abs(self.status_voltages[self.ramp_channel].value)

        # disable input fields
        self.spinbox_ramp_time.setEnabled(False)
        self.spinbox_ramp_voltage.setEnabled(False)
        self.combobox_ramp_channel.setEnabled(False)
        self.indicator_ramp.setValue(True)
        self.button_ramp.setText('Stop Ramp')
        self.spinbox_voltages[self.ramp_channel].setEnabled(False)

        self.status_remaining_ramp.setValue(self.spinbox_ramp_time.value())

    def stopRampVoltage(self):
        """Stops the voltage ramp"""

        self.ramp_timer.stop()

        # enable input fields
        self.spinbox_ramp_time.setEnabled(True)
        self.spinbox_ramp_voltage.setEnabled(True)
        self.combobox_ramp_channel.setEnabled(True)
        self.indicator_ramp.setValue(False)
        self.button_ramp.setText('Start Ramp')
        self.spinbox_voltages[self.ramp_channel].setEnabled(True)

        # reset input values
        self.spinbox_ramp_time.setValue(self.time_ramp_default)
        self.spinbox_ramp_voltage.reset()
        self.combobox_ramp_channel.setCurrentIndex(0)
        self.status_remaining_ramp.setDeviation(1)
        self.status_remaining_ramp.setValue(0)

    def updateRamp(self):
        """Called periodically to update the voltage ramp"""

        time_available = self.spinbox_ramp_time.value() * 60
        time_spent = (datetime.now() - self.ramp_start_time).total_seconds()
        time_remaining = time_available - time_spent

        if time_remaining > 0:
            self.status_remaining_ramp.setValue(time_remaining / 60)
            new_voltage = self.ramp_start_voltage - (self.ramp_start_voltage - self.spinbox_ramp_voltage.value()) * time_spent / time_available
        else:
            new_voltage = self.spinbox_ramp_voltage.value()
            self.stopRampVoltage()

        self.spinbox_voltages[self.ramp_channel].setValue(new_voltage)
        self.setVoltage(self.ramp_channel, new_voltage)

    def reset(self):
        """Resets everything to default"""

        self.device_wrapper.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')

        for row in self.channel_rows + self.limit_rows:
            row.reset()

        self.spinbox_advanced_settings_ramp.reset()
        self.stopRampVoltage()

        self.combobox_connection.setEnabled(True)
        self.button_connection_refresh.setEnabled(True)
        self.setComportsComboBox()

    def setComportsComboBox(self):
        """Sets available ports in the comports combobox"""

        comports = getComports(not_available_entry=True)
        comport_ports = [port for port, description, hardware_id in comports]
        comport_description = [f'{port}: {description} [{hardware_id}]' for port, description, hardware_id in comports]

        self.combobox_connection.reinitialize(
            entries=comport_ports,
            tooltips=comport_description
        )

    def closeEvent(self):
        """Must be called when application is closed"""

        self.device_wrapper.threaded_connection.close()

        # remember the port if connected or if the connection was lost (not if the user disconnected)
        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port or self.combobox_connection.getValue(text=True)
        self.auto_reconnect.stop()
        if self.connection is not None:
            self.connection.close()

        GlobalConf.updateConnections(psu=last_connection)

    def databaseLabels(self) -> dict[str, tuple[str, str]]:
        """Returns the labels of the channels for the database as {database_column: (label, unit)}"""

        labels = {}
        for row in self.channel_rows:
            labels[f'Channel{row.channel}_Voltage'] = (f'{row.name} Voltage', 'V')
            labels[f'Channel{row.channel}_Current'] = (f'{row.name} Current', 'A')
        return labels

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if not self.checkConnection(False):
            return

        values = []
        for row in self.channel_rows:
            values.extend([row.status_voltage.value, row.status_current.value])
        db.insertPSU(*values)
