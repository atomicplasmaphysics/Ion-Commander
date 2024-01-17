from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QCheckBox
from PyQt6.QtGui import QFont


from Utility.Layouts import InputHBoxLayout, DoubleSpinBox, SpinBox, SpinBoxRange


def selectFileDialog(
    parent,
    for_saving: bool,
    instruction: str,
    start_dir: str,
    file_filter: str = '',
    multiple: bool = False
) -> None | str | list[str]:
    """
    Dialog window for selecting a file

    :param parent: parent widget
    :param for_saving: save (True) or open (False)
    :param instruction: instruction text
    :param start_dir: starting directory
    :param file_filter: (optional) filter for allowed files
    :param multiple: (optional) multiple files allowed

    :return: path as string (one file) or list of strings (multiple files) or None (no files)
    """

    full_file_paths = []

    if for_saving:
        full_file_path, _ = QFileDialog.getSaveFileName(parent, instruction, start_dir, file_filter)
        full_file_paths.append(full_file_path)

    else:
        if multiple:
            full_file_paths, _ = QFileDialog.getOpenFileNames(parent, instruction, start_dir, file_filter)

        else:
            full_file_path, _ = QFileDialog.getOpenFileName(parent, instruction, start_dir, file_filter)
            full_file_paths.append(full_file_path)

    file_names = []

    for full_file_path in full_file_paths:
        file_names.append(QFileInfo(full_file_path).filePath())
    if len(file_names) == 0:
        return None
    if len(file_names) == 1 and not multiple:
        return file_names[0]
    else:
        return file_names


def showMessageBox(
    parent,
    icon: QMessageBox.Icon,
    window_title: str,
    text: str,
    info_message: str = '',
    detailed_message: str = '',
    standard_buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    check_box_text: str = '',
    expand_details: bool = False
):
    """
    Displays message box

    :param parent: parent widget
    :param icon: icon for message box (e.g. QMessageBox.Icon.Warning)
    :param window_title: title of message box
    :param text: text of message box
    :param info_message: (optional) informative text of message box
    :param detailed_message: (optional) detailed text of message box
    :param standard_buttons: (optional) buttons of message box
    :param check_box_text: (optional) if set a checkbox with this text is displayed
    :param expand_details: (optional) automatically expand the details
    """

    msg_box = QMessageBox(icon, window_title, text, standard_buttons, parent)
    font = QFont()
    font.setBold(False)
    msg_box.setFont(font)
    msg_box.setInformativeText(info_message)
    msg_box.setDetailedText(detailed_message)

    if len(check_box_text) > 0:
        msg_box.setCheckBox(QCheckBox(check_box_text, msg_box))

    if expand_details:
        for button in msg_box.buttons():
            if msg_box.buttonRole(button) == QMessageBox.ButtonRole.ActionRole:
                button.click()
                break

    return msg_box, msg_box.exec()


class TACDialog(QDialog):
    """
    Dialog for entering TAC settings

    :param parent: parent widget
    :param filename: name of file
    """

    def __init__(self, parent, filename: str):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)
        self.setWindowTitle('Specify TAC values')

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.info_label = QLabel(f'Provide TAC values for file <strong>"{filename}"</strong>')
        self.main_layout.addWidget(self.info_label)

        # TAC time
        self.tac_input = SpinBox(
            default=50,
            input_range=SpinBoxRange.ZERO_INF
        )
        self.tac_layout = InputHBoxLayout(
            'TAC time [ns]:',
            self.tac_input,
            tooltip='Time chosen for TAC in nanoseconds',
            split=0
        )
        self.main_layout.addLayout(self.tac_layout)

        # delay time
        self.delay_input = DoubleSpinBox(
            default=0,
            input_range=SpinBoxRange.INF_INF
        )
        self.delay_layout = InputHBoxLayout(
            'Delay time [ns]:',
            self.delay_input,
            tooltip='Time chosen for delay in nanoseconds',
            split=0
        )
        self.main_layout.addLayout(self.delay_layout)

        self.ok_button = QPushButton('Ok', self)
        self.ok_button.setToolTip('Update values')
        self.ok_button.clicked.connect(self.accept)
        self.main_layout.addWidget(self.ok_button)
