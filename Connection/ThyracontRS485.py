from re import fullmatch, findall


from Connection.USBPorts import COMConnection


def thyracontChecksum(package: str) -> str:
    """Returns checksum character of package: (sum of all characters) mod 64 + 64"""
    return chr(sum(package.encode('ascii')) % 64 + 64)


def thyracontBuildPackage(address: int, access_code: int, command: str, data: str = '') -> str:
    """
    Builds a package of the Thyracont Communication Protocol V2

    :param address: RS485 address of gauge (1 - 16)
    :param access_code: access code (0: read, 2: write, 4: factory default)
    :param command: two character command
    :param data: data of package
    """

    if not 1 <= address <= 16:
        raise ValueError(f'Address {address} is not in the range from 1 to 16')
    if len(data) > 99:
        raise ValueError(f'Data "{data}" is too long, a maximum of 99 characters is possible')
    package = f'{address:03d}{access_code}{command}{len(data):02d}{data}'
    return f'{package}{thyracontChecksum(package)}\r'


def thyracontFloat(value: float) -> str:
    """Converts a value to the float format of the gauge (e.g. 1e-4, 1.3e1, 9.815e2)"""
    mantissa, exponent = f'{value:.5e}'.split('e')
    return f'{mantissa.rstrip("0").rstrip(".")}e{int(exponent)}'


class ThyracontRS485Error(ConnectionError):
    """Gauge answered with an error (access code 7) or with an invalid package, or a safety check refused the command"""


class ThyracontRS485Connection(COMConnection):
    """
    Context manager for Thyracont Smartline hot cathode gauges (VSH, e.g. VSH89DL) on a RS485 bus, built on top of the
    COMConnection context manager. All gauges are on the same comport and are distinguished by their address, which is
    set with the rotary switch of the gauge.

    All commands of the Communication Protocol V2 for VSH gauges are available. Depending on the firmware some of them
    are not supported and raise a <ThyracontRS485Error> with "NO_DEF" (firmware 0215: Display Data Source, Sensor Wear).

    Commands that heat up the gauge are refused unless the gauge itself measures vacuum, see <setDegas> and <setCathodeControl>.

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param baudrate: Baudrate [in Bd/s]
    :param cleaning: If output cache should be cleared when entering and exiting
    :param debug: If debug is enabled
    """

    # pressures from the manual [in mbar]: Degas is only possible below, hot cathode is at most switched on below (highest sensor transition)
    degas_pressure_limit = 2E-6
    cathode_pressure_limit = 1E-2

    # values of the gauge if the pressure is out of range [in mbar] (same as thyracontVoltageToPressure)
    overrange_pressure = 1000
    underrange_pressure = 5E-10
    # with the hot cathode off the Pirani sensor is used down to this pressure [in mbar]
    underrange_pressure_pirani = 1E-4

    # timeout for writes and factory defaults [in s]
    write_timeout = 2

    baudrates = (9600, 14400, 19200, 28800, 38400, 57600, 115200)
    display_units = ('mbar', 'Torr', 'hPa')

    def __init__(
        self,
        comport: str,
        timeout: float = 0.2,
        baudrate: int = 9600,
        cleaning: bool = True,
        debug: bool = False
    ):
        super().__init__(
            comport,
            timeout=timeout,
            encoding='ascii',
            baudrate=baudrate,
            echo=False,
            cleaning=cleaning,
            tx_term='\r',
            debug=debug
        )

    def _readPackage(self) -> str:
        """Reads one package up to the carriage return"""
        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        package = self.serial.read_until(b'\r').decode(self.encoding, errors='replace')
        if not package.endswith('\r'):
            raise TimeoutError(f'No complete answer on port "{self.comport}", received {package!r}')
        return package

    def _transfer(self, access_code: int, command: str, address: int, data: str = '') -> str:
        """
        Sends a package and returns the data of the answer. The access code of a valid answer is increased by one

        :param access_code: access code (0: read, 2: write, 4: factory default)
        :param command: two character command
        :param address: RS485 address of gauge (1 - 16)
        :param data: data of package
        """

        package = thyracontBuildPackage(address, access_code, command, data)
        if self.serial is None:
            raise ConnectionError('Connection has not been established')
        # a late answer after a timeout must not be taken for the answer of this package
        self.serial.reset_input_buffer()
        # a stored parameter is only acknowledged after about 255 ms, reads stay fast so a dead gauge does not block the bus for long
        self.serial.timeout = self.timeout if access_code == 0 else max(self.timeout, self.write_timeout)
        self.write(package)

        answer = self._readPackage()
        # some adapters also receive what they send on the bus
        if answer == package:
            answer = self._readPackage()

        body, checksum = answer[:-2], answer[-2:-1]
        if len(body) < 8 or thyracontChecksum(body) != checksum:
            raise ThyracontRS485Error(f'Wrong checksum in answer {answer!r}')

        answer_address, answer_access_code, answer_command, length, answer_data = body[:3], body[3], body[4:6], body[6:8], body[8:]
        if answer_address != f'{address:03d}' or answer_command != command or length != f'{len(answer_data):02d}':
            raise ThyracontRS485Error(f'Answer {answer!r} does not belong to command {package!r}')
        if answer_access_code == '7':
            raise ThyracontRS485Error(f'Gauge {address} answered {command} with error "{answer_data}"')
        if answer_access_code != str(access_code + 1):
            raise ThyracontRS485Error(f'Unexpected access code in answer {answer!r}')
        return answer_data

    def query(self, command: str, address: int = 1, data: str = '') -> str:
        """
        Sends read command and returns data of the answer

        :param command: two character command
        :param address: RS485 address of gauge (1 - 16)
        :param data: data of read command (only needed for some commands)
        """

        return self._transfer(0, command, address, data)

    def setParameter(self, command: str, data: str = '', address: int = 1):
        """
        Sends write command

        :param command: two character command
        :param data: new value
        :param address: RS485 address of gauge (1 - 16)
        """

        self._transfer(2, command, address, data)

    def restoreDefault(self, command: str, address: int = 1, data: str = ''):
        """
        Restores the factory default of a parameter

        :param command: two character command
        :param address: RS485 address of gauge (1 - 16)
        :param data: data of command (only needed for some commands)
        """

        self._transfer(4, command, address, data)

    def _queryFloat(self, command: str, address: int) -> float:
        """Queries a float value"""
        data = self.query(command, address)
        try:
            return float(data)
        except ValueError:
            raise ThyracontRS485Error(f'Gauge {address} answered {command} with "{data}", expected a number') from None

    def _queryPressure(self, command: str, address: int, underrange: float = underrange_pressure) -> float:
        """Queries a pressure in mbar. Limits of the measurement range are returned on under- and overrange"""
        data = self.query(command, address)
        if data == 'UR':
            return underrange
        if data == 'OR':
            return self.overrange_pressure
        try:
            return float(data)
        except ValueError:
            raise ThyracontRS485Error(f'Gauge {address} answered {command} with "{data}", expected a pressure') from None

    def _requireVacuum(self, limit: float, action: str, address: int):
        """Raises <ThyracontRS485Error> without sending anything if the pressure of the gauge is not below the limit [in mbar]"""
        pressure = self.getPressure(address)
        if pressure >= limit:
            raise ThyracontRS485Error(f'Refused to {action} on gauge {address}: pressure is {pressure:g} mbar, must be below {limit:g} mbar')

    #
    # Device information
    #

    def getDeviceType(self, address: int = 1) -> str:
        """Returns type of device (e.g. VSH208)"""
        return self.query('TD', address)

    def getProductName(self, address: int = 1) -> str:
        """Returns product name (e.g. VSH89DL)"""
        return self.query('PN', address)

    def getSerialNumber(self, address: int = 1) -> str:
        """Returns serial number of device"""
        return self.query('SD', address)

    def getSerialNumberHead(self, address: int = 1) -> str:
        """Returns serial number of sensor head"""
        return self.query('SH', address)

    def getDeviceVersion(self, address: int = 1) -> str:
        """Returns hardware version of device"""
        return self.query('VD', address)

    def getFirmwareVersion(self, address: int = 1) -> str:
        """Returns firmware version"""
        return self.query('VF', address)

    def getBootloaderVersion(self, address: int = 1) -> str:
        """Returns bootloader version"""
        return self.query('VB', address)

    def getOperatingHours(self, address: int = 1) -> tuple[float, float]:
        """Returns operating hours of the device and of the hot cathode as tuple of (device, cathode) [in h]"""
        data = self.query('OH', address)
        match = fullmatch(r'(\d+)C(\d+)', data)
        if match is None:
            raise ThyracontRS485Error(f'Gauge {address} answered OH with "{data}", expected [int]C[int]')
        # counted in intervals of 15 minutes
        return int(match.group(1)) / 4, int(match.group(2)) / 4

    def getSensorWear(self, address: int = 1) -> tuple[int, float]:
        """
        Returns the Pirani sensor statistics as tuple of (wear [in %], hours since last zero adjustment).
        Negative wear means corrosion, positive wear means contamination, 32767 means no calculation
        """
        data = self.query('PM', address, '1')
        match = fullmatch(r'W(-?\d+)A(\d+)', data)
        if match is None:
            raise ThyracontRS485Error(f'Gauge {address} answered PM with "{data}", expected W[int]A[int]')
        return int(match.group(1)), int(match.group(2)) / 4

    def resetSensorWear(self, address: int = 1):
        """Resets the calculated Pirani wear to 0. Can not be undone"""
        self.restoreDefault('PM', address, '1')

    #
    # Communication
    #

    def setBaudrate(self, baudrate: int, address: int = 1, permanent: bool = False):
        """
        Sets the baudrate of the gauge and of this connection. All gauges on a bus must use the same baudrate

        :param baudrate: new baudrate, one of <baudrates>
        :param address: RS485 address of gauge (1 - 16)
        :param permanent: store the current baudrate permanently, it must have been set temporarily before
        """

        if baudrate not in self.baudrates:
            raise ValueError(f'Baudrate {baudrate} is not one of {self.baudrates}')
        if permanent:
            self.setParameter('BR', f'S{baudrate}', address)
            return

        self.setParameter('BR', str(baudrate), address)
        self.serial.baudrate = baudrate
        self.baudrate = baudrate

    def getResponseDelay(self, address: int = 1) -> int:
        """Returns time between receiving a package and sending the answer [in us]"""
        return int(self.query('RD', address))

    def setResponseDelay(self, delay: int, address: int = 1):
        """
        Sets time between receiving a package and sending the answer until the next restart

        :param delay: response delay in [us] (1 - 99999, default 5500)
        :param address: RS485 address of gauge (1 - 16)
        """

        if not 1 <= delay <= 99999:
            raise ValueError(f'Response delay {delay} is not in the range from 1 to 99999 us')
        self.setParameter('RD', str(int(delay)), address)

    def restart(self, address: int = 1):
        """Restarts the gauge, it answers again after a few seconds"""
        self.setParameter('DR', '', address)

    #
    # Measurement
    #

    def getMeasurementRange(self, address: int = 1) -> tuple[float, float]:
        """Returns measurement range as tuple of (upper limit, lower limit) [in mbar]"""
        data = self.query('MR', address)
        match = fullmatch(r'H(.+)L(.+)', data)
        if match is None:
            raise ThyracontRS485Error(f'Gauge {address} answered MR with "{data}", expected H[float]L[float]')
        return float(match.group(1)), float(match.group(2))

    def getPressure(self, address: int = 1) -> float:
        """Returns pressure in mbar of the combined measurement (Pirani and Hot Cathode)"""
        return self._queryPressure('MV', address)

    def getPressurePirani(self, address: int = 1) -> float:
        """Returns pressure in mbar of the Pirani sensor"""
        return self._queryPressure('M1', address, self.underrange_pressure_pirani)

    def getPressureHotCathode(self, address: int = 1) -> float:
        """Returns pressure in mbar of the Hot Cathode sensor. Raises <ThyracontRS485Error> with "_SEDIS" if the Hot Cathode is off"""
        return self._queryPressure('M3', address)

    def getPressures(self, addresses: list[int] | tuple[int, ...]) -> dict[int, float | None]:
        """
        Returns the combined pressures in mbar of multiple gauges as dictionary of {address: pressure}.
        The pressure of a gauge that does not answer correctly is None, it does not affect the other gauges

        :param addresses: RS485 addresses of the gauges
        """

        pressures = {}
        for address in addresses:
            try:
                pressures[address] = self.getPressure(address)
            except (TimeoutError, ThyracontRS485Error):
                pressures[address] = None
        return pressures

    def getReadings(self, addresses: list[int] | tuple[int, ...]) -> dict[int, tuple[float | None, bool | None]]:
        """
        Returns the combined pressures in mbar and if Degas is on of multiple gauges as dictionary of {address: (pressure, degas)}.
        A value is None if the gauge does not answer correctly (e.g. a gauge without Degas), it does not affect the other gauges

        :param addresses: RS485 addresses of the gauges
        """

        readings = {}
        for address, pressure in self.getPressures(addresses).items():
            degas = None
            if pressure is not None:
                try:
                    degas = self.getDegas(address)
                except (TimeoutError, ThyracontRS485Error):
                    pass
            readings[address] = (pressure, degas)
        return readings

    def scan(self, addresses: range = range(1, 17)) -> dict[int, str]:
        """Returns dictionary of address and product name of all gauges that answer on the bus"""
        gauges = {}
        for address in addresses:
            try:
                gauges[address] = self.getProductName(address)
            except (TimeoutError, ThyracontRS485Error):
                continue
        return gauges

    #
    # Display (only for gauges with a display)
    #

    def getDisplayUnit(self, address: int = 1) -> str:
        """Returns the unit of the display. The pressures of this class are not affected and always in mbar"""
        return self.query('DU', address)

    def setDisplayUnit(self, unit: str, address: int = 1):
        """
        Sets the unit of the display

        :param unit: unit, one of <display_units>
        :param address: RS485 address of gauge (1 - 16)
        """

        if unit not in self.display_units:
            raise ValueError(f'Display unit "{unit}" is not one of {self.display_units}')
        self.setParameter('DU', unit, address)

    def resetDisplayUnit(self, address: int = 1):
        """Restores the default unit of the display (mbar)"""
        self.restoreDefault('DU', address)

    def getDisplayRotated(self, address: int = 1) -> bool:
        """Returns if the display is rotated by 180 degrees"""
        return self.query('DO', address) == '1'

    def setDisplayRotated(self, rotated: bool, address: int = 1):
        """Rotates the display by 180 degrees or back"""
        self.setParameter('DO', '1' if rotated else '0', address)

    def resetDisplayRotated(self, address: int = 1):
        """Restores the default orientation of the display (not rotated)"""
        self.restoreDefault('DO', address)

    def getDisplayDataSource(self, address: int = 1) -> int:
        """Returns data source of the display (0: combination, 1: Pirani, 3: Hot Cathode)"""
        return int(self.query('DD', address))

    def setDisplayDataSource(self, source: int, address: int = 1):
        """Sets data source of the display (0: combination, 1: Pirani, 3: Hot Cathode)"""
        self.setParameter('DD', str(int(source)), address)

    def resetDisplayDataSource(self, address: int = 1):
        """Restores the default data source of the display (combination)"""
        self.restoreDefault('DD', address)

    #
    # Relays (switchpoints)
    #

    def getRelay(self, relay: int, address: int = 1) -> str:
        """
        Returns the setting of a relay, e.g. "T1e1F1.3e1" (see <setRelay>)

        :param relay: relay (1 or 2)
        :param address: RS485 address of gauge (1 - 16)
        """

        return self.query(f'R{self._relayNumber(relay)}', address)

    def setRelay(self, relay: int, setting: str, address: int = 1):
        """
        Sets the setting of a relay

        :param relay: relay (1 or 2)
        :param setting: T[float]F[float]: switch by pressure (see <setRelayPressure>)
                        E, !E: closes, opens if device error
                        U, !U: closes, opens if underrange
                        C, !C: closes, opens if cathode is on
                        W, !W: closes, opens if a filament is defective
                        T0, T1: open, close by software
        :param address: RS485 address of gauge (1 - 16)
        """

        self.setParameter(f'R{self._relayNumber(relay)}', setting, address)

    def setRelayPressure(self, relay: int, pressure_true: float, pressure_false: float, address: int = 1):
        """
        Lets a relay switch by pressure. The manual warns that a small gap between the pressures can damage the relay.
        pressure_true < pressure_false: closes below pressure_true and opens above pressure_false
        pressure_true > pressure_false: opens below pressure_false and closes above pressure_true

        :param relay: relay (1 or 2)
        :param pressure_true: T pressure in [mbar]
        :param pressure_false: F pressure in [mbar]
        :param address: RS485 address of gauge (1 - 16)
        """

        if pressure_true == pressure_false:
            raise ValueError('The manual does not allow the same pressure for both thresholds of a relay')
        self.setRelay(relay, f'T{thyracontFloat(pressure_true)}F{thyracontFloat(pressure_false)}', address)

    def resetRelay(self, relay: int, address: int = 1):
        """Restores the default setting of a relay"""
        self.restoreDefault(f'R{self._relayNumber(relay)}', address)

    @staticmethod
    def _relayNumber(relay: int) -> int:
        """Returns the checked number of the relay"""
        if relay not in (1, 2):
            raise ValueError(f'Relay {relay} does not exist, must be 1 or 2')
        return relay

    #
    # Adjustment
    #

    def adjustHigh(self, address: int = 1):
        """Adjusts the Pirani sensor to atmosphere. Replaces the adjustment of the gauge and can not be undone, warm up for at least 10 minutes"""
        self.setParameter('AH', '', address)

    def adjustLow(self, address: int = 1):
        """Adjusts the Pirani sensor to zero, pressure must be below 5E-5 mbar. Replaces the adjustment of the gauge and can not be undone, warm up for at least 10 minutes"""
        self.setParameter('AL', '', address)

    #
    # Degas
    #

    def getDegas(self, address: int = 1) -> bool:
        """Returns if Degas is on"""
        return self.query('DG', address) == '1'

    def setDegas(self, on: bool, address: int = 1):
        """
        Switches Degas on or off. Degas heats the anode to around 800 degrees Celsius for about 3 minutes.
        Switching on is refused without sending it if the gauge does not measure a pressure below <degas_pressure_limit>

        :param on: switch Degas on
        :param address: RS485 address of gauge (1 - 16)
        """

        if on:
            self._requireVacuum(self.degas_pressure_limit, 'switch on Degas', address)
        self.setParameter('DG', '1' if on else '0', address)

    def getDegasLogic(self, address: int = 1) -> bool:
        """Returns if the Degas signal on pin 9 is active high (3 - 24 V) instead of active low (GND, default)"""
        return self.query('DL', address) == '1'

    def setDegasLogic(self, active_high: bool, address: int = 1):
        """Sets if the Degas signal on pin 9 is active high (3 - 24 V) or active low (GND). Check the wiring of pin 9 first, it could start Degas"""
        self.setParameter('DL', '1' if active_high else '0', address)

    def resetDegasLogic(self, address: int = 1):
        """Restores the default of the Degas signal on pin 9 (active low). Check the wiring of pin 9 first, it could start Degas"""
        self.restoreDefault('DL', address)

    #
    # Hot cathode
    #

    def getSensorTransition(self, address: int = 1) -> str:
        """
        Returns transition between Pirani and Hot Cathode, see <setSensorTransition>, e.g. "1"
        """
        return self.query('ST', address)

    def setSensorTransition(self, setting: int | str, address: int = 1):
        """
        Sets transition between Pirani and Hot Cathode

        :param setting: 0: direct switch at 4E-4 mbar
                        1: continuous between 1E-3 and 2E-3 mbar (default)
                        2: continuous between 2E-3 and 5E-3 mbar
                        F[float]T[float]: continuous between the pressures in mbar (4E-4 to 1E-2 mbar)
                        D[float]: direct switch at the pressure in mbar (4E-4 to 1E-2 mbar)
        :param address: RS485 address of gauge (1 - 16)
        """

        self.setParameter('ST', str(setting), address)

    def resetSensorTransition(self, address: int = 1):
        """Restores the default transition between Pirani and Hot Cathode"""
        self.restoreDefault('ST', address)

    def getCathodeStatus(self, address: int = 1) -> bool:
        """Returns if the Hot Cathode is on at the moment"""
        return self.query('CA', address) == '1'

    def getCathodeControl(self, address: int = 1) -> bool:
        """Returns if the Hot Cathode is enabled, so the gauge switches it on automatically at low pressure"""
        return self.query('CC', address) == '1'

    def setCathodeControl(self, enabled: bool, address: int = 1):
        """
        Enables or disables the Hot Cathode until the next restart. Enabled means the gauge switches it on automatically at low pressure.
        Enabling is refused without sending it if the gauge does not measure a pressure below <cathode_pressure_limit>

        :param enabled: enable Hot Cathode
        :param address: RS485 address of gauge (1 - 16)
        """

        if enabled:
            self._requireVacuum(self.cathode_pressure_limit, 'enable the Hot Cathode', address)
        self.setParameter('CC', '1' if enabled else '0', address)

    def resetCathodeControl(self, address: int = 1):
        """Restores the default of the Hot Cathode (enabled). Refused like in <setCathodeControl>"""
        self._requireVacuum(self.cathode_pressure_limit, 'enable the Hot Cathode', address)
        self.restoreDefault('CC', address)

    def getFilamentControl(self, address: int = 1) -> int:
        """Returns usage of the filaments, see <setFilamentControl>"""
        return int(self.query('FC', address))

    def setFilamentControl(self, mode: int, address: int = 1):
        """
        Sets usage of the filaments

        :param mode: 0: filament 1, filament 2 if filament 1 is defective (default)
                     1: only filament 1
                     2: only filament 2
                     3: alternating at every start of the Hot Cathode
        :param address: RS485 address of gauge (1 - 16)
        """

        if mode not in (0, 1, 2, 3):
            raise ValueError(f'Filament control {mode} does not exist, must be 0, 1, 2 or 3')
        self.setParameter('FC', str(mode), address)

    def resetFilamentControl(self, address: int = 1):
        """Restores the default usage of the filaments"""
        self.restoreDefault('FC', address)

    def getFilamentNumber(self, address: int = 1) -> int:
        """Returns the active filament (1 or 2)"""
        return int(self.query('FN', address))

    def getFilamentStatus(self, address: int = 1) -> int:
        """Returns the status of the filaments (0: both ok, 1: filament 1 defective, 2: filament 2 defective, 3: both defective)"""
        return int(self.query('FS', address))

    #
    # Gas correction factors
    #

    def getGasCorrectionPirani(self, address: int = 1) -> float:
        """Returns gas correction factor of the Pirani sensor"""
        return self._queryFloat('C1', address)

    def setGasCorrectionPirani(self, factor: float, address: int = 1):
        """
        Sets gas correction factor of the Pirani sensor. It also changes the analog output

        :param factor: gas correction factor (0.2 - 8)
        :param address: RS485 address of gauge (1 - 16)
        """

        self.setParameter('C1', self._gasCorrectionData(factor), address)

    def resetGasCorrectionPirani(self, address: int = 1):
        """Restores the default gas correction factor of the Pirani sensor (1)"""
        self.restoreDefault('C1', address)

    def getGasCorrectionHotCathode(self, address: int = 1) -> float:
        """Returns gas correction factor of the Hot Cathode sensor"""
        return self._queryFloat('C3', address)

    def setGasCorrectionHotCathode(self, factor: float, address: int = 1):
        """
        Sets gas correction factor of the Hot Cathode sensor. It also changes the analog output

        :param factor: gas correction factor (0.2 - 8)
        :param address: RS485 address of gauge (1 - 16)
        """

        self.setParameter('C3', self._gasCorrectionData(factor), address)

    def resetGasCorrectionHotCathode(self, address: int = 1):
        """Restores the default gas correction factor of the Hot Cathode sensor (1)"""
        self.restoreDefault('C3', address)

    @staticmethod
    def _gasCorrectionData(factor: float) -> str:
        """Returns the checked gas correction factor as data"""
        if not 0.2 <= factor <= 8:
            raise ValueError(f'Gas correction factor {factor} is not in the range from 0.2 to 8')
        return f'{factor:.2f}'

    #
    # Analog output
    #

    def getAnalogOutput(self, address: int = 1) -> str:
        """Returns the characteristic of the analog output, e.g. "LogG0.6O6.8L0.0L10.5U0.9O8.6F0.4", see <parseAnalogOutput>"""
        return self.query('OC', address)

    @staticmethod
    def parseAnalogOutput(data: str) -> dict[str, str | float]:
        """
        Returns a logarithmic or linear characteristic as dictionary, voltages in [V]:
        U = gain * log10(p) + offset (logarithmic) with lower limit, upper limit and the voltages in case of underrange, overrange and fault

        :param data: answer of <getAnalogOutput>
        """

        values = findall(r'[A-Z]([-\d.e]+)', data[3:])
        if data[:3] not in ('Log', 'Lin') or len(values) < 7:
            raise ValueError(f'"{data}" is not a logarithmic or linear characteristic')
        names = ('gain', 'offset', 'lower_limit', 'upper_limit', 'underrange', 'overrange', 'fault')
        return {'type': data[:3], **{name: float(value) for name, value in zip(names, values)}}

    def getAnalogOutputTableEntry(self, entry: int, address: int = 1) -> str:
        """
        Returns entry of the characteristic if it is a table, e.g. "P1e3U8.51"

        :param entry: index of table entry
        :param address: RS485 address of gauge (1 - 16)
        """

        return self.query('OC', address, f'E{int(entry)}')

    def setAnalogOutput(self, data: str, address: int = 1):
        """
        Sets the characteristic of the analog output. The readout with the LucidControl ADC relies on the default characteristic

        :param data: e.g. "LogG0.6O6.8L0.0L10.5U0.9O8.6F0.4" (see communication protocol for tables)
        :param address: RS485 address of gauge (1 - 16)
        """

        self.setParameter('OC', data, address)

    def resetAnalogOutput(self, address: int = 1):
        """Restores the default characteristic of the analog output"""
        self.restoreDefault('OC', address)


def main():
    from sys import argv
    from Connection.USBPorts import printComports

    printComports()
    comport = argv[1] if len(argv) > 1 else 'COM3'

    with ThyracontRS485Connection(comport) as thyracont:
        print(f'Scanning all addresses on {comport} ...')
        gauges = thyracont.scan()
        print(f'{gauges = }')

        for address in gauges:
            print(f'***** GAUGE {address} *****')
            print(f'{thyracont.getProductName(address) = }')
            print(f'{thyracont.getDeviceType(address) = }')
            print(f'{thyracont.getSerialNumber(address) = }')
            print(f'{thyracont.getFirmwareVersion(address) = }')
            print(f'{thyracont.getOperatingHours(address) = }')
            print(f'{thyracont.getMeasurementRange(address) = }')
            print(f'{thyracont.getPressure(address) = }')
            print(f'{thyracont.getPressurePirani(address) = }')
            try:
                print(f'{thyracont.getPressureHotCathode(address) = }')
            except ThyracontRS485Error as error:
                print(f'Hot Cathode: {error}')


if __name__ == '__main__':
    main()
