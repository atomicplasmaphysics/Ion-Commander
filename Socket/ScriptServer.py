import ast
import csv
import operator
import re
from typing import Self
from pathlib import Path
from socket import socket, AF_INET, SOCK_STREAM
from time import time, sleep


from PyQt6.QtCore import pyqtSignal, QObject, QRunnable, pyqtSlot, QThreadPool


from Config.GlobalConf import GlobalConf, DefaultParams


RANGE_PATTERN = re.compile(r'^\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*:\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*:\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*$')
NUMBER_PATTERN = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


def expandArguments(arguments: list[str]) -> list[str]:
    """
    Expands ranges "start:stop:step" (stop is included) into single values, other arguments are kept

    Example: ["0:1:0.5", "5"] -> ["0", "0.5", "1", "5"]

    :param arguments: list of arguments
    """

    expanded = []
    for argument in arguments:
        match = RANGE_PATTERN.match(argument)
        if match is None:
            expanded.append(argument.strip())
            continue
        start, stop, step = (float(value) for value in match.groups())
        if step == 0 or (stop - start) / step < 0:
            raise ValueError(f'Invalid range "{argument}" (step must not be 0 and must point from start to stop)')
        count = int(round((stop - start) / step, 9)) + 1
        if count > 100000:
            raise ValueError(f'Range "{argument}" has too many values ({count})')
        expanded.extend(formatNumber(start + i * step) for i in range(count))
    return expanded


def formatNumber(value: float | int) -> str:
    """Short text of a number without float noise (0.30000000000000004 -> "0.3", 2.0 -> "2", 1E-13 -> "1e-13")"""

    if isinstance(value, int):
        return str(value)
    value = float(f'{value:.12g}')
    if value.is_integer() and abs(value) < 1E15:
        return str(int(value))
    return repr(value)


MATH_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
MATH_FUNCTIONS = {'abs': abs, 'round': round, 'min': min, 'max': max}


def evaluateMath(expression: str) -> float | int:
    """
    Safely evaluates basic math: numbers, + - * / // **, brackets and abs(), round(), min(), max()

    :param expression: e.g. "-(5)", "(5)*10+2", "max((5)-10,0)"
    :raises ValueError: if the expression is not basic math
    """

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in MATH_OPERATORS:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError('exponent too large')
            return MATH_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in MATH_OPERATORS:
            return MATH_OPERATORS[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in MATH_FUNCTIONS and not node.keywords:
            return MATH_FUNCTIONS[node.func.id](*[evaluate(argument) for argument in node.args])
        raise ValueError(f'"{expression}" is not basic math')

    try:
        result = evaluate(ast.parse(expression.strip(), mode='eval'))
    except (SyntaxError, TypeError, ZeroDivisionError, OverflowError) as error:
        raise ValueError(f'"{expression}" cannot be calculated: {error}')
    if isinstance(result, complex):
        raise ValueError(f'"{expression}" is complex')
    return result


def splitArguments(arguments: str) -> list[str]:
    """Splits "1,'a,b',[2,3]" at the commas that are not inside brackets or quotes"""

    parts = []
    current = ''
    depth = 0
    quote = ''
    for char in arguments:
        if quote:
            if char == quote:
                quote = ''
        elif char in '\'"':
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(current)
            current = ''
            continue
        current += char
    parts.append(current)
    return parts


def substitutePlaceholder(command: str, value: str, placeholder: str = '%') -> str:
    """
    Replaces the placeholder in a command by the value. Arguments of the function with basic math are calculated:
    "PSU:voltageSet(1,-%)" with value 5 -> "PSU:voltageSet(1,-5)", also "%+5", "%*10", "(%-1)/2", "abs(%)", "max(%,0)".
    Arguments that are no math (e.g. strings 'file_%.lmf') or non-numeric values are simply replaced.
    Several commands ("A(%);B(-%)") are handled separately.

    :param command: command with placeholder
    :param value: value of the placeholder
    :param placeholder: placeholder character
    """

    try:
        float(value)
        numeric = True
    except ValueError:
        numeric = False

    substituted = []
    for single in splitCommands(command):
        start, stop = single.find('('), single.rfind(')')
        if not numeric or start < 0 or stop < start:
            substituted.append(single.replace(placeholder, value))
            continue

        arguments = []
        for argument in splitArguments(single[start + 1:stop]):
            if placeholder in argument:
                try:
                    argument = formatNumber(evaluateMath(argument.replace(placeholder, f'({value})')))
                except ValueError:
                    argument = argument.replace(placeholder, value)
            arguments.append(argument)

        substituted.append(f'{single[:start].replace(placeholder, value)}({",".join(arguments)}){single[stop + 1:].replace(placeholder, value)}')
    return ';'.join(substituted)


def splitCommands(command: str) -> list[str]:
    """
    Splits "A(1);B(2)" into ["A(1)", "B(2)"] - several commands in one step (";" inside brackets or quotes is kept)

    :param command: command string
    """

    commands = []
    current = ''
    depth = 0
    quote = ''
    for char in command:
        if quote:
            if char == quote:
                quote = ''
        elif char in '\'"':
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif char == ';' and depth == 0:
            if current.strip():
                commands.append(current.strip())
            current = ''
            continue
        current += char
    if current.strip():
        commands.append(current.strip())
    return commands


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
            try:
                args = expandArguments(args) if args[0] else args
            except ValueError as error:
                cmd_queue.error = f'Line {line_nbr}: "{line}": {error}'
                return cmd_queue

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
                line_commands.append((line_nbr, indent, [substitutePlaceholder(func_name, arg, placeholder_char) for arg in args]))
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
    result: (elapsed time, step, command, answer) of every sent command
    """

    log = pyqtSignal(str)
    finish = pyqtSignal()
    result = pyqtSignal(float, int, str, str)


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
        # several commands in one step: nested loops and "A;B"
        for command in [single for command in commands for single in splitCommands(command)]:
            if command == 'WAIT':
                continue
            self.socket_connection.sendall(command.encode(self.encoding))
            elapsed_time = time() - self.command_queue.start_time
            self.command_queue.command_times.append(elapsed_time)
            recv_msg = self.socket_connection.recv(4096).decode(self.encoding)
            self.signal.log.emit(f'ScriptServer sent "{command}" at {elapsed_time:.3f} seconds and received "{recv_msg}"')
            self.signal.result.emit(elapsed_time, self.command_queue_idx, command, recv_msg)

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
    :param results_file: CSV file where every command and its answer is written to (None: no file)
    """

    log = pyqtSignal(str)
    finish = pyqtSignal()

    results_header = ['time_s', 'step', 'command', 'state', 'answer', 'value']

    def __init__(
        self,
        script: str,
        host: str = DefaultParams.cs_host,
        port: int = DefaultParams.cs_port,
        encoding: str = DefaultParams.cs_encoding,
        debug: bool = False,
        results_file: str | Path | None = None
    ):
        super().__init__()
        self.script = script
        self.results_file = Path(results_file) if results_file is not None else None

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
        self.worker.signal.result.connect(self.handleResult)

        if self.results_file is not None:
            self.results_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.results_file, 'w', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow(self.results_header)

    @pyqtSlot(float, int, str, str)
    def handleResult(self, elapsed_time: float, step: int, command: str, answer: str):
        """Writes the answer of a command into the results file (state = 0 means no error, value = first number of the answer)"""

        if self.results_file is None:
            return
        state, _, answer_text = answer.partition(':')
        numbers = NUMBER_PATTERN.findall(answer_text) if state == '0' else []
        value = numbers[0] if numbers and answer_text.strip() not in ('None', 'Ok') else ''
        try:
            with open(self.results_file, 'a', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow([f'{elapsed_time:.3f}', step + 1, command, state, answer_text, value])
        except OSError as error:
            GlobalConf.logger.error(f'ScriptServer: could not write results to "{self.results_file}": {error}')

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
# basic math with '%' is calculated, e.g. -%, %+5, %*10, (%-1)/2, abs(%), max(%,0) (no spaces in the command)
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
