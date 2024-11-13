from os import path
from ctypes import c_int, c_int16, c_uint16, c_uint32, c_long, c_double, c_char_p, c_bool, create_string_buffer, byref, cdll
from enum import IntEnum


class TLPMxValues:
    """
    Class that summarizes possible values used in functions of the TLPMx class
    """

    class Attribute(IntEnum):
        SetValue = 0
        MinimumValue = 1
        MaximumValue = 2
        DefaultValue = 3

    class AdapterTypes(IntEnum):
        PhotodiodeSensor = 1
        ThermopileSensor = 2
        PyroelectricSensor = 3
        QuadrantSensor = 4

    class PowerUnit(IntEnum):
        Watt = 0
        dBm = 1

    class AnalogRoute(IntEnum):
        RoutePur = 0
        RouteCBA = 1
        RouteCMA = 2

    class I2C(IntEnum):
        Intermediate = 0
        Slow = 1
        Fast = 2

    class FanMode(IntEnum):
        Off = 0
        Full = 1
        OpenLoop = 2
        ClosedLoop = 3
        TemperatureControl = 4

    class FanTemperatureSource(IntEnum):
        Head = 0
        ExternalNTC = 1

    class Registers(IntEnum):
        ServiceRequestEnable = 1
        StandardEventEnable = 3
        OperationEventEnable = 6
        OperationPositiveTransition = 7
        OperationNegativeTransition = 8
        QuestionableEventEnable = 11
        QuestionablePositiveTransition = 12
        QuestionableNegativeTransition = 13
        MeasurementEventEnable = 16
        MeasurementPositiveTransition = 17
        MeasurementNegativeTransition = 18
        AuxiliaryEventEnable = 21
        AuxiliaryPositiveTransition = 22
        AuxiliaryNegativeTransition = 23

    class LineFrequency(IntEnum):
        Frequency50 = 50
        Frequency60 = 60

    class FrequencyMode(IntEnum):
        CW = 0
        Peak = 1


class TLPMxConnection:
    """
    Class for communication with the TLPMx driver, which is responsible for communication with the Thorlabs Powermeters

    :param resource_name: name of the resource or None
    :param id_query: queries the specific resource
    :param reset_device: resets the device
    :param dll_path: path to the driver *.dll file
    :param dll_name: name of the driver *.dll file
    :param encoding: encoding used on strings, returns will always be in bytearrays
    """

    dll_path_list = [
        # list where drivers might be stored
        'C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin',
        'C:\\Program Files\\IVI Foundation\\VISA\\WinNT\\Bin',
        'C:\\Program Files (x86)\\IVI Foundation\\VISA\\Win64\\Bin',
        'C:\\Program Files (x86)\\IVI Foundation\\VISA\\WinNT\\Bin',
    ]

    dll_name_list = {
        # standard names of drivers for different architectures
        32: 'TLPMX_32.dll',
        64: 'TLPMX_64.dll'
    }

    def __init__(
        self,
        resource_name: bytearray | None = None,
        id_query: bool = False,
        reset_device: bool = False,
        dll_path: str | None = None,
        dll_name: str | None = None,
        dll_system: int = 64,
        encoding: str = 'utf-8'
    ):
        if dll_name is None:
            self.dll_name = self.dll_name_list.get(dll_system, None)
            if self.dll_name is None:
                raise AttributeError(f'dll_system "{dll_system}" is not supported. Supported are dll_systems: {self.dll_name_list.keys()}')
        else:
            self.dll_name = dll_name

        self.dll = None
        if dll_path is None:
            for dll_path_list in self.dll_path_list:
                try:
                    self.dll = cdll.LoadLibrary(path.join(dll_path_list, self.dll_name))
                    break
                except (FileNotFoundError, OSError):
                    pass
        else:
            self.dll = cdll.LoadLibrary(path.join(dll_path, self.dll_name))

        if self.dll is None:
            raise FileNotFoundError(f'path to dll "{self.dll_name}" could not be found')

        self.devSession = c_long()
        self.devSession.value = 0

        self.resource_name = resource_name
        self.id_query = id_query
        self.reset_device = reset_device
        self.encoding = encoding

        if self.resource_name is not None:
            if not isinstance(self.resource_name, bytearray) and not isinstance(self.resource_name, bytes):
                raise AttributeError(f'resource_name must be of <class "bytearray">, <class "bytes"> or None. Got {type(self.resource_name)}')
            result = self.dll.TLPMX_init(
                create_string_buffer(self.resource_name),
                c_bool(self.id_query),
                c_bool(self.reset_device),
                byref(self.devSession)
            )
            self.checkError(result)

    def __enter__(self):
        """Enter connection"""
        return self.open()

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Closes connection"""
        self.close()

    def open(self):
        """Opens the connection"""
        return self

    def writeRaw(self, command: str):
        """Writes directly to the instrument"""
        result = self.dll.TLPMX_writeRaw(self.devSession, c_char_p(command.encode(self.encoding)))
        self.checkError(result)

    def readRaw(self, size: int = 1024) -> tuple[str, int]:
        """Reads directly from the instrument"""
        buffer = create_string_buffer(1024)
        return_count = c_uint32(0)
        result = self.dll.TLPMX_readRaw(self.devSession, buffer, c_uint32(size), byref(return_count))
        self.checkError(result)
        return c_char_p(buffer.raw).value.decode(self.encoding), return_count.value

    def queryRaw(self, command: str, size: int = 1024) -> tuple[str, int]:
        """Directly queries the instrument"""
        self.writeRaw(command)
        return self.readRaw(size)

    def checkError(self, status: int):
        if status < 0:
            msg = create_string_buffer(1024)
            self.dll.TLPMX_errorMessage(self.devSession, c_int(status), msg)
            raise NameError(c_char_p(msg.raw).value)
        return status

    def findResources(self) -> int:
        """Returns the number of resources found"""
        resource_count = c_uint32(0)
        result = self.dll.TLPMX_findRsrc(self.devSession, byref(resource_count))
        try:
            self.checkError(result)
        except NameError:
            return 0
        return resource_count.value

    def getResourceName(self, index: int) -> bytearray:
        """Returns the name of the provided resource id"""
        resource_name = create_string_buffer(1024)
        result = self.dll.TLPMX_getRsrcName(self.devSession, c_uint32(index), resource_name)
        self.checkError(result)
        return c_char_p(resource_name.raw).value

    def getResourceInfo(self, index: int) -> tuple[bytearray, bytearray, bytearray, int]:
        """Returns info about the provided resource id"""
        model_name = create_string_buffer(1024)
        serial_number = create_string_buffer(1024)
        manufacturer = create_string_buffer(1024)
        device_available = c_int16(0)
        result = self.dll.TLPMX_getRsrcInfo(
            self.devSession,
            c_uint32(index),
            model_name,
            serial_number,
            manufacturer,
            byref(device_available)
        )
        self.checkError(result)
        return c_char_p(model_name.raw).value, c_char_p(serial_number.raw).value, c_char_p(manufacturer.raw).value, device_available.value

    def writeRegister(self, register: TLPMxValues.Registers | int, value: int):
        """Writes the content of any writable instrument register"""
        result = self.dll.TLPMX_writeRegister(self.devSession, c_int16(register), c_int16(value))
        self.checkError(result)

    def readRegister(self, register: TLPMxValues.Registers | int) -> int:
        """Reads the content of any readable instrument register"""
        value = c_int16(0)
        result = self.dll.TLPMX_readRegister(self.devSession, c_int16(register), byref(value))
        self.checkError(result)
        return value.value

    def presetRegister(self):
        """Presets all status registers to default"""
        result = self.dll.TLPMX_presetRegister(self.devSession)
        self.checkError(result)

    def sendNTPRequest(self, time_mode: int, time_zone: int) -> bytearray:
        """Set the system date and time of the powermeter"""
        ip_address = create_string_buffer(1024)
        result = self.dll.TLPMX_sendNTPRequest(self.devSession, c_int16(time_mode), c_int16(time_zone), ip_address)
        self.checkError(result)
        return c_char_p(ip_address.raw).value

    def setTime(self, year: int, month: int, day: int, hour: int, minute: int, second: int):
        """Set the system date and time of the powermeter"""
        result = self.dll.TLPMX_setTime(self.devSession, c_int16(year), c_int16(month), c_int16(day), c_int16(hour), c_int16(minute), c_int16(second))
        self.checkError(result)

    def getTime(self) -> tuple[int, int, int, int, int, int]:
        """Returns the system date and time of the powermeter (year, month, day, hour, minute, second)"""
        year = c_int16(0)
        month = c_int16(0)
        day = c_int16(0)
        hour = c_int16(0)
        minute = c_int16(0)
        second = c_int16(0)
        result = self.dll.TLPMX_getTime(self.devSession, byref(year), byref(month), byref(day), byref(hour), byref(minute), byref(second))
        self.checkError(result)
        return year.value, month.value, day.value, hour.value, minute.value, second.value

    def setSummertime(self, time_mode: int):
        """Set the clock to summertime"""
        result = self.dll.TLPMX_setSummertime(self.devSession, c_int16(time_mode))
        self.checkError(result)

    def getSummertime(self) -> int:
        """Returns if the device uses the summertime"""
        time_mode = c_int16(0)
        result = self.dll.TLPMX_getSummertime(self.devSession, byref(time_mode))
        self.checkError(result)
        return time_mode.value

    def setLineFrequency(self, line_frequency: TLPMxValues.LineFrequency):
        """Selects the line frequency"""
        result = self.dll.TLPMX_setLineFrequency(self.devSession, c_int16(line_frequency))
        self.checkError(result)

    def getLineFrequency(self) -> int:
        """Returns the selected line frequency"""
        line_frequency = c_int16(0)
        result = self.dll.TLPMX_getLineFrequency(self.devSession, byref(line_frequency))
        self.checkError(result)
        return line_frequency.value

    def getBatteryVoltage(self) -> float:
        """Return the battery voltage readings from the instrument"""
        voltage = c_double(0)
        result = self.dll.TLPMX_getBatteryVoltage(self.devSession, byref(voltage))
        self.checkError(result)
        return voltage.value

    def setDispBrightness(self, value: float):
        """Set the display brightness"""
        result = self.dll.TLPMX_setDispBrightness(self.devSession, c_double(value))
        self.checkError(result)

    def getDispBrightness(self) -> float:
        """Returns the display brightness"""
        value = c_double(0)
        result = self.dll.TLPMX_getDispBrightness(self.devSession, byref(value))
        self.checkError(result)
        return value.value

    def setDispContrast(self, value: float):
        """Set the display contrast of a PM100D"""
        result = self.dll.TLPMX_setDispContrast(self.devSession, c_double(value))
        self.checkError(result)

    def getDispContrast(self) -> float:
        """Returns the display contrast of a PM100D"""
        value = c_double(0)
        result = self.dll.TLPMX_getDispContrast(self.devSession, byref(value))
        self.checkError(result)
        return value.value

    def beep(self):
        """Plays a beep sound"""
        result = self.dll.TLPMX_beep(self.devSession)
        self.checkError(result)

    def setInputFilterState(self, input_filter_state: int, channel: int = 1):
        """Set the instrument's photodiode input filter state"""
        result = self.dll.TLPMX_setInputFilterState(self.devSession, c_int16(input_filter_state), c_uint16(channel))
        self.checkError(result)

    def getInputFilterState(self, channel: int = 1) -> int:
        """Returns the instrument's photodiode input filter state"""
        input_filter_state = c_int16(0)
        result = self.dll.TLPMX_getInputFilterState(self.devSession, byref(input_filter_state), c_uint16(channel))
        self.checkError(result)
        return input_filter_state.value

    def setAccelerationState(self, acceleration_state: int, channel: int = 1):
        """Sets the thermopile acceleration state"""
        result = self.dll.TLPMX_setAccelState(self.devSession, c_int16(acceleration_state), c_uint16(channel))
        self.checkError(result)

    def getAccelerationState(self, channel: int = 1) -> int:
        """Returns the thermopile acceleration state"""
        acceleration_state = c_int16(0)
        result = self.dll.TLPMX_getAccelState(self.devSession, byref(acceleration_state), c_uint16(channel))
        self.checkError(result)
        return acceleration_state.value

    def setAccelerationAutoMode(self, acceleration_auto_mode: int, channel: int = 1):
        """Sets the thermopile acceleration auto mode"""
        result = self.dll.TLPMX_setAccelMode(self.devSession, c_int16(acceleration_auto_mode), c_uint16(channel))
        self.checkError(result)

    def getAccelerationAutoMode(self, channel: int = 1):
        """Returns the thermopile acceleration mode"""
        acceleration_auto_mode = c_int16(0)
        result = self.dll.TLPMX_getAccelMode(self.devSession, byref(acceleration_auto_mode), c_uint16(channel))
        self.checkError(result)
        return acceleration_auto_mode.value

    def setAccelerationTimeConstant(self, acceleration_time_constant: float, channel: int = 1):
        """Set the thermopile acceleration time constant in seconds [s]"""
        result = self.dll.TLPMX_setAccelTau(self.devSession, c_double(acceleration_time_constant), c_uint16(channel))
        self.checkError(result)

    def getAccelerationTimeConstant(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the thermopile acceleration time constant in seconds [s]"""
        acceleration_time_constant = c_double(0)
        result = self.dll.TLPMX_getAccelTau(self.devSession, c_int16(attribute), byref(acceleration_time_constant), c_uint16(channel))
        self.checkError(result)
        return acceleration_time_constant.value

    def setInputAdapterType(self, adapter_type: TLPMxValues.AdapterTypes, channel: int = 1):
        """Set the sensor type to assume for custom sensors without calibration data memory connected to the instrument"""
        result = self.dll.TLPMX_setInputAdapterType(self.devSession, c_int16(adapter_type), c_uint16(channel))
        self.checkError(result)

    def getInputAdapterType(self, channel: int = 1) -> int:
        """Returns the assumed sensor type for custom sensors without calibration data memory connected to the instrument"""
        adapter_type = c_int16(0)
        result = self.dll.TLPMX_getInputAdapterType(self.devSession, byref(adapter_type), c_uint16(channel))
        self.checkError(result)
        return adapter_type.value

    def setAverageTime(self, average_time: float, channel: int = 1):
        """Set the average time for measurement value generation"""
        result = self.dll.TLPMX_setAvgTime(self.devSession, c_double(average_time), c_uint16(channel))
        self.checkError(result)

    def getAverageTime(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the average time for measurement value generation"""
        average_time = c_double(0)
        result = self.dll.TLPMX_getAvgTime(self.devSession, c_int16(attribute), byref(average_time), c_uint16(channel))
        self.checkError(result)
        return average_time.value

    def setAverageCount(self, average_count: int, channel: int = 1):
        """Set the average count for measurement value generation"""
        result = self.dll.TLPMX_setAvgCnt(self.devSession, c_int16(average_count), c_uint16(channel))
        self.checkError(result)

    def getAverageCount(self, channel: int = 1) -> int:
        """Returns the average count for measurement value generation"""
        average_count = c_int16(0)
        result = self.dll.TLPMX_getAvgCnt(self.devSession, byref(average_count), c_uint16(channel))
        self.checkError(result)
        return average_count.value

    def setAttenuation(self, attenuation: float, channel: int = 1):
        """Set the input attenuation"""
        result = self.dll.TLPMX_setAttenuation(self.devSession, c_double(attenuation), c_uint16(channel))
        self.checkError(result)

    def getAttenuation(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the input attenuation"""
        attenuation = c_double(0)
        result = self.dll.TLPMX_getAttenuation(self.devSession, c_int16(attribute), byref(attenuation), c_uint16(channel))
        self.checkError(result)
        return attenuation.value

    def startDarkAdjust(self, channel: int = 1):
        """Starts the dark current/zero offset adjustment procedure"""
        result = self.dll.TLPMX_startDarkAdjust(self.devSession, c_uint16(channel))
        self.checkError(result)

    def cancelDarkAdjust(self, channel: int = 1):
        """Cancels a running dark current/zero offset adjustment procedure"""
        result = self.dll.TLPMX_cancelDarkAdjust(self.devSession, c_uint16(channel))
        self.checkError(result)

    def getDarkAdjustState(self, channel: int = 1) -> int:
        """Returns the state of a dark current/zero offset adjustment procedure previously initiated by <Start Dark Adjust>"""
        state = c_int16(0)
        result = self.dll.TLPMX_getDarkAdjustState(self.devSession, byref(state), c_uint16(channel))
        self.checkError(result)
        return state.value

    def setDarkOffset(self, dark_offset: float, channel: int = 1):
        """Set the dark/zero offset"""
        result = self.dll.TLPMX_setDarkOffset(self.devSession, c_double(dark_offset), c_uint16(channel))
        self.checkError(result)

    def getDarkOffset(self, channel: int = 1) -> float:
        """Returns the dark/zero offset"""
        dark_offset = c_double(0)
        result = self.dll.TLPMX_getDarkOffset(self.devSession, byref(dark_offset), c_uint16(channel))
        self.checkError(result)
        return dark_offset.value

    def setBeamDiameter(self, beam_diameter: float, channel: int = 1):
        """Sets the users beam diameter in millimeter [mm]"""
        result = self.dll.TLPMX_setBeamDia(self.devSession, c_double(beam_diameter), c_uint16(channel))
        self.checkError(result)

    def getBeamDiameter(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the users beam diameter in millimeter [mm]"""
        beam_diameter = c_double(0)
        result = self.dll.TLPMX_getBeamDia(self.devSession, c_int16(attribute), byref(beam_diameter), c_uint16(channel))
        self.checkError(result)
        return beam_diameter.value

    def setWavelength(self, wavelength: float, channel: int = 1):
        """Sets the users wavelength in nanometer [nm]"""
        result = self.dll.TLPMX_setWavelength(self.devSession, c_double(wavelength), c_uint16(channel))
        self.checkError(result)

    def getWavelength(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the users wavelength in nanometer [nm]"""
        wavelength = c_double(0)
        result = self.dll.TLPMX_getWavelength(self.devSession, c_int16(attribute), byref(wavelength), c_uint16(channel))
        self.checkError(result)
        return wavelength.value

    def setPhotodiodeResponsivity(self, responsivity: float, channel: int = 1):
        """Sets the photodiode responsivity in ampere per watt [A/W]"""
        result = self.dll.TLPMX_setPhotodiodeResponsivity(self.devSession, c_double(responsivity), c_uint16(channel))
        self.checkError(result)

    def getPhotodiodeResponsivity(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the photodiode responsivity in ampere per watt [A/W]"""
        responsivity = c_double(0)
        result = self.dll.TLPMX_getPhotodiodeResponsivity(self.devSession, c_int16(attribute), byref(responsivity), c_uint16(channel))
        self.checkError(result)
        return responsivity.value

    def setThermopileResponsivity(self, responsivity: float, channel: int = 1):
        """Sets the thermopile responsivity in volt per watt [V/W]"""
        result = self.dll.TLPMX_setThermopileResponsivity(self.devSession, c_double(responsivity), c_uint16(channel))
        self.checkError(result)

    def getThermopileResponsivity(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the thermopile responsivity in volt per watt [V/W]"""
        responsivity = c_double(0)
        result = self.dll.TLPMX_getThermopileResponsivity(self.devSession, c_int16(attribute), byref(responsivity), c_uint16(channel))
        self.checkError(result)
        return responsivity.value

    def setPyrosensorResponsivity(self, responsivity: float, channel: int = 1):
        """Sets the pyrosensor responsivity in volt per joule [V/J]"""
        result = self.dll.TLPMX_setPyrosensorResponsivity(self.devSession, c_double(responsivity), c_uint16(channel))
        self.checkError(result)

    def getPyrosensorResponsivity(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the pyrosensor responsivity in volt per joule [V/J]"""
        responsivity = c_double(0)
        result = self.dll.TLPMX_getPyrosensorResponsivity(self.devSession, c_int16(attribute), byref(responsivity), c_uint16(channel))
        self.checkError(result)
        return responsivity.value

    def setCurrentAutoRange(self, current_auto_range_mode: int, channel: int = 1):
        """Sets the current auto range mode"""
        result = self.dll.TLPMX_setCurrentAutoRange(self.devSession, c_int16(current_auto_range_mode), c_uint16(channel))
        self.checkError(result)

    def getCurrentAutoRange(self, channel: int = 1) -> int:
        """Returns the current auto range mode"""
        current_auto_range_mode = c_int16(0)
        result = self.dll.TLPMX_getCurrentAutorange(self.devSession, byref(current_auto_range_mode), c_uint16(channel))
        self.checkError(result)
        return current_auto_range_mode.value

    def setCurrentRange(self, current_to_measure: float, channel: int = 1):
        """Sets the sensor's current range"""
        result = self.dll.TLPMX_setCurrentRange(self.devSession, c_double(current_to_measure), c_uint16(channel))
        self.checkError(result)

    def getCurrentRange(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the actual current range value"""
        current_to_measure = c_double(0)
        result = self.dll.TLPMX_getCurrentRange(self.devSession, c_int16(attribute), byref(current_to_measure), c_uint16(channel))
        self.checkError(result)
        return current_to_measure.value

    def getCurrentRanges(self, current_value, channel: int = 1) -> int:
        """Returns the actual voltage range value"""
        count = c_uint16(0)
        result = self.dll.TLPMX_getCurrentRanges(self.devSession, current_value, byref(count), c_uint16(channel))
        self.checkError(result)
        return count.value

    def setCurrentRangeSearch(self, channel: int = 1):
        """Sets the actual voltage range value"""
        result = self.dll.TLPMX_setCurrentRangeSearch(self.devSession, c_uint16(channel))
        self.checkError(result)

    def setCurrentReference(self, current_reference_value: float, channel: int = 1):
        """Sets the current reference value"""
        result = self.dll.TLPMX_setCurrentRef(self.devSession, c_double(current_reference_value), c_uint16(channel))
        self.checkError(result)

    def getCurrentReference(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the current reference value"""
        current_reference_value = c_double(0)
        result = self.dll.TLPMX_getCurrentRef(self.devSession, c_int16(attribute), byref(current_reference_value), c_uint16(channel))
        self.checkError(result)
        return current_reference_value.value

    def setCurrentReferenceState(self, current_reference_state: int, channel: int = 1):
        """Sets the current reference state"""
        result = self.dll.TLPMX_setCurrentRefState(self.devSession, c_int16(current_reference_state), c_uint16(channel))
        self.checkError(result)

    def getCurrentReferenceState(self, channel: int = 1) -> int:
        """Returns the current reference state"""
        current_reference_state = c_int16(0)
        result = self.dll.TLPMX_getCurrentRefState(self.devSession, byref(current_reference_state), c_uint16(channel))
        self.checkError(result)
        return current_reference_state.value

    def setEnergyRange(self, energy: float, channel: int = 1):
        """Sets the pyro sensor's energy range"""
        result = self.dll.TLPMX_setEnergyRange(self.devSession, c_double(energy), c_uint16(channel))
        self.checkError(result)

    def getEnergyRange(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the pyro sensor's energy range"""
        energy = c_double(0)
        result = self.dll.TLPMX_getEnergyRange(self.devSession, c_int16(attribute), byref(energy), c_uint16(channel))
        self.checkError(result)
        return energy.value

    def setEnergyReference(self, energy_reference_value: float, channel: int = 1):
        """Sets the pyro sensor's energy reference value"""
        result = self.dll.TLPMX_setEnergyRef(self.devSession, c_double(energy_reference_value), c_uint16(channel))
        self.checkError(result)

    def getEnergyReference(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the specified pyro sensor's energy reference value"""
        energy_reference_value = c_double(0)
        result = self.dll.TLPMX_getEnergyRef(self.devSession, c_int16(attribute), byref(energy_reference_value), c_uint16(channel))
        self.checkError(result)
        return energy_reference_value.value

    def setEnergyReferenceState(self, energy_reference_state: int, channel: int = 1):
        """Sets the instrument's energy reference state"""
        result = self.dll.TLPMX_setEnergyRefState(self.devSession, c_int16(energy_reference_state), c_uint16(channel))
        self.checkError(result)

    def getEnergyReferenceState(self, channel: int = 1) -> int:
        """Returns the instrument's energy reference state"""
        energy_reference_state = c_int16(0)
        result = self.dll.TLPMX_getEnergyRefState(self.devSession, byref(energy_reference_state), c_uint16(channel))
        self.checkError(result)
        return energy_reference_state.value

    def getFrequencyRange(self, channel: int = 1) -> tuple[float, float]:
        """Returns the instruments frequency measurement range"""
        frequency_low = c_double(0)
        frequency_high = c_double(0)
        result = self.dll.TLPMX_getFreqRange(self.devSession, byref(frequency_low), byref(frequency_high), c_uint16(channel))
        self.checkError(result)
        return frequency_low.value, frequency_high.value

    def setFrequencyMode(self, frequency_mode: TLPMxValues.FrequencyMode, channel: int = 1):
        """Sets the instruments frequency measurement mode. Only for photodiodes"""
        result = self.dll.TLPMX_setFreqMode(self.devSession, c_uint16(frequency_mode), c_uint16(channel))
        self.checkError(result)

    def getFrequencyMode(self, channel: int = 1) -> int:
        """Returns the instruments frequency measurement mode"""
        frequency_mode = c_uint16(0)
        result = self.dll.TLPMX_getFreqMode(self.devSession, byref(frequency_mode), c_uint16(channel))
        self.checkError(result)
        return frequency_mode.value

    def setPowerAutoRange(self, power_auto_range_mode: int, channel: int = 1):
        """Sets the power auto range mode"""
        result = self.dll.TLPMX_setPowerAutoRange(self.devSession, c_int16(power_auto_range_mode), c_uint16(channel))
        self.checkError(result)

    def getPowerAutoRange(self, channel: int = 1) -> int:
        """Returns the power auto range mode"""
        power_auto_range_mode = c_int16(0)
        result = self.dll.TLPMX_getPowerAutorange(self.devSession, byref(power_auto_range_mode), c_uint16(channel))
        self.checkError(result)
        return power_auto_range_mode.value

    def setPowerRange(self, power_range: float, channel: int = 1):
        """Sets the sensor's power range"""
        result = self.dll.TLPMX_setPowerRange(self.devSession, c_double(power_range), c_uint16(channel))
        self.checkError(result)

    def getPowerRange(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the actual power range value"""
        power_range = c_double(0)
        result = self.dll.TLPMX_getPowerRange(self.devSession, c_int16(attribute), byref(power_range), c_uint16(channel))
        self.checkError(result)
        return power_range.value

    def setPowerReference(self, power_reference_value: float, channel: int = 1):
        """Sets the power reference value"""
        result = self.dll.TLPMX_setPowerRef(self.devSession, c_double(power_reference_value), c_uint16(channel))
        self.checkError(result)

    def getPowerReference(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the power reference value"""
        power_reference_value = c_double(0)
        result = self.dll.TLPMX_getPowerRef(self.devSession, c_int16(attribute), byref(power_reference_value), c_uint16(channel))
        self.checkError(result)
        return power_reference_value.value

    def setPowerReferenceState(self, power_reference_state: int, channel: int = 1):
        """Sets the power reference state"""
        result = self.dll.TLPMX_setPowerRefState(self.devSession, c_int16(power_reference_state), c_uint16(channel))
        self.checkError(result)

    def getPowerReferenceState(self, channel: int = 1) -> int:
        """Returns the power reference state"""
        power_reference_state = c_int16(0)
        result = self.dll.TLPMX_getPowerRefState(self.devSession, byref(power_reference_state), c_uint16(channel))
        self.checkError(result)
        return power_reference_state.value

    def setPowerUnit(self, power_unit: TLPMxValues.PowerUnit, channel: int = 1):
        """Sets the unit of the power value"""
        result = self.dll.TLPMX_setPowerUnit(self.devSession, c_int16(power_unit), c_uint16(channel))
        self.checkError(result)

    def getPowerUnit(self, channel: int = 1) -> TLPMxValues.PowerUnit:
        """Returns the unit of the power value"""
        power_unit = c_int16(0)
        result = self.dll.TLPMX_getPowerUnit(self.devSession, byref(power_unit), c_uint16(channel))
        self.checkError(result)
        return power_unit.value

    def getPowerCalibrationPointsInformation(self, index: int, channel: int = 1) -> tuple[bytearray, bytearray, int, bytearray, int]:
        """Queries the customer adjustment header (serial number, calibration date, calibration points count, author, sensor position)"""
        serial_number = create_string_buffer(1024)
        calibration_date = create_string_buffer(1024)
        calibration_points_count = c_uint16(0)
        author = create_string_buffer(1024)
        sensor_position = c_uint16(0)
        result = self.dll.TLPMX_getPowerCalibrationPointsInformation(self.devSession, c_uint16(index), serial_number, calibration_date, byref(calibration_points_count), author, byref(sensor_position), c_uint16(channel))
        self.checkError(result)
        return c_char_p(serial_number.raw).value, c_char_p(calibration_date.raw).value, calibration_points_count.value, c_char_p(author.raw).value, sensor_position.value

    def getPowerCalibrationPointsState(self, index: int, channel: int = 1) -> int:
        """Queries the state if the power calibration of this sensor is activated"""
        state = c_int16(0)
        result = self.dll.TLPMX_getPowerCalibrationPointsState(self.devSession, c_uint16(index), byref(state), c_uint16(channel))
        self.checkError(result)
        return state.value

    def setPowerCalibrationPointsState(self, index: int, state: int, channel: int = 1):
        """Activates/inactivates the power calibration of this sensor"""
        result = self.dll.TLPMX_setPowerCalibrationPointsState(self.devSession, c_uint16(index), c_int16(state), c_uint16(channel))
        self.checkError(result)

    def setPowerCalibrationPoints(self, index: int, point_counts: int, wavelengths, power_correction_factors, channel: int = 1):
        """Sets a list of wavelength and the corresponding power correction factor"""
        result = self.dll.TLPMX_setPowerCalibrationPoints(self.devSession, c_uint16(index), c_uint16(point_counts), wavelengths, power_correction_factors, c_uint16(channel))
        self.checkError(result)

    def getPowerCalibrationPoints(self, index: int, point_counts: int, wavelengths, power_correction_factors, sensor_position: int, channel: int = 1) -> bytearray:
        """Returns the author of wavelength and the corresponding power correction factor"""
        author = create_string_buffer(1024)
        result = self.dll.TLPMX_getPowerCalibrationPoints(self.devSession, c_uint16(index), c_uint16(point_counts), wavelengths, power_correction_factors, author, c_uint16(sensor_position), c_uint16(channel))
        self.checkError(result)
        return c_char_p(author.raw).value

    def reinitSensor(self, channel: int = 1):
        """Reinitialize the sensor"""
        result = self.dll.TLPMX_reinitSensor(self.devSession, c_uint16(channel))
        self.checkError(result)

    def setVoltageAutoRange(self, voltage_auto_range_mode: int, channel: int = 1):
        """Sets the voltage auto range mode"""
        result = self.dll.TLPMX_setVoltageAutoRange(self.devSession, c_int16(voltage_auto_range_mode), c_uint16(channel))
        self.checkError(result)

    def getVoltageAutoRange(self, channel: int = 1) -> int:
        """Returns the voltage auto range mode"""
        voltage_auto_range_mode = c_int16(0)
        result = self.dll.TLPMX_getVoltageAutorange(self.devSession, byref(voltage_auto_range_mode), c_uint16(channel))
        self.checkError(result)
        return voltage_auto_range_mode.value

    def setVoltageRange(self, voltage_range: float, channel: int = 1):
        """Sets the sensor's voltage range"""
        result = self.dll.TLPMX_setVoltageRange(self.devSession, c_double(voltage_range), c_uint16(channel))
        self.checkError(result)

    def getVoltageRange(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the actual voltage range value"""
        voltage_range = c_double(0)
        result = self.dll.TLPMX_getVoltageRange(self.devSession, c_int16(attribute), byref(voltage_range), c_uint16(channel))
        self.checkError(result)
        return voltage_range.value

    def getVoltageRanges(self, voltage_ranges, channel: int = 1):
        """Returns the actual voltage range value"""
        range_count = c_uint16(0)
        result = self.dll.TLPMX_getVoltageRanges(self.devSession, voltage_ranges, byref(range_count), c_uint16(channel))
        self.checkError(result)
        return range_count.value

    def setVoltageRangeSearch(self, channel: int = 1):
        """Sets the voltage range search"""
        result = self.dll.TLPMX_setVoltageRangeSearch(self.devSession, c_uint16(channel))
        self.checkError(result)

    def setVoltageReference(self, voltage_reference_value: float, channel: int = 1):
        """Sets the voltage reference value"""
        result = self.dll.TLPMX_setVoltageRef(self.devSession, c_double(voltage_reference_value), c_uint16(channel))
        self.checkError(result)

    def getVoltageReference(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the voltage reference value"""
        voltage_reference_value = c_double(0)
        result = self.dll.TLPMX_getVoltageRef(self.devSession, c_int16(attribute), byref(voltage_reference_value), c_uint16(channel))
        self.checkError(result)
        return voltage_reference_value.value

    def setVoltageReferenceState(self, voltage_reference_state: int, channel: int = 1):
        """Sets the voltage reference state"""
        result = self.dll.TLPMX_setVoltageRefState(self.devSession, c_int16(voltage_reference_state), c_uint16(channel))
        self.checkError(result)

    def getVoltageReferenceState(self, channel: int = 1):
        """Returns the voltage reference state"""
        voltage_reference_state = c_int16(0)
        result = self.dll.TLPMX_getVoltageRefState(self.devSession, byref(voltage_reference_state), c_uint16(channel))
        self.checkError(result)
        return voltage_reference_state.value

    def setPeakThreshold(self, peak_threshold: float, channel: int = 1):
        """Sets the peak detector threshold"""
        result = self.dll.TLPMX_setPeakThreshold(self.devSession, c_double(peak_threshold), c_uint16(channel))
        self.checkError(result)

    def getPeakThreshold(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the peak detector threshold"""
        peak_threshold = c_double(0)
        result = self.dll.TLPMX_getPeakThreshold(self.devSession, c_int16(attribute), byref(peak_threshold), c_uint16(channel))
        self.checkError(result)
        return peak_threshold.value

    def startPeakDetector(self, channel: int = 1):
        """Starts peak finder"""
        result = self.dll.TLPMX_startPeakDetector(self.devSession, c_uint16(channel))
        self.checkError(result)

    def isPeakDetectorRunning(self, channel: int = 1) -> int:
        """Tests if peak finder is active at the moment"""
        is_running = c_int16(0)
        result = self.dll.TLPMX_isPeakDetectorRunning(self.devSession, byref(is_running), c_uint16(channel))
        self.checkError(result)
        return is_running.value

    def setPeakFilter(self, peak_filter: int, channel: int = 1):
        """Sets peak filter"""
        result = self.dll.TLPMX_setPeakFilter(self.devSession, c_int16(peak_filter), c_uint16(channel))
        self.checkError(result)

    def getPeakFilter(self, channel: int = 1) -> int:
        """Gets peak filter"""
        peak_filter = c_int16(0)
        result = self.dll.TLPMX_getPeakFilter(self.devSession, byref(peak_filter), c_uint16(channel))
        self.checkError(result)
        return peak_filter.value

    def setExternalNtcParameter(self, r0_coefficient: float, beta_coefficient: float, channel: int = 1):
        """Sets the temperature calculation coefficients for the NTC sensor externally connected to the instrument (NTC IN)"""
        result = self.dll.TLPMX_setExtNtcParameter(self.devSession, c_double(r0_coefficient), c_double(beta_coefficient), c_uint16(channel))
        self.checkError(result)

    def getExternalNtcParameter(self, attribute, channel: int = 1) -> tuple[float, float]:
        """Gets the temperature calculation coefficients for the NTC sensor externally connected to the instrument (NTC IN)"""
        r0_coefficient = c_double(0)
        beta_coefficient = c_double(0)
        result = self.dll.TLPMX_getExtNtcParameter(self.devSession, c_int16(attribute), byref(r0_coefficient), byref(beta_coefficient), c_uint16(channel))
        self.checkError(result)
        return r0_coefficient.value, beta_coefficient.value

    def setFilterPosition(self, filter_position: int):
        """Sets the current filter position"""
        result = self.dll.TLPMX_setFilterPosition(self.devSession, c_int16(filter_position))
        self.checkError(result)

    def getFilterPosition(self) -> int:
        """Returns the current filter position"""
        filter_position = c_int16(0)
        result = self.dll.TLPMX_getFilterPosition(self.devSession, byref(filter_position))
        self.checkError(result)
        return filter_position.value

    def setFilterAutoMode(self, filter_auto_position_detection: int):
        """Enables / disables the automatic filter position detection"""
        result = self.dll.TLPMX_setFilterAutoMode(self.devSession, c_int16(filter_auto_position_detection))
        self.checkError(result)

    def getFilterAutoMode(self) -> int:
        """Returns if the automatic filter position detection is used"""
        filter_auto_position_detection = c_int16(0)
        result = self.dll.TLPMX_getFilterAutoMode(self.devSession, byref(filter_auto_position_detection))
        self.checkError(result)
        return filter_auto_position_detection.value

    def getAnalogOutputSlopeRange(self, channel: int = 1) -> tuple[float, float]:
        """Returns range of the responsivity in volts per watt [V/W] for the analog output (min, max)"""
        slope_min = c_double(0)
        slope_max = c_double(0)
        result = self.dll.TLPMX_getAnalogOutputSlopeRange(self.devSession, byref(slope_min), byref(slope_max), c_uint16(channel))
        self.checkError(result)
        return slope_min.value, slope_max.value

    def setAnalogOutputSlope(self, slope: float, channel: int = 1):
        """Sets the responsivity in volts per watt [V/W] for the analog output"""
        result = self.dll.TLPMX_setAnalogOutputSlope(self.devSession, c_double(slope), c_uint16(channel))
        self.checkError(result)

    def getAnalogOutputSlope(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the responsivity in volts per watt [V/W] for the analog output"""
        slope = c_double(0)
        result = self.dll.TLPMX_getAnalogOutputSlope(self.devSession, c_int16(attribute), byref(slope), c_uint16(channel))
        self.checkError(result)
        return slope.value

    def getAnalogOutputVoltageRange(self, channel: int = 1) -> tuple[float, float]:
        """Returns the range in Volt [V] of the analog output (min, max)"""
        voltage_min = c_double(0)
        voltage_max = c_double(0)
        result = self.dll.TLPMX_getAnalogOutputVoltageRange(self.devSession, byref(voltage_min), byref(voltage_max), c_uint16(channel))
        self.checkError(result)
        return voltage_min.value, voltage_max.value

    def getAnalogOutputVoltage(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> float:
        """Returns the analog output in Volt [V]"""
        voltage = c_double(0)
        result = self.dll.TLPMX_getAnalogOutputVoltage(self.devSession, c_int16(attribute), byref(voltage), c_uint16(channel))
        self.checkError(result)
        return voltage.value

    def getAnalogOutputGainRange(self, channel: int = 1) -> int:
        """Returns the analog output hub in Volt [V]"""
        gain_range_index = c_int16(0)
        result = self.dll.TLPMX_getAnalogOutputGainRange(self.devSession, byref(gain_range_index), c_uint16(channel))
        self.checkError(result)
        return gain_range_index.value

    def setAnalogOutputGainRange(self, gain_range_index: int, channel: int = 1):
        """Sets the analog output hub in Volt [V]"""
        result = self.dll.TLPMX_setAnalogOutputGainRange(self.devSession, c_int16(gain_range_index), c_uint16(channel))
        self.checkError(result)

    def getAnalogOutputRoute(self, channel: int = 1) -> bytearray:
        """Returns the analog output hub in Volt [V]"""
        route_name = create_string_buffer(1024)
        result = self.dll.TLPMX_getAnalogOutputRoute(self.devSession, route_name, c_uint16(channel))
        self.checkError(result)
        return c_char_p(route_name.raw).value

    def setAnalogOutputRoute(self, route_strategy: TLPMxValues.AnalogRoute, channel: int = 1):
        """Sets the analog output hub in Volt [V]"""
        result = self.dll.TLPMX_setAnalogOutputRoute(self.devSession, c_uint16(route_strategy), c_uint16(channel))
        self.checkError(result)

    def getPositionAnalogOutputSlopeRange(self, channel: int = 1) -> tuple[float, float]:
        """Returns range of the responsivity in volts per µm [V/µm] for the analog output (min, max)"""
        slope_min = c_double(0)
        slope_max = c_double(0)
        result = self.dll.TLPMX_getPositionAnalogOutputSlopeRange(self.devSession, byref(slope_min), byref(slope_max), c_uint16(channel))
        self.checkError(result)
        return slope_min.value, slope_max.value

    def setPositionAnalogOutputSlope(self, slope: float, channel: int = 1):
        """Sets the responsivity in volts per µm [V/µm] for the analog output"""
        result = self.dll.TLPMX_setPositionAnalogOutputSlope(self.devSession, c_double(slope), c_uint16(channel))
        self.checkError(result)

    def getPositionAnalogOutputSlope(self, attribute: TLPMxValues.Attribute, channel: int = 1):
        """Returns the responsivity in volts per µm [V/µm] for the analog output channels"""
        slope = c_double(0)
        result = self.dll.TLPMX_getPositionAnalogOutputSlope(self.devSession, c_int16(attribute), byref(slope), c_uint16(channel))
        self.checkError(result)
        return slope.value

    def getPositionAnalogOutputVoltageRange(self, channel: int = 1) -> tuple[float, float]:
        """Returns the range in Volt [V] of the analog output (min, max)"""
        voltage_min = c_double(0)
        voltage_max = c_double(0)
        result = self.dll.TLPMX_getPositionAnalogOutputVoltageRange(self.devSession, byref(voltage_min), byref(voltage_max), c_uint16(channel))
        self.checkError(result)
        return voltage_min.value, voltage_max.value

    def getPositionAnalogOutputVoltage(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> tuple[float, float]:
        """Returns the analog output in Volt [V] (x, y)-direction"""
        voltage_x = c_double(0)
        voltage_y = c_double(0)
        result = self.dll.TLPMX_getPositionAnalogOutputVoltage(self.devSession, c_int16(attribute), byref(voltage_x), byref(voltage_y), c_uint16(channel))
        self.checkError(result)
        return voltage_x.value, voltage_y.value

    def getMeasurementPinMode(self, channel: int = 1) -> int:
        """Returns the meas pin state (analog output hub in Volt [V])"""
        state = c_int16(0)
        result = self.dll.TLPMX_getMeasPinMode(self.devSession, byref(state), c_uint16(channel))
        self.checkError(result)
        return state.value

    def getMeasurementPinPowerLevel(self, channel: int = 1) -> float:
        """Returns the meas pin power level in [W]"""
        level = c_double(0)
        result = self.dll.TLPMX_getMeasPinPowerLevel(self.devSession, byref(level), c_uint16(channel))
        self.checkError(result)
        return level.value

    def setMeasurementPinPowerLevel(self, level: float, channel: int = 1):
        """Sets the meas pin power level in [W]"""
        result = self.dll.TLPMX_setMeasPinPowerLevel(self.devSession, c_double(level), c_uint16(channel))
        self.checkError(result)

    def getMeasurementPinEnergyLevel(self, channel: int = 1) -> float:
        """Returns the meas pin energy level in [J]"""
        level = c_double(0)
        result = self.dll.TLPMX_getMeasPinEnergyLevel(self.devSession, byref(level), c_uint16(channel))
        self.checkError(result)
        return level.value

    def setMeasurementPinEnergyLevel(self, level: float, channel: int = 1):
        """Sets the meas pin energy level in [J]"""
        result = self.dll.TLPMX_setMeasPinEnergyLevel(self.devSession, c_double(level), c_uint16(channel))
        self.checkError(result)

    def setNegativePulseWidth(self, pulse_duration: float, channel: int = 1):
        """Sets the low pulse duration in [s]"""
        result = self.dll.TLPMX_setNegativePulseWidth(self.devSession, c_double(pulse_duration), c_uint16(channel))
        self.checkError(result)

    def setPositivePulseWidth(self, pulse_duration: float, channel: int = 1):
        """Sets the high pulse duration in [s]"""
        result = self.dll.TLPMX_setPositivePulseWidth(self.devSession, c_double(pulse_duration), c_uint16(channel))
        self.checkError(result)

    def setNegativeDutyCycle(self, duty_cycle: float, channel: int = 1):
        """Sets the low duty cycle in [%]"""
        result = self.dll.TLPMX_setNegativeDutyCycle(self.devSession, c_double(duty_cycle), c_uint16(channel))
        self.checkError(result)

    def setPositiveDutyCycle(self, duty_cycle, channel: int = 1):
        """Sets the high duty cycle in [%]"""
        result = self.dll.TLPMX_setPositiveDutyCycle(self.devSession, c_double(duty_cycle), c_uint16(channel))
        self.checkError(result)

    def measureCurrent(self, channel: int = 1) -> float:
        """Obtain current readings from the instrument in [A]"""
        current = c_double(0)
        result = self.dll.TLPMX_measCurrent(self.devSession, byref(current), c_uint16(channel))
        self.checkError(result)
        return current.value

    def measureVoltage(self, channel: int = 1) -> float:
        """Obtain voltage readings from the instrument in [V]"""
        voltage = c_double(0)
        result = self.dll.TLPMX_measVoltage(self.devSession, byref(voltage), c_uint16(channel))
        self.checkError(result)
        return voltage.value

    def measurePower(self, channel: int = 1):
        """Obtain power readings from the instrument"""
        power = c_double(0)
        result = self.dll.TLPMX_measPower(self.devSession, byref(power), c_uint16(channel))
        self.checkError(result)
        return power.value

    def measureEnergy(self, channel: int = 1):
        """Obtain energy readings from the instrument in [J]"""
        energy = c_double(0)
        result = self.dll.TLPMX_measEnergy(self.devSession, byref(energy), c_uint16(channel))
        self.checkError(result)
        return energy.value

    def measureFrequency(self, channel: int = 1) -> float:
        """Obtain frequency readings from the instrument"""
        frequency = c_double(0)
        result = self.dll.TLPMX_measFreq(self.devSession, byref(frequency), c_uint16(channel))
        self.checkError(result)
        return frequency.value

    def measurePowerDensity(self, channel: int = 1) -> float:
        """Obtain power density readings from the instrument in [W/cm²]"""
        power_density = c_double(0)
        result = self.dll.TLPMX_measPowerDens(self.devSession, byref(power_density), c_uint16(channel))
        self.checkError(result)
        return power_density.value

    def measureEnergyDensity(self, channel: int = 1) -> float:
        """This function is used to obtain energy density readings from the instrument in [J/cm²]"""
        energy_density = c_double(0)
        result = self.dll.TLPMX_measEnergyDens(self.devSession, byref(energy_density), c_uint16(channel))
        self.checkError(result)
        return energy_density.value

    def measureAuxiliaryAD0(self, channel: int = 1) -> float:
        """Obtain voltage readings from the instrument's auxiliary AD0 input in [V] """
        voltage = c_double(0)
        result = self.dll.TLPMX_measAuxAD0(self.devSession, byref(voltage), c_uint16(channel))
        self.checkError(result)
        return voltage.value

    def measureAuxiliaryAD1(self, channel: int = 1) -> float:
        """Obtain voltage readings from the instrument's auxiliary AD1 input in [V]"""
        voltage = c_double(0)
        result = self.dll.TLPMX_measAuxAD1(self.devSession, byref(voltage), c_uint16(channel))
        self.checkError(result)
        return voltage.value

    def measureEmmHumidity(self, channel: int = 1) -> float:
        """Obtain relative humidity readings from the Environment Monitor Module (EMM) connected to the instrument in [%]"""
        humidity = c_double(0)
        result = self.dll.TLPMX_measEmmHumidity(self.devSession, byref(humidity), c_uint16(channel))
        self.checkError(result)
        return humidity.value

    def measureEmmTemperature(self, channel: int = 1) -> float:
        """Obtain temperature readings from the Environment Monitor Module (EMM) connected to the instrument  in [°C]"""
        temperature = c_double(0)
        result = self.dll.TLPMX_measEmmTemperature(self.devSession, byref(temperature), c_uint16(channel))
        self.checkError(result)
        return temperature.value

    def measureExternalNtcTemperature(self, channel: int = 1) -> float:
        """Gets temperature readings from the external thermistor sensor connected to the instrument (NTC IN)  in [°C]"""
        temperature = c_double(0)
        result = self.dll.TLPMX_measExtNtcTemperature(self.devSession, byref(temperature), c_uint16(channel))
        self.checkError(result)
        return temperature.value

    def measureExternalNtcResistance(self, channel: int = 1) -> float:
        """Gets resistance readings from the external thermistor sensor connected to the instrument (NTC IN) in [Ohm]"""
        resistance = c_double(0)
        result = self.dll.TLPMX_measExtNtcResistance(self.devSession, byref(resistance), c_uint16(channel))
        self.checkError(result)
        return resistance.value

    def measureHeadResistance(self, channel: int = 1) -> float:
        """Returns the head resistance in [Ohm]"""
        resistance = c_double(0)
        result = self.dll.TLPMX_measHeadResistance(self.devSession, byref(resistance), c_uint16(channel))
        self.checkError(result)
        return resistance.value

    def measureHeadTemperature(self, channel: int = 1) -> float:
        """Returns the head temperature in [°C]"""
        temperature = c_double(0)
        result = self.dll.TLPMX_measHeadTemperature(self.devSession, byref(temperature), c_uint16(channel))
        self.checkError(result)
        return temperature.value

    def measure4QPositions(self, channel: int = 1) -> tuple[float, float]:
        """Returns the x and y position of a 4q sensor (x, y)"""
        x = c_double(0)
        y = c_double(0)
        result = self.dll.TLPMX_meas4QPositions(self.devSession, byref(x), byref(y), c_uint16(channel))
        self.checkError(result)
        return x.value, y.value

    def meas4QVoltages(self, channel: int = 1) -> tuple[float, float, float, float]:
        """Returns the voltage of each sector of a 4q sensor (V1, V2, V3, V4) in [V]"""
        voltage_1 = c_double(0)
        voltage_2 = c_double(0)
        voltage_3 = c_double(0)
        voltage_4 = c_double(0)
        result = self.dll.TLPMX_meas4QVoltages(self.devSession, byref(voltage_1), byref(voltage_2), byref(voltage_3), byref(voltage_4), c_uint16(channel))
        self.checkError(result)
        return voltage_1.value, voltage_2.value, voltage_3.value, voltage_4.value

    def measureNegPulseWidth(self, channel: int = 1) -> float:
        """Returns the negative pulse width in [us]"""
        pulse_width = c_double(0)
        result = self.dll.TLPMX_measNegPulseWidth(self.devSession, byref(pulse_width), c_uint16(channel))
        self.checkError(result)
        return pulse_width.value

    def measurePosPulseWidth(self, channel: int = 1) -> float:
        """Returns the positive pulse width in [us]"""
        pulse_width = c_double(0)
        result = self.dll.TLPMX_measPosPulseWidth(self.devSession, byref(pulse_width), c_uint16(channel))
        self.checkError(result)
        return pulse_width.value

    def measureNegDutyCycle(self, channel: int = 1) -> float:
        """Returns the negative duty cycle in [%]"""
        duty_cycle = c_double(0)
        result = self.dll.TLPMX_measNegDutyCycle(self.devSession, byref(duty_cycle), c_uint16(channel))
        self.checkError(result)
        return duty_cycle.value

    def measurePosDutyCycle(self, channel: int = 1):
        """Returns the positive duty cycle in [%]"""
        duty_cycle = c_double(0)
        result = self.dll.TLPMX_measPosDutyCycle(self.devSession, byref(duty_cycle), c_uint16(channel))
        self.checkError(result)
        return duty_cycle.value

    def measurePowerMeasurementSequence(self, base_time: int, channel: int = 1):
        """Set up power measurement sequence"""
        result = self.dll.TLPMX_measPowerMeasurementSequence(self.devSession, c_uint32(base_time), c_uint16(channel))
        self.checkError(result)

    def measurePowerMeasurementSequenceHWTrigger(self, base_time: int, h_pos: int, channel: int = 1):
        """Set up power measurement sequence with HW trigger"""
        result = self.dll.TLPMX_measPowerMeasurementSequenceHWTrigger(self.devSession, c_uint32(base_time), c_uint32(h_pos), c_uint16(channel))
        self.checkError(result)

    def measureCurrentMeasurementSequence(self, base_time: int, channel: int = 1):
        """Set up current measurement sequence"""
        result = self.dll.TLPMX_measureCurrentMeasurementSequence(self.devSession, c_uint32(base_time), c_uint16(channel))
        self.checkError(result)

    def measureCurrentMeasurementSequenceHWTrigger(self, base_time: int, h_pos: int, channel: int = 1):
        """Set up current measurement sequence with HW trigger"""
        result = self.dll.TLPMX_measureCurrentMeasurementSequenceHWTrigger(self.devSession, c_uint32(base_time), c_uint32(h_pos), c_uint16(channel))
        self.checkError(result)

    def measureVoltageMeasurementSequence(self, base_time: int, channel: int = 1):
        """Set up voltage measurement sequence"""
        result = self.dll.TLPMX_measureVoltageMeasurementSequence(self.devSession, c_uint32(base_time), c_uint16(channel))
        self.checkError(result)

    def measureVoltageMeasurementSequenceHWTrigger(self, base_time: int, h_pos: int, channel: int = 1):
        """Set up voltage measurement sequence with HW trigger"""
        result = self.dll.TLPMX_measureVoltageMeasurementSequenceHWTrigger(self.devSession, c_uint32(base_time), c_uint32(h_pos), c_uint16(channel))
        self.checkError(result)

    def getFetchState(self, channel: int = 1) -> int:
        """Fet the measurement state information before doing a fetch"""
        state = c_int16(0)
        result = self.dll.TLPMX_getFetchState(self.devSession, byref(state), c_uint16(channel))
        self.checkError(result)
        return state.value

    def resetFastArrayMeasurement(self, channel: int = 1):
        """Resets the array measurement."""
        result = self.dll.TLPMX_resetFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configurePowerFastArrayMeasurement(self, channel: int = 1):
        """Configure the fast array measurement of power values"""
        result = self.dll.TLPMX_confPowerFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configureCurrentFastArrayMeasurement(self, channel: int = 1):
        """Configure the fast array measurement of current values"""
        result = self.dll.TLPMX_confCurrentFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configureVoltageFastArrayMeasurement(self, channel: int = 1):
        """Configure the fast array measurement of voltage values"""
        result = self.dll.TLPMX_confVoltageFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configurePDensityFastArrayMeasurement(self, channel: int = 1):
        """Configure the fast array measurement of P density values"""
        result = self.dll.TLPMX_confPDensityFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configureEnergyFastArrayMeasurement(self, channel: int = 1):
        """Configure the fast array measurement of energy values"""
        result = self.dll.TLPMX_confEnergyFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configureEDensityFastArrayMeasurement(self, channel: int = 1):
        """Configure the fast array measurement of E density values"""
        result = self.dll.TLPMX_confEDensityFastArrayMeasurement(self.devSession, c_uint16(channel))
        self.checkError(result)

    def getNextFastArrayMeasurement(self, timestamps, values_1, values_2, channel: int = 1) -> int:
        """Obtain measurements from the instrument"""
        count = c_uint16(0)
        result = self.dll.TLPMX_getNextFastArrayMeasurement(self.devSession, byref(count), timestamps, values_1, values_2, c_uint16(channel))
        self.checkError(result)
        return count.value

    def getFastMaxSamplerate(self, channel: int = 1) -> int:
        """Obtain the maximal possible sample rate [Hz]"""
        value = c_uint32(0)
        result = self.dll.TLPMX_getFastMaxSamplerate(self.devSession, byref(value), c_uint16(channel))
        self.checkError(result)
        return value.value

    def configurePowerMeasurementSequence(self, base_time: int, channel: int = 1):
        """Configure the power measurement sequence"""
        result = self.dll.TLPMX_confPowerMeasurementSequence(self.devSession, c_uint32(base_time), c_uint16(channel))
        self.checkError(result)

    def configurePowerMeasurementSequenceHWTrigger(self, trig_src: int, base_time: int, h_pos: int, channel: int = 1):
        """Configure the power measurement sequence with HW trigger"""
        result = self.dll.TLPMX_confPowerMeasurementSequenceHWTrigger(self.devSession, c_uint16(trig_src), c_uint32(base_time), c_uint32(h_pos), c_uint16(channel))
        self.checkError(result)

    def configureCurrentMeasurementSequence(self, base_time: int, channel: int = 1):
        """Configure the current measurement sequence"""
        result = self.dll.TLPMX_confCurrentMeasurementSequence(self.devSession, c_uint32(base_time), c_uint16(channel))
        self.checkError(result)

    def configureCurrentMeasurementSequenceHWTrigger(self, trig_src: int, base_time: int, h_pos: int, channel: int = 1):
        """Configure the current measurement sequence with HW trigger"""
        result = self.dll.TLPMX_confCurrentMeasurementSequenceHWTrigger(self.devSession, c_uint16(trig_src), c_uint32(base_time), c_uint32(h_pos), c_uint16(channel))
        self.checkError(result)

    def configureVoltageMeasurementSequence(self, base_time: int, channel: int = 1):
        """Configure the voltage measurement sequence"""
        result = self.dll.TLPMX_confVolatgeMeasurementSequence(self.devSession, c_uint32(base_time), c_uint16(channel))
        self.checkError(result)

    def configureVoltageMeasurementSequenceHWTrigger(self, trig_src: int, base_time: int, h_pos: int, channel: int = 1):
        """Configure the voltage measurement sequence with HW trigger"""
        result = self.dll.TLPMX_confVolatgeMeasurementSequenceHWTrigger(self.devSession, c_uint16(trig_src), c_uint32(base_time), c_uint32(h_pos), c_uint16(channel))
        self.checkError(result)

    def startMeasurementSequence(self, auto_trigger_delay: int, channel: int = 1) -> int:
        """Starts the measurement sequence"""
        trigger_forced = c_int16(0)
        result = self.dll.TLPMX_startMeasurementSequence(self.devSession, c_uint32(auto_trigger_delay), byref(trigger_forced), c_uint16(channel))
        self.checkError(result)
        return trigger_forced.value

    def getMeasurementSequence(self, base_time: int, time_stamps, values_1, values_2, channel: int = 1):
        """Get measurement sequence"""
        result = self.dll.TLPMX_getMeasurementSequence(self.devSession, c_uint32(base_time), time_stamps, values_1, values_2, c_uint16(channel))
        self.checkError(result)

    def getMeasurementSequenceHWTrigger(self, base_time: int, time_stamps, values_1, values_2, channel: int = 1):
        """Get measurement sequence with HW trigger"""
        result = self.dll.TLPMX_getMeasurementSequenceHWTrigger(self.devSession, c_uint32(base_time), time_stamps, values_1, values_2, c_uint16(channel))
        self.checkError(result)

    def configureBurstArrayMeasurementChannel(self, channel: int = 1):
        """Configure the burst array measurement of each channel."""
        result = self.dll.TLPMX_confBurstArrayMeasurementChannel(self.devSession, c_uint16(channel))
        self.checkError(result)

    def configureBurstArrayMeasurementPowerTrigger(self, init_delay: int, burst_count: int, averaging: int):
        """Configure the burst array measurement with power trigger"""
        result = self.dll.TLPMX_confBurstArrayMeasPowerTrigger(self.devSession, c_uint32(init_delay), c_uint32(burst_count), c_uint32(averaging))
        self.checkError(result)

    def configureBurstArrayMeasurementCurrentTrigger(self, init_delay: int, burst_count: int, averaging: int):
        """Configure the burst array measurement with current trigger"""
        result = self.dll.TLPMX_confBurstArrayMeasCurrentTrigger(self.devSession, c_uint32(init_delay), c_uint32(burst_count), c_uint32(averaging))
        self.checkError(result)

    def startBurstArrayMeasurement(self):
        """Starts a burst array measurement"""
        result = self.dll.TLPMX_startBurstArrayMeasurement(self.devSession)
        self.checkError(result)

    def getBurstArraySamplesCount(self) -> int:
        """Read the amount of samples in the burst array buffer"""
        count = c_uint32(0)
        result = self.dll.TLPMX_getBurstArraySamplesCount(self.devSession, byref(count))
        self.checkError(result)
        return count.value

    def getBurstArraySamples(self, start_index: int, sample_count: int, time_stamps, values_1, values_2):
        """Read scope buffer content at index """
        result = self.dll.TLPMX_getBurstArraySamples(self.devSession, c_uint32(start_index), c_uint32(sample_count), time_stamps, values_1, values_2)
        self.checkError(result)

    def setDigIoDirection(self, io_0: int, io_1: int, io_2: int, io_3: int):
        """Sets the digital I/O port direction (0 - in; 1 - out)"""
        result = self.dll.TLPMX_setDigIoDirection(self.devSession, c_int16(io_0), c_int16(io_1), c_int16(io_2), c_int16(io_3))
        self.checkError(result)

    def getDigIoDirection(self) -> tuple[int, int, int, int]:
        """Returns the digital I/O port direction (0 - in; 1 - out)"""
        io_0 = c_int16(0)
        io_1 = c_int16(0)
        io_2 = c_int16(0)
        io_3 = c_int16(0)
        result = self.dll.TLPMX_getDigIoDirection(self.devSession, byref(io_0), byref(io_1), byref(io_2), byref(io_3))
        self.checkError(result)
        return io_0.value, io_1.value, io_2.value, io_3.value

    def setDigIoOutput(self, io_0: int, io_1: int, io_2: int, io_3: int):
        """Sets the digital I/O outputs"""
        result = self.dll.TLPMX_setDigIoOutput(self.devSession, c_int16(io_0), c_int16(io_1), c_int16(io_2), c_int16(io_3))
        self.checkError(result)

    def getDigIoOutput(self) -> tuple[int, int, int, int]:
        """Returns the digital I/O output settings"""
        io_0 = c_int16(0)
        io_1 = c_int16(0)
        io_2 = c_int16(0)
        io_3 = c_int16(0)
        result = self.dll.TLPMX_getDigIoOutput(self.devSession, byref(io_0), byref(io_1), byref(io_2), byref(io_3))
        self.checkError(result)
        return io_0.value, io_1.value, io_2.value, io_3.value

    def getDigIoPort(self) -> tuple[int, int, int, int]:
        """Returns the actual digital I/O port level"""
        io_0 = c_int16(0)
        io_1 = c_int16(0)
        io_2 = c_int16(0)
        io_3 = c_int16(0)
        result = self.dll.TLPMX_getDigIoPort(self.devSession, byref(io_0), byref(io_1), byref(io_2), byref(io_3))
        self.checkError(result)
        return io_0.value, io_1.value, io_2.value, io_3.value

    def setDigIoPinMode(self, pin_number: int, pin_mode: int):
        """Sets the digital I/O port direction (0 - in; 1 - out; 2 - alternative)"""
        result = self.dll.TLPMX_setDigIoPinMode(self.devSession, c_int16(pin_number), c_uint16(pin_mode))
        self.checkError(result)

    def getDigIoPinMode(self, pin_number: int) -> int:
        """Returns the digital I/O port direction (0 - in; 1 - out, 2 - alternative in; 3 - alternative out)"""
        pin_mode = c_uint16(0)
        result = self.dll.TLPMX_getDigIoPinMode(self.devSession, c_int16(pin_number), byref(pin_mode))
        self.checkError(result)
        return pin_mode.value

    def setDigIoOutput2(self, io_0: int, io_1: int, io_2: int, io_3: int):
        """Sets digital I/O outputs"""
        result = self.dll.TLPMX_setDigIoOutput(self.devSession, c_int16(io_0), c_int16(io_1), c_int16(io_2), c_int16(io_3))
        self.checkError(result)

    def getDigIoOutput2(self) -> tuple[int, int, int, int]:
        """Gets digital I/O output settings"""
        io_0 = c_int16(0)
        io_1 = c_int16(0)
        io_2 = c_int16(0)
        io_3 = c_int16(0)
        result = self.dll.TLPMX_getDigIoOutput(self.devSession, byref(io_0), byref(io_1), byref(io_2), byref(io_3))
        self.checkError(result)
        return io_0.value, io_1.value, io_2.value, io_3.value

    def getDigIoPinInput(self) -> tuple[int, int, int, int]:
        """Returns the actual digital I/O port level"""
        io_0 = c_int16(0)
        io_1 = c_int16(0)
        io_2 = c_int16(0)
        io_3 = c_int16(0)
        result = self.dll.TLPMX_getDigIoPinInput(self.devSession, byref(io_0), byref(io_1), byref(io_2), byref(io_3))
        self.checkError(result)
        return io_0.value, io_1.value, io_2.value, io_3.value

    def getShutterInterlock(self) -> int:
        """Gets the shutter interlock state"""
        interlock_state = c_int16(0)
        result = self.dll.TLPMX_getShutterInterlock(self.devSession, byref(interlock_state))
        self.checkError(result)
        return interlock_state.value

    def setShutterPosition(self, position: int):
        """Sets the shutter position"""
        result = self.dll.TLPMX_setShutterPosition(self.devSession, c_int16(position))
        self.checkError(result)

    def getShutterPosition(self) -> int:
        """Get the shutter position"""
        shutter_position = c_int16(0)
        result = self.dll.TLPMX_getShutterPosition(self.devSession, byref(shutter_position))
        self.checkError(result)
        return shutter_position.value

    def setI2CMode(self, mode: TLPMxValues.I2C):
        """Changes the I2C speed and operating mode"""
        result = self.dll.TLPMX_setI2CMode(self.devSession, c_uint16(mode))
        self.checkError(result)

    def getI2CMode(self) -> int:
        """Queries the I2C speed and operating mode"""
        mode = c_int16(0)
        result = self.dll.TLPMX_getI2CMode(self.devSession, byref(mode))
        self.checkError(result)
        return mode.value

    def I2CRead(self, address: int, count: int) -> int:
        """Receives data from slave with given address"""
        data = c_uint32(0)
        result = self.dll.TLPMX_I2CRead(self.devSession, c_uint32(address), c_uint32(count), byref(data))
        self.checkError(result)
        return data.value

    def I2CWrite(self, address: int, hex_data: str):
        """Writes hex_data to slave with given address"""
        result = self.dll.TLPMX_I2CWrite(self.devSession, c_uint32(address), c_char_p(hex_data.encode('utf-8')))
        self.checkError(result)

    def I2CWriteRead(self, address: int, hex_send_data: str, count: int) -> int:
        """Transmits given data to slave with given address following a bus reception from same device if transmission was successful"""
        data = c_uint32(0)
        result = self.dll.TLPMX_I2CWriteRead(self.devSession, c_uint32(address), c_char_p(hex_send_data.encode('utf-8')), c_uint32(count), byref(data))
        self.checkError(result)
        return data.value

    def getFanState(self, channel: int = 1) -> int:
        """Returns if the fan is running"""
        is_running = c_int16(0)
        result = self.dll.TLPMX_getFanState(self.devSession, byref(is_running), c_uint16(channel))
        self.checkError(result)
        return is_running.value

    def setFanMode(self, mode: TLPMxValues.FanMode, channel: int = 1):
        """Sets the state of the fan"""
        result = self.dll.TLPMX_setFanMode(self.devSession, c_uint16(mode), c_uint16(channel))
        self.checkError(result)

    def getFanMode(self, channel: int = 1) -> int:
        """Fets the state of the fan """
        mode = c_uint16(0)
        result = self.dll.TLPMX_getFanMode(self.devSession, byref(mode), c_uint16(channel))
        self.checkError(result)
        return mode.value

    def setFanVoltage(self, voltage: float, channel: int = 1):
        """Sets the fan voltage"""
        result = self.dll.TLPMX_setFanVoltage(self.devSession, c_double(voltage), c_uint16(channel))
        self.checkError(result)

    def getFanVoltage(self, channel: int = 1) -> float:
        """Gets the fan voltage"""
        voltage = c_double(0)
        result = self.dll.TLPMX_getFanVoltage(self.devSession, byref(voltage), c_uint16(channel))
        self.checkError(result)
        return voltage.value

    def setFanRpm(self, max_rpm: float, target_rpm: float, channel: int = 1):
        """Sets fan RPM"""
        result = self.dll.TLPMX_setFanRpm(self.devSession, c_double(max_rpm), c_double(target_rpm), c_uint16(channel))
        self.checkError(result)

    def getFanRpm(self, channel: int = 1) -> tuple[float, float]:
        """Gets fan RPM (max, target)"""
        rpm_max = c_double(0)
        rpm_target = c_double(0)
        result = self.dll.TLPMX_getFanRpm(self.devSession, byref(rpm_max), byref(rpm_target), c_uint16(channel))
        self.checkError(result)
        return rpm_max.value, rpm_target.value

    def getActualFanRpm(self, channel: int = 1) -> float:
        """Get actual fan RPM"""
        rpm = c_double(0)
        result = self.dll.TLPMX_getActFanRpm(self.devSession, byref(rpm), c_uint16(channel))
        self.checkError(result)
        return rpm.value

    def setFanTemperatureSource(self, source: TLPMxValues.FanTemperatureSource, channel: int = 1):
        """Sets the source for the fan temperature control"""
        result = self.dll.TLPMX_setFanTemperatureSource(self.devSession, c_uint16(source), c_uint16(channel))
        self.checkError(result)

    def getFanTemperatureSource(self, channel: int = 1) -> int:
        """Fets the source for the fan temperature control"""
        source = c_uint16(0)
        result = self.dll.TLPMX_getFanTemperatureSource(self.devSession, byref(source), c_uint16(channel))
        self.checkError(result)
        return source.value

    def setFanAdjustParameters(self, voltage_min: float, voltage_max: float, temperature_min: float, temperature_max: float, channel: int = 1):
        """Sets fan parameters"""
        result = self.dll.TLPMX_setFanAdjustParameters(self.devSession, c_double(voltage_min), c_double(voltage_max), c_double(temperature_min), c_double(temperature_max), c_uint16(channel))
        self.checkError(result)

    def getFanAdjustParameters(self, channel: int = 1) -> tuple[float, float, float, float]:
        """Gets fan parameters (voltage_min, voltage_max, temperature_min, temperature_max)"""
        voltage_min = c_double(0)
        voltage_max = c_double(0)
        temperature_min = c_double(0)
        temperature_max = c_double(0)
        result = self.dll.TLPMX_getFanAdjustParameters(self.devSession, byref(voltage_min), byref(voltage_max), byref(temperature_min), byref(temperature_max), c_uint16(channel))
        self.checkError(result)
        return voltage_min.value, voltage_max.value, temperature_min.value, temperature_max.value

    def errorMessage(self, status_code: int) -> bytearray:
        """Takes the error code returned by the instrument driver functions interprets it and returns it as an user readable string"""
        description = create_string_buffer(1024)
        result = self.dll.TLPMX_errorMessage(self.devSession, c_int(status_code), description)
        self.checkError(result)
        return c_char_p(description.raw).value

    def errorQuery(self) -> tuple[int, bytearray]:
        """Queries the instrument's error queue manually"""
        error_number = c_int(0)
        error_msg = create_string_buffer(1024)
        result = self.dll.TLPMX_errorQuery(self.devSession, byref(error_number), error_msg)
        self.checkError(result)
        return error_number.value, c_char_p(error_msg.raw).value

    def errorQueryMode(self, mode: int):
        """Selects the driver's error query mode"""
        result = self.dll.TLPMX_errorQueryMode(self.devSession, c_int16(mode))
        self.checkError(result)

    def errorCount(self) -> int:
        """Returns the number of errors in the queue"""
        count = c_uint32(0)
        result = self.dll.TLPMX_errorCount(self.devSession, byref(count))
        self.checkError(result)
        return count.value

    def reset(self):
        """Places the instrument in a default state"""
        result = self.dll.TLPMX_reset(self.devSession)
        self.checkError(result)

    def selfTest(self) -> tuple[int, bytearray]:
        """Runs the device self test routine and returns the test result"""
        test_result = c_int16(0)
        test_description = create_string_buffer(1024)
        result = self.dll.TLPMX_selfTest(self.devSession, byref(test_result), test_description)
        self.checkError(result)
        return test_result.value, c_char_p(test_description.raw).value

    def revisionQuery(self) -> tuple[bytearray, bytearray]:
        """Returns the revision numbers of the instrument driver and the device firmware"""
        instrument_driver_revision = create_string_buffer(1024)
        firmware_revision = create_string_buffer(1024)
        result = self.dll.TLPMX_revisionQuery(self.devSession, instrument_driver_revision, firmware_revision)
        self.checkError(result)
        return c_char_p(instrument_driver_revision.raw).value, c_char_p(firmware_revision.raw).value

    def identificationQuery(self) -> tuple[bytearray, bytearray, bytearray, bytearray]:
        """Returns the device identification information (manufacturer name, device name, serial number, firmware revision)"""
        manufacturer_name = create_string_buffer(1024)
        device_name = create_string_buffer(1024)
        serial_number = create_string_buffer(1024)
        firmware_revision = create_string_buffer(1024)
        result = self.dll.TLPMX_identificationQuery(self.devSession, manufacturer_name, device_name, serial_number, firmware_revision)
        self.checkError(result)
        return c_char_p(manufacturer_name.raw).value, c_char_p(device_name.raw).value, c_char_p(serial_number.raw).value, c_char_p(firmware_revision.raw).value

    def getCalibrationMsg(self, channel: int = 1) -> bytearray:
        """Returns a human-readable calibration message"""
        message = create_string_buffer(1024)
        result = self.dll.TLPMX_getCalibrationMsg(self.devSession, message, c_uint16(channel))
        self.checkError(result)
        return c_char_p(message.raw).value

    def setDisplayName(self) -> bytearray:
        """Sets display name"""
        name = create_string_buffer(1024)
        result = self.dll.TLPMX_setDisplayName(self.devSession, name)
        self.checkError(result)
        return c_char_p(name.raw).value

    def getDisplayName(self) -> bytearray:
        """Gets display name"""
        name = create_string_buffer(1024)
        result = self.dll.TLPMX_getDisplayName(self.devSession, name)
        self.checkError(result)
        return c_char_p(name.raw).value

    def getChannels(self) -> int:
        """Returns the number of supported sensor channels"""
        count = c_uint16(0)
        result = self.dll.TLPMX_getChannels(self.devSession, byref(count))
        self.checkError(result)
        return count.value

    def getSensorInfo(self, channel: int = 1) -> tuple[bytearray, bytearray, bytearray, int, int, int]:
        """Obtain information from the connected sensor (sensor name, serial number, calibration message, sensor type, sensor subtype and sensor flags)"""
        name = create_string_buffer(1024)
        snr = create_string_buffer(1024)
        message = create_string_buffer(1024)
        sensor_type = c_int16(0)
        sensor_stype = c_int16(0)
        sensor_flags = c_int16(0)
        result = self.dll.TLPMX_getSensorInfo(self.devSession, name, snr, message, byref(sensor_type), byref(sensor_stype), byref(sensor_flags), c_uint16(channel))
        self.checkError(result)
        return c_char_p(name.raw).value, c_char_p(snr.raw).value, c_char_p(message.raw).value, sensor_type.value, sensor_stype.value, sensor_flags.value

    def setTimeoutValue(self, value: int):
        """Sets the interface communication timeout value"""
        result = self.dll.TLPMX_setTimeoutValue(self.devSession, c_uint32(value))
        self.checkError(result)

    def getTimeoutValue(self) -> int:
        """Fets the interface communication timeout value"""
        value = c_uint32(0)
        result = self.dll.TLPMX_getTimeoutValue(self.devSession, byref(value))
        self.checkError(result)
        return value.value

    def setIPAddress(self) -> bytearray:
        """Set which IP address the device has to communicate with"""
        ip_address = create_string_buffer(1024)
        result = self.dll.TLPMX_setIPAddress(self.devSession, ip_address)
        self.checkError(result)
        return c_char_p(ip_address.raw).value

    def getIPAddress(self) -> bytearray:
        """Get which IP address the device has to communicate with"""
        ip_address = create_string_buffer(1024)
        result = self.dll.TLPMX_getIPAddress(self.devSession, ip_address)
        self.checkError(result)
        return c_char_p(ip_address.raw).value

    def setIPMask(self) -> bytearray:
        """Sets IP mask"""
        ip_mask = create_string_buffer(1024)
        result = self.dll.TLPMX_setIPMask(self.devSession, ip_mask)
        self.checkError(result)
        return c_char_p(ip_mask.raw).value

    def getIPMask(self) -> bytearray:
        """Gets IP mask"""
        ip_mask = create_string_buffer(1024)
        result = self.dll.TLPMX_getIPMask(self.devSession, ip_mask)
        self.checkError(result)
        return c_char_p(ip_mask.raw).value

    def getMACAddress(self) -> bytearray:
        """Gets MAC address"""
        mac_address = create_string_buffer(1024)
        result = self.dll.TLPMX_getMACAddress(self.devSession, mac_address)
        self.checkError(result)
        return c_char_p(mac_address.raw).value

    def setDHCP(self) -> bytearray:
        """Sets which IP address the device has to communicate with"""
        dhcp = create_string_buffer(1024)
        result = self.dll.TLPMX_setDHCP(self.devSession, dhcp)
        self.checkError(result)
        return c_char_p(dhcp.raw).value

    def getDHCP(self) -> bytearray:
        """Gets which IP address the device has to communicate with"""
        dhcp = create_string_buffer(1024)
        result = self.dll.TLPMX_getDHCP(self.devSession, dhcp)
        self.checkError(result)
        return c_char_p(dhcp.raw).value

    def setHostname(self) -> bytearray:
        """Sets hostname"""
        hostname = create_string_buffer(1024)
        result = self.dll.TLPMX_setHostname(self.devSession, hostname)
        self.checkError(result)
        return c_char_p(hostname.raw).value

    def getHostname(self) -> bytearray:
        """Gets hostname"""
        hostname = create_string_buffer(1024)
        result = self.dll.TLPMX_getHostname(self.devSession, hostname)
        self.checkError(result)
        return c_char_p(hostname.raw).value

    def setWebPort(self, port: int):
        """Sets web port"""
        result = self.dll.TLPMX_setWebPort(self.devSession, c_uint32(port))
        self.checkError(result)

    def getWebPort(self) -> int:
        """Gets web port"""
        port = c_uint32(0)
        result = self.dll.TLPMX_getWebPort(self.devSession, byref(port))
        self.checkError(result)
        return port.value

    def setSCPIPort(self, port: int):
        """Sets SCPI port"""
        result = self.dll.TLPMX_setSCPIPort(self.devSession, c_uint32(port))
        self.checkError(result)

    def getSCPIPort(self) -> int:
        """Gets SCPI port"""
        port = c_uint32(0)
        result = self.dll.TLPMX_getSCPIPort(self.devSession, byref(port))
        self.checkError(result)
        return port.value

    def setDFUPort(self, port: int):
        """Sets DFU port"""
        result = self.dll.TLPMX_setDFUPort(self.devSession, c_uint32(port))
        self.checkError(result)

    def getDFUPort(self) -> int:
        """Gets DFU port"""
        port = c_uint32(0)
        result = self.dll.TLPMX_getDFUPort(self.devSession, byref(port))
        self.checkError(result)
        return port.value

    def setDeviceBaudrate(self, baudrate: int):
        """Sets device baudrate"""
        result = self.dll.TLPMX_setDeviceBaudrate(self.devSession, c_uint32(baudrate))
        self.checkError(result)

    def getDeviceBaudrate(self) -> int:
        """Gets device baudrate"""
        baudrate = c_uint32(0)
        result = self.dll.TLPMX_getDeviceBaudrate(self.devSession, byref(baudrate))
        self.checkError(result)
        return baudrate.value

    def setDriverBaudrate(self, baudrate: int):
        """Sets driver baudrate"""
        result = self.dll.TLPMX_setDriverBaudrate(self.devSession, c_uint32(baudrate))
        self.checkError(result)

    def getDriverBaudrate(self):
        """Gets driver baudrate"""
        baudrate = c_uint32(0)
        result = self.dll.TLPMX_getDriverBaudrate(self.devSession, byref(baudrate))
        self.checkError(result)
        return baudrate.value

    def getCalibrationMessage(self, channel: int = 1) -> bytearray:
        """Gets a calibration message"""
        pymessage = create_string_buffer(1024)
        result = self.dll.TLPMX_getCalibrationMsg(self.devSession, pymessage, c_uint16(channel))
        self.checkError(result)
        return c_char_p(pymessage.raw).value

    def setAutoRange(self, ranges: tuple[int, int], channel: int = 1):
        """Sets auto ranges for (Power, Current)"""
        self.setPowerAutoRange(ranges[0], channel)
        self.setCurrentAutoRange(ranges[1], channel)

    def getAutoRange(self, channel: int = 1) -> tuple[int, int]:
        """Gets auto ranges for (Power, Current)"""
        return (
            self.getPowerAutoRange(channel),
            self.getCurrentAutoRange(channel)
        )

    def setRange(self, ranges: tuple[float, float], channel: int = 1):
        """Sets ranges for (Power, Current)"""
        self.setPowerRange(ranges[0], channel)
        self.setCurrentRange(ranges[1], channel)

    def getRange(self, attribute: TLPMxValues.Attribute, channel: int = 1) -> tuple[float, float]:
        """Gets ranges for (Power, Current)"""
        return (
            self.getPowerRange(attribute, channel),
            self.getCurrentRange(attribute, channel)
        )

    def measure(self, channel: int = 1) -> tuple[float, float]:
        """Obtain (Power, Current)"""
        return (
            self.measurePower(channel),
            self.measureCurrent(channel)
        )

    def close(self):
        """Closes the connection"""
        result = self.dll.TLPMX_close(self.devSession)
        return result


def getResources() -> dict[bytearray, tuple[bytearray, bytearray, bytearray, int]]:
    """
    Returns a list of connected resources

    :returns: tuple(
        name,
        tuple(
            type_name,
            serial_number,
            company,
            id
        )
    )
    """

    resource_list = dict()
    try:
        with TLPMxConnection() as tlpmx:
            resources = tlpmx.findResources()
            for resource in range(resources):
                try:
                    resource_list[tlpmx.getResourceName(resource)] = tlpmx.getResourceInfo(resource)
                except NameError:
                    continue
    except NameError:
        pass

    finally:
        return resource_list


def main():
    from time import time

    with TLPMxConnection() as tlpmx:
        st_time = time()
        rs = tlpmx.findResources()
        print('findResources', rs)
        print(f'Took {time() - st_time}s\n')
        rn = b'123'
        for i in range(rs):
            st_time = time()
            rn = tlpmx.getResourceName(i)
            print('getResourceName', rn)
            print(f'Took {time() - st_time}s\n')

            st_time = time()
            print('getResourceInfo', tlpmx.getResourceInfo(i))
            print(f'Took {time() - st_time}s\n')
            if rn:
                break

    with TLPMxConnection(rn, True, False) as tlpmx:
        st_time = time()
        print('getCalibrationMessage', tlpmx.getCalibrationMessage())
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('getPowerAutoRange', tlpmx.getPowerAutoRange())
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('getBeamDiameter', tlpmx.getBeamDiameter(TLPMxValues.Attribute.SetValue))
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('measurePower:', tlpmx.measurePower())
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('getWavelength', tlpmx.getWavelength(TLPMxValues.Attribute.SetValue))
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('autoRange', tlpmx.getAutoRange())
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('range', tlpmx.getRange(TLPMxValues.Attribute.SetValue))
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('measure', tlpmx.measure())
        print(f'Took {time() - st_time}s\n')

        st_time = time()
        print('*IDN?:', tlpmx.queryRaw('*IDN?\n'))
        print(f'Took {time() - st_time}s\n')


if __name__ == '__main__':
    print(getResources())
    #main()
