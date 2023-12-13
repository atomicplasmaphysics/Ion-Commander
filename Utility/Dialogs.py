from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QLabel, QPushButton


from Utility.Layouts import InputHBoxLayout, DoubleSpinBox, SpinBox, SpinBoxRange


def selectFileDialog(parent, for_saving: bool, instruction: str, start_dir: str,
                     file_filter: str = '', multiple: bool = False) -> None | str | list[str]:
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
