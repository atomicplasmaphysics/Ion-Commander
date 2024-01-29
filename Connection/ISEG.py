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


def convertInChannelString(channels: int | str | list) -> tuple[str, int]:
    """
    Converts channel in channel input string. Returns input string and amount of channels.
    Possible notations:
        2 -> '2'
        [1, 4, 5] -> '1,3,5'
        ['0', '3', '2 '] -> '0,2,3'
        '0, 3, 1' -> '0,1,3'
        '0-2' -> '0,1,2'
        '0-2, 5 -7' -> '0,1,2,5,6,7'
    """

    # in int form
    if isinstance(channels, int):
        channels_out = {channels}

    # in list form
    elif isinstance(channels, list):
        channels_out = {int(channel) for channel in channels}

    # in string form
    else:
        channels_out = set()

        for channel in [channel for channel in channels.split(',')]:
            # single channel
            if '-' not in channel:
                channels_out.add(int(channel))
                continue

            # channel range
            channel_parts = channel.split('-')
            if len(channel_parts) > 2:
                raise ValueError(f'Channel range is invalid: {channel}')
            channels_out.update(set(range(int(channel_parts[0]), int(channel_parts[1]) + 1)))

    channels_out = list(channels_out)

    # check if output string might be valid
    if not channels_out:
        raise ValueError('Conversion of channels in channel string failed. No channels selected')

    return ','.join([str(channel_out) for channel_out in sorted(channels_out)]), len(channels_out)


def convertToString(inp: float | int, precision: int = 6):
    """Converts a float or integer to a scientific notation with given precision"""
    return f'{float(inp):.{precision}E}'


class ISEGConnection(COMConnection):
    """
    Context manager for ISEG Serial connection, built on top of the COMConnection context manager

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param echo: If device has echo. Will be checked
    :param cleaning: If output cache should be cleared when entering and exiting
    :param strict: If identification string should contain "iseg"
    """

    class EchoMode(Enum):
        ECHO_ENABLED = auto()
        ECHO_DISABLED = auto()
        ECHO_AUTO = auto()

    def __init__(
        self,
        comport: str,
        timeout: float = 0.05,
        encoding: str = 'utf-8',
        echo: EchoMode = EchoMode.ECHO_AUTO,
        cleaning: bool = True,
        strict: bool = False
    ):
        self.echo_mode = echo
        self.strict = strict

        super().__init__(
            comport,
            timeout=timeout,
            encoding=encoding,
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

            GlobalConf.logger.info(f'<ISEGConnection> auto-detected echo-mode on port "{self.comport}" to {self.echo}')
            self.clean()

        # detect if it is ISEG device
        identification = self.identification()
        if 'iseg' not in identification.lower():
            GlobalConf.logger.warning(f'<ISEGConnection> on port "{self.comport}" does not identify with "iseg". Identification is "{identification}"')
            if self.strict:
                raise ConnectionError(f'Device identification "{identification}" does not contain "iseg"')

        return self

    def _queryAndReturn(self, cmd: str) -> str:
        """Queries command and returns striped result"""
        self.write(cmd)
        return self.readline().strip()

    def _queryAndReturnFloat(self, cmd: str, unit: str = '') -> float:
        """Queries command and returns striped result as float without unit. If float conversion fails, -1 will be returned."""
        try:
            return float(self._queryAndReturn(cmd).replace(unit, ''))
        except ValueError:
            return -1

    def _queryAndReturnInt(self, cmd: str, unit: str = '') -> int:
        """Queries command and returns striped result as integer without unit. If integer conversion fails, -1 will be returned."""
        return int(self._queryAndReturnFloat(cmd, unit))

    def _queryAndReturnList(self, cmd: str, unit: str = '') -> list:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list"""
        return convertInUnitList(self._queryAndReturn(cmd).split(','), unit)

    def _queryAndReturnStrOrList(self, cmd: str, number_channels: int) -> str | list[str]:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list or string"""
        return self._queryAndReturn(cmd) if number_channels == 1 else self._queryAndReturnList(cmd)

    def _queryAndReturnFloatOrList(self, cmd: str, number_channels: int, unit: str = '') -> float | list[float]:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list or float"""
        return self._queryAndReturnFloat(cmd, unit) if number_channels == 1 else self._queryAndReturnList(cmd, unit)

    def identification(self) -> str:
        """Query the module identification"""
        return self._queryAndReturn('*IDN?')

    def clearStatus(self):
        """Clear the Module Event Status and all Channel Event Status registers"""
        self._queryAndReturn('*CLS')

    def resetDevice(self):
        """
        Reset the device to save values:
        • turn high voltage off with ramp for all channel
        • set voltage set Vset to zero for all channels
        • set current set Iset to the current nominal for all channels
        """
        self._queryAndReturn('*RST')

    def instructionSetGet(self) -> str:
        """
        Query the currently selected instruction set. All devices support the EDCP command set.
        Some devices (HPS, EHQ) support further command sets, refer to the devices manual for them.
        """
        return self._queryAndReturn('*INSTR?')

    def instructionSetSet(self, instruction_set: str):
        """
        Switch the device to the EDCP command set. Only for devices that support other command sets beside EDCP.
        For HPS and EHQ with other command sets, refer to the devices manual. This setting is permanent.
        """
        self._queryAndReturn(f'*INSTR,{instruction_set}')

    def localLockout(self):
        """Local Lockout: Front panel buttons and rotary encoders are disabled. The device can only be controlled remotely."""
        self._queryAndReturn('*LLO')

    def gotoLocal(self):
        """Goto Local: Front panel buttons and rotary encoders are enabled"""
        self._queryAndReturn('*GTL')

    def operationComplete(self):
        """Query the operation complete status. The query returns “1” when all commands before this query have been processed."""
        return self._queryAndReturn('*OPC?')

    def readModuleList(self) -> list:
        """Query which slots are available and returns a comma separated list."""
        return self._queryAndReturnList(':READ:MOD:LIST?')

    def readModuleIdentification(self, slot: int) -> str:
        """Read the module identification for a specific slot"""
        return self._queryAndReturn(f':READ:MOD:IDENT? (#{slot})')

    def cratePowerQuery(self) -> int:
        """Returns 0 if the crate backplane is powered off, or 1 if the backplane is powered on"""
        return self._queryAndReturnInt(':CRATE:POWER?')

    def cratePowerSet(self, on: bool | int):
        """CC24: Turn the crate backplane off (0) resp. on (1)"""
        self._queryAndReturn(f':CRATE:POWER {int(on)}')

    def crateStatus(self) -> int:
        """Returns the CC24 Crate Controller Status register"""
        return self._queryAndReturnInt(':CRATE:STATUS?')

    def crateEventClear(self):
        """Clears the Crate Controller Event Status register"""
        self._queryAndReturn(':CRATE:EVENT CLEAR')

    def crateEventResetMask(self, reset_mask: int):
        """Clears the given bits in the ResetMask"""
        self._queryAndReturn(f':CRATE:EVENT {reset_mask}')

    def crateEventStatus(self) -> int:
        """Queries the Crate Controller Event Status register"""
        return self._queryAndReturnInt(':CRATE:EVENT:STATUS?')

    def crateEventMaskQuery(self) -> int:
        """Queries the Crate Controller Event Mask register"""
        return self._queryAndReturnInt(':CRATE:EVENT:MASK?')

    def crateEventMaskSet(self, mask: int):
        """Sets the Crate Controllers Event Mask register"""
        return self._queryAndReturnInt(f':CRATE:EVENT:MASK {mask}')

    def crateSupply(self, x: int) -> int:
        """
        Query the crate controller supply voltage x, for x =
            0: +24 V High voltage backplane
            2: +5 V High voltage backplane
            5: +5 V CC24 intern
            6: +3.3 V CC24 intern
            7: 230 V AC line power
            8: +24 V UPS Battery
            9: Safety Loop Voltage
        """
        return self._queryAndReturnInt(f':CRATE:SUPPLY? (@{x})', 'V')

    def crateTemperature(self, y: int) -> float:
        """
        Queries the crate controllers temperatures that effect fan regulation.
            y = 0, y = 1: CC24 internal temperature sensors,
            y = 2: highest module temperature in the crate
        """
        return self._queryAndReturnFloat(f':CRATE:TEMP? (@{y})', 'C')

    def crateFanSpeed(self) -> float:
        """Returns the crates fan speed in percent"""
        return self._queryAndReturnFloat(':CRATE:FAN?', '%')

    def voltageSet(self, channel: int, voltage: float):
        """
        Set the channel voltage set Vset in Volt.
        MICC: If the channel is configured with EPU, the voltage sign defines the polarity of the output voltage.
        """
        self._queryAndReturn(f':VOLT {convertToString(voltage)},(@{channel})')

    def voltageOn(self, channel: int | str | list):
        """Switch on High Voltage with the configured ramp speed"""
        channel, _ = convertInChannelString(channel)
        self._queryAndReturn(f':VOLT ON,(@{channel})')

    def voltageOff(self, channel: int | str | list):
        """Switch off High Voltage with the configured ramp speed"""
        channel, _ = convertInChannelString(channel)
        self._queryAndReturn(f':VOLT OFF,(@{channel})')

    def voltageEmergencyOff(self, channel: int | str | list):
        """Shut down the channel High Voltage (without ramp). The channel stays in Emergency Off until the command EMCY˽CLR is given."""
        channel, _ = convertInChannelString(channel)
        self._queryAndReturn(f':VOLT EMCY OFF,(@{channel})')

    def voltageEmergencyClear(self, channel: int | str | list):
        """Clear the channel from state emergency off. The channel goes to state off."""
        channel, _ = convertInChannelString(channel)
        self._queryAndReturn(f':VOLT EMCY CLR,(@{channel})')

    def voltageBoundarySet(self, channel: int, voltage: float):
        """Set the channel voltage bounds Vbounds in Volt"""
        self._queryAndReturn(f':VOLT:BOUNDS {convertToString(voltage)},(@{channel})')

    def currentSet(self, channel: int, current: float):
        """Set the channel current set Iset in Ampere"""
        self._queryAndReturn(f':CURR {convertToString(current)},(@{channel})')

    def currentBoundarySet(self, channel: int, current: float):
        """Set the channel current bounds Ibounds in Ampere"""
        self._queryAndReturn(f':CURR:BOUNDS {convertToString(current)},(@{channel})')

    def eventClear(self, channel: int | str | list):
        """Clear the Channel Event Status register"""
        channel, _ = convertInChannelString(channel)
        self._queryAndReturn(f':EVENT CLEAR,(@{channel})')

    def eventResetMask(self, channel: int,  word: int):
        """Clears single bits or bit combinations in the Channel Event Status register by writing a one to the corresponding bit position"""
        self._queryAndReturn(f':EVENT {word},(@{channel})')

    def eventMask(self, channel: int,  word: int):
        """Set the Channel Event Mask register"""
        self._queryAndReturn(f':EVENT:MASK {word},(@{channel})')

    def configureTripTimeSet(self, channel: int, time: int):
        """Set the trip timeout with one millisecond resolution"""
        self._queryAndReturn(f':CONF:TRIP:TIME {time},(@{channel})')

    def configureTripTimeGet(self, channel: int | str | list) -> float | list[float]:
        """Query the programmed trip timeout in milliseconds"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:TRIP:TIME? (@{channel})', nunber_channels, 'ms')

    def configureTripActionSet(self, channel: int, action: int):
        """
        Set the action that should happen when a current trip for the channel occurs
        Action:
            0 – no action, status flag Trip will be set after timeout
            1 – turn off the channel with ramp
            2 – shut down the channel without ramp
            3 – shut down the whole module without ramp
            4 – disable the Delayed Trip function
        """
        self._queryAndReturn(f':CONF:TRIP:ACTION {action},(@{channel})')

    def configureTripActionGet(self, channel: int | str | list) -> float | list[float]:
        """Query the action that should happen when a current trip for the channel occurs"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:TRIP:ACTION? (@{channel})', nunber_channels)

    def configureInhibitActionSet(self, channel: int, action: int):
        """
        Set the action that should happen when an External Inhibit for the channel occurs
        Action:
            0 – no action, status flag External Inhibit will be set
            1 – turn off the channel with ramp
            2 – shut down the channel without ramp
            3 – shut down the whole module without
        """
        self._queryAndReturn(f':CONF:INHP:ACTION {action},(@{channel})')

    def configureInhibitActionGet(self, channel: int | str | list) -> float | list[float]:
        """Query the action that should happen when an External Inhibit for the channel occurs"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:INHP:ACTION? (@{channel})', nunber_channels)

    def configureOutputModeSet(self, channel: int, mode: int):
        """Set the channel output mode. Only values that are contained in output mode list are allowed."""
        self._queryAndReturn(f':CONF:OUTPUT:MODE {mode},(@{channel})')

    def configureOutputModeGet(self, channel: int | str | list) -> float | list[float]:
        """Query the configured channel output mode"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:OUTPUT:MODE? (@{channel})', nunber_channels)

    def configureOutputModeList(self, channel: int) -> list[float]:
        """Query the available channel output modes as list"""
        return self._queryAndReturnList(f':CONF:OUTPUT:MODE:LIST? (@{channel})')

    def configureOutputPolaritySet(self, channel: int, positive: bool):
        """Set output polarity (positive = p, negative = n)"""
        positive = 'p' if positive else 'n'
        self._queryAndReturn(f':CONF:OUTPUT:POL {positive},(@{channel})')

    def configureOutputPolarityGet(self, channel: int | str | list) -> bool | list[bool]:
        """Query the current output polarity"""
        channel, nunber_channels = convertInChannelString(channel)
        result = [True if r.lower() == 'p' else False for r in self._queryAndReturnList(f':CONF:OUTPUT:POL? (@{channel})')]
        return result[0] if nunber_channels == 1 else result

    def configureOutputPolarityList(self, channel: int) -> list[bool]:
        """Query the available channel output polarities"""
        return [True if r.lower() == 'p' else False for r in self._queryAndReturnList(f':CONF:OUTPUT:POL:LIST? (@{channel})')]

    def readVoltage(self, channel: int | str | list) -> float | list[float]:
        """Query the voltage set Vset in Volt"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT? (@{channel})', nunber_channels, 'V')

    def readVoltageLimit(self, channel: int | str | list) -> float | list[float]:
        """Query the voltage limit Vlim in Volt"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:LIM? (@{channel})', nunber_channels, 'V')

    def readVoltageNominal(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage nominal Vnom in Volt"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:NOM? (@{channel})', nunber_channels, 'V')

    def readVoltageMode(self, channel: int | str | list) -> float | list[float]:
        """Query the configured channel voltage mode with polarity sign in Volt"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:MODE? (@{channel})', nunber_channels, 'V')

    def readVoltageModeList(self, channel: int | str | list) -> float | list[float]:
        """Query the available channel voltage modes as list which corresponds to the request configureOutputModeList()"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:MODE:LIST? (@{channel})', nunber_channels, 'V')

    def readVoltageBoundaries(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage bounds Vbounds in Volt"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:BOUNDS? (@{channel})', nunber_channels, 'V')

    def readVoltageOn(self, channel: int | str | list) -> float | list[float]:
        """Query the channel control bit Set On"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:ON? (@{channel})', nunber_channels, 'V')

    def readVoltageEmergency(self, channel: int | str | list) -> float | list[float]:
        """Query the channel control bit Set Emergency Off"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:VOLT:EMCY? (@{channel})', nunber_channels, 'V')

    def readCurrent(self, channel: int | str | list) -> float | list[float]:
        """Query the current set Iset in Ampere"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CURR? (@{channel})', nunber_channels, 'A')

    def readCurrentLimit(self, channel: int | str | list) -> float | list[float]:
        """Query the current limit Ilim in Ampere"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CURR:LIM? (@{channel})', nunber_channels, 'A')

    def readCurrentNominal(self, channel: int | str | list) -> float | list[float]:
        """Query the channel current nominal in Ampere, answer is absolute value"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CURR:NOM? (@{channel})', nunber_channels, 'A')

    def readCurrentMode(self, channel: int | str | list) -> float | list[float]:
        """Query the configured channel current mode in Ampere"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CURR:MODE? (@{channel})', nunber_channels, 'A')

    def readCurrentModeList(self, channel: int | str | list) -> float | list[float]:
        """Query the available channel current modes as list which corresponds to the request configureOutputModeList()"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CURR:MODE:LIST? (@{channel})', nunber_channels, 'A')

    def readCurrentBoundaries(self, channel: int | str | list) -> float | list[float]:
        """Query the channel current bounds Ibounds in Ampere"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CURR:BOUNDS? (@{channel})', nunber_channels, 'A')

    def readRampVoltage(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage ramp speed in Volt/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:RAMP:VOLT? (@{channel})', nunber_channels, 'V/s')

    def readRampVoltageMin(self, channel: int | str | list) -> float | list[float]:
        """Query channel voltage ramp speed minimum in Volt/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:RAMP:VOLT:MIN? (@{channel})', nunber_channels, 'V/s')

    def readRampVoltageMax(self, channel: int | str | list) -> float | list[float]:
        """Query channel voltage ramp speed maximum in Volt/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:RAMP:VOLT:MAX? (@{channel})', nunber_channels, 'V/s')

    def readRampCurrent(self, channel: int | str | list) -> float | list[float]:
        """Query channel current ramp speed in Ampere/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:RAMP:CURR? (@{channel})', nunber_channels, 'A/s')

    def readRampCurrentMin(self, channel: int | str | list) -> float | list[float]:
        """Query channel current ramp speed minimum in Ampere/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:RAMP:CURR:MIN? (@{channel})', nunber_channels, 'A/s')

    def readRampCurrentMax(self, channel: int | str | list) -> float | list[float]:
        """Query channel current ramp speed maximum in Ampere/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:RAMP:CURR:MAX? (@{channel})', nunber_channels, 'A/s')

    def readChannelControl(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Control register"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CHAN:CONTROL? (@{channel})', nunber_channels)

    def readChannelStatus(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Status register"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CHAN:STATUS? (@{channel})', nunber_channels)

    def readChannelEventStatus(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Event Status register"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CHAN:EVENT:STATUS? (@{channel})', nunber_channels)

    def readChannelEventMask(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Event Mask register"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':READ:CHAN:EVENT:MASK? (@{channel})', nunber_channels)

    def measureVoltage(self, channel: int | str | list) -> float | list[float]:
        """Query the measured channel voltage in Volt"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':MEAS:VOLT? (@{channel})', nunber_channels, 'V')

    def measureCurrent(self, channel: int | str | list) -> float | list[float]:
        """Query the measured channel current in Ampere"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':MEAS:CURR? (@{channel})', nunber_channels, 'A')

    def configureRampVoltageSet(self, speed: float):
        """Set the module voltage ramp speed in percent/second"""
        self._queryAndReturn(f':CONF:RAMP:VOLT {convertToString(speed)}')

    def configureRampVoltageGet(self) -> float:
        """Query the module voltage ramp speed in percent/second"""
        return self._queryAndReturnFloat(':CONF:RAMP:VOLT?', '%/s')

    def configureRampVoltageSetChannel(self, channel: int, speed: float):
        """Set the channel voltage ramp up speed in Volt/second"""
        self._queryAndReturn(f':CONF:RAMP:VOLT {convertToString(speed)},(@{channel})')

    def configureRampVoltageUpSet(self, channel: int, speed: float):
        """Set the channel voltage ramp up speed in Volt/second"""
        self._queryAndReturn(f':CONF:RAMP:VOLT:UP {convertToString(speed)},(@{channel})')

    def configureRampVoltageUpGet(self, channel: int | str | list) -> float | list[float]:
        """Set the channel voltage ramp up speed in Volt/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:RAMP:VOLT:UP? (@{channel})', nunber_channels, 'V/s')

    def configureRampVoltageDownSet(self, channel: int, speed: float):
        """Set the channel voltage ramp down speed in Volt/second"""
        self._queryAndReturn(f':CONF:RAMP:VOLT:DOWN {convertToString(speed)},(@{channel})')

    def configureRampVoltageDownGet(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage ramp down speed in Volt/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:RAMP:VOLT:DOWN? (@{channel})', nunber_channels, 'V/s')

    def configureRampCurrentSet(self, speed: float):
        """Set the module current ramp speed in percent/second"""
        self._queryAndReturn(f':CONF:RAMP:CURR {convertToString(speed)}')

    def configureRampCurrentGet(self) -> float:
        """Query the module current ramp speed in percent/second"""
        return self._queryAndReturnFloat(':CONF:RAMP:CURR?', '%/s')

    def configureRampCurrentSetChannel(self, channel: int, speed: float):
        """Set the channel current ramp speed for up and down direction in Ampere/second"""
        self._queryAndReturn(f':CONF:RAMP:CURR {convertToString(speed)},(@{channel})')

    def configureRampCurrentUpSet(self, channel: int, speed: float):
        """Set the channel current ramp up speed in Ampere/second"""
        self._queryAndReturn(f':CONF:RAMP:CURR:UP {convertToString(speed)},(@{channel})')

    def configureRampCurrentUpGet(self, channel: int | str | list) -> float | list[float]:
        """Set the channel current ramp up speed in Ampere/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:RAMP:CURR:UP? (@{channel})', nunber_channels, 'A/s')

    def configureRampCurrentDownSet(self, channel: int, speed: float):
        """Set the channel current ramp down speed in Ampere/second"""
        self._queryAndReturn(f':CONF:RAMP:CURR:DOWN {convertToString(speed)},(@{channel})')

    def configureRampCurrentDownGet(self, channel: int | str | list) -> float | list[float]:
        """Query the channel current ramp down speed in Ampere/second"""
        channel, nunber_channels = convertInChannelString(channel)
        return self._queryAndReturnFloatOrList(f':CONF:RAMP:CURR:DOWN? (@{channel})', nunber_channels, 'A/s')

    def configureAverageSet(self, average: int):
        """Set the number of digital filter averaging steps. Factory default is 64."""
        self._queryAndReturn(f':CONF:AVER {average}')

    def configureAverageGet(self) -> int:
        """Query the digital filter averaging steps"""
        return self._queryAndReturnInt(':CONF:AVER?')

    def configureKillSet(self, kill: bool | int):
        """Set function kill enable (1) or kill disable (0). Factory default is Kill Disable."""
        self._queryAndReturn(f':CONF:KILL {int(kill)}')

    def configureKillGet(self) -> int:
        """Query the current value for the kill enable function"""
        return self._queryAndReturnInt(':CONF:KILL?')

    def configureAdjustSet(self, adjust: bool | int):
        """Set the fine adjustment function on (1) or off (0). Factory default is adjustment on."""
        self._queryAndReturn(f':CONF:ADJUST {int(adjust)}')

    def configureAdjustGet(self) -> int:
        """Query the fine adjustment state"""
        return self._queryAndReturnInt(':CONF:ADJUST?')

    def configureEventClear(self):
        """Reset the Module Event Status register"""
        self._queryAndReturn(':CONF:EVENT CLEAR')

    def configureEventResetMask(self, event: int):
        """Clears single bits or bit combinations in the Module Event Status register by writing a one to the corresponding bit position."""
        self._queryAndReturn(f':CONF:EVENT {event}')

    def configureEventMaskSet(self, word: int):
        """Set the Module Event Mask register"""
        self._queryAndReturn(f':CONF:EVENT:MASK {word}')

    def configureEventMaskGet(self) -> int:
        """Query the Module Event Mask register"""
        return self._queryAndReturnInt(':CONF:EVENT:MASK?')

    def configureEventChannelMaskSet(self, word: int):
        """Set the Module Event Channel Mask register"""
        self._queryAndReturn(f':CONF:EVENT:CHANMASK {word}')

    def configureEventChannelMaskGet(self) -> int:
        """Query the Module Event Channel Mask register"""
        return self._queryAndReturnInt(':CONF:EVENT:CHANMASK?')

    def configureCanAddressSet(self, address: int):
        """Set the modules CAN bus address (0…63). Can only be set in configuration mode."""
        self._queryAndReturn(f':CONF:CAN:ADDR {address}')

    def configureCanAddressGet(self) -> int:
        """Query the modules CAN bus address"""
        return self._queryAndReturnInt(':CONF:CAN:ADDR?')

    def configureCanBitrateSet(self, bitrate: int):
        """Set the CAN bus bit rate to 125 kBit/s or 250 kBit/s. Can only be set in configuration mode."""
        self._queryAndReturn(f':CONF:CAN:BITRATE {bitrate}')

    def configureCanBitrateGet(self) -> int:
        """Query the modules CAN bus bit rate"""
        return self._queryAndReturnInt(':CONF:CAN:BITRATE?')

    def configureSerialBaudrateSet(self, word: int):
        """
        Dynamically switches the serial connection to 115200 Baud.
        If the devices supports baud rate switches, it answers with 115200 and uses this new baudrate afterwards.
        Therefore, the recommended command to change to the higher baud rate is: ':CONF:SERIAL:BAUD 115200;BAUD?'
        Note: The device switches back to 9600 baud after 10 seconds without serial communication or after any power cycle.
        """
        self._queryAndReturn(f':CONF:SERIAL:BAUD {word}')

    def configureSerialBaudrateGet(self) -> int:
        """Query the devices serial baud rate"""
        return self._queryAndReturnInt(':CONF:SERIAL:BAUD?')

    def configureSerialEchoSet(self, echo: bool | int):
        """
        Sets the serial echo:
        1: The device echos all characters received on the serial interface (factory default)
        0: The device does not echo received characters on the serial interface.

        Be careful when switching off the echo as there is no other possibility to synchronize the HV device with the computer (no hardware/software handshake).
        This mode is only available for compatibility reasons and without support.
        """
        self._queryAndReturn(f':CONF:SERIAL:ECHO {int(echo)}')

    def configureSerialEchoGet(self) -> int:
        """Query if there is serial echo is enabled (1) or disabled (0)"""
        return self._queryAndReturnInt(':CONF:SERIAL:ECHO?')

    def readVoltageLimitModule(self) -> float:
        """Query the module voltage limit in percent"""
        return self._queryAndReturnFloat(':READ:VOLT:LIM?', '%')

    def readCurrentLimitModule(self) -> float:
        """Query the module current limit in percent"""
        return self._queryAndReturnFloat(':READ:CURR:LIM?', '%')

    def readRampVoltageSpeedModule(self) -> float:
        """Query the module voltage ramp speed in percent/second"""
        return self._queryAndReturnFloat(':READ:RAMP:VOLT?', '%/s')

    def readRampCurrentSpeedModule(self) -> float:
        """Query the module current ramp speed in percent/second"""
        return self._queryAndReturnFloat(':READ:RAMP:CURR?', '%/s')

    def readModuleControl(self) -> int:
        """Query the Module Control register"""
        return self._queryAndReturnInt(':READ:MODULE:CONTROL?')

    def readModuleStatus(self) -> int:
        """Query the Module Status register"""
        return self._queryAndReturnInt(':READ:MODULE:STATUS?')

    def readModuleEventStatus(self) -> int:
        """Query the Module Event Status register"""
        return self._queryAndReturnInt(':READ:MODULE:EVENT:STATUS?')

    def readModuleEventMask(self) -> int:
        """Query the Module Event Mask register"""
        return self._queryAndReturnInt(':READ:MODULE:EVENT:MASK?')

    def readModuleEventChannelStatus(self) -> int:
        """Query the Module Event Channel Status register"""
        return self._queryAndReturnInt(':READ:MODULE:EVENT:CHANSTAT?')

    def readModuleEventChannelMask(self) -> int:
        """Query the Module Event Channel Mask register"""
        return self._queryAndReturnInt(':READ:MODULE:EVENT:CHANMASK?')

    def readModuleSupply(self, index: int) -> float:
        """
        Query one of the module supplies specified by Index:
            0: +24 V external supply
            1: -24 V external supply
            2: +5 V external supply
            3: +15 V internal supply
            4: -15 V internal supply
            5: +5.0 V internal supply
            6: +3.3 V intern supply
        """
        return self._queryAndReturnFloat(f':READ:MODULE:SUPPLY? (@{index})', 'V')

    def readModelSupplyPositive24V(self) -> float:
        """Query the module supply voltage +24 Volt"""
        return self._queryAndReturnFloat(':READ:MODULE:SUPPLY:P24V?', 'V')

    def readModelSupplyNegative24V(self) -> float:
        """Query the module supply voltage -24 Volt"""
        return self._queryAndReturnFloat(':READ:MODULE:SUPPLY:N24V?', 'V')

    def readModelSupplyPositive5V(self) -> float:
        """Query the module supply voltage +5 Volt"""
        return self._queryAndReturnFloat(':READ:MODULE:SUPPLY:P5V?', 'V')

    def readModelSupplyPositive3V(self) -> float:
        """Query the module supply voltage +3 Volt"""
        return self._queryAndReturnFloat(':READ:MODULE:SUPPLY:P3V?', 'V')

    def readModelSupplyPositive12V(self) -> float:
        """Query the module supply voltage +12 Volt"""
        return self._queryAndReturnFloat(':READ:MODULE:SUPPLY:P12V?', 'V')

    def readModelSupplyNegative12V(self) -> float:
        """Query the module supply voltage -12 Volt"""
        return self._queryAndReturnFloat(':READ:MODULE:SUPPLY:N12V?', 'V')

    def readModelTemperature(self) -> float:
        """Query the module temperature in degree Celsius"""
        return self._queryAndReturnFloat(':READ:MODULE:TEMPERATURE?', 'C')

    def readModelNumberOfChannels(self) -> int:
        """Query the number of channels in the module"""
        return self._queryAndReturnInt(':READ:MODULE:CHANNELNUMBER?')

    def readModelSetvalueChanges(self) -> int:
        """
        Query the setvalue changes counter.
        This counter is incremented each time a set value (like voltage set or a ramp speed) is changed by interface, front panel or an internal event.
        """
        return self._queryAndReturnInt(':READ:MODULE:SETVALUE?')

    def readFirmwareName(self) -> str:
        """Query the modules firmware name"""
        return self._queryAndReturn(':READ:FIRMWARE:NAME?')

    def readFirmwareRelease(self) -> str:
        """Query the firmware release version"""
        return self._queryAndReturn(':READ:FIRMWARE:RELEASE?')

    def systemUserConfigurationSet(self, serial_number: int):
        """
        Set the device to configuration mode to change the CAN bitrate or address.
        Only possible if all channels are off. As parameter, the device serial number must be given.
        For MICC, this also switches the device in a mode where user calibration is possible.
        """
        self._queryAndReturn(f':SYSTEM:USER:CONFIG {serial_number}')

    def systemUserConfigurationReset(self):
        """Set the device back to normal mode"""
        self.systemUserConfigurationSet(0)

    def systemUserConfigurationGet(self) -> int:
        """Returns 1 in configuration mode, otherwise 0"""
        return self._queryAndReturnInt(':SYSTEM:USER:CONFIG?')

    def systemUserConfigurationSave(self):
        """SHR: Saves the changed output mode or polarity to icsConfig.xml"""
        self._queryAndReturnInt(':SYSTEM:USER:CONFIG SAVE')


def assertionTest():
    """
    Different assertion tests
    """

    def testConvertInListUnit():
        """Test if conversion in list format works"""
        assert convertInUnitList(['1', '2', '3']) == [1, 2, 3]
        assert convertInUnitList([' 1', '2', '3 ']) == [1, 2, 3]
        assert convertInUnitList(['1E4', '2E-5', '3']) == [1E4, 2E-5, 3]

        assert convertInUnitList(['1V', '2V', '3V'], 'V') == [1, 2, 3]
        assert convertInUnitList([' 1A', '2A', '3 A'], 'A') == [1, 2, 3]
        assert convertInUnitList(['1E4%', '2E-5%', '3%'], '%') == [1E4, 2E-5, 3]

    def testChannelInChannelString():
        """Test if conversion in channel format works"""
        assert convertInChannelString(2) == ('2', 1)
        assert convertInChannelString([1, 4, 5]) == ('1,4,5', 3)
        assert convertInChannelString(['0', '3', '2 ']) == ('0,2,3', 3)
        assert convertInChannelString('0, 3, 1') == ('0,1,3', 3)
        assert convertInChannelString('0-2') == ('0,1,2', 3)
        assert convertInChannelString('0-2, 5 -7') == ('0,1,2,5,6,7', 6)

    def testToString():
        """Test if conversion from numeric to string format works"""
        assert convertToString(1) == '1.000000E+00'
        assert convertToString(10) == '1.000000E+01'
        assert convertToString(100) == '1.000000E+02'
        assert convertToString(1000) == '1.000000E+03'
        assert convertToString(10000) == '1.000000E+04'
        assert convertToString(2) == '2.000000E+00'
        assert convertToString(123.45) == '1.234500E+02'
        assert convertToString(1234.567) == '1.234567E+03'
        assert convertToString(0.1) == '1.000000E-01'
        assert convertToString(0.01) == '1.000000E-02'
        assert convertToString(0.001) == '1.000000E-03'
        assert convertToString(0.0001) == '1.000000E-04'
        assert convertToString(0) == '0.000000E+00'

        assert convertToString(-1) == '-1.000000E+00'
        assert convertToString(-10) == '-1.000000E+01'
        assert convertToString(-100) == '-1.000000E+02'
        assert convertToString(-1000) == '-1.000000E+03'
        assert convertToString(-10000) == '-1.000000E+04'
        assert convertToString(-2) == '-2.000000E+00'
        assert convertToString(-123.45) == '-1.234500E+02'
        assert convertToString(-1234.567) == '-1.234567E+03'
        assert convertToString(-0.1) == '-1.000000E-01'
        assert convertToString(-0.01) == '-1.000000E-02'
        assert convertToString(-0.001) == '-1.000000E-03'
        assert convertToString(-0.0001) == '-1.000000E-04'
        assert convertToString(-0) == '0.000000E+00'

        assert convertToString(1, 4) == '1.0000E+00'
        assert convertToString(10, 4) == '1.0000E+01'
        assert convertToString(100, 4) == '1.0000E+02'
        assert convertToString(1000, 4) == '1.0000E+03'
        assert convertToString(10000, 4) == '1.0000E+04'
        assert convertToString(2, 4) == '2.0000E+00'
        assert convertToString(123.45, 4) == '1.2345E+02'
        assert convertToString(1234.567, 4) == '1.2346E+03'
        assert convertToString(0.1, 4) == '1.0000E-01'
        assert convertToString(0.01, 4) == '1.0000E-02'
        assert convertToString(0.001, 4) == '1.0000E-03'
        assert convertToString(0.0001, 4) == '1.0000E-04'
        assert convertToString(0, 4) == '0.0000E+00'

    testConvertInListUnit()
    testChannelInChannelString()
    testToString()


def main():
    with ISEGConnection(comport='COM4') as iseg:
        print(iseg.identification())


if __name__ == '__main__':
    assertionTest()
    main()
