from datetime import datetime
from pathlib import Path
from time import monotonic


import numpy as np

import pyqtgraph as pg


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QImage
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceCameraWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, ComboBox, ReadingAgeLabel, IndicatorLedButton
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox

from Connection.Camera import CameraConnection, listCameras, backendHelp, availableBackend, beamStatistics, VIRTUAL_CAMERA_ID
from Connection.Threaded import ThreadedCameraConnection, ThreadedDummyConnection


class CameraVBoxLayout(QVBoxLayout):
    """
    Panel for a FLIR/Teledyne camera (as used with SpinView): live image, exposure, gain, beam statistics, saving images
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.active_message_box = False

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('Camera', self.reconnect)

        self.device_wrapper = DeviceCameraWrapper()
        self.connection: None | CameraConnection = None

        self.image: np.ndarray | None = None
        self.maximum_value = 4095
        self.grab_pending = False
        self.frame_times: list[float] = []
        self.image_folder = Path(__file__).parents[1] / DefaultParams.camera_folder

        self.live_timer = QTimer()
        self.live_timer.setInterval(DefaultParams.camera_live_interval)
        self.live_timer.timeout.connect(self.grabImage)

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection')
        self.addWidget(self.connection_group_box)
        self.connection_vbox = QVBoxLayout()
        self.connection_group_box.setLayout(self.connection_vbox)

        self.connection_grid = InsertingGridLayout()
        self.connection_vbox.addLayout(self.connection_grid)

        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
        self.indicator_connection.setToolTip('Green if the camera is connected')
        self.status_connection = QLabel('Not connected')
        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('Camera (the virtual camera simulates a laser spot for testing)')
        self.button_connection = QPushButton('Connect')
        self.button_connection.setToolTip('Connect to / disconnect from the selected camera')
        self.button_connection.pressed.connect(self.manualConnect)
        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh camera list')
        self.button_connection_refresh.setIcon(QIcon('icons/refresh.png'))
        self.button_connection_refresh.pressed.connect(self.setCamerasComboBox)
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

        self.label_backend = QLabel(backendHelp())
        self.label_backend.setWordWrap(True)
        self.label_backend.setToolTip('Library that is used to talk to the cameras')
        self.connection_vbox.addWidget(self.label_backend)

        # Settings Group Box
        self.settings_group_box = QGroupBox('Settings')
        self.addWidget(self.settings_group_box)
        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.settings_group_box.setLayout(self.settings_hbox)
        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        self.label_exposure = QLabel('Exposure [µs]')
        self.spinbox_exposure = DoubleSpinBox(default=10000, step_size=100, input_range=(1, 3E7), decimals=0, buttons=False)
        self.spinbox_exposure.setToolTip('Exposure time in µs (press enter to apply, clipped to the range of the camera)')
        self.spinbox_exposure.editingFinished.connect(self.setExposure)
        self.status_exposure = QLabel('')
        self.status_exposure.setToolTip('Exposure time set in the camera')
        self.settings_grid.addWidgets(self.label_exposure, self.spinbox_exposure, self.status_exposure)

        self.label_gain = QLabel('Gain [dB]')
        self.spinbox_gain = DoubleSpinBox(default=0, step_size=1, input_range=(0, 48), decimals=1, buttons=False)
        self.spinbox_gain.setToolTip('Gain in dB (press enter to apply, clipped to the range of the camera)')
        self.spinbox_gain.editingFinished.connect(self.setGain)
        self.status_gain = QLabel('')
        self.status_gain.setToolTip('Gain set in the camera')
        self.settings_grid.addWidgets(self.label_gain, self.spinbox_gain, self.status_gain)

        self.button_live = QPushButton('Start live')
        self.button_live.setToolTip('Start/stop the live image')
        self.button_live.pressed.connect(self.toggleLive)
        self.button_single = QPushButton('Single image')
        self.button_single.setToolTip('Take one image')
        self.button_single.pressed.connect(self.grabImage)
        self.button_save = QPushButton('Save image')
        self.button_save.setToolTip(f'Save the current image as PNG (8 bit, for viewing) and NPY (raw values) into "{self.image_folder}"')
        self.button_save.pressed.connect(self.saveImage)
        self.settings_grid.addWidgets(self.button_live, self.button_single, self.button_save)

        self.button_auto_levels = IndicatorLedButton('Auto levels', initial_state=True)
        self.button_auto_levels.setToolTip('Adjust the color scale to every image (otherwise use the histogram on the right)')
        self.button_crosshair = IndicatorLedButton('Crosshair', initial_state=True)
        self.button_crosshair.setToolTip('Show the centroid of the beam')
        self.button_crosshair.clicked.connect(self.updateCrosshair)
        self.settings_grid.addWidgets(self.button_auto_levels, self.button_crosshair)

        # Beam statistics
        self.statistics_group_box = QGroupBox('Beam')
        self.addWidget(self.statistics_group_box)
        self.statistics_hbox = QHBoxLayout()
        self.statistics_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.statistics_group_box.setLayout(self.statistics_hbox)
        self.statistics_grid = InsertingGridLayout()
        self.statistics_hbox.addLayout(self.statistics_grid)

        self.status_maximum = QLabel('-')
        self.status_maximum.setToolTip('Maximum pixel value and fraction of saturated pixels (red if saturated: reduce exposure/gain)')
        self.status_centroid = QLabel('-')
        self.status_centroid.setToolTip('Centroid of the beam (background subtracted) in pixels')
        self.status_width = QLabel('-')
        self.status_width.setToolTip('FWHM of the beam (2.355 x rms width, background subtracted) in pixels')
        self.status_fps = QLabel('-')
        self.status_fps.setToolTip('Displayed images per second')
        self.statistics_grid.addWidgets(QLabel('Maximum'), self.status_maximum, QLabel('Centroid'), self.status_centroid)
        self.statistics_grid.addWidgets(QLabel('FWHM'), self.status_width, QLabel('Frame rate'), self.status_fps)

        # Image
        self.image_view = pg.ImageView()
        self.image_view.setMinimumSize(400, 300)
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        self.image_view.setToolTip('Camera image (zoom with the mouse wheel, color scale with the histogram on the right)')
        self.crosshair_x = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(Colors.color_red, width=1))
        self.crosshair_y = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(Colors.color_red, width=1))
        self.image_view.getView().addItem(self.crosshair_x)
        self.image_view.getView().addItem(self.crosshair_y)
        self.addWidget(self.image_view, stretch=1)

        self.reset()

        last_connection = GlobalConf.getConnection('camera')
        if last_connection and last_connection != VIRTUAL_CAMERA_ID:
            self.connect(last_connection, False)

    # ------------------------------------------------------------------ connection
    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection to the camera was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('Camera: Connection lost')
        self.unconnect()
        if self.last_port:
            self.auto_reconnect.start()

    def reconnect(self) -> bool:
        """Tries to reconnect silently to the last camera, returns True if connected"""

        if not self.device_wrapper.threaded_connection.isDummy():
            return True
        self.connect(self.last_port, False)
        return self.indicator_connection.value()

    def connect(self, camera_id: str = '', messagebox: bool = True):
        """
        Connect to given camera. If no camera is given, the selected camera will be connected to

        :param camera_id: id of camera (serial number, index or "virtual")
        :param messagebox: show messagebox if failed
        """

        if not camera_id:
            camera_id = self.combobox_connection.getValue(save=True)
        self.setCamera(camera_id)

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if not connect:
            return

        self.connection = CameraConnection(camera_id)
        try:
            self.connection.open()
            self.device_wrapper.threaded_connection = ThreadedCameraConnection(self.connection, self.connectionLost)
            self.last_port = camera_id
            self.indicator_connection.setValue(True)
            self.status_connection.setText('Connected')
            self.combobox_connection.setEnabled(False)
            self.button_connection_refresh.setEnabled(False)
            self.button_connection.setText('Disconnect')
            self.maximum_value = self.connection.getMaximumValue()
            self.setExposure()
            self.setGain()

        except ConnectionError as error:
            self.connection = None
            self.reset()
            GlobalConf.logger.info(f'Connection error! Could not connect to camera "{camera_id}", because of: {error}')
            if messagebox:
                showMessageBox(
                    None,
                    QMessageBox.Icon.Critical,
                    'Connection error!',
                    f'Could not connect to camera "{camera_id}"!',
                    f'<strong>Encountered Error:</strong><br>{error}',
                    expand_details=False
                )

    def unconnect(self):
        """Disconnect from the camera"""

        self.live_timer.stop()
        self.device_wrapper.threaded_connection.close()
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        camera_id = self.combobox_connection.getValue(save=True)
        self.reset()
        self.setCamera(camera_id)

    def setCamera(self, camera_id: str):
        """Selects the camera in the list"""

        if self.combobox_connection.entries_save and camera_id in self.combobox_connection.entries_save:
            self.combobox_connection.setCurrentIndex(self.combobox_connection.entries_save.index(camera_id))

    def setCamerasComboBox(self):
        """Sets the available cameras in the combobox"""

        cameras = listCameras()
        self.combobox_connection.reinitialize(
            entries=[description for _, description in cameras],
            entries_save=[camera_id for camera_id, _ in cameras],
            tooltips=[f'Camera id: {camera_id}' for camera_id, _ in cameras]
        )

    def reset(self):
        """Resets everything to default"""

        self.live_timer.stop()
        self.grab_pending = False
        self.frame_times = []
        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')
        self.button_live.setText('Start live')
        self.combobox_connection.setEnabled(True)
        self.button_connection_refresh.setEnabled(True)
        self.status_exposure.setText('')
        self.status_gain.setText('')
        self.status_fps.setText('-')
        self.setCamerasComboBox()

    def checkConnection(self, messagebox: bool = True) -> bool:
        """Checks if the camera is connected"""

        if self.indicator_connection.value():
            return True
        if messagebox and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(None, QMessageBox.Icon.Warning, 'Connection warning!', 'Camera is not connected, please connect first!')
            self.active_message_box = False
        return False

    # ------------------------------------------------------------------ settings
    def setExposure(self):
        """Sets the exposure time of the input field"""

        if not self.checkConnection(False):
            return
        threaded = self.device_wrapper.threaded_connection
        threaded.setExposure(self.spinbox_exposure.value())
        threaded.callback(
            lambda value: self.status_exposure.setText(f'{value:.0f} µs') if isinstance(value, float) else None,
            threaded.getExposure()
        )

    def setGain(self):
        """Sets the gain of the input field"""

        if not self.checkConnection(False):
            return
        threaded = self.device_wrapper.threaded_connection
        threaded.setGain(self.spinbox_gain.value())
        threaded.callback(
            lambda value: self.status_gain.setText(f'{value:.1f} dB') if isinstance(value, float) else None,
            threaded.getGain()
        )

    # ------------------------------------------------------------------ images
    def toggleLive(self):
        """Starts/stops the live image"""

        if self.live_timer.isActive():
            self.live_timer.stop()
            self.button_live.setText('Start live')
            return
        if not self.checkConnection():
            return
        self.frame_times = []
        self.live_timer.start()
        self.button_live.setText('Stop live')

    def grabImage(self):
        """Requests one image (only one request at a time, so slow cameras do not fill the queue)"""

        self.status_reading_age.setAge(self.device_wrapper.threaded_connection.secondsSinceLastResult(), self.indicator_connection.value())
        if self.grab_pending or not self.checkConnection(not self.live_timer.isActive()):
            return
        self.grab_pending = True
        threaded = self.device_wrapper.threaded_connection
        threaded.callback(self.showImage, threaded.grabImage())

    def showImage(self, image):
        """Shows an image and its statistics"""

        self.grab_pending = False
        if not isinstance(image, np.ndarray) or image.ndim != 2:
            GlobalConf.logger.error(f'Camera: invalid image: {image}')
            return

        self.image = image
        # pyqtgraph expects (x, y) axis order
        self.image_view.setImage(
            image.T,
            autoLevels=self.button_auto_levels.value(),
            autoRange=self.image_view.image is None,
            autoHistogramRange=self.button_auto_levels.value()
        )

        statistics = beamStatistics(image, self.maximum_value)
        saturated = statistics['saturation'] > 0
        self.status_maximum.setText(f'{statistics["maximum"]:.0f} / {self.maximum_value} ({statistics["saturation"] * 100:.2f} % saturated)')
        self.status_maximum.setStyleSheet(f'color: {Colors.color_red};' if saturated else '')
        if np.isfinite(statistics['x']):
            self.status_centroid.setText(f'x = {statistics["x"]:.1f}, y = {statistics["y"]:.1f}')
            self.status_width.setText(f'x = {2.355 * statistics["sigma_x"]:.1f}, y = {2.355 * statistics["sigma_y"]:.1f}')
            self.crosshair_x.setValue(statistics['x'])
            self.crosshair_y.setValue(statistics['y'])
        else:
            self.status_centroid.setText('no beam')
            self.status_width.setText('-')
        self.updateCrosshair()

        now = monotonic()
        self.frame_times = [t for t in self.frame_times if now - t < 2] + [now]
        if len(self.frame_times) > 1:
            self.status_fps.setText(f'{(len(self.frame_times) - 1) / (self.frame_times[-1] - self.frame_times[0]):.1f} fps')

    def updateCrosshair(self):
        """Shows/hides the crosshair"""

        visible = self.button_crosshair.value() and self.image is not None and self.status_centroid.text() not in ['-', 'no beam']
        self.crosshair_x.setVisible(visible)
        self.crosshair_y.setVisible(visible)

    def saveImage(self) -> Path | None:
        """Saves the current image as PNG (8 bit, scaled to the maximum) and NPY (raw values)"""

        if self.image is None:
            showMessageBox(None, QMessageBox.Icon.Information, 'No image', 'There is no image to save yet.')
            return None

        self.image_folder.mkdir(parents=True, exist_ok=True)
        base = self.image_folder / f'camera_{datetime.now():%Y%m%d_%H%M%S}'
        np.save(base.with_suffix('.npy'), self.image)

        scaled = np.clip(self.image.astype(float) / max(float(self.image.max()), 1) * 255, 0, 255).astype(np.uint8)
        scaled = np.ascontiguousarray(scaled)
        height, width = scaled.shape
        QImage(scaled.data, width, height, width, QImage.Format.Format_Grayscale8).save(str(base.with_suffix('.png')))

        GlobalConf.logger.info(f'Camera image saved as {base}.png/.npy')
        return base.with_suffix('.png')

    def closeEvent(self):
        """Must be called when application is closed"""

        self.live_timer.stop()
        self.device_wrapper.threaded_connection.close()

        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port
        self.auto_reconnect.stop()
        if self.connection is not None:
            self.connection.close()

        GlobalConf.updateConnections(camera=last_connection)

    def log(self, db: DB):
        """Nothing is logged for the camera (yet)"""

        pass
