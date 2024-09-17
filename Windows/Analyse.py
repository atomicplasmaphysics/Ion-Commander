from copy import copy


import numpy as np

from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout, QApplication


from Utility.Layouts import DeleteWidgetList, DeleteWidgetListItem, ComboBox, TOFCanvas, TabWidget, IndicatorLedButton
from Utility.Dialogs import TACDialog, LMFDialog
from Utility.FileDialogs import selectFileDialog
from Utility.Fitting import getFileData, FitMethod, fittingFunctionsSingle, fittingFunctionsMultiple, supported_file_types


class AnalyseWindow(TabWidget):
    """
    Widget for Analysis

    :param parent: parent widget
    """

    # TODO: shorten names if too long

    def __init__(self, parent):
        super().__init__(parent)

        #
        # Global variables
        #

        self.data: list[tuple[np.ndarray, np.ndarray]] = []
        self.files_opened = False
        self.supported_filetypes = copy(supported_file_types)
        self.supported_filetypes.append('lmf')
        self.supported_filetypes_filter = '(' + ' '.join(f'*.{file_type}' for file_type in self.supported_filetypes) + ')'
        self.setAcceptDrops(True)
        self.last_opened_directory = QDir.currentPath()

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

        self.grid_buttons = QGridLayout(self)
        self.grid_buttons.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.row_menu.addLayout(self.grid_buttons)

        self.button_open = QPushButton('Open', self)
        self.button_open.setToolTip('Open data to analyze')
        self.button_open.clicked.connect(self.openFiles)
        self.grid_buttons.addWidget(self.button_open, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)

        self.button_clear = QPushButton('Clear all', self)
        self.button_clear.setToolTip('Clear all opened data')
        self.button_clear.clicked.connect(self.clearFiles)
        self.grid_buttons.addWidget(self.button_clear, 1, 0, alignment=Qt.AlignmentFlag.AlignTop)

        self.button_check = QPushButton('Check all', self)
        self.button_check.setToolTip('Check all data to visualize all')
        self.button_check.clicked.connect(self.checkFiles)
        self.grid_buttons.addWidget(self.button_check, 0, 1, alignment=Qt.AlignmentFlag.AlignTop)

        self.button_uncheck = QPushButton('Uncheck all', self)
        self.button_uncheck.setToolTip('Uncheck all checked data to visualize only one')
        self.button_uncheck.clicked.connect(self.uncheckFiles)
        self.grid_buttons.addWidget(self.button_uncheck, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)

        self.list_files = DeleteWidgetList(self, placeholder='Select files first')
        self.list_files.setMaximumHeight(100)
        self.list_files.currentRowChanged.connect(self.loadDataSelected)
        self.list_files.checkedChanged.connect(self.loadDataChecked)

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

        self.fitting_functions = []
        self.fitting_functions_state = 0

        self.fitting_selector_label = QLabel('Select fit function:')
        self.column_fitting_selector.addWidget(self.fitting_selector_label)

        self.fitting_selector_widget = ComboBox()
        self.initializeFitFunctions()
        self.fitting_selector_widget.currentIndexChanged.connect(self.fittingSelectorChanged)
        self.column_fitting_selector.addWidget(self.fitting_selector_widget)

        self.button_reset_sliders = QPushButton('Reset sliders')
        self.button_reset_sliders.clicked.connect(self.resetSliders)
        self.column_fitting_selector.addWidget(self.button_reset_sliders)

        self.row_fitting_parameters = QHBoxLayout()
        self.row_fitting_parameters.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.row_fitting.addLayout(self.row_fitting_parameters)

        self.fitting_parameters_box = QGroupBox('Fitting Parameters')
        self.fitting_parameters_copy_button = QPushButton(self)
        self.fitting_parameters_copy_button.setIcon(QIcon('icons/copy.png'))
        self.fitting_parameters_copy_button.setToolTip('Copy fitting parameters')
        self.fitting_parameters_copy_button.clicked.connect(self.copyFittingParameters)
        self.row_fitting_parameters.addWidget(self.fitting_parameters_copy_button)
        self.row_fitting_parameters.addWidget(self.fitting_parameters_box, stretch=1)
        self.fitting_parameters_box_layout = QVBoxLayout()
        self.fitting_parameters_box.setLayout(self.fitting_parameters_box_layout)

        self.fit_function_class: FitMethod = self.fitting_functions[0](self)
        self.fitting_parameters_box_layout.addWidget(self.fit_function_class.widget)

        self.column_axis_manipulation = QVBoxLayout()
        self.column_axis_manipulation.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.row_fitting.addLayout(self.column_axis_manipulation)

        self.button_log_y = IndicatorLedButton('Log-y')
        self.button_log_y.clicked.connect(self.logYAxis)
        self.column_axis_manipulation.addWidget(self.button_log_y, alignment=Qt.AlignmentFlag.AlignTop)

        self.button_fill_histo = IndicatorLedButton('Fill histogram', initial_state=True)
        self.button_fill_histo.clicked.connect(self.loadDataChecked)
        self.column_axis_manipulation.addWidget(self.button_fill_histo, alignment=Qt.AlignmentFlag.AlignTop)

        #
        # DISPLAY
        #

        # TODO: check if legend=False is needed
        self.graph = TOFCanvas(parent=self, data=self.data, fit_class=self.fit_function_class, grid=True)
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
                start_dir=self.last_opened_directory,
                file_filter=self.supported_filetypes_filter,
                multiple=True
            )

        if files is None or not len(files):
            return

        self.last_opened_directory = files[0]

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

            # open convert window for '.lmf' file
            if file.endswith('.lmf'):
                lmf_dialog = LMFDialog(file, parent=self)
                lmf_dialog.exec()
                if not lmf_dialog.finish_state:
                    continue
                file = lmf_dialog.output_filename.path

            if self.files_opened is False:
                self.files_opened = file

            del_item = DeleteWidgetListItem(file, data=del_item_kwargs, checkbox_visible=True)
            self.list_files.addItem(del_item)

    def initializeFitFunctions(self):
        """Initializes fit functions"""

        if len(self.list_files.checkedRows()) >= 1:
            new_fitting_functions_state = 2
        else:
            new_fitting_functions_state = 1

        if self.fitting_functions_state == new_fitting_functions_state:
            return

        self.fitting_functions = [FitMethod]
        if new_fitting_functions_state == 1:
            self.fitting_functions.extend(fittingFunctionsSingle)
        else:
            self.fitting_functions.extend(fittingFunctionsMultiple)

        self.fitting_functions_state = new_fitting_functions_state
        self.fitting_selector_widget.setCurrentIndex(0)
        self.fitting_selector_widget.reinitialize(
            default=0,
            entries=[ff.title for ff in self.fitting_functions],
            tooltips=[ff.tooltip for ff in self.fitting_functions]
        )
        self.fitting_selector_widget.setCurrentIndex(0)

    def clearFiles(self):
        """Clears all opened files"""
        self.list_files.clearAll()
        self.clearData()

    def checkFiles(self):
        """Checks all files"""
        self.list_files.checkAll()

    def uncheckFiles(self):
        """Unchecks all files"""
        self.list_files.uncheckAll()

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

    def clearData(self):
        """Clears the data"""

        self.data = []
        self.graph.plotTOF(self.data)

    def loadData(self, rows: list[int]):
        """
        Loads data from selected file

        :param rows: list of indices of selected row
        """

        self.initializeFitFunctions()
        self.data = []

        if not rows:
            self.clearData()
            return

        if len(rows) > len(self.graph.graph_colors):
            self.writeStatusBar('INFO: Too many datasets selected, same colors will be reused multiple times')

        view_all = True
        self.list_files.resetColors()

        for i, row in enumerate(rows):
            widget = self.list_files.itemWidget(self.list_files.item(row))
            if isinstance(widget, DeleteWidgetListItem):
                try:
                    data = widget.data
                    self.data.append(
                        getFileData(
                            widget.path,
                            tac=data.get('tac', 50),
                            delay=data.get('delay', 0)
                        )
                    )

                    if widget.checked():
                        widget.setBackgroundColor(self.graph.graph_colors[i])

                    view_all = view_all and (self.files_opened == widget.path)
                    self.files_opened = False

                except (OSError, ValueError) as error:
                    self.writeStatusBar(f'File could not be read: {error}')

        self.graph.plotTOF(self.data, view_all=view_all, fill_histogram=self.button_fill_histo.value())

    def loadDataSelected(self, row: int):
        """
        Loads data from selected file

        :param row: index of selected row
        """

        if self.list_files.checkedRows():
            self.loadDataChecked()
            return

        self.loadData([row])

    def loadDataChecked(self):
        """
        Loads data from all selected files
        """

        if not self.list_files.checkedRows():
            self.loadDataSelected(self.list_files.currentRow())
            return

        self.loadData(self.list_files.checkedRows())

    def logYAxis(self):
        """Updates the y-axis to be logarithmic or normal"""

        self.graph.setLogY(self.button_log_y.value())

    def copyFittingParameters(self):
        """Copies the fitting parameters"""

        parameters_copy = self.fit_function_class.copyParameters()
        if parameters_copy:
            QApplication.clipboard().setText(parameters_copy)

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
