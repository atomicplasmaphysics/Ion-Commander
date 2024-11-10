import serial.tools.list_ports as list_ports
from serial import Serial
from time import sleep


from Config.GlobalConf import GlobalConf

from Connection.VirtualDevice import VirtualSerial


def getComports(not_available_entry: bool = False) -> list[tuple[str, str, str]]:
    """
    Returns list of comports as tuple of (port, description, hardware id)

    :parm not_available_entry: add a not-available entry if there are no comports available
    """

    comports = [(port, description, hardware_id) for port, description, hardware_id in sorted(list_ports.comports())]
    if not comports and not_available_entry:
        comports = [('None', 'There is no comport available', '')]

    return comports


def printComports():
    """Prints all available com ports"""

    ports = getComports()

    print('List of COM Ports:')
    if not ports:
        print('  NO COM PORTS AVAILABLE')
        return

    print('  PORT: DESCRIPTION [HARDWARE ID]')
    for port, description, hardware_id in ports:
        print(f'  {port}: {description} [{hardware_id}]')


class COMConnection:
    """
    Context manager for Serial connection

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param baudrate: Baudrate
    :param echo: If device has echo. Will be checked
    :param cleaning: If output cache should be cleared when entering and exiting
    :param tx_term: transmission terminator characters (e.g.: '\r', '\n', '\r\n')
    :param auto_tx_term: If automatic the tx_term characters will be automatically inserted
    :param init_sleep: time for waiting on connection
    :param debug: If debug is enabled
    """

    def __init__(
        self,
        comport: str,
        timeout: float = 0.05,
        encoding: str = 'utf-8',
        baudrate: int = 9600,
        echo: bool = True,
        cleaning: bool = True,
        tx_term = '\r\n',
        auto_tx_term: bool = True,
        init_sleep: int = 0,
        debug: bool = False
    ):
        self.comport = comport
        self.timeout = timeout
        self.encoding = encoding
        self.baudrate = baudrate
        self.echo = echo
        self.cleaning = cleaning
        self.tx_term = tx_term
        self.auto_tx_term = auto_tx_term
        self.init_sleep = init_sleep
        self.debug = debug

        self.serial: Serial | None = None

    def __enter__(self):
        """Enter serial connection and clean possible outputs"""
        return self.open()

    def open(self):
        """Opens the connection"""
        if self.serial is None:
            if self.comport != 'virtual':
                self.serial = Serial(self.comport, baudrate=self.baudrate, timeout=self.timeout)
            else:
                self.serial = VirtualSerial()

        sleep(self.init_sleep)

        self.clean()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Clean possible outputs and close connection"""
        self.close()

    def close(self):
        """Closes the connection"""
        if self.serial is None:
            return
        self.clean()
        self.serial.close()
        self.serial = None

    def clean(self):
        """Clean connection"""
        if not self.cleaning:
            return

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        while True:
            if not self.serial.readline():
                break

    def write(self, cmd: str):
        """
        Write command string to connection

        :param cmd: instruction command
        """

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        if self.auto_tx_term and not cmd.endswith(self.tx_term):
            cmd += self.tx_term

        cmd_encode = cmd.encode(self.encoding)
        self.writeBytes(cmd_encode)

        # if echo is not on
        if not self.echo:
            return

        # if echo is on
        echo_cmd = self.readline()
        if echo_cmd != cmd:
            self.clean()
            raise ConnectionError(f'Sent command does not match echo command: {cmd!r} was sent and {echo_cmd!r} was received on port "{self.comport}"')

    def writeBytes(self, cmd: bytes):
        """
        Writes command in bytes to connection

        :param cmd: instruction command
        """

        self.serial.write(cmd)
        if self.debug:
            GlobalConf.logger.debug(f'Command {cmd} was written to port "{self.comport}"')

    def readline(self) -> str:
        """Reads output line"""

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        return self.serial.readline().decode(self.encoding)

    def read(self, count: int = 1024) -> str:
        """
        Read defined length of output bytes

        :param count: bytes to read
        """

        if self.serial is None:
            raise ConnectionError('Connection has not been established')

        return self.serial.read(count).decode(self.encoding)


def main():
    for comport in getComports():
        print(comport)

    with COMConnection('virtual', echo=False, cleaning=False) as com:
        com.write('*IDN?')
        print(com.readline())


if __name__ == '__main__':
    main()
