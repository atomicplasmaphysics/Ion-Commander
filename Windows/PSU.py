from datetime import datetime


from serial import SerialException


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, PolarityButton, SpinBox, ComboBox
from Utility.Dialogs import showMessageBox

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

        self.connection_wrapper = DeviceWrapper()
        self.connection: None | ISEGConnection = None
        self.threaded_connection: ThreadedDummyConnection | ThreadedISEGConnection = self.connection_wrapper.threaded_connection
        self.threaded_connection = ThreadedDummyConnection()

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
        self.status_connection = QLabel('Not connected')
        self.combobox_connection = ComboBox()
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(QIcon('icons/refresh.png'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2),
            self.combobox_connection,
            self.button_connection,
            self.button_connection_refresh
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

        # MCP
        self.label_1 = QLabel('MCP Front/Back')
        self.button_polarity_1 = PolarityButton(connected_buttons=False)
        self.button_polarity_1.pressed.connect(lambda state: self.setPolarity(0, state))
        self.spinbox_1 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_1.editingFinished.connect(lambda: self.setVoltage(0, self.spinbox_1.value()))
        self.status_voltage_1 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_1 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_1 = IndicatorLed()
        self.button_enable_1 = QPushButton('Enable')
        self.button_enable_1.pressed.connect(lambda: self.setOutput(0, not self.indicator_1.value()))
        self.control_grid.addWidgets(
            self.label_1,
            self.button_polarity_1,
            self.spinbox_1,
            self.status_voltage_1,
            self.status_current_1,
            self.indicator_1,
            self.button_enable_1
        )

        # Anode
        self.label_2 = QLabel('Anode')
        self.button_polarity_2 = PolarityButton(connected_buttons=False)
        self.button_polarity_2.pressed.connect(lambda state: self.setPolarity(1, state))
        self.spinbox_2 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_2.editingFinished.connect(lambda: self.setVoltage(1, self.spinbox_2.value()))
        self.status_voltage_2 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_2 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_2 = IndicatorLed()
        self.button_enable_2 = QPushButton('Enable')
        self.button_enable_2.pressed.connect(lambda: self.setOutput(1, not self.indicator_2.value()))
        self.control_grid.addWidgets(
            self.label_2,
            self.button_polarity_2,
            self.spinbox_2,
            self.status_voltage_2,
            self.status_current_2,
            self.indicator_2,
            self.button_enable_2
        )

        # Cathode LSD
        self.label_3 = QLabel('Cathode LSD')
        self.button_polarity_3 = PolarityButton(connected_buttons=False)
        self.button_polarity_3.pressed.connect(lambda state: self.setPolarity(2, state))
        self.spinbox_3 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_3.editingFinished.connect(lambda: self.setVoltage(2, self.spinbox_3.value()))
        self.status_voltage_3 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_3 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_3 = IndicatorLed()
        self.button_enable_3 = QPushButton('Enable')
        self.button_enable_3.pressed.connect(lambda: self.setOutput(2, not self.indicator_3.value()))
        self.control_grid.addWidgets(
            self.label_3,
            self.button_polarity_3,
            self.spinbox_3,
            self.status_voltage_3,
            self.status_current_3,
            self.indicator_3,
            self.button_enable_3
        )

        # Focus LSD
        self.label_4 = QLabel('Focus LSD')
        self.button_polarity_4 = PolarityButton(connected_buttons=False)
        self.button_polarity_4.pressed.connect(lambda state: self.setPolarity(3, state))
        self.spinbox_4 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_4.editingFinished.connect(lambda: self.setVoltage(3, self.spinbox_4.value()))
        self.status_voltage_4 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_4 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_4 = IndicatorLed()
        self.button_enable_4 = QPushButton('Enable')
        self.button_enable_4.pressed.connect(lambda: self.setOutput(3, not self.indicator_4.value()))
        self.control_grid.addWidgets(
            self.label_4,
            self.button_polarity_4,
            self.spinbox_4,
            self.status_voltage_4,
            self.status_current_4,
            self.indicator_4,
            self.button_enable_4
        )

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

        # MCP
        self.label_limit_1 = QLabel('MCP Front/Back')
        self.spinbox_limit_current_1 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 2), decimals=5, buttons=False)
        self.spinbox_limit_current_1.editingFinished.connect(lambda: self.setCurrentLimit(0, self.spinbox_limit_current_1.value()))
        self.indicator_limit_1 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_1,
            self.spinbox_limit_current_1,
            self.indicator_limit_1
        )

        # Anode
        self.label_limit_2 = QLabel('Anode')
        self.spinbox_limit_current_2 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 2), decimals=5, buttons=False)
        self.spinbox_limit_current_2.editingFinished.connect(lambda: self.setCurrentLimit(1, self.spinbox_limit_current_2.value()))
        self.indicator_limit_2 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_2,
            self.spinbox_limit_current_2,
            self.indicator_limit_2
        )

        # Cathode LSD
        self.label_limit_3 = QLabel('Cathode LSD')
        self.spinbox_limit_current_3 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 2), decimals=5, buttons=False)
        self.spinbox_limit_current_3.editingFinished.connect(lambda: self.setCurrentLimit(2, self.spinbox_limit_current_3.value()))
        self.indicator_limit_3 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_3,
            self.spinbox_limit_current_3,
            self.indicator_limit_3
        )

        # Focus LSD
        self.label_limit_4 = QLabel('Focus LSD')
        self.spinbox_limit_current_4 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 2), decimals=5, buttons=False)
        self.spinbox_limit_current_4.editingFinished.connect(lambda: self.setCurrentLimit(3, self.spinbox_limit_current_4.value()))
        self.indicator_limit_4 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_4,
            self.spinbox_limit_current_4,
            self.indicator_limit_4
        )

        # Advanced Settings Group Box
        self.advanced_settings_group_box = QGroupBox('Advanced Settings')
        self.addWidget(self.advanced_settings_group_box)

        self.advanced_settings_hbox = QHBoxLayout()
        self.advanced_settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.advanced_settings_group_box.setLayout(self.advanced_settings_hbox)

        self.advanced_settings_grid = InsertingGridLayout()
        self.advanced_settings_hbox.addLayout(self.advanced_settings_grid)

        # Speed
        # TODO: get limits, unit and number of decimals right
        self.label_advanced_settings_ramp = QLabel('Ramp speed [%/s]')
        self.spinbox_advanced_settings_ramp = DoubleSpinBox(default=0, step_size=0.01, input_range=(0, 20), decimals=2, buttons=False)
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
        self.spinbox_ramp_time = SpinBox(default=self.time_ramp_default, step_size=1, input_range=(0, 600), buttons=False)
        self.ramp_grid.addWidgets(
            self.label_ramp_time,
            self.spinbox_ramp_time
        )

        # Final Value
        self.label_ramp_final = QLabel('Target Voltage [V]')
        self.spinbox_ramp_voltage = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.ramp_grid.addWidgets(
            self.label_ramp_final,
            self.spinbox_ramp_voltage
        )

        # Channel
        self.label_ramp_channel = QLabel('Channel')
        self.combobox_ramp_channel = ComboBox(default=0, entries=[self.label_1.text(), self.label_2.text(), self.label_3.text(), self.label_4.text()])
        self.ramp_grid.addWidgets(
            self.label_ramp_channel,
            self.combobox_ramp_channel
        )

        # Start
        self.status_ramp = QLabel('Remaining time:')
        self.status_remaining_ramp = DisplayLabel(value=0, target_value=0, deviation=1, unit='min')
        self.indicator_ramp = IndicatorLed()
        self.button_ramp = QPushButton('Start ramp')
        self.button_ramp.clicked.connect(self.startRampVoltage)
        self.ramp_grid.addWidgets(
            self.status_ramp,
            self.status_remaining_ramp,
            self.indicator_ramp,
            self.button_ramp
        )

        # grouped items
        self.all_channels_selector = '0-3'
        self.indicators = [
            self.indicator_1,
            self.indicator_2,
            self.indicator_3,
            self.indicator_4
        ]
        self.buttons = [
            self.button_enable_1,
            self.button_enable_2,
            self.button_enable_3,
            self.button_enable_4
        ]
        self.status_voltages = [
            self.status_voltage_1,
            self.status_voltage_2,
            self.status_voltage_3,
            self.status_voltage_4
        ]
        self.indicator_limits = [
            self.indicator_limit_1,
            self.indicator_limit_2,
            self.indicator_limit_3,
            self.indicator_limit_4
        ]
        self.status_currents = [
            self.status_current_1,
            self.status_current_2,
            self.status_current_3,
            self.status_current_4
        ]
        self.spinbox_limit_currents = [
            self.spinbox_limit_current_1,
            self.spinbox_limit_current_2,
            self.spinbox_limit_current_3,
            self.spinbox_limit_current_4
        ]
        self.button_polarities = [
            self.button_polarity_1,
            self.button_polarity_2,
            self.button_polarity_3,
            self.button_polarity_4
        ]
        self.spinbox_voltages = [
            self.spinbox_1,
            self.spinbox_2,
            self.spinbox_3,
            self.spinbox_4
        ]

        self.reset()

        last_connection = GlobalConf.getConnection('psu')
        if last_connection:
            self.connect(last_connection, False)

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

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

        self.threaded_connection.callback(checkVoltageOn, self.threaded_connection.readVoltageOn(self.all_channels_selector))

        def measureVoltage(voltages: list[float]):
            if len(voltages) != len(self.status_voltages):
                GlobalConf.logger.error(f'Measured voltages cannot be set, non matching length: expected len = {len(self.status_voltages)}, got len = {len(voltages)}')
                return

            if any([0 if isinstance(voltage, float) else 1 for voltage in voltages]):
                GlobalConf.logger.error(f'Measured voltages cannot be set, types of currents are: {[type(voltage) for voltage in voltages]}, expected only <float>s')
                return

            for status_voltage, voltage in zip(self.status_voltages, voltages):
                status_voltage.setValue(voltage)

        self.threaded_connection.callback(measureVoltage, self.threaded_connection.measureVoltage(self.all_channels_selector))

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

        self.threaded_connection.callback(measureCurrent, self.threaded_connection.measureCurrent(self.all_channels_selector))

        def checkPolarity(polarities: list[bool]):
            if len(polarities) != len(self.button_polarities):
                GlobalConf.logger.error(f'Measured polarities cannot be set, non matching length: expected len = {len(self.button_polarities)}, got len = {len(polarities)}')
                return

            for button_polarity, polarity in zip(self.button_polarities, polarities):
                button_polarity.polarityChange(polarity)

        self.threaded_connection.callback(checkPolarity, self.threaded_connection.configureOutputPolarityGet(self.all_channels_selector))

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

        self.threaded_connection.callback(readVoltage, self.threaded_connection.readVoltage(self.all_channels_selector))

        def readCurrentLimit(currents: list[float]):
            if len(currents) != len(self.spinbox_limit_currents):
                GlobalConf.logger.error(f'Set voltages cannot be set, non matching length: expected len = {len(self.spinbox_limit_currents)}, got len = {len(currents)}')
                return

            for (spinbox_limit_current, current) in zip(self.spinbox_limit_currents, currents):
                spinbox_limit_current.setValue(current * 1000)

        self.threaded_connection.callback(readCurrentLimit, self.threaded_connection.readCurrent(self.all_channels_selector))

        self.threaded_connection.callback(self.spinbox_advanced_settings_ramp.setValue, self.threaded_connection.configureRampVoltageGet())

    def setVoltage(self, channel: int, voltage: float):
        """
        Sets voltage to specified channel

        :param channel: channel to be set
        :param voltage: voltage to be set
        """

        if not self.checkConnection():
            return

        self.status_voltages[channel].setTargetValue(voltage)
        self.threaded_connection.voltageSet(channel, voltage)

    def setCurrentLimit(self, channel: int, current: float):
        """
        Sets current limit to specified channel

        :param channel: channel to be set
        :param current: current to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.currentSet(channel, current / 1000)

    def setOutput(self, channel: int, state: bool):
        """
        Sets output state to specified channel

        :param channel: channel to be set
        :param state: state of output to be set
        """

        if not self.checkConnection():
            return

        if state:
            self.threaded_connection.voltageOn(channel)
        else:
            self.threaded_connection.voltageOff(channel)

    def setRampSpeed(self, speed: float):
        """
        Sets ramp speed

        :param speed: ramp speed in %/min
        """

        if not self.checkConnection():
            return

        self.threaded_connection.configureRampVoltageSet(speed)

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

        self.threaded_connection.configureOutputPolaritySet(channel, polarity)

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

        connect = self.threaded_connection.isDummy()

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
                self.threaded_connection = ThreadedISEGConnection(self.connection)
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
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

    def unconnect(self):
        """Disconnect from any port"""

        self.threaded_connection.close()
        self.threaded_connection = ThreadedDummyConnection()
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

        self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')

        for indicator in self.indicators:
            indicator.setValue(False)

        for button in self.buttons:
            button.setText('Enable')

        for polarity in self.button_polarities:
            polarity.reset()

        for spinbox_voltage in self.spinbox_voltages:
            spinbox_voltage.reset()

        for status_voltage in self.status_voltages:
            status_voltage.setValue(0)
            status_voltage.setTargetValue(0)

        for status_current in self.status_currents:
            status_current.setValue(0)
            status_current.setTargetValue(0)

        for spinbox_limit_current in self.spinbox_limit_currents:
            spinbox_limit_current.reset()

        for indicator_limit in self.indicator_limits:
            indicator_limit.setValue(False)

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

        self.threaded_connection.close()

        last_connection = ''
        if self.connection is not None:
            last_connection = self.combobox_connection.getValue(text=True)
            self.connection.close()

        GlobalConf.updateConnections(psu=last_connection)

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if not self.checkConnection(False):
            return

        db.insertPSU(
            self.status_voltage_1.value,
            self.status_current_1.value,
            self.status_voltage_2.value,
            self.status_current_2.value,
            self.status_voltage_3.value,
            self.status_current_3.value,
            self.status_voltage_4.value,
            self.status_current_4.value,
        )
