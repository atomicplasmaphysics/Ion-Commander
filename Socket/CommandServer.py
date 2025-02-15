from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
from ast import parse, Module, Expr, Call, Name, literal_eval


from PyQt6.QtCore import QObject


from Config.GlobalConf import GlobalConf, DefaultParams

from Connection.Threaded import (
    ThreadedISEGConnection, ThreadedThyracontConnection, ThreadedTPG300Connection, ThreadedMixedPressureConnection,
    ThreadedMonacoConnection, ThreadedTLPMxConnection, ThreadedDummyConnection
)


def parseFunctionCall(func_str: str) -> tuple[str, list, dict]:
    """
    Parses a function call - provided as string

    Raises ValueError for invalid function calls or malformed arguments
    Raises NameError is function has no name

    :param func_str: function call as string
    :returns: tuple of [
        name: name of function to be called
        args: list of called arguments
        kwargs: dictionary of called keyword arguments
    ]
    """

    tree = parse(func_str)

    if not isinstance(tree, Module) or not tree.body or not isinstance(tree.body[0], Expr):
        raise ValueError('Invalid function call string')

    node = tree.body[0].value

    if not isinstance(node, Call):
        raise ValueError('The provided string is not a function call')

    if not isinstance(node.func, Name):
        raise NameError('Function does not have a name')

    func_name = node.func.id
    args = [literal_eval(arg) for arg in node.args]
    kwargs = {kw.arg: literal_eval(kw.value) for kw in node.keywords}

    return func_name, args, kwargs


class DeviceWrapper:
    """
    Simple wrapper for device connection

    :param threaded_connection: <ThreadedConnection> object
    """

    def __init__(self, threaded_connection = None):
        if threaded_connection is None:
            threaded_connection = ThreadedDummyConnection()

        self.threaded_connection = threaded_connection


class DeviceISEGWrapper(DeviceWrapper):
    """
    Simple wrapper for <ThreadedISEGConnection>

    :param threaded_connection: ThreadedISEGConnection
    """

    def __init__(self, threaded_connection: ThreadedISEGConnection | ThreadedDummyConnection = None):
        super().__init__(threaded_connection)


class DeviceThyracontWrapper(DeviceWrapper):
    """
    Simple wrapper for <ThreadedThyracontConnection>

    :param threaded_connection: ThreadedThyracontConnection
    """

    def __init__(self, threaded_connection: ThreadedThyracontConnection | ThreadedDummyConnection = None):
        super().__init__(threaded_connection)


class DeviceTPG300Wrapper(DeviceWrapper):
    """
    Simple wrapper for <ThreadedTPG300Connection>

    :param threaded_connection: ThreadedTPG300Connection
    """

    def __init__(self, threaded_connection: ThreadedTPG300Connection | ThreadedDummyConnection = None):
        super().__init__(threaded_connection)


class DeviceMixedPressureWrapper(DeviceWrapper):
    """
    Simple wrapper for <ThreadedMixedPressureConnection>

    :param threaded_connection: ThreadedMixedPressureConnection
    """

    def __init__(self, threaded_connection: ThreadedMixedPressureConnection | ThreadedDummyConnection = None):
        super().__init__(threaded_connection)


class DeviceMonacoWrapper(DeviceWrapper):
    """
    Simple wrapper for <ThreadedMonacoConnection>

    :param threaded_connection: ThreadedMonacoConnection
    """

    def __init__(self, threaded_connection: ThreadedMonacoConnection | ThreadedDummyConnection = None):
        super().__init__(threaded_connection)


class DeviceTLPMxWrapper(DeviceWrapper):
    """
    Simple wrapper for <ThreadedTLPMxConnection>

    :param threaded_connection: ThreadedTLPMxConnection
    """

    def __init__(self, threaded_connection: ThreadedTLPMxConnection | ThreadedDummyConnection = None):
        super().__init__(threaded_connection)


class CommandServer(QObject):
    """
    Server to accept incoming commands to GUI that will be forwarded to the connected devices

    :param devices: dictionary of device_name and <DeviceWrapper>
    :param host: hostname or ip
    :param port: port that the server will run on
    :param encoding: used encoding
    :param max_connections: maximum number of simultaneous connections
    :param max_packet: maximum bytesize of packet
    :param debug: if debug messages should be displayed
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
                GlobalConf.logger.debug(f'CommandServer received connection from {client_address}')

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

                    if cmd.lower() in ['help', '?', 'h', '-help', '--help', '-?', '--?', '-h']:
                        self.answerHelp(client_socket)
                        continue

                    if self.debug:
                        GlobalConf.logger.debug(f'CommandServer received message from {client_address}: "{cmd}"')

                    result_state, result_str = self.evaluateCmd(cmd, client_socket)
                    if result_str:
                        if self.debug:
                            GlobalConf.logger.debug(f'CommandServer instantly answers')
                        self.answerCmd(result_str, client_socket, state=result_state)
                except ConnectionResetError:
                    break
            if self.debug:
                GlobalConf.logger.debug(f'CommandServer closed connection from {client_address}')

    def answerHelp(self, client_socket: socket):
        """Answer help message to client"""

        help_msg = 'Call Server via DEVICE:func(args), where the function and its arguments match the Classes in the Connection-folder\nCall DEVICE to see if device is connected\nReturns STATE:answer where STATE is a single digit (0=no error, all else=error)'
        self.answerCmd(help_msg, client_socket)

    def answerCmd(self, answer, client_socket: socket, state: int = None):
        """Answer client"""

        if state is None:
            state = int(isinstance(answer, Exception))
        answer = f'{state}:{answer}'

        if self.debug:
            GlobalConf.logger.debug(f'CommandServer delayed answers to {client_socket.getsockname()}: "{answer}"')

        client_socket.sendall(answer.encode(self.encoding))

    def evaluateCmd(self, cmd: str, client_socket: socket) -> tuple[int, str]:
        """Evaluate sent commands"""

        cmd_split = cmd.split(':')

        device_name = cmd_split[0]
        device = self.devices.get(device_name)

        if device is None:
            return 1, f'Device {device_name} not in device list {self.devices.keys()}'
        if device.threaded_connection is None or device.threaded_connection.isDummy():
            return 2, 'Device connection is not established'

        if len(cmd_split) == 1:
            return 0, 'Ok'

        function_call = ':'.join(cmd_split[1:])
        try:
            func_name, args, kwargs = parseFunctionCall(function_call)

        except (NameError, ValueError) as error:
            return 3, f'Got error while parsing function call "function_call" with error: {error}'

        try:
            device.threaded_connection.callback(
                lambda x, cs=client_socket: self.answerCmd(x, cs),
                getattr(device.threaded_connection, func_name)(*args, **kwargs)
            )

        except (AttributeError, ConnectionError, NameError, TypeError, ValueError) as error:
            return 4, f'Got error while calling function "{func_name}({args}, {kwargs})" for device "{device_name}" with error: {error}'

        return 0, ''

    def stopServer(self):
        """Stop the server and close all connections"""

        self.is_running = False
        self.server_socket.close()
        if self.debug:
            GlobalConf.logger.debug('CommandServer is stopped')
