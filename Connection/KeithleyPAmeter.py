"""
Keithley Model 6514 System Electrometer via RS-232 (SCPI), see the manual "D:/Datasheets/Keithley 6514.pdf".

RS-232 settings of the instrument (front panel: SHIFT + RS-232): baud rate 9600 , 8 data bits, no parity,
no flow control. The response terminator (LF, CR, CRLF or LFCR) can be chosen freely, all of them are accepted.
Commands are terminated with CR (the instrument processes a command after <CR>).

Readings are returned with the data elements READing, TIME and STATus (FORMat:ELEMents), e.g.
"+1.040564E-06,+2.236299E+02,+1.380000E+02" = 1.04 uA, 223.6 s after power on, status word 138.
An overflowed reading is returned as +9.9E37 (converted to nan by the read functions).
"""

import re
from enum import Enum, auto
from math import isfinite, nan, sqrt
from time import monotonic, sleep
from typing import NamedTuple


from Config.GlobalConf import GlobalConf

from Connection.USBPorts import COMConnection


KEITHLEY_NUMBER_PATTERN = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


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


def parseNumbers(response: str) -> list[float]:
    """Returns all numbers of a response (units or suffixes like "NADC" are ignored)"""
    return [float(number) for number in KEITHLEY_NUMBER_PATTERN.findall(response)]


class KeithleyReading(NamedTuple):
    """
    One reading of the electrometer

    :param value: reading (A, V, Ohm or C); nan if overflowed
    :param timestamp: seconds since power on (or reset of the timestamp)
    :param status: 16 bit status word
    """

    value: float
    timestamp: float
    status: int

    @property
    def overflow(self) -> bool:
        """Reading was overflowed (bit 0)"""
        return bool(self.status & 1) or not isfinite(self.value)

    @property
    def zero_check(self) -> bool:
        """Zero check was enabled (bit 9) - the reading is not the input signal"""
        return bool(self.status & (1 << 9))

    @property
    def zero_correct(self) -> bool:
        """Zero correct was enabled (bit 10)"""
        return bool(self.status & (1 << 10))

    @property
    def function(self) -> str:
        """Measured function (bits 7 and 8)"""
        return ['VOLT', 'CURR', 'RES', 'CHAR'][(self.status >> 7) & 0b11]


class KeithleyPAmeterConnection(COMConnection):
    """
    Context manager for the Keithley 6514 electrometer (RS-232), built on top of the COMConnection context manager

    :param comport: COM Port
    :param timeout: Timeout for one character [in s]
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
        self.elements = 3  # READing, TIME, STATus
        self.nplc = 5.
        self.trigger_count = 1
        # front panel mode measures continuously (ARM:COUN INF), restored on close
        self.continuous_on_close = False

        super().__init__(
            comport,
            timeout=timeout,
            encoding=encoding,
            baudrate=9600,
            tx_term='\r',
            echo=True if echo == self.EchoMode.ECHO_ENABLED else False,
            cleaning=cleaning
        )

    # ------------------------------------------------------------------ connection
    def open(self):
        """Opens the connection, checks the identification and sets the data format"""

        super().open()
        self.breakOperation()

        # detect echo mode
        if self.echo_mode == self.EchoMode.ECHO_AUTO:
            cmd = '*IDN?'
            self.write(cmd)
            first_line = self._readResponse()
            if first_line == cmd:
                self.echo = True
                self._readResponse()
            GlobalConf.logger.info(f'<KeithleyPAmeterConnection> auto-detected echo-mode on port "{self.comport}" to {self.echo}')
            self.clean()

        # detect if it is KeithleyPAmeterConnection device
        identification = self.identification()
        if not identification:
            raise ConnectionError(f'No answer from the electrometer on port "{self.comport}" (check baud rate and RS-232 settings)')
        if self.strict and self.strict not in identification:
            GlobalConf.logger.warning(f'<KeithleyPAmeterConnection> on port "{self.comport}" does not identify with "{self.strict}". Identification is {identification!r}')
            raise ConnectionError(f'Device identification {identification!r} does not contain {self.strict!r}')

        self.setFormatElements()
        self.setupTrigger()
        self.nplc = self.getNPLC()
        return self

    def close(self):
        """Puts the instrument back into local mode (front panel usable) and closes the connection"""

        if self.serial is not None:
            try:
                if self.continuous_on_close:
                    self.presetFrontPanel()
                self.setLocal()
            except Exception as error:
                GlobalConf.logger.debug(f'<KeithleyPAmeterConnection> could not set local mode: {error}')
        super().close()

    # ------------------------------------------------------------------ low level
    @staticmethod
    def _on_off(state: bool | int) -> str:
        """Convert state to 'ON' or 'OFF' string"""
        return 'ON' if state else 'OFF'

    def _readResponse(self, timeout: float | None = None) -> str:
        """
        Reads one response line, terminated by CR, LF, CRLF or LFCR

        :param timeout: maximum time in s until the response must be complete (default: serial timeout)
        """

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        deadline = monotonic() + (timeout if timeout is not None else self.timeout)
        data = bytearray()
        while True:
            byte = self.serial.read(1)
            if not byte:
                if monotonic() > deadline:
                    break
                continue
            if byte in (b'\r', b'\n'):
                # a leading terminator is the rest of a CRLF/LFCR of the last response
                if not data:
                    continue
                break
            data += byte
        return data.decode(self.encoding, errors='replace').strip()

    def _write(self, cmd: str):
        """Sends a command without response"""
        self.write(cmd)

    def _queryAndReturn(self, cmd: str, timeout: float | None = None) -> str:
        """Queries command and returns striped result"""
        self.write(cmd)
        return self._readResponse(timeout)

    def _queryAndReturnFloat(self, cmd: str, unit: str = '') -> float:
        """Queries command and returns striped result as float without unit. If float conversion fails, -1 will be returned."""
        numbers = parseNumbers(self._queryAndReturn(cmd).replace(unit, ''))
        return numbers[0] if numbers else -1

    def _queryAndReturnInt(self, cmd: str, unit: str = '') -> int:
        """Queries command and returns striped result as integer without unit. If integer conversion fails, -1 will be returned."""
        return int(self._queryAndReturnFloat(cmd, unit))

    def _queryAndReturnBool(self, cmd: str) -> bool:
        """Queries command and returns ON/1 as True"""
        return self._queryAndReturn(cmd).strip().upper() in ('1', 'ON')

    def _queryAndReturnList(self, cmd: str, unit: str = '') -> list:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list"""
        return convertInUnitList(self._queryAndReturn(cmd).split(','), unit)

    def _readingTimeout(self, count: int = 1) -> float:
        """Time in s that <count> readings can take (integration time + overhead, at least 10 s: the first reading after
        switching the function/zero check with auto range took 5.4 s on the real instrument)"""
        return max(10., count * (self.nplc / 50 + 0.05) * 2 + 1)

    def _parseReadings(self, response: str) -> list[KeithleyReading]:
        """Parses the reading string (data elements READing, TIME, STATus)"""

        numbers = parseNumbers(response)
        if not numbers:
            raise ConnectionError(f'No reading in response {response!r}')
        if len(numbers) % self.elements:
            raise ConnectionError(f'Response {response!r} does not contain {self.elements} elements per reading')

        readings = []
        for i in range(0, len(numbers), self.elements):
            value = numbers[i]
            if abs(value) >= 9.9E37 * 0.99:  # overflow value
                value = nan
            timestamp = numbers[i + 1] if self.elements > 1 else nan
            status = int(numbers[i + 2]) if self.elements > 2 else 0
            readings.append(KeithleyReading(value, timestamp, status))
        return readings

    # ------------------------------------------------------------------ general
    def identification(self) -> str:
        """Returns the manufacturer, model number, serial number, and firmware revision levels of the unit"""
        return self._queryAndReturn('*IDN?')

    def clearStatus(self):
        """Clears all event registers and error queue"""
        self._write('*CLS')

    def resetDevice(self):
        """Reset the device to default condition (the data format is set again)"""
        self._write('*RST')
        self.setFormatElements()
        self.trigger_count = 1
        self.nplc = self.getNPLC()

    def operationComplete(self) -> bool:
        """Waits until all pending operations are finished (*OPC?)"""
        return self._queryAndReturn('*OPC?', timeout=30) == '1'

    def getError(self) -> tuple[int, str]:
        """Returns the oldest error of the error queue as (code, message); (0, 'No error') if empty"""

        response = self._queryAndReturn('SYST:ERR?')
        code, _, message = response.partition(',')
        try:
            return int(code), message.strip().strip('"')
        except ValueError:
            return -1, response

    def getErrors(self) -> list[tuple[int, str]]:
        """Returns (and clears) all errors of the error queue"""

        errors = []
        for _ in range(20):
            code, message = self.getError()
            if code == 0:
                break
            errors.append((code, message))
        return errors

    def setLocal(self):
        """Takes the instrument out of remote, the front panel can be used again (RS-232 only)"""
        self._write('SYST:LOC')

    def setRemote(self):
        """Puts the instrument into remote (RS-232 only)"""
        self._write('SYST:REM')

    def setDisplay(self, state: bool | int):
        """Turns the front panel display on or off (off is a bit faster)"""
        self._write(f'DISP:ENAB {self._on_off(state)}')

    def saveState(self, location: MemoryLocation):
        """Saves the present setup as the user-saved setup"""
        self._write(f'*SAV {location.value}')

    def loadState(self, location: MemoryLocation):
        """"Returns into to the user-saved setup"""
        self._write(f'*RCL {location.value}')

    def setLineFrequency(self, frequency: LineFrequency):
        """Select power line frequency (in Hz); 50 or 60"""
        self._write(f'SYST:LFR {frequency.value}')

    def getLineFrequency(self) -> int:
        """Read present line frequency setting"""
        return self._queryAndReturnInt('SYST:LFR?')

    def setFormatElements(self, reading: bool = True, time: bool = True, status: bool = True):
        """Selects the data elements of the readings (the read functions expect all three)"""

        elements = [name for name, enabled in (('READ', reading), ('TIME', time), ('STAT', status)) if enabled]
        self._write(f'FORM:ELEM {",".join(elements)}')
        self.elements = len(elements)

    # ------------------------------------------------------------------ zero check / correct
    def acquireZeroCorrect(self):
        """Acquire a new zero correct value"""
        self._write('SYST:ZCOR:ACQ')

    def setAutoZero(self, state: bool | int):
        """Enable or disable autozero"""
        self._write(f'SYST:AZER {self._on_off(state)}')

    def setZeroCheck(self, state: bool | int):
        """Enable or disable zero check (input is shunted, readings are not the input signal)"""
        self._write(f'SYST:ZCH {self._on_off(state)}')

    def getZeroCheck(self) -> bool:
        """Returns if zero check is enabled"""
        return self._queryAndReturnBool('SYST:ZCH?')

    def setZeroCorrect(self, state: bool | int):
        """Enable or disable zero correct"""
        self._write(f'SYST:ZCOR {self._on_off(state)}')

    def getZeroCorrect(self) -> bool:
        """Returns if zero correct is enabled"""
        return self._queryAndReturnBool('SYST:ZCOR?')

    def zeroCorrect(self, function: Functions = Functions.CURRENT):
        """
        Zero correction as in the manual (programming example amps): zero check on, lowest range, zero correct on,
        auto range on, zero check off. Nothing should change at the input during this procedure.
        """

        lowest_range = {
            self.Functions.CURRENT: self.CurrentRange._20pA.value,
            self.Functions.VOLTAGE: self.VoltageRange._2V.value,
            self.Functions.CHARGE: self.ChargeRange._20nC.value,
            self.Functions.RESISTANCE: self.ResistanceRange._2kR.value,
        }[function]
        self.setZeroCheck(True)
        self.selectFunction(function)
        self._write(f'{function.value}:RANG {lowest_range}')
        self.setZeroCorrect(True)
        self._write(f'{function.value}:RANG:AUTO ON')
        self.setZeroCheck(False)
        self.operationComplete()

    # ------------------------------------------------------------------ calibration
    def calibrateCurrentOffset(self):
        """Input bias current calibration"""
        self._write(':CAL:UNPR:IOFF')

    def calibrateVoltageOffset(self):
        """Offset voltage calibration"""
        self._write(':CAL:UNPR:VOFF')

    # ------------------------------------------------------------------ function, range, rate, filters
    def selectFunction(self, function: Functions | str):
        """Select sensing function"""
        if isinstance(function, str):
            function = self.Functions[function.upper()] if function.upper() in self.Functions.__members__ else self.Functions(function.upper())
        self._write(f'FUNC "{function.value}"')

    def getFunction(self) -> str:
        """Returns the sensing function (VOLT, CURR, RES or CHAR)"""
        return self._queryAndReturn('FUNC?').strip('"\'').split(':')[0].upper()

    def _setRange(self, function: str, input_range, enum_class):
        """Sets range of function (enum, number in base units or 'AUTO')"""

        if isinstance(input_range, str) and input_range.upper() == 'AUTO':
            input_range = enum_class.AUTO
        if isinstance(input_range, enum_class):
            if input_range == enum_class.AUTO:
                self._write(f'{function}:RANG:AUTO ON')
                return
            input_range = input_range.value
        self._write(f'{function}:RANG {float(input_range):.6G}')

    def setVoltageRange(self, input_range: VoltageRange | float | str):
        """Sets voltage range (enum, value in V or 'AUTO')"""
        self._setRange('VOLT', input_range, self.VoltageRange)

    def setVoltageGuard(self, state: bool | int):
        """Enable or disable guard"""
        self._write(f'SENS:VOLT:GUAR {self._on_off(state)}')

    def setResistanceRange(self, input_range: ResistanceRange | float | str):
        """Sets resistance range (enum, value in Ohm or 'AUTO')"""
        self._setRange('RES', input_range, self.ResistanceRange)

    def setResistanceGuard(self, state: bool | int):
        """Enable or disable guard"""
        self._write(f'SENS:RES:GUAR {self._on_off(state)}')

    def setCurrentRange(self, input_range: CurrentRange | float | str):
        """Sets current range (enum, value in A or 'AUTO')"""
        self._setRange('CURR', input_range, self.CurrentRange)

    def getCurrentRange(self) -> float:
        """Returns the current range in A"""
        return self._queryAndReturnFloat('CURR:RANG?')

    def getCurrentAutoRange(self) -> bool:
        """Returns if auto range is enabled for current"""
        return self._queryAndReturnBool('CURR:RANG:AUTO?')

    def setCurrentDamping(self, state: bool | int):
        """Enable or disable damping"""
        self._write(f'SENS:CURR:DAMP {self._on_off(state)}')

    def setChargeRange(self, input_range: ChargeRange | float | str):
        """Sets charge range (enum, value in C or 'AUTO')"""
        self._setRange('CHAR', input_range, self.ChargeRange)

    def setChargeAutoDischarge(self, state: bool | int):
        """Enable or disable auto discharge"""
        self._write(f'SENS:CHAR:ADI:STATE {self._on_off(state)}')

    def setChargeAutoDischargeLevel(self, level: float):
        """Set auto discharge level; -2.1e-5 to 2.1e-5"""
        self._write(f'SENS:CHAR:ADI:LEV {convertToString(level)}')

    def setNPLC(self, nplc: float):
        """Sets the integration rate in power line cycles (0.01 to 10, global for all functions); 1 PLC = 20 ms at 50 Hz"""
        nplc = min(max(float(nplc), 0.01), 10)
        self._write(f'VOLT:NPLC {nplc:g}')
        self.nplc = nplc

    def getNPLC(self) -> float:
        """Returns the integration rate in power line cycles"""
        nplc = self._queryAndReturnFloat('VOLT:NPLC?')
        return nplc if nplc > 0 else 5.

    def setMedianFilter(self, state: bool | int, rank: int = 1):
        """Median filter of rank 1 to 5"""
        self._write(f'MED:RANK {min(max(int(rank), 1), 5)}')
        self._write(f'MED {self._on_off(state)}')

    def setAverageFilter(self, state: bool | int, count: int = 10, moving: bool = False):
        """Digital (average) filter over 2 to 100 readings, repeating or moving"""
        self._write(f'AVER:COUN {min(max(int(count), 2), 100)}')
        self._write(f'AVER:TCON {"MOV" if moving else "REP"}')
        self._write(f'AVER {self._on_off(state)}')

    def setupTrigger(self):
        """
        Single readings on request: aborts a running (continuous) measurement, sets arm and trigger count to 1 and
        clears old errors. READ? is invalid with an infinite arm count (error 830, e.g. after using the front panel).
        """

        self.continuous_on_close = self._queryAndReturn('ARM:COUN?').strip().upper() in ('INF', '+9.9E37', '9.9E37', '+9.900000E+37')
        self._write('ABOR')
        self._write('ARM:SOUR IMM')
        self._write('ARM:COUN 1')
        self._write('TRIG:SOUR IMM')
        self.setTriggerCount(1)
        self.clearStatus()

    def presetFrontPanel(self):
        """
        Front panel defaults like after power on (SYST:PRES): continuous readings, zero check on, auto range.
        Do not use INIT with an infinite arm count instead, the RS-232 parser is blocked then (only ^C helps).
        """

        self._write('SYST:PRES')
        self.trigger_count = 1

    def breakOperation(self):
        """
        Sends ^C: clears any pending operation and output (the instrument answers "DCL"). Recovers an instrument that
        does not answer anymore, e.g. after INIT with an infinite arm count.
        """

        self.serial.write(b'\x03')
        sleep(0.5)
        self.serial.reset_input_buffer()

    def setTriggerCount(self, count: int):
        """Number of readings per READ? (1 to 2500)"""
        count = min(max(int(count), 1), 2500)
        self._write(f'TRIG:COUN {count}')
        self.trigger_count = count

    def configureCurrent(self, current_range: CurrentRange | float | str = 'AUTO', nplc: float = 1, damping: bool = False, zero_check: bool = False):
        """
        Configures the instrument for current measurements

        :param current_range: range (enum, value in A or 'AUTO')
        :param nplc: integration rate in power line cycles
        :param damping: damping (for high capacitance at the input)
        :param zero_check: leave zero check enabled (input shunted)
        """

        self.selectFunction(self.Functions.CURRENT)
        self.setCurrentRange(current_range)
        self.setNPLC(nplc)
        self.setCurrentDamping(damping)
        self.setZeroCheck(zero_check)

    # ------------------------------------------------------------------ measuring
    def initiate(self):
        """Trigger readings (they can be requested with getLastData/FETC?)"""
        self._write('INIT')

    def getLastData(self) -> float:
        """Return latest 'raw' reading (does not trigger a new reading)"""
        readings = self._parseReadings(self._queryAndReturn('SENS:DATA?', timeout=self._readingTimeout()))
        return readings[0].value

    def readData(self) -> list[float]:
        """Trigger and return reading(s) (only the values)"""
        return [reading.value for reading in self.readAll()]

    def readAll(self) -> list[KeithleyReading]:
        """Trigger and return all readings of one READ? (trigger count readings)"""
        return self._parseReadings(self._queryAndReturn('READ?', timeout=self._readingTimeout(self.trigger_count)))

    def read(self) -> KeithleyReading:
        """Trigger and return one reading with timestamp and status"""

        if self.trigger_count != 1:
            self.setTriggerCount(1)
        return self.readAll()[0]

    def readValue(self) -> float:
        """Trigger and return one reading of the selected function (nan if overflowed)"""
        return self.read().value

    def readCurrent(self) -> float:
        """Trigger and return one current reading in A (nan if overflowed). Switches to the current function if needed."""

        reading = self.read()
        if reading.function != 'CURR':
            self.selectFunction(self.Functions.CURRENT)
            reading = self.read()
        if reading.zero_check:
            GlobalConf.logger.warning('<KeithleyPAmeterConnection> zero check is enabled, the reading is not the input current')
        return reading.value

    def readAverage(self, count: int = 10) -> tuple[float, float, int]:
        """
        Takes <count> readings (one READ? with trigger count) and returns (mean, standard deviation, number of valid readings)

        :param count: number of readings (1 to 2500)
        """

        self.setTriggerCount(count)
        try:
            readings = self.readAll()
        finally:
            self.setTriggerCount(1)
        values = [reading.value for reading in readings if isfinite(reading.value)]
        if not values:
            return nan, nan, 0
        mean = sum(values) / len(values)
        std = sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1)) if len(values) > 1 else 0.
        return mean, std, len(values)


def testDevice(comport: str = 'COM6', readings: int = 10):
    """
    Test routine for the real instrument (the input should be connected to the experiment or capped)

    :param comport: COM port of the electrometer
    :param readings: number of readings for the average test
    """

    print(f'***** Keithley 6514 on {comport} (9600 baud) *****')
    with KeithleyPAmeterConnection(comport, strict='MODEL 6514') as electrometer:
        print(f'identification: {electrometer.identification()}')
        print(f'echo: {electrometer.echo}, line frequency: {electrometer.getLineFrequency()} Hz, NPLC: {electrometer.getNPLC()}')
        print(f'errors in queue: {electrometer.getErrors()}')

        print('\n***** current measurement *****')
        electrometer.configureCurrent('AUTO', nplc=1)
        print(f'function: {electrometer.getFunction()}, auto range: {electrometer.getCurrentAutoRange()}, zero check: {electrometer.getZeroCheck()}')

        start = monotonic()
        reading = electrometer.read()
        print(f'single reading: {reading.value:.4E} A, timestamp {reading.timestamp:.2f} s, status {reading.status} '
              f'(overflow {reading.overflow}, zero check {reading.zero_check}, zero correct {reading.zero_correct}) in {monotonic() - start:.2f} s')

        start = monotonic()
        mean, std, count = electrometer.readAverage(readings)
        print(f'average of {readings}: {mean:.4E} +- {std:.1E} A ({count} valid) in {monotonic() - start:.2f} s')

        for nplc in (0.1, 1, 10):
            electrometer.setNPLC(nplc)
            start = monotonic()
            value = electrometer.readCurrent()
            print(f'NPLC {nplc:>4}: {value:.4E} A in {monotonic() - start:.2f} s')
        electrometer.setNPLC(1)

        print(f'range: {electrometer.getCurrentRange():.0E} A')
        print(f'errors in queue: {electrometer.getErrors()}')
    print('\nInstrument is in local mode again (front panel usable).')


if __name__ == '__main__':
    testDevice()
