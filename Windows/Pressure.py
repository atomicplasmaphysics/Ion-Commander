from serial import SerialException


from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors

from Utility.Layouts import PressureWidget, IndicatorLed, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.USBPorts import getComports
from Connection.Thyracont import thyracontVoltageToPressure
from Connection.TPG300 import tpg300VoltageToPressure, TPG300Type
from Connection.MixedPressure import MixedPressureConnection
from Connection.Threaded import ThreadedMixedPressureConnection, ThreadedDummyConnection


class PressureVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updatePressure)
        self.update_timer.setInterval(GlobalConf.update_timer_time)
        self.update_timer.start()

        self.connection: None | MixedPressureConnection = None
        self.threaded_connection: ThreadedDummyConnection | ThreadedMixedPressureConnection = ThreadedDummyConnection()

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
        self.indicator_connection = IndicatorLed(off_color=Colors.cooperate_error)
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

        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(QIcon('icons/refresh.png'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.connection_hbox_selection.addWidget(self.button_connection_refresh)

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

        # Pre-vacuum
        self.group_box_prevac = QGroupBox('Pre-Vacuum')
        self.pressure_widget_prevac = PressureWidget(input_range=(3, -3))
        self.layout_prevac = QVBoxLayout()
        self.layout_prevac.addWidget(self.pressure_widget_prevac)
        self.group_box_prevac.setLayout(self.layout_prevac)
        self.addWidget(self.group_box_prevac)

        # grouped items
        self.pressure_widgets = [
            self.pressure_widget_pitbul,
            self.pressure_widget_lsd,
            self.pressure_widget_prevac,
            None
        ]

        self.reset()

        last_connection = GlobalConf.getConnection('pressure')
        if last_connection:
            self.connect(last_connection, False)

    def updatePressure(self):
        """Updates the pressure variables"""

        if self.threaded_connection.isDummy():
            return

        def setPressures(pressures: list[float]):
            if len(pressures) != 4:
                GlobalConf.logger.error(f'Pressures cannot be set, non matching length: expected len = {len(self.pressure_widgets)}, got len = {len(pressures)}')
                return
            for pressure_widget, pressure in zip(self.pressure_widgets, pressures):
                if pressure_widget is None:
                    continue
                pressure_widget.setPressure(pressure)

        self.threaded_connection.callback(setPressures, self.threaded_connection.getPressureAll())

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
            self.connection = MixedPressureConnection(comport, [
                thyracontVoltageToPressure,
                thyracontVoltageToPressure,
                lambda voltage: tpg300VoltageToPressure(voltage, TPG300Type.Pirani),
                lambda voltage: 0
            ])
            try:
                self.connection.open()
                self.threaded_connection = ThreadedMixedPressureConnection(self.connection)
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
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

                GlobalConf.logger.info(f'Connection error! Could not connect to Lucid Control ADC on port "{comport}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to Lucid Control ADC on port "{comport}"!',
                        f'<strong>Encountered Error:</strong><br>{error}',
                        expand_details=False
                    )
        else:
            self.combobox_connection.setEnabled(True)
            self.button_connection_refresh.setEnabled(True)
            self.button_connection.setText('Connect')

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

        self.pressure_widget_pitbul.setPressure(0)
        self.pressure_widget_lsd.setPressure(0)
        self.pressure_widget_prevac.setPressure(0)

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
        last_connection = ''
        if self.connection is not None:
            last_connection = self.combobox_connection.getValue(text=True)
            self.connection.close()

        GlobalConf.updateConnections(pressure=last_connection)
