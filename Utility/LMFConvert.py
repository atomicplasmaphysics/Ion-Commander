from typing import BinaryIO
from datetime import datetime
import struct


def bits_to_dec(bits: list[bool]) -> int:
    """Convert bits array to integer"""
    number = 0
    for i, bit in enumerate(bits):
        number += bit
        if i + 1 < len(bits):
            number *= 2
    return number


def dec_to_bits(number: int, bits: int) -> list[bool]:
    """Converts integer to bits array"""
    if number < 0:
        raise ValueError('Number must be non-negative')
    if number >= 2 ** bits:
        raise ValueError(f'Number too large to fit in {bits} bits')
    return [bool((number >> i) & 1) for i in range(bits - 1, -1, -1)]


def read_bits(file: BinaryIO, number_of_bytes: int) -> list[bool]:
    """Reads number of bytes and returns list of int"""
    bits_total = []
    for _ in range(number_of_bytes):
        bits_total.extend(dec_to_bits(read_bytes(file, 1), 8))
    return bits_total


def read_double(file: BinaryIO) -> float:
    """Reads double from file"""
    return struct.unpack('d', file.read(8))[0]


def read_bool(file: BinaryIO) -> bool:
    """Reads bool from file"""
    return bool(struct.unpack('B', file.read(1))[0])


def read_bytes(file: BinaryIO, number_of_bytes: int, byte_char: str = '') -> int:
    """Reads bytes from file"""

    byte_chars = {
        1: 'B',
        4: 'L',
        8: 'Q'
    }

    if not byte_char:
        try:
            byte_char = byte_chars[number_of_bytes]
        except KeyError:
            raise ValueError(f'Reading of {number_of_bytes} bytes is not defined')

    return struct.unpack(byte_char, file.read(number_of_bytes))[0]


def read_char(file: BinaryIO, errors: str = 'ignore') -> str:
    """Reads character from file"""
    return file.read(1).decode(errors=errors)


def read_Cstring(file: BinaryIO, errors: str = 'ignore') -> str:
    """Reads CString from file"""
    return read_string(file, length_bits=1, errors=errors)


def read_string(file: BinaryIO, length_bits: int = 4, errors: str = 'ignore') -> str:
    """Reads CString from file"""
    string = ''
    for _ in range(read_bytes(file, length_bits)):
        string += read_char(file, errors=errors)
    return string


class TDC:

    def __init__(self):

        self._Initialized: bool = False

        self.DAQVersion: int = 0
        self.DAQID: int = 0

        self.frequency: float = 0
        self.IOAddress: int = 0
        self.timestampFormat: int = 0
        self.DAQInfo: str = ''
        self.UserHeaderVersion: int = 0
        self.LMFVersion: int = 0

        self.ignore_DAQ: bool = False
        self.DAQSourceCode_list: list[str] = []

        self.timeReference: int = 0
        self.TDCResolution: float = 0
        self.TDCDataType: int = 0
        self.NumberOfChannels: int = 0
        self.maxNumberOfHits: int = 0
        self.DataFormatUserHeader: int = 0

        self.NoConfigFileRead: bool = False
        self.RisingEnable: int = 0
        self.FallingEnable: int = 0
        self.TriggerEdge: int = 0
        self.TriggerChannel: int = 0
        self.OutputLevel: bool = False
        self.GroupingEnable: bool = False
        self.AllowOverlap: bool = False
        self.TriggerDeadTime: float = 0
        self.GroupRangeStart: float = 0
        self.GroupRangeEnd: float = 0
        self.ExternalClock: bool = False
        self.OutputRollOvers: bool = False

    def readTDC(self, file: BinaryIO, DAQ_Version: int, DAQ_ID: int, ignore_DAQ: bool = False):
        """Reads TDC data"""

        self.DAQVersion = DAQ_Version
        self.DAQID = DAQ_ID
        self.ignore_DAQ = ignore_DAQ

        if self.DAQID == 0x8 or self.DAQID == 0x10:
            self._readTDC8HP(file)
        else:
            raise NotImplementedError(f'Reading DAQ ID {self.DAQID} is not implemented yet.')

    def _readTDC8HP(self, file: BinaryIO):
        """Reads TDC data from TDC8HP"""

        self.frequency = read_double(file)
        self.IOAddress = read_bytes(file, 4)
        self.timestampFormat = read_bytes(file, 4)

        self.DAQInfo = read_string(file)

        if self.DAQVersion > 20080000:
            self.UserHeaderVersion = 4

        if self.UserHeaderVersion >= 1:
            self.LMFVersion = read_bytes(file, 4)
            if self.LMFVersion == 8:
                self.UserHeaderVersion = 5
            elif self.LMFVersion == 9:
                self.UserHeaderVersion = 6
            elif self.LMFVersion >= 10:
                self.UserHeaderVersion = 7
            elif self.LMFVersion >= 11:
                self.UserHeaderVersion = 8

        if self.UserHeaderVersion >= 7:
            self._readTDC8HP_LMFV_10(file)
        else:
            raise NotImplementedError(f'Not implemented for UserHeaderVersion of {self.UserHeaderVersion} yet.')

        self._Initialized = True

    def _readTDC8HP_LMFV_10(self, file: BinaryIO):
        """Reads TDC data from TDC8HP for LMF Version 10"""

        if self.ignore_DAQ:
            for _ in range(read_bytes(file, 4)):
                file.seek(file.tell() + 4 + read_bytes(file, 4))
        else:
            for _ in range(read_bytes(file, 4)):
                self.DAQSourceCode_list.append(read_string(file))

        self.timeReference = read_bytes(file, 4)
        self.TDCResolution = read_double(file)
        self.TDCDataType = read_bytes(file, 4)
        self.NumberOfChannels = read_bytes(file, 8)
        self.maxNumberOfHits = read_bytes(file, 8)
        self.DataFormatUserHeader = read_bytes(file, 4)

        self.NoConfigFileRead = read_bool(file)
        self.RisingEnable = read_bytes(file, 8)
        self.FallingEnable = read_bytes(file, 8)
        self.TriggerEdge = read_bytes(file, 4)
        self.TriggerChannel = read_bytes(file, 4)
        self.OutputLevel = read_bool(file)
        self.GroupingEnable = read_bool(file)
        self.AllowOverlap = read_bool(file)
        self.TriggerDeadTime = read_double(file)
        self.GroupRangeStart = read_double(file)
        self.GroupRangeEnd = read_double(file)
        self.ExternalClock = read_bool(file)
        self.OutputRollOvers = read_bool(file)

        # TODO: maybe also get other parameters if needed

    def __repr__(self):
        if not self._Initialized:
            raise RuntimeError('TDC not initialized yet')
        output_dict = {
            'Frequency': self.frequency,
            'IOAddress': self.IOAddress,
            'timestampFormat': self.timestampFormat,
            'DAQInfo': self.DAQInfo,
            'UserHeaderVersion': self.UserHeaderVersion,
            'LMFVersion': self.LMFVersion,
            'DAQSourceCode': len(self.DAQSourceCode_list),
            'timeReference': datetime.fromtimestamp(self.timeReference),
            'TDCResolution': self.TDCResolution,
            'TDCDataType': self.TDCDataType,
            'NumberOfChannels': self.NumberOfChannels,
            'maxNumberOfHits': self.maxNumberOfHits,
            'DataFormatUserHeader': self.DataFormatUserHeader,
            'NoConfigFileRead': self.NoConfigFileRead,
            'RisingEnable': self.RisingEnable,
            'FallingEnable': self.FallingEnable,
            'TriggerEdge': self.TriggerEdge,
            'TriggerChannel': self.TriggerChannel,
            'OutputLevel': self.OutputLevel,
            'GroupingEnable': self.GroupingEnable,
            'AllowOverlap': self.AllowOverlap,
            'TriggerDeadTime': self.TriggerDeadTime,
            'GroupRangeStart': self.GroupRangeStart,
            'GroupRangeEnd': self.GroupRangeEnd,
            'ExternalClock': self.ExternalClock,
            'OutputRollOvers': self.OutputRollOvers,
        }
        return 'TDC(' + ', '.join([f'{key}={value}' for key, value in output_dict.items()]) + ')'


class LM:

    def __init__(self):

        self._Initialized: bool = False

        self._filepath: str = ''
        self._EventOffset: int = 0

        self.TDC: TDC = TDC()

        self.HeaderVersion: int = 0
        self.DataFormat: int = 0
        self.NumberOfCoordinates: int = 0
        self.HeaderSize: int = 0
        self.UserHeaderSize: int = 0
        self.NumberOfEvents: int = 0
        self.StartTime: float = 0
        self.StopTime: float = 0
        self.VersionString: str = ''
        self.FilePathName: str = ''
        self.Comment: str = ''

        self.DAQSourceCode: bool = False
        self.DANSourceCode: bool = False
        self.CCFHistory: bool = False

        self.DAQVersion: int = 0
        self.DAQID: int = 0

        self.CCFHistory_list: list[str] = []
        self.DANSourceCode_list: list[str] = []

        self.int_size: int = 0

    def reset(self):
        """Resets self"""
        self.__init__()

    def readLMF(self, filepath: str, ignore_DAN: bool = False, ignore_DAQ: bool = False):
        """Reads LMF file and fills own parameters"""

        if self._Initialized:
            raise ValueError('Was already initialized, reset first.')

        self._filepath = filepath

        try:
            with open(self._filepath, 'rb') as file:
                # get general header
                self.HeaderVersion = read_bytes(file, 4)
                self._updateHeaderVersion()
                self.DataFormat = read_bytes(file, 4)
                self.NumberOfCoordinates = read_bytes(file, self.int_size)
                self.HeaderSize = read_bytes(file, self.int_size)
                self.UserHeaderSize = read_bytes(file, self.int_size)
                self.NumberOfEvents = read_bytes(file, self.int_size)

                file.read(4)
                self.StartTime = read_bytes(file, 4)
                file.read(4)

                file.read(4)
                self.StopTime = read_bytes(file, 4)
                file.read(4)

                self.VersionString = read_Cstring(file)
                self.FilePathName = read_Cstring(file)
                self.Comment = read_Cstring(file)

                # CCF history strings
                if self.CCFHistory:
                    for _ in range(read_bytes(file, 4)):
                        self.CCFHistory_list.append(read_string(file))

                # DAN source code strings
                if self.DANSourceCode:
                    if ignore_DAN:
                        for _ in range(read_bytes(file, 4)):
                            file.seek(file.tell() + 4 + read_bytes(file, 4))
                    else:
                        for _ in range(read_bytes(file, 4)):
                            self.DANSourceCode_list.append(read_string(file))

                # Sanity check
                if self.int_size == 8:
                    self.HeaderVersion = read_bytes(file, 4)
                user_header_size_sanity = read_bytes(file, self.int_size)

                if user_header_size_sanity != self.UserHeaderSize:
                    raise ValueError('Something is wrong in the user data section...')

                # DAQ information
                self.DAQVersion = read_bytes(file, 4)
                self.DAQID = read_bytes(file, 4)

                # TDC stuff
                self.TDC.readTDC(file, self.DAQVersion, self.DAQID, ignore_DAQ)

                # set self to initialized
                self._Initialized = True

        except (FileNotFoundError, OSError):
            raise FileNotFoundError(f'File "{self._filepath}" could not be opened or found.')

    def _readEventTDC8HPRawFormatNoGroupingNewUserHeaderLMFV11(self, file: BinaryIO):
        """Read next event from file"""
        # TODO: not implemented fully yet - probably never needed since python would be too slow for reading anyways

        try:
            start_tell = file.tell()

            bits = read_bits(file, read_bytes(file, 4) * 4)
            # TODO: do something with bits

            changed_mask_read = read_bytes(file, 4)
            if changed_mask_read:
                for _ in range(32):
                    read_double(file)

            for _ in range(read_bytes(file, 4)):
                file.read(1)

            self._EventOffset += file.tell() - start_tell
            return True

        except struct.error:
            return False

    def readEvent(self):
        """Read next event from file"""
        # TODO: not implemented fully yet - probably never needed since python would be too slow for reading anyways

        if not self._Initialized:
            raise ValueError('LM was not initialized yet.')

        try:
            with open(self._filepath, 'rb') as file:
                file.seek(self.HeaderSize + self.UserHeaderSize + self._EventOffset)
                if self.TDC.GroupingEnable and self.TDC.UserHeaderVersion >= 5 and self.DAQID == 0x10 and self.TDC.LMFVersion >= 11:
                    return self._readEventTDC8HPRawFormatNoGroupingNewUserHeaderLMFV11(file)
                else:
                    raise NotImplementedError('These TDC parameters are not implemented yet.')

        except (FileNotFoundError, OSError):
            raise FileNotFoundError(f'File "{self._filepath}" could not be opened or found.')

    def readEvents(self):
        """Read all events from file"""
        # TODO: not implemented fully yet - probably never needed since python would be too slow for reading anyways

        if not self._Initialized:
            raise ValueError('LM was not initialized yet.')

        try:
            with open(self._filepath, 'rb') as file:
                file.seek(self.HeaderSize + self.UserHeaderSize)
                # TODO: self.readEvent() in a loop and return total data

        except (FileNotFoundError, OSError):
            raise FileNotFoundError(f'File "{self._filepath}" could not be opened or found.')

    def _updateHeaderVersion(self):
        """Updates the header version, should be called after setting the header version"""

        if not isinstance(self.HeaderVersion, int):
            raise ValueError('HeaderVersion has not yet been set')

        header_bits = dec_to_bits(self.HeaderVersion, 32)

        self.DAQSourceCode = header_bits[31]
        self.DANSourceCode = header_bits[30]
        self.CCFHistory = header_bits[29]

        # get actual header version
        actual_version = bits_to_dec(header_bits[3:])
        if actual_version == 0 or actual_version == 0x74656:
            self.int_size = 4
        elif actual_version == 0x74657:
            self.int_size = 8
        else:
            raise NotImplementedError(f'Unknown version with LMHeaderVersion = {hex(actual_version)}')

    def __repr__(self):
        if not self._Initialized:
            raise RuntimeError('LM not initialized yet')
        output_dict = {
            'HeaderVersion': hex(self.HeaderVersion),
            'IntSize': self.int_size,
            'DataFormat': hex(self.DataFormat),
            'NumberOfCoordinates': self.NumberOfCoordinates,
            'HeaderSize': self.HeaderSize,
            'UserHeadSize': self.UserHeaderSize,
            'NumberOfEvents': self.NumberOfEvents,
            'StartTime': datetime.fromtimestamp(self.StartTime),
            'StopTime': datetime.fromtimestamp(self.StopTime),
            'VersionString': self.VersionString,
            'FilePathName': self.FilePathName,
            'Comment': self.Comment,
            'DANSourceCode': len(self.DANSourceCode_list),
            'CCFHistory': len(self.CCFHistory_list),
            'DAQVersion': self.DAQVersion,
            'DAQID': self.DAQID,
            'TDC': self.TDC
        }
        return 'LM(' + ', '.join([f'{key}={value}' for key, value in output_dict.items()]) + ')'


def main():
    from time import time

    lm = LM()
    lm.readLMF(f'C:/Users/Alex/Uni/TU/Doktorat/Laser/Messungen/240618_Equal_inputs/from_picoTimingDiscriminator_16ns_100s.lmf', ignore_DAN=True, ignore_DAQ=True)
    print(lm)

    start = time()
    i = 0
    while True:
        if i % 10000 == 0:
            print(f'Event {i}')
        if not lm.readEvent():
            break
        i += 1
    print(f'Event {i}')
    print(f'Took {time() - start} seconds to read from file')


if __name__ == '__main__':
    main()
