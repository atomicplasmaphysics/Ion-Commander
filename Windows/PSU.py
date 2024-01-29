from serial import SerialException


from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, PolarityButton, SpinBox, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.USBPorts import getComports
from Connection.ISEG import ISEGConnection
from Connection.Threaded import ThreadedISEGConnection


class PSUVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        # TODO: do not use hardcoded interval time
        self.update_timer.setInterval(1000)
        self.update_timer.start()

        # TODO: make indicator sizes global somewhere
        indicator_size = QSize(20, 20)

        self.connection: None | ISEGConnection = None
        self.threaded_connection: None | ThreadedISEGConnection = None

        self.comports = getComports()
        self.comport_ports = [port for port, description, hardware_id in self.comports]
        self.comport_description = [f'{port}: {description} [{hardware_id}]' for port, description, hardware_id in self.comports]

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection')
        self.addWidget(self.connection_group_box)

        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_group_box.setLayout(self.connection_hbox)

        self.connection_grid = InsertingGridLayout()
        self.connection_hbox.addLayout(self.connection_grid)

        # TODO: remove clickable from all <IndicatorLed> instances
        # TODO: change values of <DisplayLabel> instances to None

        # Connection
        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(size=indicator_size, off_color=Colors.cooperate_error)
        self.status_connection = QLabel('Not connected')
        self.combobox_connection = ComboBox(entries=self.comport_ports, tooltips=self.comport_description)
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2),
            self.combobox_connection,
            self.button_connection
        )

        # TODO: do we need high voltage?
        # High Voltage
        self.label_high_voltage = QLabel('High Voltage')
        self.indicator_high_voltage = IndicatorLed(size=indicator_size)
        self.status_high_voltage = QLabel('Disabled')
        self.button_high_voltage = QPushButton('Enable')
        self.button_high_voltage.pressed.connect(lambda: self.setGlobalOutput(not self.indicator_high_voltage.value()))
        self.connection_grid.addWidgets(
            self.label_high_voltage,
            self.indicator_high_voltage,
            self.status_high_voltage,
            self.button_high_voltage
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
        self.spinbox_1 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_1.valueChanged.connect(lambda: self.setVoltage(0, self.spinbox_1.value()))
        self.status_voltage_1 = DisplayLabel(0, unit='V')
        self.status_current_1 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_1 = IndicatorLed(size=indicator_size)
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
        self.spinbox_2 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_2.valueChanged.connect(lambda: self.setVoltage(1, self.spinbox_2.value()))
        self.status_voltage_2 = DisplayLabel(0, unit='V')
        self.status_current_2 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_2 = IndicatorLed(size=indicator_size)
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
        self.spinbox_3 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_3.valueChanged.connect(lambda: self.setVoltage(2, self.spinbox_3.value()))
        self.status_voltage_3 = DisplayLabel(0, unit='V')
        self.status_current_3 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_3 = IndicatorLed(size=indicator_size)
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
        self.spinbox_4 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_4.valueChanged.connect(lambda: self.setVoltage(3, self.spinbox_4.value()))
        self.status_voltage_4 = DisplayLabel(0, unit='V')
        self.status_current_4 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_4 = IndicatorLed(size=indicator_size)
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
            QLabel('Voltage [V]'),
            QLabel('Current [mA]'),
            QLabel('Reached')
        )

        # TODO: adjust current limit spin-boxes

        # MCP
        self.label_limit_1 = QLabel('MCP Front/Back')
        self.spinbox_limit_voltage_1 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_voltage_1.valueChanged.connect(lambda: self.setVoltageLimit(0, self.spinbox_limit_voltage_1.value()))
        self.spinbox_limit_current_1 = DoubleSpinBox(default=0, step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.spinbox_limit_current_1.valueChanged.connect(lambda: self.setCurrentLimit(0, self.spinbox_limit_current_1.value()))
        self.indicator_limit_1 = IndicatorLed(size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_1,
            self.spinbox_limit_voltage_1,
            self.spinbox_limit_current_1,
            self.indicator_limit_1
        )

        # Anode
        self.label_limit_2 = QLabel('Anode')
        self.spinbox_limit_voltage_2 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_voltage_2.valueChanged.connect(lambda: self.setVoltageLimit(1, self.spinbox_limit_voltage_2.value()))
        self.spinbox_limit_current_2 = DoubleSpinBox(default=0, step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.spinbox_limit_current_2.valueChanged.connect(lambda: self.setCurrentLimit(1, self.spinbox_limit_current_2.value()))
        self.indicator_limit_2 = IndicatorLed(size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_2,
            self.spinbox_limit_voltage_2,
            self.spinbox_limit_current_2,
            self.indicator_limit_2
        )

        # Cathode LSD
        self.label_limit_3 = QLabel('Cathode LSD')
        self.spinbox_limit_voltage_3 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_voltage_3.valueChanged.connect(lambda: self.setVoltageLimit(2, self.spinbox_limit_voltage_3.value()))
        self.spinbox_limit_current_3 = DoubleSpinBox(default=0, step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.spinbox_limit_current_3.valueChanged.connect(lambda: self.setCurrentLimit(2, self.spinbox_limit_current_3.value()))
        self.indicator_limit_3 = IndicatorLed(size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_3,
            self.spinbox_limit_voltage_3,
            self.spinbox_limit_current_3,
            self.indicator_limit_3
        )

        # Focus LSD
        self.label_limit_4 = QLabel('Focus LSD')
        self.spinbox_limit_voltage_4 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_voltage_4.valueChanged.connect(lambda: self.setVoltageLimit(3, self.spinbox_limit_voltage_4.value()))
        self.spinbox_limit_current_4 = DoubleSpinBox(default=0, step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.spinbox_limit_current_4.valueChanged.connect(lambda: self.setCurrentLimit(3, self.spinbox_limit_current_4.value()))
        self.indicator_limit_4 = IndicatorLed(size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_4,
            self.spinbox_limit_voltage_4,
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
        self.spinbox_advanced_settings_ramp = DoubleSpinBox(default=0, step_size=0.001, input_range=(0, 100), decimals=3, buttons=True)
        self.spinbox_advanced_settings_ramp.valueChanged.connect(lambda: self.setRampSpeed(self.spinbox_advanced_settings_ramp.value()))
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
        self.spinbox_ramp_time = SpinBox(default=15, step_size=1, input_range=(0, 600), buttons=True)
        self.ramp_grid.addWidgets(
            self.label_ramp_time,
            self.spinbox_ramp_time
        )

        # Final Value
        self.label_ramp_final = QLabel('Voltage [V]')
        self.spinbox_ramp_voltage = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
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
        self.button_ramp = QPushButton('Start')
        self.status_ramp = QLabel('Remaining time:')
        self.status_remaining_ramp = DisplayLabel(value=0, target_value=15, deviation=1, unit='min')
        self.ramp_grid.addWidgets(
            self.status_ramp,
            self.status_remaining_ramp,
            self.button_ramp
        )

        # TODO: remove this hardcoded value, but load it from settings and set comport on startup to last set comport
        self.connect('COM1', False)

        self.reset()

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

        if not self.checkConnection(False):
            return

        self.indicator_limit_1.setValue(False)
        self.indicator_limit_2.setValue(False)
        self.indicator_limit_3.setValue(False)
        self.indicator_limit_4.setValue(False)

        def highVoltage(state: bool):
            if not isinstance(state, bool):
                raise ValueError('State must be bool')

            self.indicator_high_voltage.setValue(state)
            self.status_high_voltage.setText('Enabled' if state else 'Disabled')
            self.button_high_voltage.setText('Disable' if state else 'Enable')

        # TODO: what is query of general output state?
        #self.threaded_connection.callback(highVoltage, self.threaded_connection...)

        def voltageOn(states: list[float]):
            indicators = [
                self.indicator_1,
                self.indicator_2,
                self.indicator_3,
                self.indicator_4
            ]

            buttons = [
                self.button_enable_1,
                self.button_enable_2,
                self.button_enable_3,
                self.button_enable_4
            ]

            if len(states) != len(indicators) != len(buttons):
                raise ValueError('High voltage indicators cannot be set, non matching length')

            for indicator, state, button in zip(indicators, states, buttons):
                state = bool(state)
                indicator.setValue(state)
                button.setText('Disable' if state else 'Enable')

        self.threaded_connection.callback(voltageOn, self.threaded_connection.readVoltageOn('0-3'))

        def setVoltage(voltages: list[float]):
            status_voltages = [
                self.status_voltage_1,
                self.status_voltage_2,
                self.status_voltage_3,
                self.status_voltage_4
            ]
            indicator_limits = [
                self.indicator_limit_1,
                self.indicator_limit_2,
                self.indicator_limit_3,
                self.indicator_limit_4
            ]
            voltage_limits = [
                self.spinbox_limit_voltage_1,
                self.spinbox_limit_voltage_2,
                self.spinbox_limit_voltage_3,
                self.spinbox_limit_voltage_4
            ]

            if len(voltages) != len(status_voltages) != len(indicator_limits) != len(voltage_limits):
                raise ValueError('Measured voltages cannot be set, non matching length')

            for status_voltage, indicator_limit, voltage_limit, voltage in zip(status_voltages, indicator_limits, voltage_limits, voltages):
                status_voltage.setValue(voltage)
                if voltage >= voltage_limit:
                    indicator_limit.setValue(True)

        self.threaded_connection.callback(setVoltage, self.threaded_connection.measureVoltage('0-3'))

        def setCurrent(currents: list[float]):
            status_currents = [
                self.status_current_1,
                self.status_current_2,
                self.status_current_3,
                self.status_current_4
            ]
            indicator_limits = [
                self.indicator_limit_1,
                self.indicator_limit_2,
                self.indicator_limit_3,
                self.indicator_limit_4
            ]
            current_limits = [
                self.spinbox_limit_current_1,
                self.spinbox_limit_current_2,
                self.spinbox_limit_current_3,
                self.spinbox_limit_current_4
            ]

            if len(currents) != len(status_currents) != len(indicator_limits) != len(current_limits):
                raise ValueError('Measured currents cannot be set, non matching length')

            for status_current, indicator_limit, current_limit, current in zip(status_currents, indicator_limits, current_limits, currents):
                status_current.setValue(current)
                if current >= current_limit:
                    indicator_limit.setValue(True)

        self.threaded_connection.callback(setCurrent, self.threaded_connection.measureCurrent('0-3'))

        def setPolarity(polarities: list[bool]):
            status_polarities = [
                self.button_polarity_1,
                self.button_polarity_2,
                self.button_polarity_3,
                self.button_polarity_4
            ]

            if len(polarities) != len(status_polarities):
                raise ValueError('Measured polarities cannot be set, non matching length')

            for status_polarity, polarity in zip(status_polarities, polarities):
                status_polarity.polarityChange(polarity)

        self.threaded_connection.callback(setPolarity, self.threaded_connection.configureOutputPolarityGet('0-3'))


    def updateAllValues(self):
        """Updates all values"""

        if not self.checkConnection(False):
            return

        self.updateLoop()

        def setVoltage(voltages: list[float]):
            set_voltages = [
                self.spinbox_1,
                self.spinbox_2,
                self.spinbox_3,
                self.spinbox_4
            ]

            if len(voltages) != len(set_voltages):
                raise ValueError('Set voltages cannot be set, non matching length')

            for set_voltage, voltage in zip(set_voltages, voltages):
                set_voltage.setValue(voltage)

        self.threaded_connection.callback(setVoltage, self.threaded_connection.readVoltage('0-3'))

        def setVoltageLimit(voltages: list[float]):
            set_voltages = [
                self.spinbox_limit_voltage_1,
                self.spinbox_limit_voltage_2,
                self.spinbox_limit_voltage_3,
                self.spinbox_limit_voltage_4
            ]

            if len(voltages) != len(set_voltages):
                raise ValueError('Set voltages cannot be set, non matching length')

            for set_voltage, voltage in zip(set_voltages, voltages):
                set_voltage.setValue(voltage)

        self.threaded_connection.callback(setVoltageLimit, self.threaded_connection.readVoltageBoundaries('0-3'))

        def setCurrentLimit(currents: list[float]):
            set_currents = [
                self.spinbox_limit_current_1,
                self.spinbox_limit_current_2,
                self.spinbox_limit_current_3,
                self.spinbox_limit_current_4
            ]

            if len(currents) != len(set_currents):
                raise ValueError('Set voltages cannot be set, non matching length')

            for set_current, current in zip(set_currents, currents):
                set_current.setValue(current)

        self.threaded_connection.callback(setCurrentLimit, self.threaded_connection.readCurrentBoundaries('0-3'))

        self.threaded_connection.callback(self.spinbox_advanced_settings_ramp.setValue, self.threaded_connection.configureRampVoltageGet())

    def setVoltage(self, channel: int, voltage: float):
        """
        Sets voltage to specified channel

        :param channel: channel to be set
        :param voltage: voltage to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.voltageSet(channel, voltage)

    def setVoltageLimit(self, channel: int, voltage: float):
        """
        Sets voltage limit to specified channel

        :param channel: channel to be set
        :param voltage: voltage to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.voltageBoundarySet(channel, voltage)

    def setCurrentLimit(self, channel: int, current: float):
        """
        Sets current limit to specified channel

        :param channel: channel to be set
        :param current: current to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.currentBoundarySet(channel, current)

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

        polarities = [
            self.button_polarity_1,
            self.button_polarity_2,
            self.button_polarity_3,
            self.button_polarity_4
        ]
        if polarities[channel].state == polarity:
            return

        high_voltages = [
            self.indicator_1,
            self.indicator_2,
            self.indicator_3,
            self.indicator_4
        ]
        if high_voltages[channel].value():
            showMessageBox(
                None,
                QMessageBox.Icon.Information,
                'Polarity switch',
                'Polarity can only be switched if high voltage of the same channel is turned off'
            )
            return

        self.threaded_connection.configureOutputPolaritySet(channel, polarity)

        # TODO: set all other channels on again

    def setGlobalOutput(self, state: bool):
        """
        Sets global output state

        :param state: state of global output to be set
        """

        if not self.checkConnection():
            return

        # TODO: what is query to set general output state?
        #self.threaded_connection...

    def checkConnection(self, messagebox: bool = True) -> bool:
        """
        Checks if connection is established and pops up messagebox if it does not

        :param messagebox: enable popup of infobox
        """

        if self.indicator_connection.value():
            return True

        if messagebox:
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'Connection warning!',
                'ISEG crate power supply is not connected, please connect first!'
            )

        return False

    def connect(self, comport: str = '', messagebox: bool = True):
        """
        Connect to given comport. If no comport is given, the current selected comport will be connected to

        :param comport: comport to connect to
        :param messagebox: show messagebox if failed
        """

        if comport:
            entries = {port.lower(): i for i, port in enumerate(self.combobox_connection.entries)}
            if comport in entries.keys():
                self.combobox_connection.setCurrentIndex(entries[comport])
        else:
            comport = self.combobox_connection.getValue(text=True)

        if self.threaded_connection is not None:
            self.threaded_connection.close()
            self.threaded_connection = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        self.connection = ISEGConnection(comport, echo=True, cleaning=True)
        try:
            self.connection.open()
            self.threaded_connection = ThreadedISEGConnection(self.connection)
            self.indicator_connection.setValue(True)
            self.status_connection.setText('Connected')

        except (SerialException, ConnectionError) as error:
            try:
                self.connection.close()
            except ConnectionError:
                pass
            self.connection = None
            self.reset()

            if messagebox:
                showMessageBox(
                    None,
                    QMessageBox.Icon.Critical,
                    'Connection error!',
                    'Could not connect to ISEG crate power supply!',
                    f'<strong>Encountered Error:</strong><br>{error}',
                    expand_details=False
                )
            GlobalConf.logger.info(f'Connection error! Could not connect to ISEG crate power supply, because of: {error}')

    def reset(self):
        """Resets everything to default"""

        if self.threaded_connection is not None:
            self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')

        self.indicator_high_voltage.setValue(False)
        self.label_high_voltage.setText('Disabled')
        self.button_high_voltage.setText('Enable')

        self.button_polarity_1.reset()
        self.spinbox_1.reset()
        self.status_voltage_1.setValue(0)
        self.status_current_1.setValue(0)
        self.indicator_1.setValue(False)
        self.button_enable_1.setText('Enable')

        self.button_polarity_2.reset()
        self.spinbox_2.reset()
        self.status_voltage_2.setValue(0)
        self.status_current_2.setValue(0)
        self.indicator_2.setValue(False)
        self.button_enable_2.setText('Enable')

        self.button_polarity_3.reset()
        self.spinbox_3.reset()
        self.status_voltage_3.setValue(0)
        self.status_current_3.setValue(0)
        self.indicator_3.setValue(False)
        self.button_enable_3.setText('Enable')

        self.button_polarity_4.reset()
        self.spinbox_4.reset()
        self.status_voltage_4.setValue(0)
        self.status_current_4.setValue(0)
        self.indicator_4.setValue(False)
        self.button_enable_4.setText('Enable')
        
        self.spinbox_limit_voltage_1.reset()
        self.spinbox_limit_current_1.reset()
        self.indicator_limit_1.setValue(False)

        self.spinbox_limit_voltage_2.reset()
        self.spinbox_limit_current_2.reset()
        self.indicator_limit_2.setValue(False)

        self.spinbox_limit_voltage_3.reset()
        self.spinbox_limit_current_3.reset()
        self.indicator_limit_3.setValue(False)

        self.spinbox_limit_voltage_4.reset()
        self.spinbox_limit_current_4.reset()
        self.indicator_limit_4.setValue(False)

        self.spinbox_advanced_settings_ramp.reset()
        self.spinbox_ramp_time.setValue(15)
        self.spinbox_ramp_voltage.reset()
        self.combobox_ramp_channel.setCurrentIndex(0)
        self.status_remaining_ramp.setValue(0)
        self.status_remaining_ramp.setDeviation(1)
        self.status_remaining_ramp.setTargetValue(15)

        self.setComportsComboBox()

    def setComportsComboBox(self):
        """Sets available ports in the comports combobox"""

        comports = getComports()
        comport_ports = [port for port, description, hardware_id in comports]
        comport_description = [f'{port}: {description} [{hardware_id}]' for port, description, hardware_id in comports]

        self.combobox_connection.reinitialize(
            entries=comport_ports,
            tooltips=comport_description
        )

    def closeEvent(self):
        """Must be called when application is closed"""

        if self.threaded_connection is not None:
            self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()
