from serial import SerialException


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.USBPorts import getComports
from Connection.ISEG import ISEGConnection
from Connection.Threaded import ThreadedISEGConnection, ThreadedDummyConnection


class EBISVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.active_message_box = False

        self.connection: None | ISEGConnection = None
        self.threaded_connection: ThreadedDummyConnection | ThreadedISEGConnection = ThreadedDummyConnection()

        self.voltage_deviation = DefaultParams.ebis_voltage_deviation
        self.voltage_maximum = DefaultParams.ebis_voltage_maximum
        self.current_maximum = DefaultParams.ebis_current_maximum
        self.current_deviation = DefaultParams.ebis_current_deviation

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

        # Potentials Group Box
        self.potential_group_box = QGroupBox('Potentials')
        self.addWidget(self.potential_group_box)

        self.potential_vbox = QVBoxLayout()
        self.potential_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.potential_group_box.setLayout(self.potential_vbox)

        self.highvoltage_hbox = QHBoxLayout()
        self.highvoltage_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.potential_vbox.addLayout(self.highvoltage_hbox)

        # High Voltage
        self.label_high_voltage = QLabel('High Voltage')
        self.indicator_high_voltage = IndicatorLed()
        self.status_high_voltage = QLabel('Disabled')
        self.button_high_voltage = QPushButton('Enable')
        self.button_high_voltage.pressed.connect(lambda: self.setGlobalOutput(not self.indicator_high_voltage.value()))
        self.highvoltage_hbox.addWidget(self.label_high_voltage)
        self.highvoltage_hbox.addWidget(self.indicator_high_voltage)
        self.highvoltage_hbox.addWidget(self.status_high_voltage)
        self.highvoltage_hbox.addWidget(self.button_high_voltage)

        self.potential_hbox = QHBoxLayout()
        self.potential_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.potential_vbox.addLayout(self.potential_hbox)

        self.potential_grid = InsertingGridLayout()
        self.potential_hbox.addLayout(self.potential_grid)

        # Labels
        self.potential_grid.addWidgets(
            None,
            QLabel('Set [V]'),
            QLabel('Voltage'),
            QLabel('Current'),
            (QLabel('High Voltage'), 2)
        )

        # Cathode Potential
        self.label_1 = QLabel('Cathode')
        self.spinbox_1 = DoubleSpinBox(default=0, step_size=50, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_1.editingFinished.connect(lambda: self.setVoltage(0, self.spinbox_1.value()))
        self.status_voltage_1 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_1 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_1 = IndicatorLed()
        self.button_1 = QPushButton('Enable')
        self.button_1.pressed.connect(lambda: self.setOutput(0, not self.indicator_1.value()))
        self.potential_grid.addWidgets(
            self.label_1,
            self.spinbox_1,
            self.status_voltage_1,
            self.status_current_1,
            self.indicator_1,
            self.button_1
        )

        # Drift Tube 1
        self.label_2 = QLabel('Drift Tube 1')
        self.spinbox_2 = DoubleSpinBox(default=0, step_size=50, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_2.editingFinished.connect(lambda: self.setVoltage(1, self.spinbox_2.value()))
        self.status_voltage_2 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_2 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_2 = IndicatorLed()
        self.button_2 = QPushButton('Enable')
        self.button_2.pressed.connect(lambda: self.setOutput(1, not self.indicator_2.value()))
        self.potential_grid.addWidgets(
            self.label_2,
            self.spinbox_2,
            self.status_voltage_2,
            self.status_current_2,
            self.indicator_2,
            self.button_2
        )

        # Drift Tube 2
        self.label_3 = QLabel('Drift Tube 2')
        self.spinbox_3 = DoubleSpinBox(default=0, step_size=50, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_3.editingFinished.connect(lambda: self.setVoltage(2, self.spinbox_3.value()))
        self.status_voltage_3 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_3 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_3 = IndicatorLed()
        self.button_3 = QPushButton('Enable')
        self.button_3.pressed.connect(lambda: self.setOutput(2, not self.indicator_3.value()))
        self.potential_grid.addWidgets(
            self.label_3,
            self.spinbox_3,
            self.status_voltage_3,
            self.status_current_3,
            self.indicator_3,
            self.button_3
        )

        # Drift Tube 3
        self.label_4 = QLabel('Drift Tube 3')
        self.spinbox_4 = DoubleSpinBox(default=0, step_size=50, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_4.editingFinished.connect(lambda: self.setVoltage(3, self.spinbox_4.value()))
        self.status_voltage_4 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_4 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_4 = IndicatorLed()
        self.button_4 = QPushButton('Enable')
        self.button_4.pressed.connect(lambda: self.setOutput(3, not self.indicator_4.value()))
        self.potential_grid.addWidgets(
            self.label_4,
            self.spinbox_4,
            self.status_voltage_4,
            self.status_current_4,
            self.indicator_4,
            self.button_4
        )

        # Repeller
        self.label_5 = QLabel('Repeller')
        self.spinbox_5 = DoubleSpinBox(default=0, step_size=50, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_5.editingFinished.connect(lambda: self.setVoltage(4, self.spinbox_5.value()))
        self.status_voltage_5 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_5 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_5 = IndicatorLed()
        self.button_5 = QPushButton('Enable')
        self.button_5.pressed.connect(lambda: self.setOutput(4, not self.indicator_5.value()))
        self.potential_grid.addWidgets(
            self.label_5,
            self.spinbox_5,
            self.status_voltage_5,
            self.status_current_5,
            self.indicator_5,
            self.button_5
        )

        # Heating Group Box
        self.heating_group_box = QGroupBox('Heating')
        self.addWidget(self.heating_group_box)

        self.heating_hbox = QHBoxLayout()
        self.heating_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.heating_group_box.setLayout(self.heating_hbox)

        self.heating_grid = InsertingGridLayout()
        self.heating_hbox.addLayout(self.heating_grid)

        # Labels
        self.heating_grid.addWidgets(
            None,
            QLabel('Set Value'),
            QLabel('Actual Value'),
            None,
            (QLabel('High Voltage'), 2)
        )

        # Cathode Heating Voltage
        self.label_voltage_6 = QLabel('Heating Voltage')
        self.spinbox_voltage_6 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 5), decimals=1, buttons=False)
        self.spinbox_voltage_6.editingFinished.connect(lambda: self.setVoltage(5, self.spinbox_voltage_6.value()))
        self.status_voltage_6 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.indicator_6 = IndicatorLed()
        self.button_6 = QPushButton('Enable')
        self.button_6.pressed.connect(lambda: self.setOutput(5, not self.indicator_6.value()))
        self.heating_grid.addWidgets(
            self.label_voltage_6,
            self.spinbox_voltage_6,
            self.status_voltage_6,
            None,
            self.indicator_6,
            self.button_6
        )

        # Cathode Heating Current
        self.label_current_6 = QLabel('Heating Current')
        # TODO: enable button here, but it will be stuck on the editingFinished if the warning label overtakes!
        self.spinbox_current_6 = DoubleSpinBox(default=0, step_size=0.01, input_range=(0, 5), decimals=2, buttons=False)
        self.spinbox_current_6.editingFinished.connect(lambda: self.setCurrent(5, self.spinbox_current_6.value()))
        self.status_current_6 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_deviation, decimals=4)
        self.heating_grid.addWidgets(
            self.label_current_6,
            self.spinbox_current_6,
            self.status_current_6,
        )

        # Pressure safety
        self.pressure_group_box = QGroupBox('Pressure Control')
        self.addWidget(self.pressure_group_box)

        self.pressure_hbox = QHBoxLayout()
        self.pressure_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.pressure_group_box.setLayout(self.pressure_hbox)

        self.pressure_grid = InsertingGridLayout()
        self.pressure_hbox.addLayout(self.pressure_grid)

        # Hard pressure limit (turns off immediately)
        self.label_hard_pmax = QLabel('Hard limit max pressure [10^-8 mbar]') # Not great but I dont want to make a new SpinBox class for scientific notation
        self.hard_pmax_val = 10
        self.spinbox_hard_pmax = DoubleSpinBox(default=self.hard_pmax_val, step_size=1, input_range=(0.1, 1000), decimals=1, buttons=False)
        self.spinbox_hard_pmax.editingFinished.connect(lambda: setattr(self, 'hard_pmax_val', self.spinbox_hard_pmax.value()*1E-8)) # set pressure in 10^-8mbar
        self.pressure_grid.addWidgets(
            self.label_hard_pmax,
            self.spinbox_hard_pmax
        )

        # Safe heating current
        self.label_hard_current = QLabel('Hard target current [A]')
        self.hard_current_val = 0.0
        self.spinbox_hard_current = DoubleSpinBox(default=self.hard_current_val, step_size=0.1, input_range=(0, 3), decimals=2, buttons=False)
        self.spinbox_hard_current.editingFinished.connect(lambda: setattr(self, 'hard_current_val', self.spinbox_hard_current.value()))
        self.pressure_grid.addWidgets(
            self.label_hard_current,
            self.spinbox_hard_current
        )

        # Soft pressure limit (turns off if avg perssure is over limit for too long)
        self.label_soft_pmax = QLabel('Soft limit max pressure [10^-8 mbar]')
        self.soft_pmax_val = 10
        self.spinbox_soft_pmax = DoubleSpinBox(default=self.soft_pmax_val, step_size=1, input_range=(0.11, 1000), decimals=1, buttons=False)
        self.spinbox_soft_pmax.editingFinished.connect(lambda: setattr(self, 'soft_pmax_val', self.spinbox_soft_pmax.value()*1E-8)) # set pressure in 10^-8mbar
        self.pressure_grid.addWidgets(
            self.label_soft_pmax,
            self.spinbox_soft_pmax
        )

        # Soft pressure limit time
        self.label_soft_pmax_time = QLabel('Soft limit duration [s]')
        self.soft_time_val = 3
        self.spinbox_soft_time = DoubleSpinBox(default=self.soft_time_val, step_size=1, input_range=(0, 100), decimals=1, buttons=False)
        self.spinbox_soft_time.editingFinished.connect(lambda: setattr(self, 'soft_time_val', self.spinbox_soft_time.value()))
        self.pressure_grid.addWidgets(
            self.label_soft_pmax_time,
            self.spinbox_soft_time
        )

        # Safe heating current
        self.label_soft_current = QLabel('Soft target current [A]')
        self.soft_current_val = 0.0
        self.spinbox_soft_current = DoubleSpinBox(default=self.soft_current_val, step_size=0.1, input_range=(0, 3), decimals=2, buttons=False)
        self.spinbox_soft_current.editingFinished.connect(lambda: setattr(self, 'soft_current_val', self.spinbox_soft_current.value()))
        self.pressure_grid.addWidgets(
            self.label_soft_current,
            self.spinbox_soft_current
        )

        # grouped items
        self.channel_dict = {
            0: 0,
            1: 2,
            2: 3,
            3: 4,
            4: 1,
            5: 10
        }
        self.all_channels_selector = [channel for _, channel in self.channel_dict.items()]
        self.spinbox_voltages = [
            self.spinbox_1,
            self.spinbox_2,
            self.spinbox_3,
            self.spinbox_4,
            self.spinbox_5,
            self.spinbox_voltage_6
        ]
        self.status_voltages = [
            self.status_voltage_1,
            self.status_voltage_2,
            self.status_voltage_3,
            self.status_voltage_4,
            self.status_voltage_5,
            self.status_voltage_6
        ]
        self.status_currents = [
            self.status_current_1,
            self.status_current_2,
            self.status_current_3,
            self.status_current_4,
            self.status_current_5,
            self.status_current_6
        ]
        self.indicators = [
            self.indicator_1,
            self.indicator_2,
            self.indicator_3,
            self.indicator_4,
            self.indicator_5,
            self.indicator_6
        ]
        self.buttons = [
            self.button_1,
            self.button_2,
            self.button_3,
            self.button_4,
            self.button_5,
            self.button_6
        ]

        self.reset()

        last_connection = GlobalConf.getConnection('ebis')
        if last_connection:
            self.connect(last_connection, False)

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

        if not self.checkConnection(False):
            return

        def checkHighVoltageOn(state: int):
            if not isinstance(state, int) or state == -1:
                GlobalConf.logger.error(f'State must be int and not -1, got <{type(state)}> with value {state}')
                return

            state = bool(state)
            self.indicator_high_voltage.setValue(state)
            self.status_high_voltage.setText('Enabled' if state else 'Disabled')
            self.button_high_voltage.setText('Disable' if state else 'Enable')

        self.threaded_connection.callback(checkHighVoltageOn, self.threaded_connection.configureMiccGet())

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

            for status_voltage, voltage in zip(self.status_voltages, voltages):
                status_voltage.setValue(voltage)

        self.threaded_connection.callback(measureVoltage, self.threaded_connection.measureVoltage(self.all_channels_selector))

        def measureCurrent(currents: list[float]):
            if len(currents) != len(self.status_currents):
                GlobalConf.logger.error(f'Measured currents cannot be set, non matching length: expected len = {len(self.status_currents)}, got len = {len(currents)}')
                return

            for status_current, current in zip(self.status_currents, currents):
                status_current.setValue(current)

        self.threaded_connection.callback(measureCurrent, self.threaded_connection.measureCurrent(self.all_channels_selector))

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
                spinbox_voltage.setValue(voltage)
                status_voltage.setTargetValue(voltage)

        self.threaded_connection.callback(readVoltage, self.threaded_connection.readVoltage(self.all_channels_selector))

        def readCurrent(current: float):
            if not isinstance(current, float):
                GlobalConf.logger.error(f'Set current cannot be set: expected <float> type, got {type(current)}')
                return

            self.spinbox_current_6.setValue(current)
            self.status_current_6.setTargetValue(current)

        self.threaded_connection.callback(readCurrent, self.threaded_connection.readCurrent(10))

    def setVoltage(self, channel: int, voltage: float):
        """
        Sets voltage to specified channel

        :param channel: channel to be set
        :param voltage: voltage to be set
        """

        if not self.checkConnection():
            return

        self.status_voltages[channel].setTargetValue(voltage)
        phys_channel = self.channel_dict[channel]
        self.threaded_connection.voltageSet(phys_channel, voltage)

    def setCurrent(self, channel: int, current: float):
        """
        Sets current to specified channel

        :param channel: channel to be set
        :param current: current to be set
        """

        if not self.checkConnection():
            return

        self.status_currents[channel].setTargetValue(current)
        phys_channel = self.channel_dict[channel]
        self.threaded_connection.currentSet(phys_channel, current)

    def setOutput(self, channel: int, state: bool):
        """
        Sets output state to specified channel

        :param channel: channel to be set
        :param state: state of output to be set
        """

        if not self.checkConnection():
            return

        if channel != 5 and not self.indicator_high_voltage.state and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(
                None,
                QMessageBox.Icon.Information,
                'Enable high voltage warning!',
                'General high voltage of EBIS power supply is not enabled, please enable it first!'
            )
            self.active_message_box = False

        phys_channel = self.channel_dict[channel]

        if state:
            self.threaded_connection.voltageOn(phys_channel)
        else:
            self.threaded_connection.voltageOff(phys_channel)

    def setGlobalOutput(self, state: bool):
        """
        Sets global output state

        :param state: state of global output to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.configureMiccSet(state)

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
                'EBIS power supply is not connected, please connect first!'
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
                strict='iseg Spezialelektronik GmbH,MICCETH,5200180,4.28'
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

                GlobalConf.logger.info(f'Connection error! Could not connect to EBIS power supply on port "{comport}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to EBIS power supply on port "{comport}"!',
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

    def reset(self):
        """Resets everything to default"""

        self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')

        self.indicator_high_voltage.setValue(False)
        self.status_high_voltage.setText('Disabled')
        self.button_high_voltage.setText('Enable')

        for indicator in self.indicators:
            indicator.setValue(False)

        for button in self.buttons:
            button.setText('Enable')

        for spinbox_voltage in self.spinbox_voltages:
            spinbox_voltage.reset()

        for status_voltage in self.status_voltages:
            status_voltage.setValue(0)
            status_voltage.setTargetValue(0)

        for status_current in self.status_currents:
            status_current.setValue(0)
            status_current.setTargetValue(0)

        self.spinbox_current_6.reset()

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

        GlobalConf.updateConnections(ebis=last_connection)

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if self.connection is not None:
            db.insertEBIS(
                abs(self.status_voltage_1.value),  # CatV, negative
                abs(self.status_current_1.value),  # CatI, negative
                self.status_voltage_2.value,  # DT1V
                self.status_current_2.value,  # DT1I
                self.status_voltage_3.value,  # DT2V
                self.status_current_3.value,  # DT2I
                self.status_voltage_4.value,  # DT3V
                self.status_current_4.value,  # DT3I
                abs(self.status_voltage_5.value),  # RepV, negative
                abs(self.status_current_5.value),  # RepI, negative
                self.status_voltage_6.value,  # HeatV
                self.status_current_6.value   # HeatI
            )