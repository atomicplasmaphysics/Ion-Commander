import ast
import csv
from datetime import datetime
import operator
import re
from typing import NamedTuple, Self
from pathlib import Path
from socket import socket, AF_INET, SOCK_STREAM
from time import time, sleep


from PyQt6.QtCore import pyqtSignal, QObject, QRunnable, pyqtSlot, QThreadPool


from Config.GlobalConf import GlobalConf, DefaultParams


RANGE_PATTERN = re.compile(r'^\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*:\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*:\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*$')
NUMBER_PATTERN = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
# placeholders: "%" (value of the line), "%1", "%2", ... (value of the loop line with 0, 1, ... tabs) and variables "$name"
TOKEN_PATTERN = re.compile(r'%(\d+)|%|\$([A-Za-z_]\w*)')
OWN_PLACEHOLDER_PATTERN = re.compile(r'%(?!\d)')
VARIABLE_NAME_PATTERN = re.compile(r'^[A-Za-z_]\w*$')
# a script with more steps is not built (e.g. nested ranges by mistake)
MAX_STEPS = 1000000


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


class ScriptError(ValueError):
    """Error in a line of a script"""

    def __init__(self, line_nbr: int, line: str, message: str):
        super().__init__(f'Line {line_nbr}: "{line}": {message}')
        self.line_nbr = line_nbr


def isNumber(text: str) -> bool:
    """True if the text is a number"""

    try:
        float(text)
        return True
    except ValueError:
        return False


def replaceTokens(text: str, values: dict[str, str], brackets: bool = False, strict: bool = True) -> str:
    """
    Replaces the placeholders "%", "%1", "%2", ... and the variables "$name" in the text by their values

    :param text: text with placeholders
    :param values: {placeholder: value}, e.g. {'%': '5', '%1': '10', '$u': '2'}
    :param brackets: put the values in brackets (for math: "-%" -> "-(5)")
    :param strict: raise ValueError for placeholders without value (else they are kept)
    """

    def replace(match: re.Match) -> str:
        token = match.group(0)
        if token in values:
            return f'({values[token]})' if brackets else values[token]
        if not strict:
            return token
        if token == '%':
            raise ValueError('"%" has no value (values are given after the command, e.g. "PSU:voltageSet(0,%) 0:10:1")')
        if token.startswith('%'):
            raise ValueError(f'"{token}" has no value (%1, %2, ... are the values of the enclosing loop lines with 0, 1, ... tabs)')
        raise ValueError(f'"{token}" is not defined (define it above with "VAR {token[1:]} <values>")')

    return TOKEN_PATTERN.sub(replace, text)


def evaluateText(text: str, values: dict[str, str]) -> str:
    """
    Replaces the placeholders/variables of a text (e.g. one argument) and calculates it if it is basic math with numbers:
    "-%" -> "-5", "$u*2+%1" -> "30", "'file_%.lmf'" -> "'file_5.lmf'" (no math), non-numeric values are only replaced

    :param text: text with placeholders
    :param values: {placeholder: value}
    :raises ValueError: if a placeholder has no value
    """

    plain = replaceTokens(text, values)
    tokens = [match.group(0) for match in TOKEN_PATTERN.finditer(text)]
    if tokens and all(isNumber(values[token]) for token in tokens):
        try:
            return formatNumber(evaluateMath(replaceTokens(text, values, brackets=True)))
        except ValueError:
            pass
    return plain


def substituteValues(command: str, values: dict[str, str]) -> str:
    """
    Replaces the placeholders and variables in a command. Arguments of the function with basic math are calculated:
    "PSU:voltageSet(1,-%)" with % = 5 -> "PSU:voltageSet(1,-5)", also "%+5", "%*10", "(%1-%)/2", "abs($u)", "max(%,0)".
    Arguments that are no math (e.g. strings 'file_%.lmf') or non-numeric values are simply replaced.
    Several commands ("A(%);B(-%)") are handled separately.

    :param command: command with placeholders
    :param values: {placeholder: value}, e.g. {'%': '5', '%1': '10', '$u': '2'}
    :raises ValueError: if a placeholder has no value
    """

    substituted = []
    for single in splitCommands(command):
        start, stop = single.find('('), single.rfind(')')
        if start < 0 or stop < start:
            substituted.append(replaceTokens(single, values))
            continue

        arguments = [evaluateText(argument, values) for argument in splitArguments(single[start + 1:stop])]
        substituted.append(f'{replaceTokens(single[:start], values)}({",".join(arguments)}){replaceTokens(single[stop + 1:], values)}')
    return ';'.join(substituted)


def substitutePlaceholder(command: str, value: str, placeholder: str = '%') -> str:
    """
    Replaces the placeholder "%" in a command by the value (see <substituteValues>)

    :param command: command with placeholder
    :param value: value of the placeholder
    :param placeholder: placeholder (only "%" is supported)
    """

    return substituteValues(command, {placeholder: value})


def evaluateValues(argument: str, values: dict[str, str]) -> list[str]:
    """
    Evaluates one value of a line: placeholders/variables are replaced, math is calculated and ranges are expanded,
    e.g. "0:$umax:0.5", "0:%1*2:1", "$u*2", "5", "'text'"

    :param argument: one value (between commas) of a line
    :param values: {placeholder: value} of the enclosing loops and the variables
    :raises ValueError: if a placeholder has no value or the range is invalid
    """

    parts = argument.split(':')
    if len(parts) == 3:
        return expandArguments([':'.join(evaluateText(part, values) for part in parts)])
    return expandArguments([evaluateText(argument, values)])


def isPrint(command: str) -> bool:
    """True for "PRINT <text>" (the text is not split at ";")"""
    return command == 'PRINT' or command.startswith('PRINT ')


def waitSeconds(command: str) -> float | None:
    """Seconds of "WAIT <seconds>", None for other commands (also for the plain "WAIT")"""

    if not command.startswith('WAIT '):
        return None
    return float(command[len('WAIT '):])


def stepCommands(step: str | list[str]) -> list[str]:
    """All single commands of a step (nested loops give lists, "A;B" is split, PRINT texts are kept)"""

    commands = step if isinstance(step, list) else [step]
    return [single for command in commands for single in ([command] if isPrint(command) else splitCommands(command))]


def stepDuration(commands: list[str], interval: float) -> float:
    """
    Duration of a step: "WAIT <seconds>" (the longest one if there are several), 0 if the step only prints,
    else the interval of the script (TIME)

    :param commands: single commands of the step (see <stepCommands>)
    :param interval: interval of the script in seconds
    """

    waits = [seconds for seconds in (waitSeconds(command) for command in commands) if seconds is not None]
    if waits:
        return max(waits)
    if commands and all(isPrint(command) for command in commands):
        return 0.
    return interval


def formatDuration(seconds: float) -> str:
    """Short text of a duration: "45 s", "12 min 5 s", "3 h 20 min" """

    seconds = max(0., seconds)
    if seconds < 60:
        return f'{seconds:.0f} s' if seconds >= 10 else f'{seconds:.1f} s'
    minutes, seconds = divmod(round(seconds), 60)
    if minutes < 60:
        return f'{minutes} min {seconds} s'
    hours, minutes = divmod(minutes, 60)
    return f'{hours} h {minutes} min'


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


class ScriptLine(NamedTuple):
    """One parsed line of a script"""
    number: int  # line number (starting with 1)
    indent: int  # number of tabs
    kind: str  # 'COMMAND', 'PRINT', 'WAIT' or 'VAR'
    text: str  # command / text of PRINT / seconds of WAIT ('' = one interval) / name of the variable
    values: list[str]  # values after the command (not evaluated yet, empty: no values)
    source: str  # line without tabs (for error messages)


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
        # line number of the error (0: no error or unknown)
        self.error_line = 0

    def getQueue(self):
        """Returns the queue"""
        return self.queue

    def stepDurations(self) -> list[float]:
        """Planned duration of every step in seconds"""
        return [stepDuration(stepCommands(step), self.interval) for step in self.queue]

    def duration(self) -> float:
        """Planned duration of the script in seconds (more if commands take longer than the interval)"""
        return sum(self.stepDurations())

    @staticmethod
    def _lineCommand(line: ScriptLine, values: dict[str, str]) -> str | None:
        """
        Command of a line for the given values of the placeholders/variables (None for VAR lines)

        :raises ValueError: if a placeholder has no value or the result is invalid
        """

        if line.kind == 'VAR':
            return None
        if line.kind == 'PRINT':
            # the text is kept as it is, only placeholders/variables with a value are replaced
            return f'PRINT {replaceTokens(line.text, values, strict=False)}'.rstrip()
        if line.kind == 'WAIT':
            if not line.text:
                return 'WAIT'
            text = evaluateText(line.text, values)
            try:
                seconds = float(text)
                if seconds < 0:
                    raise ValueError
            except ValueError:
                raise ValueError(f'"WAIT <seconds>" expects one number >= 0, got "{text}"')
            return f'WAIT {formatNumber(seconds)}'
        return substituteValues(line.text, values)

    @staticmethod
    def _buildCommands(
        lines: list[ScriptLine],
        index: int = 0,
        loop_values: dict[str, str] | None = None,
        variables: dict[str, str] | None = None
    ) -> tuple[list[str | list[str]], int]:
        """
        Builds the steps from the lines. An indented block is a loop: it is executed for every value of the line
        directly above it (the first step of the block is combined with the command of that line, a VAR line has no
        command of its own). Lines on the same level are executed one after another.

        :param lines: parsed lines in the order of the script
        :param index: index of the first line of this level
        :param loop_values: values of the enclosing loop lines {'%1': value, '%2': value, ...}
        :param variables: variables {'$name': value} (a VAR line without block sets a variable for the following lines)
        :returns: (steps, index of the first line that does not belong to this level anymore)
        :raises ScriptError: if a line cannot be built
        """

        loop_values = dict(loop_values or {})
        variables = dict(variables or {})

        steps = []
        level = lines[index].indent if index < len(lines) else 0
        while index < len(lines) and lines[index].indent == level:
            line = lines[index]
            has_block = index + 1 < len(lines) and lines[index + 1].indent > level

            try:
                context = {**loop_values, **variables}
                values = [value for argument in line.values for value in evaluateValues(argument, context)] if line.values else [None]

                # VAR without block: variable for the following lines of this level (and their blocks)
                if line.kind == 'VAR' and not has_block:
                    if len(values) != 1:
                        raise ValueError(f'VAR with several values needs an indented block below (a loop over the values)')
                    variables[f'${line.text}'] = values[0]
                    index += 1
                    continue

                entries = []
                for value in values:
                    value_context = dict(context)
                    if value is not None:
                        value_context['%'] = value
                        value_context[f'%{level + 1}'] = value
                        if line.kind == 'VAR':
                            value_context[f'${line.text}'] = value
                    entries.append((value_context, CommandQueue._lineCommand(line, value_context)))
            except ValueError as error:
                raise ScriptError(line.number, line.source, str(error))

            if not has_block:
                steps.extend(command for _, command in entries if command is not None)
                index += 1
            else:
                next_index = index + 1
                for value_context, command in entries:
                    block_loop_values = {key: value for key, value in value_context.items() if key.startswith('%') and key != '%'}
                    block_variables = {key: value for key, value in value_context.items() if key.startswith('$')}
                    block, next_index = CommandQueue._buildCommands(lines, index + 1, block_loop_values, block_variables)
                    if command is None:
                        steps.extend(block)
                    elif not block:
                        steps.append(command)
                    else:
                        first = block[0].copy() if isinstance(block[0], list) else [block[0]]
                        first.insert(0, command)
                        steps.append(first)
                        steps.extend(block[1:])
                    if len(steps) > MAX_STEPS:
                        raise ScriptError(line.number, line.source, f'the script has more than {MAX_STEPS} steps')
                index = next_index
        return steps, index

    @staticmethod
    def _parseLine(line_nbr: int, indent: int, line: str) -> ScriptLine:
        """
        Parses one line (without tabs, not empty, no comment)

        :raises ScriptError: if the line is invalid
        """

        # PRINT <text>: the text is shown in the output and written to the results (spaces are kept)
        if line.split(' ')[0].upper() == 'PRINT':
            return ScriptLine(line_nbr, indent, 'PRINT', line[len('PRINT'):].strip(), [], line)

        parts = [part for part in line.split(' ') if part]
        func_name = parts[0]

        def values(start: int) -> list[str]:
            """Values after the command, separated by commas (spaces are removed)"""
            text = ''.join(parts[start:])
            return text.split(',') if text else []

        if func_name.upper() == 'TIME':
            raise ScriptError(line_nbr, line, 'TIME already set in line 1')

        # WAIT: one interval, WAIT <seconds>: this step takes the given time instead of the interval,
        # WAIT % <values>: wait times as loop values, WAIT $t / WAIT %1*2: wait time from a variable/loop
        if func_name.upper().startswith('WAIT'):
            if func_name.upper() != 'WAIT':
                raise ScriptError(line_nbr, line, 'unknown statement, did you mean "WAIT", "WAIT <seconds>" or "WAIT % <values>"?')
            seconds = parts[1] if len(parts) > 1 else ''
            wait_values = values(2)
            if OWN_PLACEHOLDER_PATTERN.search(seconds) and not wait_values:
                raise ScriptError(line_nbr, line, '"%" in WAIT, but no values are given (e.g. "WAIT % 1, 2, 5")')
            if wait_values and not OWN_PLACEHOLDER_PATTERN.search(seconds):
                raise ScriptError(line_nbr, line, f'values were given, but no "%" in WAIT (e.g. "WAIT % 1, 2, 5")')
            if seconds and not TOKEN_PATTERN.search(seconds):
                try:
                    if float(seconds) < 0:
                        raise ValueError
                except ValueError:
                    raise ScriptError(line_nbr, line, '"WAIT <seconds>" expects one number >= 0')
            return ScriptLine(line_nbr, indent, 'WAIT', seconds, wait_values, line)

        # VAR <name> <values>: loop over the values (with indented block) or a variable for the following lines
        if func_name.upper() == 'VAR':
            if len(parts) < 3:
                raise ScriptError(line_nbr, line, '"VAR <name> <values>" expects a name and values, e.g. "VAR u 0:100:10"')
            name = parts[1].lstrip('$')
            if not VARIABLE_NAME_PATTERN.match(name):
                raise ScriptError(line_nbr, line, f'"{parts[1]}" is not a valid name (letters, digits and "_", not starting with a digit)')
            return ScriptLine(line_nbr, indent, 'VAR', name, values(2), line)

        command_values = values(1)
        if OWN_PLACEHOLDER_PATTERN.search(func_name) and not command_values:
            raise ScriptError(line_nbr, line, '"%" in function, but no arguments are given')
        if command_values and not OWN_PLACEHOLDER_PATTERN.search(func_name):
            raise ScriptError(line_nbr, line, 'arguments were given, but no "%" in function')
        return ScriptLine(line_nbr, indent, 'COMMAND', func_name, command_values, line)

    @classmethod
    def parseScript(
        cls,
        script: str,
        indent_char: str = '\t',
        comment_char: str = '#'
    ) -> Self:
        """
        Parse provided script and return <CommandQueue> container (with the error message in <error> if it is invalid)

        :param script: script to be parsed
        :param indent_char: character as indent
        :param comment_char: character for commenting (only at line begin)
        """

        cmd_queue = cls([], -1)

        # line number of the first line that is not empty (the line numbers of the errors are the ones of the editor)
        first_line = script[:len(script) - len(script.lstrip())].count('\n') + 1
        script = script.strip()
        script_split = script.split('\n')

        # check if we have script
        if not script:
            cmd_queue.error = 'Empty file'
            cmd_queue.error_line = 1
            return cmd_queue

        # first line is TIME
        args = script_split[0].split()
        first_line_error = len(args) != 2 or args[0].upper() != 'TIME'
        try:
            cmd_queue.interval = float(args[1])
            if cmd_queue.interval < 0:
                first_line_error = True
        except (ValueError, IndexError):
            first_line_error = True

        if first_line_error:
            cmd_queue.interval = -1
            cmd_queue.error = f'Line {first_line}: "{script_split[0].strip()}": "TIME <seconds>" is expected!'
            cmd_queue.error_line = first_line
            return cmd_queue

        # Parse all other lines
        lines = []
        try:
            for line_nbr, line in enumerate(script_split[1:], first_line + 1):

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

                lines.append(cls._parseLine(line_nbr, indent, line))

            # command builder (indented blocks are loops of the line above)
            cmd_queue.queue, index = cls._buildCommands(lines)
            if index < len(lines):
                raise ScriptError(lines[index].number, lines[index].source, 'indentation is less than in the first line of the script')

        except ScriptError as error:
            cmd_queue.queue = []
            cmd_queue.error = str(error)
            cmd_queue.error_line = error.line_nbr

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
        # time (time()) when the next step is executed
        self.next_time = 0.

    def stepDuration(self, commands: list[str]) -> float:
        """Duration of a step (see <stepDuration>)"""
        return stepDuration(commands, self.command_queue.interval)

    @pyqtSlot()
    def run(self):
        """Called when worker is started"""

        self.is_running = True
        self.command_queue.start_time = time()
        self.next_time = self.command_queue.start_time

        while self.is_running:
            if time() < self.next_time:
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

        # several commands in one step: nested loops and "A;B"
        commands = stepCommands(self.command_queue.queue[self.command_queue_idx])
        # the time of the next step is counted from the planned time of this step (no drift)
        self.next_time += self.stepDuration(commands)

        for command in commands:
            if command == 'WAIT' or waitSeconds(command) is not None:
                continue
            if isPrint(command):
                elapsed_time = time() - self.command_queue.start_time
                text = command[len('PRINT'):].strip()
                self.signal.log.emit(f'PRINT at {elapsed_time:.3f} seconds: {text}')
                # empty state: no command was sent
                self.signal.result.emit(elapsed_time, self.command_queue_idx, 'PRINT', f':{text}')
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
    :param results_file: CSV file where every command and its answer is written to (None: no file), the output (log) of the
                         script is written to a file with the same name and the extension ".log"
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
        self.log_file = self.results_file.with_suffix('.log') if self.results_file is not None else None

        self.command_queue = CommandQueue.parseScript(script)
        if self.command_queue.error or self.command_queue.interval == -1:
            raise ValueError(self.command_queue.error)

        # remaining planned time from every step to the end (for the progress)
        self.remaining_durations = [0.] * (len(self.command_queue.queue) + 1)
        for index, duration in reversed(list(enumerate(self.command_queue.stepDurations()))):
            self.remaining_durations[index] = self.remaining_durations[index + 1] + duration

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
        """Handles log signals (also written to the log file)"""
        if self.debug:
            GlobalConf.logger.debug(log)
        if self.log_file is not None:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as file:
                    file.write(f'{datetime.now():%Y-%m-%d %H:%M:%S.%f}'[:-3] + f' {log}\n')
            except OSError as error:
                GlobalConf.logger.error(f'ScriptServer: could not write the log to "{self.log_file}": {error}')
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

    def duration(self) -> float:
        """Planned duration of the script in seconds"""
        return self.remaining_durations[0]

    def progressInfo(self) -> tuple[int, int, float, float]:
        """
        Returns (executed steps, number of steps, seconds until the next step, remaining seconds).
        The remaining time is the planned time, it is longer if commands take longer than the interval.
        """

        steps = len(self.command_queue.queue)
        index = min(self.worker.command_queue_idx, steps)
        if not self.worker.is_running:
            return index, steps, 0., self.remaining_durations[index] if index < steps else 0.
        until_next = max(0., self.worker.next_time - time())
        return index, steps, until_next, until_next + self.remaining_durations[index]

    def progress(self) -> int:
        """Returns the progress in percent (planned time)"""

        total = self.duration()
        steps = len(self.command_queue.queue)
        if not steps:
            return 0
        index, _, _, remaining = self.progressInfo()
        if total <= 0:
            return round(100 * index / steps)
        return max(0, min(100, round(100 * (total - remaining) / total)))


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
# waits 5 seconds (this step takes 5 s instead of the interval)
WAIT 5
# PRINT writes the text into the output and the results (takes no time)
PRINT starting the laser scan

# commands will be set one after another
# '%' can be used as placeholder and following arguments will be placed inside
# basic math with '%' is calculated, e.g. -%, %+5, %*10, (%-1)/2, abs(%), max(%,0) (no spaces in the command)
LASER:rfSet(%) 23, 24

# %1, %2, ... are the values of the enclosing loop lines (%1: line without tab, %2: line with one tab, ...)
# VAR <name> <values> loops the indented block over the values ($name in the commands, no step of its own),
# VAR <name> <value> without block is a variable for the following lines; WAIT % <values>: wait times as loop values
VAR umax 100
PSU:voltageSet(0,%) 0:$umax:50
\tPSU:voltageSet(1,-%1/2+%) 0, 5
\t\tWAIT % 1, 2

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
