import re
import numpy as np
from math import ceil
from datetime import datetime, timedelta

import pyqtgraph as pg


from PyQt6.QtWidgets import (
    QSplitter, QWidget, QBoxLayout, QHBoxLayout, QVBoxLayout, QPushButton, QGroupBox, QListWidget, QListWidgetItem, QApplication,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Utility.Functions import mergeArraysFirstColumn
from Utility.FileDialogs import selectFileDialog
from Utility.Dialogs import showMessageBox
from Utility.Layouts import TabWidget, TimeCanvas, IndicatorLedButton, DateTimeEdit, FilePath, ComboBox
from Utility.PressureFit import FIT_MODELS, FINAL_VALUE_MODELS, PressureFitResult, formatDuration


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
        self.envelope_items: list = []
        self.current_series: list[tuple[str, np.ndarray, np.ndarray]] = []
        self.fit_items: list = []

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

            # tables with names get one entry per name (<updateNames>)
            for _ in [] if table.track_names else list(table.structure.keys())[1:]:
                list_item = QListWidgetItem()
                list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                list_item.setCheckState(Qt.CheckState.Unchecked)
                selection_listwidget.addItem(list_item)

        self.updateLabels()

        self.splitter.addWidget(self.selection_widget)

        # PREVIEW AND EXPORT
        self.preview_export_widget = QWidget()
        self.preview_export_vbox = QVBoxLayout()
        self.preview_export_widget.setLayout(self.preview_export_vbox)

        self.export_title_hbox = QHBoxLayout()
        self.export_title_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.preview_export_vbox.addLayout(self.export_title_hbox)

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

        # Auto update button
        self.auto_update_button = IndicatorLedButton('Auto update')
        self.auto_update_button.setToolTip('Shows the last 10 minutes and updates every second')
        self.auto_update_button.clicked.connect(self.autoUpdate)
        self.export_title_hbox.addWidget(self.auto_update_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.export_title_hbox.addStretch()

        # Events button
        self.button_events_preview = IndicatorLedButton('Events', initial_state=True)
        self.button_events_preview.setToolTip('Mark events (interlock trips, lost connections, ...) as vertical lines')
        self.button_events_preview.clicked.connect(self.updateEvents)
        self.export_title_hbox.addWidget(self.button_events_preview, alignment=Qt.AlignmentFlag.AlignRight)

        # Min/max envelope button
        self.button_envelope_preview = IndicatorLedButton('Min/Max')
        self.button_envelope_preview.setToolTip(
            'Show the minimum and maximum of every time bucket as shaded band (only for downsampled data),\n'
            'so short spikes (e.g. of the pressure) are not averaged away'
        )
        self.button_envelope_preview.clicked.connect(self.replot)
        self.export_title_hbox.addWidget(self.button_envelope_preview, alignment=Qt.AlignmentFlag.AlignRight)

        # Resolution label
        self.label_resolution = QLabel('')
        self.label_resolution.setToolTip('Resolution of the shown data. Zoom in to load the data with a finer resolution.')
        self.export_title_hbox.addWidget(self.label_resolution, alignment=Qt.AlignmentFlag.AlignRight)

        # Y-log button
        self.button_log_y_preview = IndicatorLedButton('Log-y')
        self.button_log_y_preview.setToolTip('Logarithmic y-axis')
        self.button_log_y_preview.clicked.connect(self.logYAxis)
        self.export_title_hbox.addWidget(self.button_log_y_preview, alignment=Qt.AlignmentFlag.AlignRight)

        # Prediction fit (e.g. final pressure after pumping down)
        self.fit_hbox = QHBoxLayout()
        self.fit_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.preview_export_vbox.addLayout(self.fit_hbox)

        self.button_fit_enable = IndicatorLedButton('Fit')
        self.button_fit_enable.setToolTip(
            'Fits the visible part of the selected curve (dashed line). The fit stays on and is updated with every update,\n'
            'zoom or auto update until it is switched off:\n'
            'Exponential: p(t) = p∞ + A·exp(-t/τ) (pumping of the gas volume, prediction of the final pressure)\n'
            'Power law: p(t) = p∞ + A·(t + t1)^-n (outgassing of the walls, usually better for long times)\n'
            'Linear: y(t) = a + b·t (drift, slope per hour)\n'
            'Gaussian: y(t) = c + A·exp(-(t - t0)²/(2σ²)) (peak or dip)\n'
            'Log-normal: asymmetric peak with a long tail\n'
            'Exponential, power law and linear are extrapolated into the future.'
        )
        self.button_fit_enable.clicked.connect(self.toggleFit)
        self.fit_hbox.addWidget(self.button_fit_enable)
        self.combobox_fit_model = ComboBox(entries=list(FIT_MODELS.keys()))
        self.combobox_fit_model.setToolTip(self.button_fit_enable.toolTip())
        self.combobox_fit_model.currentIndexChanged.connect(self.updateFit)
        self.fit_hbox.addWidget(self.combobox_fit_model)
        self.combobox_fit_series = ComboBox(entries=[])
        self.combobox_fit_series.setToolTip('Curve that is fitted')
        self.combobox_fit_series.setMinimumWidth(200)
        self.combobox_fit_series.currentIndexChanged.connect(self.updateFit)
        self.fit_hbox.addWidget(self.combobox_fit_series)
        self.label_fit_result = QLabel('')
        self.label_fit_result.setToolTip('Result of the fit')
        self.fit_hbox.addWidget(self.label_fit_result)
        self.fit_widgets = [self.combobox_fit_model, self.combobox_fit_series, self.label_fit_result]
        for widget in self.fit_widgets:
            widget.setVisible(False)

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

        # Division between selection (top) and plot (bottom); the sizes are restored from the last session
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setSizes([200, 800])
        splitter_state = GlobalConf.settings.value(self.splitter_state_name, defaultValue=None)
        if splitter_state is not None:
            self.splitter.restoreState(splitter_state)

    splitter_state_name = 'history_splitter_state'

    def closeEvent(self, event):
        """Stores the splitter sizes"""

        GlobalConf.settings.setValue(self.splitter_state_name, self.splitter.saveState())
        GlobalConf.settings.sync()
        super().closeEvent(event)

    def updateLabels(self):
        """Shows the current labels of the database columns in the selection (e.g. after a pressure gauge was renamed), the selection stays"""

        for table, selection_listwidget in zip(self.database.tables, self.selection_listwidgets):
            if table.track_names:
                self.updateNames(table.name, selection_listwidget)
                continue
            for row, attribute in enumerate(list(table.structure.keys())[1:]):
                list_item = selection_listwidget.item(row)
                list_item.setText(self.columnLabel(table.name, attribute))
                list_item.setToolTip(self.columnToolTip(table.name, attribute))

    def updateNames(self, table_name: str, selection_listwidget: QListWidget):
        """
        Shows one entry per name of a table, names that are not used anymore show when they were last used. The selection stays.

        :param table_name: name of table
        :param selection_listwidget: selection of the table
        """

        checked = {item.data(Qt.ItemDataRole.UserRole) for item in self.listItems(selection_listwidget) if item.checkState() == Qt.CheckState.Checked}
        selection_listwidget.clear()
        for name, periods in self.database.getNamePeriods(table_name).items():
            unit = periods[0][1]
            text = f'{name} [{unit}]' if unit else name
            tooltip = [f'{name}:']
            for column_name, _, start_time, end_time in periods:
                start = f'{datetime.fromtimestamp(start_time):%Y-%m-%d %H:%M}' if start_time else 'beginning'
                end = f'{datetime.fromtimestamp(end_time):%Y-%m-%d %H:%M}' if end_time is not None else 'now'
                tooltip.append(f'  {table_name}.{column_name}: {start} to {end}')
            if periods[-1][3] is not None:
                text += f' (until {datetime.fromtimestamp(periods[-1][3]):%Y-%m-%d})'

            list_item = QListWidgetItem(text)
            list_item.setToolTip('\n'.join(tooltip))
            list_item.setData(Qt.ItemDataRole.UserRole, name)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            list_item.setCheckState(Qt.CheckState.Checked if name in checked else Qt.CheckState.Unchecked)
            selection_listwidget.addItem(list_item)

    @staticmethod
    def listItems(selection_listwidget: QListWidget) -> list[QListWidgetItem]:
        """Returns all items of a selection"""
        return [selection_listwidget.item(row) for row in range(selection_listwidget.count())]

    def nameData(self, table_index: int, name: str, start_time: int, end_time: int, bucket_seconds: int = 1, envelope: bool = False, gaps: bool = True) -> np.ndarray | None:
        """
        Returns the readings of a name: only the times when a gauge had this name

        :param table_index: index of table
        :param name: name
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        :param bucket_seconds: average data in time buckets of this size
        :param envelope: also return minimum and maximum of every bucket
        :param gaps: nan row between the times, so no line is drawn between them
        :returns: array with time in the first column or None if there is no data
        """

        parts = []
        for column_name, _, period_start, period_end in self.database.getNamePeriods(self.database.tables[table_index].name).get(name, []):
            # the next name starts at <period_end>
            first = max(start_time, period_start)
            last = end_time if period_end is None else min(end_time, period_end - 1)
            data = self.database.getData(table_index, ['Time', column_name], first, last, bucket_seconds, envelope) if first <= last else False
            if data is False:
                continue

            values = data[1].astype(float)
            values = values[values[:, 0].argsort()]
            if parts and gaps:
                parts.append(np.full((1, values.shape[1]), np.nan))
                parts[-1][0, 0] = values[0, 0]
            parts.append(values)
        return np.concatenate(parts) if parts else None

    @staticmethod
    def nameLabel(item: QListWidgetItem) -> str:
        """
        Returns the label of a curve of a name (with the unit, without the date of the entry)

        :param item: entry of the name
        """

        return re.sub(r' \(until [\d-]+\)$', '', item.text())

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
            item = self.selection_listwidgets[listwidget_index].item(row)
            if not item.isHidden():
                item.setCheckState(state)

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

    def getSeries(self, start_time: int, end_time: int, bucket_seconds: int = 1, envelope: bool = False) -> list[tuple]:
        """
        Gets checked data as separate series (no merging, so no gaps are filled with nan)

        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        :param bucket_seconds: average data in time buckets of this size
        :param envelope: also return minimum and maximum of every bucket (only if bucket_seconds > 1)
        :returns: list of (label, time, values) or (label, time, values, minima, maxima) with envelope
        """

        envelope = envelope and bucket_seconds > 1

        series = []
        for i, table in enumerate(self.database.tables):
            if table.track_names:
                for item in self.listItems(self.selection_listwidgets[i]):
                    if item.checkState() != Qt.CheckState.Checked:
                        continue
                    values = self.nameData(i, item.data(Qt.ItemDataRole.UserRole), start_time, end_time, bucket_seconds, envelope)
                    if values is not None:
                        series.append((f'{table.name}: {self.nameLabel(item)}', *values.T))
                continue

            checked = [0]
            for row in range(len(table.structure) - 1):
                if self.selection_listwidgets[i].item(row).checkState() == Qt.CheckState.Checked:
                    checked.append(row + 1)
            if len(checked) < 2:
                continue

            data = self.database.getData(i, tuple(checked), start_time, end_time, bucket_seconds, envelope)
            if data is False:
                continue
            column_names, column_values = data
            column_values = column_values.astype(float)

            for index, column_name in enumerate(column_names[1:]):
                label = f'{table.name}: {self.columnLabel(table.name, column_name)}'
                if envelope:
                    column = 1 + 3 * index
                    series.append((label, column_values[:, 0], column_values[:, column], column_values[:, column + 1], column_values[:, column + 2]))
                else:
                    series.append((label, column_values[:, 0], column_values[:, index + 1]))
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
            if table.track_names:
                for item in self.listItems(self.selection_listwidgets[i]):
                    if item.checkState() != Qt.CheckState.Checked:
                        continue
                    values = self.nameData(i, item.data(Qt.ItemDataRole.UserRole), start_time, end_time, gaps=False)
                    if values is not None:
                        labels.append(f'{table.name}: {self.nameLabel(item)}')
                        datas.append(values)
                continue

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
            # NULL values are exported as nan
            datas.append(column_values.astype(float))

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
            for item in self.envelope_items:
                self.time_canvas.plotItem.removeItem(item)
            self.envelope_items = []

            series = self.getSeries(start_time, end_time, bucket_seconds, self.button_envelope_preview.value())
            for label, x, y, *envelope in series:
                self.time_canvas.plot(x, y, label=label, plot_params={'connect': 'finite'})
                curve = self.time_canvas.graph_curves[-1]
                # clipping and peak-downsampling of pyqtgraph keep the rendering fast and spikes visible
                # (must be set after the curve was added to the plot)
                curve.setClipToView(True)
                curve.setDownsampling(auto=True, method='peak')

                if envelope:
                    self.addEnvelope(x, envelope[0], envelope[1], curve.opts['pen'].color())

            self.current_series = [(label, x, y) for label, x, y, *_ in series]
            self.updateFitSeries()

            self.loaded_range = (start_time, end_time)
            self.loaded_bucket = bucket_seconds
            self.label_resolution.setText(f'Resolution: {bucket_seconds} s' if bucket_seconds > 1 else 'Resolution: all data')
        finally:
            self.plotting = False
            QApplication.restoreOverrideCursor()

        return bool(series)

    def addEnvelope(self, x: np.ndarray, minima: np.ndarray, maxima: np.ndarray, color):
        """
        Adds a shaded band between minima and maxima

        :param x: time values
        :param minima: minimum of every bucket
        :param maxima: maximum of every bucket
        :param color: color of the curve (QColor)
        """

        valid = np.isfinite(minima) & np.isfinite(maxima)
        if not np.any(valid):
            return
        lower = pg.PlotDataItem(x[valid], minima[valid], pen=pg.mkPen(None))
        upper = pg.PlotDataItem(x[valid], maxima[valid], pen=pg.mkPen(None))
        fill_color = pg.mkColor(color)
        fill_color.setAlpha(70)
        band = pg.FillBetweenItem(lower, upper, brush=pg.mkBrush(fill_color))
        for item in (lower, upper, band):
            self.time_canvas.plotItem.addItem(item, ignoreBounds=item is band)
            self.envelope_items.append(item)

    def replot(self):
        """Plots the loaded range again (e.g. after the min/max option changed)"""

        if self.loaded_range is not None:
            self.plotSeries(*self.loaded_range, self.loaded_bucket)

    def updateFitSeries(self):
        """Fills the curves that can be fitted (pressures first)"""

        labels = [label for label, _, _ in self.current_series]
        current = self.combobox_fit_series.getValue(text=True) if self.combobox_fit_series.entries else ''
        self.combobox_fit_series.reinitialize(entries=labels)
        if current in labels:
            self.combobox_fit_series.setCurrentIndex(labels.index(current))
        else:
            pressures = [i for i, label in enumerate(labels) if label.startswith(self.database.pressure_table.name)]
            if pressures:
                self.combobox_fit_series.setCurrentIndex(pressures[0])

    def clearFit(self):
        """Removes the fit from the plot"""

        for item in self.fit_items:
            self.time_canvas.plotItem.removeItem(item)
        self.fit_items = []
        self.label_fit_result.setText('')

    def toggleFit(self):
        """Fit switched on/off: the fit selection is only shown if the fit is on"""

        enabled = self.button_fit_enable.value()
        for widget in self.fit_widgets:
            widget.setVisible(enabled)
        if enabled:
            self.updateFit()
        else:
            self.clearFit()

    def updateFit(self, *args):
        """Fits the selected curve in the visible range and draws it (only if the fit is switched on)"""

        if self.plotting or not self.button_fit_enable.value():
            return

        self.clearFit()
        if not self.current_series or not 0 <= self.combobox_fit_series.currentIndex() < len(self.current_series):
            self.label_fit_result.setText('No curve to fit, load data first')
            return

        label, x, y = self.current_series[self.combobox_fit_series.currentIndex()]
        view_start, view_end = self.time_canvas.getViewBox().viewRange()[0]
        visible = (x >= view_start) & (x <= view_end)
        model = self.combobox_fit_model.getValue(text=True)
        unit = re.search(r'\[(.*)]\s*$', label)

        try:
            result: PressureFitResult = FIT_MODELS[model](x[visible], y[visible], unit=unit.group(1) if unit else '')
        except (ValueError, RuntimeError) as error:
            self.label_fit_result.setText(f'Fit failed: {error}')
            return

        # predictions from the first fitted point until 3x the fitted time span into the future, peaks only over the fitted range
        span = result.extra['t_span']
        t_fit = np.linspace(result.t_start, result.t_start + (4 if result.prediction else 1) * span, 500)
        curve = pg.PlotDataItem(
            t_fit,
            result.predict(t_fit),
            pen=pg.mkPen(color=Colors.color_red, width=2, style=Qt.PenStyle.DashLine),
            name=f'{model} fit: {label}'
        )
        self.time_canvas.plotItem.addItem(curve, ignoreBounds=True)
        self.fit_items.append(curve)

        text = f'{model}: {result.description}'
        if model in FINAL_VALUE_MODELS:
            reach = result.timeToReach(result.p_inf * 1.1)
            if reach is not None:
                text += f' | 1.1·p∞ reached at {datetime.fromtimestamp(reach):%Y-%m-%d %H:%M}'
        self.label_fit_result.setText(text)

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
        # the fit stays on: fitted again with the new data
        self.updateFit()

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
        if not covered or finer_needed or coarser_needed:
            # load a bit more than visible, so small pans do not need to load again
            margin = (view_end - view_start) * 0.5
            load_start = int(max(self.selected_range[0], view_start - margin))
            load_end = int(min(self.selected_range[1], view_end + margin))
            self.plotSeries(load_start, load_end, wanted_bucket)

        # the fit uses the visible range
        self.updateFit()

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
