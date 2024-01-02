import logging


import serial.tools.list_ports as list_ports
from serial import Serial


def get_comports() -> list[tuple[str, str, str]]:
    """Returns list of comports as tuple of (name, description, hardware id)"""
    return sorted(list_ports.comports())


def print_comports():
    """Prints all available com ports"""

    ports = get_comports()

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
    """

    def __init__(
        self,
        comport: str,
        timeout: float = 0.05,
        encoding: str = 'utf-8',
        baudrate: int = 9600,
        echo: bool = True,
        cleaning: bool = True
    ):
        self.comport = comport
        self.timeout = timeout
        self.encoding = encoding
        self.baudrate = baudrate
        self.echo = echo
        self.cleaning = cleaning

    def __enter__(self):
        """Enter serial connection and clean possible outputs"""
        self.serial = Serial(self.comport, baudrate=self.baudrate, timeout=self.timeout)
        self.clean()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Clean possible outputs and close connection"""
        self.clean()
        self.serial.close()

    def clean(self):
        """Clean connection"""
        if not self.cleaning:
            return

        while True:
            if not self.serial.readline():
                break

    def write(self, cmd: str):
        """Write command string to connection"""
        if not cmd.endswith('\r\n'):
            cmd += '\r\n'
        self.serial.write(cmd.encode(self.encoding))
        logging.info(f'Command {cmd} was written to port {self.comport}')

        # if echo is not on
        if not self.echo:
            return

        # if echo is on
        echocmd = self.readline()
        if echocmd != cmd:
            raise ConnectionError(f'Sent command does not match echo command: "{cmd}" was sent and "{echocmd}" was received')

    def readline(self) -> str:
        """Reads output line"""
        return self.serial.readline().decode(self.encoding)

    def read(self, count: int = 1024) -> str:
        """Read defined length of output bytes"""
        return self.serial.read(count).decode(self.encoding)


def main():
    with COMConnection('COM4') as com:
        com.write('*IDN?')
        print(com.readline().strip())


if __name__ == '__main__':
    main()
