from math import ceil
from time import monotonic
from typing import Callable


from serial import SerialException


from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout, QMessageBox, QInputDialog, QGridLayout, QWidget, QDialog,
    QFormLayout, QDialogButtonBox, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, QEvent, QObject, pyqtSignal


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB, PressureTable, PressureRS485Table

from Socket.CommandServer import DeviceMixedPressureWrapper

from Utility.Layouts import ConnectButton, IconButton, PressureWidget, IndicatorLed, ComboBox, ReadingAgeLabel, VBoxTitleLayout
from Utility.AutoReconnect import AutoReconnect, EventLog
from Utility.Dialogs import showMessageBox
from Utility.Icons import getIcon

from Connection.USBPorts import getComports
from Connection.Thyracont import thyracontVoltageToPressure
from Connection.TPG300 import tpg300VoltageToPressure, TPG300Type
from Connection.MixedPressure import MixedPressureConnection
from Connection.ThyracontRS485 import ThyracontRS485Connection
from Connection.Threaded import ThreadedMixedPressureConnection, ThreadedThyracontRS485Connection, ThreadedDummyConnection


# types of gauges on the ADC: Name: (voltage_to_pressure_function, input range of the pressure widget as (maximum, minimum))
pressure_gauge_types = {
    'Thyracont': (thyracontVoltageToPressure, (1E3, 5E-10)),
    'TPG300 Pirani': (lambda voltage: tpg300VoltageToPressure(voltage, TPG300Type.Pirani), (1E3, 5E-3)),
    'TPG300 Cold Cathode': (lambda voltage: tpg300VoltageToPressure(voltage, TPG300Type.ColdCathod), (1E-2, 5E-9)),
}


class PressureGaugeBox(QGroupBox):
    """
    Compact group box of one gauge: digit on the left, on the right the pressure and below it the controls

    :param title: title of group box
    :param tooltip: tooltip of group box
    :param rename_function: called when the rename button is pressed
    :param remove_function: called when the remove button is pressed
    """

    def __init__(self, title: str, tooltip: str, rename_function: Callable, remove_function: Callable):
        super().__init__(title)
        self.setToolTip(tooltip)

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        self.pressure_widget = PressureWidget(stack_size=QSize(84, 84))
        self.pressure_widget.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.pressure_widget)

        self.info_vbox = QVBoxLayout()
        self.info_vbox.setSpacing(4)
        self.info_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.addLayout(self.info_vbox, 1)

        # the width of the group box does not change with the pressure
        self.pressure_label = self.pressure_widget.pressure_label
        self.pressure_label.setStyleSheet('font-size: 12pt; font-weight: bold;')
        self.pressure_label.setText('8.88 x 10<sup>-10</sup> mbar')
        self.pressure_label.ensurePolished()
        self.pressure_label.setMinimumWidth(self.pressure_label.sizeHint().width())
        self.pressure_widget.setPressure(0)
        self.info_vbox.addWidget(self.pressure_label)

        self.buttons_hbox = QHBoxLayout()
        self.buttons_hbox.setSpacing(4)
        self.buttons_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_vbox.addLayout(self.buttons_hbox)

        self.button_rename = IconButton()
        self.button_rename.setIcon(getIcon('rename.svg'))
        self.button_rename.setToolTip('Rename: change the name of the gauge. The history in the database stays intact')
        self.button_rename.clicked.connect(lambda: rename_function())
        self.buttons_hbox.addWidget(self.button_rename)

        self.button_remove = IconButton()
        self.button_remove.setIcon(getIcon('delete.svg'))
        self.button_remove.setToolTip('Remove: stop showing and logging this gauge. The history in the database stays intact')
        self.button_remove.clicked.connect(lambda: remove_function())
        self.buttons_hbox.addWidget(self.button_remove)


class PressureSource(QObject):
    """
    Connection (row of the connection section) and gauges of one device that reads pressure gauges

    :param name: name shown in the connection section and used for logging
    :param connection_type: type of the connection for <GlobalConf.getConnection>
    :param auto_reconnect_name: name for the automatic reconnect
    :param tooltip: tooltip of the connection row
    """

    def __init__(self, name: str, connection_type: str, auto_reconnect_name: str, tooltip: str):
        super().__init__()

        self.name = name
        self.connection_type = connection_type

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updatePressure)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect(auto_reconnect_name, self.reconnect)
        self.connection = None

        # time (monotonic) of the last successful reading, None if there was no reading since connecting
        self.last_update_time: float | None = None

        # gauges {key: group box}, key is the channel of the ADC or the address on the bus
        self.gauges: dict[int, PressureGaugeBox] = {}

        self.label_connection = QLabel(name)
        self.label_connection.setToolTip(tooltip)
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
        self.indicator_connection.setToolTip('Green if the device is connected')
        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('Port of the device (refresh the list with the button on the right)')
        self.button_connection = ConnectButton()
        self.button_connection.setToolTip('Connect to / disconnect from the selected port')
        self.button_connection.pressed.connect(self.manualConnect)
        self.button_connection_refresh = IconButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(getIcon('refresh.svg'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.status_reading_age = ReadingAgeLabel()

    @property
    def threaded_connection(self):
        """Threaded connection of the device"""
        raise NotImplementedError

    @threaded_connection.setter
    def threaded_connection(self, threaded_connection):
        raise NotImplementedError

    def createConnection(self, comport: str):
        """
        Returns the (not opened) connection to the device

        :param comport: comport to connect to
        """
        raise NotImplementedError

    def createThreadedConnection(self):
        """Returns the threaded connection of the opened <connection>"""
        raise NotImplementedError

    def readPressures(self):
        """Requests new pressures from the device, called periodically if connected"""
        raise NotImplementedError

    def addToGrid(self, grid: QGridLayout, row: int):
        """
        Adds the widgets of the connection to a row of a grid

        :param grid: grid of the connection section
        :param row: row of the grid
        """

        widgets = (self.label_connection, self.indicator_connection, self.combobox_connection, self.button_connection, self.button_connection_refresh, self.status_reading_age)
        for column, widget in enumerate(widgets):
            grid.addWidget(widget, row, column)

    def updatePressure(self):
        """Updates the pressure variables"""

        self.status_reading_age.setAge(self.secondsSinceLastUpdate(), not self.threaded_connection.isDummy())

        if not self.threaded_connection.isDummy():
            self.readPressures()

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
            self.connection = self.createConnection(comport)
            try:
                self.connection.open()
                self.threaded_connection = self.createThreadedConnection()
                self.indicator_connection.setValue(True)
                self.last_port = comport
                self.combobox_connection.setEnabled(False)
                self.button_connection_refresh.setEnabled(False)
                self.button_connection.setConnected(True)

            except (SerialException, ConnectionError) as error:
                try:
                    self.connection.close()
                except ConnectionError:
                    pass
                self.connection = None
                self.reset()

                GlobalConf.logger.info(f'Connection error! Could not connect to {self.name} on port "{comport}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to {self.name} on port "{comport}"!',
                        f'<strong>Encountered Error:</strong><br>{error}',
                        expand_details=False
                    )
        else:
            self.combobox_connection.setEnabled(True)
            self.button_connection_refresh.setEnabled(True)
            self.button_connection.setConnected(False)

    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection to the device was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning(f'{self.name}: Connection lost')
        self.unconnect()
        if self.last_port:
            self.auto_reconnect.start()

    def reconnect(self) -> bool:
        """Tries to reconnect silently to the last port, returns True if connected"""

        if not self.threaded_connection.isDummy():
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
        self.button_connection.setConnected(False)

        for gauge in self.gauges.values():
            gauge.pressure_widget.setPressure(0)
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

        GlobalConf.updateConnections(**{self.connection_type: last_connection})


class PressureLucidControl(PressureSource):
    """
    Gauges with an analog output on the channels of the LucidControl ADC. The name and the type of a gauge can be changed
    and a channel can be unused. The database column of a channel is a stable id and must not be changed.
    """

    # channel: (name, type of gauge), used until the gauges are changed in the GUI
    default_gauges = {
        0: ('PITBUL', 'Thyracont'),
        1: ('LSD', 'Thyracont'),
        2: ('ESD', 'Thyracont'),
        3: ('Pre-Vacuum', 'TPG300 Pirani'),
    }
    # database columns of the channels
    database_columns = {0: 'PITBUL', 1: 'LSD', 2: 'ESD', 3: 'Prevac'}
    channels = tuple(default_gauges)

    def __init__(self):
        super().__init__(
            'LucidControl',
            'pressure',
            'Pressure',
            'ADC with the analog outputs of the gauges. Used by the EBIS pressure interlock'
        )

        self.device_wrapper = DeviceMixedPressureWrapper()
        self.gauge_types: dict[int, str] = {}

    @property
    def threaded_connection(self):
        return self.device_wrapper.threaded_connection

    @threaded_connection.setter
    def threaded_connection(self, threaded_connection):
        self.device_wrapper.threaded_connection = threaded_connection

    @classmethod
    def gaugeConfiguration(cls) -> dict[int, tuple[str, str]]:
        """Returns the gauges as {channel: (name, type of gauge)}, invalid entries are ignored"""

        stored = GlobalConf.getPressureGauges()
        if stored is None:
            return dict(cls.default_gauges)
        return {channel: gauge for channel, gauge in stored.items() if channel in cls.channels and gauge[1] in pressure_gauge_types}

    def voltageFunction(self, channel: int) -> Callable[[float], float]:
        """
        Returns function that converts the voltage of a channel to the pressure in mbar

        :param channel: channel of the ADC
        """

        return pressure_gauge_types[self.gauge_types.get(channel, 'Thyracont')][0]

    def createConnection(self, comport: str) -> MixedPressureConnection:
        return MixedPressureConnection(comport, [self.voltageFunction(channel) for channel in self.channels])

    def createThreadedConnection(self) -> ThreadedMixedPressureConnection:
        return ThreadedMixedPressureConnection(self.connection, self.connectionLost)

    def setGaugeType(self, channel: int, gauge_type: str):
        """
        Sets the type of gauge of a channel, valid immediately

        :param channel: channel of the ADC
        :param gauge_type: type of gauge, key of <pressure_gauge_types>
        """

        self.gauge_types[channel] = gauge_type
        if self.connection is not None:
            self.connection.voltage_to_pressure_fct[channel] = self.voltageFunction(channel)

    def readPressures(self):
        def setPressures(pressures: tuple[float, ...] | Exception):
            if isinstance(pressures, Exception):
                return
            if len(pressures) != len(self.channels):
                GlobalConf.logger.error(f'Pressures cannot be set, non matching length: expected len = {len(self.channels)}, got len = {len(pressures)}')
                return
            for channel, gauge in self.gauges.items():
                gauge.pressure_widget.setPressure(pressures[channel])
            self.last_update_time = monotonic()

        self.threaded_connection.callback(setPressures, self.threaded_connection.getPressureAll())

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if self.connection is not None:
            # insert by database column, so the order of the gauges does not matter
            pressures = {self.database_columns[channel]: gauge.pressure_widget.pressure for channel, gauge in self.gauges.items()}
            db.insertPressure(*[pressures.get(column, 0) for column in db.pressure_table.variables])


class PressureRS485(PressureSource):
    """
    Gauges on the RS485 bus. They are logged by their address, so the name is only a label.
    Their pressures are only read and logged: the EBIS pressure interlock uses the gauges of the LucidControl ADC.
    """

    def __init__(self):
        super().__init__(
            'RS485',
            'pressure_rs485',
            'Pressure RS485',
            'RS485 adapter of the gauges, every gauge has an address (rotary switch on the gauge)'
        )

        self._threaded_connection = ThreadedDummyConnection()

        # only one reading at a time: gauges that do not answer take longer than the update timer
        self.update_pending = False

        # last readings {address: (pressure in mbar, Degas is on)}, None if the gauge did not answer it
        self.readings: dict[int, tuple[float | None, bool | None]] = {}

    @property
    def threaded_connection(self):
        return self._threaded_connection

    @threaded_connection.setter
    def threaded_connection(self, threaded_connection):
        self._threaded_connection = threaded_connection

    def createConnection(self, comport: str) -> ThyracontRS485Connection:
        return ThyracontRS485Connection(comport)

    def createThreadedConnection(self) -> ThreadedThyracontRS485Connection:
        return ThreadedThyracontRS485Connection(self.connection, self.connectionLost)

    def readPressures(self):
        if not self.gauges or self.update_pending:
            return

        def setReadings(readings: dict[int, tuple[float | None, bool | None]] | Exception):
            self.update_pending = False
            if not isinstance(readings, dict):
                return

            # a gauge could have been removed in the meantime
            self.readings = {address: reading for address, reading in readings.items() if address in self.gauges}
            for address, (pressure, _) in self.readings.items():
                self.gauges[address].pressure_widget.setPressure(pressure if pressure is not None else 0)
            if any(pressure is not None for pressure, _ in self.readings.values()):
                self.last_update_time = monotonic()
            self.updateDegasButtons()

        self.update_pending = True
        self.threaded_connection.callback(setReadings, self.threaded_connection.getReadings(list(self.gauges)))

    def updateDegasButtons(self):
        """Updates the Degas buttons: Degas can only be started below the pressure limit of the gauge and stopped at any time"""

        limit = ThyracontRS485Connection.degas_pressure_limit
        for address, gauge in self.gauges.items():
            pressure, degas = self.readings.get(address, (None, None))
            if degas is None:
                enabled = False
                tooltip = 'Degas is not available: not connected, no answer of the gauge or not supported by the gauge'
            elif degas:
                enabled = True
                tooltip = 'Degas is running (red), it stops automatically after about 3 minutes. Press to stop it now'
            else:
                enabled = pressure is not None and 0 < pressure < limit
                tooltip = f'Starts Degas (only possible below {limit:g} mbar): heats the anode to around 800 °C for about 3 minutes'

            gauge.button_degas.setEnabled(enabled)
            gauge.button_degas.setToolTip(tooltip)
            gauge.button_degas.setStyleSheet(f'background-color: {Colors.color_red};' if degas else '')

    def degasPressed(self, address: int):
        """
        Starts Degas after asking, or stops it if it is running

        :param address: RS485 address of gauge
        """

        pressure, degas = self.readings.get(address, (None, None))
        if self.threaded_connection.isDummy() or degas is None:
            return
        name = self.gauges[address].name

        def degasSet(result: Exception | None):
            if isinstance(result, Exception):
                showMessageBox(None, QMessageBox.Icon.Warning, 'Degas not changed!', f'The gauge "{name}" did not change Degas!', str(result))
                return
            EventLog.log(self.name, 'degas_stop' if degas else 'degas_start', f'Degas of "{name}" {"stopped" if degas else "started"} by the user', pressure if pressure is not None else 0)

        if degas:
            self.threaded_connection.callback(degasSet, self.threaded_connection.setDegas(False, address))
            return

        answer = QMessageBox.question(
            None,
            'Start Degas',
            f'Start Degas on "{name}" at {pressure:.2E} mbar?\n\n'
            'The anode is heated to around 800 °C for about 3 minutes and the pressure will rise, '
            'which can trip the EBIS pressure interlock.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # the connection checks the pressure of the gauge again and refuses to start if it is too high
        self.threaded_connection.callback(degasSet, self.threaded_connection.setDegas(True, address))

    def reset(self):
        self.readings = {}
        self.update_pending = False
        super().reset()
        self.updateDegasButtons()

    def getPressures(self) -> dict[str, float | None]:
        """Returns the last pressures in mbar as {name: pressure}, None if the gauge did not answer"""

        return {gauge.name: self.readings.get(address, (None, None))[0] for address, gauge in self.gauges.items()}

    def databaseLabels(self) -> dict[str, tuple[str, str]]:
        """Returns the labels of the pressure gauges for the database as {database_column: (name, unit)}"""

        return {PressureRS485Table.column(address): (gauge.name, 'mbar') for address, gauge in self.gauges.items()}

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        # a gauge without an answer is stored as NULL, so it is a gap in the history and not a pressure of 0
        pressures = {address: pressure for address, (pressure, _) in self.readings.items()}
        if self.connection is not None and any(pressure is not None for pressure in pressures.values()):
            db.insertPressureRS485(pressures)


class PressureAddGaugeDialog(QDialog):
    """
    Dialog for adding a gauge

    :param channels: free channels of the ADC
    :param addresses: free addresses of the RS485 bus
    """

    source_lucid_control = 'LucidControl ADC (analog)'
    source_rs485 = 'RS485 bus'

    def __init__(self, channels: list[int], addresses: list[int]):
        super().__init__()
        self.setWindowTitle('Add gauge')

        self.channels = channels
        self.addresses = addresses

        self.main_layout = QFormLayout()
        self.setLayout(self.main_layout)

        sources = ([self.source_lucid_control] if channels else []) + ([self.source_rs485] if addresses else [])
        self.combobox_source = ComboBox(entries=sources)
        self.main_layout.addRow('Connected to', self.combobox_source)

        self.label_key = QLabel('')
        self.combobox_key = ComboBox()
        self.main_layout.addRow(self.label_key, self.combobox_key)

        self.line_name = QLineEdit()
        self.main_layout.addRow('Name', self.line_name)

        self.label_type = QLabel('Type')
        self.combobox_type = ComboBox(entries=list(pressure_gauge_types))
        self.main_layout.addRow(self.label_type, self.combobox_type)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.main_layout.addRow(self.buttons)

        self.combobox_source.currentIndexChanged.connect(self.sourceChanged)
        self.sourceChanged()

    def isRS485(self) -> bool:
        """Returns if the gauge is on the RS485 bus"""
        return self.combobox_source.getValue(text=True) == self.source_rs485

    def sourceChanged(self, *args):
        """Shows the fields of the selected source"""

        rs485 = self.isRS485()
        self.label_key.setText('Address (rotary switch)' if rs485 else 'Channel')
        self.combobox_key.reinitialize(entries=[str(address) for address in self.addresses] if rs485 else [str(channel + 1) for channel in self.channels])
        self.label_type.setVisible(not rs485)
        self.combobox_type.setVisible(not rs485)

    def key(self) -> int:
        """Returns the selected address of the bus or channel of the ADC"""

        value = int(self.combobox_key.getValue(text=True))
        return value if self.isRS485() else value - 1


class PressureVBoxLayout(QVBoxLayout):
    """
    All pressure gauges in one panel: the gauges on the LucidControl ADC and on the RS485 bus. Gauges can be added, renamed and
    removed in the GUI. The gauges are arranged in as many columns as needed to see all of them without scrolling.
    The EBIS pressure interlock uses the gauges of the LucidControl ADC (<getPressure>, <secondsSinceLastUpdate>).
    """

    # emitted if a gauge was added, renamed or removed: old name, new name (empty if it was not renamed)
    gauges_changed = pyqtSignal(str, str)

    max_columns = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.lucid_control = PressureLucidControl()
        self.rs485 = PressureRS485()
        self.device_wrapper = self.lucid_control.device_wrapper

        # returns the name of the gauge that is used by the EBIS pressure interlock
        self.interlock_gauge_function: Callable[[], str] | None = None

        self.title_layout: VBoxTitleLayout | None = None
        self.columns = 1

        # Connection
        self.connection_group_box = QGroupBox('Connection')
        self.addWidget(self.connection_group_box)

        self.connection_vbox = QVBoxLayout()
        self.connection_group_box.setLayout(self.connection_vbox)

        self.connection_grid = QGridLayout()
        self.connection_vbox.addLayout(self.connection_grid)
        self.lucid_control.addToGrid(self.connection_grid, 0)
        self.rs485.addToGrid(self.connection_grid, 1)
        self.connection_grid.setColumnStretch(5, 1)

        self.gauge_buttons_hbox = QHBoxLayout()
        self.gauge_buttons_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.gauge_buttons_hbox)

        self.button_add = QPushButton('Add gauge')
        self.button_add.setToolTip('Add a gauge on a channel of the LucidControl ADC or on the RS485 bus')
        self.button_add.clicked.connect(self.addGauge)
        self.gauge_buttons_hbox.addWidget(self.button_add)

        self.button_scan = QPushButton('Scan RS485')
        self.button_scan.setToolTip('Searches all addresses of the RS485 bus (takes a few seconds) and adds the gauges that are not in the list yet')
        self.button_scan.clicked.connect(self.scan)
        self.gauge_buttons_hbox.addWidget(self.button_scan)

        self.status_scan = QLabel('')
        self.status_scan.setToolTip('Result of the last scan of the RS485 bus')
        self.gauge_buttons_hbox.addWidget(self.status_scan)

        # Gauges
        self.gauges_widget = QWidget()
        self.gauges_grid = QGridLayout()
        self.gauges_grid.setContentsMargins(0, 0, 0, 0)
        self.gauges_widget.setLayout(self.gauges_grid)
        self.addWidget(self.gauges_widget)

        for channel, (name, gauge_type) in PressureLucidControl.gaugeConfiguration().items():
            self._createLucidControlGauge(channel, name, gauge_type)
        for address, name in GlobalConf.getPressureRS485Gauges().items():
            self._createRS485Gauge(address, name)
        self.columns = 2 if len(self.allGauges()) > 4 else 1
        self.arrangeGauges()

        for source in (self.lucid_control, self.rs485):
            source.reset()
            last_connection = GlobalConf.getConnection(source.connection_type)
            if last_connection:
                source.connect(last_connection, False)

    def setTitleLayout(self, title_layout: VBoxTitleLayout):
        """
        Sets the layout around this one, its visible height decides on the number of columns

        :param title_layout: layout with the scroll area of the body
        """

        self.title_layout = title_layout
        self.title_layout.body_scroll.viewport().installEventFilter(self)
        self.title_layout.updateBodyMinimumWidth()

    def eventFilter(self, watched, event) -> bool:
        """Arranges the gauges if the height of the panel changed"""

        if event.type() == QEvent.Type.Resize and self.title_layout is not None and watched is self.title_layout.body_scroll.viewport():
            self.fitColumns()
        return False

    def fitColumns(self):
        """Uses the smallest number of columns where all gauges are visible without scrolling"""

        gauges = self.allGauges()
        height = self.title_layout.body_scroll.viewport().height()
        # not laid out yet
        if not gauges or height < 300:
            return

        spacing = max(self.gauges_grid.verticalSpacing(), 0)
        gauge_height = max(gauge.sizeHint().height() for gauge in gauges) + spacing
        margins = self.contentsMargins()
        available = height - self.connection_group_box.sizeHint().height() - self.spacing() - margins.top() - margins.bottom()

        columns = 1
        while columns < self.max_columns and ceil(len(gauges) / columns) * gauge_height > available:
            columns += 1

        if columns != self.columns:
            self.columns = columns
            self.arrangeGauges()

    def allGauges(self) -> list[PressureGaugeBox]:
        """Returns all gauges in the order they are shown"""
        return list(self.lucid_control.gauges.values()) + list(self.rs485.gauges.values())

    def arrangeGauges(self):
        """Puts the gauges into the grid with the current number of columns"""

        for gauge in self.allGauges():
            self.gauges_grid.removeWidget(gauge)
        for index, gauge in enumerate(self.allGauges()):
            self.gauges_grid.addWidget(gauge, index // self.columns, index % self.columns)
        for column in range(self.max_columns):
            self.gauges_grid.setColumnStretch(column, 1 if column < self.columns else 0)

        # the size of the grid must be up to date for the minimum width of the panel
        self.gauges_grid.invalidate()
        self.gauges_grid.activate()
        self.gauges_widget.updateGeometry()
        self.invalidate()
        self.activate()
        if self.title_layout is not None:
            self.title_layout.updateBodyMinimumWidth()

    def _createLucidControlGauge(self, channel: int, name: str, gauge_type: str):
        """
        Creates the group box of a gauge on the ADC, sorted by channel

        :param channel: channel of the ADC
        :param name: name of gauge
        :param gauge_type: type of gauge, key of <pressure_gauge_types>
        """

        gauge = PressureGaugeBox(
            '',
            f'Gauge on channel {channel + 1} of the LucidControl ADC, logged in the database column {PressureTable.name}.{PressureLucidControl.database_columns[channel]}',
            lambda: self.renameGauge(self.lucid_control, channel),
            lambda: self.removeGauge(self.lucid_control, channel)
        )
        gauge.key_text = f'ADC {channel + 1}'
        gauge.combobox_type = ComboBox(entries=list(pressure_gauge_types), default=list(pressure_gauge_types).index(gauge_type))
        gauge.combobox_type.setToolTip('Type of the gauge, used to convert the voltage of the channel to the pressure')
        gauge.combobox_type.currentIndexChanged.connect(lambda: self.gaugeTypeChanged(channel))
        # the width does not depend on the longest type, the list still shows the full names
        gauge.combobox_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        gauge.combobox_type.setMinimumContentsLength(7)
        gauge.combobox_type.view().setMinimumWidth(gauge.combobox_type.view().sizeHintForColumn(0) + 20)
        gauge.info_vbox.insertWidget(1, gauge.combobox_type)
        self._setGaugeName(gauge, name)

        self.lucid_control.gauges[channel] = gauge
        self.lucid_control.gauges = dict(sorted(self.lucid_control.gauges.items()))
        self.lucid_control.setGaugeType(channel, gauge_type)
        gauge.pressure_widget.setInputRange(pressure_gauge_types[gauge_type][1])

    def _createRS485Gauge(self, address: int, name: str):
        """
        Creates the group box of a gauge on the bus, sorted by address

        :param address: RS485 address of gauge
        :param name: name of gauge
        """

        gauge = PressureGaugeBox(
            '',
            f'Gauge with address {address} on the RS485 bus, logged in the database column {PressureRS485Table.name}.{PressureRS485Table.column(address)}',
            lambda: self.renameGauge(self.rs485, address),
            lambda: self.removeGauge(self.rs485, address)
        )
        gauge.key_text = f'RS485 {address}'
        gauge.button_degas = IconButton()
        gauge.button_degas.setIcon(getIcon('flame.svg'))
        gauge.button_degas.clicked.connect(lambda: self.rs485.degasPressed(address))
        gauge.buttons_hbox.addWidget(gauge.button_degas)
        self._setGaugeName(gauge, name)

        self.rs485.gauges[address] = gauge
        self.rs485.gauges = dict(sorted(self.rs485.gauges.items()))
        self.rs485.updateDegasButtons()

    @staticmethod
    def _setGaugeName(gauge: PressureGaugeBox, name: str):
        """
        Sets the name of a gauge

        :param gauge: group box of gauge
        :param name: new name
        """

        gauge.name = name
        gauge.setTitle(f'{name} ({gauge.key_text})')

    def _validName(self, name: str, gauge: PressureGaugeBox | None = None) -> bool:
        """
        Returns if the name can be used (shows a message box otherwise). The names are unique over all gauges.

        :param name: new name
        :param gauge: gauge that gets the name, if it already exists
        """

        if not name:
            return False
        if name in [other.name for other in self.allGauges() if other is not gauge]:
            showMessageBox(None, QMessageBox.Icon.Warning, 'Name already used!', f'There is already a gauge with the name "{name}". Please use a different name.')
            return False
        return True

    def _gaugesChanged(self, old_name: str = '', new_name: str = ''):
        """
        Stores the gauges and tells everyone else that they changed

        :param old_name: old name of a renamed gauge
        :param new_name: new name of a renamed gauge
        """

        GlobalConf.updatePressureGauges({channel: (gauge.name, gauge.combobox_type.getValue(text=True)) for channel, gauge in self.lucid_control.gauges.items()})
        GlobalConf.updatePressureRS485Gauges({address: gauge.name for address, gauge in self.rs485.gauges.items()})
        self.gauges_changed.emit(old_name, new_name)

    def addGauge(self):
        """Asks for a new gauge and adds it"""

        channels = [channel for channel in PressureLucidControl.channels if channel not in self.lucid_control.gauges]
        addresses = [address for address in PressureRS485Table.addresses if address not in self.rs485.gauges]
        if not channels and not addresses:
            showMessageBox(None, QMessageBox.Icon.Information, 'All used!', 'All channels of the ADC and all addresses of the bus are already used.')
            return

        dialog = PressureAddGaugeDialog(channels, addresses)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = dialog.line_name.text().strip()
        if not self._validName(name):
            return

        if dialog.isRS485():
            self._createRS485Gauge(dialog.key(), name)
        else:
            self._createLucidControlGauge(dialog.key(), name, dialog.combobox_type.getValue(text=True))
        self.arrangeGauges()
        self._gaugesChanged()
        if self.title_layout is not None:
            self.fitColumns()

    def renameGauge(self, source: PressureSource, key: int):
        """
        Asks for a new name of a gauge

        :param source: source of the gauge
        :param key: channel of the ADC or address of the bus
        """

        gauge = source.gauges[key]
        name, ok = QInputDialog.getText(None, 'Rename gauge', f'New name of "{gauge.name}" ({gauge.key_text}):', text=gauge.name)
        name = name.strip()
        if not ok or name == gauge.name or not self._validName(name, gauge):
            return

        old_name = gauge.name
        self._setGaugeName(gauge, name)
        self._gaugesChanged(old_name, name)

    def removeGauge(self, source: PressureSource, key: int):
        """
        Removes a gauge after asking. Its data stays in the database and is used again if a gauge with this channel/address is added

        :param source: source of the gauge
        :param key: channel of the ADC or address of the bus
        """

        gauge = source.gauges[key]

        if source is self.lucid_control and self.interlock_gauge_function is not None and self.interlock_gauge_function() == gauge.name:
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'Gauge is used by the interlock!',
                f'"{gauge.name}" is used by the EBIS pressure interlock. Please select a different gauge in the EBIS panel first.'
            )
            return

        answer = QMessageBox.question(None, 'Remove gauge', f'Stop showing and logging "{gauge.name}" ({gauge.key_text})?\nThe logged data stays in the database.')
        if answer != QMessageBox.StandardButton.Yes:
            return

        del source.gauges[key]
        self.gauges_grid.removeWidget(gauge)
        gauge.deleteLater()
        if source is self.rs485:
            self.rs485.readings.pop(key, None)
        self.arrangeGauges()
        self._gaugesChanged()
        if self.title_layout is not None:
            self.fitColumns()

    def gaugeTypeChanged(self, channel: int):
        """
        The type of a gauge on the ADC was selected

        :param channel: channel of the ADC
        """

        gauge = self.lucid_control.gauges[channel]
        new_type = gauge.combobox_type.getValue(text=True)
        old_type = self.lucid_control.gauge_types[channel]
        if new_type == old_type:
            return

        if self.interlock_gauge_function is not None and self.interlock_gauge_function() == gauge.name:
            answer = QMessageBox.question(
                None,
                'Gauge is used by the interlock!',
                f'"{gauge.name}" is used by the EBIS pressure interlock, a wrong type means wrong pressures for the interlock.\n\nChange the type to {new_type}?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if answer != QMessageBox.StandardButton.Yes:
                gauge.combobox_type.blockSignals(True)
                gauge.combobox_type.setCurrentIndex(list(pressure_gauge_types).index(old_type))
                gauge.combobox_type.blockSignals(False)
                return

        self.lucid_control.setGaugeType(channel, new_type)
        gauge.pressure_widget.setInputRange(pressure_gauge_types[new_type][1])
        GlobalConf.logger.info(f'Pressure: Type of "{gauge.name}" changed from {old_type} to {new_type}')
        EventLog.log('Pressure', 'gauge_type_changed', f'Type of "{gauge.name}" changed from {old_type} to {new_type}')
        self._gaugesChanged()

    def scan(self):
        """Searches for gauges on the RS485 bus"""

        if self.rs485.threaded_connection.isDummy():
            self.status_scan.setText('Connect first')
            return

        self.button_scan.setEnabled(False)
        self.status_scan.setText('Scanning...')

        def setGauges(gauges: dict[int, str] | Exception):
            self.button_scan.setEnabled(True)
            if not isinstance(gauges, dict):
                self.status_scan.setText('Scan failed')
                return

            new_gauges = {address: product for address, product in gauges.items() if address not in self.rs485.gauges}
            names = [gauge.name for gauge in self.allGauges()]
            for address, product in new_gauges.items():
                name = f'{product} {address}'
                # e.g. after renaming another gauge to this name
                while name in names:
                    name += '_'
                names.append(name)
                self._createRS485Gauge(address, name)
            if new_gauges:
                self.arrangeGauges()
                self._gaugesChanged()
                if self.title_layout is not None:
                    self.fitColumns()
            self.status_scan.setText(f'{len(gauges)} found, {len(new_gauges)} new')

        self.rs485.threaded_connection.callback(setGauges, self.rs485.threaded_connection.scan())

    @classmethod
    def gaugeNames(cls) -> list[str]:
        """Returns the names of the gauges that can be used by the EBIS pressure interlock (gauges on the ADC)"""
        return [name for name, _ in PressureLucidControl.gaugeConfiguration().values()]

    def secondsSinceLastUpdate(self) -> float | None:
        """Returns the seconds since the last successful reading of the ADC, None if there was no reading since connecting"""
        return self.lucid_control.secondsSinceLastUpdate()

    def getPressure(self, gauge_name: str) -> float:
        """
        Returns last pressure of a gauge on the ADC

        :param gauge_name: name of the pressure gauge
        :returns: pressure in mbar (0 if not available)
        """

        for gauge in self.lucid_control.gauges.values():
            if gauge.name == gauge_name:
                return gauge.pressure_widget.pressure
        return 0

    def getPressures(self) -> dict[str, float]:
        """Returns the last pressures in mbar of the gauges on the ADC as {name: pressure}"""
        return {gauge.name: gauge.pressure_widget.pressure for gauge in self.lucid_control.gauges.values()}

    def databaseLabels(self) -> dict[str, tuple[str, str]]:
        """Returns the labels of the gauges on the ADC for the database as {database_column: (name, unit)}"""
        return {PressureLucidControl.database_columns[channel]: (gauge.name, 'mbar') for channel, gauge in self.lucid_control.gauges.items()}

    def databaseGauges(self) -> list[tuple[str, str, str, str | None]]:
        """Returns all possible gauges as (table name, column name, text of gauge, current name or None if it is not shown)"""

        gauges = []
        for channel, column in PressureLucidControl.database_columns.items():
            gauge = self.lucid_control.gauges.get(channel)
            gauges.append((PressureTable.name, column, f'ADC {channel + 1}', gauge.name if gauge is not None else None))
        for address in PressureRS485Table.addresses:
            gauge = self.rs485.gauges.get(address)
            gauges.append((PressureRS485Table.name, PressureRS485Table.column(address), f'RS485 {address}', gauge.name if gauge is not None else None))
        return gauges

    def setGaugeNames(self, names: dict[tuple[str, str], str]):
        """
        Sets the names of the gauges after they were changed in the database

        :param names: {(table name, column name): name}
        """

        gauges = [(PressureTable.name, PressureLucidControl.database_columns[channel], gauge) for channel, gauge in self.lucid_control.gauges.items()]
        gauges += [(PressureRS485Table.name, PressureRS485Table.column(address), gauge) for address, gauge in self.rs485.gauges.items()]
        for table, column, gauge in gauges:
            name = names.get((table, column), gauge.name)
            if name != gauge.name:
                old_name = gauge.name
                self._setGaugeName(gauge, name)
                self._gaugesChanged(old_name, name)

    def closeEvent(self):
        """Must be called when application is closed"""

        self.lucid_control.closeEvent()
        self.rs485.closeEvent()

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        self.lucid_control.log(db)
        self.rs485.log(db)
