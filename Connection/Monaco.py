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


from Connection.Telnet import TelnetConnection


def tryConvertToFloat(inp, fallback: float = -1) -> float:
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
        host: str,
        port: int,
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

    def readInit(self):
        """Reads initial """
        self.read(1024 * 16)
        self.parseRead()

    def parseRead(self, count: int = 1024) -> str:
        """Reads output and strips cursor for next input"""
        recv = self.read(count)
        if not recv.endswith(self.terminating_string):
            raise ConnectionError(f'Expected terminating {self.terminating_string.encode(self.encoding)} cursor, but received {recv.encode(self.encoding)}')
        return recv[:-len(self.terminating_string)]

    def _queryAndReturn(self, cmd: str) -> str:
        """Queries command and returns result"""
        self.write(cmd)
        return self.parseRead()

    def _queryAndReturnFloat(self, cmd: str) -> float:
        """Queries command and returns result as float. If float conversion fails, -1 will be returned."""
        return tryConvertToFloat(self._queryAndReturn(cmd))

    def _queryAndReturnInt(self, cmd: str) -> int:
        """Queries command and returns result as integer. If integer conversion fails, -1 will be returned."""
        return int(self._queryAndReturnFloat(cmd))

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Close Monaco connection"""
        self.close()
        super().__exit__(exception_type, exception_value, exception_traceback)

    def close(self):
        """Closes Monaco connection"""
        self.write('EXIT')

    def __enter__(self):
        """Enters Monaco connection"""
        return self.open()

    def open(self):
        """Enters Monaco connection"""
        super().open()
        self.readInit()
        return self

    def altmodGet(self) -> int:
        """Gets the pulse energy modulation mode"""
        return self._queryAndReturnInt(f'?ALTMOD')

    def altmodSet(self, mode: int | bool):
        """
        Sets the pulse energy modulation mode:
            n=0 sets control to Extended Interface pin 15
            n=1 sets control to EXT MOD mini BNC connector
        """
        self._queryAndReturn(f'ALTMOD={int(mode)}')

    def amp3hGet(self) -> float:
        """Returns the laser amplifier hours"""
        return self._queryAndReturnFloat('?AMP3H')

    def amp3snGet(self) -> str:
        """Returns the laser amplifier serial number"""
        return self._queryAndReturn('?AMP3SN')

    def autoipSet(self, mode: int | bool):
        """
        Sets Enable flag to scan for an available IP address:
            n = 0 disabled
            n = 1 enabled
        """
        self._queryAndReturn(f'AUTOIP={int(mode)}')

    def autoipGet(self) -> int:
        """Returns the AUTOIP function status"""
        return self._queryAndReturnInt('?AUTOIP')

    def batGet(self) -> float:
        """Returns battery voltage, nominal 3V"""
        return self._queryAndReturnFloat('?BAT')

    def boot(self):
        """Entering this command will reboot the firmware"""
        self._queryAndReturn('BOOT=1')

    def bpSet(self, burst: int):
        """Sets the number of pulses in a burst. Allowed range is 1 to 4,294,967,295 pulses."""
        self._queryAndReturn(f'BP={burst}')

    def bpGet(self) -> int:
        """Returns the number of pulses in a burst"""
        return self._queryAndReturnInt('?BP')

    def btGet(self) -> float:
        """Returns laser head baseplate measured temperature in °C"""
        return self._queryAndReturnFloat('?BT')

    def chenSet(self, mode: int | bool):
        """
        Set chiller enable:
            n = 0 turns off the chiller
            n = 1 turns on the chiller
        """
        self._queryAndReturn(f'CHEN={int(mode)}')

    def chenGet(self) -> int:
        """Returns status of chiller enable"""
        return self._queryAndReturnInt('?CHEN')

    def chfGet(self) -> float:
        """Returns chiller flow"""
        return self._queryAndReturnFloat('?CHF')

    # TODO: better faults
    def chfaultGet(self) -> str:
        """Returns chiller faults"""
        return self._queryAndReturn('?CHFAULT')

    def chfhGet(self) -> float:
        """Returns chiller high flow rate warning limit"""
        return self._queryAndReturnFloat('?CHFH')

    def chflGet(self) -> float:
        """Returns chiller low flow rate warning limit"""
        return self._queryAndReturnFloat('?CHFL')

    def chflfGet(self) -> float:
        """Returns chiller low flow rate fault limit"""
        return self._queryAndReturnFloat('?CHFLF')

    def chpGet(self) -> float:
        """Returns chiller pressure"""
        return self._queryAndReturnFloat('?CHP')

    def chphGet(self) -> float:
        """Returns chiller maximum pressure"""
        return self._queryAndReturnFloat('?CHPH')

    def chplGet(self) -> float:
        """Returns chiller minimum pressure"""
        return self._queryAndReturnFloat('?CHPL')

    def chservenGet(self) -> int:
        """Get chiller service warning enable"""
        return self._queryAndReturnInt('?CHSERVEN')

    def chservicedSet(self):
        """Will clear the chiller service warning, and resets the service start time"""
        self._queryAndReturn(f'CHSERVICED=1')

    def chservicehrsremGet(self) -> float:
        """Displays the remaining hours before chiller service is required."""
        return self._queryAndReturnFloat('?CHSERVICEHRSREM')

    def chservoperiodGet(self) -> float:
        """Returns light loop period"""
        return self._queryAndReturnFloat('?CHSERVOPERIOD')

    def chservstartGet(self) -> float:
        """Get start chiller service timer"""
        return self._queryAndReturnFloat('?CHSERVSTART')

    def chsnGet(self) -> str:
        """Returns chiller serial number"""
        return self._queryAndReturn('?CHSN')

    def chstGet(self) -> float:
        """Returns chiller set point"""
        return self._queryAndReturnFloat('?CHST')

    def chtGet(self) -> float:
        """Returns chiller temperature"""
        return self._queryAndReturnFloat('?CHT')

    def chthGet(self) -> float:
        """Returns chiller high temperature limit"""
        return self._queryAndReturnFloat('?CHTH')

    def chtlGet(self) -> float:
        """Returns chiller low temperature limit"""
        return self._queryAndReturnFloat('?CHTL')

    def cpumtGet(self) -> float:
        """Returns CPU package temperature"""
        return self._queryAndReturnFloat('?CPUMT')

    def cputGet(self) -> float:
        """Returns CPU chip temperature"""
        return self._queryAndReturnFloat('?CPUT')

    def crrGet(self) -> float:
        """Returns measured output repetition rate"""
        rrd = self.rrdGet()
        mmr = self.mrrGet()
        if rrd == 0 or mmr == 0:
            return 0
        if rrd == -1 or mmr == -1:
            return -1
        return mmr / rrd

    # TODO: better errors
    def dafGet(self) -> str:
        """Returns descriptions of active faults"""
        return self._queryAndReturn('?DAF')

    # TODO: better data get
    def dataGet(self, cmd: str) -> str:
        """Returns data from the datalogger"""
        return self._queryAndReturn(f'?DATA {cmd}')

    def datasheetGet(self) -> str:
        """Returns name of datasheet"""
        return self._queryAndReturn(f'?DATASHEET')

    def d1hGet(self) -> float:
        """Returns the number of operating hours on laser diode 1"""
        return self._queryAndReturnFloat('?D1H')

    def d1rcGet(self) -> float:
        """Returns the set maximum current of diode 1 in Amps"""
        return self._queryAndReturnFloat('?D1RC')

    def d1snGet(self) -> str:
        """Returns serial number of the diode 1"""
        return self._queryAndReturn('?D1SN')

    def d2hGet(self) -> float:
        """Returns the number of operating hours on laser diode 2"""
        return self._queryAndReturnFloat('?D2H')

    def d2rcGet(self) -> float:
        """Returns the set maximum current of diode 2 in Amps"""
        return self._queryAndReturnFloat('?D2RC')

    def d2snGet(self) -> str:
        """Returns serial number of the diode 2"""
        return self._queryAndReturn('?D2SN')

    def d3hGet(self) -> float:
        """Returns the number of operating hours on laser diode 3"""
        return self._queryAndReturnFloat('?D3H')

    def d3llenGet(self) -> int:
        """Returns the D3 light loop enable"""
        return self._queryAndReturnInt('?D3LLEN')

    def d3rcGet(self) -> float:
        """Returns the set maximum current of diode 3 in Amps"""
        return self._queryAndReturnFloat('?D3RC')

    def d3rcllGet(self) -> float:
        """Returns the D3 rated current before light loop"""
        return self._queryAndReturnFloat('?D3RCLL')

    def d3snGet(self) -> str:
        """Returns serial number of the diode 3"""
        return self._queryAndReturn('?D3SN')

    def dhcpSet(self, mode: int | bool):
        """
        Enables or disables the dynamic host configuration protocol (DHCP):
            n = 0 DHCP is disabled
            n = 1 DHCP is enabled
        """
        self._queryAndReturn(f'DHCP={int(mode)}')

    def dhcpGet(self) -> int:
        """Returns the status of DHCP"""
        return self._queryAndReturnInt('?DHCP')

    def dnsSet(self, dns: str):
        """Sets the DNS address when DHCP is disabled"""
        self._queryAndReturn(f'DNS={dns}')

    def dnsGet(self) -> str:
        """Returns the DNS server address"""
        return self._queryAndReturn('?DNS')

    def dshGet(self) -> float:
        """Returns the hours of DS"""
        return self._queryAndReturnFloat('?DSH')

    def dsllenGet(self) -> int:
        """Returns DS light loop enable"""
        return self._queryAndReturnInt('?DSLLEN')

    def dsrcGet(self) -> float:
        """Returns the DS rated current"""
        return self._queryAndReturnFloat('?DSRC')

    def dssnGet(self) -> str:
        """Returns the serial number for DS"""
        return self._queryAndReturn('?DSSN')

    def echoSet(self, mode: int | bool):
        """
        Turns the Characters transmitted to the laser (echoed) on or off
            n = 0 turns off echo
            n = 1 turns on echo
        """
        self._queryAndReturn(f'ECHO={int(mode)}')

    def echoGet(self) -> int:
        """Returns echo mode"""
        return self._queryAndReturnInt('?ECHO')

    def egSet(self, mode: int | bool):
        """
        Enable the external gate:
            n = 0 disables PulseEQ external gate (default)
            n = 1 turns on PulseEQ external gate
        """
        self._queryAndReturn(f'EG={int(mode)}')

    def egGet(self) -> int:
        """Returns the status of DHCP"""
        return self._queryAndReturnInt('?EG')

    def emSet(self, mode: int | bool):
        """Sets external modulation"""
        self._queryAndReturn(f'EM={int(mode)}')

    def emGet(self) -> int:
        """Returns external modulation status"""
        return self._queryAndReturnInt('?EM')

    def enSet(self, mode: int | bool):
        """Enable enhanced notifications"""
        self._queryAndReturn(f'EN={int(mode)}')

    def enGet(self) -> int:
        """Returns enhanced notifications status"""
        return self._queryAndReturnInt('?EN')

    def epSet(self, mode: int):
        """Enhanced serial protocol"""
        self._queryAndReturn(f'EP={mode}')

    def epGet(self) -> int:
        """Returns enhanced serial protocol"""
        return self._queryAndReturnInt('?EP')

    def exitSet(self):
        """Closes an Ethernet connection"""
        self._queryAndReturn('EXIT')

    # TODO: better faults
    def fGet(self) -> str:
        """
        Displays a list of faults, if present.
        Use ?FNAME command to show a description of a particular fault.
        If a fault is present, it will turn off the laser.
        """
        return self._queryAndReturn('?F')

    def fackSet(self):
        """Acknowledge faults and return the laser to a ready state if the fault condition is lifted"""
        self._queryAndReturn('FACK=1')

    # TODO: better faults
    def faultsGet(self) -> str:
        """Returns a list of numbered codes of all active faults. separated by an &, or returns “System OK” if no active faults"""
        return self._queryAndReturn('?FAULTS')

    # TODO: better faults
    def fhGet(self) -> str:
        """
        Returns the fault history with index numbers delimited by “&” sign with no spaces.
        Faults are recorded in chronological order since last AC power up or last FHC command.
        Fault history is limited to the last 20 faults.
        """
        return self._queryAndReturn('?FH')

    def fhcSet(self):
        """Clears the fault history"""
        self._queryAndReturn('FHC')

    def fnameGet(self, code: int) -> str:
        """Returns the description of fault code or warning code nn"""
        return self._queryAndReturn(f'?FNAME:{code}')

    def fvGet(self) -> str:
        """Returns the version number of the FPGA firmware of the laser"""
        return self._queryAndReturn('?FV')

    def gatewaySet(self, gateway: str):
        """Set the gateway when DHCP is disabled"""
        self._queryAndReturn(f'GATEWAY={gateway}')

    def gatewayGet(self) -> str:
        """Returns the Ethernet gateway"""
        return self._queryAndReturn('?GATEWAY')

    def grrSet(self, rate: float):
        """Sets the PulseEQ internal repetition rate to {rate}kHz"""
        self._queryAndReturn(f'GRR={rate}')

    def grrGet(self) -> float:
        """Returns the Ethernet gateway"""
        return self._queryAndReturnFloat('?GRR')

    def grrenSet(self, mode: int | bool):
        """
        Enables the internal repetition rate gate:
            n = 0 disables PulseEQ Internal triggering
            n = 1 enables PulseEQ Internal triggering
        """
        self._queryAndReturn(f'GRREN={int(mode)}')

    def grrenGet(self) -> int:
        """Returns the status of the internal repetition rate gate"""
        return self._queryAndReturnInt('?GRREN')

    def guiGet(self) -> str:
        """Returns the status of the internal repetition rate gate"""
        return self._queryAndReturn('?GUI')

    def hbSet(self, time: int):
        """Sets the heartbeat timeout in secs, 0 or 5-300 (0=disabled)"""
        self._queryAndReturn(f'HB={time}')

    def hbGet(self) -> int:
        """Returns the heartbeat timeout in seconds (0=disabled)"""
        return self._queryAndReturnInt('?HB')

    # TODO: better help
    def helpGet(self, search: str = '') -> str:
        """Query commands, with optional filter"""
        cmd = '?HELP'
        if search:
            cmd += f' {search}'
        return self._queryAndReturn(cmd)

    def hhGet(self) -> float:
        """Returns the number of operating hours on the system head"""
        return self._queryAndReturnFloat('?HH')

    def hhlGet(self) -> float:
        """Returns the laser head humidity warning limit"""
        return self._queryAndReturnFloat('?HHL')

    def hostnameSet(self, hostname: str):
        """Sets host name for Ethernet connection"""
        self._queryAndReturn(f'HOSTNAME={hostname}')

    def hostnameGet(self) -> str:
        """Returns host name of Ethernet connection"""
        return self._queryAndReturn('?HOSTNAME')

    def hsnGet(self) -> str:
        """Returns serial number of the laser head"""
        return self._queryAndReturn('?HSN')

    def hsvGet(self) -> str:
        """Returns firmware version of the laser head as HEAD rev x.xx, date"""
        return self._queryAndReturn('?HSV')

    def hvGet(self) -> str:
        """Displays the internal revision level of major hardware components"""
        return self._queryAndReturn('?HV')

    def ipSet(self, ip: str):
        """Sets the static IP address"""
        self._queryAndReturn(f'IP={ip}')

    def ipGet(self) -> str:
        """Returns the IP address for Ethernet"""
        return self._queryAndReturn('?IP')

    def ipmaxSet(self, ip: str):
        """Sets end of range for AutoIP scan"""
        self._queryAndReturn(f'IPMAX={ip}')

    def ipmaxGet(self) -> str:
        """Returns end of range for AutoIP scan"""
        return self._queryAndReturn('?IPMAX')

    def ipminSet(self, ip: str):
        """Sets start of range for AutoIP scan"""
        self._queryAndReturn(f'IPMIN={ip}')

    def ipminGet(self) -> str:
        """Returns start of range for AutoIP scan"""
        return self._queryAndReturn('?IPMIN')

    def ireGet(self) -> float:
        """Returns the IR energy"""
        return self._queryAndReturnFloat('?IRE')

    def irecGet(self) -> int:
        """Returns the IR count"""
        return self._queryAndReturnInt('?IREC')

    def irep1Set(self, value: float):
        """Sets the IR point 1 calibration"""
        self._queryAndReturn(f'IREP1={value}')

    def irep2Set(self, value: float):
        """Sets the IR point 2 calibration"""
        self._queryAndReturn(f'IREP2={value}')

    def kGet(self) -> int:
        """
        Returns laser enable keyswitch state:
            0 = laser in Standby (laser diodes cannot be turned on)
            1 = laser enabled
        """
        return self._queryAndReturnInt('?K')

    def lSet(self, state: int | bool):
        """
        Sets the laser state:
            0 = turns off laser
            1 = turns on laser
        """
        self._queryAndReturn(f'L={int(state)}')

    def lGet(self) -> int:
        """
        Returns laser state:
            0 = if the laser is in STANDBY, key-switch is off
            1 = a fault is active and the system has been shut down
            2 = if the laser is READY, key-switch is on but the diodes are off
            3-"22" = starting: 3: 0%, 22: 100%; but 22 is not in range anymore
            22 = waiting for baseplate temperature
            24 = if the laser is ON, all the diodes are on and the laser is ready to produce output pulses
            27-30 = stopping
        """
        return self._queryAndReturnInt('?L')

    def lGetInfo(self) -> tuple[str, bool, int]:
        """
        Returns laser state info

        :return: tuple(
            description: str,
            state: bool,
            laser state id: int
        )
        """

        l_state = self.lGet()

        l_states = {
            0: ('Standby', False),
            1: ('Error', False),
            2: ('Ready', False),
            22: ('Waiting for Baseplate Temperature', True),
            24: ('On', True),
        }

        if 3 <= l_state < 22:
            return f'Starting ({round((l_state - 3) / 19 * 100)}%)', True, l_state

        if 26 <= l_state <= 30:
            return f'Stopping ({(l_state - 26) * 20 + 10}%)', True, l_state

        ret_state = l_states.get(l_state, ('Not defined', True))
        return ret_state[0], ret_state[1], l_state

    # TODO: return ip in tuple of 4 ints instead of string -> external function
    def lipGet(self) -> str:
        """Returns last used static IP address"""
        return self._queryAndReturn('?LIP')

    def lmGet(self) -> str:
        """Returns the laser model"""
        return self._queryAndReturn('?LM')

    def lnameGet(self, state: int) -> str:
        """Returns name of the specified laser state"""
        return self._queryAndReturn(f'?LNAME={state}')

    def lockGet(self) -> str:
        """Returns locked commands"""
        return self._queryAndReturn('?LOCK')

    def lockoutSet(self, mode: int | bool):
        """
        Sets laser LOCKOUT control state (only one connection can have exclusive control of laser at any given time):
            n = 0 unlocks laser to release control to other remote control device. The next remote device issuing a command will have exclusive
                  control, which sets LOCKOUT=1 for that device.
            n = 1 locks out other remote devices from controlling laser; only current control device has exclusive control of laser (default)
        """
        self._queryAndReturn(f'LOCKOUT={int(mode)}')

    def lockoutGet(self) -> int:
        """
        Returns LOCKOUT state of laser control:
            0 = laser is unlocked from current connection for control by another remote control device or connection.
            1 = laser remote control is locked out: only current connection has exclusive control of the laser
            x = a connection from device X has exclusive control of the laser
        """
        return self._queryAndReturnInt('?LOCKOUT')

    # TODO: better implementation
    def lookupRepratesNamesGet(self) -> str:
        """
        Returns a list of the laser repetition rates/seeder burst lengths that are available in the format:
        {reprate in kHz}:{seeder burst length}
        """
        return self._queryAndReturn('?LOOKUP REPRATES NAMES')

    def lpssnGet(self) -> str:
        """Returns low power stage serial number"""
        return self._queryAndReturn('?LPSSN')

    def macGet(self) -> str:
        """Returns the MAC address of the Ethernet interface"""
        return self._queryAndReturn('?MAC')

    def manualGet(self) -> str:
        """Returns the operator's manual filename"""
        return self._queryAndReturn('?MANUAL')

    def mrrGet(self) -> float:
        """Returns the laser amplifier repetition rate (in kHz)"""
        return self._queryAndReturnFloat('?MRR')

    def mscGet(self) -> int:
        """Get machine safe shutter count"""
        return self._queryAndReturnInt('?MSC')

    def msiGet(self) -> int:
        """Get machine safe shutter installed"""
        return self._queryAndReturnInt('?MSI')

    # TODO: better output
    def newGet(self) -> str:
        """Returns every parameter that has changed"""
        return self._queryAndReturn('?NEW')

    def passwordSet(self, password: str):
        """Sets up or changes the user password"""
        self._queryAndReturn(f'PASSWORD={password}')

    def pcSet(self, mode: int | bool):
        """
        Sets pulse control:
            n = 0 is pulse control off
            n = 1 is pulse control on
        """
        self._queryAndReturn(f'PC={int(mode)}')

    def pcGet(self) -> int:
        """Returns the status of pulse control"""
        return self._queryAndReturnInt('?PC')

    def pd3tGet(self) -> float:
        """Returns the status of pulse control"""
        return self._queryAndReturnFloat('?PD3T')

    def pd4optenGet(self) -> int:
        """
        Returns PD4 optimization enable status:
            0 = PD4 optimization off
            1 = PD4 optimization on
        """
        return self._queryAndReturnInt('?PD4OPTEN')

    def pdsvGet(self) -> float:
        """Returns seed photodiode voltage"""
        return self._queryAndReturnFloat('?PDSV')

    def penrgvGet(self) -> float:
        """Returns the external pulse energy control voltage"""
        return self._queryAndReturnFloat('?PENRGV')

    def pepSet(self, percentage: float):
        """Sets the output pulse energy as percentage of maximum, 0 to 100"""
        self._queryAndReturn(f'PEP={percentage}')

    def pepGet(self) -> float:
        """Returns the current pulse energy percentage"""
        return self._queryAndReturnFloat('?PEP')

    def periodSet(self, period: float):
        """Set how often to report new data"""
        self._queryAndReturn(f'PERIOD={period}')

    def periodGet(self) -> float:
        """Return how often to report new data"""
        return self._queryAndReturnFloat('?PERIOD')

    def pmSet(self, mode: int):
        """
        Sets the pulse mode:
            n = 0 for Continuous pulsing
            n = 1 for Gated mode
            n = 2 for Divided mode
            n = 3 for Divided and Gated mode
            n = 4 for Burst mode
            n = 5 for Burst and Divided mode
        """
        self._queryAndReturn(f'PM={mode}')

    def pmGet(self) -> int:
        """Returns the pulse mode"""
        return self._queryAndReturnInt('?PM')

    def promptSet(self, mode: int | bool):
        """
        Sets the mode of prompt:
            n = 0 turns off “Monaco Laser >” prompt
            n = 1 turns on “Monaco Laser >” prompt
        """
        self._queryAndReturn(f'PROMPT={int(mode)}')

    def promptGet(self) -> int:
        """Return the mode of prompt"""
        return self._queryAndReturnInt('?PROMPT')

    def pscodeGet(self) -> int:
        """Return the power supply family code"""
        return self._queryAndReturnInt('?PSCODE')

    def psidGet(self) -> int:
        """Return the power supply ID"""
        return self._queryAndReturnInt('?PSID')

    def pssnGet(self) -> str:
        """Returns the power supply serial number"""
        return self._queryAndReturn('?PSSN')

    def pwSet(self, width: float):
        """Sets the pulse width in femtoseconds"""
        self._queryAndReturn(f'PW={width}')

    def pwGet(self) -> float:
        """Return the pulse width in femtoseconds"""
        return self._queryAndReturnFloat('?PW')

    def pwfineSet(self, tuning: float):
        """
        Sets the pulse width fine tuning in %, range of -100 to 100.
        This works in conjunction with the Peak Power Optimizer.
        """
        self._queryAndReturn(f'PWFINE={tuning}')

    def pwfineGet(self) -> float:
        """Returns the pulse width fine tuning in %"""
        return self._queryAndReturnFloat('?PWFINE')

    def pwsGet(self) -> float:
        """Returns the pulse width set point"""
        return self._queryAndReturnFloat('?PWS')

    def quitSet(self):
        """Closes an Ethernet connection"""
        self._queryAndReturn('QUIT')

    def readyGet(self) -> int:
        """Returns laser ready status"""
        return self._queryAndReturnInt('?READY')

    def relhGet(self) -> float:
        """Returns the relative humidity"""
        return self._queryAndReturnFloat('?RELH')

    def relhoGet(self) -> float:
        """Returns the relative humidity offset"""
        return self._queryAndReturnFloat('?RELHO')

    def renSet(self, mode: int | bool):
        """
        Enables or disables the air recirculator inside the laser head:
            n = 0 disables the recirculator
            n = 1 enables the recirculator
        """
        self._queryAndReturn(f'REN={int(mode)}')

    def renGet(self) -> int:
        """Returns recirculator control status"""
        return self._queryAndReturnInt('?REN')

    def rlSet(self, percentage: float):
        """Sets the Output AOM voltage as percentage of maximum, from 0 to 100"""
        self._queryAndReturn(f'RL={percentage}')

    def rlGet(self) -> float:
        """Returns the Output AOM voltage as percentage of maximum"""
        return self._queryAndReturnFloat('?RL')

    def rrGet(self) -> float:
        """Returns the laser pulse or seeder burst output repetition rate in Hz"""
        return self._queryAndReturnFloat('?RR')

    def rrdSet(self, divisor: int):
        """Allows the amplifier laser pulse repetition rate to be divided by an integer"""
        self._queryAndReturn(f'RRD={divisor}')

    def rrdGet(self) -> int:
        """Returns the laser pulse repetition rate divisor"""
        return self._queryAndReturnInt('?RRD')

    def sSet(self, mode: int | bool):
        """
        Sets the shutter state:
            n = 0 closes external shutter
            n = 1 opens external shutter
        """
        self._queryAndReturn(f'S={int(mode)}')

    def sGet(self) -> int:
        """Returns the shutter state"""
        return self._queryAndReturnInt('?S')

    def scGet(self) -> int:
        """Returns the shutter cycle counter value"""
        return self._queryAndReturnInt('?SC')

    def sciSet(self, mode: int | bool):
        """
        Shutter control inversion:
            n = 0 disables inversion (default)
            n = 1 enables inversion
        """
        self._queryAndReturn(f'SCI={int(mode)}')

    def sciGet(self) -> int:
        """Returns inversion of shutter control input value"""
        return self._queryAndReturnInt('?SCI')

    def scoiSet(self, mode: int | bool):
        """
        Shutter control output inversion:
            n = 0 disables output inversion (default)
            n = 1 enables output inversion
        """
        self._queryAndReturn(f'SCOI={int(mode)}')

    def scoiGet(self) -> int:
        """Returns inversion of shutter control output inversion"""
        return self._queryAndReturnInt('?SCOI')

    def seGet(self) -> int:
        """
        Returns the shutter control (pin 17) state:
            0 = pin 17 at GND and S = 0 (both are off)
            1 = pin 17 at GND and S = 1
            2 = pin 17 is high and S = 0
            3 = pin 17 is high and S = 1 (both are on)
        """
        return self._queryAndReturnInt('?SE')

    # TODO: better output
    def sessionsGet(self) -> str:
        """Lists the active connections"""
        return self._queryAndReturn('?SESSIONS')

    def setSet(
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

        self._queryAndReturn(cmd)

    # TODO: better output variables
    def setGet(self) -> tuple[float, float, int, int]:
        """
        Returns the current values for the laser parameters:
            MRR: amplifier repetition rate in kHz
            PW: pulse width in femtoseconds
            RRD: repetition rate divisor
            SB: number of seeder bursts
        """
        query = self._queryAndReturn('?SET').split(',')
        query.extend(['0'] * (4 - len(query)))
        return (
            tryConvertToFloat(query[0]),
            tryConvertToFloat(query[1]),
            int(tryConvertToFloat(query[2])),
            int(tryConvertToFloat(query[3]))
        )

    def sisGet(self) -> int:
        """
        Returns the status of the shutter interlock sense:
            0 = shutter interlock closed
            1 = shutter interlock open
        """
        return self._queryAndReturnInt('?SIS')

    def srrGet(self) -> float:
        """Returns the seed laser pulse repetition rate"""
        return self._queryAndReturnFloat('?SRR')

    def ssiGet(self) -> int:
        """
        Returns the status of the shutter installation:
            0 = Shutter not installed
            1 = Shutter installed
        """
        return self._queryAndReturnInt('?SSI')

    def ssnGet(self) -> str:
        """Get Seed serial number"""
        return self._queryAndReturn('?SSN')

    def sspSet(self, position: str):
        """Sets the SESAM spot position"""
        self._queryAndReturn(f'SSP={position}')

    def sspGet(self) -> int:
        """Returns current SESAM spot position"""
        return self._queryAndReturnInt('?SSP')

    def sspcGet(self) -> int:
        """Returns the SESAM spot transition count"""
        return self._queryAndReturnInt('?SSPC')

    def ssphGet(self) -> float:
        """Returns current SESAM spot hours"""
        return self._queryAndReturnFloat('?SSPH')

    def sspsGet(self) -> int:
        """Returns SESAM spot status"""
        return self._queryAndReturnInt('?SSPS')

    def stGet(self) -> str:
        """Returns the name of the current laser state"""
        return self._queryAndReturn('?ST')

    def subnetSet(self, subnet: str):
        """Sets the subnet when DHCP is disabled"""
        self._queryAndReturn(f'SUBNET={subnet}')

    def subnetGet(self) -> str:
        """Returns the Ethernet subnet"""
        return self._queryAndReturn('?SUBNET')

    def svGet(self) -> str:
        """Displays the revision level of major software components"""
        return self._queryAndReturn('?SV')

    def sync1Set(self, mode: int | bool):
        """
        Sets the output from the Sync 1 HD-BNC connector on the back of the laser head:
            n = 0 provides a representation of the drive signal for AOM1
                  (if shutter closed/pulsing off then output is the amplifier rep rate)
            n = 1 provides a representation of the seeder pulses
        """
        self._queryAndReturn(f'SYNC1={int(mode)}')

    def sync1Get(self) -> int:
        """Returns the output setting from the Sync 1 HD-BNC connector"""
        return self._queryAndReturnInt('?SYNC1')

    def sync2Set(self, mode: int | bool):
        """
        Sets the output from the Sync 2 HD-BNC connector on the back of the laser head:
            n = 0 provides a representation of the drive signal for AOM2
                  (if shutter closed/pulsing off then output is the amplifier rep rate)
            n = 1 provides a representation of the seeder pulses
        """
        self._queryAndReturn(f'SYNC2={int(mode)}')

    def sync2Get(self) -> int:
        """Returns the output setting from the Sync 2 HD-BNC connector"""
        return self._queryAndReturnInt('?SYNC2')

    def timeSet(self, date_time: datetime | None):
        """Sets local time on the laser clock. If left empty the current time will be used."""
        if date_time is None:
            date_time = datetime.now()
        self._queryAndReturn(f'TIME={date_time.strftime("%Y-%m-%d %H:%M")}')

    def timeGet(self) -> datetime:
        """Returns local time on the laser clock"""
        query = self._queryAndReturn('?TIME')
        try:
            return datetime.strptime(query, '%Y-%m-%d %H:%M.%S')
        except ValueError:
            return datetime(1, 1, 1)

    def timezoneSet(self, timezone: str):
        """Sets local time zone on the laser clock"""
        self._queryAndReturn(f'TIMEZONE={timezone}')

    def timezoneGet(self) -> str:
        """Returns local time zone on the laser clock"""
        return self._queryAndReturn('?TIMEZONE')

    # TODO: better returning
    def timezonesGet(self) -> str:
        """Returns available time zones for this laser"""
        return self._queryAndReturn('?TIMEZONES')

    def tstlGet(self) -> int:
        """Checks if all temperature servos are tight locked"""
        return self._queryAndReturnInt('?TSTL')

    def tstlsGet(self) -> str:
        """Returns the temperature servos tight locked status"""
        return self._queryAndReturn('?TSTLS')

    def usbSet(self, connection: str):
        """Set the mode for the USB connection"""
        self._queryAndReturn(f'USB={connection}')

    def usbGet(self) -> str:
        """Returns the USB connection mode"""
        return self._queryAndReturn('?USB')

    def wGet(self) -> list[int]:
        """Displays a list of warning ids"""
        res = self._queryAndReturn('?W')
        ret = []
        try:
            ret = [int(s) for s in res.split(',')]
        except ValueError:
            pass
        return ret

    def wGetInfo(self) -> dict[int, tuple[str, str]]:
        """Displays a list of warning ids and their type and description"""
        ret = {}
        for w in self.wGet():
            res = []
            try:
                res = self.fnameGet(w).split(':')
            except ConnectionError:
                pass

            if len(res) < 2:
                res = ['', '']
            ret[w] = (res[0].strip(), str(':'.join(res[1:]).strip()))
        return ret

    # TODO: better output
    def whGet(self) -> str:
        """Displays the warning history"""
        return self._queryAndReturn('?WH')

    def whcSet(self):
        """Clears the warning history"""
        self._queryAndReturn('WHC')

    def wnameGet(self, code: int) -> str:
        """Returns the description of a warning code"""
        return self._queryAndReturn(f'?WNAME={code}')

    def identification(self) -> str:
        """Get the laser identification"""
        return f'{self.lmGet()} with S/N {self.hsnGet()}'


def main():
    with MonacoConnection(host='169.254.21.151', port=23) as monaco:
        print('***** GENERAL VALUES *****')
        print(f'{monaco.identification() = }')
        print(f'\n')

        print('***** READ VALUES *****')
        print(f'keyswitch: {monaco.kGet() = }')
        print(f'shutter: {monaco.sGet() = }')
        print(f'pulse control: {monaco.pcGet() = }')
        print(f'system status: {monaco.readyGet() = }')
        print(f'laser status: {monaco.lGet() = }')
        print(f'chiller temperature: {monaco.chtGet() = }')
        print(f'chiller set point: {monaco.chstGet() = }')
        print(f'baseplate temperature: {monaco.btGet() = }')
        print(f'chiller flow: {monaco.chfGet() = }')
        print(f'faults: {monaco.fGet() = }')
        print(f'fault list: {monaco.dafGet() = }')
        print(f'chiller faults: {monaco.chfaultGet() = }')
        print(f'warnings: {monaco.wGet() = }')
        for warning in monaco.wGet():
            print(f'warning #{warning}: {monaco.fnameGet(warning)}')
        print(f'warnings: {monaco.wGetInfo() = }')
        print(f'warnings history: {monaco.whGet() = }')
        print(f'Rep Rate: {monaco.mrrGet() = }')
        print(f'stats: {monaco.setGet() = }')
        print(f'RF level: {monaco.rlGet() = }')
        print('\n')

        monaco.sSet(0)
        monaco.pcSet(0)
        monaco.fackSet()
        monaco.lSet(1)


def toggleLaserAndReadStatus():
    from time import sleep

    with MonacoConnection(host='169.254.21.151', port=23) as monaco:
        _, state, _ = monaco.lGetInfo()
        monaco.lSet(not state)

        l_id_old = -1
        while True:
            desc, l_state, l_id = monaco.lGetInfo()
            if l_id != l_id_old:
                l_id_old = l_id
                print(f'#{l_id}: {desc}, {l_state}')
            sleep(0.1)


def readOutValues():
    with MonacoConnection(host='169.254.21.151', port=23) as monaco:
        for func in dir(monaco):
            if not func.endswith('Get'):
                continue
            if func in ['faultsGet', 'helpGet', 'newGet', 'sessionsGet', 'timezonesGet']:
                continue

            try:
                print(f'{func}: {getattr(monaco, func)()}')
            except (TypeError, ConnectionError):
                pass

    """
    altmodGet: 1
    amp3hGet: 712.996
    amp3snGet: K0073943
    autoipGet: 1
    batGet: 3.045
    bpGet: 1
    btGet: 27.582
    chenGet: 1
    chfGet: 5.1
    chfaultGet: There are no active chiller faults
    chfhGet: 5.3
    chflGet: 4.7
    chflfGet: 4.2
    chpGet: 20.0
    chphGet: 35.0
    chplGet: 3.0
    chservenGet: 1
    chservicehrsremGet: 1296.253
    chservoperiodGet: 5.0
    chservstartGet: 1.0
    chsnGet: Not set
    chstGet: 28.0
    chtGet: 28.0
    chthGet: 33.0
    chtlGet: 12.0
    cpumtGet: 51.0
    cputGet: 51.0
    d1hGet: 809.508
    d1rcGet: 0.25
    d1snGet: 
    d2hGet: 806.365
    d2rcGet: 0.5
    d2snGet: 
    d3hGet: 712.996
    d3llenGet: 1
    d3rcGet: 8.4
    d3rcllGet: 0.0
    d3snGet: NC7666
    dafGet: SYSTEM OK-
    datasheetGet: The datasheet is not installed
    dhcpGet: 1
    dnsGet: Not set yet
    dshGet: 809.507
    dsllenGet: 1
    dsrcGet: 0.078
    dssnGet: 
    echoGet: 0
    egGet: 0
    emGet: 0
    enGet: 0
    epGet: 0
    fGet: SYSTEM OK
    fhGet: SYSTEM OK
    fvGet: 7.154_50MHz.48
    gatewayGet: Not set yet
    grrGet: 1000.0
    grrenGet: 0
    guiGet: 3.82.104
    hbGet: 0
    hhGet: 5664.783
    hhlGet: 8.0
    hostnameGet: 
    hsnGet: G0123251815
    hsvGet: 42.4.462
    hvGet: HD:AL, A1:2.0, FPGA:7.154_50MHz.48, MODULE: Colibri_T20_512MB
    ipGet: No network connections found, is the Ethernet cable connected?
    ipmaxGet: 192.9.200.255
    ipminGet: 192.9.200.1
    ireGet: -1
    irecGet: -1
    kGet: 0
    lGet: 0
    lipGet: Error, bad command
    lmGet: Monaco 1035-40-40
    lockGet: No commands are locked
    lockoutGet: -1
    lookup_reprates_namesGet: 200:5:'', 200:5:'PulseEQ', 250:4:'', 250:4:'PulseEQ', 330:3:'', 330:3:'PulseEQ', 500:2:'', 500:2:'PulseEQ', 1000:5:'', 1000:10:'', 1000:15:'', 1000:20:'', 1000:1:'', 1000:1:'PulseEQ', 2000:1:'', 4000:1:'', 10000:1:'', 50000:1:''
    lpssnGet: P1122249858
    macGet: 00-1B-1C-04-F1-D2
    manualGet: FC626346 Monaco_IR_1297688_RevAE.pdf
    mrrGet: 0.0
    mscGet: 0
    msiGet: 0
    pcGet: 0
    pd3tGet: 56.017
    pd4optenGet: 0
    pdsvGet: 0.001
    penrgvGet: 4.636
    pepGet: 100.0
    periodGet: -1.0
    pmGet: 2
    promptGet: 1
    pscodeGet: 0
    psidGet: 0
    pssnGet: Not set
    pwGet: -1
    pwfineGet: 0.0
    pwsGet: 276.0
    readyGet: 0
    relhGet: 0.0
    relhoGet: 0.0
    renGet: 1
    rlGet: 29.0
    rrGet: 0.0
    rrdGet: 10
    sGet: 2533
    scGet: 0
    sciGet: 0
    scoiGet: 0
    seGet: 2
    setGet: (1000.0, 276.0, 10, 1)
    sisGet: -1
    srrGet: 0.0
    ssiGet: 1
    ssnGet: Not set
    stGet: Standby
    subnetGet: Not set yet
    svGet: HD:42.4.462, A1:91.0, IM:2.1, OS:7.0, CH:0.0, WEB:0.6.462, JSON:0.8.462, POST:0.030.8, UP:3.0.462
    sync1Get: 0
    sync2Get: 0
    timeGet: 2023-12-28 13:33:23
    timezoneGet: (UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna
    tstlGet: 0
    tstlsGet: No crystal temperature servos are present
    usbGet: RNDIS
    wGet: SYSTEM OK
    whGet: SYSTEM OK
    """


if __name__ == '__main__':
    toggleLaserAndReadStatus()
