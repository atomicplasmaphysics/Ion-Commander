from enum import Enum, auto


from Config.GlobalConf import GlobalConf

from Connection.USBPorts import COMConnection


def convertInUnitList(data: list, unit: str = '') -> list[str | float]:
    """Tries to convert list of strings and given unit into list with applied conversion function. If it fails, a stripped list will be returned."""

    return_data = [d.strip() for d in data]

    # try to convert into conversion function
    try:
        return [float(d.replace(unit, '')) for d in return_data]
    except ValueError:
        return return_data


def convertToString(inp: float | int, precision: int = 6):
    """Converts a float or integer to a scientific notation with given precision"""
    return f'{float(inp):.{precision}E}'


class KeithleyPAmeterConnection(COMConnection):
    """
    Context manager for Keithley PAmeter Serial connection, built on top of the COMConnection context manager

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param echo: If device has echo. Will be checked
    :param cleaning: If output cache should be cleared when entering and exiting
    :param strict: If identification string should contain <strict>-string
    """

    class EchoMode(Enum):
        """Different echo modes"""
        ECHO_ENABLED = auto()
        ECHO_DISABLED = auto()
        ECHO_AUTO = auto()

    class MemoryLocation(Enum):
        """Memory locations of user-programs"""
        LOC_0 = '0'
        LOC_1 = '1'
        LOC_2 = '2'

    class LineFrequency(Enum):
        """Line frequencies"""
        HZ_50 = 50
        HZ_60 = 60

    class Functions(Enum):
        VOLTAGE = 'VOLT'
        CURRENT = 'CURR'
        RESISTANCE = 'RES'
        CHARGE = 'CHAR'

    class VoltageRange(Enum):
        """Supported voltage ranges"""
        AUTO = 0
        _2V = '2'
        _20V = '20'
        _200V = '200'

    class CurrentRange(Enum):
        """Supported current ranges"""
        AUTO = 0
        _20pA = '20e-12'
        _200pA = '200e-12'
        _2nA = '2e-9'
        _20nA = '20e-9'
        _200nA = '200e-9'
        _2uA = '2e-6'
        _20uA = '20e-6'
        _200uA = '200e-6'
        _2mA = '2e-3'
        _20mA = '20e-3'

    class ResistanceRange(Enum):
        """Supported resistance ranges"""
        AUTO = 0
        _2kR = '2e3'
        _20kR = '20e3'
        _200kR = '200e3'
        _2MR = '2e6'
        _20MR = '20e6'
        _200MR = '200e6'
        _2GR = '2e9'
        _20GR = '20e9'
        _200GR = '200e9'

    class ChargeRange(Enum):
        """Supported charge ranges"""
        AUTO = 0
        _20nC = '20e-9'
        _200nC = '200e-9'
        _2uC = '2e-6'
        _20uC = '20e-6'

    def __init__(
        self,
        comport: str,
        timeout: float = 1,
        encoding: str = 'utf-8',
        echo: EchoMode = EchoMode.ECHO_AUTO,
        cleaning: bool = True,
        strict: str = ''
    ):
        self.echo_mode = echo
        self.strict = strict

        super().__init__(
            comport,
            timeout=timeout,
            encoding=encoding,
            tx_term='\r',
            echo=True if echo == self.EchoMode.ECHO_ENABLED else False,
            cleaning=cleaning
        )

    def open(self):
        """Opens the connection"""
        super().open()

        # detect echo mode
        if self.echo_mode == self.EchoMode.ECHO_AUTO:
            cmd = '*IDN?'
            self.write(cmd)

            if self.readline().strip() == cmd:
                self.echo = True

            GlobalConf.logger.info(f'<KeithleyPAmeterConnection> auto-detected echo-mode on port "{self.comport}" to {self.echo}')
            self.clean()

        # detect if it is KeithleyPAmeterConnection device
        identification = self.identification()
        if self.strict and self.strict not in identification:
            GlobalConf.logger.warning(f'<KeithleyPAmeterConnection> on port "{self.comport}" does not identify with "{self.strict}". Identification is {identification!r}')
            raise ConnectionError(f'Device identification {identification!r} does not contain {self.strict!r}')

        return self

    @staticmethod
    def _on_off(state: bool | int) -> str:
        """Convert state to 'ON' or 'OFF' string"""
        return 'ON' if state else 'OFF'

    def _queryAndReturn(self, cmd: str) -> str:
        """Queries command and returns striped result"""
        self.write(cmd)
        return self.readline().strip()

    def _queryAndReturnFloat(self, cmd: str, unit: str = '') -> float:
        """Queries command and returns striped result as float without unit. If float conversion fails, -1 will be returned."""
        try:
            result = self._queryAndReturn(cmd).replace(unit, '')
            return float(result)
        except ValueError:
            return -1

    def _queryAndReturnInt(self, cmd: str, unit: str = '') -> int:
        """Queries command and returns striped result as integer without unit. If integer conversion fails, -1 will be returned."""
        return int(self._queryAndReturnFloat(cmd, unit))

    def _queryAndReturnList(self, cmd: str, unit: str = '') -> list:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list"""
        return convertInUnitList(self._queryAndReturn(cmd).split(','), unit)

    def identification(self) -> str:
        """Returns the manufacturer, model number, serial number, and firmware revision levels of the unit"""
        return self._queryAndReturn('*IDN?')

    def clearStatus(self):
        """Clears all event registers and error queue"""
        self._queryAndReturn('*CLS')

    def resetDevice(self):
        """Reset the device to default condition"""
        self._queryAndReturn('*RST')

    def saveState(self, location: MemoryLocation):
        """Saves the present setup as the user-saved setup"""
        self._queryAndReturn(f'*SAV {location.value}')

    def loadState(self, location: MemoryLocation):
        """"Returns into to the user-saved setup"""
        self._queryAndReturn(f'*RCL {location.value}')

    def setLineFrequency(self, frequency: LineFrequency):
        """Select power line frequency (in Hz); 50 or 60"""
        self._queryAndReturn(f'SYST:LFR {frequency.value}')

    def getLineFrequency(self) -> int:
        """Read present line frequency setting"""
        return self._queryAndReturnInt('SYST:LFR?')

    def acquireZeroCorrect(self):
        """Acquire a new zero correct value"""
        self._queryAndReturn('SYST:ZCOR:ACQ')

    def setAutoZero(self, state: bool | int):
        """Enable or disable autozero"""
        self._queryAndReturn(f'SYST:AZER {self._on_off(state)}')

    def setZeroCheck(self, state: bool | int):
        """Enable or disable zero check"""
        self._queryAndReturn(f'SYST:ZCH {self._on_off(state)}')

    def setZeroCorrect(self, state: bool | int):
        """Enable or disable zero correct"""
        self._queryAndReturn(f'SYST:ZCOR {self._on_off(state)}')

    def initiate(self):
        """Trigger a reading"""
        # TODO: does this return something?!
        return self._queryAndReturn('INIT')

    def calibrateCurrentOffset(self):
        """Input bias current calibration"""
        self._queryAndReturn(':CAL:UNPR:IOFF')

    def calibrateVoltageOffset(self):
        """Offset voltage calibration"""
        self._queryAndReturn(':CAL:UNPR:VOFF')

    def selectFunction(self, function: Functions):
        """Select sensing function"""
        self._queryAndReturn(f'FUNC "{function.value}"')

    def getLastData(self) -> float:
        """Return latest 'raw' reading"""
        # TODO: is this really a float
        return self._queryAndReturnFloat('SENS:DATA?')

    def readData(self) -> list[float]:
        """Trigger and return reading(s)"""
        return self._queryAndReturnList('READ?')

    def setVoltageRange(self, input_range: VoltageRange):
        """Sets voltage range"""
        if input_range == KeithleyPAmeterConnection.VoltageRange.AUTO:
            self._queryAndReturn('VOLT:RANG:AUTO ON')
        else:
            self._queryAndReturn(f'VOLT:RANG {input_range.value}')

    def setVoltageGuard(self, state: bool | int):
        """Enable or disable guard"""
        self._queryAndReturn(f'SENS:VOLT:GUAR {self._on_off(state)}')

    def setResistanceRange(self, input_range: ResistanceRange):
        """Sets resistance range"""
        if input_range == KeithleyPAmeterConnection.ResistanceRange.AUTO:
            self._queryAndReturn('RES:RANG:AUTO ON')
        else:
            self._queryAndReturn(f'RES:RANG {input_range.value}')

    def setResistanceGuard(self, state: bool | int):
        """Enable or disable guard"""
        self._queryAndReturn(f'SENS:RES:GUAR {self._on_off(state)}')

    def setCurrentRange(self, input_range: CurrentRange):
        """Sets current range"""
        if input_range == KeithleyPAmeterConnection.CurrentRange.AUTO:
            self._queryAndReturn('CURR:RANG:AUTO ON')
        else:
            self._queryAndReturn(f'CURR:RANG {input_range.value}')

    def setCurrentDamping(self, state: bool | int):
        """Enable or disable damping"""
        self._queryAndReturn(f'SENS:CURR:DAMP {self._on_off(state)}')

    def setChargeRange(self, input_range: ChargeRange):
        """Sets charge range"""
        if input_range == KeithleyPAmeterConnection.ChargeRange.AUTO:
            self._queryAndReturn('CHAR:RANG:AUTO ON')
        else:
            self._queryAndReturn(f'CHAR:RANG {input_range.value}')

    def setChargeAutoDischarge(self, state: bool | int):
        """Enable or disable auto discharge"""
        self._queryAndReturn(f'SENS:CHAR:ADI:STATE {self._on_off(state)}')

    def setChargeAutoDischargeLevel(self, level: float):
        """Set auto discharge level; -2.1e-5 to 2.1e-5"""
        self._queryAndReturn(f'SENS:CHAR:ADI:LEV {convertToString(level)}')


def main():
    with KeithleyPAmeterConnection(
        comport='COM7',
        echo=KeithleyPAmeterConnection.EchoMode.ECHO_AUTO,
        cleaning=True,
        strict='KEITHLEY INSTRUMENTS INC.,MODEL 6514,4310331,A13'  # Keithley 6514
    ) as pam:
        print('***** GENERAL VALUES *****')
        print(f'{pam.echo = }')
        print(f'{pam.identification() = }')
        print('\n')

        print('***** READING VALUES *****')
        #print(f'{pam.readVoltage(0) = }')
        #print(f'{pam.readCurrent(0) = }')
        #print(f'{pam.measureVoltage(0) = }')
        #print(f'{pam.measureCurrent(0) = }')
        #print(f'{pam.readVoltageBoundaries(0) = }')
        #print(f'{pam.readCurrentBoundaries(0) = }')
        #print(f'{pam.readVoltageLimit(0) = }')
        #print(f'{pam.readCurrentLimit(0) = }')
        #print(f'{pam.crateStatus() = }')
        #print(f'{pam.readChannelControl(0) = }')
        #print(f'{pam.readChannelStatus(0) = }')
        #print(f'{pam.readChannelEventStatus(0) = }')
        #print(f'{pam.readChannelEventMask(0) = }')
        #print(f'{pam.configureRampVoltageGet() = }')
        print('\n')

        print('***** SETTING VALUES *****')
        #print(f'{pam.voltageSet(0, 10) = }')
        #print(f'{pam.currentSet(0, 5E-6) = }')
        print('\n')


if __name__ == '__main__':
    main()
