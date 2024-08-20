from enum import Enum, IntEnum
from serial import Serial
import struct


from Config.GlobalConf import GlobalConf


class LucidControlId:
    """
    Container for Lucid Control ID
    """

    def __init__(self):
        self.revision_fw = 0
        self.revision_hw = 0
        self.device_class = 0
        self.device_type = 0
        self.device_snr = 0
        self.valid_data = False

    def set(
        self,
        revision_fw: int,
        revision_hw: int,
        device_class: int,
        device_type: int,
        device_snr: int
    ):
        """
        Sets all parameters of Lucid Control ID

        :param revision_fw: revision number of firmware
        :param revision_hw: revision number of hardware
        :param device_class: device class
        :param device_type: device type
        :param device_snr: device serial number
        """
        self.revision_fw = revision_fw
        self.revision_hw = revision_hw
        self.device_class = device_class
        self.device_type = device_type
        self.device_snr = device_snr
        self.valid_data = True


class LucidControlConnection:
    """
    Context manager for serial connection to LucidControl

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param baudrate: Baudrate
    :param channels: Number of channels
    """

    class ReturnCode(IntEnum):
        """Opcode of return states"""
        OK = 0x00
        NSUP = 0xA0
        INV_LENGTH = 0xB0
        INV_P1 = 0xB2
        INV_P2 = 0xB4
        INV_VALUE = 0xB6
        INV_IOCH = 0xB8
        INV_PARAM = 0xBA
        INV_DATA = 0xC0
        ERR_EXEC = 0xD0
        ERR_INTERNAL = 0xFF

    class OpCode(IntEnum):
        """Opcodes for operation codes"""
        SETIO = 0x40  # NOT PRESENT IN DATASHEET
        SETIO_GROUP = 0x42  # NOT PRESENT IN DATASHEET
        GETIO = 0x46
        GETIO_GROUP = 0x48
        CALIBIO = 0x52  # NOT PRESENT IN DATASHEET
        GETID = 0xC0
        SETPARAM = 0xA0
        GETPARAM = 0xA2  # NOT PRESENT IN DATASHEET

    class ParamAddress(IntEnum):
        """Opcodes for parameter addresses"""
        VALUE = 0x1000
        MODE = 0x1100
        FLAGS = 0x1101
        NR_SAMPLES = 0x1112
        OFFSET = 0x1120

    class DeviceClass(Enum):
        """Device classes"""
        DI4 = (0x0000, 'DIGITAL INPUT 4 CHANNELS')
        DI8 = (0x0010, 'DIGITAL INPUT 8 CHANNELS')
        AI4 = (0x0100, 'ANALOG INPUT 4 CHANNELS')
        AI8 = (0x0110, 'ANALOG INPUT 8 CHANNELS')
        RI4 = (0x0A00, 'RTD INPUT 4 CHANNELS')
        RI8 = (0x0A10, 'RTD INPUT 8 CHANNELS')
        DO4 = (0x1000, 'DIGITAL OUTPUT 4 CHANNELS')
        DO8 = (0x1010, 'DIGITAL OUTPUT 8 CHANNELS')
        AO4 = (0x1100, 'ANALOG OUTPUT 4 CHANNELS')
        AO8 = (0x1110, 'ANALOG OUTPUT 8 CHANNELS')
        DI4DO4 = (0x4000, 'DIGITAL INPUT 4 CHANNELS, DIGITAL OUTPUT 4 CHANNELS')

    class DeviceType(Enum):
        """Device types"""
        NONE = (0x0000, "Not identified")
        V0_5 = (0x1000, "0 V ~ 5 V")
        V0_10 = (0x1001, "0 V ~ 10 V")
        V0_12 = (0x1002, "0 V ~ 12 V")
        V0_15 = (0x1003, "0 V ~ 15 V")
        V0_20 = (0x1004, "0 V ~ 20 V")
        V0_24 = (0x1005, "0 V ~ 24 V")
        V5_5 = (0x1010, "-5 V ~ 5 V")
        V10_10 = (0x1011, "-10 V ~ 10 V")
        V12_12 = (0x1012, "-12 V ~ 12 V")
        V15_15 = (0x1013, "-15 V ~ 15 V")
        V20_20 = (0x1014, "-20 V ~ 20 V")
        V24_24 = (0x1015, "-24 V ~ 24 V")
        V0_20MA_500 = (0x1110, "0 A ~ 0.02 A")

    def __init__(
        self,
        comport: str,
        timeout: float = 0.05,
        baudrate: int = 9600,
        channels: int = 4
    ):
        self.comport = comport
        self.timeout = timeout
        self.baudrate = baudrate
        self.channels = channels

        self.id = LucidControlId()

        self.serial: Serial | None = None

    def __enter__(self):
        """Enter serial connection and clean possible outputs"""
        return self.open()

    def open(self):
        """Opens the connection"""
        self.serial = Serial(self.comport, baudrate=self.baudrate, timeout=self.timeout)
        self.identify()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Closes the connection"""
        self.close()

    def close(self):
        """Clean possible outputs and close connection"""
        if self.serial is not None:
            self.serial.close()

    def read(self) -> bytearray:
        """
        Reads output and returns bytearray. Returned bytearray will be empty if the response was a simple OK.
        If errors occur a ConnectionError will be raised.
        """

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        header_data = bytearray(2)
        header_length = self.serial.readinto(header_data)
        if header_length != len(header_data):
            raise ConnectionError(f'Reading failed, expected length of header response ({header_length}) is not {len(header_data)}!')
        if header_data[0] != self.ReturnCode.OK:
            raise ConnectionError(f'Got error connection code: {header_data[0]}')

        return_length = int(header_data[1])
        if return_length == 0:
            return bytearray()

        return_data = bytearray(return_length)
        return_length = self.serial.readinto(return_data)
        if return_length != len(return_data):
            raise ConnectionError(f'Reading failed, expected length of data response ({return_length}) is not {len(return_data)}!')
        return return_data

    def write(
        self,
        opc: OpCode,
        p1: int,
        p2: int,
        p1a: int | None = None,
        data: bytearray | None = None
    ):
        """
        Writes bytes to lucid control

        :param opc: operation code from <LucidControl.OpCode>
        :param p1: parameter 1
        :param p2: parameter 2
        :param p1a: (optional) parameter 1a
        :param data: (optional) additional data to send
        """

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        if data is None:
            data = bytearray()

        if p1a is not None:
            data_write = bytearray([opc, p1, p1a, p2])
        else:
            data_write = bytearray([opc, p1, p2])
        data_write.append(len(data))
        data_write += data

        GlobalConf.logger.debug(f'Data {data_write} was written to port {self.comport}')
        self.serial.write(data_write)

    def query(
        self,
        opc: OpCode,
        p1: int,
        p2: int,
        p1a: int | None = None,
        data: bytearray | None = None
    ) -> bytearray:
        """
        Querries bytes from lucid control

        :param opc: operation code from <LucidControl.OpCode>
        :param p1: parameter 1
        :param p2: parameter 2
        :param p1a: (optional) parameter 1a
        :param data: (optional) additional data to send
        """

        self.write(opc, p1, p2, p1a, data)
        return self.read()

    def parameterGet(
        self,
        p_addr: ParamAddress,
        channel: int
    ) -> bytearray:
        """
        Returns parameter

        :param p_addr: parameter address
        :param channel: channel
        """

        if channel >= self.channels:
            raise ValueError(f'Channel {channel} out of range, must be in [0-{self.channels}]')

        data_write = bytearray()
        data_write += bytearray(struct.pack("<H", p_addr))

        return self.query(self.OpCode.GETPARAM, channel, 0, data=data_write)

    def parameterSet(
        self,
        p_addr: ParamAddress,
        channel: int,
        persistent: bool,
        data: bytearray | None = None,
        default: bool = False
    ) -> bool:
        """
        Sets parameter

        :param p_addr: parameter address
        :param channel: channel
        :param persistent: if changes should persist
        :param data: additional data
        :param default: use default parameter
        :return: if successfully
        """

        if data is None and not default:
            raise ValueError('Either data or default must be defined')

        if channel >= self.channels:
            raise ValueError(f'Channel {channel} out of range, must be in [0-{self.channels}]')

        data_write = bytearray()

        p2 = 0x00
        if default:
            p2 = 0x01
        if persistent:
            p2 |= 0x80

        data_write += bytearray(struct.pack('<H', p_addr))
        if not default:
            data_write += data

        query = self.query(self.OpCode.SETPARAM, channel, p2, data=data_write)
        return not len(query)

    def identify(self, options: int = 0):
        """
        Identifies the lucid control

        :param options: (optional) provided options
        """

        query = self.query(self.OpCode.GETID, 0, options)
        self.id.set(
            revision_fw=struct.unpack("<H", query[0:2])[0],
            revision_hw=struct.unpack("B", query[2:3])[0],
            device_class=struct.unpack("<H", query[3:5])[0],
            device_type=struct.unpack("<H", query[5:7])[0],
            device_snr=struct.unpack("<I", query[7:11])[0]
        )

    def serialNumberGet(self) -> int:
        """Returns serial number of device"""
        if not self.id.valid_data:
            return -1
        return self.id.device_snr

    def deviceClassGet(self) -> str:
        """Returns name of device class"""
        if not self.id.valid_data:
            return 'Device not registered'

        for device_class in self.DeviceClass:
            if device_class.value[0] == self.id.device_class:
                return device_class.value[1]
        return f'Device Class {self.id.device_class} not defined'

    def deviceTypeGet(self) -> str:
        """Returns name of device type"""
        if not self.id.valid_data:
            return 'Device not registered'

        for device_type in self.DeviceType:
            if device_type.value[0] == self.id.device_type:
                return device_type.value[1]
        return f'Device Type {self.id.device_type} not defined'

    def revisionFirmwareGet(self) -> int:
        """Returns the firmware revision number"""
        if not self.id.valid_data:
            return -1
        return self.id.revision_fw

    def revisionHardwareGet(self) -> int:
        """Returns the hardware revision number"""
        if not self.id.valid_data:
            return -1
        return self.id.revision_hw

    def ioGet(self, channel: int) -> float:
        """Return voltage on one channel"""
        if channel >= self.channels:
            raise ValueError(f'Channel {channel} out of range, must be in [0-{self.channels}]')
        query = self.query(self.OpCode.GETIO, channel, 0x1D)  # 0x1D is opcode for 4 byte voltage value
        return struct.unpack("<i", query)[0] / 1000000.0

    def ioGroupGet(self, channels: tuple[bool, ...]) -> tuple[float, ...]:
        """Return voltage for multiple channels"""
        if len(channels) != self.channels:
            raise ValueError(f'Exactly {self.channels} must be defined. There were {len(channels)} channels defined')

        # Build Channel Mask and count values
        channel_mask = 0
        for i, channel in enumerate(channels):
            if channel:
                channel_mask |= (1 << i)

        p1 = channel_mask & 0x7F  # Channels 0-6 in P1
        p1a = None
        if channel_mask > 0x7F:
            p1 |= 0x80
            p1a = (channel_mask >> 7) & 0x7F

        query = self.query(self.OpCode.GETIO_GROUP, p1, 0x1D, p1a)  # 0x1D is opcode for 4 byte voltage value

        output = []
        j = 0  # Marker in data frame
        for i, channel in enumerate(channels):
            if not channel:
                output.append(0)
                continue
            output.append(struct.unpack("<i", query[4 * j: 4 * (j + 1)])[0] / 1000000.0)
            j = j + 1

        return tuple(output)

    def valueGet(self, channel: int) -> int:
        """Returns the configuration parameter 'Value' for one channel"""
        data = self.parameterGet(self.ParamAddress.VALUE, channel)
        return struct.unpack("<H", data)[0]

    def modeSet(self, channel: int, mode: int, persistent: bool = False) -> bool:
        """Sets the mode for one channel"""
        data = bytearray([mode])
        return self.parameterSet(self.ParamAddress.MODE, channel, persistent, data=data)

    def modeSetDefault(self, channel: int, persistent: bool = False) -> bool:
        """Resets the mode for one channel"""
        return self.parameterSet(self.ParamAddress.MODE, channel, persistent, default=True)

    def modeGet(self, channel: int) -> int:
        """Returns the mode for one channel"""
        return self.parameterGet(self.ParamAddress.MODE, channel)[0]

    def flagsSetDefault(self, channel: int, persistent: bool = False) -> bool:
        """Resets the flags for one channel"""
        return self.parameterSet(self.ParamAddress.FLAGS, channel, persistent)

    def sampleNumberSet(self, channel: int, sample_number: int, persistent: bool = False) -> bool:
        """Sets the number of samples for one channel"""
        if sample_number < 0:
            raise ValueError('Sample number must be above 0')
        data = bytearray(struct.pack("<H", sample_number))
        return self.parameterSet(self.ParamAddress.NR_SAMPLES, channel, persistent, data=data)

    def sampleNumberSetDefault(self, channel: int, persistent: bool = False) -> bool:
        """Resets the number of samples to default for one channel"""
        return self.parameterSet(self.ParamAddress.NR_SAMPLES, channel, persistent, default=True)

    def sampleNumberGet(self, channel: int) -> int:
        """Returns the number of samples for one channel"""
        data = self.parameterGet(self.ParamAddress.NR_SAMPLES, channel)
        if not data:
            return 0
        else:
            return struct.unpack("<H", data)[0]

    def offsetSet(self, channel: int, offset: int, persistent: bool = False) -> bool:
        """Sets the offset for one channel"""
        if offset < -pow(2, 15) or offset >= pow(2, 16):
            raise ValueError('Offset out of range [-2^15 to 2^16] are allowed')
        data = bytearray(struct.pack("<h", offset))
        return self.parameterSet(self.ParamAddress.OFFSET, channel, persistent, data=data)

    def offsetSetDefault(self, channel: int, persistent: bool = False) -> bool:
        """Resets the offset to default for one channel"""
        return self.parameterSet(self.ParamAddress.OFFSET, channel, persistent, default=True)

    def offsetGet(self, channel: int) -> int:
        """Returns the offset for one channel"""
        data = self.parameterGet(self.ParamAddress.OFFSET, channel)
        if not data:
            return 0
        else:
            return struct.unpack("<H", data)[0]


def main():
    with LucidControlConnection('COM3') as lc:
        print(lc.ioGet(0))
        print(lc.ioGet(1))
        print(lc.ioGet(2))
        print(lc.ioGet(3))
        print(lc.ioGroupGet((True, True, True, True)))


if __name__ == '__main__':
    main()


"""
START EXAMPLE
PORT OPENED
=========================================================================
 IDENTIFY DEVICE
=========================================================================
INFO: writing data: bytearray(b'\xc0\x00\x00\x00')
INFO: reading data (length=2): bytearray(b'\x00\x10')
INFO: reading data (length=16): bytearray(b'\x16\x00\x03\x00\x01\x01\x10\x00\x00H#\x00\x00\x00\x00\x00')
Device Class:       ANALOG INPUT 4 CHANNELS
Device Type:        0 V ~ 10 V
Serial No.:         591921152
Firmware Rev.:      22
Hardware Rev.:      3
=========================================================================
 CONFIGURE NUMBER OF SAMPLES OF CHANNEL 0
=========================================================================
INFO: writing data: bytearray(b'\xa0\x00\x00\x04\x12\x11\x10\x00')
INFO: reading data (length=2): bytearray(b'\x00\x00')
=========================================================================
 READ VOLTAGE VALUE OF CHANNEL 0
=========================================================================
INFO: writing data: bytearray(b'F\x00\x1d\x00')
INFO: reading data (length=2): bytearray(b'\x00\x04')
INFO: reading data (length=4): bytearray(b'^\xcc\x1a\x00')
CH0 voltage is 1.756254 V
=========================================================================
 READ VOLTAGE VALUES OF CH0, CH1, CH2 AND CH3 AS GROUP
=========================================================================
INFO: writing data: bytearray(b'H\x0f\x1d\x00')
INFO: reading data (length=2): bytearray(b'\x00\x10')
INFO: reading data (length=16): bytearray(b'^\xcc\x1a\x00r<\x19\x00+\t\x00\x00\xcc\x0b\x00\x00')
CH0 is 1.756254 V, CH1 is 1.653874 V, CH2 is 0.002347 V, CH3 is 0.00302 V
END EXAMPLE
"""
