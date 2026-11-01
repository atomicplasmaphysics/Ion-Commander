from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceDelayStageWrapper

from Utility.Layouts import ConnectButton, IconButton, InsertingGridLayout, IndicatorLed, LedButton, DoubleSpinBox, SpinBox, ComboBox, ReadingAgeLabel
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox
from Utility.Icons import getIcon

from Connection.USBPorts import getComports
from Connection.AdjustableDelayStage import AdjustableDelayStage, DelayStageStatus, MicrostepMode, A4988, IDENTIFICATION, SPEED_OF_LIGHT
from Connection.Threaded import ThreadedAdjustableDelayStage, ThreadedDummyConnection


class DelayStageVBoxLayout(QVBoxLayout):
    """
    Panel for the adjustable delay stage (stepper motor with a lead screw): delay, limit switches, moves and settings.
    Positions are shown as delay relative to the zero time.
    """

    # delays of the buttons [in ps]
    preset_times = (0.01, 0.1, 1, 10, 100, 1000)
    # interval of reading position and limit switches [in ms], also while moving
    status_interval = 200

    # driver board of the stage, the step size offers its microstepping modes
    driver = A4988

    answers = {
        'ERR motor_disabled': 'Motor is off, switch it on first',
        'ERR already_moving': 'Stage is still moving',
        'ERR limit1_active': 'Limit 1 is active (switch or disconnected wire): can only move in the other direction',
        'ERR limit2_active': 'Limit 2 is active (switch or disconnected wire): can only move in the other direction',
        'ERR stop_before_changing_speed_or_accel': 'Stop the stage before changing speed or acceleration',
        'ERR stop_before_changing_mode': 'Stop the stage before changing the step size',
        'ERR stop_before_zero': 'Stop the stage before setting the zero time',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.active_message_box = False

        self.modes: dict[str, MicrostepMode] = {f'1/{mode.value}' if mode.value > 1 else '1': mode for mode in self.driver.modes}

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('Delay stage', self.reconnect)

        self.device_wrapper = DeviceDelayStageWrapper()
        self.connection: None | AdjustableDelayStage = None

        self.status: DelayStageStatus | None = None
        self.status_pending = False
        self.zero_set = False
        self.message = ''

        self.update_timer = QTimer()
        self.update_timer.setInterval(self.status_interval)
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.start()

        # the longest possible delay limits the input fields
        time_maximum = DefaultParams.delay_stage_travel * DefaultParams.delay_stage_path_factor / SPEED_OF_LIGHT

        # Connection and Status Group Box
        self.connection_group_box = QGroupBox('Connection and Status')
        self.addWidget(self.connection_group_box)
        self.position_vbox = QVBoxLayout()
        self.connection_group_box.setLayout(self.position_vbox)
        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.position_vbox.addLayout(self.connection_hbox)
        self.connection_grid = InsertingGridLayout()
        self.connection_hbox.addLayout(self.connection_grid)

        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
        self.indicator_connection.setToolTip('Green if the delay stage is connected')
        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('COM port of the Arduino of the delay stage')
        self.button_connection = ConnectButton()
        self.button_connection.setToolTip('Connect to / disconnect from the selected port. Disconnecting stops the motor and switches it off')
        self.button_connection.pressed.connect(self.manualConnect)
        self.button_connection_refresh = IconButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(getIcon('refresh.svg'))
        self.button_connection_refresh.pressed.connect(self.setComportsComboBox)
        self.status_reading_age = ReadingAgeLabel()
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            self.combobox_connection,
            self.button_connection,
            self.button_connection_refresh,
            self.status_reading_age
        )

        self.position_hbox = QHBoxLayout()
        self.position_vbox.addLayout(self.position_hbox)
        self.label_time = QLabel('-')
        font = QFont()
        font.setPointSizeF(font.pointSizeF() * 1.5)
        font.setBold(True)
        self.label_time.setFont(font)
        self.label_time.setToolTip('Delay relative to the zero time')
        self.position_hbox.addWidget(self.label_time)
        self.label_length = QLabel('')
        self.label_length.setToolTip('Distance of the slide from the zero time')
        self.position_hbox.addWidget(self.label_length)
        self.position_hbox.addStretch(1)

        # buttons that start a move or need a stage at rest
        self.motion_buttons: list[QPushButton] = []
        self.preset_buttons: dict[QPushButton, float] = {}

        self.button_set_zero = self.motionButton('Set zero', 'The current position becomes the zero time (the stage does not move)', self.setZero)
        self.position_hbox.addWidget(self.button_set_zero)
        self.button_go_zero = self.motionButton('Go to zero', 'Moves back to the zero time', self.goZero)
        self.position_hbox.addWidget(self.button_go_zero)

        self.state_hbox = QHBoxLayout()
        self.position_vbox.addLayout(self.state_hbox)
        self.button_enable = LedButton()
        self.button_enable.setToolTip('Motor on/off (click to change). If it is on, the coils are powered also at rest and get warm')
        self.button_enable.clicked.connect(self.toggleEnable)
        self.state_hbox.addWidget(self.button_enable)
        self.state_hbox.addWidget(QLabel('Motor'))
        self.indicator_moving = IndicatorLed()
        self.indicator_moving.setToolTip('Green while the stage is moving')
        self.state_hbox.addWidget(self.indicator_moving)
        self.state_hbox.addWidget(QLabel('Moving'))
        self.indicator_limit1 = IndicatorLed(on_color=Colors.color_red)
        self.indicator_limit1.setToolTip('Limit 1 (end of the moves with positive motor steps), shown while the motor is on: green if free, red if the switch is activated or its wire is disconnected')
        self.state_hbox.addWidget(self.indicator_limit1)
        self.state_hbox.addWidget(QLabel('Limit 1'))
        self.indicator_limit2 = IndicatorLed(on_color=Colors.color_red)
        self.indicator_limit2.setToolTip('Limit 2 (end of the moves with negative motor steps), shown while the motor is on: green if free, red if the switch is activated or its wire is disconnected')
        self.state_hbox.addWidget(self.indicator_limit2)
        self.state_hbox.addWidget(QLabel('Limit 2'))
        self.state_hbox.addStretch(1)
        self.button_stop = QPushButton('Stop')
        self.button_stop.setToolTip('Stops the motor immediately')
        self.button_stop.pressed.connect(self.stop)
        self.state_hbox.addWidget(self.button_stop)

        self.label_message = QLabel('')
        self.label_message.setWordWrap(True)
        self.label_message.setToolTip('Why the stage does not move, and if the zero time is missing')
        self.position_vbox.addWidget(self.label_message)

        # Move Group Box
        self.move_group_box = QGroupBox('Move [ps]')
        self.addWidget(self.move_group_box)
        self.move_vbox = QVBoxLayout()
        self.move_group_box.setLayout(self.move_vbox)
        self.preset_hbox = QHBoxLayout()
        self.preset_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.move_vbox.addLayout(self.preset_hbox)
        self.preset_grid = InsertingGridLayout()
        self.preset_grid.setSpacing(2)
        self.preset_hbox.addLayout(self.preset_grid)
        self.move_hbox = QHBoxLayout()
        self.move_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.move_vbox.addLayout(self.move_hbox)
        self.move_grid = InsertingGridLayout()
        self.move_hbox.addLayout(self.move_grid)

        # one row per direction, one column per delay
        for sign in (1, -1):
            buttons = []
            for preset in self.preset_times:
                value = sign * preset
                button = self.motionButton(f'{value:+g}', f'Moves by {value:+g} ps (only available if the step size is small enough)', lambda _=False, time=value: self.moveBy(time))
                button.setMinimumWidth(0)
                button.setFixedWidth(button.fontMetrics().horizontalAdvance('+1000') + 28)
                self.preset_buttons[button] = preset
                buttons.append(button)
            self.preset_grid.addWidgets(*buttons)

        self.spinbox_move = DoubleSpinBox(default=10, input_range=(-time_maximum, time_maximum), decimals=3)
        self.spinbox_move.setToolTip('Delay to move by in ps')
        self.button_move = self.motionButton('Move', 'Moves by this delay, rounded to the step size', lambda: self.moveBy(self.spinbox_move.value()))

        self.spinbox_go = DoubleSpinBox(default=0, input_range=(-time_maximum, time_maximum), decimals=3)
        self.spinbox_go.setToolTip('Delay relative to the zero time to go to in ps')
        self.button_go = self.motionButton('Go', 'Moves to this delay relative to the zero time, rounded to the step size', self.goTo)
        self.move_grid.addWidgets(QLabel('Move by'), self.spinbox_move, self.button_move, QLabel('Go to'), self.spinbox_go, self.button_go)

        # Settings Group Box
        self.settings_group_box = QGroupBox()
        self.addWidget(self.settings_group_box)
        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.settings_group_box.setLayout(self.settings_hbox)
        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        self.spinbox_speed = SpinBox(default=GlobalConf.settings.value(GlobalConf.delay_stage_speed_name, defaultValue=10000, type=int), input_range=(1, 100000))
        self.spinbox_speed.setToolTip(f'Speed in 1/{self.driver.units_per_full_step} of a full step per second, independent of the step size (press enter to apply). An Arduino Uno probably does not reach the upper end of the range')
        self.spinbox_speed.editingFinished.connect(self.setSpeed)

        self.spinbox_acceleration = SpinBox(default=GlobalConf.settings.value(GlobalConf.delay_stage_acceleration_name, defaultValue=0, type=int), input_range=(0, 100000))
        self.spinbox_acceleration.setToolTip(f'Acceleration in 1/{self.driver.units_per_full_step} of a full step per second², 0: no ramp, starts and stops at full speed (press enter to apply)')
        self.spinbox_acceleration.editingFinished.connect(self.setAcceleration)

        # the finest step size if the stored one is not available on this driver
        mode_names = list(self.modes)
        mode_name = GlobalConf.settings.value(GlobalConf.delay_stage_mode_name, defaultValue=mode_names[-1], type=str)
        self.combobox_mode = ComboBox(
            default=mode_names.index(mode_name) if mode_name in mode_names else len(mode_names) - 1,
            entries=mode_names
        )
        self.combobox_mode.setToolTip(f'Step size of the {self.driver.name} driver (microstepping) as part of a full step: smallest possible change of the delay')
        self.combobox_mode.currentIndexChanged.connect(self.setMode)
        self.settings_grid.addWidgets(QLabel('Speed'), self.spinbox_speed, QLabel('Accel.'), self.spinbox_acceleration, QLabel('Step size'), self.combobox_mode)

        self.updateSettingLabels()
        self.spinbox_speed.valueChanged.connect(self.updateSettingLabels)
        self.spinbox_acceleration.valueChanged.connect(self.updateSettingLabels)

        self.reset()

        last_connection = GlobalConf.getConnection('delay_stage')
        if last_connection:
            self.connect(last_connection, False)

    def motionButton(self, text: str, tooltip: str, function) -> QPushButton:
        """
        Returns a button that is only available if the stage is connected and at rest

        :param text: text of button
        :param tooltip: tooltip of button
        :param function: function called on click
        """

        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.clicked.connect(function)
        self.motion_buttons.append(button)
        return button

    def selectedMode(self) -> MicrostepMode:
        """Returns the selected step size"""
        return self.modes[self.combobox_mode.getValue(text=True)]

    def updateSettingLabels(self):
        """Shows the settings as delay in the title of the settings"""

        time_per_position = abs(self.driver.positionToTime(1))
        speed = self.spinbox_speed.value()
        acceleration = self.spinbox_acceleration.value()
        ramp = f'{speed / acceleration:.3g} s ramp' if acceleration else 'no ramp'
        step = time_per_position * self.driver.unitsPerStep(self.selectedMode()) * 1000
        self.settings_group_box.setTitle(f'Settings: {time_per_position * speed:.3g} ps/s, {ramp}, {step:.3g} fs per step')
        self.settings_group_box.setToolTip(f'The slide moves with {self.driver.positionToLength(speed):.3g} mm/s')

    # ------------------------------------------------------------------ connection
    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('Delay stage: Connection lost')
        self.unconnect()
        if self.last_port:
            self.auto_reconnect.start()

    def reconnect(self) -> bool:
        """Tries to reconnect silently to the last port, returns True if connected"""

        if not self.device_wrapper.threaded_connection.isDummy():
            return True
        self.connect(self.last_port, False)
        return self.indicator_connection.value()

    def connect(self, comport: str = '', messagebox: bool = True):
        """
        Connect to given comport. If no comport is given, the selected comport will be connected to

        :param comport: comport to connect to
        :param messagebox: show messagebox if failed
        """

        if not comport:
            comport = self.combobox_connection.getValue(text=True)
        self.setComport(comport)

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if not connect:
            return

        self.connection = AdjustableDelayStage(comport, strict=IDENTIFICATION, driver=self.driver)
        try:
            self.connection.open()
            self.device_wrapper.threaded_connection = ThreadedAdjustableDelayStage(self.connection, self.connectionLost)
            self.last_port = comport
            self.indicator_connection.setValue(True)
            self.combobox_connection.setEnabled(False)
            self.button_connection_refresh.setEnabled(False)
            self.button_connection.setConnected(True)

            # the stage works with the selected settings, the motor stays as it is
            self.setMode()
            self.setSpeed()
            self.setAcceleration()
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showZeroed, threaded.getZeroed())

        except (ConnectionError, OSError) as error:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
            self.reset()
            GlobalConf.logger.info(f'Connection error! Could not connect to the delay stage on port "{comport}", because of: {error}')
            if messagebox:
                showMessageBox(
                    None,
                    QMessageBox.Icon.Critical,
                    'Connection error!',
                    f'Could not connect to the delay stage on port "{comport}"!',
                    f'<strong>Encountered Error:</strong><br>{error}',
                    expand_details=False
                )

    def unconnect(self):
        """Disconnect from any port (the motor stops and is switched off)"""

        self.device_wrapper.threaded_connection.close()
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception as error:
                GlobalConf.logger.debug(f'Delay stage: error while closing: {error}')
            self.connection = None

        comport = self.combobox_connection.getValue(text=True)
        self.reset()
        self.setComport(comport)

    def setComport(self, comport: str):
        """Selects the comport in the list of comports"""

        entries = {port.lower(): i for i, port in enumerate(self.combobox_connection.entries)}
        if comport.lower() in entries:
            self.combobox_connection.setCurrentIndex(entries[comport.lower()])

    def setComportsComboBox(self):
        """Sets available ports in the comports combobox"""

        comports = getComports(not_available_entry=True)
        self.combobox_connection.reinitialize(
            entries=[port for port, _, _ in comports],
            tooltips=[f'{port}: {description} [{hardware_id}]' for port, description, hardware_id in comports]
        )

    def reset(self):
        """Resets everything to default"""

        self.status_pending = False
        self.status = None
        self.zero_set = False
        self.message = ''
        self.indicator_connection.setValue(False)
        self.button_connection.setConnected(False)
        self.combobox_connection.setEnabled(True)
        self.button_connection_refresh.setEnabled(True)
        self.label_time.setText('-')
        self.label_length.setText('')
        self.button_enable.setValue(False)
        self.indicator_moving.setValue(False)
        self.showLimit(self.indicator_limit1, None)
        self.showLimit(self.indicator_limit2, None)
        self.setComportsComboBox()
        self.updateButtons()
        self.showMessage()

    @staticmethod
    def showLimit(indicator: IndicatorLed, active: bool | None):
        """
        Shows a limit switch

        :param indicator: led of the switch
        :param active: limit is active, None if it is not known (led is off)
        """

        indicator.off_color = Colors.app_background if active is None else Colors.color_green
        indicator.setValue(bool(active))

    def checkConnection(self, messagebox: bool = True) -> bool:
        """Checks if the delay stage is connected"""

        if self.indicator_connection.value():
            return True
        if messagebox and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(None, QMessageBox.Icon.Warning, 'Connection warning!', 'Delay stage is not connected, please connect first!')
            self.active_message_box = False
        return False

    # ------------------------------------------------------------------ settings
    def setSpeed(self):
        """Sets the speed"""
        if self.checkConnection(False):
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.setSpeed(self.spinbox_speed.value()))

    def setAcceleration(self):
        """Sets the acceleration"""
        if self.checkConnection(False):
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.setAccel(self.spinbox_acceleration.value()))

    def setMode(self):
        """Sets the step size"""
        self.updateSettingLabels()
        self.updateButtons()
        if self.checkConnection(False):
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.setMode(self.selectedMode()))

    def toggleEnable(self):
        """Switches the motor on/off"""
        if self.checkConnection():
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.setEnable(not self.button_enable.value()))

    # ------------------------------------------------------------------ moves
    def stop(self):
        """Stops the motor"""
        if self.checkConnection(False):
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.halt())

    def moveBy(self, time: float):
        """
        Moves by a delay

        :param time: delay [in ps]
        """

        if self.checkConnection():
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.moveTime(time))

    def goTo(self):
        """Moves to the selected delay relative to the zero time"""

        if self.checkConnection():
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.moveToTime(self.spinbox_go.value()))

    def goZero(self):
        """Moves back to the zero time"""

        if self.checkConnection():
            threaded = self.device_wrapper.threaded_connection
            threaded.callback(self.showAnswer, threaded.moveZero())

    def setZero(self):
        """The current position becomes the zero time (an existing zero time is only replaced after asking)"""

        if not self.checkConnection():
            return

        if self.zero_set and self.status is not None and self.status.position != 0:
            _, answer = showMessageBox(
                None,
                QMessageBox.Icon.Question,
                'Set zero time?',
                f'Replace the zero time? It is {self.timeText(self.status.position)} away from the current position.',
                standard_buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        threaded = self.device_wrapper.threaded_connection
        threaded.callback(self.zeroAnswer, threaded.setZero())

    def zeroAnswer(self, answer):
        """Answer of setting the zero time"""

        self.showAnswer(answer)
        if answer == 'OK':
            self.zero_set = True
            self.updateButtons()
            self.showMessage()

    def showZeroed(self, zeroed):
        """Shows if the Arduino still knows its zero time"""

        self.zero_set = zeroed is True
        self.updateButtons()
        self.showMessage()

    def showAnswer(self, answer):
        """
        Shows the answer of a command: nothing if it was successful, otherwise why not

        :param answer: answer of the device or an exception
        """

        self.message = '' if answer == 'OK' else self.answers.get(answer, str(answer))
        self.showMessage()

    def showMessage(self):
        """Shows the last problem and the warnings of the current state"""

        messages = [self.message] if self.message else []
        if self.status is not None:
            if not self.zero_set:
                messages.append('Zero time not set (the Arduino restarted): the delay is relative to its start position')
        self.label_message.setText('\n'.join(messages))
        self.label_message.setVisible(bool(messages))
        self.label_message.setStyleSheet(f'color: {Colors.color_red};' if messages else '')

    def updateButtons(self):
        """Buttons for moves are only available if the stage is connected and at rest"""

        available = self.status is not None and not self.status.moving
        for button in self.motion_buttons:
            button.setEnabled(available)
        self.button_go_zero.setEnabled(available and self.zero_set)
        self.button_go.setEnabled(available and self.zero_set)
        # a delay smaller than a step would not move or be far off
        step = abs(self.driver.positionToTime(self.driver.unitsPerStep(self.selectedMode())))
        for button, preset in self.preset_buttons.items():
            button.setEnabled(available and preset >= step)
        self.button_stop.setEnabled(self.status is not None)

    # ------------------------------------------------------------------ readings
    def updateLoop(self):
        """Called by timer; requests a new status (only one request at a time)"""

        connected = self.indicator_connection.value()
        self.status_reading_age.setAge(self.device_wrapper.threaded_connection.secondsSinceLastResult(), connected)
        if not connected or self.status_pending:
            return
        self.status_pending = True
        threaded = self.device_wrapper.threaded_connection
        threaded.callback(self.showStatus, threaded.getStatus())

    def timeText(self, position: int) -> str:
        """Returns a position as text of the delay"""
        return f'{self.driver.positionToTime(position):+.3f} ps'

    def showStatus(self, status):
        """Shows the status of the stage"""

        self.status_pending = False
        if not isinstance(status, DelayStageStatus):
            GlobalConf.logger.error(f'Delay stage: invalid status {status}')
            return

        self.status = status
        self.label_time.setText(self.timeText(status.position))
        self.label_length.setText(f'({self.driver.positionToLength(status.position):+.3f} mm)')
        self.button_enable.setValue(status.enabled)
        self.indicator_moving.setValue(status.moving)
        self.showLimit(self.indicator_limit1, AdjustableDelayStage.LimitSwitch.LIMIT1 in status.limits if status.enabled else None)
        self.showLimit(self.indicator_limit2, AdjustableDelayStage.LimitSwitch.LIMIT2 in status.limits if status.enabled else None)
        self.updateButtons()
        self.showMessage()

    def timeForLog(self) -> float | None:
        """Returns the delay of the last status in ps, None if there is none"""

        if self.status is None:
            return None
        return self.driver.positionToTime(self.status.position)

    def closeEvent(self):
        """Must be called when application is closed"""

        self.update_timer.stop()
        self.device_wrapper.threaded_connection.close()

        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port
        self.auto_reconnect.stop()
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass

        GlobalConf.updateConnections(delay_stage=last_connection)
        GlobalConf.settings.setValue(GlobalConf.delay_stage_speed_name, self.spinbox_speed.value())
        GlobalConf.settings.setValue(GlobalConf.delay_stage_acceleration_name, self.spinbox_acceleration.value())
        GlobalConf.settings.setValue(GlobalConf.delay_stage_mode_name, self.combobox_mode.getValue(text=True))

    def log(self, db: DB):
        """Logs the delay"""

        if not self.checkConnection(False) or self.status is None:
            return
        db.insertDelayStage(self.timeForLog())
