from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton


from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox


class EBISVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        indicator_size = QSize(20, 20)

        # Connection Grid
        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.addLayout(self.connection_hbox)
        self.connection_grid = InsertingGridLayout()
        self.connection_hbox.addLayout(self.connection_grid)

        # TODO: remove clickable from all <IndicatorLed> instances

        # Connection
        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(clickable=True, size=indicator_size, off_color=Colors.cooperate_error)
        self.status_connection = QLabel('Not connected')
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            self.status_connection
        )

        # High Voltage
        self.label_high_voltage = QLabel('High Voltage')
        self.indicator_high_voltage = IndicatorLed(clickable=True, size=indicator_size)
        self.status_high_voltage = QLabel('Disbled')
        self.button_high_voltage = QPushButton('Enable')
        self.connection_grid.addWidgets(
            self.label_high_voltage,
            self.indicator_high_voltage,
            self.status_high_voltage,
            self.button_high_voltage
        )

        # Control Grid
        self.control_hbox = QHBoxLayout()
        self.control_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.addLayout(self.control_hbox)
        self.control_grid = InsertingGridLayout()
        self.control_hbox.addLayout(self.control_grid)

        # Cathode Potential
        self.label_cathode = QLabel('Cathode')
        self.spinbox_cathode = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_cathode = QLabel('0V')
        self.status_current_cathode = QLabel('0A')
        self.indicator_cathode = IndicatorLed(clickable=True, size=indicator_size)
        self.button_cathode = QPushButton('Enable')
        self.control_grid.addWidgets(
            self.label_cathode,
            self.spinbox_cathode,
            self.status_voltage_cathode,
            self.status_current_cathode,
            self.indicator_cathode,
            self.button_cathode
        )

        # Drift Tube 1
        self.label_drift_tube_1 = QLabel('Drift Tube 1')
        self.spinbox_drift_tube_1 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_drift_tube_1 = QLabel('0V')
        self.status_current_drift_tube_1 = QLabel('0A')
        self.indicator_drift_tube_1 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_drift_tube_1 = QPushButton('Enable')
        self.control_grid.addWidgets(
            self.label_drift_tube_1,
            self.spinbox_drift_tube_1,
            self.status_voltage_drift_tube_1,
            self.status_current_drift_tube_1,
            self.indicator_drift_tube_1,
            self.button_drift_tube_1
        )

        # Drift Tube 2
        self.label_drift_tube_2 = QLabel('Drift Tube 2')
        self.spinbox_drift_tube_2 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_drift_tube_2 = QLabel('0V')
        self.status_current_drift_tube_2 = QLabel('0A')
        self.indicator_drift_tube_2 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_drift_tube_2 = QPushButton('Enable')
        self.control_grid.addWidgets(
            self.label_drift_tube_2,
            self.spinbox_drift_tube_2,
            self.status_voltage_drift_tube_2,
            self.status_current_drift_tube_2,
            self.indicator_drift_tube_2,
            self.button_drift_tube_2
        )

        # Drift Tube 3
        self.label_drift_tube_3 = QLabel('Drift Tube 3')
        self.spinbox_drift_tube_3 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_drift_tube_3 = QLabel('0V')
        self.status_current_drift_tube_3 = QLabel('0A')
        self.indicator_drift_tube_3 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_drift_tube_3 = QPushButton('Enable')
        self.control_grid.addWidgets(
            self.label_drift_tube_3,
            self.spinbox_drift_tube_3,
            self.status_voltage_drift_tube_3,
            self.status_current_drift_tube_3,
            self.indicator_drift_tube_3,
            self.button_drift_tube_3
        )

        # Repeller
        self.label_repeller = QLabel('Repeller')
        self.spinbox_repeller = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_repeller = QLabel('0V')
        self.status_current_repeller = QLabel('0A')
        self.indicator_repeller = IndicatorLed(clickable=True, size=indicator_size)
        self.button_repeller = QPushButton('Enable')
        self.control_grid.addWidgets(
            self.label_repeller,
            self.spinbox_repeller,
            self.status_voltage_repeller,
            self.status_current_repeller,
            self.indicator_repeller,
            self.button_repeller
        )

        # Cathode Heating Voltage
        self.label_cathode_voltage = QLabel('Cathode Heating Voltage')
        self.spinbox_cathode_voltage = DoubleSpinBox(step_size=0.1, input_range=(0, 5), decimals=1, buttons=True)
        self.status_cathode_voltage = QLabel('0V')
        self.indicator_cathode_heating = IndicatorLed(clickable=True, size=indicator_size)
        self.button_cathode_heating = QPushButton('Enable')
        self.control_grid.addWidgets(
            self.label_cathode_voltage,
            self.spinbox_cathode_voltage,
            self.status_cathode_voltage,
            None,
            self.indicator_cathode_heating,
            self.button_cathode_heating
        )

        # Cathode Heating Current
        self.label_cathode_current = QLabel('Cathode Heating Current')
        self.spinbox_cathode_current = DoubleSpinBox(step_size=0.01, input_range=(0, 5), decimals=1, buttons=True)
        self.status_cathode_current = QLabel('0A')
        self.control_grid.addWidgets(
            self.label_cathode_current,
            self.spinbox_cathode_current,
            self.status_cathode_current,
        )
