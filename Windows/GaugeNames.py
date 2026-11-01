from datetime import datetime


from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QInputDialog,
    QMessageBox, QDialogButtonBox, QLabel
)


from DB.db import DB

from Utility.Dialogs import showMessageBox


class GaugeNamesDialog(QDialog):
    """
    Dialog to assign the readings of the pressure gauges to names (e.g. chambers): which name a gauge had at which time.
    Only the names in the database change, the readings stay. Nothing is stored until the dialog is accepted.

    :param database: database
    :param gauges: list of (table name, column name, text of gauge, current name in the pressure panel or None if the gauge is not shown)
    """

    time_format = '%Y-%m-%d %H:%M'

    def __init__(self, database: DB, gauges: list[tuple[str, str, str, str | None]]):
        super().__init__()
        self.setWindowTitle('Pressure gauge names')
        self.resize(720, 500)

        self.database = database
        self.gauge_texts = {(table, column): text for table, column, text, _ in gauges}
        self.live_names = {(table, column): name for table, column, _, name in gauges if name is not None}

        # {(table, column): [[time, label, unit], ...]}
        self.histories = {}
        for table, column, _, _ in gauges:
            history = [list(entry) for entry in database.getLabelHistory(table, column)]
            if history:
                self.histories[(table, column)] = history
        self.original_histories = {key: [list(entry) for entry in history] for key, history in self.histories.items()}

        # (key of history, index in history) of every row of the table
        self.rows: list[tuple[tuple[str, str], int]] = []

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.addWidget(QLabel(
            'Which name a gauge had at which time. Every name is its own entry in the History tab.\n'
            'The same name on several rows is shown as one curve. The readings in the database are never changed.'
        ))

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Gauge', 'Name', 'From', 'Until'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.updateButtons)
        self.main_layout.addWidget(self.table)

        self.buttons_hbox = QHBoxLayout()
        self.main_layout.addLayout(self.buttons_hbox)

        self.button_rename = QPushButton('Assign name...')
        self.button_rename.setToolTip('Gives this time of the gauge a different name. Select an existing name to combine them')
        self.button_rename.clicked.connect(self.assignName)
        self.buttons_hbox.addWidget(self.button_rename)

        self.button_split = QPushButton('New name from...')
        self.button_split.setToolTip('The gauge has a new name from a date on, e.g. it moved to a new chamber at that time')
        self.button_split.clicked.connect(self.newNameFrom)
        self.buttons_hbox.addWidget(self.button_split)

        self.button_start = QPushButton('Change start...')
        self.button_start.setToolTip('Changes the date from which this name is valid, the name before it ends at this date')
        self.button_start.clicked.connect(self.changeStart)
        self.buttons_hbox.addWidget(self.button_start)

        self.button_delete = QPushButton('Delete name')
        self.button_delete.setToolTip(
            'Removes the name of this time (e.g. a test), it is not shown in the History tab anymore.\n'
            'The readings stay in the database without a name and can get a name again here.'
        )
        self.button_delete.clicked.connect(self.deleteName)
        self.buttons_hbox.addWidget(self.button_delete)
        self.buttons_hbox.addStretch(1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)

        self.updateTable()

    def timeText(self, timestamp: int | None, empty: str) -> str:
        """
        Returns the text of a time

        :param timestamp: timestamp
        :param empty: text for the beginning (0) or the end (None)
        """

        return datetime.fromtimestamp(timestamp).strftime(self.time_format) if timestamp else empty

    def updateTable(self, selected: tuple[tuple[str, str], int] | None = None):
        """
        Combines neighbouring rows with the same name and shows all rows

        :param selected: (key of history, index in history) of the row to select
        """

        self.rows = []
        self.table.setRowCount(0)
        for key, history in self.histories.items():
            history[:] = [entry for index, entry in enumerate(history) if index == 0 or entry[1] != history[index - 1][1]]
            for index, (time, label, _) in enumerate(history):
                until = history[index + 1][0] if index + 1 < len(history) else None
                texts = (self.gauge_texts[key], label or '(no name)', self.timeText(time, 'beginning'), self.timeText(until, 'now'))
                row = self.table.rowCount()
                self.table.insertRow(row)
                for column, text in enumerate(texts):
                    self.table.setItem(row, column, QTableWidgetItem(text))
                self.rows.append((key, index))

        self.table.resizeColumnsToContents()
        if selected is not None and selected[0] in self.histories:
            selected = (selected[0], min(selected[1], len(self.histories[selected[0]]) - 1))
            self.table.selectRow(self.rows.index(selected))
        self.updateButtons()

    def selectedRow(self) -> tuple[tuple[str, str], int] | None:
        """Returns (key of history, index in history) of the selected row"""

        row = self.table.currentRow()
        return self.rows[row] if self.table.selectedItems() and 0 <= row < len(self.rows) else None

    def updateButtons(self):
        """Enables the buttons that can be used for the selected row"""

        selected = self.selectedRow()
        self.button_rename.setEnabled(selected is not None)
        self.button_split.setEnabled(selected is not None)
        self.button_start.setEnabled(selected is not None and selected[1] > 0)
        self.button_delete.setEnabled(selected is not None and bool(self.histories[selected[0]][selected[1]][1]) and not self.isLive(*selected))

    def isLive(self, key: tuple[str, str], index: int) -> bool:
        """
        Returns if a row is the current name of a gauge in the pressure panel (this name can be changed, but not deleted)

        :param key: key of history
        :param index: index in history
        """

        return key in self.live_names and index == len(self.histories[key]) - 1

    def askName(self, title: str, text: str, current: str = '') -> str | None:
        """
        Asks for a name, existing names can be selected

        :param title: title of dialog
        :param text: text of dialog
        :param current: preselected name
        :returns: name or None if cancelled
        """

        names = sorted({entry[1] for history in self.histories.values() for entry in history if entry[1]})
        if current not in names:
            names.insert(0, current)
        name, ok = QInputDialog.getItem(self, title, text, names, names.index(current), True)
        name = name.strip()
        return name if ok and name else None

    def askTime(self, title: str, text: str, minimum: int, maximum: int | None, current: int | None = None) -> int | None:
        """
        Asks for a date and time between two times

        :param title: title of dialog
        :param text: text of dialog
        :param minimum: time has to be after this one
        :param maximum: time has to be before this one (None: before now)
        :param current: preselected time
        :returns: timestamp or None if cancelled or invalid
        """

        maximum = maximum if maximum is not None else int(datetime.now().timestamp())
        answer, ok = QInputDialog.getText(
            self,
            title,
            f'{text}\nFormat: YYYY-MM-DD HH:MM, between {self.timeText(minimum, "beginning")} and {self.timeText(maximum, "now")}',
            text=self.timeText(current, '') if current else ''
        )
        if not ok:
            return None

        try:
            timestamp = int(datetime.strptime(answer.strip(), self.time_format).timestamp())
        except (ValueError, OSError):
            showMessageBox(None, QMessageBox.Icon.Warning, 'Invalid date!', f'"{answer}" is not a date in the format YYYY-MM-DD HH:MM.')
            return None

        if not minimum < timestamp < maximum:
            showMessageBox(None, QMessageBox.Icon.Warning, 'Invalid date!', f'The date has to be between {self.timeText(minimum, "the beginning")} and {self.timeText(maximum, "now")}.')
            return None
        return timestamp

    def assignName(self):
        """Gives the selected row a different name"""

        key, index = self.selectedRow()
        name = self.askName('Assign name', f'Name of {self.gauge_texts[key]} in this time:', self.histories[key][index][1])
        if name is not None:
            self.histories[key][index][1] = name
            self.updateTable((key, index))

    def newNameFrom(self):
        """Splits the selected row: a new name from a date on"""

        key, index = self.selectedRow()
        history = self.histories[key]
        time = self.askTime('New name from', 'From which date on does the gauge have a new name?', history[index][0], history[index + 1][0] if index + 1 < len(history) else None)
        if time is None:
            return
        name = self.askName('New name from', f'Name of {self.gauge_texts[key]} from {self.timeText(time, "")} on:')
        if name is not None:
            history.insert(index + 1, [time, name, history[index][2]])
            self.updateTable((key, index + 1))

    def changeStart(self):
        """Moves the start of the selected row"""

        key, index = self.selectedRow()
        history = self.histories[key]
        time = self.askTime(
            'Change start',
            f'From which date on is "{history[index][1] or "(no name)"}" valid?',
            history[index - 1][0],
            history[index + 1][0] if index + 1 < len(history) else None,
            history[index][0]
        )
        if time is not None:
            history[index][0] = time
            self.updateTable((key, index))

    def deleteName(self):
        """Removes the name of the selected row"""

        key, index = self.selectedRow()
        self.histories[key][index][1] = ''
        self.updateTable((key, index))

    def currentNames(self) -> dict[tuple[str, str], str]:
        """Returns the current names of the gauges in the pressure panel as {(table name, column name): name}"""
        return {key: self.histories[key][-1][1] for key in self.live_names if key in self.histories}

    def save(self):
        """Stores the changed names and closes the dialog"""

        names = list(self.currentNames().values())
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            showMessageBox(None, QMessageBox.Icon.Warning, 'Name already used!', f'Gauges in the pressure panel can not have the same current name: {", ".join(duplicates)}')
            return

        failed = False
        for key, history in self.histories.items():
            if history != self.original_histories[key]:
                failed = not self.database.setLabelHistory(*key, [tuple(entry) for entry in history]) or failed
        if failed:
            showMessageBox(None, QMessageBox.Icon.Critical, 'Names not stored!', 'Not all names could be stored in the database, see the log.')
        self.accept()
