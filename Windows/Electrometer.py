from math import isfinite, nan
from time import time


import numpy as np

import pyqtgraph as pg


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceKeithleyWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, ComboBox, ReadingAgeLabel, IndicatorLedButton, TimeCanvas
from Utility.Functions import getPrefix, isSaneNumber
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox
from Utility.Icons import getIcon

from Connection.USBPorts import getComports
from Connection.KeithleyPAmeter import KeithleyPAmeterConnection, KeithleyReading
from Connection.Threaded import ThreadedKeithleyConnection, ThreadedDummyConnection


class ElectrometerVBoxLayout(QVBoxLayout):
    """
    Panel for the Keithley 6514 electrometer (current measurement): live reading, range, NPLC, zero check/correct
    """

    current_ranges = ['AUTO'] + [member.value for name, member in KeithleyPAmeterConnection.CurrentRange.__members__.items() if name != 'AUTO']
    history_seconds = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.active_message_box = False

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('Electrometer', self.reconnect)

        self.device_wrapper = DeviceKeithleyWrapper()
        self.connection: None | KeithleyPAmeterConnection = None

        self.reading: KeithleyReading | None = None
        self.read_pending = False
        self.history_time: list[float] = []
        self.history_value: list[float] = []

        self.update_timer = QTimer()
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.start()

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection')
        self.addWidget(self.connection_group_box)
        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_group_box.setLayout(self.connection_hbox)
        self.connection_grid = InsertingGridLayout()
        self.connection_hbox.addLayout(self.connection_grid)

        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
        self.indicator_connection.setToolTip('Green if the electrometer is connected')
        self.status_connection = QLabel('Not connected')
        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('COM port of the electrometer')
        self.button_connection = QPushButton('Connect')
        self.button_connection.setToolTip('Connect to / disconnect from the selected port')
        self.button_connection.pressed.connect(self.manualConnect)
        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(getIcon('refresh.svg'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.status_reading_age = ReadingAgeLabel()
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            (self.status_connection, 2),
            self.combobox_connection,
            self.button_connection,
            self.button_connection_refresh,
            self.status_reading_age
        )

        # Settings Group Box
        self.settings_group_box = QGroupBox('Settings')
        self.addWidget(self.settings_group_box)
        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.settings_group_box.setLayout(self.settings_hbox)
        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        self.combobox_range = ComboBox(entries=[self.rangeText(current_range) for current_range in self.current_ranges], entries_save=self.current_ranges)
        self.combobox_range.setToolTip('Current range (AUTO: auto range)')
        self.combobox_range.currentIndexChanged.connect(self.setRange)
        self.spinbox_nplc = DoubleSpinBox(default=1, step_size=0.1, input_range=(0.01, 10), decimals=2, buttons=False)
        self.spinbox_nplc.setToolTip('Integration time in power line cycles (1 PLC = 20 ms at 50 Hz): larger = less noise, slower (press enter to apply)')
        self.spinbox_nplc.editingFinished.connect(self.setNPLC)
        self.settings_grid.addWidgets(QLabel('Range'), self.combobox_range, QLabel('NPLC'), self.spinbox_nplc)

        self.button_damping = IndicatorLedButton('Damping')
        self.button_damping.setToolTip('Damping of the current measurement (for high input capacitance)')
        self.button_damping.clicked.connect(self.setDamping)
        self.button_zero_check = IndicatorLedButton('Zero check')
        self.button_zero_check.setToolTip('Zero check: the input is shunted, the readings are NOT the input current (enable before changing connections)')
        self.button_zero_check.clicked.connect(self.setZeroCheck)
        self.button_zero_correct = QPushButton('Zero correct')
        self.button_zero_correct.setToolTip('Performs a zero correction (zero check on, correct, zero check off) - do not change the input meanwhile')
        self.button_zero_correct.pressed.connect(self.zeroCorrect)
        self.button_live = IndicatorLedButton('Live', initial_state=True)
        self.button_live.setToolTip('Read the current continuously (also logged to the database)')
        self.settings_grid.addWidgets(self.button_damping, self.button_zero_check, self.button_zero_correct, self.button_live)

        # Display
        self.display_group_box = QGroupBox('Current')
        self.addWidget(self.display_group_box)
        self.display_vbox = QVBoxLayout()
        self.display_group_box.setLayout(self.display_vbox)

        self.label_current = QLabel('-')
        font = QFont()
        font.setPointSizeF(font.pointSizeF() * 3)
        self.label_current.setFont(font)
        self.label_current.setToolTip('Last reading of the electrometer')
        self.display_vbox.addWidget(self.label_current)
        self.label_status = QLabel('')
        self.label_status.setToolTip('Status of the last reading (overflow, zero check)')
        self.display_vbox.addWidget(self.label_status)

        self.time_canvas = TimeCanvas([], grid=True, legend=False, time_fmt='%H:%M:%S')
        self.time_canvas.setMinimumHeight(200)
        self.time_canvas.setToolTip(f'Readings of the last {self.history_seconds} seconds')
        self.time_canvas.plot(np.array([]), np.array([]))
        self.display_vbox.addWidget(self.time_canvas)

        self.reset()

        last_connection = GlobalConf.getConnection('electrometer')
        if last_connection:
            self.connect(last_connection, False)

    @staticmethod
    def rangeText(current_range: str) -> str:
        """Human readable range, e.g. '2e-9' -> '2 nA'"""

        if current_range == 'AUTO':
            return 'AUTO'
        value, prefix = getPrefix(float(current_range))
        return f'{value:g} {prefix}A'

    # ------------------------------------------------------------------ connection
    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('Electrometer: Connection lost')
        self.unconnect()
        if self.last_port:
            self.auto_reconnect.start()

    def reconnect(self) -> bool:
        """Tries to reconnect silently to the last port, returns True if connected"""

        if not self.device_wrapper.threaded_connection.isDummy():
            return True
        self.connect(self.last_port, False)
        return self.indicator_connection.value()

    def connect(self, comport: str = '', messagebox: bool = True):
        """
        Connect to given comport. If no comport is given, the selected comport will be connected to

        :param comport: comport to connect to
        :param messagebox: show messagebox if failed
        """

        if not comport:
            comport = self.combobox_connection.getValue(text=True)
        self.setComport(comport)

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if not connect:
            return

        self.connection = KeithleyPAmeterConnection(comport, strict='MODEL 6514')
        try:
            self.connection.open()
            self.device_wrapper.threaded_connection = ThreadedKeithleyConnection(self.connection, self.connectionLost)
            self.last_port = comport
            self.indicator_connection.setValue(True)
            self.status_connection.setText('Connected')
            self.combobox_connection.setEnabled(False)
            self.button_connection_refresh.setEnabled(False)
            self.button_connection.setText('Disconnect')

            # current measurement with the selected settings
            threaded = self.device_wrapper.threaded_connection
            threaded.configureCurrent(self.combobox_range.getValue(save=True), self.spinbox_nplc.value(), self.button_damping.value(), True)
            threaded.callback(self.showZeroCheck, threaded.getZeroCheck())

        except (ConnectionError, OSError) as error:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
            self.reset()
            GlobalConf.logger.info(f'Connection error! Could not connect to the electrometer on port "{comport}", because of: {error}')
            if messagebox:
                showMessageBox(
                    None,
                    QMessageBox.Icon.Critical,
                    'Connection error!',
                    f'Could not connect to the electrometer on port "{comport}"!',
                    f'<strong>Encountered Error:</strong><br>{error}',
                    expand_details=False
                )

    def unconnect(self):
        """Disconnect from any port"""

        self.device_wrapper.threaded_connection.close()
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception as error:
                GlobalConf.logger.debug(f'Electrometer: error while closing: {error}')
            self.connection = None

        comport = self.combobox_connection.getValue(text=True)
        self.reset()
        self.setComport(comport)

    def setComport(self, comport: str):
        """Selects the comport in the list of comports"""

        entries = {port.lower(): i for i, port in enumerate(self.combobox_connection.entries)}
        if comport.lower() in entries:
            self.combobox_connection.setCurrentIndex(entries[comport.lower()])

    def setComportsComboBox(self):
        """Sets available ports in the comports combobox"""

        comports = getComports()
        self.combobox_connection.reinitialize(
            entries=[port for port, _, _ in comports],
            tooltips=[f'{port}: {description} [{hardware_id}]' for port, description, hardware_id in comports]
        )

    def reset(self):
        """Resets everything to default"""

        self.read_pending = False
        self.reading = None
        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')
        self.combobox_connection.setEnabled(True)
        self.button_connection_refresh.setEnabled(True)
        self.label_current.setText('-')
        self.label_status.setText('')
        self.setComportsComboBox()

    def checkConnection(self, messagebox: bool = True) -> bool:
        """Checks if the electrometer is connected"""

        if self.indicator_connection.value():
            return True
        if messagebox and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(None, QMessageBox.Icon.Warning, 'Connection warning!', 'Electrometer is not connected, please connect first!')
            self.active_message_box = False
        return False

    # ------------------------------------------------------------------ settings
    def setRange(self):
        """Sets the selected current range"""
        if self.checkConnection(False):
            self.device_wrapper.threaded_connection.setCurrentRange(self.combobox_range.getValue(save=True))

    def setNPLC(self):
        """Sets the integration time"""
        if self.checkConnection(False):
            self.device_wrapper.threaded_connection.setNPLC(self.spinbox_nplc.value())

    def setDamping(self):
        """Sets damping"""
        if self.checkConnection(False):
            self.device_wrapper.threaded_connection.setCurrentDamping(self.button_damping.value())

    def setZeroCheck(self):
        """Sets zero check"""
        if self.checkConnection(False):
            self.device_wrapper.threaded_connection.setZeroCheck(self.button_zero_check.value())

    def showZeroCheck(self, state):
        """Shows the zero check state of the instrument"""
        if isinstance(state, bool):
            self.button_zero_check.indicator_led.setValue(state)

    def zeroCorrect(self):
        """Performs a zero correction"""

        if not self.checkConnection():
            return
        threaded = self.device_wrapper.threaded_connection
        self.label_status.setText('Zero correction ...')
        threaded.zeroCorrect()
        self.combobox_range.setCurrentIndex(0)  # zero correct ends with auto range
        threaded.callback(self.showZeroCheck, threaded.getZeroCheck())

    # ------------------------------------------------------------------ readings
    def updateLoop(self):
        """Called by timer; requests a new reading (only one request at a time)"""

        connected = self.indicator_connection.value()
        self.status_reading_age.setAge(self.device_wrapper.threaded_connection.secondsSinceLastResult(), connected)
        if not connected or self.read_pending or not self.button_live.value():
            return
        self.read_pending = True
        threaded = self.device_wrapper.threaded_connection
        threaded.callback(self.showReading, threaded.read())

    def showReading(self, reading):
        """Shows a reading"""

        self.read_pending = False
        if not isinstance(reading, KeithleyReading):
            GlobalConf.logger.error(f'Electrometer: invalid reading {reading}')
            return

        self.reading = reading
        self.button_zero_check.indicator_led.setValue(reading.zero_check)

        if reading.overflow:
            self.label_current.setText('Overflow')
        else:
            value, prefix = getPrefix(reading.value)
            unit = {'CURR': 'A', 'VOLT': 'V', 'RES': 'Ω', 'CHAR': 'C'}[reading.function]
            self.label_current.setText(f'{value:+.4f} {prefix}{unit}')

        status = []
        if reading.overflow:
            status.append('Overflow - choose a larger range or AUTO')
        if reading.zero_check:
            status.append('Zero check is ON - the reading is not the input current')
        if reading.function != 'CURR':
            status.append(f'Function {reading.function} (not current)')
        self.label_status.setText(' | '.join(status))
        self.label_status.setStyleSheet(f'color: {Colors.color_red};' if status else '')

        # history plot of the last minutes
        now = time()
        self.history_time.append(now)
        self.history_value.append(reading.value if not reading.overflow and not reading.zero_check else nan)
        while self.history_time and now - self.history_time[0] > self.history_seconds:
            self.history_time.pop(0)
            self.history_value.pop(0)
        self.time_canvas.graph_curves[0].setData(np.array(self.history_time), np.array(self.history_value), connect='finite')

    def currentForLog(self) -> float | None:
        """Returns the current of the last reading if it is valid (no overflow, no zero check), else None"""

        reading = self.reading
        if reading is None or reading.overflow or reading.zero_check or reading.function != 'CURR' or not isSaneNumber(reading.value):
            return None
        return reading.value

    def closeEvent(self):
        """Must be called when application is closed"""

        self.update_timer.stop()
        self.device_wrapper.threaded_connection.close()

        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port
        self.auto_reconnect.stop()
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass

        GlobalConf.updateConnections(electrometer=last_connection)

    def log(self, db: DB):
        """Logs the current (only valid readings)"""

        if not self.checkConnection(False):
            return
        current = self.currentForLog()
        if current is not None:
            db.insertElectrometer(current)
