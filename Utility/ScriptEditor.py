import inspect
import re
from functools import lru_cache
from html import escape
from typing import NamedTuple


from PyQt6.QtCore import Qt, QEvent, QModelIndex, QPoint, QTimer
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPalette, QStandardItemModel, QStandardItem, QTextCursor, QKeySequence
from PyQt6.QtWidgets import QCompleter, QToolTip


from Utility.Layouts import FileEditor


class ScriptFunction(NamedTuple):
    """Function of a device that can be called by scripts"""
    name: str
    parameters: list[str]  # parameter names (without self)
    signature: str  # full signature with annotations and defaults (without self)
    doc: str  # docstring


# statements of the script language (see Socket/ScriptServer.py): name -> description
SCRIPT_KEYWORDS = {
    'TIME': 'TIME <seconds>\nInterval between the steps (first line of every script)',
    'WAIT': 'WAIT: does nothing for one interval\nWAIT <seconds>: this step takes the given time\nWAIT % <values>: wait times as loop values',
    'VAR': 'VAR <name> <values>: loop of the indented block over the values ($name)\nVAR <name> <value>: variable for the following lines',
    'PRINT': 'PRINT <text>\nWrites the text into the output and the results (takes no time, %, %1 and $name are replaced)',
}

# placeholders "%", "%1", ... and variables "$name" (same as the parser)
PLACEHOLDER_PATTERN = re.compile(r'%\d*|\$[A-Za-z_]\w*')
NUMBER_PATTERN = re.compile(r'(?<![\w$%.])[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
STRING_PATTERN = re.compile(r'\'[^\']*\'?|"[^"]*"?')
# "DEVICE:function" at the start of a command (after tabs or ";")
COMMAND_PATTERN = re.compile(r'(?:^|;)\s*([A-Za-z_]\w*)(?::([A-Za-z_]\w*))?')
INDENT_PATTERN = re.compile(r'^\t*')


@lru_cache(maxsize=None)
def deviceFunctions(connection_class: type) -> dict[str, ScriptFunction]:
    """
    Public functions of a connection class (the CommandServer calls them by name), sorted by name

    :param connection_class: e.g. ISEGConnection
    """

    functions = {}
    for name, function in sorted(inspect.getmembers(connection_class, inspect.isfunction), key=lambda item: item[0].lower()):
        if name.startswith('_'):
            continue
        try:
            parameters = list(inspect.signature(function).parameters.values())[1:]
        except (TypeError, ValueError):
            parameters = []
        signature = f'({", ".join(str(parameter) for parameter in parameters)})'
        functions[name] = ScriptFunction(name, [parameter.name for parameter in parameters], signature, inspect.getdoc(function) or '')
    return functions


class ScriptCatalog:
    """
    Devices of the CommandServer and their functions (autocomplete, highlighting and check of the script editor)

    :param devices: {device name: connection class}, e.g. {'PSU': ISEGConnection}
    """

    def __init__(self, devices: dict[str, type] | None = None):
        self.devices = {name: cls for name, cls in (devices or {}).items() if cls is not None}

    def isEmpty(self) -> bool:
        """No devices known (nothing is marked as unknown)"""
        return not self.devices

    def functions(self, device: str) -> dict[str, ScriptFunction]:
        """Functions of a device (empty if the device is unknown)"""

        cls = self.devices.get(device)
        return deviceFunctions(cls) if cls is not None else {}

    def function(self, device: str, name: str) -> ScriptFunction | None:
        """Function of a device or None"""
        return self.functions(device).get(name)

    def checkCommand(self, device: str, function: str | None) -> str:
        """Error message for an unknown device or function, '' if it is known (or no devices are known)"""

        if self.isEmpty():
            return ''
        if device not in self.devices:
            return f'unknown device "{device}" (devices: {", ".join(self.devices)})'
        if function and function not in self.functions(device):
            return f'unknown function "{device}:{function}"'
        return ''

    def checkScript(self, script: str) -> list[tuple[int, str]]:
        """
        Unknown devices/functions of a script (the parser does not know the devices)

        :param script: text of the script
        :returns: [(line number, message), ...]
        """

        problems = []
        for line_nbr, line in enumerate(script.split('\n'), 1):
            text = line.strip()
            if line_nbr == 1 or not text or text.startswith('#') or text.split(' ')[0].upper() in SCRIPT_KEYWORDS:
                continue
            # the command is the first part of the line (values follow after a space)
            command = text.split(' ')[0]
            for match in COMMAND_PATTERN.finditer(command):
                message = self.checkCommand(match.group(1), match.group(2))
                if message:
                    problems.append((line_nbr, message))
        return problems


def isDarkPalette(palette: QPalette) -> bool:
    """True if the background of text fields is dark"""
    return palette.color(QPalette.ColorRole.Base).lightness() < 128


class ScriptHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighting of scripts: comments, statements (TIME, WAIT, VAR, PRINT), devices, functions, numbers,
    strings, placeholders/variables. Unknown devices/functions and the faulty line (syntax check) are underlined.

    :param document: document of the editor
    :param catalog: known devices and functions
    :param dark: colors for a dark background
    """

    colors_dark = {
        'comment': '#7f848e', 'keyword': '#cc7832', 'device': '#4ec9b0', 'function': '#ffc66d',
        'number': '#6897bb', 'string': '#6a8759', 'placeholder': '#c77dbb', 'error': '#ff5555',
    }
    colors_light = {
        'comment': '#8c8c8c', 'keyword': '#0033b3', 'device': '#00796b', 'function': '#7a3e9d',
        'number': '#1750eb', 'string': '#067d17', 'placeholder': '#c24e00', 'error': '#e00000',
    }

    def __init__(self, document, catalog: ScriptCatalog, dark: bool = False):
        super().__init__(document)
        self.catalog = catalog
        # line number (starting with 1) and message of the syntax error, 0: none
        self.error_line = 0
        self.error_message = ''

        colors = self.colors_dark if dark else self.colors_light
        self.formats: dict[str, QTextCharFormat] = {}
        for name, color in colors.items():
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(color))
            self.formats[name] = text_format
        self.formats['comment'].setFontItalic(True)
        self.formats['keyword'].setFontWeight(QFont.Weight.Bold)
        self.formats['device'].setFontWeight(QFont.Weight.Bold)
        self.error_color = QColor(colors['error'])

    def setCatalog(self, catalog: ScriptCatalog):
        """New devices/functions (highlights again)"""
        self.catalog = catalog
        self.rehighlight()

    def setError(self, line: int, message: str = ''):
        """Underlines the faulty line (0: no error)"""

        if (line, message) == (self.error_line, self.error_message):
            return
        old_line = self.error_line
        self.error_line, self.error_message = line, message
        for number in {old_line, line}:
            block = self.document().findBlockByNumber(number - 1)
            if number > 0 and block.isValid():
                self.rehighlightBlock(block)

    def underline(self, start: int, length: int):
        """Red wavy underline (keeps the color of the text)"""

        for position in range(start, start + length):
            text_format = QTextCharFormat(self.format(position))
            text_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            text_format.setUnderlineColor(self.error_color)
            self.setFormat(position, 1, text_format)

    def highlightBlock(self, text: str):
        """Highlights one line"""

        line_nbr = self.currentBlock().blockNumber() + 1
        indent = len(INDENT_PATTERN.match(text).group(0))
        body = text[indent:]

        # comments only at the beginning of a line (after tabs), like the parser
        if body.startswith('#'):
            self.setFormat(0, len(text), self.formats['comment'])
            return

        word = body.split(' ')[0]
        keyword = word.upper()
        if keyword in SCRIPT_KEYWORDS:
            self.setFormat(indent, len(word), self.formats['keyword'])
            rest_start = indent + len(word)
            if keyword == 'PRINT':
                self.setFormat(rest_start, len(text) - rest_start, self.formats['string'])
            else:
                self.highlightValues(text, rest_start)
            if keyword == 'VAR':
                match = re.match(r'\s+(\$?[A-Za-z_]\w*)', text[rest_start:])
                if match:
                    self.setFormat(rest_start + match.start(1), len(match.group(1)), self.formats['placeholder'])
        elif body:
            command_end = indent + len(word)
            self.highlightValues(text, indent)
            for match in COMMAND_PATTERN.finditer(text[indent:command_end]):
                device, function = match.group(1), match.group(2)
                device_start = indent + match.start(1)
                self.setFormat(device_start, len(device), self.formats['device'])
                if function:
                    self.setFormat(indent + match.start(2), len(function), self.formats['function'])
                message = self.catalog.checkCommand(device, function)
                if message.startswith('unknown device'):
                    self.underline(device_start, len(device))
                elif message:
                    self.underline(indent + match.start(2), len(function))

        if line_nbr == self.error_line and text.strip():
            self.underline(indent, len(text) - indent)

    def highlightValues(self, text: str, start: int):
        """Numbers, strings and placeholders/variables from <start> to the end of the line"""

        part = text[start:]
        for match in NUMBER_PATTERN.finditer(part):
            self.setFormat(start + match.start(), len(match.group(0)), self.formats['number'])
        for match in PLACEHOLDER_PATTERN.finditer(part):
            self.setFormat(start + match.start(), len(match.group(0)), self.formats['placeholder'])
        for match in STRING_PATTERN.finditer(part):
            self.setFormat(start + match.start(), len(match.group(0)), self.formats['string'])


class ScriptEditor(FileEditor):
    """
    Editor for scripts: syntax highlighting, autocomplete of statements, devices and their functions (Ctrl+Space,
    automatically while typing), the documentation of a function as tooltip and the faulty line underlined

    :param parent: parent widget
    :param catalog: known devices and functions (see <setCatalog>)
    """

    completion_role = Qt.ItemDataRole.UserRole + 1
    insert_role = Qt.ItemDataRole.UserRole + 2
    kind_role = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None, catalog: ScriptCatalog | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.catalog = catalog or ScriptCatalog()

        self.highlighter = ScriptHighlighter(self.document(), self.catalog, isDarkPalette(self.palette()))

        # completion list: the items are filtered and sorted here (prefix matches first), the completer only shows them
        self.completion_model = QStandardItemModel(self)
        self.completer = QCompleter(self.completion_model, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setCompletionRole(self.completion_role)
        self.completer.setMaxVisibleItems(12)
        self.completer.activated[QModelIndex].connect(self.insertCompletion)
        self.completer.highlighted[QModelIndex].connect(self.showCompletionDoc)
        # start of the text that is replaced by the completion (position in the document)
        self.completion_start = 0

    def setCatalog(self, catalog: ScriptCatalog):
        """Sets the known devices and functions"""

        self.catalog = catalog
        self.highlighter.setCatalog(catalog)

    def setError(self, line: int, message: str = ''):
        """Underlines the faulty line of the syntax check (0: no error)"""
        self.highlighter.setError(line, message)

    # completion

    def completionContext(self) -> tuple[str, str, str] | None:
        """
        What can be completed at the cursor

        :returns: ('function', device, prefix), ('start', '', prefix) or None
        """

        cursor = self.textCursor()
        if cursor.hasSelection():
            return None
        line = cursor.block().text()[:cursor.positionInBlock()]
        if line.lstrip('\t').startswith('#'):
            return None
        # function after "DEVICE:" (also after ";" for several commands)
        match = re.search(r'(?:^\t*|;\s*)([A-Za-z_]\w*):(\w*)$', line)
        if match:
            return 'function', match.group(1), match.group(2)
        # statement or device at the beginning of the line (or after ";")
        match = re.search(r'(?:^\t*|;\s*)(\w*)$', line)
        if match:
            return 'start', '', match.group(1)
        return None

    @staticmethod
    def matches(prefix: str, names: list[str]) -> list[str]:
        """
        Names that start with the prefix, then names that contain it, then names that contain its characters in this
        order (e.g. "voltS" -> "voltageSet"), ignoring case
        """

        prefix = prefix.lower()
        starting = [name for name in names if name.lower().startswith(prefix)]
        containing = [name for name in names if prefix in name.lower() and not name.lower().startswith(prefix)]
        subsequence = re.compile('.*?'.join(re.escape(char) for char in prefix))
        found = set(starting + containing)
        # best first: the characters start early and are close together ("voltS": voltageSet before configureRampVoltageSet)
        ranked = []
        for name in names:
            match = subsequence.search(name.lower()) if name not in found else None
            if match is not None:
                ranked.append((match.start(), match.end() - match.start(), len(name), name))
        return starting + containing + [name for *_, name in sorted(ranked)]

    def hideCompletion(self):
        """Hides the popup and its documentation"""

        if self.completer.popup().isVisible():
            self.completer.popup().hide()
            QToolTip.hideText()

    def updateCompletion(self, force: bool = False):
        """Shows/updates the completion popup for the text at the cursor (force: also without prefix)"""

        context = self.completionContext()
        if context is None or (not force and context[0] == 'start' and not context[2]):
            self.hideCompletion()
            return
        kind, device, prefix = context

        self.completion_model.clear()
        if kind == 'function':
            functions = self.catalog.functions(device)
            for name in self.matches(prefix, list(functions)):
                function = functions[name]
                item = QStandardItem(f'{name}({", ".join(function.parameters)})')
                item.setData(name, self.completion_role)
                item.setData(f'{name}()' if not function.parameters else f'{name}(', self.insert_role)
                item.setData('function', self.kind_role)
                item.setData(f'{device}:{name}', Qt.ItemDataRole.ToolTipRole)
                self.completion_model.appendRow(item)
        else:
            is_first_line = self.textCursor().block().blockNumber() == 0
            keywords = ['TIME'] if is_first_line else [keyword for keyword in SCRIPT_KEYWORDS if keyword != 'TIME']
            devices = [] if is_first_line else list(self.catalog.devices)
            for name in self.matches(prefix, keywords):
                item = QStandardItem(f'{name}  (statement)')
                item.setData(name, self.completion_role)
                item.setData(f'{name} ', self.insert_role)
                item.setData('keyword', self.kind_role)
                item.setData(name, Qt.ItemDataRole.ToolTipRole)
                self.completion_model.appendRow(item)
            for name in self.matches(prefix, devices):
                item = QStandardItem(f'{name}:  ({self.catalog.devices[name].__name__})')
                item.setData(name, self.completion_role)
                item.setData(f'{name}:', self.insert_role)
                item.setData('device', self.kind_role)
                item.setData(name, Qt.ItemDataRole.ToolTipRole)
                self.completion_model.appendRow(item)

        # an exact match of the only entry: nothing to complete
        if self.completion_model.rowCount() == 0 or (
            self.completion_model.rowCount() == 1 and self.completion_model.item(0).data(self.completion_role) == prefix and kind != 'function'
        ):
            self.hideCompletion()
            return

        self.completion_start = self.textCursor().position() - len(prefix)
        popup = self.completer.popup()
        rect = self.cursorRect()
        rect.setWidth(max(300, popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width() + 10))
        # the cursor rectangle is relative to the viewport (right of the line numbers)
        rect.translate(self.viewport().pos())
        self.completer.complete(rect)
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

    def insertCompletion(self, index: QModelIndex):
        """Replaces the typed prefix by the selected entry"""

        text = index.data(self.insert_role)
        kind = index.data(self.kind_role)
        if not text:
            return
        cursor = self.textCursor()
        cursor.setPosition(self.completion_start)
        cursor.setPosition(self.textCursor().position(), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        QToolTip.hideText()
        if kind == 'device':
            # continue with the functions of the device (after the completer has closed its popup)
            QTimer.singleShot(0, lambda: self.updateCompletion(force=True))
        elif kind == 'function':
            self.showCallTip()

    def showCompletionDoc(self, index: QModelIndex):
        """Documentation of the highlighted entry next to the popup"""

        popup = self.completer.popup()
        if not popup.isVisible():
            return
        html = self.documentation(index.data(Qt.ItemDataRole.ToolTipRole) or '')
        if not html:
            QToolTip.hideText()
            return
        rect = popup.visualRect(popup.currentIndex())
        QToolTip.showText(popup.mapToGlobal(QPoint(popup.width() + 4, rect.top())), html, popup)

    def documentation(self, name: str) -> str:
        """HTML documentation of "DEVICE:function", a device or a statement ('' if unknown)"""

        if name.upper() in SCRIPT_KEYWORDS:
            return f'<pre>{escape(SCRIPT_KEYWORDS[name.upper()])}</pre>'
        device, _, function_name = name.partition(':')
        if device not in self.catalog.devices:
            return ''
        if not function_name:
            return f'<b>{escape(device)}</b>: {escape(self.catalog.devices[device].__name__)}, {len(self.catalog.functions(device))} functions'
        function = self.catalog.function(device, function_name)
        if function is None:
            return ''
        return f'<b>{escape(device)}:{escape(function.name)}</b>{escape(function.signature)}<pre>{escape(function.doc)}</pre>'

    def callContext(self) -> tuple[str, str] | None:
        """(device, function) if the cursor is inside the brackets of "DEVICE:function(...", else None"""

        cursor = self.textCursor()
        line = cursor.block().text()[:cursor.positionInBlock()]
        match = re.search(r'([A-Za-z_]\w*):([A-Za-z_]\w*)\(([^()]*)$', line)
        if match is None:
            return None
        return match.group(1), match.group(2)

    def showCallTip(self):
        """Signature of the function while the arguments are typed"""

        context = self.callContext()
        function = self.catalog.function(*context) if context is not None else None
        if function is None:
            return
        position = self.viewport().mapToGlobal(self.cursorRect().bottomLeft())
        QToolTip.showText(position, self.documentation(f'{context[0]}:{context[1]}'), self)

    def keyPressEvent(self, event):
        """Keys of the completion popup, Ctrl+Space shows the completion"""

        popup = self.completer.popup()
        if popup.isVisible() and event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            # handled by the completer (enter/tab insert the selected entry, escape closes it)
            event.ignore()
            return

        if event.key() == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.updateCompletion(force=True)
            return

        super().keyPressEvent(event)

        text = event.text()
        if self.isReadOnly() or event.matches(QKeySequence.StandardKey.Undo) or event.matches(QKeySequence.StandardKey.Redo):
            return
        if text and (text.isalnum() or text in '_:') or (event.key() == Qt.Key.Key_Backspace and popup.isVisible()):
            self.updateCompletion(force=text == ':')
        else:
            self.hideCompletion()
        if text in '(,' and text:
            self.showCallTip()
        elif text == ')':
            QToolTip.hideText()

    def focusOutEvent(self, event):
        """Hides the call tip"""
        if not self.completer.popup().isVisible():
            QToolTip.hideText()
        super().focusOutEvent(event)

    def viewportEvent(self, event):
        """Tooltips: documentation of the function/device/statement under the mouse, message of a faulty line"""

        if event.type() == QEvent.Type.ToolTip:
            html = self.tooltipAt(event.pos())
            if html:
                QToolTip.showText(event.globalPos(), html, self.viewport())
            else:
                QToolTip.hideText()
            return True
        return super().viewportEvent(event)

    def tooltipAt(self, position: QPoint) -> str:
        """HTML tooltip for the text at a position of the viewport"""

        cursor = self.cursorForPosition(position)
        block = cursor.block()
        text = block.text()
        column = cursor.positionInBlock()
        line_nbr = block.blockNumber() + 1

        parts = []
        if line_nbr == self.highlighter.error_line and self.highlighter.error_message:
            parts.append(f'<span style="color: {self.highlighter.error_color.name()}">{escape(self.highlighter.error_message)}</span>')

        body = text.lstrip('\t')
        indent = len(text) - len(body)
        if body and not body.startswith('#'):
            word = body.split(' ')[0]
            if word.upper() in SCRIPT_KEYWORDS and indent <= column <= indent + len(word):
                parts.append(self.documentation(word))
            elif word.upper() not in SCRIPT_KEYWORDS:
                for match in COMMAND_PATTERN.finditer(word):
                    device, function = match.group(1), match.group(2)
                    end = indent + (match.end(2) if function else match.end(1))
                    if indent + match.start(1) <= column <= end:
                        message = self.catalog.checkCommand(device, function)
                        if message:
                            parts.append(f'<span style="color: {self.highlighter.error_color.name()}">{escape(message)}</span>')
                        else:
                            parts.append(self.documentation(f'{device}:{function}' if function else device))
        return '<br>'.join(part for part in parts if part)
