from Telnet import TelnetConnection


class MonacoConnection(TelnetConnection):
    """
    Context manager for Monaco RNDIS connection, built on top of the TelnetConnection context manager

    :param host: host name
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    """

    def __init__(
        self,
        host: str,
        port: int = 23,
        timeout: float = 5,
        encoding: str = 'utf-8'
    ):
        super().__init__(
            host,
            port=port,
            timeout=timeout,
            encoding=encoding
        )

        self.terminating_string = '\r\nMonaco> '

    def read_init(self):
        """Reads initial """
        self.read(1024 * 16)
        self.parse_read()

    def parse_read(self, count: int = 1024) -> str:
        """Reads output and strips cursor for next input"""
        recv = self.read(count)
        if not recv.endswith(self.terminating_string):
            raise ConnectionError(
                f'Expected terminating {self.terminating_string.encode(self.encoding)} cursor, but received {recv.encode(self.encoding)}'
            )
        return recv[:-len(self.terminating_string)]

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Close Monaco connection"""
        self.write('EXIT')
        super().__exit__(exception_type, exception_value, exception_traceback)

    def altmod_set(self, mode: bool | int):
        """
        Sets the pulse energy modulation mode:
            n=0 sets control to Extended Interface pin 15
            n=1 sets control to EXT MOD mini BNC connector
        """
        self.write(f'ALTMOD={int(mode)}')
        self.parse_read()

    def amp3h_get(self) -> float:
        """Returns the laser amplifier hours"""
        self.write('?AMP3H')
        return float(self.parse_read())

    def autoip_set(self, mode: bool | int):
        """
        Sets Enable flag to scan for an available IP address:
            n = 0 disabled
            n = 1 enabled
        """
        self.write(f'AUTOIP={int(mode)}')
        self.parse_read()

    def autoip_get(self) -> bool:
        """Returns the AUTOIP function status"""
        self.write('?AUTOIP')
        return int(self.parse_read()) == 1

    def bat_get(self) -> float:
        """Returns battery voltage, nominal 3V"""
        self.write('?BAT')
        return float(self.parse_read())

    def boot(self):
        """Entering this command will reboot the firmware"""
        self.write('BOOT=1')
        self.parse_read()

    def bp_set(self, burst: int):
        """Sets the number of pulses in a burst. Allowed range is 1 to 4,294,967,295 pulses."""
        self.write(f'BP={burst}')
        self.parse_read()

    def bp_get(self) -> int:
        """Returns the number of pulses in a burst"""
        self.write('?BP')
        return int(self.parse_read())

    def bt_get(self) -> float:
        """Returns laser head baseplate measured temperature in °C"""
        self.write('?BT')
        return float(self.parse_read())

    def chen_set(self, mode: int | bool):
        """
        Set chiller enable:
            n = 0 turns off the chiller
            n = 1 turns on the chiller
        """
        self.write(f'CHEN={int(mode)}')
        self.parse_read()

    def chen_get(self) -> bool:
        """Returns status of chiller enable"""
        self.write('?CHEN')
        return int(self.parse_read()) == 1

    def chf_get(self) -> float:
        """Returns chiller flow"""
        self.write('?CHF')
        return float(self.parse_read())

    def chfault_get(self) -> str:
        """Returns chiller faults"""
        self.write('?CHFAULT')
        return self.parse_read()

    def chfh_get(self) -> float:
        """Returns chiller high flow rate warning limit"""
        self.write('?CHFH')
        return float(self.parse_read())

    def chfl_get(self) -> float:
        """Returns chiller low flow rate warning limit"""
        self.write('?CHFL')
        return float(self.parse_read())

    def chflf_get(self) -> float:
        """Returns chiller low flow rate fault limit"""
        self.write('?CHFLF')
        return float(self.parse_read())

    def chp_get(self) -> float:
        """Returns chiller pressure"""
        self.write('?CHP')
        return float(self.parse_read())

    def chph_get(self) -> float:
        """Returns chiller maximum pressure"""
        self.write('?CHPH')
        return float(self.parse_read())

    def chpl_get(self) -> float:
        """Returns chiller minimum pressure"""
        self.write('?CHPL')
        return float(self.parse_read())

    def chserviced_set(self, service: int):
        """Setting n=1 will clear the chiller service warning, and resets the service start time"""
        self.write(f'?CHSERVICED={service}')
        self.parse_read()

    def chservicehrsrem_get(self) -> float:
        """Displays the remaining hours before chiller service is required."""
        self.write('?CHSERVICEHRSREM')
        return float(self.parse_read())

    def chservoperiod_get(self) -> float:
        """Returns light loop period"""
        self.write('?CHSERVOPERIOD')
        return float(self.parse_read())

    def chsn_get(self) -> str:
        """Returns chiller serial number"""
        self.write('?CHSN')
        return self.parse_read()

    def chst_get(self) -> float:
        """Returns chiller set point"""
        self.write('?CHST')
        return float(self.parse_read())

    def cht_get(self) -> float:
        """Returns chiller temperature"""
        self.write('?CHT')
        return float(self.parse_read())

    def chth_get(self) -> float:
        """Returns chiller high temperature limit"""
        self.write('?CHTH')
        return float(self.parse_read())

    def chtl_get(self) -> float:
        """Returns chiller low temperature limit"""
        self.write('?CHTL')
        return float(self.parse_read())

    def cpumt_get(self) -> float:
        """Returns CPU package temperature"""
        self.write('?CPUMT')
        return float(self.parse_read())

    def cput_get(self) -> float:
        """Returns CPU chip temperature"""
        self.write('?CPUT')
        return float(self.parse_read())

    def daf_get(self) -> str:
        """Returns descriptions of active faults"""
        self.write('?DAF')
        return self.parse_read()

    # TODO: better implementation
    def data_get(self, cmd: str) -> str:
        """Returns data from the datalogger"""
        self.write(f'?DATA {cmd}')
        return self.parse_read()

    def d1h_get(self) -> float:
        """Returns the number of operating hours on laser diode 1"""
        self.write('?D1H')
        return float(self.parse_read())

    def d1rc_get(self) -> float:
        """Returns the set maximum current of diode 1 in Amps"""
        self.write('?D1RC')
        return float(self.parse_read())

    def d1sn_get(self) -> str:
        """Returns serial number of the diode 1"""
        self.write('?D1SN')
        return self.parse_read()

    def d2h_get(self) -> float:
        """Returns the number of operating hours on laser diode 2"""
        self.write('?D2H')
        return float(self.parse_read())

    def d2rc_get(self) -> float:
        """Returns the set maximum current of diode 2 in Amps"""
        self.write('?D2RC')
        return float(self.parse_read())

    def d2sn_get(self) -> str:
        """Returns serial number of the diode 2"""
        self.write('?D2SN')
        return self.parse_read()

    def d3h_get(self) -> float:
        """Returns the number of operating hours on laser diode 3"""
        self.write('?D3H')
        return float(self.parse_read())

    def d3llen_get(self) -> bool:
        """Returns the D3 light loop enable"""
        self.write('?D3LLEN')
        return int(self.parse_read()) == 1

    def d3rc_get(self) -> float:
        """Returns the set maximum current of diode 3 in Amps"""
        self.write('?D3RC')
        return float(self.parse_read())

    def d3rcll_get(self) -> float:
        """Returns the D3 rated current before light loop"""
        self.write('?D3RCLL')
        return float(self.parse_read())

    def d3sn_get(self) -> str:
        """Returns serial number of the diode 3"""
        self.write('?D3SN')
        return self.parse_read()

    def dhcp_set(self, mode: int | bool):
        """
        Enables or disables the dynamic host configuration protocol (DHCP):
            n = 0 DHCP is disabled
            n = 1 DHCP is enabled
        """
        self.write(f'DHCP={int(mode)}')
        self.parse_read()

    def dhcp_get(self) -> bool:
        """Returns the status of DHCP"""
        self.write('?DHCP')
        return int(self.parse_read()) == 1

    def dns_set(self, dns: str):
        """Sets the DNS address when DHCP is disabled"""
        self.write(f'DNS={dns}')
        self.parse_read()

    def dns_get(self) -> str:
        """Returns the DNS server address"""
        self.write('?DNS')
        return self.parse_read()

    def dsh_get(self) -> float:
        """Returns the hours of DS"""
        self.write('?DSH')
        return float(self.parse_read())

    def dsllen_get(self) -> bool:
        """Returns DS light loop enable"""
        self.write('?DSLLEN')
        return int(self.parse_read()) == 1

    def dsrc_get(self) -> float:
        """Returns the DS rated current"""
        self.write('?DSRC')
        return float(self.parse_read())

    def dssn_get(self) -> str:
        """Returns the serial number for DS"""
        self.write('?DSSN')
        return self.parse_read()

    def echo_set(self, mode: int | bool):
        """
        Turns the Characters transmitted to the laser (echoed) on or off
            n = 0 turns off echo
            n = 1 turns on echo
        """
        self.write(f'ECHO={int(mode)}')
        self.parse_read()

    def eg_set(self, mode: int | bool):
        """
        Enable the external gate:
            n = 0 disables PulseEQ external gate (default)
            n = 1 turns on PulseEQ external gate
        """
        self.write(f'EG={int(mode)}')
        self.parse_read()

    def eg_get(self) -> bool:
        """Returns the status of DHCP"""
        self.write('?EG')
        return int(self.parse_read()) == 1

    def em_set(self, mode: int | bool):
        """Sets external modulation"""
        self.write(f'EM={int(mode)}')
        self.parse_read()

    def em_get(self) -> bool:
        """Returns external modulation status"""
        self.write('?EM')
        return int(self.parse_read()) == 1

    def ep_set(self, mode: int):
        """Enhanced serial protocol"""
        self.write(f'EP={mode}')
        self.parse_read()

    def ep_get(self) -> int:
        """Returns enhanced serial protocol"""
        self.write('?EP')
        return int(self.parse_read())

    def exit_set(self):
        """Closes an Ethernet connection"""
        self.write('EXIT')
        self.parse_read()

    # TODO: better faults
    def f_get(self) -> str:
        """
        Displays a list of faults, if present.
        Use ?FNAME command to show a description of a particular fault.
        If a fault is present, it will turn off the laser.
        """
        self.write('?F')
        return self.parse_read()

    # TODO: implement pages 4, 5, 6, 7, 8, 9, 10

