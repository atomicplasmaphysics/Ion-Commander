from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, DoubleSpinBox, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.AdjustableDelayStage import DelayStageStatus


class DelayStageCalibrationDialog(QDialog):
    """
    Dialog to calibrate the distance of the slide per motor rotation: the stage moves a known number of steps, the
    distance is measured by hand and gives the lead. Motor, speed and step size stay in the panel, which remains usable.

    :param panel: panel of the delay stage
    :param parent: parent widget
    """

    # distance to move first, so the measurement starts without the play of the screw [in mm]
    prepare_distance = 2.

    # a larger change of the lead is asked for, it is probably a mistake when measuring [in %]
    warn_deviation = 5.

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Delay stage calibration')

        self.panel = panel
        self.driver = panel.driver
        self.finished_function = None
        self.start_position: int | None = None
        self.expected = 0
        self.moved = 0
        self.status_pending = False

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(100)
        self.poll_timer.timeout.connect(self.poll)

        self.main_layout = QVBoxLayout(self)

        self.label_info = QLabel(
            '1. Switch on the motor in the panel, set the direction with enough free way.\n'
            '2. "Prepare" moves a little in this direction to take out the play of the screw. Measure the start position.\n'
            '3. "Move" moves the distance. Measure the end position.\n'
            '4. Enter the measured distance and apply it.'
        )
        self.main_layout.addWidget(self.label_info)

        self.grid = InsertingGridLayout()
        self.main_layout.addLayout(self.grid)

        self.spinbox_distance = DoubleSpinBox(default=150, input_range=(1, DefaultParams.delay_stage_travel), decimals=1)
        self.spinbox_distance.setToolTip('Distance to move with the current lead: as long as possible for an accurate result, but measurable (calliper: 18 cm)')
        self.spinbox_distance.valueChanged.connect(self.updateLabels)
        self.label_steps = QLabel('')
        self.grid.addWidgets(QLabel('Distance [mm]'), self.spinbox_distance, self.label_steps)

        self.combobox_direction = ComboBox(entries=['Longer delay', 'Shorter delay'])
        self.combobox_direction.setToolTip('Direction of the moves')
        self.grid.addWidgets(QLabel('Direction'), self.combobox_direction)

        self.spinbox_measured = DoubleSpinBox(default=150, input_range=(0.01, 10000), decimals=2)
        self.spinbox_measured.setToolTip('Measured distance between the start and the end position')
        self.spinbox_measured.valueChanged.connect(self.updateLabels)
        self.label_result = QLabel('')
        self.grid.addWidgets(QLabel('Measured [mm]'), self.spinbox_measured, self.label_result)

        self.buttons_hbox = QHBoxLayout()
        self.main_layout.addLayout(self.buttons_hbox)
        self.button_prepare = QPushButton('Prepare')
        self.button_prepare.setToolTip(f'Moves {self.prepare_distance:g} mm in the selected direction, then measure the start position')
        self.button_prepare.clicked.connect(self.prepare)
        self.buttons_hbox.addWidget(self.button_prepare)
        self.button_move = QPushButton('Move')
        self.button_move.setToolTip('Moves the distance in the selected direction, then measure the end position')
        self.button_move.clicked.connect(self.move)
        self.buttons_hbox.addWidget(self.button_move)
        self.button_stop = QPushButton('Stop')
        self.button_stop.setToolTip('Stops the motor immediately (the move then does not count)')
        self.button_stop.clicked.connect(self.panel.stop)
        self.buttons_hbox.addWidget(self.button_stop)
        self.button_apply = QPushButton('Apply')
        self.button_apply.setToolTip('Stores the new lead (used immediately, also in the preferences). The zero time stays at the same position of the stage')
        self.button_apply.setEnabled(False)
        self.button_apply.clicked.connect(self.apply)
        self.buttons_hbox.addWidget(self.button_apply)

        self.label_status = QLabel('')
        self.label_status.setWordWrap(True)
        self.main_layout.addWidget(self.label_status)

        self.updateLabels()

    def distanceUnits(self, distance: float) -> int:
        """
        Returns a signed position difference [in 16th-steps] in the selected direction

        :param distance: distance with the current lead [in mm]
        """

        longer = self.combobox_direction.currentIndex() == 0
        positive = (self.driver.positionToTime(1) > 0) == longer
        units = round(distance / DefaultParams.delay_stage_lead * self.driver.units_per_rotation)
        return units if positive else -units

    def newLead(self) -> float:
        """Returns the lead that follows from the last move and the measured distance [in mm]"""
        return self.spinbox_measured.value() * self.driver.units_per_rotation / abs(self.moved)

    def updateLabels(self):
        """Shows what the distance means and what the measured distance gives"""

        units = round(self.spinbox_distance.value() / DefaultParams.delay_stage_lead * self.driver.units_per_rotation)
        seconds = units / self.panel.spinbox_speed.value()
        self.label_steps.setText(f'= {units / self.driver.units_per_rotation:g} rotations, {units} 1/{self.driver.units_per_full_step} steps, about {seconds:.0f} s')

        if self.moved:
            lead = self.newLead()
            deviation = (lead / DefaultParams.delay_stage_lead - 1) * 100
            self.label_result.setText(f'Lead {DefaultParams.delay_stage_lead:.4f} -> {lead:.4f} mm/rotation ({deviation:+.2f} %)')
        else:
            self.label_result.setText(f'Lead {DefaultParams.delay_stage_lead:.4f} mm/rotation')

    def showStatus(self, text: str, error: bool = False):
        """
        Shows what happens

        :param text: text to show
        :param error: show as a problem
        """

        self.label_status.setText(text)
        self.label_status.setStyleSheet(f'color: {Colors.color_red};' if error else '')

    def setBusy(self, busy: bool):
        """No other move can be started while one is running"""

        self.button_prepare.setEnabled(not busy)
        self.button_move.setEnabled(not busy)

    def prepare(self):
        """Moves a little to take out the play of the screw"""

        self.moved = 0
        self.button_apply.setEnabled(False)
        self.startMove(self.prepare_distance, self.prepareFinished)

    def prepareFinished(self):
        """The play is out"""
        self.showStatus('Prepared: measure the start position, then press "Move".')

    def move(self):
        """Moves the distance"""

        self.moved = 0
        self.button_apply.setEnabled(False)
        self.startMove(self.spinbox_distance.value(), self.moveFinished)

    def moveFinished(self):
        """The distance was moved, it can be measured"""

        self.moved = self.expected
        self.spinbox_measured.setValue(abs(self.driver.positionToLength(self.moved)))
        self.button_apply.setEnabled(True)
        self.updateLabels()
        self.showStatus(f'Moved {abs(self.moved)} 1/{self.driver.units_per_full_step} steps: measure the end position and enter the distance.')

    def startMove(self, distance: float, finished_function):
        """
        Starts a move, whole steps of the selected step size

        :param distance: distance with the current lead [in mm]
        :param finished_function: called if the stage moved completely
        """

        if not self.panel.checkConnection():
            return

        step = self.driver.unitsPerStep(self.panel.selectedMode())
        steps = round(self.distanceUnits(distance) / step)
        self.expected = steps * step
        self.finished_function = finished_function
        self.start_position = None
        self.setBusy(True)
        self.showStatus('Moving ...')

        threaded = self.panel.device_wrapper.threaded_connection
        threaded.callback(self.storeStart, threaded.getPos())
        threaded.callback(self.moveAnswer, threaded.move(steps))

    def storeStart(self, position):
        """Stores the position before the move"""
        self.start_position = position if isinstance(position, int) else None

    def moveAnswer(self, answer):
        """Answer of the move command: it runs now, or why not"""

        if answer == 'OK' and self.start_position is not None:
            self.status_pending = False
            self.poll_timer.start()
            return
        self.setBusy(False)
        self.showStatus(self.panel.answers.get(answer, str(answer)), error=True)

    def poll(self):
        """Asks if the move is finished"""

        if not self.panel.checkConnection(False):
            self.poll_timer.stop()
            self.setBusy(False)
            self.showStatus('Connection lost, the move does not count.', error=True)
            return

        if self.status_pending:
            return
        self.status_pending = True
        threaded = self.panel.device_wrapper.threaded_connection
        threaded.callback(self.showPoll, threaded.getStatus())

    def showPoll(self, status):
        """A finished move only counts if the stage moved the whole way"""

        self.status_pending = False
        if not isinstance(status, DelayStageStatus) or status.moving:
            return

        self.poll_timer.stop()
        self.setBusy(False)
        moved = status.position - self.start_position
        if moved != self.expected:
            self.showStatus(f'The stage stopped early ({moved} of {self.expected} 1/{self.driver.units_per_full_step} steps: limit switch or stop), this move does not count.', error=True)
            return
        self.finished_function()

    def apply(self):
        """Stores the new lead"""

        lead = self.newLead()
        deviation = (lead / DefaultParams.delay_stage_lead - 1) * 100
        if abs(deviation) > self.warn_deviation:
            _, answer = showMessageBox(
                self,
                QMessageBox.Icon.Warning,
                'Large change!',
                f'The lead would change by {deviation:+.1f} %, to {lead:.4f} mm per rotation. Is the measured distance right?',
                standard_buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            DefaultParams.saveOverride(GlobalConf.settings, 'delay_stage_lead', lead, GlobalConf.default_params_group_name)
        except ValueError as error:
            self.showStatus(str(error), error=True)
            return

        GlobalConf.logger.info(f'Delay stage: lead calibrated to {lead} mm/rotation ({deviation:+.2f} %)')
        self.moved = 0
        self.button_apply.setEnabled(False)
        self.panel.updateSettingLabels()
        self.updateLabels()
        self.showStatus(f'Stored: {lead:.4f} mm per rotation.')

    def closeEvent(self, event):
        """A running move does not continue unattended"""

        if self.poll_timer.isActive():
            self.poll_timer.stop()
            self.panel.stop()
        super().closeEvent(event)
