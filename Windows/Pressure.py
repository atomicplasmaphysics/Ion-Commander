from serial import SerialException


from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QSize


from Config.StylesConf import Colors

from Utility.Layouts import PressureWidget, IndicatorLed, ComboBox

from Connection.USBPorts import getComports
from Connection.Thyracont import ThyracontConnection
from Connection.Threaded import ThreadedThyracontConnection


class PressureVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: make indicator sizes global somewhere
        indicator_size = QSize(20, 20)

        self.comports = getComports()
        self.comport_ports = [port for port, description, hardware_id in self.comports]
        self.comport_description = [f'{port}: {description} [{hardware_id}]' for port, description, hardware_id in self.comports]

        self.connection: None | ThyracontConnection = None
        self.threaded_connection: None | ThreadedThyracontConnection = None

        # Connection
        self.connection_group_box = QGroupBox('Connection')
        self.addWidget(self.connection_group_box)

        self.connection_vbox = QVBoxLayout()
        self.connection_group_box.setLayout(self.connection_vbox)

        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox)

        self.label_connection = QLabel('Connection')
        self.connection_hbox.addWidget(self.label_connection)
        self.indicator_connection = IndicatorLed(clickable=True, size=indicator_size, off_color=Colors.cooperate_error)
        self.connection_hbox.addWidget(self.indicator_connection)
        self.status_connection = QLabel('Not connected')
        self.connection_hbox.addWidget(self.status_connection)

        self.connection_hbox_selection = QHBoxLayout()
        self.connection_hbox_selection.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox_selection)

        self.combobox_connection = ComboBox(entries=self.comport_ports, tooltips=self.comport_description)
        self.connection_hbox_selection.addWidget(self.combobox_connection)
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.connection_hbox_selection.addWidget(self.button_connection)

        # PITBUL
        self.group_box_pitbul = QGroupBox('PITBUL')
        self.pressure_widget_pitbul = PressureWidget()
        self.layout_pitbul = QVBoxLayout()
        self.layout_pitbul.addWidget(self.pressure_widget_pitbul)
        self.group_box_pitbul.setLayout(self.layout_pitbul)
        self.addWidget(self.group_box_pitbul)

        # LSD
        self.group_box_lsd = QGroupBox('LSD')
        self.pressure_widget_lsd = PressureWidget()
        self.layout_lsd = QVBoxLayout()
        self.layout_lsd.addWidget(self.pressure_widget_lsd)
        self.group_box_lsd.setLayout(self.layout_lsd)
        self.addWidget(self.group_box_lsd)

        # TODO: remove this but add all connection ports in settings and retrieve them at start
        self.connect()

    def connect(self, comport: str = ''):
        """
        Connect to given comport. If no comport is given, the current selected comport will be connected to

        :param comport: comport to connect to
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

        self.connection = ThyracontConnection(comport)
        try:
            self.connection.open()
            self.threaded_connection = ThreadedThyracontConnection(self.connection)
            self.indicator_connection.setValue(True)
            self.status_connection.setText('Connected')

        except SerialException:
            self.connection.close()
            self.connection = None
            self.indicator_connection.setValue(False)
            self.status_connection.setText('Not connected')

    def closeEvent(self):
        """Must be called when application is closed"""
        if self.threaded_connection is not None:
            self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()
