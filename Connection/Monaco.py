"""
COMMAND        ACCESS    TYPE MIN  MAX     DESCRIPTION
 >             READONLY  INT  0    1       Display a prompt before each command
?>             READONLY  INT               Get prompt status
 ACCESS        READONLY  STR               Change the access Level
?ALL           READONLY  STR               Returns the value of every parameter
?ALTMOD        CUST      INT               Get alternate modulation
 ALTMOD        CUST      INT  0    1       Set alternate modulation
?AMP3H         CUST      FLT               Get AMP3 hours
?AMP3SN        CUST      STR               Get AMP3 serial number
?AUTOIP        CUST      INT               Get enable flag to scan for an available IP address
 AUTOIP        CUST      INT  0    1       Set enable flag to scan for an available IP address
?BAT           CUST      FLT               Get battery voltage
?BP            CUST      I64               Get burst length
 BP            CUST      I64  1 4294967295 Set burst length
?BT            CUST      FLT               Get baseplate 1 temperature
?CHEN          CUST      INT               Get chiller enable
 CHEN          CUST      INT  0    1       Set chiller enable
?CHF           CUST      FLT               Get chiller flow rate
?CHFAULT       CUST      STR               Get chiller faults
?CHFH          CUST      FLT               Get chiller high flow rate warning
?CHFL          CUST      FLT               Get chiller low flow rate warning
?CHFLF         CUST      FLT               Get chiller low flow rate fault
?CHP           CUST      INT               Get chiller pressure
?CHPH          CUST      INT               Get chiller maximum pressure
?CHPL          CUST      INT               Get chiller minimum pressure
?CHSERVEN      CUST      INT               Get chiller service warning enable
 CHSERVICED    CUST      STR               Set chiller serviced status
?CHSERVOPERIOD CUST      INT               Get D3 Light loop period
?CHSERVSTART   CUST      INT               Get start chiller service timer
?CHSN          CUST      STR               Get chiller serial number
?CHST          CUST      FLT               Get chiller set point
?CHT           CUST      FLT               Get chiller temperature
?CHTH          CUST      FLT               Get chiller high temperature limit
?CHTL          CUST      FLT               Get chiller low temperature limit
?CPUMT         CUST      INT               Get module temperature
?CPUT          CUST      INT               Get CPU temperature
?D1H           CUST      FLT               Get D1 hours
?D1RC          CUST      FLT               Get D1 rated current
?D1SN          CUST      STR               Get D1 serial number
?D2H           CUST      FLT               Get D2 hours
?D2RC          CUST      FLT               Get D2 rated current
?D2SN          CUST      STR               Get D2 serial number
?D3H           CUST      FLT               Get D3 hours
?D3LLEN        CUST      INT               Get D3 Light loop enable
?D3RC          CUST      FLT               Get D3 rated current
?D3SN          CUST      STR               Get D3 serial number
?DAF           CUST      STR               Descriptions of active faults
?DATA          READONLY  STR               Return data from the datalogger
?DATASHEET     READONLY  STR               Datasheet filename
?DHCP          CUST      INT               Get DHCP enable status
 DHCP          CUST      INT  0    1       Set DHCP enable
?DNS           CUST      STR               Get the DNS server address
 DNS           CUST      STR               Set the DNS address when DHCP is disabled
?DSH           CUST      FLT               Get DS hours
?DSLLEN        CUST      INT               Get DS Light loop enable
?DSRC          CUST      FLT               Get DS rated current
?DSSN          CUST      STR               Get DS serial number
?E             READONLY  INT               Get echo status
 E             READONLY  INT  0    2       Echo characters back to the sender
?ECHO          READONLY  INT               Get echo status
 ECHO          READONLY  INT  0    2       Echo characters back to the sender
?EG            CUST      INT               Get external gate enable
 EG            CUST      INT  0    1       Set external gate enable
?EM            CUST      INT               Get external modulation
 EM            CUST      INT  0    2       Set external modulation
?EN            READONLY  INT               Are enhanced notifications enabled?
 EN            READONLY  INT  0    1       Enable enhanced notifications
?EP            READONLY  INT               Is the enhanced protocol enabled?
 EP            READONLY  INT  0    4       Use the enhanced protocol
 EXIT          CUST                        Close an Ethernet connection
?F             CUST      STR               Are any faults latched?
 FACK          CUST      INT  1    1       Acknowledge and clear fault codes
?FAULTS        CUST      STR               Return a list of all fault codes
?FH            CUST      STR               Display the fault history
 FHC           CUST                        Clear the fault history
?FNAME         CUST      STR               Get the description of a fault code
?FV            CUST      STR               Get the FPGA version
?GATEWAY       CUST      STR               Get the ethernet gateway
 GATEWAY       CUST      STR               Set the gateway when DHCP is disabled
?GRR           CUST      FLT               Get gate internal rep rate in kHz
 GRR           CUST      FLT  20   1000    Set gate internal rep rate in kHz
?GRREN         CUST      INT               Get enable gate internal rep rate
 GRREN         CUST      INT  0    2       Set enable gate internal rep rate
 GUI           READONLY  STR               Tells the firmware which GUI version is being used
?GUI           READONLY  STR               Get the minimum required GUI version
?HB            READONLY  INT               Get heartbeat timout in secs (0=disabled)
 HB            READONLY  INT  0    300     Set heartbeat timout in secs (0=disabled)
?HELP          READONLY  STR               Query commands, with optional filter
 HELP          READONLY                    Query commands, with optional filter
?HH            CUST      FLT               Get Head hours
?HHL           CUST      FLT               Get head humidity limit
?HOSTNAME      CUST      STR               Get hostname for ethernet connection
 HOSTNAME      CUST      STR               Set hostname for ethernet connection
?HSN           CUST      STR               Get laser head serial number
?HSV           CUST      STR               Get the head software version
?HV            CUST      STR               Get the hardware version
?IP            CUST      STR               Get the IP address
 IP            CUST      STR               Set the static IP address
?IPMAX         CUST      STR               Get end of range for AutoIP scan
 IPMAX         CUST      STR               Set end of range for AutoIP scan
?IPMIN         CUST      STR               Get start of range for AutoIP scan
 IPMIN         CUST      STR               Set start of range for AutoIP scan
?IRE           CUST      FLT               IR energy
?IREC          CUST      INT               IR count
 IREP1         CUST      FLT  0    100     IR point 1 calibration
 IREP2         CUST      FLT  0    100     IR point 2 calibration
?K             CUST      INT               Is the keyswitch on?
?L             CUST      INT               Which state is the system in?
 L             CUST      INT  0    24      Switch the diodes on or off
?LASTIP        CUST      STR               Get last used static IP address
?LM            CUST      STR               Get laser model information
?LNAME         CUST      STR               What is the name of the specified state?
?LOCK          READONLY  STR               What commands are locked?
?LOCKOUT       READONLY  STR               Are other users locked out from this laser?
 LOCKOUT       READONLY  INT  0    1       Prevent other users from controlling this laser
?LPSSN         CUST      STR               Get low power stage serial number
?MAC           CUST      STR               Get the MAC address of the ethernet interface
?MANUAL        READONLY  STR               Operator's manual filename
?MRR           CUST      FLT               Measured amplifier rep rate
?MSC           CUST      INT               Get machine safe shutter count
?MSI           CUST      INT               Get machine safe shutter installed
?NEW           READONLY  STR               Returns every parameter that has changed
 PASSWORD      CUST                        change the customer mode password
?PC            CUST      INT               Get pulse control
 PC            CUST      INT  0    1       Set pulse control
?PD3T          CUST      FLT               Get PD3 temperature
?PD4OPTEN      CUST      INT               Get PD4 optimization enable
?PDSV          CUST      FLT               Get seed photo diode voltage
?PENRGV        CUST      FLT               External pulse energy control voltage
?PEP           CUST      FLT               Get Linearized pulse energy percentage
 PEP           CUST      FLT  0    100     Set Linearized pulse energy percentage
?PERIOD        READONLY  FLT               How often to report new data
 PERIOD        READONLY  FLT  -1   1000    Set how often to report new data
?PM            CUST      INT               Get pulse mode
 PM            CUST      INT  0    6       Set pulse mode
?PROMPT        READONLY  INT               Get prompt status
 PROMPT        READONLY  INT  0    1       Display a prompt before each command
?PSCODE        READONLY  INT               Get the power supply family code
?PSID          READONLY  I64               Get the power supply ID
?PSSN          CUST      STR               Get power supply serial number
?PW            CUST      FLT               Get pulse width
 PW            CUST      FLT  200  100000  Set pulse width in fs
?PWFINE        CUST      FLT               Get pulse width fine tuning in %
 PWFINE        CUST      FLT  -100 100     Set pulse width fine tuning in %
?PWS           CUST      FLT               Get pulse width set point
 QUIT          CUST                        Close an Ethernet connection
?READY         CUST      INT               Laser ready status
?RELH          CUST      FLT               Get head relative humidity
?RELHO         CUST      FLT               Get RH offset
?REN           CUST      INT               Get recirculator control
 REN           CUST      INT  0    1       Set recirculator control
?RL            CUST      FLT               Get RF percent level
 RL            CUST      FLT  0    100     Set RF percent level
?RR            CUST      FLT               Output rep rate
?RRD           CUST      INT               Get rep rate divisor
 RRD           CUST      INT               Set rep rate divisor
?S             CUST      INT               Get shutter state
 S             CUST      INT  0    1       Set shutter state
?SC            CUST      INT               Get shutter count
?SCI           CUST      INT               Get inversion of shutter control input
 SCI           CUST      INT  0    1       Set inversion of shutter control input
?SCOI          CUST      INT               Get shutter control output inversion
 SCOI          CUST      INT  0    1       Set shutter control output inversion
?SE            CUST      INT               Get external shutter control state
?SESSIONS      READONLY  STR               List active connections
?SET           CUST      STR               How is the laser configured?
 SET           CUST                        SET RR,PW,RRD and SEEDERBURST together
?SSI           CUST      INT               Get shutter installed
?SSN           CUST      STR               Get Seed serial number
?SSP           CUST      INT               Get spot position
 SSP           CUST      STR               Set spot position
?SSPC          CUST      INT               Get spot transition count
?SSPH          CUST      FLT               Get spot hour
?SSPS          CUST      INT               Get spot status
?ST            CUST      STR               What is the name of the current state?
?SUBNET        CUST      STR               Get the ethernet subnet
 SUBNET        CUST      STR               Set the subnet when DHCP is disabled
?SV            CUST      STR               Get the software version
 SYNC1         CUST      INT  0    65535   Set Sync1 connector output mode
?SYNC2         CUST      INT               Get Sync2 connector output mode
 SYNC2         CUST      INT  0    65535   Set Sync2 connector output mode
?TIME          CUST      STR               Get local time on the laser clock
 TIME          CUST      STR               Set local time on the laser clock
?TIMEZONE      CUST      STR               What timezone is the laser clock set to?
 TIMEZONE      CUST                        Set the timezone for the laser clock
?TSTL          CUST      INT               check if all temperature servos are tight locked
?TSTLS         CUST      STR               check temperature servos tight locked status
?USB           CUST      STR               Get the mode for the USB connection
 USB           CUST      STR               Set the mode for the USB connection
?W             CUST      STR               Are any warnings latched?
?WH            CUST      STR               Display the warning history
 WHC           CUST                        Clear the warning history
?WNAME         CUST      STR               Get the description of a warning code
"""

from datetime import datetime


from Telnet import TelnetConnection


def try_float(inp, fallback: float = -1) -> float:
    """
    Tries to convert given input into a float; if not successful, the fallback is used

    :param inp: input to convert
    :param fallback: fallback value if conversion fails
    :return: converted input or fallback value
    """

    try:
        return float(inp)
    except ValueError:
        return fallback


class MonacoConnection(TelnetConnection):
    """
    Context manager for Monaco RNDIS connection, built on top of the TelnetConnection context manager

    :param host: host name
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    """

    def __init__(
        self,
        host: str = '169.254.21.151',
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

    def _query_and_return(self, cmd: str) -> str:
        """Queries command and returns result"""
        self.write(cmd)
        return self.parse_read()

    def _query_and_return_float(self, cmd: str) -> float:
        """Queries command and returns result as float. If float conversion fails, -1 will be returned."""
        return try_float(self._query_and_return(cmd))

    def _query_and_return_int(self, cmd: str) -> int:
        """Queries command and returns result as integer. If integer conversion fails, -1 will be returned."""
        return int(self._query_and_return_float(cmd))

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Close Monaco connection"""
        self.write('EXIT')
        super().__exit__(exception_type, exception_value, exception_traceback)

    def __enter__(self):
        """Enters Monaco connection"""
        super().__enter__()
        self.read_init()
        return self

    def altmod_get(self) -> int:
        """Gets the pulse energy modulation mode"""
        return self._query_and_return_int(f'?ALTMOD')

    def altmod_set(self, mode: int | bool):
        """
        Sets the pulse energy modulation mode:
            n=0 sets control to Extended Interface pin 15
            n=1 sets control to EXT MOD mini BNC connector
        """
        self._query_and_return(f'ALTMOD={int(mode)}')

    def amp3h_get(self) -> float:
        """Returns the laser amplifier hours"""
        return self._query_and_return_float('?AMP3H')

    def amp3sn_get(self) -> str:
        """Returns the laser amplifier serial number"""
        return self._query_and_return('?AMP3SN')

    def autoip_set(self, mode: int | bool):
        """
        Sets Enable flag to scan for an available IP address:
            n = 0 disabled
            n = 1 enabled
        """
        self._query_and_return(f'AUTOIP={int(mode)}')

    def autoip_get(self) -> int:
        """Returns the AUTOIP function status"""
        return self._query_and_return_int('?AUTOIP')

    def bat_get(self) -> float:
        """Returns battery voltage, nominal 3V"""
        return self._query_and_return_float('?BAT')

    def boot(self):
        """Entering this command will reboot the firmware"""
        self._query_and_return('BOOT=1')

    def bp_set(self, burst: int):
        """Sets the number of pulses in a burst. Allowed range is 1 to 4,294,967,295 pulses."""
        self._query_and_return(f'BP={burst}')

    def bp_get(self) -> int:
        """Returns the number of pulses in a burst"""
        return self._query_and_return_int('?BP')

    def bt_get(self) -> float:
        """Returns laser head baseplate measured temperature in °C"""
        return self._query_and_return_float('?BT')

    def chen_set(self, mode: int | bool):
        """
        Set chiller enable:
            n = 0 turns off the chiller
            n = 1 turns on the chiller
        """
        self._query_and_return(f'CHEN={int(mode)}')

    def chen_get(self) -> int:
        """Returns status of chiller enable"""
        return self._query_and_return_int('?CHEN')

    def chf_get(self) -> float:
        """Returns chiller flow"""
        return self._query_and_return_float('?CHF')

    # TODO: better faults
    def chfault_get(self) -> str:
        """Returns chiller faults"""
        return self._query_and_return('?CHFAULT')

    def chfh_get(self) -> float:
        """Returns chiller high flow rate warning limit"""
        return self._query_and_return_float('?CHFH')

    def chfl_get(self) -> float:
        """Returns chiller low flow rate warning limit"""
        return self._query_and_return_float('?CHFL')

    def chflf_get(self) -> float:
        """Returns chiller low flow rate fault limit"""
        return self._query_and_return_float('?CHFLF')

    def chp_get(self) -> float:
        """Returns chiller pressure"""
        return self._query_and_return_float('?CHP')

    def chph_get(self) -> float:
        """Returns chiller maximum pressure"""
        return self._query_and_return_float('?CHPH')

    def chpl_get(self) -> float:
        """Returns chiller minimum pressure"""
        return self._query_and_return_float('?CHPL')

    def chserven_get(self) -> int:
        """Get chiller service warning enable"""
        return self._query_and_return_int('?CHSERVEN')

    def chserviced_set(self, service: str):
        """Setting n=1 will clear the chiller service warning, and resets the service start time"""
        self._query_and_return(f'?CHSERVICED={service}')

    def chservicehrsrem_get(self) -> float:
        """Displays the remaining hours before chiller service is required."""
        return self._query_and_return_float('?CHSERVICEHRSREM')

    def chservoperiod_get(self) -> float:
        """Returns light loop period"""
        return self._query_and_return_float('?CHSERVOPERIOD')

    def chservstart_get(self) -> float:
        """Get start chiller service timer"""
        return self._query_and_return_float('?CHSERVSTART')

    def chsn_get(self) -> str:
        """Returns chiller serial number"""
        return self._query_and_return('?CHSN')

    def chst_get(self) -> float:
        """Returns chiller set point"""
        return self._query_and_return_float('?CHST')

    def cht_get(self) -> float:
        """Returns chiller temperature"""
        return self._query_and_return_float('?CHT')

    def chth_get(self) -> float:
        """Returns chiller high temperature limit"""
        return self._query_and_return_float('?CHTH')

    def chtl_get(self) -> float:
        """Returns chiller low temperature limit"""
        return self._query_and_return_float('?CHTL')

    def cpumt_get(self) -> float:
        """Returns CPU package temperature"""
        return self._query_and_return_float('?CPUMT')

    def cput_get(self) -> float:
        """Returns CPU chip temperature"""
        return self._query_and_return_float('?CPUT')

    # TODO: better errors
    def daf_get(self) -> str:
        """Returns descriptions of active faults"""
        return self._query_and_return('?DAF')

    # TODO: better data get
    def data_get(self, cmd: str) -> str:
        """Returns data from the datalogger"""
        return self._query_and_return(f'?DATA {cmd}')

    def datasheet_get(self) -> str:
        """Returns name of datasheet"""
        return self._query_and_return(f'?DATASHEET')

    def d1h_get(self) -> float:
        """Returns the number of operating hours on laser diode 1"""
        return self._query_and_return_float('?D1H')

    def d1rc_get(self) -> float:
        """Returns the set maximum current of diode 1 in Amps"""
        return self._query_and_return_float('?D1RC')

    def d1sn_get(self) -> str:
        """Returns serial number of the diode 1"""
        return self._query_and_return('?D1SN')

    def d2h_get(self) -> float:
        """Returns the number of operating hours on laser diode 2"""
        return self._query_and_return_float('?D2H')

    def d2rc_get(self) -> float:
        """Returns the set maximum current of diode 2 in Amps"""
        return self._query_and_return_float('?D2RC')

    def d2sn_get(self) -> str:
        """Returns serial number of the diode 2"""
        return self._query_and_return('?D2SN')

    def d3h_get(self) -> float:
        """Returns the number of operating hours on laser diode 3"""
        return self._query_and_return_float('?D3H')

    def d3llen_get(self) -> int:
        """Returns the D3 light loop enable"""
        return self._query_and_return_int('?D3LLEN')

    def d3rc_get(self) -> float:
        """Returns the set maximum current of diode 3 in Amps"""
        return self._query_and_return_float('?D3RC')

    def d3rcll_get(self) -> float:
        """Returns the D3 rated current before light loop"""
        return self._query_and_return_float('?D3RCLL')

    def d3sn_get(self) -> str:
        """Returns serial number of the diode 3"""
        return self._query_and_return('?D3SN')

    def dhcp_set(self, mode: int | bool):
        """
        Enables or disables the dynamic host configuration protocol (DHCP):
            n = 0 DHCP is disabled
            n = 1 DHCP is enabled
        """
        self._query_and_return(f'DHCP={int(mode)}')

    def dhcp_get(self) -> int:
        """Returns the status of DHCP"""
        return self._query_and_return_int('?DHCP')

    def dns_set(self, dns: str):
        """Sets the DNS address when DHCP is disabled"""
        self._query_and_return(f'DNS={dns}')

    def dns_get(self) -> str:
        """Returns the DNS server address"""
        return self._query_and_return('?DNS')

    def dsh_get(self) -> float:
        """Returns the hours of DS"""
        return self._query_and_return_float('?DSH')

    def dsllen_get(self) -> int:
        """Returns DS light loop enable"""
        return self._query_and_return_int('?DSLLEN')

    def dsrc_get(self) -> float:
        """Returns the DS rated current"""
        return self._query_and_return_float('?DSRC')

    def dssn_get(self) -> str:
        """Returns the serial number for DS"""
        return self._query_and_return('?DSSN')

    def echo_set(self, mode: int | bool):
        """
        Turns the Characters transmitted to the laser (echoed) on or off
            n = 0 turns off echo
            n = 1 turns on echo
        """
        self._query_and_return(f'ECHO={int(mode)}')

    def echo_get(self) -> int:
        """Returns echo mode"""
        return self._query_and_return_int('?ECHO')

    def eg_set(self, mode: int | bool):
        """
        Enable the external gate:
            n = 0 disables PulseEQ external gate (default)
            n = 1 turns on PulseEQ external gate
        """
        self._query_and_return(f'EG={int(mode)}')

    def eg_get(self) -> int:
        """Returns the status of DHCP"""
        return self._query_and_return_int('?EG')

    def em_set(self, mode: int | bool):
        """Sets external modulation"""
        self._query_and_return(f'EM={int(mode)}')

    def em_get(self) -> int:
        """Returns external modulation status"""
        return self._query_and_return_int('?EM')

    def en_set(self, mode: int | bool):
        """Enable enhanced notifications"""
        self._query_and_return(f'EN={int(mode)}')

    def en_get(self) -> int:
        """Returns enhanced notifications status"""
        return self._query_and_return_int('?EN')

    def ep_set(self, mode: int):
        """Enhanced serial protocol"""
        self._query_and_return(f'EP={mode}')

    def ep_get(self) -> int:
        """Returns enhanced serial protocol"""
        return self._query_and_return_int('?EP')

    def exit_set(self):
        """Closes an Ethernet connection"""
        self._query_and_return('EXIT')

    # TODO: better faults
    def f_get(self) -> str:
        """
        Displays a list of faults, if present.
        Use ?FNAME command to show a description of a particular fault.
        If a fault is present, it will turn off the laser.
        """
        return self._query_and_return('?F')

    def fack_set(self):
        """Acknowledge faults and return the laser to a ready state if the fault condition is lifted"""
        self._query_and_return('FACK=1')

    # TODO: better faults
    def faults_get(self) -> str:
        """Returns a list of numbered codes of all active faults. separated by an &, or returns “System OK” if no active faults"""
        return self._query_and_return('?FAULTS')

    # TODO: better faults
    def fh_get(self) -> str:
        """
        Returns the fault history with index numbers delimited by “&” sign with no spaces.
        Faults are recorded in chronological order since last AC power up or last FHC command.
        Fault history is limited to the last 20 faults.
        """
        return self._query_and_return('?FH')

    def fhc_set(self):
        """Clears the fault history"""
        self._query_and_return('FHC')

    def fname_get(self, code: int) -> str:
        """Returns the description of fault code or warning code nn"""
        return self._query_and_return(f'?FNAME:{code}')

    def fv_get(self) -> str:
        """Returns the version number of the FPGA firmware of the laser"""
        return self._query_and_return('?FV')

    def gateway_set(self, gateway: str):
        """Set the gateway when DHCP is disabled"""
        self._query_and_return(f'GATEWAY={gateway}')

    def gateway_get(self) -> str:
        """Returns the Ethernet gateway"""
        return self._query_and_return('?GATEWAY')

    def grr_set(self, rate: float):
        """Sets the PulseEQ internal repetition rate to {rate}kHz"""
        self._query_and_return(f'GRR={rate}')

    def grr_get(self) -> float:
        """Returns the Ethernet gateway"""
        return self._query_and_return_float('?GRR')

    def grren_set(self, mode: int | bool):
        """
        Enables the internal repetition rate gate:
            n = 0 disables PulseEQ Internal triggering
            n = 1 enables PulseEQ Internal triggering
        """
        self._query_and_return(f'GRREN={int(mode)}')

    def grren_get(self) -> int:
        """Returns the status of the internal repetition rate gate"""
        return self._query_and_return_int('?GRREN')

    def gui_get(self) -> str:
        """Returns the status of the internal repetition rate gate"""
        return self._query_and_return('?GUI')

    def hb_set(self, time: int):
        """Sets the heartbeat timeout in secs, 0 or 5-300 (0=disabled)"""
        self._query_and_return(f'HB={time}')

    def hb_get(self) -> int:
        """Returns the heartbeat timeout in seconds (0=disabled)"""
        return self._query_and_return_int('?HB')

    # TODO: better help
    def help_get(self, search: str = '') -> str:
        """Query commands, with optional filter"""
        cmd = '?HELP'
        if search:
            cmd += f' {search}'
        return self._query_and_return(cmd)

    def hh_get(self) -> float:
        """Returns the number of operating hours on the system head"""
        return self._query_and_return_float('?HH')

    def hhl_get(self) -> float:
        """Returns the laser head humidity warning limit"""
        return self._query_and_return_float('?HHL')

    def hostname_set(self, hostname: str):
        """Sets host name for Ethernet connection"""
        self._query_and_return(f'HOSTNAME={hostname}')

    def hostname_get(self) -> str:
        """Returns host name of Ethernet connection"""
        return self._query_and_return('?HOSTNAME')

    def hsn_get(self) -> str:
        """Returns serial number of the laser head"""
        return self._query_and_return('?HSN')

    def hsv_get(self) -> str:
        """Returns firmware version of the laser head as HEAD rev x.xx, date"""
        return self._query_and_return('?HSV')

    def hv_get(self) -> str:
        """Displays the internal revision level of major hardware components"""
        return self._query_and_return('?HV')

    def ip_set(self, ip: str):
        """Sets the static IP address"""
        self._query_and_return(f'IP={ip}')

    def ip_get(self) -> str:
        """Returns the IP address for Ethernet"""
        return self._query_and_return('?IP')

    def ipmax_set(self, ip: str):
        """Sets end of range for AutoIP scan"""
        self._query_and_return(f'IPMAX={ip}')

    def ipmax_get(self) -> str:
        """Returns end of range for AutoIP scan"""
        return self._query_and_return('?IPMAX')

    def ipmin_set(self, ip: str):
        """Sets start of range for AutoIP scan"""
        self._query_and_return(f'IPMIN={ip}')

    def ipmin_get(self) -> str:
        """Returns start of range for AutoIP scan"""
        return self._query_and_return('?IPMIN')

    def ire_get(self) -> float:
        """Returns the IR energy"""
        return self._query_and_return_float('?IRE')

    def irec_get(self) -> int:
        """Returns the IR count"""
        return self._query_and_return_int('?IREC')

    def irep1_set(self, value: float):
        """Sets the IR point 1 calibration"""
        self._query_and_return(f'IREP1={value}')

    def irep2_set(self, value: float):
        """Sets the IR point 2 calibration"""
        self._query_and_return(f'IREP2={value}')

    def k_get(self) -> int:
        """
        Returns laser enable keyswitch state:
            0 = laser in Standby (laser diodes cannot be turned on)
            1 = laser enabled
        """
        return self._query_and_return_int('?K')

    def l_set(self, state: int | bool):
        """
        Sets the laser state:
            0 = turns off laser
            1 = turns on laser
        """
        self._query_and_return(f'L={int(state)}')

    def l_get(self) -> int:
        """
        Returns laser state:
            0 = if the laser is in STANDBY, key-switch is off
            1 = a fault is active and the system has been shut down
            2 = if the laser is READY, key-switch is on but the diodes are off
            24 = if the laser is ON, all the diodes are on and the laser is ready to produce output pulses
        """
        return self._query_and_return_int('?L')

    def lip_get(self) -> str:
        """Returns last used static IP address"""
        return self._query_and_return('?LIP')

    def lm_get(self) -> str:
        """Returns the laser model"""
        return self._query_and_return('?LM')

    def lname_get(self, state: int) -> str:
        """Returns name of the specified laser state"""
        return self._query_and_return(f'?LNAME={state}')

    def lock_get(self) -> str:
        """Returns locked commands"""
        return self._query_and_return('?LOCK')

    def lockout_set(self, mode: int | bool):
        """
        Sets laser LOCKOUT control state (only one connection can have exclusive control of laser at any given time):
            n = 0 unlocks laser to release control to other remote control device. The next remote device issuing a command will have exclusive
                  control, which sets LOCKOUT=1 for that device.
            n = 1 locks out other remote devices from controlling laser; only current control device has exclusive control of laser (default)
        """
        self._query_and_return(f'LOCKOUT={int(mode)}')

    def lockout_get(self) -> int:
        """
        Returns LOCKOUT state of laser control:
            0 = laser is unlocked from current connection for control by another remote control device or connection.
            1 = laser remote control is locked out: only current connection has exclusive control of the laser
            x = a connection from device X has exclusive control of the laser
        """
        return self._query_and_return_int('?LOCKOUT')

    # TODO: better implementation
    def lookup_reprates_names_get(self) -> str:
        """
        Returns a list of the laser repetition rates/seeder burst lengths that are available in the format:
        {reprate in kHz}:{seeder burst length}
        """
        return self._query_and_return('?LOOKUP REPRATES NAMES')

    def lpssn_get(self) -> str:
        """Returns low power stage serial number"""
        return self._query_and_return('?LPSSN')

    def mac_get(self) -> str:
        """Returns the MAC address of the Ethernet interface"""
        return self._query_and_return('?MAC')

    def manual_get(self) -> str:
        """Returns the operator's manual filename"""
        return self._query_and_return('?MANUAL')

    def mrr_get(self) -> float:
        """Returns the laser amplifier repetition rate (in kHz)"""
        return self._query_and_return_float('?MRR')

    def msc_get(self) -> int:
        """Get machine safe shutter count"""
        return self._query_and_return_int('?MSC')

    def msi_get(self) -> int:
        """Get machine safe shutter installed"""
        return self._query_and_return_int('?MSI')

    # TODO: better output
    def new_get(self) -> str:
        """Returns every parameter that has changed"""
        return self._query_and_return('?NEW')

    def password_set(self, password: str):
        """Sets up or changes the user password"""
        self._query_and_return(f'PASSWORD={password}')

    def pc_set(self, mode: int | bool):
        """
        Sets pulse control:
            n = 0 is pulse control off
            n = 1 is pulse control on
        """
        self._query_and_return(f'PC={int(mode)}')

    def pc_get(self) -> int:
        """Returns the status of pulse control"""
        return self._query_and_return_int('?PC')

    def pd3t_get(self) -> float:
        """Returns the status of pulse control"""
        return self._query_and_return_float('?PD3T')

    def pd4opten_get(self) -> int:
        """
        Returns PD4 optimization enable status:
            0 = PD4 optimization off
            1 = PD4 optimization on
        """
        return self._query_and_return_int('?PD4OPTEN')

    def pdsv_get(self) -> float:
        """Returns seed photodiode voltage"""
        return self._query_and_return_float('?PDSV')

    def penrgv_get(self) -> float:
        """Returns the external pulse energy control voltage"""
        return self._query_and_return_float('?PENRGV')

    def pep_set(self, percentage: float):
        """Sets the output pulse energy as percentage of maximum, 0 to 100"""
        self._query_and_return(f'PEP={percentage}')

    def pep_get(self) -> float:
        """Returns the current pulse energy percentage"""
        return self._query_and_return_float('?PEP')

    def period_set(self, period: float):
        """Set how often to report new data"""
        self._query_and_return(f'PERIOD={period}')

    def period_get(self) -> float:
        """Return how often to report new data"""
        return self._query_and_return_float('?PERIOD')

    def pm_set(self, mode: int):
        """
        Sets the pulse mode:
            n = 0 for Continuous pulsing
            n = 1 for Gated mode
            n = 2 for Divided mode
            n = 3 for Divided and Gated mode
            n = 4 for Burst mode
            n = 5 for Burst and Divided mode
        """
        self._query_and_return(f'PM={mode}')

    def pm_get(self) -> int:
        """Returns the pulse mode"""
        return self._query_and_return_int('?PM')

    def prompt_set(self, mode: int | bool):
        """
        Sets the mode of prompt:
            n = 0 turns off “Monaco Laser >” prompt
            n = 1 turns on “Monaco Laser >” prompt
        """
        self._query_and_return(f'PROMPT={int(mode)}')

    def prompt_get(self) -> int:
        """Return the mode of prompt"""
        return self._query_and_return_int('?PROMPT')

    def pscode_get(self) -> int:
        """Return the power supply family code"""
        return self._query_and_return_int('?PSCODE')

    def psid_get(self) -> int:
        """Return the power supply ID"""
        return self._query_and_return_int('?PSID')

    def pssn_get(self) -> str:
        """Returns the power supply serial number"""
        return self._query_and_return('?PSSN')

    def pw_set(self, width: float):
        """Sets the pulse width in femtoseconds"""
        self._query_and_return(f'PW={width}')

    def pw_get(self) -> float:
        """Return the pulse width in femtoseconds"""
        return self._query_and_return_float('?PW')

    def pwfine_set(self, tuning: float):
        """
        Sets the pulse width fine tuning in %, range of -100 to 100.
        This works in conjunction with the Peak Power Optimizer.
        """
        self._query_and_return(f'PWFINE={tuning}')

    def pwfine_get(self) -> float:
        """Returns the pulse width fine tuning in %"""
        return self._query_and_return_float('?PWFINE')

    def pws_get(self) -> float:
        """Returns the pulse width set point"""
        return self._query_and_return_float('?PWS')

    def quit_set(self):
        """Closes an Ethernet connection"""
        self._query_and_return('QUIT')

    def ready_get(self) -> int:
        """Returns laser ready status"""
        return self._query_and_return_int('?READY')

    def relh_get(self) -> float:
        """Returns the relative humidity"""
        return self._query_and_return_float('?RELH')

    def relho_get(self) -> float:
        """Returns the relative humidity offset"""
        return self._query_and_return_float('?RELHO')

    def ren_set(self, mode: int | bool):
        """
        Enables or disables the air recirculator inside the laser head:
            n = 0 disables the recirculator
            n = 1 enables the recirculator
        """
        self._query_and_return(f'REN={int(mode)}')

    def ren_get(self) -> int:
        """Returns recirculator control status"""
        return self._query_and_return_int('?REN')

    def rl_set(self, percentage: float):
        """Sets the Output AOM voltage as percentage of maximum, from 0 to 100"""
        self._query_and_return(f'RL={percentage}')

    def rl_get(self) -> float:
        """Returns the Output AOM voltage as percentage of maximum"""
        return self._query_and_return_float('?RL')

    def rr_get(self) -> float:
        """Returns the laser pulse or seeder burst output repetition rate in Hz"""
        return self._query_and_return_float('?RR')

    def rrd_set(self, divisor: int):
        """Allows the amplifier laser pulse repetition rate to be divided by an integer"""
        self._query_and_return(f'RRD={divisor}')

    def rrd_get(self) -> int:
        """Returns the laser pulse repetition rate divisor"""
        return self._query_and_return_int('?RRD')

    def s_set(self, mode: int | bool):
        """
        Sets the shutter state:
            n = 0 closes external shutter
            n = 1 opens external shutter
        """
        self._query_and_return(f'S={int(mode)}')

    def s_get(self) -> int:
        """Returns the shutter cycle counter value"""
        return self._query_and_return_int('?SC')

    def sc_get(self) -> int:
        """Returns inversion of shutter control input value"""
        return self._query_and_return_int('?SCI')

    def sci_set(self, mode: int | bool):
        """
        Shutter control inversion:
            n = 0 disables inversion (default)
            n = 1 enables inversion
        """
        self._query_and_return(f'SCI={int(mode)}')

    def sci_get(self) -> int:
        """Returns inversion of shutter control input value"""
        return self._query_and_return_int('?SCI')

    def scoi_set(self, mode: int | bool):
        """
        Shutter control output inversion:
            n = 0 disables output inversion (default)
            n = 1 enables output inversion
        """
        self._query_and_return(f'SCOI={int(mode)}')

    def scoi_get(self) -> int:
        """Returns inversion of shutter control output inversion"""
        return self._query_and_return_int('?SCOI')

    def se_get(self) -> int:
        """
        Returns the shutter control (pin 17) state:
            0 = pin 17 at GND and S = 0 (both are off)
            1 = pin 17 at GND and S = 1
            2 = pin 17 is high and S = 0
            3 = pin 17 is high and S = 1 (both are on)
        """
        return self._query_and_return_int('?SE')

    # TODO: better output
    def sessions_get(self) -> str:
        """Lists the active connections"""
        return self._query_and_return('?SESSIONS')

    def set_set(
        self,
        mrr: float = -1,
        pw: float = -1,
        rrd: int = -1,
        pulses: int = -1,
        name: str = '',
        grr: float = -1,
        eg: int | bool = -1
    ):
        """
        Sets several laser parameters simultaneously including:
            MRR: amplifier repetition rate
            PW: pulse width
            RRD: repetition rate divisor
            PULSES: number of pulses per seeder burst
            NAME: named operation modes
            GRR: internal triggering rate
            EG: enable external gating
        Unset values will not be set
        """

        cmd = 'SET'
        if mrr != -1:
            cmd += f' MRR={mrr}'
        if pw != -1:
            cmd += f' PW={pw}'
        if rrd != -1:
            cmd += f' RRD={rrd}'
        if pulses != -1:
            cmd += f' PULSES={pulses}'
        if name:
            cmd += f' NAME={name}'
        if grr != -1:
            cmd += f' GRR={grr}'
        if eg != -1:
            cmd += f' EG={eg}'

        self._query_and_return(cmd)

    # TODO: better output variables
    def set_get(self) -> tuple[float, float, int, int]:
        """
        Returns the current values for the laser parameters:
            MRR: amplifier repetition rate in kHz
            PW: pulse width in femtoseconds,
            RRD: repetition rate divisor
            SB: number of seeder bursts
        """
        query = self._query_and_return('?SET').split(',')
        query.extend(['0'] * (4 - len(query)))
        return (
            try_float(query[0]),
            try_float(query[1]),
            int(try_float(query[2])),
            int(try_float(query[3]))
        )

    def sis_get(self) -> int:
        """
        Returns the status of the shutter interlock sense:
            0 = shutter interlock closed
            1 = shutter interlock open
        """
        return self._query_and_return_int('?SIS')

    def srr_get(self) -> float:
        """Returns the seed laser pulse repetition rate"""
        return self._query_and_return_float('?SRR')

    def ssi_get(self) -> int:
        """
        Returns the status of the shutter installation:
            0 = Shutter not installed
            1 = Shutter installed
        """
        return self._query_and_return_int('?SSI')

    def ssn_get(self) -> str:
        """Get Seed serial number"""
        return self._query_and_return('?SSN')

    def ssp_set(self, position: str):
        """Sets the SESAM spot position"""
        self._query_and_return(f'SSP={position}')

    def ssp_int(self) -> int:
        """Returns current SESAM spot position"""
        return self._query_and_return_int('?SSP')

    def sspc_int(self) -> int:
        """Returns the SESAM spot transition count"""
        return self._query_and_return_int('?SSPC')

    def ssph_int(self) -> float:
        """Returns current SESAM spot hours"""
        return self._query_and_return_float('?SSPH')

    def ssps_int(self) -> int:
        """Returns SESAM spot status"""
        return self._query_and_return_int('?SSPS')

    def st_get(self) -> str:
        """Returns the name of the current laser state"""
        return self._query_and_return('?ST')

    def subnet_set(self, subnet: str):
        """Sets the subnet when DHCP is disabled"""
        self._query_and_return(f'SUBNET={subnet}')

    def subnet_get(self) -> str:
        """Returns the Ethernet subnet"""
        return self._query_and_return('?SUBNET')

    def sv_get(self) -> str:
        """Displays the revision level of major software components"""
        return self._query_and_return('?SV')

    def sync1_set(self, mode: int | bool):
        """
        Sets the output from the Sync 1 HD-BNC connector on the back of the laser head:
            n = 0 provides a representation of the drive signal for AOM1
                  (if shutter closed/pulsing off then output is the amplifier rep rate)
            n = 1 provides a representation of the seeder pulses
        """
        self._query_and_return(f'SYNC1={int(mode)}')

    def sync1_get(self) -> int:
        """Returns the output setting from the Sync 1 HD-BNC connector"""
        return self._query_and_return_int('?SYNC1')

    def sync2_set(self, mode: int | bool):
        """
        Sets the output from the Sync 2 HD-BNC connector on the back of the laser head:
            n = 0 provides a representation of the drive signal for AOM2
                  (if shutter closed/pulsing off then output is the amplifier rep rate)
            n = 1 provides a representation of the seeder pulses
        """
        self._query_and_return(f'SYNC2={int(mode)}')

    def sync2_get(self) -> int:
        """Returns the output setting from the Sync 2 HD-BNC connector"""
        return self._query_and_return_int('?SYNC2')

    def time_set(self, date_time: datetime | None):
        """Sets local time on the laser clock. If left empty the current time will be used."""
        if date_time is None:
            date_time = datetime.now()
        self._query_and_return(f'TIME={date_time.strftime("%Y-%m-%d %H:%M")}')

    def time_get(self) -> datetime:
        """Returns local time on the laser clock"""
        query = self._query_and_return('?TIME')
        try:
            return datetime.strptime(query, '%Y-%m-%d %H:%M.%S')
        except ValueError:
            return datetime(1, 1, 1)

    def timezone_set(self, timezone: str):
        """Sets local time zone on the laser clock"""
        self._query_and_return(f'TIMEZONE={timezone}')

    def timezone_get(self) -> str:
        """Returns local time zone on the laser clock"""
        return self._query_and_return('?TIMEZONE')

    # TODO: better returning
    def timezones_get(self) -> str:
        """Returns available time zones for this laser"""
        return self._query_and_return('?TIMEZONES')

    def tstl_get(self) -> int:
        """Checks if all temperature servos are tight locked"""
        return self._query_and_return_int('?TSTL')

    def tstls_get(self) -> str:
        """Returns the temperature servos tight locked status"""
        return self._query_and_return('?TSTLS')

    def usb_set(self, connection: str):
        """Set the mode for the USB connection"""
        self._query_and_return(f'USB={connection}')

    def usb_get(self) -> str:
        """Returns the USB connection mode"""
        return self._query_and_return('?USB')

    # TODO: better output
    def w_get(self) -> str:
        """Displays a list of warnings"""
        return self._query_and_return('?W')

    # TODO: better output
    def wh_get(self) -> str:
        """Displays the warning history"""
        return self._query_and_return('?WH')

    def whc_set(self):
        """Clears the warning history"""
        self._query_and_return('WHC')

    def wname_get(self, code: int) -> str:
        """Returns the description of a warning code"""
        return self._query_and_return(f'?WNAME={code}')

    def identification(self) -> str:
        """Get the laser identification"""
        return f'Connected to {self.lm_get()} with S/N {self.hsn_get()}'


def main():
    with MonacoConnection() as monaco:
        for func in dir(monaco):
            if not func.endswith('_get'):
                continue
            if func in ['faults_get', 'help_get', 'new_get', 'sessions_get', 'timezones_get']:
                continue

            try:
                print(f'{func}: {getattr(monaco, func)()}')
            except (TypeError, ConnectionError):
                pass

    """
    altmod_get: 1
    amp3h_get: 712.996
    amp3sn_get: K0073943
    autoip_get: 1
    bat_get: 3.045
    bp_get: 1
    bt_get: 27.582
    chen_get: 1
    chf_get: 5.1
    chfault_get: There are no active chiller faults
    chfh_get: 5.3
    chfl_get: 4.7
    chflf_get: 4.2
    chp_get: 20.0
    chph_get: 35.0
    chpl_get: 3.0
    chserven_get: 1
    chservicehrsrem_get: 1296.253
    chservoperiod_get: 5.0
    chservstart_get: 1.0
    chsn_get: Not set
    chst_get: 28.0
    cht_get: 28.0
    chth_get: 33.0
    chtl_get: 12.0
    cpumt_get: 51.0
    cput_get: 51.0
    d1h_get: 809.508
    d1rc_get: 0.25
    d1sn_get: 
    d2h_get: 806.365
    d2rc_get: 0.5
    d2sn_get: 
    d3h_get: 712.996
    d3llen_get: 1
    d3rc_get: 8.4
    d3rcll_get: 0.0
    d3sn_get: NC7666
    daf_get: SYSTEM OK-
    datasheet_get: The datasheet is not installed
    dhcp_get: 1
    dns_get: Not set yet
    dsh_get: 809.507
    dsllen_get: 1
    dsrc_get: 0.078
    dssn_get: 
    echo_get: 0
    eg_get: 0
    em_get: 0
    en_get: 0
    ep_get: 0
    f_get: SYSTEM OK
    fh_get: SYSTEM OK
    fv_get: 7.154_50MHz.48
    gateway_get: Not set yet
    grr_get: 1000.0
    grren_get: 0
    gui_get: 3.82.104
    hb_get: 0
    hh_get: 5664.783
    hhl_get: 8.0
    hostname_get: 
    hsn_get: G0123251815
    hsv_get: 42.4.462
    hv_get: HD:AL, A1:2.0, FPGA:7.154_50MHz.48, MODULE: Colibri_T20_512MB
    ip_get: No network connections found, is the Ethernet cable connected?
    ipmax_get: 192.9.200.255
    ipmin_get: 192.9.200.1
    ire_get: -1
    irec_get: -1
    k_get: 0
    l_get: 0
    lip_get: Error, bad command
    lm_get: Monaco 1035-40-40
    lock_get: No commands are locked
    lockout_get: -1
    lookup_reprates_names_get: 200:5:'', 200:5:'PulseEQ', 250:4:'', 250:4:'PulseEQ', 330:3:'', 330:3:'PulseEQ', 500:2:'', 500:2:'PulseEQ', 1000:5:'', 1000:10:'', 1000:15:'', 1000:20:'', 1000:1:'', 1000:1:'PulseEQ', 2000:1:'', 4000:1:'', 10000:1:'', 50000:1:''
    lpssn_get: P1122249858
    mac_get: 00-1B-1C-04-F1-D2
    manual_get: FC626346 Monaco_IR_1297688_RevAE.pdf
    mrr_get: 0.0
    msc_get: 0
    msi_get: 0
    pc_get: 0
    pd3t_get: 56.017
    pd4opten_get: 0
    pdsv_get: 0.001
    penrgv_get: 4.636
    pep_get: 100.0
    period_get: -1.0
    pm_get: 2
    prompt_get: 1
    pscode_get: 0
    psid_get: 0
    pssn_get: Not set
    pw_get: -1
    pwfine_get: 0.0
    pws_get: 276.0
    ready_get: 0
    relh_get: 0.0
    relho_get: 0.0
    ren_get: 1
    rl_get: 29.0
    rr_get: 0.0
    rrd_get: 10
    s_get: 2533
    sc_get: 0
    sci_get: 0
    scoi_get: 0
    se_get: 2
    set_get: (1000.0, 276.0, 10, 1)
    sis_get: -1
    srr_get: 0.0
    ssi_get: 1
    ssn_get: Not set
    st_get: Standby
    subnet_get: Not set yet
    sv_get: HD:42.4.462, A1:91.0, IM:2.1, OS:7.0, CH:0.0, WEB:0.6.462, JSON:0.8.462, POST:0.030.8, UP:3.0.462
    sync1_get: 0
    sync2_get: 0
    time_get: 2023-12-28 13:33:23
    timezone_get: (UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna
    tstl_get: 0
    tstls_get: No crystal temperature servos are present
    usb_get: RNDIS
    w_get: SYSTEM OK
    wh_get: SYSTEM OK
    """


if __name__ == '__main__':
    main()
