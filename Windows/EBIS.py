from time import monotonic


from serial import SerialException


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceISEGWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, ComboBox, ScientificDoubleSpinBox, ReadingAgeLabel
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox
from Utility.Interlock import PressureInterlock, InterlockLimits, InterlockResult

from Connection.USBPorts import getComports
from Connection.ISEG import ISEGConnection
from Connection.Threaded import ThreadedISEGConnection, ThreadedDummyConnection

from Windows.Pressure import PressureVBoxLayout


class EBISVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.active_message_box = False

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('EBIS', self.reconnect)

        # device wrapper, so the EBIS can be controlled via the CommandServer/Scripts (device name "EBIS")
        self.device_wrapper = DeviceISEGWrapper()
        self.connection: None | ISEGConnection = None
        self.threaded_connection = ThreadedDummyConnection()

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
        self.button_connection.pressed.connect(self.manualConnect)
        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(QIcon('icons/refresh.png'))
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

        # Cathode
        self.label_voltage_1 = QLabel('Cathode')
        self.spinbox_voltage_1 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_voltage_1.editingFinished.connect(lambda: self.setVoltage(0, self.spinbox_voltage_1.value()))
        self.status_voltage_1 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_1 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_voltage_1 = IndicatorLed()
        self.button_enable_1 = QPushButton('Enable')
        self.button_enable_1.pressed.connect(lambda: self.setOutput(0, not self.indicator_voltage_1.value()))
        self.potential_grid.addWidgets(
            self.label_voltage_1,
            self.spinbox_voltage_1,
            self.status_voltage_1,
            self.status_current_1,
            self.indicator_voltage_1,
            self.button_enable_1
        )

        # Drift Tube 1
        self.label_voltage_2 = QLabel('Drift Tube 1')
        self.spinbox_voltage_2 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_voltage_2.editingFinished.connect(lambda: self.setVoltage(1, self.spinbox_voltage_2.value()))
        self.status_voltage_2 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_2 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_voltage_2 = IndicatorLed()
        self.button_enable_2 = QPushButton('Enable')
        self.button_enable_2.pressed.connect(lambda: self.setOutput(1, not self.indicator_voltage_2.value()))
        self.potential_grid.addWidgets(
            self.label_voltage_2,
            self.spinbox_voltage_2,
            self.status_voltage_2,
            self.status_current_2,
            self.indicator_voltage_2,
            self.button_enable_2
        )

        # Drift Tube 2
        self.label_voltage_3 = QLabel('Drift Tube 2')
        self.spinbox_voltage_3 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_voltage_3.editingFinished.connect(lambda: self.setVoltage(2, self.spinbox_voltage_3.value()))
        self.status_voltage_3 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_3 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_voltage_3 = IndicatorLed()
        self.button_enable_3 = QPushButton('Enable')
        self.button_enable_3.pressed.connect(lambda: self.setOutput(2, not self.indicator_voltage_3.value()))
        self.potential_grid.addWidgets(
            self.label_voltage_3,
            self.spinbox_voltage_3,
            self.status_voltage_3,
            self.status_current_3,
            self.indicator_voltage_3,
            self.button_enable_3
        )

        # Drift Tube 3
        self.label_voltage_4 = QLabel('Drift Tube 3')
        self.spinbox_voltage_4 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_voltage_4.editingFinished.connect(lambda: self.setVoltage(3, self.spinbox_voltage_4.value()))
        self.status_voltage_4 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_4 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_voltage_4 = IndicatorLed()
        self.button_enable_4 = QPushButton('Enable')
        self.button_enable_4.pressed.connect(lambda: self.setOutput(3, not self.indicator_voltage_4.value()))
        self.potential_grid.addWidgets(
            self.label_voltage_4,
            self.spinbox_voltage_4,
            self.status_voltage_4,
            self.status_current_4,
            self.indicator_voltage_4,
            self.button_enable_4
        )

        # Repeller
        self.label_voltage_5 = QLabel('Repeller')
        self.spinbox_voltage_5 = DoubleSpinBox(default=0, step_size=0.1, input_range=(0, self.voltage_maximum), decimals=1, buttons=False)
        self.spinbox_voltage_5.editingFinished.connect(lambda: self.setVoltage(4, self.spinbox_voltage_5.value()))
        self.status_voltage_5 = DisplayLabel(value=0, unit='V', target_value=0, deviation=self.voltage_deviation)
        self.status_current_5 = DisplayLabel(value=0, unit='A', target_value=0, deviation=self.current_maximum, enable_prefix=True)
        self.indicator_voltage_5 = IndicatorLed()
        self.button_enable_5 = QPushButton('Enable')
        self.button_enable_5.pressed.connect(lambda: self.setOutput(4, not self.indicator_voltage_5.value()))
        self.potential_grid.addWidgets(
            self.label_voltage_5,
            self.spinbox_voltage_5,
            self.status_voltage_5,
            self.status_current_5,
            self.indicator_voltage_5,
            self.button_enable_5
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

        # TODO: global values for input ranges
        # Cathode
        self.label_limit_1 = QLabel('Cathode')
        self.spinbox_limit_current_1 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 2), decimals=3, buttons=False)
        self.spinbox_limit_current_1.editingFinished.connect(lambda: self.setCurrentLimit(0, self.spinbox_limit_current_1.value()))
        self.indicator_current_limit_1 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_1,
            self.spinbox_limit_current_1,
            self.indicator_current_limit_1
        )

        # Drift Tube 1
        self.label_limit_2 = QLabel('Drift Tube 1')
        self.spinbox_limit_current_2 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 1), decimals=3, buttons=False)
        self.spinbox_limit_current_2.editingFinished.connect(lambda: self.setCurrentLimit(1, self.spinbox_limit_current_2.value()))
        self.indicator_current_limit_2 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_2,
            self.spinbox_limit_current_2,
            self.indicator_current_limit_2
        )

        # Drift Tube 2
        self.label_limit_3 = QLabel('Drift Tube 2')
        self.spinbox_limit_current_3 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 1), decimals=3, buttons=False)
        self.spinbox_limit_current_3.editingFinished.connect(lambda: self.setCurrentLimit(2, self.spinbox_limit_current_3.value()))
        self.indicator_current_limit_3 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_3,
            self.spinbox_limit_current_3,
            self.indicator_current_limit_3
        )

        # Drift Tube 3
        self.label_limit_4 = QLabel('Drift Tube 3')
        self.spinbox_limit_current_4 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 1), decimals=3, buttons=False)
        self.spinbox_limit_current_4.editingFinished.connect(lambda: self.setCurrentLimit(3, self.spinbox_limit_current_4.value()))
        self.indicator_current_limit_4 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_4,
            self.spinbox_limit_current_4,
            self.indicator_current_limit_4
        )

        # Repeller
        self.label_limit_5 = QLabel('Repeller')
        self.spinbox_limit_current_5 = DoubleSpinBox(default=0.002, step_size=0.001, input_range=(0.002, 1), decimals=3, buttons=False)
        self.spinbox_limit_current_5.editingFinished.connect(lambda: self.setCurrentLimit(4, self.spinbox_limit_current_5.value()))
        self.indicator_current_limit_5 = IndicatorLed(on_color=Colors.color_red)
        self.limits_grid.addWidgets(
            self.label_limit_5,
            self.spinbox_limit_current_5,
            self.indicator_current_limit_5
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
        self.indicator_voltage_6 = IndicatorLed()
        self.button_enable_6 = QPushButton('Enable')
        self.button_enable_6.pressed.connect(lambda: self.setOutput(5, not self.indicator_voltage_6.value()))
        self.heating_grid.addWidgets(
            self.label_voltage_6,
            self.spinbox_voltage_6,
            self.status_voltage_6,
            None,
            self.indicator_voltage_6,
            self.button_enable_6
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

        # Pressure interlock
        self.pressure_group_box = QGroupBox('Pressure Interlock')
        self.pressure_group_box.setToolTip(
            'Lowers the cathode heating current if the pressure is too high or if there is no valid pressure reading.\n'
            'A trip is latched until "Re-arm" is pressed.'
        )
        self.addWidget(self.pressure_group_box)

        self.pressure_vbox = QVBoxLayout()
        self.pressure_group_box.setLayout(self.pressure_vbox)

        self.pressure_hbox = QHBoxLayout()
        self.pressure_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.pressure_vbox.addLayout(self.pressure_hbox)

        self.pressure_grid = InsertingGridLayout()
        self.pressure_hbox.addLayout(self.pressure_grid)

        stored_limits, stored_gauge = GlobalConf.getEBISInterlock()
        self.interlock = PressureInterlock(
            InterlockLimits.fromDict(stored_limits),
            check_interval=DefaultParams.update_timer_time / 1000
        )
        limits = self.interlock.limits

        # Interlock state
        self.label_interlock_state = QLabel('State')
        self.indicator_interlock_state = IndicatorLed(on_color=Colors.color_red, off_color=Colors.color_green)
        self.indicator_interlock_state.setToolTip('Green: armed, red: tripped')
        self.status_interlock_state = QLabel(self.interlock.state.text())
        self.button_interlock_reset = QPushButton('Re-arm')
        self.button_interlock_reset.setToolTip('Re-arms the interlock after a trip. It trips again immediately if the cause is still present.')
        self.button_interlock_reset.pressed.connect(self.resetInterlock)
        self.pressure_grid.addWidgets(
            self.label_interlock_state,
            self.indicator_interlock_state,
            (self.status_interlock_state, 2),
            self.button_interlock_reset
        )

        # Pressure gauge selection
        self.label_pressure_gauge = QLabel('Pressure Gauge')
        pressure_gauge_names = list(PressureVBoxLayout.pressure_gauges.keys())
        self.combobox_pressure_gauge = ComboBox(
            entries=pressure_gauge_names,
            default=pressure_gauge_names.index(stored_gauge) if stored_gauge in pressure_gauge_names else 0
        )
        self.combobox_pressure_gauge.setToolTip('Pressure gauge used by the interlock')
        self.combobox_pressure_gauge.currentIndexChanged.connect(self.saveInterlockSettings)
        self.status_interlock_pressure = QLabel('')
        self.status_interlock_pressure.setToolTip('Last pressure of the selected gauge and age of the reading')
        self.pressure_grid.addWidgets(
            self.label_pressure_gauge,
            None,
            self.combobox_pressure_gauge,
            self.status_interlock_pressure
        )

        # Hard pressure limit (lowers current immediately)
        self.label_hard_pmax = QLabel('Hard limit [mbar]')
        self.spinbox_hard_pmax = ScientificDoubleSpinBox(default=limits.hard_pressure, input_range=(1E-11, 1E3))
        self.spinbox_hard_pmax.setToolTip('If the pressure is above this value, the heating current is lowered immediately (e.g. 1E-7)')
        self.spinbox_hard_pmax.editingFinished.connect(self.saveInterlockSettings)
        self.label_hard_current = QLabel('Current [A]')
        self.spinbox_hard_current = DoubleSpinBox(default=limits.hard_current, step_size=0.1, input_range=(0, 3), decimals=2, buttons=False)
        self.spinbox_hard_current.setToolTip('Heating current after a hard trip or if there is no valid pressure reading')
        self.spinbox_hard_current.editingFinished.connect(self.saveInterlockSettings)
        self.pressure_grid.addWidgets(
            self.label_hard_pmax,
            None,
            self.spinbox_hard_pmax,
            self.label_hard_current,
            self.spinbox_hard_current
        )

        # Soft pressure limit (lowers current if median pressure is over limit for too long)
        self.label_soft_pmax = QLabel('Soft limit [mbar]')
        self.spinbox_soft_pmax = ScientificDoubleSpinBox(default=limits.soft_pressure, input_range=(1E-11, 1E3))
        self.spinbox_soft_pmax.setToolTip('If the median pressure over the soft limit duration is above this value, the heating current is lowered')
        self.spinbox_soft_pmax.editingFinished.connect(self.saveInterlockSettings)
        self.label_soft_current = QLabel('Current [A]')
        self.spinbox_soft_current = DoubleSpinBox(default=limits.soft_current, step_size=0.1, input_range=(0, 3), decimals=2, buttons=False)
        self.spinbox_soft_current.setToolTip('Heating current after a soft trip')
        self.spinbox_soft_current.editingFinished.connect(self.saveInterlockSettings)
        self.pressure_grid.addWidgets(
            self.label_soft_pmax,
            None,
            self.spinbox_soft_pmax,
            self.label_soft_current,
            self.spinbox_soft_current
        )

        # Soft pressure limit time
        self.label_soft_pmax_time = QLabel('Soft limit duration [s]')
        self.spinbox_soft_time = DoubleSpinBox(default=limits.soft_time, step_size=1, input_range=(0, 1000), decimals=1, buttons=False)
        self.spinbox_soft_time.setToolTip('Duration over which the median pressure is compared with the soft limit')
        self.spinbox_soft_time.editingFinished.connect(self.saveInterlockSettings)
        self.pressure_grid.addWidgets(
            self.label_soft_pmax_time,
            None,
            self.spinbox_soft_time
        )

        # Watchdog time
        self.label_watchdog_time = QLabel('No reading timeout [s]')
        self.spinbox_watchdog_time = DoubleSpinBox(default=limits.watchdog_time, step_size=1, input_range=(2, 600), decimals=1, buttons=False)
        self.spinbox_watchdog_time.setToolTip(
            'If there is no valid pressure reading for this time (gauge/ADC disconnected, pressure 0 or not updating),\n'
            'the heating current is lowered to the hard limit current'
        )
        self.spinbox_watchdog_time.editingFinished.connect(self.saveInterlockSettings)
        self.pressure_grid.addWidgets(
            self.label_watchdog_time,
            None,
            self.spinbox_watchdog_time
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
            self.spinbox_voltage_1,
            self.spinbox_voltage_2,
            self.spinbox_voltage_3,
            self.spinbox_voltage_4,
            self.spinbox_voltage_5,
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
        self.indicators_voltage = [
            self.indicator_voltage_1,
            self.indicator_voltage_2,
            self.indicator_voltage_3,
            self.indicator_voltage_4,
            self.indicator_voltage_5,
            self.indicator_voltage_6
        ]
        self.buttons_enable = [
            self.button_enable_1,
            self.button_enable_2,
            self.button_enable_3,
            self.button_enable_4,
            self.button_enable_5,
            self.button_enable_6
        ]
        self.spinbox_limit_currents = [
            self.spinbox_limit_current_1,
            self.spinbox_limit_current_2,
            self.spinbox_limit_current_3,
            self.spinbox_limit_current_4,
            self.spinbox_limit_current_5,
            None
        ]
        self.indicator_current_limits = [
            self.indicator_current_limit_1,
            self.indicator_current_limit_2,
            self.indicator_current_limit_3,
            self.indicator_current_limit_4,
            self.indicator_current_limit_5,
            None
        ]

        self.reset()
        self.updateInterlockDisplay()

        last_connection = GlobalConf.getConnection('ebis')
        if last_connection:
            self.connect(last_connection, False)

    @property
    def threaded_connection(self) -> ThreadedDummyConnection | ThreadedISEGConnection:
        """Threaded connection of the device wrapper (shared with the CommandServer)"""
        return self.device_wrapper.threaded_connection

    @threaded_connection.setter
    def threaded_connection(self, threaded_connection: ThreadedDummyConnection | ThreadedISEGConnection):
        self.device_wrapper.threaded_connection = threaded_connection

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""

        self.status_reading_age.setAge(self.threaded_connection.secondsSinceLastResult(), self.indicator_connection.value())

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
            if len(states) != len(self.indicators_voltage) != len(self.buttons_enable) != len(self.status_voltages):
                GlobalConf.logger.error(f'High voltage indicators cannot be set, non matching length: expected len = {len(self.indicators_voltage)}, got len = {len(states)}')
                return

            for indicator, status_voltage, state, button in zip(self.indicators_voltage, self.status_voltages, states, self.buttons_enable):
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

            if any([0 if isinstance(current, float) else 1 for current in currents]):
                GlobalConf.logger.error(f'Measured currents cannot be set, types of currents are: {[type(current) for current in currents]}, expected only <float>s')
                return

            for status_current, indicator_limit, spinbox_limit_current, current in zip(self.status_currents, self.indicator_current_limits, self.spinbox_limit_currents, currents):
                status_current.setValue(current)
                if indicator_limit is not None and spinbox_limit_current is not None:
                    indicator_limit.setValue(current >= spinbox_limit_current.value() / 1000)

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

        def readCurrentLimit(currents: list[float]):
            if len(currents) != len(self.spinbox_limit_currents):
                GlobalConf.logger.error(f'Set currents cannot be set, non matching length: expected len = {len(self.spinbox_limit_currents)}, got len = {len(currents)}')
                return

            for (spinbox_limit_current, current) in zip(self.spinbox_limit_currents, currents):
                if spinbox_limit_current is not None:
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

        # heating current is limited while the pressure interlock is tripped
        trip_current = self.interlock.tripCurrent()
        if channel == 5 and trip_current is not None and current > trip_current:
            GlobalConf.logger.warning(f'EBIS: Heating current {current} A refused, pressure interlock is tripped (max. {trip_current} A)')
            self.spinbox_current_6.setValue(trip_current)
            if not self.active_message_box:
                self.active_message_box = True
                showMessageBox(
                    None,
                    QMessageBox.Icon.Warning,
                    'Pressure interlock tripped!',
                    f'The heating current is limited to {trip_current} A, because the pressure interlock is tripped:<br>{self.interlock.trip_message}',
                    'Re-arm the interlock first (EBIS panel: Pressure Interlock: Re-arm).'
                )
                self.active_message_box = False
            current = trip_current

        self.status_currents[channel].setTargetValue(current)
        phys_channel = self.channel_dict[channel]
        self.threaded_connection.currentSet(phys_channel, current)

    def saveInterlockSettings(self):
        """Takes the interlock limits from the input fields and stores them persistently"""

        self.interlock.limits = InterlockLimits(
            hard_pressure=self.spinbox_hard_pmax.value(),
            hard_current=self.spinbox_hard_current.value(),
            soft_pressure=self.spinbox_soft_pmax.value(),
            soft_time=self.spinbox_soft_time.value(),
            soft_current=self.spinbox_soft_current.value(),
            watchdog_time=self.spinbox_watchdog_time.value()
        )
        GlobalConf.updateEBISInterlock(
            self.interlock.limits.toDict(),
            self.combobox_pressure_gauge.getValue(text=True)
        )

    def resetInterlock(self):
        """Re-arms the interlock after a trip"""

        if self.interlock.isTripped():
            GlobalConf.logger.info(f'EBIS: Pressure interlock re-armed by user (was: {self.interlock.state.text()}: {self.interlock.trip_message})')
        self.interlock.reset()
        if not self.indicator_connection.value():
            self.interlock.disable()
        self.updateInterlockDisplay()

    def checkInterlock(self, pressure: float | None, reading_age: float | None) -> InterlockResult | None:
        """
        Checks the pressure interlock and lowers the heating current if needed. Should be called periodically.

        :param pressure: last pressure of the selected gauge in mbar (0 or None if not available)
        :param reading_age: seconds since the last successful pressure reading (None if there was none)
        :returns: result of the check (None if the EBIS is not connected)
        """

        if not self.indicator_connection.value():
            self.interlock.disable()
            self.updateInterlockDisplay(pressure, reading_age)
            return None

        result = self.interlock.check(pressure, reading_age, monotonic())

        if result.target_current is not None:
            # also compare with the measured current, so changes from scripts/CommandServer are caught as well
            set_current = self.spinbox_current_6.value()
            measured_current = self.status_current_6.value
            if set_current > result.target_current or measured_current > result.target_current + self.current_deviation:
                GlobalConf.logger.warning(f'EBIS: Pressure interlock lowers heating current to {result.target_current} A ({result.message})')
                self.spinbox_current_6.setValue(result.target_current)
                self.status_current_6.setTargetValue(result.target_current)
                self.threaded_connection.currentSet(self.channel_dict[5], result.target_current)

        if result.new_trip:
            GlobalConf.logger.error(f'EBIS: Pressure interlock {result.state.text()}: {result.message}')

        self.updateInterlockDisplay(pressure, reading_age)
        return result

    def updateInterlockDisplay(self, pressure: float | None = None, reading_age: float | None = None):
        """
        Updates the interlock state in the GUI

        :param pressure: last pressure of the selected gauge in mbar
        :param reading_age: seconds since the last successful pressure reading
        """

        state = self.interlock.state
        self.indicator_interlock_state.setValue(state.isTripped())
        text = state.text()
        if state.isTripped():
            text = f'{text}, max. {self.interlock.tripCurrent()} A'
        self.status_interlock_state.setText(text)
        self.status_interlock_state.setToolTip(self.interlock.trip_message)
        self.status_interlock_state.setStyleSheet(f'color: {Colors.color_red};' if state.isTripped() else '')

        if PressureInterlock.isValidPressure(pressure):
            age_text = 'no reading' if reading_age is None else f'{reading_age:.1f} s ago'
            self.status_interlock_pressure.setText(f'{pressure:.2E} mbar ({age_text})')
        else:
            self.status_interlock_pressure.setText('No valid pressure')

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

    def setRampSpeed(self, speed: float):
        """
        Sets ramp speed

        :param speed: ramp speed in %/min
        """

        if not self.checkConnection():
            return

        self.threaded_connection.configureRampVoltageSet(speed)

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
                self.threaded_connection = ThreadedISEGConnection(
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

    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection to the device was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('EBIS: Connection lost')
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

        for indicator in self.indicators_voltage:
            indicator.setValue(False)

        for button in self.buttons_enable:
            button.setText('Enable')

        for spinbox in self.spinbox_voltages:
            spinbox.reset()

        for status in self.status_voltages:
            status.setValue(0)
            status.setTargetValue(0)

        for status in self.status_currents:
            status.setValue(0)
            status.setTargetValue(0)

        for indicator in self.indicator_current_limits:
            if indicator is not None:
                indicator.setValue(False)

        for spinbox in self.spinbox_limit_currents:
            if spinbox is not None:
                spinbox.reset()

        self.spinbox_current_6.reset()

        self.spinbox_advanced_settings_ramp.reset()

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
        # remember the port if connected or if the connection was lost (not if the user disconnected)
        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port or self.combobox_connection.getValue(text=True)
        self.auto_reconnect.stop()
        if self.connection is not None:
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