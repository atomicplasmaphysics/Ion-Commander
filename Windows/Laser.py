from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton


from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, ErrorTable, DoubleSpinBox, ComboBox


class LaserVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        indicator_size = QSize(20, 20)

        # Indicator Grid
        self.indicator_hbox = QHBoxLayout()
        self.indicator_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.addLayout(self.indicator_hbox)
        self.indicator_grid = InsertingGridLayout()
        self.indicator_hbox.addLayout(self.indicator_grid)

        # TODO: remove clickable from all <IndicatorLed> instances

        # Connection
        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(clickable=True, size=indicator_size, off_color=Colors.cooperate_error)
        self.status_connection = QLabel('Not connected')
        self.indicator_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            self.status_connection
        )

        # Key-switch
        self.label_key_switch = QLabel('Key-Switch')
        self.indicator_key_switch = IndicatorLed(clickable=True, size=indicator_size)
        self.status_key_switch = QLabel('Key off')
        self.indicator_grid.addWidgets(
            self.label_key_switch,
            self.indicator_key_switch,
            self.status_key_switch
        )

        # Shutter
        self.label_shutter = QLabel('Shutter')
        self.indicator_shutter = IndicatorLed(clickable=True, size=indicator_size)
        self.status_shutter = QLabel('Closed')
        self.button_shutter = QPushButton('Open')
        self.indicator_grid.addWidgets(
            self.label_shutter,
            self.indicator_shutter,
            self.status_shutter,
            self.button_shutter
        )

        # Pulsing
        self.label_pulsing = QLabel('Pulsing')
        self.indicator_pulsing = IndicatorLed(clickable=True, size=indicator_size)
        self.status_pulsing = QLabel('Off')
        self.button_pulsing = QPushButton('On')
        self.indicator_grid.addWidgets(
            self.label_pulsing,
            self.indicator_pulsing,
            self.status_pulsing,
            self.button_pulsing
        )

        # System status
        self.label_system_status = QLabel('System Status')
        self.indicator_system_status = IndicatorLed(clickable=True, size=indicator_size)
        self.status_system_status = QLabel('Standby')
        self.button_system_status = QPushButton('Start')
        self.indicator_grid.addWidgets(
            self.label_system_status,
            self.indicator_system_status,
            self.status_system_status,
            self.button_system_status
        )

        # Chiller Temperature
        self.label_chiller_temperature = QLabel('Chiller Temperature')
        self.indicator_chiller_temperature = IndicatorLed(clickable=True, size=indicator_size)
        self.status_chiller_temperature = QLabel('28 °C')
        self.spinbox_chiller_temperature = DoubleSpinBox(step_size=0.1, input_range=(18, 35), decimals=1, buttons=True)
        self.indicator_grid.addWidgets(
            self.label_chiller_temperature,
            self.indicator_chiller_temperature,
            self.status_chiller_temperature,
            self.spinbox_chiller_temperature
        )

        # Baseplate Temperature
        self.label_baseplate_temperature = QLabel('Baseplate Temperature')
        self.indicator_baseplate_temperature = IndicatorLed(clickable=True, size=indicator_size)
        self.status_baseplate_temperature = QLabel('27.7 °C')
        self.indicator_grid.addWidgets(
            self.label_baseplate_temperature,
            self.indicator_baseplate_temperature,
            self.status_baseplate_temperature
        )

        # Chiller Flow
        self.label_chiller_flow = QLabel('Chiller Flow')
        self.indicator_chiller_flow = IndicatorLed(clickable=True, size=indicator_size)
        self.status_chiller_flow = QLabel('25 lpm')
        self.indicator_grid.addWidgets(
            self.label_chiller_flow,
            self.indicator_chiller_flow,
            self.status_chiller_flow
        )

        # System faults
        self.label_system_faults = QLabel('System Faults')
        self.indicator_system_faults = IndicatorLed(clickable=True, size=indicator_size)
        self.status_system_faults = QLabel('No faults')
        self.button_system_faults = QPushButton('Clear')
        self.button_system_faults.clicked.connect(lambda: self.table_system_faults.resetTable())
        self.indicator_grid.addWidgets(
            self.label_system_faults,
            self.indicator_system_faults,
            self.status_system_faults,
            self.button_system_faults
        )

        # System faults table
        self.table_system_faults = ErrorTable()
        self.addWidget(self.table_system_faults)

        for i in range(5):
            self.table_system_faults.insertError(i, f'Type {i}', f'Pretty long and unusefull description of error from state {i}')

        # Laser Settings Grid
        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.addLayout(self.settings_hbox)
        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        # Amplifier Settings
        self.combobox_settings_amplifier = ComboBox()
        self.settings_grid.addWidgets(
            QLabel('Amplifier'),
            self.combobox_settings_amplifier
        )

        # Output Settings
        self.combobox_settings_output = ComboBox()
        self.status_settings_output = QLabel('Actual: 99.93 kHz')
        self.settings_grid.addWidgets(
            QLabel('Output'),
            self.combobox_settings_output,
            self.status_settings_output
        )

        # RF Level Settings
        self.spinbox_settings_rflvel = DoubleSpinBox(step_size=0.1, input_range=(0, 100), decimals=1, buttons=True)
        self.settings_grid.addWidgets(
            QLabel('RF Level'),
            self.spinbox_settings_rflvel
        )

        # Pulse Width Settings
        self.spinbox_settings_pulsewidth = DoubleSpinBox(step_size=0.1, input_range=(276, 10000), decimals=1, buttons=True)
        self.settings_grid.addWidgets(
            QLabel('Pulse Width'),
            self.spinbox_settings_pulsewidth
        )
