from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox


from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, PolarityButton, SpinBox, ComboBox


class PSUVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: make indicator sizes global somewhere
        indicator_size = QSize(20, 20)

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
        self.indicator_connection = IndicatorLed(clickable=True, size=indicator_size, off_color=Colors.cooperate_error)
        self.status_connection = QLabel('Not connected')
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2)
        )

        # TODO: do we need high voltage?
        # High Voltage
        self.label_high_voltage = QLabel('High Voltage')
        self.indicator_high_voltage = IndicatorLed(clickable=True, size=indicator_size)
        self.status_high_voltage = QLabel('Disabled')
        self.button_high_voltage = QPushButton('Enable')
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
        self.button_polarity_1 = PolarityButton()
        self.spinbox_1 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_1 = DisplayLabel(0.3, unit='V')
        self.status_current_1 = DisplayLabel(0.2, unit='A', enable_prefix=True)
        self.indicator_1 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_enable_1 = QPushButton('Enable')
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
        self.button_polarity_2 = PolarityButton()
        self.spinbox_2 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_2 = DisplayLabel(0.9, unit='V')
        self.status_current_2 = DisplayLabel(0.8, unit='A', enable_prefix=True)
        self.indicator_2 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_enable_2 = QPushButton('Enable')
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
        self.button_polarity_3 = PolarityButton()
        self.spinbox_3 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_3 = DisplayLabel(0.8, unit='V')
        self.status_current_3 = DisplayLabel(0.5, unit='A', enable_prefix=True)
        self.indicator_3 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_enable_3 = QPushButton('Enable')
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
        self.button_polarity_4 = PolarityButton()
        self.spinbox_4 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_4 = DisplayLabel(0.4, unit='V')
        self.status_current_4 = DisplayLabel(0.6, unit='A', enable_prefix=True)
        self.indicator_4 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_enable_4 = QPushButton('Enable')
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
        self.label_limit_1 = self.label_1
        self.spinbox_limit_voltage_1 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_current_1 = DoubleSpinBox(step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.indicator_limit_1 = IndicatorLed(clickable=True, size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_1,
            self.spinbox_limit_voltage_1,
            self.spinbox_limit_current_1,
            self.indicator_limit_1
        )

        # Anode
        self.label_limit_2 = self.label_2
        self.spinbox_limit_voltage_2 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_current_2 = DoubleSpinBox(step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.indicator_limit_2 = IndicatorLed(clickable=True, size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_2,
            self.spinbox_limit_voltage_2,
            self.spinbox_limit_current_2,
            self.indicator_limit_2
        )

        # Cathode LSD
        self.label_limit_3 = self.label_3
        self.spinbox_limit_voltage_3 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_current_3 = DoubleSpinBox(step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.indicator_limit_3 = IndicatorLed(clickable=True, size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_3,
            self.spinbox_limit_voltage_3,
            self.spinbox_limit_current_3,
            self.indicator_limit_3
        )

        # Focus LSD
        self.label_limit_4 = self.label_4
        self.spinbox_limit_voltage_4 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.spinbox_limit_current_4 = DoubleSpinBox(step_size=0.001, input_range=(0, 1), decimals=3, buttons=True)
        self.indicator_limit_4 = IndicatorLed(clickable=True, size=indicator_size, on_color=Colors.cooperate_error)
        self.limits_grid.addWidgets(
            self.label_limit_4,
            self.spinbox_limit_voltage_4,
            self.spinbox_limit_current_4,
            self.indicator_limit_4
        )

        # Ramp Group Box
        self.ramp_group_box = QGroupBox('Ramp')
        self.addWidget(self.ramp_group_box)

        self.ramp_hbox = QHBoxLayout()
        self.ramp_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.ramp_group_box.setLayout(self.ramp_hbox)

        self.ramp_grid = InsertingGridLayout()
        self.ramp_hbox.addLayout(self.ramp_grid)

        # Speed
        # TODO: get limits, unit and number of decimals right
        self.label_ramp_speed = QLabel('Speed [%/min]')
        self.spinbox_ramp_speed = DoubleSpinBox(step_size=0.001, input_range=(0, 100), decimals=3, buttons=True)
        self.ramp_grid.addWidgets(
            self.label_ramp_speed,
            self.spinbox_ramp_speed
        )

        # Time
        self.label_ramp_time = QLabel('Time [min]')
        self.spinbox_ramp_time = SpinBox(step_size=1, input_range=(0, 600), buttons=True)
        self.ramp_grid.addWidgets(
            self.label_ramp_time,
            self.spinbox_ramp_time
        )

        # Final Value
        self.label_ramp_final = QLabel('Voltage [V]')
        self.spinbox_ramp_voltage = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.ramp_grid.addWidgets(
            self.label_ramp_final,
            self.spinbox_ramp_voltage
        )

        # Channel
        self.label_ramp_channel = QLabel('Channel')
        self.combobox_ramp_channel = ComboBox(entries=[self.label_1.text(), self.label_2.text(), self.label_3.text(), self.label_4.text()])
        self.ramp_grid.addWidgets(
            self.label_ramp_channel,
            self.combobox_ramp_channel
        )

        # Start
        self.button_ramp = QPushButton('Start')
        self.status_ramp = QLabel('Remaining time:')
        self.status_remaining_ramp = DisplayLabel(value=400, target_value=0, deviation=600, unit='min')
        self.ramp_grid.addWidgets(
            self.button_ramp,
            self.status_ramp,
            self.status_remaining_ramp
        )
