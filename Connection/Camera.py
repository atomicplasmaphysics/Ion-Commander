"""
Connection to FLIR/Teledyne cameras (the ones used with SpinView).

Backends (the first available one is used):
1) PySpin      - Python wrapper of the Spinnaker SDK (download "spinnaker_python" matching the installed Spinnaker
                 version and the Python version from the Teledyne website and install the wheel with pip)
2) harvesters  - generic GenICam library (pip install harvesters) that uses the GenTL producer (.cti) of the installed
                 Spinnaker SDK, e.g. "C:/Program Files/Teledyne/Spinnaker/cti64/vs2015/Spinnaker_GenTL_v140.cti"

All functions are blocking, use the threaded connection in the GUI.
"""

from glob import glob


import numpy as np


from Config.GlobalConf import GlobalConf


try:
    import PySpin
except ImportError:
    PySpin = None

try:
    from harvesters.core import Harvester
except ImportError:
    Harvester = None


# possible locations of the Spinnaker GenTL producer (used by harvesters)
SPINNAKER_CTI_PATTERNS = [
    'C:/Program Files/Teledyne/Spinnaker/cti64/*/Spinnaker_GenTL*.cti',
    'C:/Program Files/FLIR Systems/Spinnaker/cti64/*/Spinnaker_GenTL*.cti',
    'C:/Program Files/Point Grey Research/Spinnaker/cti64/*/Spinnaker_GenTL*.cti',
]


def findSpinnakerCTI() -> str:
    """Returns the path of the Spinnaker GenTL producer ('' if not found)"""

    for pattern in SPINNAKER_CTI_PATTERNS:
        files = sorted(glob(pattern))
        if files:
            return files[-1]
    return ''


def availableBackend() -> str:
    """Returns the name of the camera backend that can be used ('pyspin', 'harvesters' or '' if none)"""

    if PySpin is not None:
        return 'pyspin'
    if Harvester is not None and findSpinnakerCTI():
        return 'harvesters'
    return ''


def backendHelp() -> str:
    """Explains how to make real cameras available"""

    if availableBackend():
        return f'Camera backend: {availableBackend()}'
    cti = findSpinnakerCTI()
    text = 'No camera backend installed. Install either\n'
    text += '- the Spinnaker Python wrapper "spinnaker_python" (wheel from the Teledyne website, must match the Spinnaker and Python version) or\n'
    text += '- "pip install harvesters"'
    text += f' (uses the installed Spinnaker GenTL producer: {cti})' if cti else ' together with the Spinnaker SDK'
    return text


def listCameras() -> list[tuple[str, str]]:
    """
    Returns the connected cameras as list of (camera id, description), an entry without id if there is none.
    The camera id is the serial number (PySpin) or the index (harvesters).
    """

    cameras = []
    backend = availableBackend()
    try:
        if backend == 'pyspin':
            system = PySpin.System.GetInstance()
            camera_list = system.GetCameras()
            try:
                for i in range(camera_list.GetSize()):
                    camera = camera_list.GetByIndex(i)
                    node_map = camera.GetTLDeviceNodeMap()
                    serial = PySpin.CStringPtr(node_map.GetNode('DeviceSerialNumber')).GetValue()
                    model = PySpin.CStringPtr(node_map.GetNode('DeviceModelName')).GetValue()
                    cameras.append((str(serial), f'{model} (S/N {serial})'))
                    del camera
            finally:
                camera_list.Clear()
                system.ReleaseInstance()

        elif backend == 'harvesters':
            harvester = Harvester()
            harvester.add_file(findSpinnakerCTI())
            harvester.update()
            for i, info in enumerate(harvester.device_info_list):
                model = getattr(info, 'model', 'Camera')
                serial = getattr(info, 'serial_number', str(i))
                cameras.append((str(i), f'{model} (S/N {serial})'))
            harvester.reset()

    except Exception as error:
        GlobalConf.logger.error(f'Camera: listing cameras with backend "{backend}" failed: {error}')

    return cameras or [('', 'None')]


class CameraConnection:
    """
    Connection to one camera

    :param camera_id: serial number (PySpin) or index (harvesters)
    :param timeout: timeout for grabbing an image in ms
    """

    def __init__(self, camera_id: str, timeout: int = 2000):
        self.camera_id = str(camera_id)
        self.timeout = timeout
        self.backend = availableBackend()

        self.acquiring = False

        # PySpin
        self._system = None
        self._camera_list = None
        self._camera = None

        # harvesters
        self._harvester = None
        self._acquirer = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()

    # ------------------------------------------------------------------ connection
    def open(self):
        """Opens the connection (raises ConnectionError if not possible)"""

        if not self.backend:
            raise ConnectionError(backendHelp())

        if not self.camera_id:
            raise ConnectionError('There is no camera available')

        try:
            if self.backend == 'pyspin':
                self._system = PySpin.System.GetInstance()
                self._camera_list = self._system.GetCameras()
                camera = self._camera_list.GetBySerial(self.camera_id)
                if camera is None or not camera.IsValid():
                    raise ConnectionError(f'Camera with serial number "{self.camera_id}" not found')
                self._camera = camera
                self._camera.Init()
                self._camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
                # manual exposure and gain, so the values of the GUI are used
                self._camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                self._camera.GainAuto.SetValue(PySpin.GainAuto_Off)
                # 8/16 bit mono images if possible
                try:
                    self._camera.PixelFormat.SetValue(PySpin.PixelFormat_Mono16)
                except PySpin.SpinnakerException:
                    pass
                # always the newest image (default "OldestFirst" returns old buffered images -> lag)
                try:
                    handling = PySpin.CEnumerationPtr(self._camera.GetTLStreamNodeMap().GetNode('StreamBufferHandlingMode'))
                    handling.SetIntValue(handling.GetEntryByName('NewestOnly').GetValue())
                except PySpin.SpinnakerException:
                    pass

            elif self.backend == 'harvesters':
                self._harvester = Harvester()
                self._harvester.add_file(findSpinnakerCTI())
                self._harvester.update()
                index = int(self.camera_id)
                create = getattr(self._harvester, 'create', None) or getattr(self._harvester, 'create_image_acquirer')
                self._acquirer = create(index)
                node_map = self._acquirer.remote_device.node_map
                for name, value in [('ExposureAuto', 'Off'), ('GainAuto', 'Off'), ('AcquisitionMode', 'Continuous')]:
                    try:
                        getattr(node_map, name).value = value
                    except Exception:
                        pass
                # always the newest image (default "OldestFirst" returns old buffered images -> lag)
                try:
                    self._acquirer.data_streams[0].node_map.StreamBufferHandlingMode.value = 'NewestOnly'
                except Exception as error:
                    GlobalConf.logger.info(f'Camera: could not set the stream buffer handling mode: {error}')

        except ConnectionError:
            self.close()
            raise
        except Exception as error:
            self.close()
            raise ConnectionError(f'Could not open camera "{self.camera_id}" ({self.backend}): {error}')

        return self

    def close(self):
        """Closes the connection"""

        try:
            self.stopAcquisition()
        except Exception:
            pass

        if self.backend == 'pyspin':
            try:
                if self._camera is not None:
                    self._camera.DeInit()
            except Exception:
                pass
            self._camera = None
            if self._camera_list is not None:
                self._camera_list.Clear()
                self._camera_list = None
            if self._system is not None:
                self._system.ReleaseInstance()
                self._system = None

        elif self.backend == 'harvesters':
            try:
                if self._acquirer is not None:
                    self._acquirer.destroy()
            except Exception:
                pass
            self._acquirer = None
            if self._harvester is not None:
                self._harvester.reset()
                self._harvester = None

    def identification(self) -> str:
        """Returns model and serial number"""

        if self.backend == 'pyspin' and self._camera is not None:
            return f'{self._camera.TLDevice.DeviceModelName.GetValue()} (S/N {self._camera.TLDevice.DeviceSerialNumber.GetValue()})'
        if self.backend == 'harvesters' and self._acquirer is not None:
            info = self._acquirer.remote_device.node_map
            return f'{info.DeviceModelName.value} (S/N {info.DeviceSerialNumber.value})'
        return self.camera_id

    # ------------------------------------------------------------------ parameters
    def _node(self, name: str):
        """Returns node of the harvesters node map"""
        return getattr(self._acquirer.remote_device.node_map, name)

    def setExposure(self, exposure: float):
        """Sets the exposure time in µs (clipped to the allowed range)"""

        minimum, maximum = self.getExposureRange()
        exposure = float(np.clip(exposure, minimum, maximum))
        if self.backend == 'pyspin':
            self._camera.ExposureTime.SetValue(exposure)
        elif self.backend == 'harvesters':
            self._node('ExposureTime').value = exposure

    def getExposure(self) -> float:
        """Returns the exposure time in µs"""

        if self.backend == 'pyspin':
            return float(self._camera.ExposureTime.GetValue())
        return float(self._node('ExposureTime').value)

    def getExposureRange(self) -> tuple[float, float]:
        """Returns (minimum, maximum) of the exposure time in µs"""

        if self.backend == 'pyspin':
            return float(self._camera.ExposureTime.GetMin()), float(self._camera.ExposureTime.GetMax())
        node = self._node('ExposureTime')
        return float(node.min), float(node.max)

    def setGain(self, gain: float):
        """Sets the gain in dB (clipped to the allowed range)"""

        minimum, maximum = self.getGainRange()
        gain = float(np.clip(gain, minimum, maximum))
        if self.backend == 'pyspin':
            self._camera.Gain.SetValue(gain)
        elif self.backend == 'harvesters':
            self._node('Gain').value = gain

    def getGain(self) -> float:
        """Returns the gain in dB"""

        if self.backend == 'pyspin':
            return float(self._camera.Gain.GetValue())
        return float(self._node('Gain').value)

    def getGainRange(self) -> tuple[float, float]:
        """Returns (minimum, maximum) of the gain in dB"""

        if self.backend == 'pyspin':
            return float(self._camera.Gain.GetMin()), float(self._camera.Gain.GetMax())
        node = self._node('Gain')
        return float(node.min), float(node.max)

    def getMaximumValue(self) -> int:
        """Returns the maximum pixel value (saturation) of the current pixel format"""

        if self.backend == 'pyspin':
            try:
                return 65535 if 'Mono16' in self._camera.PixelFormat.GetCurrentEntry().GetSymbolic() else 255
            except Exception:
                return 65535
        if self.backend == 'harvesters':
            try:
                return 65535 if '16' in str(self._node('PixelFormat').value) else 255
            except Exception:
                return 65535
        return 4095

    # ------------------------------------------------------------------ acquisition
    def startAcquisition(self):
        """Starts the continuous acquisition"""

        if self.acquiring:
            return
        if self.backend == 'pyspin':
            self._camera.BeginAcquisition()
        elif self.backend == 'harvesters':
            self._acquirer.start()
        self.acquiring = True

    def stopAcquisition(self):
        """Stops the acquisition"""

        if not self.acquiring:
            return
        self.acquiring = False
        if self.backend == 'pyspin' and self._camera is not None:
            self._camera.EndAcquisition()
        elif self.backend == 'harvesters' and self._acquirer is not None:
            self._acquirer.stop()

    def grabImage(self) -> np.ndarray:
        """Returns the next image as 2D numpy array (starts the acquisition if needed)"""

        self.startAcquisition()

        if self.backend == 'pyspin':
            image = self._camera.GetNextImage(self.timeout)
            try:
                if image.IsIncomplete():
                    raise ConnectionError(f'Incomplete image (status {image.GetImageStatus()})')
                return np.array(image.GetNDArray(), copy=True)
            finally:
                image.Release()

        with self._acquirer.fetch(timeout=self.timeout / 1000) as buffer:
            component = buffer.payload.components[0]
            return np.array(component.data, copy=True).reshape(component.height, component.width)


def beamStatistics(image: np.ndarray, maximum_value: int, background_percentile: float = 10) -> dict[str, float]:
    """
    Simple beam profile statistics of an image

    :param image: 2D image
    :param maximum_value: saturation value of the camera
    :param background_percentile: percentile of the pixels used as background
    :returns: dictionary with maximum, saturation (fraction of saturated pixels), centroid x/y and rms width x/y (pixels)
    """

    image = np.asarray(image)
    maximum = float(image.max())
    saturation = float(np.count_nonzero(image >= maximum_value)) / image.size

    # background and noise from the border of the image (5 % on every side), where usually no beam is
    border = max(1, int(min(image.shape) * 0.05))
    frame = np.concatenate([image[:border].ravel(), image[-border:].ravel(), image[:, :border].ravel(), image[:, -border:].ravel()]).astype(np.float32)
    background = float(np.median(frame))
    noise = float(np.std(frame))
    if background_percentile is not None and frame.size < 10:
        background = float(np.percentile(image, background_percentile))

    # float32 and projections instead of full coordinate grids (live view: ~80 ms -> a few ms for 1440x1080)
    signal = image.astype(np.float32)
    signal -= background
    # only the spot: ignore pixels within the noise
    signal[signal < 3 * noise] = 0
    profile_x = signal.sum(axis=0, dtype=np.float64)
    profile_y = signal.sum(axis=1, dtype=np.float64)
    total = float(profile_x.sum())

    statistics = {
        'maximum': maximum,
        'saturation': saturation,
        'x': float('nan'),
        'y': float('nan'),
        'sigma_x': float('nan'),
        'sigma_y': float('nan'),
    }
    if total <= 0:
        return statistics

    # the moments of the projections are the same as the moments of the image
    x = np.arange(profile_x.size)
    y = np.arange(profile_y.size)
    cx = float((profile_x * x).sum() / total)
    cy = float((profile_y * y).sum() / total)
    statistics.update({
        'x': cx,
        'y': cy,
        'sigma_x': float(np.sqrt(max((profile_x * (x - cx) ** 2).sum() / total, 0))),
        'sigma_y': float(np.sqrt(max((profile_y * (y - cy) ** 2).sum() / total, 0))),
    })
    return statistics


def main():
    print(backendHelp())
    print('Cameras:', listCameras())
    with CameraConnection(listCameras()[0][0]) as camera:
        camera.setExposure(20000)
        image = camera.grabImage()
        print(camera.identification(), image.shape, image.dtype, beamStatistics(image, camera.getMaximumValue()))


if __name__ == '__main__':
    main()
