from os import makedirs
from os.path import join, exists, abspath


from PyQt6.QtWidgets import (
    QSplitter, QWidget, QBoxLayout, QVBoxLayout, QPushButton, QLabel, QInputDialog, QMessageBox, QToolBar, QProgressBar,
    QHBoxLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import TabWidget, VBoxTitleLayout, FilesList, FileEditor

from Socket.ScriptServer import ScriptServer


class ScriptsWindow(TabWidget):
    """
    Widget for scripts to run

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        self.path_scripts = DefaultParams.script_folder
        self.extension_scripts = DefaultParams.script_extension
        self.scripts: list[str] = []
        makedirs(abspath(self.path_scripts), exist_ok=True)

        self.script_server: ScriptServer | None = None

        # SPLITTER
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        # SCRIPT SELECTION
        self.script_selection_vbox = VBoxTitleLayout('Script Selection', parent=self, add_stretch=True)
        self.script_selection_group_vbox = QVBoxLayout()

        # Add script and update
        self.script_add_update_hbox = QHBoxLayout()
        self.script_add_update_hbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.script_selection_group_vbox.addLayout(self.script_add_update_hbox)

        # New script button
        self.script_new_button = QPushButton('Add new Script')
        self.script_new_button.setToolTip('Add a new script')
        self.script_new_button.pressed.connect(self.addNewScript)
        self.script_add_update_hbox.addWidget(self.script_new_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Update button
        self.script_update_button = QPushButton()
        self.script_update_button.setIcon(QIcon('icons/refresh.png'))
        self.script_update_button.setToolTip('Update list')
        self.script_add_update_hbox.addWidget(self.script_update_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Scripts grid
        self.script_selection_list = FilesList(folder=self.path_scripts, extensions=self.extension_scripts)
        self.script_selection_group_vbox.addWidget(self.script_selection_list)
        self.script_selection_list.currentRowChanged.connect(self.editScript)

        self.script_update_button.pressed.connect(self.script_selection_list.listFiles)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.script_selection_vbox_parent = QWidget(self)
        self.script_selection_vbox.setBodyLayout(self.script_selection_group_vbox)
        self.script_selection_vbox_parent.setLayout(self.script_selection_vbox)
        self.splitter.addWidget(self.script_selection_vbox_parent)

        # SCRIPT EDITOR
        self.script_editor_vbox = VBoxTitleLayout('Script Editor', parent=self, add_stretch=True)
        self.script_editor_group_vbox = QVBoxLayout()

        self.script_splitter = QSplitter(Qt.Orientation.Vertical)
        self.script_splitter.setChildrenCollapsible(False)
        self.script_editor_group_vbox.addWidget(self.script_splitter)

        # Top part
        self.script_editor_top_vbox = QVBoxLayout()
        self.script_editor_top_vbox_parent = QWidget(self)
        self.script_editor_top_vbox_parent.setLayout(self.script_editor_top_vbox)
        self.script_splitter.addWidget(self.script_editor_top_vbox_parent)

        # Headline
        self.script_selected_headline = QLabel('Selected script: None')
        self.script_editor_top_vbox.addWidget(self.script_selected_headline, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Text editor
        self.script_editor = FileEditor(readonly=False)
        self.script_editor_path = ''
        self.script_editor.setDisabled(True)
        self.script_editor.setToolTip('Select script first to edit')
        self.script_editor_top_vbox.addWidget(self.script_editor)

        # Bottom part
        self.script_editor_bottom_vbox = QVBoxLayout()
        self.script_editor_bottom_vbox_parent = QWidget(self)
        self.script_editor_bottom_vbox_parent.setLayout(self.script_editor_bottom_vbox)
        self.script_splitter.addWidget(self.script_editor_bottom_vbox_parent)

        # Run script toolbar
        self.toolbar = QToolBar()
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.toolbar.toggleViewAction().setEnabled(False)
        self.script_editor_bottom_vbox.addWidget(self.toolbar)

        # Run script toolbar: start
        self.script_action_run = self.toolbar.addAction(QIcon('icons/play.png'), 'Run')
        self.script_action_run.setToolTip('<b>Run</b> the current selected script')
        self.script_action_run.triggered.connect(lambda: self.runScript())

        # Run script toolbar: abort
        self.script_action_abort = self.toolbar.addAction(QIcon('icons/abort.png'), 'Abort')
        self.script_action_abort.setToolTip('<b>Abort</b> the currently running script')
        self.script_action_abort.setEnabled(False)
        self.script_action_abort.triggered.connect(lambda: self.abortScript())

        # Run script toolbar: progress bar
        self.script_run_progress = QProgressBar(self)
        self.script_run_progress.setToolTip('The progress of the script')
        self.script_run_progress.setMinimumWidth(50)
        self.script_run_progress.setMaximumWidth(400)
        self.toolbar.addWidget(self.script_run_progress)

        # Script output
        self.script_output = FileEditor(self, line_numbering=False, highlighting=False)
        self.script_output.setPlaceholderText('Output of the script is here')
        self.script_editor_bottom_vbox.addWidget(self.script_output)

        # Stretch to bottom
        self.script_editor_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.script_editor_vbox_parent = QWidget(self)
        self.script_editor_vbox.setBodyLayout(self.script_editor_group_vbox)
        self.script_editor_vbox_parent.setLayout(self.script_editor_vbox)
        self.splitter.addWidget(self.script_editor_vbox_parent)

        # Division between columns
        self.splitter.setStretchFactor(0, 20)
        self.splitter.setStretchFactor(1, 80)

        # set up editor
        self.editScript(self.script_selection_list.currentRow())

    def addNewScript(self):
        """Add new script"""

        new_name, ok = QInputDialog.getText(self, 'Create new script', 'Name:')
        if ok and new_name:
            if not new_name.endswith(f'.{self.extension_scripts}'):
                new_name += f'.{self.extension_scripts}'

            new_path = join(self.path_scripts, new_name)

            if exists(new_path):
                QMessageBox.warning(self, 'Error', 'File with this name already exists!')
                return

            try:
                with open(new_path, 'w', encoding=DefaultParams.script_encoding) as _:
                    self.writeStatusBar(f'Script file "{new_path}" generated successfully')
                self.script_selection_list.selected_file = new_name
                self.script_selection_list.listFiles()

            except FileNotFoundError:
                self.writeStatusBar(f'Script file "{new_path}" could not be generated')

    def saveScript(self):
        """Saves script to given path"""

        if not self.script_editor_path:
            return

        try:
            with open(self.script_editor_path, 'w', encoding='utf-8') as file:
                file.write(self.script_editor.toPlainText())
        except (FileNotFoundError, FileExistsError, OSError) as error:
            GlobalConf.logger.warning(f'Script "{self.script_editor_path}" could not be saved because of: {error}')
            self.writeStatusBar(f'File "{self.script_editor_path}" could not be saved')

        self.script_editor_path = ''

    def loadScript(self, script_path: str) -> bool:
        """Loads script from given path"""

        try:
            with open(script_path, 'r', encoding='utf-8') as file:
                self.script_editor.setPlainText(file.read())
            return True
        except (FileNotFoundError, FileExistsError, OSError) as error:
            GlobalConf.logger.warning(f'Script "{script_path}" could not be loaded because of: {error}')
            self.writeStatusBar(f'Error while loading script "{script_path}"')
            return False

    def editScript(self, list_idx: int):
        """
        Script to edit

        :param list_idx: index of list
        """

        if list_idx < 0 or list_idx >= self.script_selection_list.count():
            self.script_editor.clear()
            self.script_selected_headline.setText('Selected script: None')
            self.script_editor.setDisabled(True)
            self.script_editor.setToolTip('Select script first to edit')
            self.script_editor_path = ''
            self.script_action_run.setDisabled(True)
            self.script_action_abort.setDisabled(True)
            return

        name = self.script_selection_list.item(list_idx).text()

        self.saveScript()

        self.script_editor.clear()
        self.script_selected_headline.setText('Selected script: None')
        self.script_editor.setDisabled(True)
        self.script_editor.setToolTip('Select script first to edit')

        # open new script file
        script_path = str(join(self.path_scripts, f'{name}'))
        if not self.loadScript(script_path):
            return

        self.script_editor_path = script_path
        self.script_selected_headline.setText(f'Selected script: {name}')
        self.script_editor.setDisabled(False)
        self.script_editor.setToolTip('')
        self.script_action_run.setDisabled(False)

    def disableWidgets(self, state: bool):
        """Disables needed widgets"""

        self.script_selection_list.setDisabled(state)
        self.script_editor.setDisabled(state)

        self.script_action_run.setDisabled(state)
        self.script_action_abort.setEnabled(state)

        self.script_update_button.setDisabled(state)
        self.script_new_button.setDisabled(state)

    def runScript(self):
        """Run the given script"""

        self.saveScript()
        self.disableWidgets(True)

        self.script_run_progress.setValue(0)

        self.script_output.clear()

        try:
            self.script_server = ScriptServer(self.script_editor.toPlainText())
            self.script_server.log.connect(self.processLogScript)
            self.script_server.finish.connect(self.processFinishScript)
            self.script_server.start()

        except ValueError as error:
            self.script_output.setPlainText(str(error))
            self.abortScript()
            return

    def abortScript(self):
        """Abort the script"""

        # stop script server
        if self.script_server is not None:
            self.script_server.stop()
            self.script_server = None

        self.disableWidgets(False)

        self.script_run_progress.setValue(0)

    def processFinishScript(self):
        """Processes finished script"""

        self.disableWidgets(False)

        self.script_run_progress.setValue(100)


    def processLogScript(self, log: str):
        """Processes the log messages of the script running"""

        self.script_output.appendPlainText(log)

        if self.script_server is None:
            return

        if not self.script_server.command_queue.queue:
            self.script_run_progress.setValue(0)
        else:
            self.script_run_progress.setValue(round(100 * self.script_server.command_queue_idx / len(self.script_server.command_queue.queue)))

    def closeEvent(self, event):
        """Save current script editor"""

        self.abortScript()
        self.saveScript()
