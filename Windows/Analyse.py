import numpy as np

from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

import pyqtgraph as pg


from Utility.Layouts import DeleteWidgetList, DeleteWidgetListItem, ComboBox, TOFCanvas, TabWidget
from Utility.Dialogs import selectFileDialog, TACDialog
from Utility.Fitting import getFileData, fittingFunctions


class AnalyseWindow(TabWidget):
    """
    Widget for Analysis

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        #
        # Global variables
        #

        self.data: tuple[np.ndarray, np.ndarray] = (np.array([]), np.array([]))
        self.files_opened = False
        self.supported_filetypes = ['dat', 'cod']
        self.setAcceptDrops(True)

        #
        # SET UP WIDGET AND LAYOUT
        #

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.main_layout)

        #
        # MENU ROW
        #

        self.row_menu = QHBoxLayout(self)
        self.row_menu.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addLayout(self.row_menu)

        self.column_buttons = QVBoxLayout(self)
        self.column_buttons.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.row_menu.addLayout(self.column_buttons)

        self.button_open = QPushButton('Open', self)
        self.button_open.clicked.connect(self.openFiles)
        self.column_buttons.addWidget(self.button_open, alignment=Qt.AlignmentFlag.AlignTop)

        self.button_clear = QPushButton('Clear', self)
        self.button_clear.clicked.connect(self.clearFiles)
        self.column_buttons.addWidget(self.button_clear, alignment=Qt.AlignmentFlag.AlignTop)

        self.list_files = DeleteWidgetList(self)
        self.list_files.setMaximumHeight(100)
        self.list_files.currentRowChanged.connect(self.loadData)

        self.row_menu.addWidget(self.list_files)

        #
        # FITTING PARAMETERS
        #

        self.row_fitting = QHBoxLayout()
        self.row_fitting.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addLayout(self.row_fitting)

        self.column_fitting_selector = QVBoxLayout()
        self.column_fitting_selector.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.row_fitting.addLayout(self.column_fitting_selector)

        self.fitting_functions = fittingFunctions

        self.fitting_selector_label = QLabel('Select fit function:')
        self.column_fitting_selector.addWidget(self.fitting_selector_label)

        self.fitting_selector_widget = ComboBox(
            default=0,
            entries=[ff.title for ff in self.fitting_functions],
            tooltips=[ff.tooltip for ff in self.fitting_functions]
        )
        self.fitting_selector_widget.currentIndexChanged.connect(self.fittingSelectorChanged)
        self.column_fitting_selector.addWidget(self.fitting_selector_widget)

        self.button_reset_sliders = QPushButton('Reset sliders')
        self.button_reset_sliders.clicked.connect(self.resetSliders)
        self.column_fitting_selector.addWidget(self.button_reset_sliders)

        self.row_fitting_parameters = QHBoxLayout()
        self.row_fitting_parameters.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.row_fitting.addLayout(self.row_fitting_parameters)

        self.fitting_parameters_box = QGroupBox('Fitting Parameters')
        self.row_fitting_parameters.addWidget(self.fitting_parameters_box, stretch=1)
        self.fitting_parameters_box_layout = QVBoxLayout()
        self.fitting_parameters_box.setLayout(self.fitting_parameters_box_layout)

        self.fit_function_class = self.fitting_functions[0](self)
        self.fitting_parameters_box_layout.addWidget(self.fit_function_class.widget)

        #
        # DISPLAY
        #

        self.graph = TOFCanvas(parent=self, data=self.data, fit_class=self.fit_function_class)
        self.main_layout.addWidget(self.graph)

    def openFiles(self, files: list[str] = None):
        """
        Displays open file dialog and opens selected files

        :param files: list of filepaths to open
        """

        if not isinstance(files, list):
            files = selectFileDialog(
                parent=self,
                for_saving=False,
                instruction='Select Files',
                start_dir=QDir.currentPath(),
                file_filter='(*.dat *.cod)',
                multiple=True
            )

        if files is None or not len(files):
            return

        for file in files:
            if not file.split('.')[-1].lower() in self.supported_filetypes:
                self.writeStatusBar(f'File "{file}" has unsupported filetype')
                continue

            if file in [str(item) for item in self.list_files.containedItems()]:
                self.writeStatusBar(f'File "{file}" already opened')
                continue

            # ask for tac and delay if '.dat' file
            del_item_kwargs = {}
            if file.endswith('.dat'):
                tac_dialog = TACDialog(file, parent=self)
                tac_dialog.exec()
                del_item_kwargs = {
                    'tac': tac_dialog.tac_input.value(),
                    'delay': tac_dialog.delay_input.value(),
                }

            if self.files_opened is False:
                self.files_opened = file

            del_item = DeleteWidgetListItem(self, file, **del_item_kwargs)
            self.list_files.addItem(del_item)

    def clearFiles(self):
        """Clears all opened files"""
        self.list_files.clearAll()

    def fittingSelectorChanged(self, index: int):
        """
        Called when fitting selector is changed

        :param index: new index of fitting function
        """

        self.fit_function_class.widget.deleteLater()
        del self.fit_function_class
        self.fit_function_class = self.fitting_functions[index](self)
        self.fitting_parameters_box_layout.addWidget(self.fit_function_class.widget)
        self.graph.updateFitClass(self.fit_function_class)

    def resetSliders(self):
        """
        Resets the sliders in the currently visible area
        """

        selected_index = self.fitting_selector_widget.currentIndex()
        if selected_index:
            self.fitting_selector_widget.setCurrentIndex(0)
            self.fitting_selector_widget.setCurrentIndex(selected_index)

    def loadData(self, row: int):
        """
        Loads data from selected file

        :param row: index of selected row
        """

        self.data = (np.array([]), np.array([]))
        if row == -1:
            self.graph.plotData(self.data)
            return

        view_all = False
        widget = self.list_files.itemWidget(self.list_files.item(row))
        if isinstance(widget, DeleteWidgetListItem):
            try:
                self.data = getFileData(
                    widget.path,
                    tac=widget.tac,
                    delay=widget.delay
                )
                view_all = (self.files_opened == widget.path)
                self.files_opened = False

            except (OSError, ValueError) as error:
                self.writeStatusBar(f'File could not be read: {error}')

        else:
            self.writeStatusBar('File could not be loaded!')

        self.graph.plotData(self.data, view_all=view_all)

    def updatePlotLimits(self, plot_widget: pg.PlotWidget = None, view_range: list[list[float, float]] = None):
        """
        Updates the y limit of the plot depending on the selected x range

        :param plot_widget: PlotWidget from where this is called
        :param view_range: ranges for x and y: [[x_min, x_max], [y_min, y_max]]
        """

        # default plot widget
        if plot_widget is None:
            plot_widget = self.graph

        # default view range
        if view_range is None:
            view_range = plot_widget.getViewBox().viewRange()

        selected_range = np.logical_and(self.data[0] > view_range[0][0], self.data[0] < view_range[0][1])
        selected_ydata = self.data[1][selected_range]
        if not len(selected_ydata):
            return
        plot_widget.setYRange(np.min(selected_ydata), np.max(selected_ydata))

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Executed when files are dragged over

        :param event: drag enter event
        """

        if event.mimeData().hasUrls():
            filetypes = [url.toLocalFile().split('.')[-1].lower() for url in event.mimeData().urls()]
            if [i for i in filetypes if i in self.supported_filetypes]:
                event.accept()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """
        Executed when files are dropped over

        :param event: drop event
        """

        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.openFiles(files)

    def checkClosable(self) -> bool:
        """Checks if this tab is currently closeable"""
        return True
