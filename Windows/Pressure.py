from serial import SerialException


from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceMixedPressureWrapper

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
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.device_wrapper = DeviceMixedPressureWrapper()
        self.connection: None | MixedPressureConnection = None

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
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
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
        self.group_box_1 = QGroupBox('PITBUL')
        self.pressure_widget_1 = PressureWidget()
        self.layout_1 = QVBoxLayout()
        self.layout_1.addWidget(self.pressure_widget_1)
        self.group_box_1.setLayout(self.layout_1)
        self.addWidget(self.group_box_1)

        # LSD
        self.group_box_2 = QGroupBox('LSD')
        self.pressure_widget_2 = PressureWidget()
        self.layout_2 = QVBoxLayout()
        self.layout_2.addWidget(self.pressure_widget_2)
        self.group_box_2.setLayout(self.layout_2)
        self.addWidget(self.group_box_2)

        # ESD
        self.group_box_3 = QGroupBox('ESD')
        self.pressure_widget_3 = PressureWidget()
        self.layout_3 = QVBoxLayout()
        self.layout_3.addWidget(self.pressure_widget_3)
        self.group_box_3.setLayout(self.layout_3)
        self.addWidget(self.group_box_3)

        # Pre-vacuum
        self.group_box_4 = QGroupBox('Pre-Vacuum')
        self.pressure_widget_4 = PressureWidget(input_range=(1E3, 5E-3))
        self.layout_4 = QVBoxLayout()
        self.layout_4.addWidget(self.pressure_widget_4)
        self.group_box_4.setLayout(self.layout_4)
        self.addWidget(self.group_box_4)

        # grouped items
        self.pressure_widgets = [
            self.pressure_widget_1,
            self.pressure_widget_2,
            self.pressure_widget_3,
            self.pressure_widget_4
        ]

        self.reset()

        last_connection = GlobalConf.getConnection('pressure')
        if last_connection:
            self.connect(last_connection, False)

    def updatePressure(self):
        """Updates the pressure variables"""

        if self.device_wrapper.threaded_connection.isDummy():
            return

        def setPressures(pressures: list[float]):
            if len(pressures) != 4:
                GlobalConf.logger.error(f'Pressures cannot be set, non matching length: expected len = {len(self.pressure_widgets)}, got len = {len(pressures)}')
                return
            for pressure_widget, pressure in zip(self.pressure_widgets, pressures):
                if pressure_widget is None:
                    continue
                pressure_widget.setPressure(pressure)

        self.device_wrapper.threaded_connection.callback(setPressures, self.device_wrapper.threaded_connection.getPressureAll())

    def connect(self, comport: str = '', messagebox: bool = True):
        """
        Connect to given comport. If no comport is given, the current selected comport will be connected to

        :param comport: comport to connect to
        :param messagebox: show messagebox if failed
        """

        if not comport:
            comport = self.combobox_connection.getValue(text=True)
        self.setComport(comport)

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if connect:
            self.connection = MixedPressureConnection(comport, [
                thyracontVoltageToPressure,
                thyracontVoltageToPressure,
                thyracontVoltageToPressure,
                lambda voltage: tpg300VoltageToPressure(voltage, TPG300Type.Pirani),
            ])
            try:
                self.connection.open()
                self.device_wrapper.threaded_connection = ThreadedMixedPressureConnection(
                    self.connection,
                    self.unconnect
                )
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

        self.device_wrapper.threaded_connection.close()
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
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

        self.device_wrapper.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')

        self.pressure_widget_1.setPressure(0)
        self.pressure_widget_2.setPressure(0)
        self.pressure_widget_4.setPressure(0)

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

        self.device_wrapper.threaded_connection.close()
        last_connection = ''
        if self.connection is not None:
            last_connection = self.combobox_connection.getValue(text=True)
            self.connection.close()

        GlobalConf.updateConnections(pressure=last_connection)

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if self.connection is not None:
            db.insertPressure(
                self.pressure_widget_1.pressure,
                self.pressure_widget_2.pressure,
                self.pressure_widget_3.pressure,
                self.pressure_widget_4.pressure,
            )
