import socket


from Config.GlobalConf import GlobalConf

from Connection.VirtualDevice import VirtualSocket


class TelnetConnection:
    """
    Context manager for Telnet connection

    :param host: name of host
    :param port: port of host
    :param timeout: Timeout [in s]
    :param encoding: Encoding type
    :param debug: If debug is enabled
    """

    def __init__(
        self,
        host: str,
        port: int = 23,
        timeout: float = 5,
        encoding: str = 'utf-8',
        debug: bool = False
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.encoding = encoding
        self.debug = debug

        self.socket: socket.socket | None = None

    def __enter__(self):
        """Enter telnet socket connection"""
        return self.open()

    def open(self):
        """Enter telnet socket connection"""
        if self.socket is None:
            if self.host != 'virtual':
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self.socket.connect((self.host, self.port))
            else:
                self.socket = VirtualSocket()

        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Close telnet connection"""
        self.close()

    def close(self):
        """Closes telnet connection"""

        if self.socket is None:
            raise ConnectionError('Connection has not been established')

        self.socket.close()
        self.socket = None

    def write(self, cmd: str):
        """
        Write command string to connection

        :param cmd: instruction command
        """

        if self.socket is None:
            raise ConnectionError('Connection has not been established')

        if not cmd.endswith('\r\n'):
            cmd += '\r\n'

        cmd_encode = cmd.encode(self.encoding)
        self.socket.send(cmd_encode)
        if self.debug:
            GlobalConf.logger.debug(f'Command {cmd_encode} was written to {self.host}:{self.port}')

    def readline(self) -> str:
        """Reads until linebreak"""

        if self.socket is None:
            raise ConnectionError('Connection has not been established')

        line = ''
        while True:
            new_char = self.socket.recv(1).decode(self.encoding)
            if new_char != '\n':
                line += new_char
            else:
                break
        return line

    def read(self, count: int = 1024) -> str:
        """
        Read defined length of output bytes

        :param count: bytes to read
        """

        if self.socket is None:
            raise ConnectionError('Connection has not been established')

        return self.socket.recv(count).decode(self.encoding)


def main():
    with TelnetConnection('virtual') as telnet:
        print(telnet.read(2048))
        while True:
            telnet.write(input(telnet.read(4096)))


if __name__ == '__main__':
    main()
