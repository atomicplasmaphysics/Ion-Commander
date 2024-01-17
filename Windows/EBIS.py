from serial import SerialException


from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.USBPorts import getComports
from Connection.ISEG import ISEGConnection
from Connection.Threaded import ThreadedISEGConnection


class EBISVBoxLayout(QVBoxLayout):
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
        self.combobox_connection = ComboBox()
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2),
            self.combobox_connection,
            self.button_connection
        )

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

        # Potentials Group Box
        self.potential_group_box = QGroupBox('Potentials')
        self.addWidget(self.potential_group_box)

        self.potential_hbox = QHBoxLayout()
        self.potential_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.potential_group_box.setLayout(self.potential_hbox)

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
        self.spinbox_1 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_1.valueChanged.connect(lambda: self.setVoltage(0, self.spinbox_1.value()))
        self.status_voltage_1 = DisplayLabel(0, unit='V')
        self.status_current_1 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_1 = IndicatorLed(size=indicator_size)
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
        self.spinbox_2 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_2.valueChanged.connect(lambda: self.setVoltage(1, self.spinbox_2.value()))
        self.status_voltage_2 = DisplayLabel(0, unit='V')
        self.status_current_2 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_2 = IndicatorLed(size=indicator_size)
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
        self.spinbox_3 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_3.valueChanged.connect(lambda: self.setVoltage(2, self.spinbox_3.value()))
        self.status_voltage_3 = DisplayLabel(0, unit='V')
        self.status_current_3 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_3 = IndicatorLed(size=indicator_size)
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
        self.spinbox_4 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_4.valueChanged.connect(lambda: self.setVoltage(3, self.spinbox_4.value()))
        self.status_voltage_4 = DisplayLabel(0, unit='V')
        self.status_current_4 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_4 = IndicatorLed(size=indicator_size)
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
        self.spinbox_5 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_5.valueChanged.connect(lambda: self.setVoltage(4, self.spinbox_5.value()))
        self.status_voltage_5 = DisplayLabel(0, unit='V')
        self.status_current_5 = DisplayLabel(0, unit='A', enable_prefix=True)
        self.indicator_5 = IndicatorLed(size=indicator_size)
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
        self.spinbox_voltage_6 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 5), decimals=1, buttons=True)
        self.spinbox_voltage_6.valueChanged.connect(lambda: self.setVoltage(5, self.spinbox_voltage_6.value()))
        self.status_voltage_6 = DisplayLabel(0, unit='V')
        self.indicator_6 = IndicatorLed(size=indicator_size)
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
        self.spinbox_current_6 = DoubleSpinBox(default=0, step_size=0.01, input_range=(0, 5), decimals=1, buttons=True)
        self.spinbox_current_6.valueChanged.connect(lambda: self.setCurrent(5, self.spinbox_current_6.value()))
        self.status_current_6 = DisplayLabel(0, unit='A')
        self.heating_grid.addWidgets(
            self.label_current_6,
            self.spinbox_current_6,
            self.status_current_6,
        )

        # TODO: remove this hardcoded value, but load it from settings and set comport on startup to last set comport
        self.connect('COM4', False)

        self.reset()

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

        if not self.checkConnection(False):
            return

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
                self.indicator_4,
                self.indicator_5,
                self.indicator_6
            ]

            buttons = [
                self.button_1,
                self.button_2,
                self.button_3,
                self.button_4,
                self.button_5,
                self.button_6
            ]

            if len(states) != len(indicators) != len(buttons):
                raise ValueError('High voltage indicators cannot be set, non matching length')

            for indicator, state, button in zip(indicators, states, buttons):
                state = bool(state)
                indicator.setValue(state)
                button.setText('Disable' if state else 'Enable')

        self.threaded_connection.callback(voltageOn, self.threaded_connection.readVoltageOn('0-5'))

        def setVoltage(voltages: list[float]):
            status_voltages = [
                self.status_voltage_1,
                self.status_voltage_2,
                self.status_voltage_3,
                self.status_voltage_4,
                self.status_voltage_5,
                self.status_voltage_6
            ]

            if len(voltages) != len(status_voltages):
                raise ValueError('Measured voltages cannot be set, non matching length')

            for status_voltage, voltage in zip(status_voltages, voltages):
                status_voltage.setValue(voltage)

        self.threaded_connection.callback(setVoltage, self.threaded_connection.measureVoltage('0-5'))

        def setCurrent(currents: list[float]):
            status_currents = [
                self.status_current_1,
                self.status_current_2,
                self.status_current_3,
                self.status_current_4,
                self.status_current_5,
                self.status_current_6
            ]

            if len(currents) != len(status_currents):
                raise ValueError('Measured currents cannot be set, non matching length')

            for status_current, current in zip(status_currents, currents):
                status_current.setValue(current)

        self.threaded_connection.callback(setCurrent, self.threaded_connection.measureCurrent('0-5'))

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
                self.spinbox_4,
                self.spinbox_5,
                self.spinbox_voltage_6
            ]

            if len(voltages) != len(set_voltages):
                raise ValueError('Set voltages cannot be set, non matching length')

            for set_voltage, voltage in zip(set_voltages, voltages):
                set_voltage.setValue(voltage)

        self.threaded_connection.callback(setVoltage, self.threaded_connection.readVoltage('0-5'))

        self.threaded_connection.callback(self.spinbox_current_6.setValue, self.threaded_connection.readCurrent(5))

    def setVoltage(self, channel: int, voltage: float):
        """
        Sets voltage to specified channel

        :param channel: channel to be set
        :param voltage: voltage to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.voltageSet(channel, voltage)

    def setCurrent(self, channel: int, current: float):
        """
        Sets current to specified channel

        :param channel: channel to be set
        :param current: current to be set
        """

        if not self.checkConnection():
            return

        self.threaded_connection.currentSet(channel, current)

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
                'EBIS power supply is not connected, please connect first!'
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
                    'Could not connect to EBIS power supply!',
                    f'<strong>Encountered Error:</strong><br>{error}',
                    expand_details=False
                )

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

        self.indicator_1.setValue(False)
        self.button_1.setText('Enable')
        self.spinbox_1.reset()
        self.status_voltage_1.setValue(0)
        self.status_current_1.setValue(0)

        self.indicator_2.setValue(False)
        self.button_2.setText('Enable')
        self.spinbox_2.reset()
        self.status_voltage_2.setValue(0)
        self.status_current_2.setValue(0)

        self.indicator_3.setValue(False)
        self.button_3.setText('Enable')
        self.spinbox_3.reset()
        self.status_voltage_3.setValue(0)
        self.status_current_3.setValue(0)

        self.indicator_4.setValue(False)
        self.button_4.setText('Enable')
        self.spinbox_4.reset()
        self.status_voltage_4.setValue(0)
        self.status_current_4.setValue(0)

        self.indicator_5.setValue(False)
        self.button_5.setText('Enable')
        self.spinbox_5.reset()
        self.status_voltage_5.setValue(0)
        self.status_current_5.setValue(0)

        self.indicator_6.setValue(False)
        self.button_6.setText('Enable')
        self.spinbox_voltage_6.reset()
        self.spinbox_current_6.reset()
        self.status_voltage_6.setValue(0)
        self.status_current_6.setValue(0)
        
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
