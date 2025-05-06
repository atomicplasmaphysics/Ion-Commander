from typing import Self
from socket import socket, AF_INET, SOCK_STREAM
from time import time, sleep


from PyQt6.QtCore import pyqtSignal, QObject, QRunnable, pyqtSlot, QThreadPool


from Config.GlobalConf import GlobalConf, DefaultParams


class CommandQueue:
    """
    Container to store command queues

    :param queue: Queue of commands, which can be strings or list of strings
    :param interval: interval of commands
    :param start_time: when command queue was started
    :param command_times: when command times were started
    :param error: error messages
    """

    def __init__(
        self,
        queue: list[str | list[str]],
        interval: float,
        start_time: float = -1,
        command_times: list[float] = None,
        error: str = ''
    ):
        self.queue = queue
        self.interval = interval
        self.start_time = start_time
        if command_times is None:
            command_times = []
        self.command_times = command_times
        self.error = error

    def getQueue(self):
        """Returns the queue"""
        return self.queue

    # TODO: also allow multiple commands to be set at each timestep
    @staticmethod
    def _buildCommands(indent_commands: list[tuple[int, list[str]]]) -> tuple[int, list[str | list[str]]]:
        """
        Builds commands from given indent_commands

        :param indent_commands: list of tuple(indent, [list of commands])
        """

        if not indent_commands:
            return 0, []

        if len(indent_commands) == 1:
            return 1, indent_commands[0][1]

        indent_command = indent_commands[0]
        next_command = indent_commands[1]
        if next_command[0] < indent_command[0]:
            return 1, indent_commands[0][1]

        commands = []
        skip, next_commands = CommandQueue._buildCommands(indent_commands[1:])
        for ic in indent_command[1]:
            nc0 = next_commands[0]
            if not isinstance(nc0, list):
                nc0 = [nc0]
            else:
                nc0 = nc0.copy()
            nc0.insert(0, ic)
            commands.append(nc0)
            commands.extend(next_commands[1:])

        next_command = indent_commands[skip + 1:]
        if not next_command:
            return skip + 1, commands
        next_command = next_command[0]
        if next_command and next_command[0] < indent_command[0]:
            return skip + 1, commands

        skip2, commands2 = CommandQueue._buildCommands(indent_commands[skip + 1:])
        commands.extend(commands2)
        return skip + skip2 + 1, commands

    @classmethod
    def parseScript(
        cls,
        script: str,
        placeholder_char: str = '%',
        indent_char: str = '\t',
        comment_char: str = '#'
    ) -> Self:
        """
        Parse provided script and return <CommandQueue> container

        :param script: script to be parsed
        :param placeholder_char: character as placeholder
        :param indent_char: character as indent
        :param comment_char: character for commenting (only at line begin)
        """

        cmd_queue = cls([], -1)

        script = script.strip()
        script_split = script.split('\n')

        # check if we have script
        if not script_split:
            cmd_queue.error = 'Empty file'
            return cmd_queue

        # first line is TIME
        args = script_split[0].split(' ')
        first_line_error = False
        if not len(args) == 2:
            first_line_error = True
        elif not args[0].upper() == 'TIME':
            first_line_error = True

        try:
            cmd_queue.interval = float(args[1])
        except (ValueError, IndexError):
            first_line_error = True

        if first_line_error:
            cmd_queue.error = f'Line 1: "{script_split[0]}": "TIME <seconds>" is expected!'
            return cmd_queue

        # Parse all other lines
        line_commands = []
        for line_nbr, line in enumerate(script_split[1:], 2):

            # strip right side of line
            line = line.rstrip()

            indent = 0
            while line:
                if not line[0] == indent_char:
                    break
                indent += 1
                line = line[1:]

            # check if line is empty or commented out
            if not line or line.startswith(comment_char):
                continue

            args = line.split(' ')
            if not args:
                cmd_queue.error = f'Line {line_nbr}: "{line}": unsplittable line "{line}"'
                return cmd_queue
            func_name = args[0]
            args = ''.join(args[1:]).split(',')

            if func_name.upper() == 'TIME':
                cmd_queue.error = f'Line {line_nbr}: "{line}": TIME already set in line 1'
                return cmd_queue

            if func_name.upper().startswith('WAIT') and len(line) != len('WAIT'):
                cmd_queue.error = f'Line {line_nbr}: "{line}": WAIT statement has no allowed arguments'
                return cmd_queue

            if placeholder_char in func_name:
                if not args[0]:
                    cmd_queue.error = f'Line {line_nbr}: "{line}": "{placeholder_char}" in function, but no arguments are given'
                    return cmd_queue
                line_commands.append((line_nbr, indent, [func_name.replace(placeholder_char, arg) for arg in args]))
            else:
                if args[0]:
                    cmd_queue.error = f'Line {line_nbr}: "{line}": arguments were given, but no "{placeholder_char}" in function'
                    return cmd_queue
                line_commands.append((line_nbr, indent, [func_name]))

        # concatenate lines if they are on the same level
        indent_commands = []
        current_group = []
        current_number = None

        for _, number, commands in line_commands:
            if number != current_number:
                if current_group:
                    indent_commands.append((current_number, current_group))
                current_group = []
                current_number = number

            current_group.extend(commands)

        if current_group:
            indent_commands.append((current_number, current_group))

        # command builder
        _, cmd_queue.queue = cls._buildCommands(indent_commands)

        return cmd_queue


class ScriptServerWorkerSignals(QObject):
    """
    Signals for <ScriptServerWorker>

    log: log messages
    finish: only signal on finish
    """

    log = pyqtSignal(str)
    finish = pyqtSignal()


class ScriptServerWorker(QRunnable):
    """
    Threaded ScriptServer for communicating with socket server

    :param command_queue: filled <CommandQueue> object
    :param socket_connection: opened socket
    :param encoding: encoding of socket
    """

    def __init__(
        self,
        command_queue: CommandQueue,
        socket_connection: socket,
        encoding: str = 'utf-8'
    ):
        super().__init__()
        self.command_queue = command_queue
        self.socket_connection = socket_connection
        self.encoding = encoding

        self.signal = ScriptServerWorkerSignals()

        self.command_queue_idx = 0
        self.is_running = False

    @pyqtSlot()
    def run(self):
        """Called when worker is started"""

        self.is_running = True
        self.command_queue.start_time = time()
        self.nextCommand()

        while True:
            if not self.is_running:
                break

            if self.command_queue_idx * self.command_queue.interval > time() - self.command_queue.start_time:
                sleep(0.001)
                continue

            self.nextCommand()

    def nextCommand(self):
        """Executes next command"""

        if self.socket_connection is None:
            raise ConnectionError('ScriptServer did not establish connection yet')

        if self.command_queue_idx >= len(self.command_queue.queue):
            self.signal.log.emit('ScriptServer executed all commands')
            self.signal.finish.emit()
            self.is_running = False
            return

        commands = self.command_queue.queue[self.command_queue_idx]
        if not isinstance(commands, list):
            commands = [commands]
        for command in commands:
            if command == 'WAIT':
                continue
            self.socket_connection.sendall(command.encode(self.encoding))
            elapsed_time = time() - self.command_queue.start_time
            self.command_queue.command_times.append(elapsed_time)
            recv_msg = self.socket_connection.recv(1024).decode(self.encoding)
            self.signal.log.emit(f'ScriptServer sent "{command}" at {elapsed_time:.3f} seconds and received "{recv_msg}"')

        self.command_queue_idx += 1

    def stop(self):
        """Stops execution of commands"""
        self.is_running = False


class ScriptServer(QObject):
    """
    Server to execute scripts on the <CommandServer>

    :param script: script to be executed
    :param host: hostname or ip
    :param port: port that the server will run on
    :param encoding: used encoding
    :param debug: if debug messages should be displayed
    """

    log = pyqtSignal(str)
    finish = pyqtSignal()

    def __init__(
        self,
        script: str,
        host: str = DefaultParams.cs_host,
        port: int = DefaultParams.cs_port,
        encoding: str = DefaultParams.cs_encoding,
        debug: bool = False,
    ):
        super().__init__()
        self.script = script

        self.command_queue = CommandQueue.parseScript(script)
        if self.command_queue.error or self.command_queue.interval == -1:
            raise ValueError(self.command_queue.error)

        self.host = host
        self.port = port
        self.encoding = encoding
        self.debug = debug

        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        if self.debug:
            GlobalConf.logger.debug(f'ScriptServer connected to "{self.host}:{self.port}"')

        self.worker = ScriptServerWorker(self.command_queue, self.socket)
        self.worker.signal.log.connect(self.handleLog)
        self.worker.signal.finish.connect(self.handleFinish)

    @pyqtSlot(str)
    def handleLog(self, log: str):
        """Handles log signals"""
        if self.debug:
            GlobalConf.logger.debug(log)
        self.log.emit(log)

    @pyqtSlot()
    def handleFinish(self):
        """Handles finish signals"""
        if self.debug:
            GlobalConf.logger.debug('ScriptServer finished')
        self.finish.emit()
        self.socket.close()

    def start(self):
        """Starts the execution of commands"""
        QThreadPool.globalInstance().start(self.worker)

    def stop(self):
        """Stops execution of commands"""
        self.worker.stop()
        self.socket.close()

    def isRunning(self) -> bool:
        """Determines if script server is running"""
        return self.worker.is_running

    def progress(self) -> int:
        """Returns progress"""
        if not self.command_queue.queue:
            return 0
        return round(100 * (self.worker.command_queue_idx - 1) / len(self.command_queue.queue))


def main():
    import sys
    import logging
    from PyQt6.QtWidgets import QApplication

    logging.basicConfig(level=logging.DEBUG)

    script = """
TIME 10
# first line always has to specify the interval of the commands
# lines with a '#' are treated as comment and are ignored
# in line comments do not work
# empty lines will also be ignored

# sleep statement does nothing for a 'cycle'
WAIT

# commands will be set one after another
# '%' can be used as placeholder and following arguments will be placed inside
LASER:rfSet(%) 23, 24

# Tabs '\t' are treated as loops
\tLASER:rrSet(%) 10, 1

# the total code will actually perform following commands:
# (0: wait)
# 1: LASER:rfSet(23) AND LASER:rrSet(10)
# 2: LASER:rrSet(1)
# 3: LASER:rfSet(24) AND LASER:rrSet(10)
# 4: LASER:rrSet(1)
    """

    app = QApplication(sys.argv)

    try:
        ss = ScriptServer(script=script, debug=True)
        ss.start()
    except (ConnectionRefusedError, ConnectionError, ValueError) as error:
        print(error)

    print('we are here')

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
