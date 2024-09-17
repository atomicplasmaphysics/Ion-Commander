from os import listdir
from os.path import join


from PyQt6.QtWidgets import QSplitter, QWidget, QBoxLayout, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import TabWidget, VBoxTitleLayout, ButtonGridLayout, TextEdit
from Utility.Dialogs import TipNameDialog


class TipsWindow(TabWidget):
    """
    Widget for tip information

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        self.path_tips = DefaultParams.tip_folder
        self.tip_extension = f'.{DefaultParams.tip_extension}'
        self.path_tips_entries = str(join(self.path_tips, DefaultParams.tip_file_folder))
        self.path_tips_images = str(join(self.path_tips, 'images'))
        self.tips: list[str] = []

        # SPLITTER
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        # TIP SELECTION
        self.tip_selection_vbox = VBoxTitleLayout('Tip Selection', parent=self, add_stretch=True)
        self.tip_selection_group_vbox = QVBoxLayout()

        # New tip
        self.tip_new_button = QPushButton('Add new Tip')
        self.tip_new_button.setToolTip('Add a new tip and description of the tip')
        self.tip_new_button.pressed.connect(self.addNewTip)
        self.tip_selection_group_vbox.addWidget(self.tip_new_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Button grid
        self.tip_selection_grid = ButtonGridLayout([], max_columns=5, max_rows=20)
        self.tip_selection_group_vbox.addLayout(self.tip_selection_grid)
        self.tip_selection_grid.buttonPressedName.connect(self.editTip)

        # Stretch to bottom
        self.tip_selection_group_vbox.addStretch(1)
        self.tip_selection_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.tip_selection_vbox_parent = QWidget(self)
        self.tip_selection_vbox.setBodyLayout(self.tip_selection_group_vbox)
        self.tip_selection_vbox_parent.setLayout(self.tip_selection_vbox)
        self.splitter.addWidget(self.tip_selection_vbox_parent)

        # TIP EDITOR
        self.tip_editor_vbox = VBoxTitleLayout('Tip Editor', parent=self, add_stretch=True)
        self.tip_editor_group_vbox = QVBoxLayout()

        # Headline
        self.tip_selected_headline = QLabel('Selected tip: None')
        self.tip_editor_group_vbox.addWidget(self.tip_selected_headline, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Text editor
        self.tip_editor = TextEdit(
            image_directory=self.path_tips_images,
            save_button=False,
            load_button=False,
            encoding=DefaultParams.tip_encoding
        )
        self.tip_editor_path = ''
        self.tip_editor.setDisabled(True)
        self.tip_editor.setToolTip('Select tip first to edit')
        self.tip_editor_group_vbox.addWidget(self.tip_editor)

        # Stretch to bottom
        self.tip_editor_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.tip_editor_vbox_parent = QWidget(self)
        self.tip_editor_vbox.setBodyLayout(self.tip_editor_group_vbox)
        self.tip_editor_vbox_parent.setLayout(self.tip_editor_vbox)
        self.splitter.addWidget(self.tip_editor_vbox_parent)

        # Division between columns
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 95)

        self.updateTips()

    def updateTips(self):
        """Updates list of tips"""

        # update list of tips
        self.tips = []
        for file in listdir(self.path_tips_entries):
            if not file.endswith(self.tip_extension):
                GlobalConf.logger.debug(f'Tips: File "{file}" in Tips folder, but has wrong file extension (not {self.tip_extension})')
            self.tips.append(file[:-len(self.tip_extension)])
        self.tips.sort()

        # update buttons grid
        self.tip_selection_grid.newLabels(self.tips)

    def addNewTip(self):
        """Add a new tip"""

        self.updateTips()

        # get new tip name
        tip_dialog = TipNameDialog(self.tips)
        tip_dialog.exec()
        tip_name = tip_dialog.getName()

        if not tip_name:
            return

        check = tip_dialog.checkName(tip_name)
        if check:
            self.writeStatusBar(f'Error in adding tip: {check}')
            return

        # try generating tip file
        tip_path = str(join(self.path_tips_entries, f'{tip_name}{self.tip_extension}'))
        try:
            with open(tip_path, 'w', encoding='utf-8') as _:
                self.writeStatusBar(f'Tip file "{tip_path}" generated successfully')
        except FileNotFoundError:
            self.writeStatusBar(f'Tip file "{tip_path}" could not be generated')

        self.updateTips()

    def editTip(self, name: str):
        """Edit selected tip"""

        # save tip editor
        if self.tip_editor_path:
            if self.tip_editor.saveFile(self.tip_editor_path):
                self.writeStatusBar(f'File "{self.tip_editor_path}" could not be saved')
            self.tip_editor_path = ''

        self.tip_editor.clearContents()
        self.tip_selected_headline.setText('Selected tip: None')
        self.tip_editor.setDisabled(True)
        self.tip_editor.setToolTip('Select tip first to edit')

        self.updateTips()

        # check if tip is valid
        if name not in self.tips:
            self.writeStatusBar(f'Tip "{name}" does not exist')
            return

        # open new tip file
        tip_path = str(join(self.path_tips_entries, f'{name}{self.tip_extension}'))
        if self.tip_editor.openFile(tip_path):
            self.writeStatusBar(f'Error while loading tip "{name}"')
            return

        self.tip_editor_path = tip_path
        self.tip_selected_headline.setText(f'Selected tip: {name}')
        self.tip_editor.setDisabled(False)
        self.tip_editor.setToolTip('')

    def closeEvent(self, event):
        """Save current tip editor"""

        if self.tip_editor_path:
            if self.tip_editor.saveFile(self.tip_editor_path):
                self.writeStatusBar(f'File "{self.tip_editor_path}" could not be saved')
            self.tip_editor_path = ''
