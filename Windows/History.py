import numpy as np
from datetime import datetime, timedelta


from PyQt6.QtWidgets import (
    QSplitter, QWidget, QBoxLayout, QHBoxLayout, QVBoxLayout, QPushButton, QGroupBox, QListWidget, QListWidgetItem, QApplication,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt


from DB.db import DB

from Utility.Functions import mergeArraysFirstColumn
from Utility.FileDialogs import selectFileDialog
from Utility.Dialogs import showMessageBox
from Utility.Layouts import TabWidget, TimeCanvas, IndicatorLedButton, DateTimeEdit, FilePath


class HistoryWindow(TabWidget):
    """
    Widget for displaying parameter histories

    :param parent: parent widget
    """

    def __init__(self, parent, database: DB):
        super().__init__(parent)

        self.database = database

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        # SPLITTER
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        # PARAMETER SELECTION
        self.selection_widget = QWidget()
        self.selection_hbox = QHBoxLayout()
        self.selection_widget.setLayout(self.selection_hbox)

        self.selection_listwidgets: list[QListWidget] = []

        for i, table in enumerate(self.database.tables):
            selection_groupbox = QGroupBox(table.name)
            self.selection_hbox.addWidget(selection_groupbox)

            selection_groupbox_vbox = QVBoxLayout()
            selection_groupbox.setLayout(selection_groupbox_vbox)

            selection_button_widget_hbox = QHBoxLayout()
            selection_groupbox_vbox.addLayout(selection_button_widget_hbox)

            button_select_all = QPushButton('Select all')
            button_select_all.clicked.connect(lambda _, idx=i: self.selectAll(idx, Qt.CheckState.Checked))
            selection_button_widget_hbox.addWidget(button_select_all)
            button_deselect_all = QPushButton('Deselect all')
            button_deselect_all.clicked.connect(lambda _, idx=i: self.selectAll(idx, Qt.CheckState.Unchecked))
            selection_button_widget_hbox.addWidget(button_deselect_all)

            selection_listwidget = QListWidget()
            self.selection_listwidgets.append(selection_listwidget)
            selection_groupbox_vbox.addWidget(selection_listwidget)

            for attribute in list(table.structure.keys())[1:]:
                list_item = QListWidgetItem(attribute)
                list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                list_item.setCheckState(Qt.CheckState.Unchecked)
                selection_listwidget.addItem(list_item)

        self.splitter.addWidget(self.selection_widget)

        # PREVIEW AND EXPORT
        self.preview_export_widget = QWidget()
        self.preview_export_vbox = QVBoxLayout()
        self.preview_export_widget.setLayout(self.preview_export_vbox)

        self.export_title_hbox = QHBoxLayout()
        self.export_title_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.preview_export_vbox.addLayout(self.export_title_hbox)

        self.button_update_preview = QPushButton('Update Preview')
        self.button_update_preview.setToolTip('Might take some time, since all data will be previewed')
        self.button_update_preview.clicked.connect(self.updatePreview)
        self.export_title_hbox.addWidget(self.button_update_preview, alignment=Qt.AlignmentFlag.AlignLeft)

        self.start_datetime_label = QLabel('Start time:')
        self.export_title_hbox.addWidget(self.start_datetime_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.start_datetime_widget = DateTimeEdit(
            popup_title='Select date-time for start',
            timestamp=datetime.now() - timedelta(days=30)
        )
        self.export_title_hbox.addWidget(self.start_datetime_widget, alignment=Qt.AlignmentFlag.AlignLeft)

        self.end_datetime_label = QLabel('End time:')
        self.export_title_hbox.addWidget(self.end_datetime_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.end_datetime_widget = DateTimeEdit(
            popup_title='Select date-time for end',
            timestamp=datetime.now()
        )
        self.export_title_hbox.addWidget(self.end_datetime_widget, alignment=Qt.AlignmentFlag.AlignLeft)

        self.export_title_hbox.addStretch()
        
        self.button_log_y_preview = IndicatorLedButton('Log-y')
        self.button_log_y_preview.clicked.connect(self.logYAxis)
        self.export_title_hbox.addWidget(self.button_log_y_preview, alignment=Qt.AlignmentFlag.AlignRight)

        self.time_canvas = TimeCanvas([], grid=True)
        self.preview_export_vbox.addWidget(self.time_canvas)

        self.export_hbox = QHBoxLayout()
        self.export_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.preview_export_vbox.addLayout(self.export_hbox)

        self.file_path_label = QLabel('File path:')
        self.export_hbox.addWidget(self.file_path_label)
        self.file_path = FilePath(
            placeholder='Select file path for saving',
            function=lambda: selectFileDialog(
                self,
                for_saving=True,
                instruction='Select output file for export',
                file_filter='*.csv'
            )
        )
        self.export_hbox.addWidget(self.file_path, alignment=Qt.AlignmentFlag.AlignLeft)

        self.export_button = QPushButton('Export')
        self.export_button.setToolTip('Export selected data to selected file')
        self.export_button.clicked.connect(self.exportData)
        self.export_hbox.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.export_hbox.addStretch()

        self.splitter.addWidget(self.preview_export_widget)

        # Division between columns
        self.splitter.setStretchFactor(0, 30)
        self.splitter.setStretchFactor(0, 70)

    def selectAll(self, listwidget_index: int, state: Qt.CheckState):
        """
        Selects all inside given listwidget

        :param listwidget_index: index of listwidget
        :param state: state of buttons
        """

        for row in range(self.selection_listwidgets[listwidget_index].count()):
            self.selection_listwidgets[listwidget_index].item(row).setCheckState(state)

    def getData(self) -> tuple[np.ndarray, list[str]]:
        """Gets checked data"""

        start_time = int(self.start_datetime_widget.getTime().timestamp())
        end_time = int(self.end_datetime_widget.getTime().timestamp())

        if end_time <= start_time:
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'End time before start time!',
                f'The selected end time ({datetime.fromtimestamp(end_time)}) is before the selected start time ({datetime.fromtimestamp(start_time)})'
            )
            return np.array([]), []

        datas = []
        labels = []

        for i, table in enumerate(self.database.tables):
            checked = []
            for row, attribute in enumerate(list(table.structure.keys())[1:]):
                if self.selection_listwidgets[i].item(row).checkState() == Qt.CheckState.Checked:
                    labels.append(f'{table.name}_{attribute}')
                    checked.append(row + 1)
            if not checked:
                continue
            data = self.database.getData(self.database.tables.index(table), start_time, end_time)

            checked.insert(0, 0)
            datas.append(data[:, checked])

        if not labels:
            return np.array([]), []
        labels.insert(0, 'Time')

        return mergeArraysFirstColumn(datas), labels

    def updatePreview(self):
        """Updates the preview with given data"""

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.time_canvas.clean()
        data, labels = self.getData()

        if len(labels) < 2:
            self.writeStatusBar('No data selected')
        else:
            for i in range(1, len(labels)):
                self.time_canvas.plot(data[:, 0], data[:, i], label=labels[i])

            self.time_canvas.setXRange(np.min(data[:, 0]), np.max(data[:, 0]))

        QApplication.restoreOverrideCursor()

    def exportData(self):
        """Exports the data"""

        if not self.file_path.path:
            showMessageBox(
                None,
                QMessageBox.Icon.Information,
                'File path missing!',
                'There is no file path selected for exporting!'
            )
            self.writeStatusBar('Exporting aborted')
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        data, labels = self.getData()

        if len(labels) < 2:
            self.writeStatusBar('No data selected')
        else:
            try:
                np.savetxt(self.file_path.path, data, delimiter=',', header=','.join(labels), encoding='utf-8')
                self.writeStatusBar('Exported successfully')
            except FileNotFoundError as error:
                showMessageBox(
                    None,
                    QMessageBox.Icon.Warning,
                    'File path not found!',
                    f'The given file path "{self.file_path.path}" can not be opened',
                    str(error)
                )
                self.writeStatusBar('Exporting aborted')

        QApplication.restoreOverrideCursor()

    def logYAxis(self):
        """Updates the y-axis to be logarithmic or normal"""

        self.time_canvas.setLogY(self.button_log_y_preview.value())
