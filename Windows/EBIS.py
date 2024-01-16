from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox


from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, ComboBox

from Connection.USBPorts import getComports
from Connection.ISEG import ISEGConnection


class EBISVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: make indicator sizes global somewhere
        indicator_size = QSize(20, 20)

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
        self.indicator_connection = IndicatorLed(clickable=True, size=indicator_size, off_color=Colors.cooperate_error)
        self.status_connection = QLabel('Not connected')
        self.combobox_connection = ComboBox(entries=self.comport_ports, tooltips=self.comport_description)
        self.button_connection = QPushButton('Connect')
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2),
            self.combobox_connection,
            self.button_connection
        )

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
        self.spinbox_1 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_1 = DisplayLabel(0.5, unit='V')
        self.status_current_1 = DisplayLabel(0.1, unit='A', enable_prefix=True)
        self.indicator_1 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_1 = QPushButton('Enable')
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
        self.spinbox_2 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_2 = DisplayLabel(0.6, unit='V')
        self.status_current_2 = DisplayLabel(0.4, unit='A', enable_prefix=True)
        self.indicator_2 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_2 = QPushButton('Enable')
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
        self.spinbox_3 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_3 = DisplayLabel(0, unit='V')
        self.status_current_3 = DisplayLabel(1, unit='A', enable_prefix=True)
        self.indicator_3 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_3 = QPushButton('Enable')
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
        self.spinbox_4 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_4 = DisplayLabel(0.9, unit='V')
        self.status_current_4 = DisplayLabel(0.8, unit='A', enable_prefix=True)
        self.indicator_4 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_4 = QPushButton('Enable')
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
        self.spinbox_5 = DoubleSpinBox(step_size=0.1, input_range=(0, 10000), decimals=1, buttons=True)
        self.status_voltage_5 = DisplayLabel(0.7, unit='V')
        self.status_current_5 = DisplayLabel(0.4, unit='A', enable_prefix=True)
        self.indicator_5 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_5 = QPushButton('Enable')
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
        self.label_6_voltage = QLabel('Heating Voltage')
        self.spinbox_6_voltage = DoubleSpinBox(step_size=0.1, input_range=(0, 5), decimals=1, buttons=True)
        self.status_6_voltage = DisplayLabel(0.3, unit='V')
        self.indicator_6 = IndicatorLed(clickable=True, size=indicator_size)
        self.button_6 = QPushButton('Enable')
        self.heating_grid.addWidgets(
            self.label_6_voltage,
            self.spinbox_6_voltage,
            self.status_6_voltage,
            None,
            self.indicator_6,
            self.button_6
        )

        # Cathode Heating Current
        self.label_6_current = QLabel('Heating Current')
        self.spinbox_6_current = DoubleSpinBox(step_size=0.01, input_range=(0, 5), decimals=1, buttons=True)
        self.status_6_current = DisplayLabel(0.9, unit='A')
        self.heating_grid.addWidgets(
            self.label_6_current,
            self.spinbox_6_current,
            self.status_6_current,
        )

    def closeEvent(self):
        """Must be called when application is closed"""
        pass


