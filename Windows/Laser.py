from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceMonacoWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, ErrorTable, DoubleSpinBox, SpinBox, ComboBox, DisplayLabel
from Utility.Dialogs import IPDialog, showMessageBox
from Utility.Functions import getPrefix, getSignificantDigits, getIntIfInt

from Connection.Monaco import MonacoConnection
from Connection.Threaded import ThreadedMonacoConnection, ThreadedDummyConnection, ThreadedConnection


class LaserVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Local variables
        self.ip = DefaultParams.laser_ip
        self.port = DefaultParams.laser_port

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.active_message_box = False
        self.combobox_message_box_warning = True
        self.update_frequency_output = False

        self.device_wrapper = DeviceMonacoWrapper()
        self.connection: None | MonacoConnection = None
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()

        self.chiller_temperature_low = DefaultParams.laser_chiller_temperature_low
        self.chiller_temperature_high = DefaultParams.laser_chiller_temperature_high
        self.chiller_flow_low = DefaultParams.laser_chiller_flow_low
        self.chiller_flow_high = DefaultParams.laser_chiller_flow_high
        self.baseplate_temperature_off = DefaultParams.laser_baseplate_temperature_off
        self.baseplate_temperature_on = DefaultParams.laser_baseplate_temperature_on

        self.energy_total = 40000
        self.amplifiers: list[tuple[tuple[float, int], float]] = [
            ((200, 5), 40),
            ((250, 4), 40),
            ((330, 3), 40),
            ((500, 2), 40),
            ((1000, 1), 40),
            ((1000, 5), 8),
            ((1000, 10), 4),
            ((1000, 15), 2.7),
            ((1000, 20), 2),
            ((2000, 1), 20),
            ((4000, 1), 10),
            ((10000, 1), 4),
            ((50000, 1), 0.8)
        ]
        self.amplifier_repetition_rate = 0

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection and Status')
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
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.button_connection_settings = QPushButton()
        self.button_connection_settings.setIcon(QIcon('icons/preferences.png'))
        self.button_connection_settings.pressed.connect(self.connectionPreferences)
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            self.status_connection,
            self.button_connection,
            self.button_connection_settings
        )

        # Key-switch
        self.label_key_switch = QLabel('Key-Switch')
        self.indicator_key_switch = IndicatorLed()
        self.status_key_switch = QLabel('Key off')
        self.connection_grid.addWidgets(
            self.label_key_switch,
            self.indicator_key_switch,
            self.status_key_switch
        )

        # Shutter
        self.label_shutter = QLabel('Shutter')
        self.indicator_shutter = IndicatorLed()
        self.status_shutter = QLabel('Closed')
        self.button_shutter = QPushButton('Open')
        self.button_shutter.pressed.connect(lambda: self.setShutter(not self.indicator_shutter.value()))
        self.connection_grid.addWidgets(
            self.label_shutter,
            self.indicator_shutter,
            self.status_shutter,
            self.button_shutter
        )

        # Pulsing
        self.label_pulsing = QLabel('Pulsing')
        self.indicator_pulsing = IndicatorLed()
        self.status_pulsing = QLabel('Off')
        self.button_pulsing = QPushButton('On')
        self.button_pulsing.pressed.connect(lambda: self.setPulsing(not self.indicator_pulsing.value()))
        self.connection_grid.addWidgets(
            self.label_pulsing,
            self.indicator_pulsing,
            self.status_pulsing,
            self.button_pulsing
        )

        # System status
        self.label_system_status = QLabel('System Status')
        self.state_system_status = 0
        self.indicator_system_status = IndicatorLed()
        self.status_system_status = QLabel('Standby')
        self.button_system_status = QPushButton('Start')
        self.button_system_status.pressed.connect(lambda: self.setSystem(not self.indicator_system_status.value()))
        self.connection_grid.addWidgets(
            self.label_system_status,
            self.indicator_system_status,
            (self.status_system_status, 2),
            self.button_system_status
        )

        # Chiller Group Box
        self.chiller_group_box = QGroupBox('Chiller')
        self.addWidget(self.chiller_group_box)

        self.chiller_hbox = QHBoxLayout()
        self.chiller_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.chiller_group_box.setLayout(self.chiller_hbox)

        self.chiller_grid = InsertingGridLayout()
        self.chiller_hbox.addLayout(self.chiller_grid)

        # Chiller Temperature
        self.label_chiller_temperature = QLabel('Chiller Temp.')
        self.indicator_chiller_temperature = IndicatorLed()
        self.status_chiller_temperature = DisplayLabel(value=0, target_value=0, deviation=0.5, unit='°C', alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.chiller_grid.addWidgets(
            self.label_chiller_temperature,
            self.indicator_chiller_temperature,
            self.status_chiller_temperature
        )

        # Baseplate Temperature
        self.label_baseplate_temperature = QLabel('Baseplate Temp.')
        self.status_baseplate_temperature = DisplayLabel(value=0, target_value=0, deviation=0.5, unit='°C', alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.chiller_grid.addWidgets(
            self.label_baseplate_temperature,
            None,
            self.status_baseplate_temperature
        )

        # Chiller Flow
        self.label_chiller_flow = QLabel('Chiller Flow')
        self.indicator_chiller_flow = IndicatorLed()
        self.status_chiller_flow = DisplayLabel(value=0, target_value=0, deviation=0.3, unit='lpm', decimals=1, alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.button_clear_chiller_service = QPushButton('Serviced')
        self.button_clear_chiller_service.pressed.connect(self.setChillerServiced)
        self.chiller_grid.addWidgets(
            self.label_chiller_flow,
            self.indicator_chiller_flow,
            self.status_chiller_flow,
            self.button_clear_chiller_service,
        )

        # Faults Group Box
        self.faults_group_box = QGroupBox('Faults')
        self.addWidget(self.faults_group_box)

        self.faults_vbox = QVBoxLayout()
        self.faults_group_box.setLayout(self.faults_vbox)

        self.faults_hbox = QHBoxLayout()
        self.faults_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.faults_vbox.addLayout(self.faults_hbox)

        self.faults_grid = InsertingGridLayout()
        self.faults_hbox.addLayout(self.faults_grid)

        # System faults
        self.button_system_faults = QPushButton('Clear')
        self.button_system_faults.pressed.connect(self.clearFaults)
        self.indicator_system_faults = IndicatorLed(on_color=Colors.color_red, off_color=Colors.color_green)
        self.status_system_faults = QLabel('No faults')
        self.faults_grid.addWidgets(
            self.button_system_faults,
            self.indicator_system_faults,
            self.status_system_faults
        )

        # System faults table
        # TODO: table does not really update correctly - might be a fundamental Laser issue
        self.table_system_faults = ErrorTable()
        self.faults_vbox.addWidget(self.table_system_faults)

        # Settings Group Box
        self.settings_group_box = QGroupBox('Settings')
        self.addWidget(self.settings_group_box)

        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.settings_group_box.setLayout(self.settings_hbox)

        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        # Amplifier Settings
        self.combobox_settings_amplifier = ComboBox()
        self.combobox_settings_amplifier.currentIndexChanged.connect(self.setAmplifier)
        self.settings_grid.addWidgets(
            QLabel('Amplifier'),
            self.combobox_settings_amplifier
        )

        # Output Settings
        self.combobox_settings_output = ComboBox()
        self.state_mrr_setting = 0
        self.state_rrd_setting = 0
        self.state_sb_setting = 0
        self.combobox_settings_output.currentIndexChanged.connect(self.setOutputFrequency)
        # TODO: deviation and target value to this on update
        self.status_settings_output = DisplayLabel(value=0, target_value=0, deviation=0, unit='Hz', enable_prefix=True, alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.settings_grid.addWidgets(
            QLabel('Output'),
            self.combobox_settings_output,
            self.status_settings_output
        )

        # RF Level Settings
        self.spinbox_settings_rflevel = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, 100), decimals=1, buttons=False)
        self.spinbox_settings_rflevel.editingFinished.connect(self.setRFLevel)
        self.status_settings_rflevel = DisplayLabel(value=0, target_value=0, deviation=0.1, decimals=1, unit='%', enable_prefix=False, alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.settings_grid.addWidgets(
            QLabel('RF Level [%]'),
            self.spinbox_settings_rflevel,
            self.status_settings_rflevel
        )

        # Pulse Width Settings
        self.spinbox_settings_pulsewidth = SpinBox(default=276, step_size=1, input_range=(276, 10000), buttons=False)
        self.spinbox_settings_pulsewidth.editingFinished.connect(self.setPulseLength)
        self.status_settings_pulsewidth = DisplayLabel(value=0, target_value=0, deviation=1, decimals=0, unit='fs', enable_prefix=False, alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.settings_grid.addWidgets(
            QLabel('Pulse Width [fs]'),
            self.spinbox_settings_pulsewidth,
            self.status_settings_pulsewidth
        )

        self.reset()

        last_connection = GlobalConf.getConnection('laser')
        if all([True if elem > 0 else False for elem in last_connection]):
            self.ip = (
                last_connection[0],
                last_connection[1],
                last_connection[2],
                last_connection[3]
            )
            self.port = last_connection[4]
            self.connect(self.ip, self.port, False)

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

        if not self.checkConnection(False):
            return

        def keyOn(state: int):
            if not isinstance(state, int) or state == -1:
                GlobalConf.logger.error(f'State for Key must be <int> and not -1, got {type(state)} with value "{state}"')
                return

            state = bool(state)
            self.indicator_key_switch.setValue(state)
            self.status_key_switch.setText('Key on' if state else 'Key off')

        self.device_wrapper.threaded_connection.callback(
            keyOn,
            self.device_wrapper.threaded_connection.kGet()
        )

        def shutterOn(state: int):
            if not isinstance(state, int) or state == -1:
                GlobalConf.logger.error(f'State for Shutter must be <int> and not -1, got {type(state)} with value "{state}"')
                return

            state = bool(state)
            self.indicator_shutter.setValue(state)
            self.status_shutter.setText('Open' if state else 'Closed')
            self.button_shutter.setText('Close' if state else 'Open')

        self.device_wrapper.threaded_connection.callback(
            shutterOn,
            self.device_wrapper.threaded_connection.sGet()
        )

        def pulsingOn(state: int):
            if not isinstance(state, int) or state == -1:
                GlobalConf.logger.error(f'State for Pulsing must be <int> and not -1, got {type(state)} with value "{state}"')
                return

            state = bool(state)
            self.indicator_pulsing.setValue(state)
            self.status_pulsing.setText('On' if state else 'Off')
            self.button_pulsing.setText('Off' if state else 'On')

        self.device_wrapper.threaded_connection.callback(
            pulsingOn,
            self.device_wrapper.threaded_connection.pcGet()
        )

        def systemStatus(l_info: tuple[str, bool, int]):
            if not isinstance(l_info, tuple) or len(l_info) != 3:
                GlobalConf.logger.error(f'State of System must be <tuple> with length 3, got {type(l_info)} with value "{l_info}')
                return

            self.indicator_system_status.setValue(l_info[1])
            self.status_system_status.setText(l_info[0])
            self.button_system_status.setText('Stop' if l_info[1] else 'Start')
            self.status_baseplate_temperature.setTargetValue(self.baseplate_temperature_on if l_info[1] else self.baseplate_temperature_off)
            self.state_system_status = l_info[2]

        self.device_wrapper.threaded_connection.callback(
            systemStatus,
            self.device_wrapper.threaded_connection.lGetInfo()
        )

        def chillerTemperature(temperature: float):
            if (not isinstance(temperature, float) and not isinstance(temperature, int)) or temperature == -1:
                GlobalConf.logger.error(f'Chiller temperature must be <float> and not -1, got {type(temperature)} with value "{temperature}"')
                return

            self.status_chiller_temperature.setValue(temperature)
            self.indicator_chiller_temperature.setValue(self.chiller_temperature_low <= temperature <= self.chiller_temperature_high)

        self.device_wrapper.threaded_connection.callback(
            chillerTemperature,
            self.device_wrapper.threaded_connection.chtGet()
        )

        def chillerSetPoint(temperature: float):
            if (not isinstance(temperature, float) and not isinstance(temperature, int)) or temperature == -1:
                GlobalConf.logger.error(f'Chiller temperature must be <float> and not -1, got {type(temperature)} with value "{temperature}"')
                return

            self.status_chiller_temperature.setTargetValue(temperature)

        self.device_wrapper.threaded_connection.callback(
            chillerSetPoint,
            self.device_wrapper.threaded_connection.chstGet()
        )

        def baseplateTemperature(temperature: float):
            if (not isinstance(temperature, float) and not isinstance(temperature, int)) or temperature == -1:
                GlobalConf.logger.error(f'Baseplate temperature must be <float> and not -1, got {type(temperature)} with value "{temperature}"')
                return

            self.status_baseplate_temperature.setValue(temperature)

        self.device_wrapper.threaded_connection.callback(
            baseplateTemperature,
            self.device_wrapper.threaded_connection.btGet()
        )

        def chillerFlow(flow: float):
            if (not isinstance(flow, float) and not isinstance(flow, int)) or flow == -1:
                GlobalConf.logger.error(f'Chiller flow must be <float> and not -1, got {type(flow)} with value "{flow}"')
                return

            self.status_chiller_flow.setValue(flow)
            self.status_chiller_flow.setTargetValue((self.chiller_flow_high + self.chiller_flow_low) / 2)
            self.indicator_chiller_flow.setValue(self.chiller_flow_low <= flow <= self.chiller_flow_high)

        self.device_wrapper.threaded_connection.callback(
            chillerFlow,
            self.device_wrapper.threaded_connection.chfGet()
        )

        def faultsTable(faults: dict[int, tuple[str, str]]):
            if not isinstance(faults, dict):
                GlobalConf.logger.error(f'Faults must be <dict>, got {type(faults)}')
                return

            error_list = self.table_system_faults.getErrorList()

            for fault, fault_info in faults.items():
                if not isinstance(fault, int) and not isinstance(fault_info, tuple) and len(fault_info) == 2:
                    GlobalConf.logger.error(f'Fault key must be <int>, got {type(fault)}, Fault Info must be <tuple> of length 2, got {type(fault_info)} with value "{fault_info}"')
                    return

                if fault not in error_list:
                    self.table_system_faults.insertError(fault, fault_info[0], fault_info[1])

            if not self.table_system_faults.getErrorList():
                self.indicator_system_faults.setValue(False)
                self.status_system_faults.setText('No faults')
            else:
                self.indicator_system_faults.setValue(True)
                self.status_system_faults.setText('Faults occurred')

        self.device_wrapper.threaded_connection.callback(
            faultsTable,
            self.device_wrapper.threaded_connection.wGetInfo()
        )

        def settings(params: tuple[float, int, int, int]):
            # params:
            #   MRR: amplifier repetition rate in kHz
            #   PW: pulse width in femtoseconds
            #   RRD: repetition rate divisor
            #   SB: number of seeder bursts

            if not isinstance(params, tuple) or len(params) != 4:
                GlobalConf.logger.error(f'Settings parameter must be <tuple> with length 4, got {type(params)} with value "{params}"')
                return

            self.setComboboxAmplifier(params[0], params[3])
            if params[0] != self.amplifier_repetition_rate:
                self.amplifier_repetition_rate = params[0]
                self.fillComboboxOutput(params[2])
            else:
                self.setComboboxOutput(params[2])
            self.status_settings_pulsewidth.setValue(int(params[1]))

        self.device_wrapper.threaded_connection.callback(
            settings,
            self.device_wrapper.threaded_connection.setGet()
        )

        def outputFrequency(frequency: float):
            if (not isinstance(frequency, float) and not isinstance(frequency, int)) or frequency == -1:
                GlobalConf.logger.error(f'Output frequency must be <float> and not -1, got {type(frequency)} with value "{frequency}"')
                return

            self.status_settings_output.setValue(frequency)

        self.device_wrapper.threaded_connection.callback(
            outputFrequency,
            self.device_wrapper.threaded_connection.crrGet()
        )

        def rfLevel(level: float):
            if (not isinstance(level, float) and not isinstance(level, int)) or level == -1:
                GlobalConf.logger.error(f'RF Level must be <float> and not -1, got {type(level)} with value "{level}"')
                return

            self.status_settings_rflevel.setValue(level)

        self.device_wrapper.threaded_connection.callback(
            rfLevel,
            self.device_wrapper.threaded_connection.rlGet()
        )

    def updateAllValues(self):
        """Updates all values"""

        if not self.checkConnection(False):
            return

        def setChillerTemperatureLow(temperature: float):
            if (not isinstance(temperature, float) and not isinstance(temperature, int)) or temperature == -1:
                GlobalConf.logger.error(f'Chiller temperature low must be <float> and not -1, got {type(temperature)} with value "{temperature}"')
                return

            self.chiller_temperature_low = temperature

        self.device_wrapper.threaded_connection.callback(
            setChillerTemperatureLow,
            self.device_wrapper.threaded_connection.chtlGet()
        )

        def setChillerTemperatureHigh(temperature: float):
            if (not isinstance(temperature, float) and not isinstance(temperature, int)) or temperature == -1:
                GlobalConf.logger.error(f'Chiller temperature high must be <float> and not -1, got {type(temperature)} with value "{temperature}"')
                return

            self.chiller_temperature_high = temperature

        self.device_wrapper.threaded_connection.callback(
            setChillerTemperatureHigh,
            self.device_wrapper.threaded_connection.chthGet()
        )

        def setChillerFlowLow(flow: float):
            if (not isinstance(flow, float) and not isinstance(flow, int)) or flow == -1:
                GlobalConf.logger.error(f'Chiller flow low must be <float> and not -1, got {type(flow)} with value "{flow}"')
                return

            self.chiller_flow_low = flow

        self.device_wrapper.threaded_connection.callback(
            setChillerFlowLow,
            self.device_wrapper.threaded_connection.chflGet()
        )

        def setChillerFlowHigh(flow: float):
            if (not isinstance(flow, float) and not isinstance(flow, int)) or flow == -1:
                GlobalConf.logger.error(f'Chiller flow high must be <float> and not -1, got {type(flow)} with value "{flow}"')
                return

            self.chiller_flow_high = flow

        self.device_wrapper.threaded_connection.callback(
            setChillerFlowHigh,
            self.device_wrapper.threaded_connection.chfhGet()
        )

        def rfLevel(level: float):
            if (not isinstance(level, float) and not isinstance(level, int)) or level == -1:
                GlobalConf.logger.error(f'RF Level must be <float> and not -1, got {type(level)} with value "{level}"')
                return

            self.status_settings_rflevel.setValue(level)
            self.status_settings_rflevel.setTargetValue(level)
            self.spinbox_settings_rflevel.setValue(level)

        self.device_wrapper.threaded_connection.callback(
            rfLevel,
            self.device_wrapper.threaded_connection.rlGet()
        )

        def settings(params: tuple[float, int, int, int]):
            # params:
            #   MRR: amplifier repetition rate in kHz
            #   PW: pulse width in femtoseconds
            #   RRD: repetition rate divisor
            #   SB: number of seeder bursts

            if not isinstance(params, tuple) or len(params) != 4:
                GlobalConf.logger.error(f'Settings parameter must be <tuple> with length 4, got {type(params)} with value "{params}"')
                return

            self.setComboboxAmplifier(params[0], params[3])
            if params[0] != self.amplifier_repetition_rate:
                self.amplifier_repetition_rate = params[0]
                self.fillComboboxOutput(params[2])
            else:
                self.setComboboxOutput(params[2])
            self.status_settings_pulsewidth.setValue(int(params[1]))
            self.status_settings_pulsewidth.setTargetValue(int(params[1]))
            self.spinbox_settings_pulsewidth.setValue(int(params[1]))

            self.state_mrr_setting = params[0]
            self.state_rdd_setting = params[2]
            self.state_sb_setting = params[3]

        self.device_wrapper.threaded_connection.callback(
            settings,
            self.device_wrapper.threaded_connection.setGet()
        )

        self.updateLoop()

    def setShutter(self, state: bool):
        """
        Sets the shutter

        :param state: new state of shutter
        """

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        if state:
            if self.active_message_box:
                return
            self.active_message_box = True
            _, result = showMessageBox(
                None,
                QMessageBox.Icon.Information,
                'Open shutter',
                'Are you shure you want to open the shutter?',
                standard_buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            self.active_message_box = False
            if result == QMessageBox.StandardButton.Cancel:
                return

        self.device_wrapper.threaded_connection.sSet(state)

    def setPulsing(self, state: bool):
        """
        Sets the pulsing

        :param state: new state of pulsing
        """

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        self.device_wrapper.threaded_connection.pcSet(state)

    def setSystem(self, start: bool):
        """
        Start/stop the laser

        :param start:
            True: start the laser
            False: stop the laser
        """

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        self.device_wrapper.threaded_connection.lSet(start)

    def setChillerServiced(self):
        """Sets the chiller state such that it was serviced now"""

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        if self.active_message_box:
            return

        self.active_message_box = True
        _, result = showMessageBox(
            None,
            QMessageBox.Icon.Information,
            'Reset Chiller Coolant Timer',
            'The laser keeps track of how much time has passed since the chiller coolant was replaced. This allows the laser to set a warning code to prompt you to change the coolant. You should press this button after changing the chiller coolant (or the chiller itself xD) to reset the timer in the laser.',
            'Have you changed the chiller coolant?',
            standard_buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self.active_message_box = False
        if result == QMessageBox.StandardButton.No:
            return

        self.device_wrapper.threaded_connection.chservicedSet()

    def clearFaults(self):
        """Clears all faults"""

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        self.device_wrapper.threaded_connection.fackSet()

    def setAmplifier(self):
        """Sets amplifier"""

        if not self.checkConnection(self.combobox_message_box_warning) or not self.checkKeySwitch(self.combobox_message_box_warning):
            return

        item_data = self.combobox_settings_amplifier.itemData(self.combobox_settings_amplifier.currentIndex())
        if not isinstance(item_data, tuple) and len(item_data) != 3:
            raise ValueError(f'Expected userData of Amplifier combobox to be a <tuple> of size 3, got {type(item_data)}')

        self.device_wrapper.threaded_connection.setSet(mrr=item_data[0], pulses=item_data[1])

    def setOutputFrequency(self):
        """Sets output frequency"""

        if not self.update_frequency_output:
            return

        if not self.checkConnection(self.combobox_message_box_warning) or not self.checkKeySwitch(self.combobox_message_box_warning):
            return

        item_data = self.combobox_settings_output.itemData(self.combobox_settings_output.currentIndex())
        if not isinstance(item_data, int):
            raise ValueError(f'Expected userData of Output combobox to be a <int>, got {type(item_data)}')

        self.device_wrapper.threaded_connection.setSet(rrd=item_data)

    def setRFLevel(self):
        """Sets RF level"""

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        self.device_wrapper.threaded_connection.rlSet(self.spinbox_settings_rflevel.value())
        self.status_settings_rflevel.setTargetValue(self.spinbox_settings_rflevel.value())

    def setPulseLength(self):
        """Sets pulse length"""

        if not self.checkConnection() or not self.checkKeySwitch():
            return

        self.device_wrapper.threaded_connection.setSet(pw=self.spinbox_settings_pulsewidth.value())
        self.status_settings_pulsewidth.setTargetValue(self.spinbox_settings_pulsewidth.value())

    def fillComboboxAmplifierItem(self, mrr: float, sb: int, energy: float = 0, select: bool = False):
        """
        Fills one item in combobox amplifier

        :param mrr: amplifier repetition rate in kHz
        :param sb: number of seeder bursts
        :param energy: energy per seeder burst
        :param select: selects newly added item
        """

        mrr_modified, mrr_prefix = getPrefix(mrr * 1000)
        mrr_modified = getSignificantDigits(mrr_modified, digits=3)
        mrr_modified = getIntIfInt(mrr_modified)

        if not energy:
            energy = self.energy_total / mrr / sb
        energy = getSignificantDigits(energy, digits=2)
        energy = getIntIfInt(energy)

        text = f'{mrr_modified} {mrr_prefix}Hz {sb}x{energy} μJ'
        item_data = (mrr, sb, energy)
        self.combobox_settings_amplifier.addItem(text, userData=item_data)

        if select:
            self.combobox_settings_amplifier.setCurrentIndex(self.combobox_settings_amplifier.count() - 1)

        current_width = self.combobox_settings_amplifier.view().width()
        new_width = self.combobox_settings_amplifier.fontMetrics().boundingRect(text).width() + 30
        if new_width > current_width:
            self.combobox_settings_amplifier.view().setFixedWidth(new_width)

    def fillComboboxAmplifier(self, index: int = -1, clear: bool = True):
        """
        Fills items in combobox amplifier

        :param index: index to be set
        :param clear: clears the combobox first
        """

        self.combobox_message_box_warning = False

        if clear:
            self.combobox_settings_amplifier.clear()
            self.combobox_settings_amplifier.view().setFixedWidth(0)

        for (mrr, sb), energy in self.amplifiers:
            self.fillComboboxAmplifierItem(mrr, sb, energy)

        if 0 <= index < self.combobox_settings_amplifier.count():
            self.combobox_settings_amplifier.setCurrentIndex(index)

        self.combobox_message_box_warning = True

    def setComboboxAmplifier(self, mrr: float, sb: int):
        """
        Switches to the given item in the combobox or adds new item and selects it

        :param mrr: amplifier repetition rate in kHz
        :param sb: number of seeder bursts
        """

        self.combobox_message_box_warning = False

        for i in range(self.combobox_settings_amplifier.count()):
            item_data = self.combobox_settings_amplifier.itemData(i)
            if not isinstance(item_data, tuple) and len(item_data) != 3:
                raise ValueError(f'Expected userData of Amplifier combobox to be a <tuple> of size 3, got {type(item_data)}')
            if sb == item_data[1] and abs(mrr - item_data[0]) < item_data[0] * 0.01:
                self.combobox_settings_amplifier.setCurrentIndex(i)
                return

        self.fillComboboxAmplifierItem(mrr, sb, select=True)

        self.combobox_message_box_warning = True

    def fillComboboxOutputItem(self, mrr: float, rrd: int, select: bool = False):
        """
        Fills one item in combobox output

        :param mrr: amplifier repetition rate in kHz
        :param rrd: repetition rate divisor
        :param select: selects newly added item
        """

        self.update_frequency_output = False

        frequency = mrr / rrd

        frequency_modified, frequency_prefix = getPrefix(frequency * 1000)
        frequency_modified = getSignificantDigits(frequency_modified, digits=3)
        frequency_modified = getIntIfInt(frequency_modified)
        text = f'{frequency_modified} {frequency_prefix}Hz'

        self.combobox_settings_output.addItem(text, userData=rrd)

        self.update_frequency_output = True

        if select:
            self.combobox_settings_output.setCurrentIndex(self.combobox_settings_output.count() - 1)

    def fillComboboxOutput(self, rrd: int = -1, clear: bool = True):
        """
        Fills items in combobox output

        :param rrd: repetition rate divisor to be selected
        :param clear: clears the combobox first
        """

        self.combobox_message_box_warning = False

        if clear:
            self.combobox_settings_output.clear()

        item_data = self.combobox_settings_amplifier.itemData(self.combobox_settings_amplifier.currentIndex())
        if not isinstance(item_data, tuple) and len(item_data) != 3:
            raise ValueError(f'Expected userData of Amplifier combobox to be a <tuple> of size 3, got {type(item_data)}')

        rrds = 100
        for i in range(1, rrds + 1):
            self.fillComboboxOutputItem(item_data[0], i)

        if 0 < rrd < rrds:
            self.combobox_settings_output.setCurrentIndex(rrd - 1)

        self.combobox_message_box_warning = True

    def setComboboxOutput(self, rrd: int):
        """
        Switches to the given output frequency in the combobox or adds new item and selects it

        :param rrd: repetition rate divisor
        """

        self.combobox_message_box_warning = False

        for i in range(self.combobox_settings_output.count()):
            item_data = self.combobox_settings_output.itemData(i)
            if not isinstance(item_data, int):
                raise ValueError(f'Item data must be an <int>, got <{tuple(item_data)}>')
            if item_data == rrd:
                self.combobox_settings_output.setCurrentIndex(rrd - 1)
                return

        item_data = self.combobox_settings_amplifier.itemData(self.combobox_settings_amplifier.currentIndex())
        if not isinstance(item_data, tuple) and len(item_data) != 3:
            raise ValueError(f'Expected userData of Amplifier combobox to be a <tuple> of size 3, got {type(item_data)}')

        self.fillComboboxOutputItem(item_data[0], rrd, select=True)

        self.combobox_message_box_warning = True

    def connectionPreferences(self):
        """Open dialog to get user input on IP address and port number of laser"""

        ip_dialog = IPDialog(ip=self.ip, port=self.port, info='Monaco Laser')
        ip_dialog.exec()
        self.ip = ip_dialog.getIP()
        self.port = ip_dialog.getPort()

    def checkKeySwitch(self, messagebox: bool = True) -> bool:
        """
        Checks if the key position is set to on

        :param messagebox: enable popup of infobox
        """

        if self.indicator_key_switch.value():
            return True

        if messagebox and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'Key Switch warning!',
                'Monaco Laser key is turned off, please turn key on first!'
            )
            self.active_message_box = False

        return False

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
                'Monaco Laser is not connected, please connect first!'
            )
            self.active_message_box = False

        return False

    def connect(self, ip: tuple[int, int, int, int] = None, port: int = None, messagebox: bool = True):
        """
        Connects to laser with given IP address and port number. If those are not provided, the current values are used.

        :param ip: IP address to connect to
        :param port: port number to connect to
        :param messagebox: show messagebox if failed
        """

        if ip is None or port is None:
            ip = self.ip
            port = self.port

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if connect:
            self.connection = MonacoConnection(
                host='.'.join(str(ip_i) for ip_i in ip),
                port=port,
                timeout=1
            )
            try:
                self.connection.open()
                self.device_wrapper.threaded_connection = ThreadedConnection(self.connection)
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
                self.button_connection_settings.setEnabled(False)
                self.button_connection.setText('Disconnect')

                # clear faults to initialize fault table
                self.device_wrapper.threaded_connection.fackSet()

            # TODO: probably add some more socket connection errors here
            except (ConnectionError, TimeoutError, ConnectionAbortedError, UnicodeDecodeError, OSError) as error:
                try:
                    self.connection.close()
                except (ConnectionError, TimeoutError, ConnectionAbortedError, UnicodeDecodeError, OSError):
                    pass
                self.connection = None
                self.reset()

                GlobalConf.logger.info(
                    f'Connection error! Could not connect to Monaco Laser with IP "{ip}" and port "{port}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to Monaco Laser with IP "{ip}" and port "{port}"!',
                        f'<strong>Encountered Error:</strong><br>{error}',
                        expand_details=False
                    )
        else:
            self.button_connection_settings.setEnabled(True)
            self.button_connection.setText('Connect')

        self.updateAllValues()

    def unconnect(self):
        """Disconnect from any port"""

        self.device_wrapper.threaded_connection.close()
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        self.reset()

    def reset(self):
        """Resets everything to default"""

        self.device_wrapper.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')
        self.button_connection_settings.setEnabled(True)

        self.indicator_key_switch.setValue(False)
        self.status_key_switch.setText('Key off')

        self.indicator_shutter.setValue(False)
        self.status_shutter.setText('Closed')
        self.button_shutter.setText('Open')

        self.indicator_pulsing.setValue(False)
        self.status_pulsing.setText('Off')
        self.button_pulsing.setText('On')

        self.indicator_system_status.setValue(False)
        self.status_system_status.setText('Standby')
        self.button_system_status.setText('Start')

        self.indicator_chiller_temperature.setValue(False)
        self.status_chiller_temperature.setValue(0)
        self.status_chiller_temperature.setTargetValue(0)

        self.status_baseplate_temperature.setValue(0)
        self.status_baseplate_temperature.setTargetValue(0)

        self.indicator_chiller_flow.setValue(False)
        self.status_chiller_flow.setValue(0)
        self.status_chiller_flow.setTargetValue(0)

        self.indicator_system_faults.setValue(False)
        self.status_system_faults.setText('No faults')
        self.table_system_faults.resetTable()

        self.fillComboboxAmplifier(4)
        self.fillComboboxOutput()
        self.setComboboxOutput(10)
        self.status_settings_output.setValue(0)
        self.status_settings_output.setTargetValue(0)
        self.status_settings_output.setDeviation(0)
        self.spinbox_settings_rflevel.reset()
        self.status_settings_rflevel.setValue(0)
        self.status_settings_rflevel.setTargetValue(0)
        self.status_settings_rflevel.setDeviation(0.1)
        self.spinbox_settings_pulsewidth.reset()
        self.status_settings_pulsewidth.setValue(0)
        self.status_settings_pulsewidth.setTargetValue(0)
        self.status_settings_pulsewidth.setDeviation(1)

    def closeEvent(self):
        """Must be called when application is closed"""

        self.device_wrapper.threaded_connection.close()
        last_connection = [-1, -1, -1, -1, -1]
        if self.connection is not None:
            last_connection[0] = self.ip[0]
            last_connection[1] = self.ip[1]
            last_connection[2] = self.ip[2]
            last_connection[3] = self.ip[3]
            last_connection[4] = self.port
            self.connection.close()

        GlobalConf.updateConnections(laser=last_connection)

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if not self.checkConnection(False):
            return

        db.insertLaser(
            self.indicator_shutter.value(),
            self.indicator_pulsing.value(),
            self.state_system_status,
            self.status_chiller_temperature.value,
            self.status_chiller_temperature.target_value,
            self.status_baseplate_temperature.value,
            self.status_chiller_flow.value,
            self.state_mrr_setting,
            int(self.status_settings_pulsewidth.value),
            self.state_rrd_setting,
            self.state_sb_setting,
            self.status_settings_rflevel.value,
        )
