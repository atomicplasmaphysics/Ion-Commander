from os import listdir


from PyQt6.QtWidgets import QSplitter, QWidget, QGroupBox, QBoxLayout, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


from Utility.Layouts import TabWidget, VBoxTitleLayout, ButtonGridLayout, TextEdit


class TipsWindow(TabWidget):
    """
    Widget for tip information

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        # TODO: put constants in Config file
        self.path_tips = 'Tips'
        self.path_tips_entries = f'{self.path_tips}/entries'
        self.path_tips_images = f'{self.path_tips}/images'
        self.tips = []
        self.tip_index = -1

        # SPLITTER
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        # TODO: Add tooltips to everything

        # TIP SELECTION
        self.tip_selection_vbox = VBoxTitleLayout('Tip Selection', parent=self, add_stretch=True)
        self.tip_selection_group_vbox = QVBoxLayout()

        # New tip
        self.tip_new_button = QPushButton('Add new Tip')
        self.tip_new_button.pressed.connect(self.addNewTip)
        self.tip_selection_group_vbox.addWidget(self.tip_new_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Button grid
        self.tip_selection_grid = ButtonGridLayout([], max_columns=5, max_rows=20)
        self.tip_selection_group_vbox.addLayout(self.tip_selection_grid)
        self.tip_selection_grid.buttonPressed.connect(self.editTip)

        # Stretch to bottom
        self.tip_selection_group_vbox.addStretch(1)
        self.tip_selection_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.tip_selection_vbox_parent = QWidget(self)
        self.tip_selection_group = QGroupBox(self)
        self.tip_selection_group.setLayout(self.tip_selection_group_vbox)
        self.tip_selection_vbox.addWidget(self.tip_selection_group)
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
            load_button=False
        )
        self.tip_editor_group_vbox.addWidget(self.tip_editor)

        # Stretch to bottom
        self.tip_editor_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.tip_editor_vbox_parent = QWidget(self)
        self.tip_editor_group = QGroupBox(self)
        self.tip_editor_group.setLayout(self.tip_editor_group_vbox)
        self.tip_editor_vbox.addWidget(self.tip_editor_group)
        self.tip_editor_vbox_parent.setLayout(self.tip_editor_vbox)
        self.splitter.addWidget(self.tip_editor_vbox_parent)

        # Division between columns
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 95)

        self.updateTips()

    def updateTips(self):
        """Updates list of tips"""

        # get list of tips "%d.txt"-files
        self.tips = []
        for file in listdir(self.path_tips_entries):
            if not file.endswith('.txt'):
                continue
            try:
                self.tips.append(int(file[:-4]))
            except ValueError:
                continue
        self.tips.sort()

        # update buttons grid
        self.tip_selection_grid.newLabels([f'Tip {tip}' for tip in self.tips])

    def addNewTip(self):
        """Add a new tip"""

        new_tip_number = 1
        if self.tips:
            new_tip_number = self.tips[-1] + 1
        open(f'{self.path_tips_entries}/{new_tip_number}.txt', 'w')
        self.updateTips()

    def editTip(self, index: int):
        """Edit selected tip"""

        if index == self.tip_index:
            return

        # save tip editor
        if self.tip_index in range(0, len(self.tips)):
            self.tip_editor.saveFile(f'{self.path_tips_entries}/{self.tips[self.tip_index]}.txt')

        # check if we are in bounds
        if index not in range(0, len(self.tips)):
            self.tip_editor.clearContents()
            self.tip_selected_headline.setText('Selected tip: None')
            return

        # open new tip file
        self.tip_editor.openFile(f'{self.path_tips_entries}/{self.tips[index]}.txt')
        self.tip_selected_headline.setText(f'Selected tip: Tip #{self.tips[index]}')
        self.tip_index = index

    def closeEvent(self, event):
        """Save current tip editor"""

        if self.tip_index in range(0, len(self.tips)):
            self.tip_editor.saveFile(f'{self.path_tips_entries}/{self.tips[self.tip_index]}.txt')
