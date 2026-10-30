from typing import NamedTuple


from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPalette
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QMessageBox, QAbstractItemView


class DifferenceViolation(NamedTuple):
    """Potential difference between two channels that is larger than allowed"""
    channel: int  # channel that is set
    other: int  # other channel
    potential: float  # new potential of the channel in V
    other_potential: float  # potential of the other channel in V
    difference: float  # absolute difference in V
    limit: float  # allowed absolute difference in V


def differenceKey(channel_a: int, channel_b: int) -> tuple[int, int]:
    """Key of a channel pair in the limits (smaller channel first)"""
    return min(channel_a, channel_b), max(channel_a, channel_b)


def checkDifferences(channel: int, potential: float, potentials: list[float], limits: dict[tuple[int, int], float]) -> list[DifferenceViolation]:
    """
    Checks the potential differences of a channel to all other channels

    Example: limit DT1<->DT2 = 500 V, DT2 at 0 V, DT1 is set to 600 V -> difference 600 V is too large

    :param channel: channel that is set
    :param potential: new potential of the channel in V (with sign)
    :param potentials: current potentials of all channels in V (with sign), the entry of the channel is ignored
    :param limits: {(channel a, channel b): maximum absolute difference in V}, pairs without limit are not checked
    :returns: violated limits (empty if everything is allowed)
    """

    violations = []
    for other, other_potential in enumerate(potentials):
        if other == channel:
            continue
        limit = limits.get(differenceKey(channel, other))
        if limit is None:
            continue
        difference = abs(potential - other_potential)
        # small tolerance for the rounding of the input fields
        if difference > limit + 1E-6:
            violations.append(DifferenceViolation(channel, other, potential, other_potential, difference, limit))
    return violations


def formatVoltage(voltage: float) -> str:
    """Short text of a voltage ("600 V", "-1500.5 V")"""
    return f'{voltage:.6g} V'


class DifferenceAnswer:
    """Answers of the warning dialog <askDifferenceViolation>"""
    set_anyway = 'set'
    abort = 'abort'
    edit_limits = 'edit'


def askDifferenceViolation(parent, names: list[str], violations: list[DifferenceViolation]) -> str:
    """
    Warning dialog if a voltage would exceed allowed potential differences: set anyway, abort or edit the limits

    :param parent: parent widget
    :param names: names of the channels
    :param violations: violated limits of one channel (see <checkDifferences>)
    :returns: <DifferenceAnswer> (abort if the dialog is closed)
    """

    channel = violations[0].channel
    lines = [
        f'<li>{names[violation.other]} ({formatVoltage(violation.other_potential)}): difference '
        f'<b>{formatVoltage(violation.difference)}</b>, allowed {formatVoltage(violation.limit)}</li>'
        for violation in violations
    ]

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle('Potential difference too large!')
    msg_box.setText(f'Setting <b>{names[channel]}</b> to <b>{formatVoltage(violations[0].potential)}</b> exceeds the allowed potential difference:')
    msg_box.setInformativeText(
        f'<ul>{"".join(lines)}</ul>'
        'The voltage is only sent with "Set anyway". "Abort" restores the previous value.'
    )
    button_set = msg_box.addButton('Set anyway', QMessageBox.ButtonRole.AcceptRole)
    button_set.setToolTip('Send the voltage to the device although the difference is too large')
    button_edit = msg_box.addButton('Edit limits...', QMessageBox.ButtonRole.ActionRole)
    button_edit.setToolTip('Open the table of the allowed potential differences in the preferences (checked again afterwards)')
    button_abort = msg_box.addButton('Abort', QMessageBox.ButtonRole.RejectRole)
    button_abort.setToolTip('Do not set the voltage, the previous value is restored')
    msg_box.setDefaultButton(button_abort)
    msg_box.setEscapeButton(button_abort)
    msg_box.exec()

    clicked = msg_box.clickedButton()
    if clicked is button_set:
        return DifferenceAnswer.set_anyway
    if clicked is button_edit:
        return DifferenceAnswer.edit_limits
    return DifferenceAnswer.abort


class PotentialDifferenceTable(QWidget):
    """
    Table of the allowed absolute potential differences between channels (upper triangle, empty cell: no limit)
    with a checkbox to switch the check off

    :param names: names of the channels
    :param enabled: check enabled
    :param limits: {(channel a, channel b): maximum absolute difference in V}
    :param parent: parent widget
    """

    def __init__(self, names: list[str], enabled: bool, limits: dict[tuple[int, int], float], parent=None):
        super().__init__(parent)
        self.names = names

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.checkbox_enabled = QCheckBox('Check the potential differences when a voltage is set')
        self.checkbox_enabled.setToolTip(
            'On: setting a voltage that exceeds an allowed difference shows a warning (set anyway, abort or edit the limits).\n'
            'Off: the table is ignored.'
        )
        self.checkbox_enabled.setChecked(enabled)
        self.checkbox_enabled.toggled.connect(self.updateEnabled)
        self.main_layout.addWidget(self.checkbox_enabled)

        info = QLabel(
            'Maximum absolute voltage difference between two channels in V (empty: no limit). '
            'The set values are compared, a channel of a negative module (e.g. the cathode) counts as negative potential. '
            'Applied immediately after saving.'
        )
        info.setWordWrap(True)
        self.main_layout.addWidget(info)

        count = len(names)
        self.table = QTableWidget(count - 1, count - 1)
        # rows: first channel (all but the last one), columns: second channel (all but the first one)
        self.table.setVerticalHeaderLabels(names[:-1])
        self.table.setHorizontalHeaderLabels(names[1:])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setToolTip('Maximum absolute voltage difference between the channel of the row and the channel of the column in V (empty: no limit)')

        # tint of the text color on the background: visible in the light and the dark theme
        base, text = self.palette().color(QPalette.ColorRole.Base), self.palette().color(QPalette.ColorRole.Text)
        disabled_brush = QBrush(QColor(*(round(0.8 * b + 0.2 * t) for b, t in zip(base.getRgb()[:3], text.getRgb()[:3]))))
        for row in range(count - 1):
            for column in range(count - 1):
                channel_a, channel_b = row, column + 1
                item = QTableWidgetItem()
                if channel_b <= channel_a:
                    # lower triangle: the pair is already in the upper triangle
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    item.setBackground(disabled_brush)
                    item.setText('–')
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    limit = limits.get((channel_a, channel_b))
                    item.setText('' if limit is None else f'{limit:g}')
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setToolTip(f'Maximum |U({names[channel_a]}) - U({names[channel_b]})| in V (empty: no limit)')
                self.table.setItem(row, column, item)

        # show all rows without scrolling
        height = self.table.horizontalHeader().height() + 2 * self.table.frameWidth()
        height += sum(self.table.rowHeight(row) for row in range(self.table.rowCount()))
        self.table.setMinimumHeight(height)
        self.table.setMaximumHeight(height)
        self.main_layout.addWidget(self.table)

        self.updateEnabled(enabled)

    def updateEnabled(self, enabled: bool):
        """The table is greyed out if the check is off"""
        self.table.setEnabled(enabled)

    def enabled(self) -> bool:
        """Check enabled"""
        return self.checkbox_enabled.isChecked()

    def limits(self) -> tuple[dict[tuple[int, int], float], list[str]]:
        """
        Entered limits and errors (invalid cells are marked red)

        :returns: ({(channel a, channel b): limit in V}, list of error messages)
        """

        limits = {}
        errors = []
        count = len(self.names)
        for row in range(count - 1):
            for column in range(row, count - 1):
                channel_a, channel_b = row, column + 1
                item = self.table.item(row, column)
                text = item.text().strip().replace(',', '.')
                item.setBackground(QBrush())
                if not text:
                    continue
                try:
                    limit = float(text)
                    if limit < 0:
                        raise ValueError
                except ValueError:
                    errors.append(f'{self.names[channel_a]} - {self.names[channel_b]}: "{item.text()}" is not a voltage >= 0')
                    item.setBackground(QBrush(Qt.GlobalColor.red))
                    continue
                limits[(channel_a, channel_b)] = limit
        return limits, errors
