from dataclasses import dataclass


from USBPorts import COMConnection


def convert_in_list_unit(data: list, unit: str = '') -> list[str | float]:
    """Tries to convert list of strings and given unit into list with applied conversion function. If it fails, a stripped list will be returned."""

    return_data = [d.strip() for d in data]

    # try to convert into conversion function
    try:
        return [float(d.replace(unit, '')) for d in return_data]
    except ValueError:
        return return_data


def channels_in_channel_string(channels: int | str | list) -> tuple[str, int]:
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
        out_channels = {channels}

    # in list form
    elif isinstance(channels, list):
        out_channels = {int(channel) for channel in channels}

    # in string form
    else:
        out_channels = set()

        for channel in [channel for channel in channels.split(',')]:
            # single channel
            if '-' not in channel:
                out_channels.add(int(channel))
                continue

            # channel range
            channel_parts = channel.split('-')
            if len(channel_parts) > 2:
                raise ValueError(f'Channel range is invalid: {channel}')
            out_channels.update(set(range(int(channel_parts[0]), int(channel_parts[1]) + 1)))

    out_channels = list(out_channels)

    # check if output string might be valid
    if not out_channels:
        raise ValueError('Conversion of channels in channel string failed. No channels selected')

    return ','.join([str(out_channel) for out_channel in sorted(out_channels)]), len(out_channels)


def to_string(inp: float | int, precision: int = 6):
    """Converts a float or integer to a scientific notation with given precision"""
    return f'{float(inp):.{precision}E}'


@dataclass
class ISEGPort:
    """ISEG Port configuration"""
    port: str = ''
    timeout: float = 0.05
    encoding: str = 'utf-8'
    echo: bool = True
    cleaning: bool = True


class ISEGConnection(COMConnection):
    """
    Context manager for ISEG Serial connection, built on top of the COMConnection context manager

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param echo: If device has echo. Will be checked
    :param cleaning: If output cache should be cleared when entering and exiting
    """

    def __init__(
        self,
        comport: str,
        timeout: float = 0.05,
        encoding: str = 'utf-8',
        echo: bool = True,
        cleaning: bool = True
    ):
        super().__init__(
            comport,
            timeout=timeout,
            encoding=encoding,
            echo=echo,
            cleaning=cleaning
        )

    def _query_and_return(self, cmd: str) -> str:
        """Queries command and returns striped result"""
        self.write(cmd)
        return self.readline().strip()

    def _query_and_return_float(self, cmd: str, unit: str = '') -> float:
        """Queries command and returns striped result as float without unit. If float conversion fails, -1 will be returned."""
        try:
            return float(self._query_and_return(cmd).replace(unit, ''))
        except ValueError:
            return -1

    def _query_and_return_int(self, cmd: str, unit: str = '') -> int:
        """Queries command and returns striped result as integer without unit. If integer conversion fails, -1 will be returned."""
        return int(self._query_and_return_float(cmd, unit))

    def _query_and_return_list(self, cmd: str, unit: str = '') -> list:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list"""
        return convert_in_list_unit(self._query_and_return(cmd).split(','), unit)

    def _query_and_return_str_or_list(self, cmd: str, nr_channels: int) -> str | list[str]:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list or string"""
        return self._query_and_return(cmd) if nr_channels == 1 else self._query_and_return_list(cmd)

    def _query_and_return_float_or_list(self, cmd: str, nr_channels: int, unit: str = '') -> float | list[float]:
        """Queries command and returns striped result separated by commas ',' in a (if possible float valued and without unit) list or float"""
        return self._query_and_return_float(cmd, unit) if nr_channels == 1 else self._query_and_return_list(cmd, unit)

    def identification(self) -> str:
        """Query the module identification"""
        return self._query_and_return('*IDN?')

    def clear_status(self):
        """Clear the Module Event Status and all Channel Event Status registers"""
        self._query_and_return('*CLS')

    def reset_device(self):
        """
        Reset the device to save values:
        • turn high voltage off with ramp for all channel
        • set voltage set Vset to zero for all channels
        • set current set Iset to the current nominal for all channels
        """
        self._query_and_return('*RST')

    def instruction_set_get(self) -> str:
        """
        Query the currently selected instruction set. All devices support the EDCP command set.
        Some devices (HPS, EHQ) support further command sets, refer to the devices manual for them.
        """
        return self._query_and_return('*INSTR?')

    def instruction_set_set(self, instruction_set: str):
        """
        Switch the device to the EDCP command set. Only for devices that support other command sets beside EDCP.
        For HPS and EHQ with other command sets, refer to the devices manual. This setting is permanent.
        """
        self._query_and_return(f'*INSTR,{instruction_set}')

    def local_lockout(self):
        """Local Lockout: Front panel buttons and rotary encoders are disabled. The device can only be controlled remotely."""
        self._query_and_return('*LLO')

    def goto_local(self):
        """Goto Local: Front panel buttons and rotary encoders are enabled"""
        self._query_and_return('*GTL')

    def operation_complete(self):
        """Query the operation complete status. The query returns “1” when all commands before this query have been processed."""
        return self._query_and_return('*OPC?')

    def read_module_list(self) -> list:
        """Query which slots are available and returns a comma separated list."""
        return self._query_and_return_list(':READ:MOD:LIST?')

    def read_module_identification(self, slot: int) -> str:
        """Read the module identification for a specific slot"""
        return self._query_and_return(f':READ:MOD:IDENT? (#{slot})')

    def crate_power_query(self) -> int:
        """Returns 0 if the crate backplane is powered off, or 1 if the backplane is powered on"""
        return self._query_and_return_int(':CRATE:POWER?')

    def crate_power_set(self, on: bool | int):
        """CC24: Turn the crate backplane off (0) resp. on (1)"""
        self._query_and_return(f':CRATE:POWER {int(on)}')

    def crate_status(self) -> int:
        """Returns the CC24 Crate Controller Status register"""
        return self._query_and_return_int(':CRATE:STATUS?')

    def crate_event_clear(self):
        """Clears the Crate Controller Event Status register"""
        self._query_and_return(':CRATE:EVENT CLEAR')

    def crate_event_reset_mask(self, reset_mask: int):
        """Clears the given bits in the ResetMask"""
        self._query_and_return(f':CRATE:EVENT {reset_mask}')

    def crate_event_status(self) -> int:
        """Queries the Crate Controller Event Status register"""
        return self._query_and_return_int(':CRATE:EVENT:STATUS?')

    def crate_event_mask_query(self) -> int:
        """Queries the Crate Controller Event Mask register"""
        return self._query_and_return_int(':CRATE:EVENT:MASK?')

    def crate_event_mask_set(self, mask: int):
        """Sets the Crate Controllers Event Mask register"""
        return self._query_and_return_int(f':CRATE:EVENT:MASK {mask}')

    def crate_supply(self, x: int) -> int:
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
        return self._query_and_return_int(f':CRATE:SUPPLY? (@{x})', 'V')

    def crate_temperature(self, y: int) -> float:
        """
        Queries the crate controllers temperatures that effect fan regulation.
            y = 0, y = 1: CC24 internal temperature sensors,
            y = 2: highest module temperature in the crate
        """
        return self._query_and_return_float(f':CRATE:TEMP? (@{y})', 'C')

    def crate_fan_speed(self) -> float:
        """Returns the crates fan speed in percent"""
        return self._query_and_return_float(':CRATE:FAN?', '%')

    def voltage_set(self, channel: int, voltage: float):
        """
        Set the channel voltage set Vset in Volt.
        MICC: If the channel is configured with EPU, the voltage sign defines the polarity of the output voltage.
        """
        self._query_and_return(f':VOLT {to_string(voltage)},(@{channel})')

    def voltage_on(self, channel: int | str | list):
        """Switch on High Voltage with the configured ramp speed"""
        channel, _ = channels_in_channel_string(channel)
        self._query_and_return(f':VOLT ON,(@{channel})')

    def voltage_off(self, channel: int | str | list):
        """Switch off High Voltage with the configured ramp speed"""
        channel, _ = channels_in_channel_string(channel)
        self._query_and_return(f':VOLT OFF,(@{channel})')

    def voltage_emergency_off(self, channel: int | str | list):
        """Shut down the channel High Voltage (without ramp). The channel stays in Emergency Off until the command EMCY˽CLR is given."""
        channel, _ = channels_in_channel_string(channel)
        self._query_and_return(f':VOLT EMCY OFF,(@{channel})')

    def voltage_emergency_clear(self, channel: int | str | list):
        """Clear the channel from state emergency off. The channel goes to state off."""
        channel, _ = channels_in_channel_string(channel)
        self._query_and_return(f':VOLT EMCY CLR,(@{channel})')

    def voltage_boundary_set(self, channel: int, voltage: float):
        """Set the channel voltage bounds Vbounds in Volt"""
        self._query_and_return(f':VOLT:BOUNDS {to_string(voltage)},(@{channel})')

    def current_set(self, channel: int, current: float):
        """Set the channel current set Iset in Ampere"""
        self._query_and_return(f':CURR {to_string(current)},(@{channel})')

    def current_boundary_set(self, channel: int, current: float):
        """Set the channel current bounds Ibounds in Ampere"""
        self._query_and_return(f':CURR:BOUNDS {to_string(current)},(@{channel})')

    def event_clear(self, channel: int | str | list):
        """Clear the Channel Event Status register"""
        channel, _ = channels_in_channel_string(channel)
        self._query_and_return(f':EVENT CLEAR,(@{channel})')

    def event_reset_mask(self, channel: int,  word: int):
        """Clears single bits or bit combinations in the Channel Event Status register by writing a one to the corresponding bit position"""
        self._query_and_return(f':EVENT {word},(@{channel})')

    def event_mask(self, channel: int,  word: int):
        """Set the Channel Event Mask register"""
        self._query_and_return(f':EVENT:MASK {word},(@{channel})')

    def configure_trip_time_set(self, channel: int, time: int):
        """Set the trip timeout with one millisecond resolution"""
        self._query_and_return(f':CONF:TRIP:TIME {time},(@{channel})')

    def configure_trip_time_get(self, channel: int | str | list) -> float | list[float]:
        """Query the programmed trip timeout in milliseconds"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:TRIP:TIME? (@{channel})', nr_channels, 'ms')

    def configure_trip_action_set(self, channel: int, action: int):
        """
        Set the action that should happen when a current trip for the channel occurs
        Action:
            0 – no action, status flag Trip will be set after timeout
            1 – turn off the channel with ramp
            2 – shut down the channel without ramp
            3 – shut down the whole module without ramp
            4 – disable the Delayed Trip function
        """
        self._query_and_return(f':CONF:TRIP:ACTION {action},(@{channel})')

    def configure_trip_action_get(self, channel: int | str | list) -> float | list[float]:
        """Query the action that should happen when a current trip for the channel occurs"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:TRIP:ACTION? (@{channel})', nr_channels)

    def configure_inhibit_action_set(self, channel: int, action: int):
        """
        Set the action that should happen when an External Inhibit for the channel occurs
        Action:
            0 – no action, status flag External Inhibit will be set
            1 – turn off the channel with ramp
            2 – shut down the channel without ramp
            3 – shut down the whole module without
        """
        self._query_and_return(f':CONF:INHP:ACTION {action},(@{channel})')

    def configure_inhibit_action_get(self, channel: int | str | list) -> float | list[float]:
        """Query the action that should happen when an External Inhibit for the channel occurs"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:INHP:ACTION? (@{channel})', nr_channels)

    def configure_output_mode_set(self, channel: int, mode: int):
        """Set the channel output mode. Only values that are contained in output mode list are allowed."""
        self._query_and_return(f':CONF:OUTPUT:MODE {mode},(@{channel})')

    def configure_output_mode_get(self, channel: int | str | list) -> float | list[float]:
        """Query the configured channel output mode"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:OUTPUT:MODE? (@{channel})', nr_channels)

    def configure_output_mode_list(self, channel: int) -> list[float]:
        """Query the available channel output modes as list"""
        return self._query_and_return_list(f':CONF:OUTPUT:MODE:LIST? (@{channel})')

    def configure_output_polarity_set(self, channel: int, positive: bool):
        """Set output polarity (positive = p, negative = n)"""
        positive = 'p' if positive else 'n'
        self._query_and_return(f':CONF:OUTPUT:POL {positive},(@{channel})')

    def configure_output_polarity_get(self, channel: int | str | list) -> bool | list[bool]:
        """Query the current output polarity"""
        channel, nr_channels = channels_in_channel_string(channel)
        result = [True if r.lower() == 'p' else False for r in self._query_and_return_list(f':CONF:OUTPUT:POL? (@{channel})')]
        return result[0] if nr_channels == 1 else result

    def configure_output_polarity_list(self, channel: int) -> list[bool]:
        """Query the available channel output polarities"""
        return [True if r.lower() == 'p' else False for r in self._query_and_return_list(f':CONF:OUTPUT:POL:LIST? (@{channel})')]

    def read_voltage(self, channel: int | str | list) -> float | list[float]:
        """Query the voltage set Vset in Volt"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT? (@{channel})', nr_channels, 'V')

    def read_voltage_limit(self, channel: int | str | list) -> float | list[float]:
        """Query the voltage limit Vlim in Volt"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:LIM? (@{channel})', nr_channels, 'V')

    def read_voltage_nominal(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage nominal Vnom in Volt"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:NOM? (@{channel})', nr_channels, 'V')

    def read_voltage_mode(self, channel: int | str | list) -> float | list[float]:
        """Query the configured channel voltage mode with polarity sign in Volt"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:MODE? (@{channel})', nr_channels, 'V')

    def read_voltage_mode_list(self, channel: int | str | list) -> float | list[float]:
        """Query the available channel voltage modes as list which corresponds to the request configure_output_mode_list()"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:MODE:LIST? (@{channel})', nr_channels, 'V')

    def read_voltage_boundaries(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage bounds Vbounds in Volt"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:BOUNDS? (@{channel})', nr_channels, 'V')

    def read_voltage_on(self, channel: int | str | list) -> float | list[float]:
        """Query the channel control bit Set On"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:ON? (@{channel})', nr_channels, 'V')

    def read_voltage_emergency(self, channel: int | str | list) -> float | list[float]:
        """Query the channel control bit Set Emergency Off"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:VOLT:EMCY? (@{channel})', nr_channels, 'V')

    def read_current(self, channel: int | str | list) -> float | list[float]:
        """Query the current set Iset in Ampere"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CURR? (@{channel})', nr_channels, 'A')

    def read_current_limit(self, channel: int | str | list) -> float | list[float]:
        """Query the current limit Ilim in Ampere"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CURR:LIM? (@{channel})', nr_channels, 'A')

    def read_current_nominal(self, channel: int | str | list) -> float | list[float]:
        """Query the channel current nominal in Ampere, answer is absolute value"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CURR:NOM? (@{channel})', nr_channels, 'A')

    def read_current_mode(self, channel: int | str | list) -> float | list[float]:
        """Query the configured channel current mode in Ampere"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CURR:MODE? (@{channel})', nr_channels, 'A')

    def read_current_mode_list(self, channel: int | str | list) -> float | list[float]:
        """Query the available channel current modes as list which corresponds to the request configure_output_mode_list()"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CURR:MODE:LIST? (@{channel})', nr_channels, 'A')

    def read_current_boundaries(self, channel: int | str | list) -> float | list[float]:
        """Query the channel current bounds Ibounds in Ampere"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CURR:BOUNDS? (@{channel})', nr_channels, 'A')

    def read_ramp_voltage(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage ramp speed in Volt/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:RAMP:VOLT? (@{channel})', nr_channels, 'V/s')

    def read_ramp_voltage_min(self, channel: int | str | list) -> float | list[float]:
        """Query channel voltage ramp speed minimum in Volt/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:RAMP:VOLT:MIN? (@{channel})', nr_channels, 'V/s')

    def read_ramp_voltage_max(self, channel: int | str | list) -> float | list[float]:
        """Query channel voltage ramp speed maximum in Volt/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:RAMP:VOLT:MAX? (@{channel})', nr_channels, 'V/s')

    def read_ramp_current(self, channel: int | str | list) -> float | list[float]:
        """Query channel current ramp speed in Ampere/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:RAMP:CURR? (@{channel})', nr_channels, 'A/s')

    def read_ramp_current_min(self, channel: int | str | list) -> float | list[float]:
        """Query channel current ramp speed minimum in Ampere/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:RAMP:CURR:MIN? (@{channel})', nr_channels, 'A/s')

    def read_ramp_current_max(self, channel: int | str | list) -> float | list[float]:
        """Query channel current ramp speed maximum in Ampere/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:RAMP:CURR:MAX? (@{channel})', nr_channels, 'A/s')

    def read_channel_control(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Control register"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CHAN:CONTROL? (@{channel})', nr_channels)

    def read_channel_status(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Status register"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CHAN:STATUS? (@{channel})', nr_channels)

    def read_channel_event_status(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Event Status register"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CHAN:EVENT:STATUS? (@{channel})', nr_channels)

    def read_channel_event_mask(self, channel: int | str | list) -> float | list[float]:
        """Query the Channel Event Mask register"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':READ:CHAN:EVENT:MASK? (@{channel})', nr_channels)

    def measure_voltage(self, channel: int | str | list) -> float | list[float]:
        """Query the measured channel voltage in Volt"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':MEAS:VOLT? (@{channel})', nr_channels, 'V')

    def measure_current(self, channel: int | str | list) -> float | list[float]:
        """Query the measured channel current in Ampere"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':MEAS:CURR? (@{channel})', nr_channels, 'A')

    def configure_ramp_voltage_set(self, speed: float):
        """Set the module voltage ramp speed in percent/second"""
        self._query_and_return(f':CONF:RAMP:VOLT {to_string(speed)}')

    def configure_ramp_voltage_get(self) -> float:
        """Query the module voltage ramp speed in percent/second"""
        return self._query_and_return_float(':CONF:RAMP:VOLT?', '%/s')

    def configure_ramp_voltage_set_channel(self, channel: int, speed: float):
        """Set the channel voltage ramp up speed in Volt/second"""
        self._query_and_return(f':CONF:RAMP:VOLT {to_string(speed)},(@{channel})')

    def configure_ramp_voltage_up_set(self, channel: int, speed: float):
        """Set the channel voltage ramp up speed in Volt/second"""
        self._query_and_return(f':CONF:RAMP:VOLT:UP {to_string(speed)},(@{channel})')

    def configure_ramp_voltage_up_get(self, channel: int | str | list) -> float | list[float]:
        """Set the channel voltage ramp up speed in Volt/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:RAMP:VOLT:UP? (@{channel})', nr_channels, 'V/s')

    def configure_ramp_voltage_down_set(self, channel: int, speed: float):
        """Set the channel voltage ramp down speed in Volt/second"""
        self._query_and_return(f':CONF:RAMP:VOLT:DOWN {to_string(speed)},(@{channel})')

    def configure_ramp_voltage_down_get(self, channel: int | str | list) -> float | list[float]:
        """Query the channel voltage ramp down speed in Volt/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:RAMP:VOLT:DOWN? (@{channel})', nr_channels, 'V/s')

    def configure_ramp_current_set(self, speed: float):
        """Set the module current ramp speed in percent/second"""
        self._query_and_return(f':CONF:RAMP:CURR {to_string(speed)}')

    def configure_ramp_current_get(self) -> float:
        """Query the module current ramp speed in percent/second"""
        return self._query_and_return_float(':CONF:RAMP:CURR?', '%/s')

    def configure_ramp_current_set_channel(self, channel: int, speed: float):
        """Set the channel current ramp speed for up and down direction in Ampere/second"""
        self._query_and_return(f':CONF:RAMP:CURR {to_string(speed)},(@{channel})')

    def configure_ramp_current_up_set(self, channel: int, speed: float):
        """Set the channel current ramp up speed in Ampere/second"""
        self._query_and_return(f':CONF:RAMP:CURR:UP {to_string(speed)},(@{channel})')

    def configure_ramp_current_up_get(self, channel: int | str | list) -> float | list[float]:
        """Set the channel current ramp up speed in Ampere/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:RAMP:CURR:UP? (@{channel})', nr_channels, 'A/s')

    def configure_ramp_current_down_set(self, channel: int, speed: float):
        """Set the channel current ramp down speed in Ampere/second"""
        self._query_and_return(f':CONF:RAMP:CURR:DOWN {to_string(speed)},(@{channel})')

    def configure_ramp_current_down_get(self, channel: int | str | list) -> float | list[float]:
        """Query the channel current ramp down speed in Ampere/second"""
        channel, nr_channels = channels_in_channel_string(channel)
        return self._query_and_return_float_or_list(f':CONF:RAMP:CURR:DOWN? (@{channel})', nr_channels, 'A/s')

    def configure_average_set(self, average: int):
        """Set the number of digital filter averaging steps. Factory default is 64."""
        self._query_and_return(f':CONF:AVER {average}')

    def configure_average_get(self) -> int:
        """Query the digital filter averaging steps"""
        return self._query_and_return_int(':CONF:AVER?')

    def configure_kill_set(self, kill: bool | int):
        """Set function kill enable (1) or kill disable (0). Factory default is Kill Disable."""
        self._query_and_return(f':CONF:KILL {int(kill)}')

    def configure_kill_get(self) -> int:
        """Query the current value for the kill enable function"""
        return self._query_and_return_int(':CONF:KILL?')

    def configure_adjust_set(self, adjust: bool | int):
        """Set the fine adjustment function on (1) or off (0). Factory default is adjustment on."""
        self._query_and_return(f':CONF:ADJUST {int(adjust)}')

    def configure_adjust_get(self) -> int:
        """Query the fine adjustment state"""
        return self._query_and_return_int(':CONF:ADJUST?')

    def configure_event_clear(self):
        """Reset the Module Event Status register"""
        self._query_and_return(':CONF:EVENT CLEAR')

    def configure_event_reset_mask(self, event: int):
        """Clears single bits or bit combinations in the Module Event Status register by writing a one to the corresponding bit position."""
        self._query_and_return(f':CONF:EVENT {event}')

    def configure_event_mask_set(self, word: int):
        """Set the Module Event Mask register"""
        self._query_and_return(f':CONF:EVENT:MASK {word}')

    def configure_event_mask_get(self) -> int:
        """Query the Module Event Mask register"""
        return self._query_and_return_int(':CONF:EVENT:MASK?')

    def configure_event_channel_mask_set(self, word: int):
        """Set the Module Event Channel Mask register"""
        self._query_and_return(f':CONF:EVENT:CHANMASK {word}')

    def configure_event_channel_mask_get(self) -> int:
        """Query the Module Event Channel Mask register"""
        return self._query_and_return_int(':CONF:EVENT:CHANMASK?')

    def configure_can_address_set(self, address: int):
        """Set the modules CAN bus address (0…63). Can only be set in configuration mode."""
        self._query_and_return(f':CONF:CAN:ADDR {address}')

    def configure_can_address_get(self) -> int:
        """Query the modules CAN bus address"""
        return self._query_and_return_int(':CONF:CAN:ADDR?')

    def configure_can_bitrate_set(self, bitrate: int):
        """Set the CAN bus bit rate to 125 kBit/s or 250 kBit/s. Can only be set in configuration mode."""
        self._query_and_return(f':CONF:CAN:BITRATE {bitrate}')

    def configure_can_bitrate_get(self) -> int:
        """Query the modules CAN bus bit rate"""
        return self._query_and_return_int(':CONF:CAN:BITRATE?')

    def configure_serial_baudrate_set(self, word: int):
        """
        Dynamically switches the serial connection to 115200 Baud.
        If the devices supports baud rate switches, it answers with 115200 and uses this new baudrate afterwards.
        Therefore, the recommended command to change to the higher baud rate is: ':CONF:SERIAL:BAUD 115200;BAUD?'
        Note: The device switches back to 9600 baud after 10 seconds without serial communication or after any power cycle.
        """
        self._query_and_return(f':CONF:SERIAL:BAUD {word}')

    def configure_serial_baudrate_get(self) -> int:
        """Query the devices serial baud rate"""
        return self._query_and_return_int(':CONF:SERIAL:BAUD?')

    def configure_serial_echo_set(self, echo: bool | int):
        """
        Sets the serial echo:
        1: The device echos all characters received on the serial interface (factory default)
        0: The device does not echo received characters on the serial interface.

        Be careful when switching off the echo as there is no other possibility to synchronize the HV device with the computer (no hardware/software handshake).
        This mode is only available for compatibility reasons and without support.
        """
        self._query_and_return(f':CONF:SERIAL:ECHO {int(echo)}')

    def configure_serial_echo_get(self) -> int:
        """Query if there is serial echo is enabled (1) or disabled (0)"""
        return self._query_and_return_int(':CONF:SERIAL:ECHO?')

    def read_voltage_limit_module(self) -> float:
        """Query the module voltage limit in percent"""
        return self._query_and_return_float(':READ:VOLT:LIM?', '%')

    def read_current_limit_module(self) -> float:
        """Query the module current limit in percent"""
        return self._query_and_return_float(':READ:CURR:LIM?', '%')

    def read_ramp_voltage_speed_module(self) -> float:
        """Query the module voltage ramp speed in percent/second"""
        return self._query_and_return_float(':READ:RAMP:VOLT?', '%/s')

    def read_ramp_current_speed_module(self) -> float:
        """Query the module current ramp speed in percent/second"""
        return self._query_and_return_float(':READ:RAMP:CURR?', '%/s')

    def read_module_control(self) -> int:
        """Query the Module Control register"""
        return self._query_and_return_int(':READ:MODULE:CONTROL?')

    def read_module_status(self) -> int:
        """Query the Module Status register"""
        return self._query_and_return_int(':READ:MODULE:STATUS?')

    def read_module_event_status(self) -> int:
        """Query the Module Event Status register"""
        return self._query_and_return_int(':READ:MODULE:EVENT:STATUS?')

    def read_module_event_mask(self) -> int:
        """Query the Module Event Mask register"""
        return self._query_and_return_int(':READ:MODULE:EVENT:MASK?')

    def read_module_event_channel_status(self) -> int:
        """Query the Module Event Channel Status register"""
        return self._query_and_return_int(':READ:MODULE:EVENT:CHANSTAT?')

    def read_module_event_channel_mask(self) -> int:
        """Query the Module Event Channel Mask register"""
        return self._query_and_return_int(':READ:MODULE:EVENT:CHANMASK?')

    def read_module_supply(self, index: int) -> float:
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
        return self._query_and_return_float(f':READ:MODULE:SUPPLY? (@{index})', 'V')

    def read_model_supply_positive_24V(self) -> float:
        """Query the module supply voltage +24 Volt"""
        return self._query_and_return_float(':READ:MODULE:SUPPLY:P24V?', 'V')

    def read_model_supply_negative_24V(self) -> float:
        """Query the module supply voltage -24 Volt"""
        return self._query_and_return_float(':READ:MODULE:SUPPLY:N24V?', 'V')

    def read_model_supply_positive_5V(self) -> float:
        """Query the module supply voltage +5 Volt"""
        return self._query_and_return_float(':READ:MODULE:SUPPLY:P5V?', 'V')

    def read_model_supply_positive_3V(self) -> float:
        """Query the module supply voltage +3 Volt"""
        return self._query_and_return_float(':READ:MODULE:SUPPLY:P3V?', 'V')

    def read_model_supply_positive_12V(self) -> float:
        """Query the module supply voltage +12 Volt"""
        return self._query_and_return_float(':READ:MODULE:SUPPLY:P12V?', 'V')

    def read_model_supply_negative_12V(self) -> float:
        """Query the module supply voltage -12 Volt"""
        return self._query_and_return_float(':READ:MODULE:SUPPLY:N12V?', 'V')

    def read_model_temperature(self) -> float:
        """Query the module temperature in degree Celsius"""
        return self._query_and_return_float(':READ:MODULE:TEMPERATURE?', 'C')

    def read_model_number_of_channels(self) -> int:
        """Query the number of channels in the module"""
        return self._query_and_return_int(':READ:MODULE:CHANNELNUMBER?')

    def read_model_setvalue_changes(self) -> int:
        """
        Query the setvalue changes counter.
        This counter is incremented each time a set value (like voltage set or a ramp speed) is changed by interface, front panel or an internal event.
        """
        return self._query_and_return_int(':READ:MODULE:SETVALUE?')

    def read_firmware_name(self) -> str:
        """Query the modules firmware name"""
        return self._query_and_return(':READ:FIRMWARE:NAME?')

    def read_firmware_release(self) -> str:
        """Query the firmware release version"""
        return self._query_and_return(':READ:FIRMWARE:RELEASE?')

    def system_user_configuration_set(self, serial_number: int):
        """
        Set the device to configuration mode to change the CAN bitrate or address.
        Only possible if all channels are off. As parameter, the device serial number must be given.
        For MICC, this also switches the device in a mode where user calibration is possible.
        """
        self._query_and_return(f':SYSTEM:USER:CONFIG {serial_number}')

    def system_user_configuration_reset(self):
        """Set the device back to normal mode"""
        self.system_user_configuration_set(0)

    def system_user_configuration_get(self) -> int:
        """Returns 1 in configuration mode, otherwise 0"""
        return self._query_and_return_int(':SYSTEM:USER:CONFIG?')

    def system_user_configuration_save(self):
        """SHR: Saves the changed output mode or polarity to icsConfig.xml"""
        self._query_and_return_int(':SYSTEM:USER:CONFIG SAVE')


def openiseg(port: str | ISEGPort, timeout: float = 0.05, encoding: str = 'utf-8', echo: bool = True,
             cleaning: bool = True) -> ISEGConnection:
    """
    Opens ISEGConnection context manager for Serial connection

    :param port: COM Port OR ISEGPort dataclass
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param echo: If device has echo. Will be checked
    :param cleaning: If output cache should be cleared when entering and exiting
    """

    # if port is ISEGPort dataclass
    if isinstance(port, ISEGPort):
        timeout = port.timeout
        encoding = port.encoding
        echo = port.echo
        cleaning = port.cleaning
        port = port.port

    return ISEGConnection(port, timeout, encoding, echo, cleaning)


def assertion_test():
    # Assertion tests
    def test_convert_in_list_unit():
        assert convert_in_list_unit(['1', '2', '3']) == [1, 2, 3]
        assert convert_in_list_unit([' 1', '2', '3 ']) == [1, 2, 3]
        assert convert_in_list_unit(['1E4', '2E-5', '3']) == [1E4, 2E-5, 3]

        assert convert_in_list_unit(['1V', '2V', '3V'], 'V') == [1, 2, 3]
        assert convert_in_list_unit([' 1A', '2A', '3 A'], 'A') == [1, 2, 3]
        assert convert_in_list_unit(['1E4%', '2E-5%', '3%'], '%') == [1E4, 2E-5, 3]

    def test_channel_in_channel_string():
        assert channels_in_channel_string(2) == ('2', 1)
        assert channels_in_channel_string([1, 4, 5]) == ('1,4,5', 3)
        assert channels_in_channel_string(['0', '3', '2 ']) == ('0,2,3', 3)
        assert channels_in_channel_string('0, 3, 1') == ('0,1,3', 3)
        assert channels_in_channel_string('0-2') == ('0,1,2', 3)
        assert channels_in_channel_string('0-2, 5 -7') == ('0,1,2,5,6,7', 6)

    def test_to_string():
        assert to_string(1) == '1.000000E+00'
        assert to_string(10) == '1.000000E+01'
        assert to_string(100) == '1.000000E+02'
        assert to_string(1000) == '1.000000E+03'
        assert to_string(10000) == '1.000000E+04'
        assert to_string(2) == '2.000000E+00'
        assert to_string(123.45) == '1.234500E+02'
        assert to_string(1234.567) == '1.234567E+03'
        assert to_string(0.1) == '1.000000E-01'
        assert to_string(0.01) == '1.000000E-02'
        assert to_string(0.001) == '1.000000E-03'
        assert to_string(0.0001) == '1.000000E-04'
        assert to_string(0) == '0.000000E+00'

        assert to_string(-1) == '-1.000000E+00'
        assert to_string(-10) == '-1.000000E+01'
        assert to_string(-100) == '-1.000000E+02'
        assert to_string(-1000) == '-1.000000E+03'
        assert to_string(-10000) == '-1.000000E+04'
        assert to_string(-2) == '-2.000000E+00'
        assert to_string(-123.45) == '-1.234500E+02'
        assert to_string(-1234.567) == '-1.234567E+03'
        assert to_string(-0.1) == '-1.000000E-01'
        assert to_string(-0.01) == '-1.000000E-02'
        assert to_string(-0.001) == '-1.000000E-03'
        assert to_string(-0.0001) == '-1.000000E-04'
        assert to_string(-0) == '0.000000E+00'

        assert to_string(1, 4) == '1.0000E+00'
        assert to_string(10, 4) == '1.0000E+01'
        assert to_string(100, 4) == '1.0000E+02'
        assert to_string(1000, 4) == '1.0000E+03'
        assert to_string(10000, 4) == '1.0000E+04'
        assert to_string(2, 4) == '2.0000E+00'
        assert to_string(123.45, 4) == '1.2345E+02'
        assert to_string(1234.567, 4) == '1.2346E+03'
        assert to_string(0.1, 4) == '1.0000E-01'
        assert to_string(0.01, 4) == '1.0000E-02'
        assert to_string(0.001, 4) == '1.0000E-03'
        assert to_string(0.0001, 4) == '1.0000E-04'
        assert to_string(0, 4) == '0.0000E+00'

    test_convert_in_list_unit()
    test_channel_in_channel_string()
    test_to_string()


def main():
    iseg_port = ISEGPort(port='COM4', echo=True)
    with openiseg(iseg_port) as iseg:
        print(iseg.identification())


if __name__ == '__main__':
    assertion_test()
    main()
