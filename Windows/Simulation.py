from os import listdir, path


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout, QSplitter, QWidget, QApplication


from Config.GlobalConf import GlobalConf

from Utility.Layouts import TabWidget, VBoxTitleLayout, DeleteWidgetList, DeleteWidgetListItem
from Utility.FileDialogs import selectFolderDialog

from Windows.SimulatonCalculator import SimulationCalculator, MassCalculatorVBoxLayout, TOFCalculatorVBoxLayout


class SimulationWindow(TabWidget):
    """
    Widget for Simulation Evaluation

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        #
        # Global variables
        #

        self.calculators = dict()

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

        self.button_add = QPushButton('Add', self)
        self.button_add.setToolTip('Add folder with simulation data')
        self.button_add.clicked.connect(self.addFolders)
        self.grid_buttons.addWidget(self.button_add, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)

        self.button_update = QPushButton('Update', self)
        self.button_update.setToolTip('Update used simulation data based on selected folders')
        self.button_update.clicked.connect(self.updateFolders)
        self.grid_buttons.addWidget(self.button_update, 1, 0, alignment=Qt.AlignmentFlag.AlignTop)

        self.list_folders = DeleteWidgetList(self, placeholder='Select folders first')
        self.list_folders.setMaximumHeight(100)
        self.list_folders.itemDeleted.connect(self.updateFolders)

        self.row_menu.addWidget(self.list_folders)

        #
        # SPLITTER FOR CONVERTERS
        #

        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        #
        # MASS CALCULATOR
        #

        self.mass_calculator_vbox = VBoxTitleLayout('<Simulation> Mass Calculator', parent=self, add_stretch=True, popout_enable=True)
        self.mass_calculator_group_vbox = MassCalculatorVBoxLayout(self.calculators)

        # Stretch to bottom
        self.mass_calculator_group_vbox.addStretch(1)
        self.mass_calculator_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.mass_calculator_vbox_parent = QWidget(self)
        self.mass_calculator_vbox.setBodyLayout(self.mass_calculator_group_vbox)
        self.mass_calculator_vbox_parent.setLayout(self.mass_calculator_vbox)
        self.splitter.addWidget(self.mass_calculator_vbox_parent)

        #
        # TOF CALCULATOR
        #

        self.tof_calculator_vbox = VBoxTitleLayout('<Simulation> TOF Calculator', parent=self, add_stretch=True, popout_enable=True)
        self.tof_calculator_group_vbox = TOFCalculatorVBoxLayout(self.calculators)

        # Stretch to bottom
        self.tof_calculator_group_vbox.addStretch(1)
        self.tof_calculator_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.tof_calculator_vbox_parent = QWidget(self)
        self.tof_calculator_vbox.setBodyLayout(self.tof_calculator_group_vbox)
        self.tof_calculator_vbox_parent.setLayout(self.tof_calculator_vbox)
        self.splitter.addWidget(self.tof_calculator_vbox_parent)

        # Division between columns
        self.splitter.setStretchFactor(0, 50)
        self.splitter.setStretchFactor(1, 50)

        # Get last parameters
        self.addFolders(GlobalConf.getSimulationPathsParameter())

    def addFolders(self, folders: list[str] = None):
        """
        Add folder to list of folders from which the simulation calculators get their data

        :param folders: folders to be loaded
        """

        given_folders = isinstance(folders, list)
        if not given_folders:
            folder = selectFolderDialog(
                parent=self,
                instruction='Select Folder'
            )
            folders = []
            if len(folder):
                folders.append(folder)

        if not folders:
            return

        for folder in folders:
            if folder in [str(item) for item in self.list_folders.containedItems()]:
                self.writeStatusBar(f'Folder "{folder}" already opened')
                continue

            del_item = DeleteWidgetListItem(folder)
            self.list_folders.addItem(del_item)

        if not given_folders:
            self.updateFolders()

    def updateFolders(self):
        """Updates simulation calculators based on folders list"""

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        files = []
        for del_item in self.list_folders.containedItems():
            del_path = del_item.path
            for file_name in listdir(del_path):
                files.append(path.join(del_path, file_name))

        self.calculators = dict()

        for file in files:
            try:
                self.calculators[file] = SimulationCalculator(file)
            except ValueError as error:
                self.main_window.writeStatusBar(f'Could not load file "{file}": {error}')

        self.mass_calculator_group_vbox.updateCalculators(self.calculators)
        self.tof_calculator_group_vbox.updateCalculators(self.calculators)

        QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        """Save to global configuration"""
        GlobalConf.updateSimulationPathsParameter([del_item.path for del_item in self.list_folders.containedItems()])
