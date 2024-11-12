from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
from typing import Any


from PyQt6.QtCore import QObject


from Config.GlobalConf import GlobalConf, DefaultParams

from Connection.Threaded import ThreadedConnection


class DeviceWrapper:
    """
    Simple wrapper for device connection

    :param threaded_connection: <ThreadedConnection> object
    """

    def __init__(self, threaded_connection: ThreadedConnection | Any = None):
        self.threaded_connection = threaded_connection


class CommandServer(QObject):
    """
    Server to accept incoming commands to GUI that will be forwarded to the connected devices

    :param devices: dictionary of device_name and <DeviceWrapper>
    :param host: hostname or ip
    :param port: port that the server will run on
    :param encoding: used encoding
    :param max_connections: maximum number of simultaneous connections
    :param max_packet: maximum bytesize of packet
    :param debug: if debug messages should be displayed,
    :param daemonic: sets the threads to daemonic
    """

    def __init__(
        self,
        devices: dict[str, DeviceWrapper],
        host: str = DefaultParams.cs_host,
        port: int = DefaultParams.cs_port,
        encoding: str = DefaultParams.cs_encoding,
        max_connections: int = DefaultParams.cs_max_connections,
        max_packet: int = 1024,
        debug: bool = False,
        daemonic: bool = False
    ):
        super().__init__()

        self.devices = devices

        self.host = host
        self.port = port
        self.encoding = encoding
        self.max_connections = max_connections
        self.max_packet = max_packet

        self.debug = debug
        self.daemonic = daemonic

        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_connections)

        self.is_running = False

    def startServer(self):
        """Start the server and accept incoming connections in separate threads"""

        if self.is_running:
            return

        self.is_running = True

        if self.debug:
            GlobalConf.logger.debug(f'CommandServer started on "{self.host}:{self.port}" with encoding "{self.encoding}"')

        Thread(
            target=self.acceptConnections,
            daemon=self.daemonic
        ).start()

    def acceptConnections(self):
        """Accept multiple client connections"""

        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()

            except TimeoutError:
                continue

            except OSError as error:
                if self.is_running:
                    raise error
                break

            if self.debug:
                GlobalConf.logger.debug(f'CommandServer received connection from "{client_address}"')

            Thread(
                target=self.handleClient,
                args=(client_socket, client_address),
                daemon=self.daemonic
            ).start()

    def handleClient(self, client_socket: socket, client_address):
        """Handle client commands"""

        with client_socket:
            while True:
                try:
                    cmd = client_socket.recv(self.max_packet).decode(self.encoding)
                    if not cmd:
                        break

                    if self.debug:
                        GlobalConf.logger.debug(f'CommandServer received message from "{client_address}": {cmd}')

                    result = self.evaluateCmd(cmd, client_socket)
                    if result:
                        if self.debug:
                            GlobalConf.logger.debug(f'CommandServer answers to "{client_address}": {result}')
                        self.answerCmd(result, client_socket)
                except ConnectionResetError:
                    break
            if self.debug:
                GlobalConf.logger.debug(f'CommandServer closed connection from "{client_address}"')

    def answerCmd(self, answer, client_socket: socket):
        """Answer client"""

        client_socket.sendall(str(answer).encode(self.encoding))

    def evaluateCmd(self, cmd: str, client_socket: socket) -> str:
        """Evaluate sent commands"""

        cmd_split = cmd.split(':')

        device_name = cmd_split[0]
        device = self.devices.get(device_name)

        if device is None:
            return f'1-Device {device_name} not in device list {self.devices.keys()}'
        if device.threaded_connection.isDummy():
            return '2-Device connection is not established'
        # TODO: maybe more checks needed

        if len(cmd_split) == 1:
            return '0-Ok'

        func_name = cmd_split[1]
        args = []
        kwargs = dict()
        if len(cmd_split) == 3:
            for arg in cmd_split[2].split(','):
                if '=' not in arg:
                    args.append(arg)

                arg_split = arg.split('=')
                if len(arg_split) != 2:
                    return f'3-Key word arguments must be of "name=value", provided was "{arg}"'
                kwargs.update({
                    arg_split[0]: arg_split[1]
                })

        try:
            device.threaded_connection.callback(
                lambda x, cs=client_socket: self.answerCmd(x, cs),
                device.threaded_connection.__getattr__(func_name)(*args, **kwargs)
            )

        except (AttributeError, ConnectionError, NameError, TypeError, ValueError) as error:
            return f'4-Got error while calling function "{func_name}({args}, {kwargs})" for device "{device_name}": {error}'

        return ''

    def stopServer(self):
        """Stop the server and close all connections"""

        self.is_running = False
        self.server_socket.close()
        if self.debug:
            GlobalConf.logger.debug('CommandServer is stopped')
