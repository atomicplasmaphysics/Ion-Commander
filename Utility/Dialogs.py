from locale import getpreferredencoding
from os import path
from time import time
from datetime import datetime


from PyQt6.QtCore import Qt, QThreadPool, QObject, QRunnable, pyqtSignal, pyqtSlot, QProcess, QDir
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QCheckBox, QHBoxLayout, QWidget, QProgressBar, QTextEdit, QMessageBox
from PyQt6.QtGui import QFont


from Utility.Layouts import InputHBoxLayout, DoubleSpinBox, SpinBox, SpinBoxRange, FilePath
from Utility.FileDialogs import selectFileDialog
from Utility.LMFConvert import LM


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

    :param filename: name of file
    """

    def __init__(
        self,
        filename: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

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


class LMFDialog(QDialog):
    """
    Dialog for converting LMFs

    :param filename: name of file
    """

    class Worker(QRunnable):
        """
        Threaded worker for analyzing the LMF

        :param filename: name of file
        """

        class WorkerSignals(QObject):
            """
            Signals for worker

            result: new LM
            """

            result = pyqtSignal(object)

        def __init__(self, filename):
            super().__init__()
            self.filename = filename
            self.signals = self.WorkerSignals()
            self.lm = LM()

        @pyqtSlot()
        def run(self):
            """Called when worker is started"""

            self.lm.readLMF(self.filename, ignore_DAN=True, ignore_DAQ=True)
            self.signals.result.emit(self.lm)

    def __init__(
        self,
        filename: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.program = path.join(QDir.currentPath(), 'lmf2txt', 'lmf2txt.exe')
        self.total_process_log: list[tuple[float, str]] = []

        self.filename = filename
        self.finish_state = False

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)
        self.setWindowTitle('LMF converter')

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.info_label = QLabel(f'Provide LMF values for file <strong>"{self.filename}"</strong>')
        self.main_layout.addWidget(self.info_label)

        self.lm = LM()
        self.information_label = QLabel(f'<i>Analyzing LMF...</i>')
        self.main_layout.addWidget(self.information_label)

        split = 50

        # Start/Stop time
        self.time_start_input = DoubleSpinBox(default=0, decimals=3, input_range=SpinBoxRange.INF_INF)
        self.time_start_layout = InputHBoxLayout(
            'Start time [s]:',
            self.time_start_input,
            tooltip='Time chosen for start of LMF in seconds',
            split=split
        )
        self.main_layout.addLayout(self.time_start_layout)

        self.time_stop_input = DoubleSpinBox(default=3600, decimals=3, input_range=SpinBoxRange.INF_INF)
        self.time_stop_layout = InputHBoxLayout(
            'Stop time [s]:',
            self.time_stop_input,
            tooltip='Time chosen for stop of LMF in seconds',
            split=split
        )
        self.main_layout.addLayout(self.time_stop_layout)

        # Output file name
        first_output_filename = f'{self.filename[:-4]}.cod2'
        self.output_filename = FilePath(
            placeholder='Output File',
            function=lambda: selectFileDialog(
                self,
                for_saving=True,
                instruction='Select output file',
                start_dir=first_output_filename,
                file_filter='*.cod2'
            )
        )
        self.output_filename.setPath(first_output_filename)
        self.output_filename_layout = InputHBoxLayout(
            'Output file:',
            self.output_filename,
            tooltip='Path of the converted LMF file',
            split=split
        )
        self.main_layout.addLayout(self.output_filename_layout)

        # Convert button
        self.convert_button = QPushButton('Convert', self)
        self.convert_button.setToolTip('Convert LMF')
        self.convert_button.clicked.connect(self.startConverting)
        self.main_layout.addWidget(self.convert_button)

        # Process
        self.process = QProcess(self)
        self.process.readyRead.connect(self.processReadyRead)
        self.process.errorOccurred.connect(self.processError)
        self.process.finished.connect(self.processFinished)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setToolTip('Progress of conversion')
        self.progress_bar.setValue(0)
        self.main_layout.addWidget(self.progress_bar)

        # Console output
        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText('Console output')
        self.console_output.setToolTip('Console output')
        self.main_layout.addWidget(self.console_output)

        # Cancel button
        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.setToolTip('Cancel conversion')
        self.cancel_button.clicked.connect(self.close)
        self.main_layout.addWidget(self.cancel_button)

        self.analyzeLMF()

    def processReadyRead(self):
        """Converting process is ready to read"""

        process_log = self.process.readLine().data().decode(getpreferredencoding(), 'ignore').rstrip()
        self.total_process_log.append((time(), process_log))
        self.console_output.append(f'<i>{datetime.fromtimestamp(time()).strftime("%H:%M:%S")}</i>: {process_log}')

        try:
            percentage = float(process_log.split('(')[-1].split('%)')[0])
            percentage = min(100., percentage)
            percentage = max(0., percentage)
            self.progress_bar.setValue(round(percentage))
        except (ValueError, IndexError):
            pass

    def processError(self, error):
        """Converting process had error"""

        if isinstance(error, int):
            errors = {
                0: 'QProcess::FailedToStart',
                1: 'QProcess::Crashed',
                2: 'QProcess::Timed out',
                3: 'QProcess::WriteError',
                4: 'QProcess::ReadError',
                5: 'QProcess::UnknownError'
            }
            error = errors.get(error)
        self.information_label.setText(f'Error occurred while converting LMF: <i>{error}</i>.')

    def processFinished(self, exit_code: int, exit_status: int):
        """Converting process has finished"""

        self.progress_bar.setValue(100)
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            self.finish_state = True
            self.accept()
            return
        self.information_label.setText(f'Error occurred while converting LMF:<br> Code: {exit_code}<br> Status: {exit_status}')

    def startConverting(self):
        """Start converting the LMF"""

        self.time_start_input.setDisabled(True)
        self.time_stop_input.setDisabled(True)
        self.output_filename.setDisabled(True)

        self.process.setProgram(f'"{self.program}" "{self.filename}" -H -v -o "{self.output_filename.path}"')
        self.process.start()

    def analyzeLMF(self):
        """Analyze the LMF"""

        worker = self.Worker(self.filename)
        worker.signals.result.connect(self.updateLMF)
        threadpool = QThreadPool.globalInstance()
        threadpool.start(worker)

    def updateLMF(self, new_lm: LM):
        """Updates the LMF"""

        self.lm = new_lm
        total_time = self.lm.StopTime - self.lm.StartTime
        self.information_label.setText(f'File is <strong>{total_time:.3f}</strong> seconds long.<br>Bin size is <strong>{self.lm.TDC.TDCResolution * 1000:.3f} ps</strong>.')


class IPDialog(QDialog):
    """
    Dialog for entering IP address and port number

    :param ip: starting IP address
    :param port: starting port number
    :param title: title of the dialog
    """

    def __init__(
        self,
        *args,
        ip: tuple[int, int, int, int] = (0, 0, 0, 0),
        port: int = 0,
        title: str = '',
        info: str = '',
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)
        if not title:
            title = 'Specify IP and port'
        self.setWindowTitle(title)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        if info:
            info = f' for {info}'
        self.info_label = QLabel(f'Provide IP address and port number{info}')
        self.main_layout.addWidget(self.info_label)

        # IP address field
        ip_input_range = (0, 255)
        self.ip_1 = SpinBox(default=ip[0], input_range=ip_input_range)
        self.ip_2 = SpinBox(default=ip[1], input_range=ip_input_range)
        self.ip_3 = SpinBox(default=ip[2], input_range=ip_input_range)
        self.ip_4 = SpinBox(default=ip[3], input_range=ip_input_range)

        self.hbox_ip = QHBoxLayout()
        self.hbox_ip.addWidget(self.ip_1)
        self.hbox_ip.addWidget(QLabel('.'))
        self.hbox_ip.addWidget(self.ip_2)
        self.hbox_ip.addWidget(QLabel('.'))
        self.hbox_ip.addWidget(self.ip_3)
        self.hbox_ip.addWidget(QLabel('.'))
        self.hbox_ip.addWidget(self.ip_4)

        self.ip_widget = QWidget()
        self.ip_widget.setLayout(self.hbox_ip)

        self.ip_layout = InputHBoxLayout(
            'IP address:',
            self.ip_widget,
            tooltip='Select IP address',
            split=0
        )
        self.main_layout.addLayout(self.ip_layout)

        # port number field
        self.port = SpinBox(default=port, input_range=SpinBoxRange.ZERO_INF)
        self.port_layout = InputHBoxLayout(
            'Port number:',
            self.port,
            tooltip='Select port number',
            split=0
        )
        self.main_layout.addLayout(self.port_layout)

        self.ok_button = QPushButton('Ok', self)
        self.ok_button.setToolTip('Update values')
        self.ok_button.clicked.connect(self.accept)
        self.main_layout.addWidget(self.ok_button)

    def getIP(self) -> tuple[int, int, int, int]:
        """Get entered IP address"""
        return (
            self.ip_1.value(),
            self.ip_2.value(),
            self.ip_3.value(),
            self.ip_4.value()
        )

    def getPort(self) -> int:
        """Get entered port number"""
        return self.port.value()
