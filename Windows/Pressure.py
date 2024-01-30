from serial import SerialException


from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, QSize, QTimer


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors

from Utility.Layouts import PressureWidget, IndicatorLed, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.USBPorts import getComports
from Connection.Thyracont import ThyracontConnection
from Connection.Threaded import ThreadedThyracontConnection, ThreadedDummyConnection


class PressureVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updatePressure)
        # TODO: do not use hardcoded interval time
        self.update_timer.setInterval(1000)
        self.update_timer.start()

        # TODO: make indicator sizes global somewhere
        indicator_size = QSize(20, 20)

        self.connection: None | ThyracontConnection = None
        self.threaded_connection: ThreadedDummyConnection | ThreadedThyracontConnection = ThreadedDummyConnection()

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
        self.indicator_connection = IndicatorLed(size=indicator_size, off_color=Colors.cooperate_error)
        self.connection_hbox.addWidget(self.indicator_connection)
        self.status_connection = QLabel('Not connected')
        self.connection_hbox.addWidget(self.status_connection)

        self.connection_hbox_selection = QHBoxLayout()
        self.connection_hbox_selection.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox_selection)

        self.combobox_connection = ComboBox()
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

        # TODO: remove this hardcoded value, but load it from settings and set comport on startup to last set comport
        #self.connect('COM3', False)

        self.reset()

    def updatePressure(self):
        """Updates the pressure variables"""

        if not self.indicator_connection.value():
            return

        self.threaded_connection.callback(self.pressure_widget_pitbul.setPressure, self.threaded_connection.getTemperature(0))
        self.threaded_connection.callback(self.pressure_widget_lsd.setPressure, self.threaded_connection.getTemperature(1))

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

        self.threaded_connection.close()
        self.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        self.connection = ThyracontConnection(comport)
        try:
            self.connection.open()
            self.threaded_connection = ThreadedThyracontConnection(self.connection)
            self.indicator_connection.setValue(True)
            self.status_connection.setText('Connected')

        except (SerialException, ConnectionError) as error:
            try:
                self.connection.close()
            except ConnectionError:
                pass
            self.connection = None
            self.reset()

            GlobalConf.logger.info(f'Connection error! Could not connect to Lucid Control ADC, because of: {error}')

            if messagebox:
                showMessageBox(
                    None,
                    QMessageBox.Icon.Critical,
                    'Connection error!',
                    'Could not connect to Lucid Control ADC!',
                    f'<strong>Encountered Error:</strong><br>{error}',
                    expand_details=False
                )

    def reset(self):
        """Resets everything to default"""

        self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.pressure_widget_pitbul.setPressure(0)
        self.pressure_widget_lsd.setPressure(0)

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
        if self.connection is not None:
            self.connection.close()
