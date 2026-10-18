import json
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Callable


from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QBoxLayout, QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QLineEdit, QMessageBox,
    QProgressBar
)


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceCoboldWrapper

from Utility.Layouts import TabWidget, VBoxTitleLayout, InsertingGridLayout, IndicatorLed, DoubleSpinBox, FilePath
from Utility.FileDialogs import selectFolderDialog
from Utility.Dialogs import showMessageBox
from Utility.AutoReconnect import EventLog

from Connection.Cobold import CoboldConnection, DAqState, buildMeasurementPath, findCoboldFolder
from Connection.Threaded import ThreadedCoboldConnection, ThreadedDummyConnection


class CoboldVBoxLayout(QVBoxLayout):
    """
    Panel to run measurements with CoboldPC: start CoboldPC, start a measurement for a fixed time into a measurement
    folder with a fixed naming format, stop it and store the settings of the devices next to the list mode file

    :param metadata_function: function returning a dictionary with the current settings of the devices (stored as JSON)
    """

    def __init__(self, *args, metadata_function: Callable[[], dict] | None = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.metadata_function = metadata_function
        self.active_message_box = False

        self.device_wrapper = DeviceCoboldWrapper()
        self.connection: CoboldConnection | None = None
        self.daq_state = DAqState.UNKNOWN
        self.state_pending = False

        # running measurement
        self.measurement_file: Path | None = None
        self.measurement_start: datetime | None = None
        self.measurement_start_monotonic = 0.
        self.measurement_duration = 0.
        self.measurement_metadata: dict = {}

        # CoboldPC group
        self.cobold_group_box = QGroupBox('CoboldPC')
        self.addWidget(self.cobold_group_box)
        self.cobold_vbox = QVBoxLayout()
        self.cobold_group_box.setLayout(self.cobold_vbox)
        self.cobold_grid = InsertingGridLayout()
        self.cobold_vbox.addLayout(self.cobold_grid)

        folder = findCoboldFolder()
        self.label_installation = QLabel(str(folder) if folder else 'CoboldPC not found')
        self.label_installation.setWordWrap(True)
        self.label_installation.setToolTip('Installation folder of CoboldPC (CoboldPCCMD.exe is used to send commands)')
        self.cobold_vbox.addWidget(self.label_installation)

        self.indicator_state = IndicatorLed(off_color=Colors.color_red)
        self.indicator_state.setToolTip('Green: CoboldPC is running')
        self.status_state = QLabel('Unknown')
        self.status_state.setToolTip('State of CoboldPC and its data acquisition (DAq)')
        self.button_start_cobold = QPushButton('Start CoboldPC')
        self.button_start_cobold.setToolTip('Start CoboldPC (it executes its Startup.ccf, which may already start an acquisition)')
        self.button_start_cobold.pressed.connect(self.startCobold)
        self.cobold_grid.addWidgets(QLabel('State'), self.indicator_state, (self.status_state, 2), self.button_start_cobold)

        # Measurement group
        self.measurement_group_box = QGroupBox('Measurement')
        self.addWidget(self.measurement_group_box)
        self.measurement_vbox = QVBoxLayout()
        self.measurement_group_box.setLayout(self.measurement_vbox)
        self.measurement_grid = InsertingGridLayout()
        self.measurement_vbox.addLayout(self.measurement_grid)

        self.line_name = QLineEdit('measurement')
        self.line_name.setToolTip('Name of the measurement (used in folder and file name, "," is replaced)')
        self.line_name.textChanged.connect(self.updatePreview)
        self.measurement_grid.addWidgets(QLabel('Name'), (self.line_name, 3))

        self.spinbox_duration = DoubleSpinBox(default=10, step_size=1, input_range=(0, 100000), decimals=1, buttons=False)
        self.spinbox_duration.setToolTip('Duration of the measurement in minutes (0: until "Stop" is pressed)')
        self.measurement_grid.addWidgets(QLabel('Duration [min]'), self.spinbox_duration)

        self.file_path_folder = FilePath(
            placeholder='Select folder for all measurements',
            function=lambda: selectFolderDialog(None, 'Select the folder for the measurements') or None
        )
        self.file_path_folder.setToolTip('Folder in which the measurement folders are created')
        self.file_path_folder.setPath(GlobalConf.settings.value(GlobalConf.cobold_measurement_folder_name, defaultValue='', type=str))
        self.file_path_folder.path_display.textChanged.connect(self.updatePreview)
        self.measurement_grid.addWidgets(QLabel('Folder'), (self.file_path_folder, 3))

        self.line_comment = QLineEdit()
        self.line_comment.setToolTip('Comment written into the header of the list mode file and into the JSON file')
        self.measurement_grid.addWidgets(QLabel('Comment'), (self.line_comment, 3))

        self.label_preview = QLabel('')
        self.label_preview.setWordWrap(True)
        self.label_preview.setToolTip(
            'File of the next measurement. The naming format can be changed in Settings > Preferences > CoboldPC\n'
            f'(folder: "{DefaultParams.cobold_folder_pattern}", file: "{DefaultParams.cobold_file_pattern}")'
        )
        self.measurement_grid.addWidgets(QLabel('Next file'), (self.label_preview, 3))

        buttons = QHBoxLayout()
        buttons.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.measurement_vbox.addLayout(buttons)
        self.button_start = QPushButton('Start measurement')
        self.button_start.setToolTip('Prepare a new list mode file in CoboldPC and start the acquisition')
        self.button_start.pressed.connect(self.startMeasurement)
        buttons.addWidget(self.button_start)
        self.button_stop = QPushButton('Stop measurement')
        self.button_stop.setToolTip('Stop the acquisition (the list mode file is closed)')
        self.button_stop.pressed.connect(lambda: self.stopMeasurement('stopped by user'))
        buttons.addWidget(self.button_stop)
        self.button_open_folder = QPushButton('Open folder')
        self.button_open_folder.setToolTip('Open the folder of the last measurement')
        self.button_open_folder.pressed.connect(self.openFolder)
        buttons.addWidget(self.button_open_folder)

        self.progress_measurement = QProgressBar()
        self.progress_measurement.setToolTip('Progress of the running measurement')
        self.progress_measurement.setTextVisible(True)
        self.measurement_vbox.addWidget(self.progress_measurement)
        self.label_measurement = QLabel('No measurement running')
        self.label_measurement.setWordWrap(True)
        self.label_measurement.setToolTip('State of the measurement')
        self.measurement_vbox.addWidget(self.label_measurement)

        # timers
        self.state_timer = QTimer()
        self.state_timer.setInterval(DefaultParams.cobold_state_interval)
        self.state_timer.timeout.connect(self.updateState)
        self.measurement_timer = QTimer()
        self.measurement_timer.setInterval(500)
        self.measurement_timer.timeout.connect(self.updateMeasurement)

        self.updateButtons()
        self.updatePreview()
        self.connect()

    # ------------------------------------------------------------------ connection
    def connect(self):
        """Creates the (threaded) connection to CoboldPC if it is installed"""

        try:
            self.connection = CoboldConnection().open()
        except ConnectionError as error:
            GlobalConf.logger.info(f'CoboldPC: {error}')
            self.connection = None
            self.button_start_cobold.setEnabled(False)
            return
        self.device_wrapper.threaded_connection = ThreadedCoboldConnection(self.connection)
        self.state_timer.start()
        self.updateState()

    def updateState(self):
        """Requests the state of CoboldPC (only one request at a time, CoboldPCCMD can be slow)"""

        threaded = self.device_wrapper.threaded_connection
        if threaded.isDummy() or self.state_pending:
            return
        self.state_pending = True
        threaded.callback(self.setState, threaded.daqState())

    def setState(self, state):
        """Shows the state of CoboldPC"""

        self.state_pending = False
        if isinstance(state, Exception):
            self.daq_state = DAqState.UNKNOWN
            self.status_state.setText(f'Error: {state}')
        else:
            self.daq_state = state
            if state == DAqState.UNKNOWN:
                self.status_state.setText('Not running (or state unknown)')
            else:
                self.status_state.setText(f'Running, acquisition: {DAqState.names.get(state, state)}')
        self.indicator_state.setValue(self.daq_state != DAqState.UNKNOWN)
        self.updateButtons()

    def startCobold(self):
        """Starts CoboldPC"""

        threaded = self.device_wrapper.threaded_connection
        if threaded.isDummy():
            return

        def started(result):
            if isinstance(result, Exception):
                showMessageBox(None, QMessageBox.Icon.Critical, 'CoboldPC', f'CoboldPC could not be started: {result}')
            elif result is False:
                self.label_measurement.setText('CoboldPC is already running')
            else:
                self.label_measurement.setText('CoboldPC started')

        threaded.callback(started, threaded.startCobold())

    # ------------------------------------------------------------------ measurement
    def nextFile(self) -> Path | None:
        """Returns the list mode file of the next measurement (None if no folder is selected)"""

        if not self.file_path_folder.path:
            return None
        return buildMeasurementPath(self.file_path_folder.path, self.line_name.text())

    def updatePreview(self):
        """Shows the file of the next measurement"""

        try:
            next_file = self.nextFile()
        except (KeyError, ValueError, IndexError, FileExistsError) as error:
            self.label_preview.setText(f'Invalid naming format: {error}')
            return
        self.label_preview.setText(str(next_file) if next_file is not None else 'Select a folder first')

    def updateButtons(self):
        """Enables/disables the buttons"""

        running = self.measurement_file is not None
        self.button_start.setEnabled(not running and self.daq_state != DAqState.UNKNOWN)
        self.button_stop.setEnabled(running)
        self.button_start_cobold.setEnabled(self.connection is not None and self.daq_state == DAqState.UNKNOWN)
        self.line_name.setEnabled(not running)
        self.spinbox_duration.setEnabled(not running)
        self.file_path_folder.setEnabled(not running)

    def metadata(self) -> dict:
        """Returns the settings of all devices (if a metadata function is set)"""

        if self.metadata_function is None:
            return {}
        try:
            return self.metadata_function()
        except Exception as error:
            GlobalConf.logger.error(f'CoboldPC: device settings could not be collected: {error}')
            return {'error': str(error)}

    def writeMetadata(self):
        """Writes the measurement information and device settings as JSON next to the list mode file"""

        if self.measurement_file is None:
            return
        try:
            self.measurement_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.measurement_file.with_suffix('.json'), 'w', encoding='utf-8') as file:
                json.dump(self.measurement_metadata, file, indent=2, ensure_ascii=False, default=str)
        except OSError as error:
            GlobalConf.logger.error(f'CoboldPC: metadata could not be written: {error}')

    def startMeasurement(self):
        """Starts a measurement"""

        if self.device_wrapper.threaded_connection.isDummy():
            return
        if not self.file_path_folder.path:
            showMessageBox(None, QMessageBox.Icon.Information, 'No folder', 'Please select a folder for the measurements first.')
            return

        try:
            lmf_file = self.nextFile()
        except (KeyError, ValueError, IndexError, FileExistsError) as error:
            showMessageBox(None, QMessageBox.Icon.Warning, 'Invalid naming format', f'The file name could not be created: {error}')
            return

        GlobalConf.settings.setValue(GlobalConf.cobold_measurement_folder_name, self.file_path_folder.path)
        self.measurement_file = lmf_file
        self.measurement_start = datetime.now()
        self.measurement_start_monotonic = monotonic()
        self.measurement_duration = self.spinbox_duration.value() * 60
        self.measurement_metadata = {
            'name': self.line_name.text(),
            'comment': self.line_comment.text(),
            'lmf_file': str(lmf_file),
            'start': self.measurement_start.isoformat(timespec='seconds'),
            'planned_duration_s': self.measurement_duration,
            'software': f'{GlobalConf.title} v{GlobalConf.version}',
            'devices_at_start': self.metadata(),
        }
        self.label_measurement.setText(f'Starting measurement {lmf_file.name} ...')
        self.updateButtons()

        threaded = self.device_wrapper.threaded_connection
        threaded.callback(self.measurementStarted, threaded.startMeasurement(str(lmf_file), self.line_comment.text()))

    def measurementStarted(self, result):
        """Called when CoboldPC started the measurement"""

        if isinstance(result, Exception):
            GlobalConf.logger.error(f'CoboldPC measurement could not be started: {result}')
            showMessageBox(None, QMessageBox.Icon.Critical, 'Measurement not started', f'The measurement could not be started: {result}')
            self.measurement_file = None
            self.label_measurement.setText(f'Start failed: {result}')
            self.updateButtons()
            return

        self.writeMetadata()
        EventLog.log('CoboldPC', 'measurement_start', str(self.measurement_file), self.measurement_duration)
        self.measurement_timer.start()
        self.updateMeasurement()

    def updateMeasurement(self):
        """Shows the progress and stops the measurement when the duration is over"""

        if self.measurement_file is None:
            self.measurement_timer.stop()
            return

        elapsed = monotonic() - self.measurement_start_monotonic
        if self.measurement_duration > 0:
            self.progress_measurement.setRange(0, 1000)
            self.progress_measurement.setValue(int(min(elapsed / self.measurement_duration, 1) * 1000))
            remaining = max(self.measurement_duration - elapsed, 0)
            self.label_measurement.setText(f'Measuring {self.measurement_file.name}: {remaining / 60:.1f} min remaining')
            if elapsed >= self.measurement_duration:
                self.stopMeasurement('duration reached')
        else:
            self.progress_measurement.setRange(0, 0)  # busy indicator
            self.label_measurement.setText(f'Measuring {self.measurement_file.name}: {elapsed / 60:.1f} min (until stopped)')

    def stopMeasurement(self, reason: str = ''):
        """Stops the measurement"""

        if self.measurement_file is None:
            return
        self.measurement_timer.stop()
        self.measurement_metadata['stop'] = datetime.now().isoformat(timespec='seconds')
        self.measurement_metadata['duration_s'] = round(monotonic() - self.measurement_start_monotonic, 1)
        self.measurement_metadata['stop_reason'] = reason
        self.measurement_metadata['devices_at_stop'] = self.metadata()

        threaded = self.device_wrapper.threaded_connection
        if threaded.isDummy():
            self.measurementStopped(ConnectionError('No connection to CoboldPC'))
            return
        threaded.callback(self.measurementStopped, threaded.stopMeasurement())

    def measurementStopped(self, result):
        """Called when CoboldPC stopped the measurement"""

        if isinstance(result, Exception):
            GlobalConf.logger.error(f'CoboldPC measurement could not be stopped: {result}')
            self.measurement_metadata['stop_error'] = str(result)
            showMessageBox(None, QMessageBox.Icon.Critical, 'Measurement not stopped', f'Stopping the measurement failed, please check CoboldPC: {result}')

        self.writeMetadata()
        EventLog.log('CoboldPC', 'measurement_stop', f'{self.measurement_file} ({self.measurement_metadata.get("stop_reason", "")})', self.measurement_metadata.get('duration_s', 0))
        self.label_measurement.setText(f'Last measurement: {self.measurement_file} ({self.measurement_metadata.get("stop_reason", "")})')
        self.last_folder = self.measurement_file.parent
        self.measurement_file = None
        self.progress_measurement.setRange(0, 1000)
        self.progress_measurement.setValue(1000)
        self.updateButtons()
        self.updatePreview()

    def openFolder(self):
        """Opens the folder of the last measurement (or the measurement folder)"""

        folder = getattr(self, 'last_folder', None) or self.file_path_folder.path
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self):
        """Must be called when application is closed (a running measurement is stopped)"""

        if self.measurement_file is not None and not self.device_wrapper.threaded_connection.isDummy():
            GlobalConf.logger.warning('CoboldPC: application closed during a measurement, stopping it')
            try:
                self.connection.stopMeasurement()
            except Exception as error:
                GlobalConf.logger.error(f'CoboldPC: measurement could not be stopped: {error}')
            self.measurement_metadata['stop_reason'] = 'application closed'
            self.writeMetadata()
        self.state_timer.stop()
        self.device_wrapper.threaded_connection.close()
        GlobalConf.settings.setValue(GlobalConf.cobold_measurement_folder_name, self.file_path_folder.path)


class MeasureWindow(TabWidget):
    """
    Tab for measurements (CoboldPC)

    :param parent: parent widget (main window)
    :param metadata_function: function returning the settings of all devices
    """

    def __init__(self, parent, metadata_function: Callable[[], dict] | None = None):
        super().__init__(parent)

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        self.cobold_vbox = VBoxTitleLayout('CoboldPC', parent=self, add_stretch=True, popout_enable=True)
        self.cobold_group_vbox = CoboldVBoxLayout(metadata_function=metadata_function)
        self.cobold_group_vbox.addStretch(1)
        self.cobold_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.cobold_parent = QWidget(self)
        self.cobold_vbox.setBodyLayout(self.cobold_group_vbox)
        self.cobold_parent.setLayout(self.cobold_vbox)
        self.splitter.addWidget(self.cobold_parent)

    def closeEvent(self, event):
        """Closes the connection"""
        self.cobold_group_vbox.closeEvent()

    def log(self, db: DB):
        """Nothing to log"""
        pass
