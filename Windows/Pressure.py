from time import monotonic


from serial import SerialException


from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceMixedPressureWrapper

from Utility.Layouts import PressureWidget, IndicatorLed, ComboBox, ReadingAgeLabel
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox
from Utility.Icons import getIcon

from Connection.USBPorts import getComports
from Connection.Thyracont import thyracontVoltageToPressure
from Connection.TPG300 import tpg300VoltageToPressure, TPG300Type
from Connection.MixedPressure import MixedPressureConnection
from Connection.Threaded import ThreadedMixedPressureConnection, ThreadedDummyConnection


class PressureVBoxLayout(QVBoxLayout):

    # list of pressure gauges (in the order of the ADC channels)
    pressure_gauges = {
        # Name: ({pressure_widget_params}, voltage_to_pressure_function, database_column)
        # The name can be changed freely (it is only a label, the history stays intact),
        # but the database column is a stable id and must not be changed for an existing gauge
        'PITBUL': ({}, thyracontVoltageToPressure, 'PITBUL'),
        'LSD': ({}, thyracontVoltageToPressure, 'LSD'),
        'ESD': ({}, thyracontVoltageToPressure, 'ESD'),
        'Pre-Vacuum': ({'input_range': (1E3, 5E-3)}, lambda voltage: tpg300VoltageToPressure(voltage, TPG300Type.Pirani), 'Prevac'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updatePressure)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.device_wrapper = DeviceMixedPressureWrapper()

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('Pressure', self.reconnect)
        self.connection: None | MixedPressureConnection = None

        # time (monotonic) of the last successful reading, None if there was no reading since connecting
        self.last_update_time: float | None = None

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
        self.indicator_connection.setToolTip('Green if the device is connected')
        self.connection_hbox.addWidget(self.indicator_connection)
        self.status_connection = QLabel('Not connected')
        self.connection_hbox.addWidget(self.status_connection)
        self.status_reading_age = ReadingAgeLabel()
        self.connection_hbox.addWidget(self.status_reading_age)

        self.connection_hbox_selection = QHBoxLayout()
        self.connection_hbox_selection.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox_selection)

        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('Port of the device (refresh the list with the button on the right)')
        self.connection_hbox_selection.addWidget(self.combobox_connection)
        self.button_connection = QPushButton('Connect')
        self.button_connection.setToolTip('Connect to / disconnect from the selected port')
        self.button_connection.pressed.connect(self.manualConnect)
        self.connection_hbox_selection.addWidget(self.button_connection)

        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(getIcon('refresh.svg'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.connection_hbox_selection.addWidget(self.button_connection_refresh)

        self.pressure_group_boxes = []
        self.pressure_widgets = []
        self.pressure_layouts = []
        for pressure_gauge_name, (pressure_widget_params, _, _) in self.pressure_gauges.items():
            group_box = QGroupBox(pressure_gauge_name)
            self.pressure_group_boxes.append(group_box)
            pressure_widget = PressureWidget(**pressure_widget_params)
            self.pressure_widgets.append(pressure_widget)
            layout = QVBoxLayout()
            self.pressure_layouts.append(layout)
            layout.addWidget(pressure_widget)
            group_box.setLayout(layout)
            self.addWidget(group_box)

        self.reset()

        last_connection = GlobalConf.getConnection('pressure')
        if last_connection:
            self.connect(last_connection, False)

    def updatePressure(self):
        """Updates the pressure variables"""

        self.status_reading_age.setAge(self.secondsSinceLastUpdate(), not self.device_wrapper.threaded_connection.isDummy())

        if self.device_wrapper.threaded_connection.isDummy():
            return

        def setPressures(pressures: list[float]):
            if len(pressures) != len(self.pressure_widgets):
                GlobalConf.logger.error(f'Pressures cannot be set, non matching length: expected len = {len(self.pressure_widgets)}, got len = {len(pressures)}')
                return
            for pressure_widget, pressure in zip(self.pressure_widgets, pressures):
                if pressure_widget is None:
                    continue
                pressure_widget.setPressure(pressure)
            self.last_update_time = monotonic()

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
            self.connection = MixedPressureConnection(comport, [voltage_func for _, voltage_func, _ in self.pressure_gauges.values()])
            try:
                self.connection.open()
                self.device_wrapper.threaded_connection = ThreadedMixedPressureConnection(
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

    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection to the device was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('Pressure: Connection lost')
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

        for pressure_widget in self.pressure_widgets:
            pressure_widget.setPressure(0)
        self.last_update_time = None

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

    def secondsSinceLastUpdate(self) -> float | None:
        """Returns the seconds since the last successful reading, None if there was no reading since connecting"""

        if self.last_update_time is None:
            return None
        return monotonic() - self.last_update_time

    def getPressure(self, gauge_name: str) -> float:
        """
        Returns last pressure of gauge

        :param gauge_name: name of the pressure gauge (key of <pressure_gauges>)
        :returns: pressure in mbar (0 if not available)
        """

        gauge_names = list(self.pressure_gauges.keys())
        if gauge_name not in gauge_names:
            return 0
        return self.pressure_widgets[gauge_names.index(gauge_name)].pressure

    @classmethod
    def databaseLabels(cls) -> dict[str, tuple[str, str]]:
        """Returns the labels of the pressure gauges for the database as {database_column: (name, unit)}"""

        return {db_column: (name, 'mbar') for name, (_, _, db_column) in cls.pressure_gauges.items()}

    def closeEvent(self):
        """Must be called when application is closed"""

        self.device_wrapper.threaded_connection.close()
        # remember the port if connected or if the connection was lost (not if the user disconnected)
        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port or self.combobox_connection.getValue(text=True)
        self.auto_reconnect.stop()
        if self.connection is not None:
            self.connection.close()

        GlobalConf.updateConnections(pressure=last_connection)

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if self.connection is not None:
            # insert by database column, so the order of the gauges does not matter
            pressures = {db_column: pressure_widget.pressure for (_, _, db_column), pressure_widget in zip(self.pressure_gauges.values(), self.pressure_widgets)}
            db.insertPressure(*[pressures.get(column, 0) for column in db.pressure_table.variables])
