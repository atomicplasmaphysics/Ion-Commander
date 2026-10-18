import numpy as np
from math import ceil
from datetime import datetime, timedelta

import pyqtgraph as pg


from PyQt6.QtWidgets import (
    QSplitter, QWidget, QBoxLayout, QHBoxLayout, QVBoxLayout, QPushButton, QGroupBox, QListWidget, QListWidgetItem, QApplication,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import DefaultParams
from Config.StylesConf import Colors

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

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updatePreview)
        self.update_timer.setInterval(DefaultParams.update_timer_time)

        # downsampling: data is averaged in time buckets inside the database (about <points_per_pixel> points per pixel of the plot).
        # When zooming/panning, the visible range is loaded again with a finer resolution (debounced by the refine timer)
        self.points_per_pixel = 2
        self.selected_range: tuple[int, int] | None = None
        self.loaded_range: tuple[int, int] | None = None
        self.loaded_bucket = 1
        self.plotting = False
        self.event_lines: list[pg.InfiniteLine] = []

        self.refine_timer = QTimer()
        self.refine_timer.setSingleShot(True)
        self.refine_timer.setInterval(300)
        self.refine_timer.timeout.connect(self.refinePreview)

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
                list_item = QListWidgetItem(self.columnLabel(table.name, attribute))
                list_item.setToolTip(self.columnToolTip(table.name, attribute))
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

        # Auto update button
        self.auto_update_button = IndicatorLedButton('Auto update')
        self.auto_update_button.setToolTip('Will show last 10 minutes')
        self.auto_update_button.clicked.connect(self.autoUpdate)
        self.export_title_hbox.addWidget(self.auto_update_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Update preview button
        self.button_update_preview = QPushButton('Update Preview')
        self.button_update_preview.setToolTip('Loads the selected data. Long time ranges are averaged (downsampled) - zoom in to see all data points')
        self.button_update_preview.clicked.connect(self.updatePreview)
        self.export_title_hbox.addWidget(self.button_update_preview, alignment=Qt.AlignmentFlag.AlignLeft)

        # Start time widget
        self.start_datetime_label = QLabel('Start time:')
        self.export_title_hbox.addWidget(self.start_datetime_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.start_datetime_widget = DateTimeEdit(
            popup_title='Select date-time for start',
            timestamp=datetime.now() - timedelta(days=30)
        )
        self.start_datetime_widget.setToolTip('Start of the time range')
        self.export_title_hbox.addWidget(self.start_datetime_widget, alignment=Qt.AlignmentFlag.AlignLeft)

        # End time widget
        self.end_datetime_label = QLabel('End time:')
        self.export_title_hbox.addWidget(self.end_datetime_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.end_datetime_widget = DateTimeEdit(
            popup_title='Select date-time for end',
            timestamp=datetime.now(),
            now_button=True
        )
        self.end_datetime_widget.setToolTip('End of the time range')
        self.export_title_hbox.addWidget(self.end_datetime_widget, alignment=Qt.AlignmentFlag.AlignLeft)

        self.export_title_hbox.addStretch()

        # Events button
        self.button_events_preview = IndicatorLedButton('Events', initial_state=True)
        self.button_events_preview.setToolTip('Mark events (interlock trips, lost connections, ...) as vertical lines')
        self.button_events_preview.clicked.connect(self.updateEvents)
        self.export_title_hbox.addWidget(self.button_events_preview, alignment=Qt.AlignmentFlag.AlignRight)

        # Resolution label
        self.label_resolution = QLabel('')
        self.label_resolution.setToolTip('Resolution of the shown data. Zoom in to load the data with a finer resolution.')
        self.export_title_hbox.addWidget(self.label_resolution, alignment=Qt.AlignmentFlag.AlignRight)

        # Y-log button
        self.button_log_y_preview = IndicatorLedButton('Log-y')
        self.button_log_y_preview.setToolTip('Logarithmic y-axis')
        self.button_log_y_preview.clicked.connect(self.logYAxis)
        self.export_title_hbox.addWidget(self.button_log_y_preview, alignment=Qt.AlignmentFlag.AlignRight)

        # Plotting canvas
        self.time_canvas = TimeCanvas([], grid=True)
        self.time_canvas.getViewBox().sigXRangeChanged.connect(self.viewRangeChanged)
        self.preview_export_vbox.addWidget(self.time_canvas)

        self.export_hbox = QHBoxLayout()
        self.export_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.preview_export_vbox.addLayout(self.export_hbox)

        # Exporting path
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
        self.file_path.setToolTip('CSV file for the export')
        self.export_hbox.addWidget(self.file_path, alignment=Qt.AlignmentFlag.AlignLeft)

        # Exporting button
        self.export_button = QPushButton('Export')
        self.export_button.setToolTip('Export selected data to selected file (full resolution, not downsampled)')
        self.export_button.clicked.connect(self.exportData)
        self.export_hbox.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.export_hbox.addStretch()

        self.splitter.addWidget(self.preview_export_widget)

        # Division between columns  # TODO: does not really work as intended
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(0, 95)

    def columnLabel(self, table_name: str, column_name: str, with_unit: bool = True) -> str:
        """
        Returns the current label of a database column (falls back to the column name)

        :param table_name: name of table
        :param column_name: name of column
        :param with_unit: append unit in brackets
        """

        label, unit = self.database.getLabels(table_name).get(column_name, (column_name, ''))
        if with_unit and unit:
            return f'{label} [{unit}]'
        return label

    def columnToolTip(self, table_name: str, column_name: str) -> str:
        """
        Returns tooltip of a database column with its stable id and all previous labels

        :param table_name: name of table
        :param column_name: name of column
        """

        tooltip = f'Database column: {table_name}.{column_name}'
        label_history = self.database.getLabelHistory(table_name, column_name)
        if len(label_history) > 1:
            tooltip += '\nPrevious names:'
            # every label is valid from its timestamp until the timestamp of the next label
            for (_, label, _), (next_timestamp, _, _) in zip(label_history[:-1], label_history[1:]):
                tooltip += f'\n  {label} (until {datetime.fromtimestamp(next_timestamp):%Y-%m-%d %H:%M})'
        return tooltip

    def selectAll(self, listwidget_index: int, state: Qt.CheckState):
        """
        Selects all inside given listwidget

        :param listwidget_index: index of listwidget
        :param state: state of buttons
        """

        for row in range(self.selection_listwidgets[listwidget_index].count()):
            self.selection_listwidgets[listwidget_index].item(row).setCheckState(state)

    def getTimeRange(self) -> tuple[int, int] | None:
        """Returns the selected (start, end) timestamps or None (with a message box) if they are invalid"""

        start_time = int(self.start_datetime_widget.getTime().timestamp())
        end_time = int(self.end_datetime_widget.getTime().timestamp())

        if end_time <= start_time:
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'End time before start time!',
                f'The selected end time ({datetime.fromtimestamp(end_time)}) is before the selected start time ({datetime.fromtimestamp(start_time)})'
            )
            return None
        return start_time, end_time

    def getSeries(self, start_time: int, end_time: int, bucket_seconds: int = 1) -> list[tuple[str, np.ndarray, np.ndarray]]:
        """
        Gets checked data as separate series (no merging, so no gaps are filled with nan)

        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        :param bucket_seconds: average data in time buckets of this size
        :returns: list of (label, time, values)
        """

        series = []
        for i, table in enumerate(self.database.tables):
            checked = [0]
            for row in range(len(table.structure) - 1):
                if self.selection_listwidgets[i].item(row).checkState() == Qt.CheckState.Checked:
                    checked.append(row + 1)
            if len(checked) < 2:
                continue

            data = self.database.getData(i, tuple(checked), start_time, end_time, bucket_seconds)
            if data is False:
                continue
            column_names, column_values = data
            column_values = column_values.astype(float)

            for column, column_name in enumerate(column_names[1:], start=1):
                series.append((f'{table.name}: {self.columnLabel(table.name, column_name)}', column_values[:, 0], column_values[:, column]))
        return series

    def getData(self) -> tuple[np.ndarray, list[str]]:
        """Gets checked data in full resolution, merged into one array (for exporting)"""

        time_range = self.getTimeRange()
        if time_range is None:
            return np.array([]), []
        start_time, end_time = time_range

        datas = []
        labels = []

        for i, table in enumerate(self.database.tables):
            checked = [0]
            table_labels = []
            for row, attribute in enumerate(list(table.structure.keys())[1:]):
                if self.selection_listwidgets[i].item(row).checkState() == Qt.CheckState.Checked:
                    table_labels.append(f'{table.name}_{attribute}')
                    checked.append(row + 1)
            if not checked:
                continue
            data = self.database.getData(self.database.tables.index(table), tuple(checked), start_time, end_time)

            if data is False:
                continue
            column_names, column_values = data

            labels.extend([f'{table.name}: {self.columnLabel(table.name, column_name)}' for column_name in column_names[1:]])
            datas.append(column_values)

        if not labels:
            return np.array([]), []
        labels.insert(0, 'Time')

        return mergeArraysFirstColumn(datas), labels

    def bucketFor(self, time_span: float) -> int:
        """
        Returns the size of the time buckets (in s) to show about <points_per_pixel> points per pixel of the plot

        :param time_span: shown time span in s
        """

        pixels = max(self.time_canvas.getViewBox().width(), 200)
        return max(1, int(ceil(time_span / (pixels * self.points_per_pixel))))

    def plotSeries(self, start_time: int, end_time: int, bucket_seconds: int) -> bool:
        """
        Loads and plots the checked data in the given range. The x-range of the plot is not changed.

        :returns: True if data was plotted
        """

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.plotting = True
        try:
            self.time_canvas.clean()
            series = self.getSeries(start_time, end_time, bucket_seconds)
            for label, x, y in series:
                self.time_canvas.plot(x, y, label=label, plot_params={'connect': 'finite'})
                # clipping and peak-downsampling of pyqtgraph keep the rendering fast and spikes visible
                # (must be set after the curve was added to the plot)
                self.time_canvas.graph_curves[-1].setClipToView(True)
                self.time_canvas.graph_curves[-1].setDownsampling(auto=True, method='peak')

            self.loaded_range = (start_time, end_time)
            self.loaded_bucket = bucket_seconds
            self.label_resolution.setText(f'Resolution: {bucket_seconds} s' if bucket_seconds > 1 else 'Resolution: all data')
        finally:
            self.plotting = False
            QApplication.restoreOverrideCursor()

        return bool(series)

    def updatePreview(self):
        """Updates the preview with given data"""

        if self.auto_update_button.value():
            self.start_datetime_widget.setTime(datetime.now() - timedelta(minutes=10))
            self.end_datetime_widget.setTime(datetime.now())

        time_range = self.getTimeRange()
        if time_range is None:
            return
        start_time, end_time = time_range

        self.selected_range = time_range
        if not self.plotSeries(start_time, end_time, self.bucketFor(end_time - start_time)):
            self.writeStatusBar('No data selected or no datapoints available')

        self.plotting = True
        self.time_canvas.setXRange(start_time, end_time, padding=0)
        self.plotting = False
        self.updateEvents()

    def viewRangeChanged(self, *args):
        """Called when the visible x-range changes (zoom/pan)"""

        if self.plotting or self.selected_range is None or self.auto_update_button.value():
            return
        self.refine_timer.start()

    def refinePreview(self):
        """Loads the visible range again if a finer (zoomed in) or coarser (zoomed out) resolution is needed"""

        if self.selected_range is None or self.loaded_range is None:
            return

        view_start, view_end = self.time_canvas.getViewBox().viewRange()[0]
        view_start = max(view_start, self.selected_range[0])
        view_end = min(view_end, self.selected_range[1])
        if view_end <= view_start:
            return

        wanted_bucket = self.bucketFor(view_end - view_start)
        covered = self.loaded_range[0] <= view_start and view_end <= self.loaded_range[1]
        finer_needed = wanted_bucket * 2 <= self.loaded_bucket
        coarser_needed = wanted_bucket >= self.loaded_bucket * 4
        if covered and not finer_needed and not coarser_needed:
            return

        # load a bit more than visible, so small pans do not need to load again
        margin = (view_end - view_start) * 0.5
        load_start = int(max(self.selected_range[0], view_start - margin))
        load_end = int(min(self.selected_range[1], view_end + margin))
        self.plotSeries(load_start, load_end, wanted_bucket)

    def updateEvents(self):
        """Marks the events of the selected time range as vertical lines"""

        for line in self.event_lines:
            self.time_canvas.plotItem.removeItem(line)
        self.event_lines = []

        if not self.button_events_preview.value() or self.selected_range is None:
            return

        for timestamp, source, event_type, message, value in self.database.getEvents(*self.selected_range):
            color = Colors.color_red if 'interlock' in event_type else Colors.color_orange
            line = pg.InfiniteLine(
                pos=timestamp,
                angle=90,
                movable=False,
                pen=pg.mkPen(color=color, width=1, style=Qt.PenStyle.DashLine),
                label=f'{source}: {event_type}',
                labelOpts={'position': 0.95, 'color': color, 'rotateAxis': (1, 0), 'anchors': [(0, 0), (0, 0)]}
            )
            line.setToolTip(f'{datetime.fromtimestamp(timestamp):%Y-%m-%d %H:%M:%S} {source} {event_type}\n{message}')
            self.time_canvas.plotItem.addItem(line, ignoreBounds=True)
            self.event_lines.append(line)

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

    def autoUpdate(self):
        """Automatically updates graphs"""

        auto_update_status = self.auto_update_button.value()

        self.button_update_preview.setDisabled(auto_update_status)
        self.start_datetime_widget.setDisabled(auto_update_status)
        self.end_datetime_widget.setDisabled(auto_update_status)

        if auto_update_status:
            self.update_timer.start()
        else:
            self.update_timer.stop()

    def logYAxis(self):
        """Updates the y-axis to be logarithmic or normal"""

        self.time_canvas.setLogY(self.button_log_y_preview.value())
