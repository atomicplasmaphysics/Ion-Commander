from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors, Styles

from Utility.Layouts import InsertingGridLayout, IndicatorLed, ErrorTable, DoubleSpinBox, ComboBox, DisplayLabel
from Utility.Dialogs import IPDialog, showMessageBox

from Connection.Monaco import MonacoConnection
from Connection.Threaded import ThreadedMonacoConnection, ThreadedDummyConnection, ThreadedConnection


class LaserVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Local variables
        # TODO: get this variables form GlobalConfig
        self.ip = (169, 254, 21, 151)
        self.port = 23

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(GlobalConf.update_timer_time)
        self.update_timer.start()

        self.active_message_box = False

        self.connection: None | MonacoConnection = None
        self.threaded_connection: ThreadedDummyConnection | ThreadedMonacoConnection = ThreadedDummyConnection()

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection and Status')
        self.addWidget(self.connection_group_box)

        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_group_box.setLayout(self.connection_hbox)

        self.connection_grid = InsertingGridLayout()
        self.connection_hbox.addLayout(self.connection_grid)

        # Connection
        self.label_connection = QLabel('Connection')
        self.indicator_connection = IndicatorLed(clickable=True, size=Styles.indicator_size, off_color=Colors.cooperate_error)
        self.status_connection = QLabel('Not connected')
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.button_connection_settings = QPushButton()
        self.button_connection_settings.setIcon(QIcon('icons/preferences.png'))
        self.button_connection_settings.pressed.connect(self.connectionPreferences)
        self.connection_grid.addWidgets(
            self.label_connection,
            self.indicator_connection,
            self.status_connection,
            self.button_connection,
            self.button_connection_settings
        )

        # Key-switch
        self.label_key_switch = QLabel('Key-Switch')
        self.indicator_key_switch = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_key_switch = QLabel('Key off')
        self.connection_grid.addWidgets(
            self.label_key_switch,
            self.indicator_key_switch,
            self.status_key_switch
        )

        # Shutter
        self.label_shutter = QLabel('Shutter')
        self.indicator_shutter = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_shutter = QLabel('Closed')
        self.button_shutter = QPushButton('Open')
        self.connection_grid.addWidgets(
            self.label_shutter,
            self.indicator_shutter,
            self.status_shutter,
            self.button_shutter
        )

        # Pulsing
        self.label_pulsing = QLabel('Pulsing')
        self.indicator_pulsing = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_pulsing = QLabel('Off')
        self.button_pulsing = QPushButton('On')
        self.connection_grid.addWidgets(
            self.label_pulsing,
            self.indicator_pulsing,
            self.status_pulsing,
            self.button_pulsing
        )

        # System status
        self.label_system_status = QLabel('System Status')
        self.indicator_system_status = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_system_status = QLabel('Standby')
        self.button_system_status = QPushButton('Start')
        self.connection_grid.addWidgets(
            self.label_system_status,
            self.indicator_system_status,
            self.status_system_status,
            self.button_system_status
        )

        # Chiller Group Box
        self.chiller_group_box = QGroupBox('Chiller')
        self.addWidget(self.chiller_group_box)

        self.chiller_hbox = QHBoxLayout()
        self.chiller_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.chiller_group_box.setLayout(self.chiller_hbox)

        self.chiller_grid = InsertingGridLayout()
        self.chiller_hbox.addLayout(self.chiller_grid)

        # Chiller Temperature
        self.label_chiller_temperature = QLabel('Chiller Temperature')
        self.indicator_chiller_temperature = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_chiller_temperature = DisplayLabel(value=0.8, unit='°C', alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.spinbox_chiller_temperature = DoubleSpinBox(step_size=0.1, input_range=(18, 35), decimals=1, buttons=True)
        self.chiller_grid.addWidgets(
            self.label_chiller_temperature,
            self.indicator_chiller_temperature,
            self.status_chiller_temperature,
            self.spinbox_chiller_temperature
        )

        # Baseplate Temperature
        self.label_baseplate_temperature = QLabel('Baseplate Temperature')
        self.indicator_baseplate_temperature = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_baseplate_temperature = DisplayLabel(value=0.75, unit='°C', alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.chiller_grid.addWidgets(
            self.label_baseplate_temperature,
            self.indicator_baseplate_temperature,
            self.status_baseplate_temperature
        )

        # Chiller Flow
        self.label_chiller_flow = QLabel('Chiller Flow')
        self.indicator_chiller_flow = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_chiller_flow = DisplayLabel(value=0.1, unit='lpm', decimals=1, alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.chiller_grid.addWidgets(
            self.label_chiller_flow,
            self.indicator_chiller_flow,
            self.status_chiller_flow
        )

        # Faults Group Box
        self.faults_group_box = QGroupBox('Faults')
        self.addWidget(self.faults_group_box)

        self.faults_vbox = QVBoxLayout()
        self.faults_group_box.setLayout(self.faults_vbox)

        self.faults_hbox = QHBoxLayout()
        self.faults_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.faults_vbox.addLayout(self.faults_hbox)

        self.faults_grid = InsertingGridLayout()
        self.faults_hbox.addLayout(self.faults_grid)

        # System faults
        self.button_system_faults = QPushButton('Clear')
        # TODO: change connected lambda-function
        self.button_system_faults.clicked.connect(lambda: self.table_system_faults.resetTable())
        self.indicator_system_faults = IndicatorLed(clickable=True, size=Styles.indicator_size)
        self.status_system_faults = QLabel('No faults')
        self.faults_grid.addWidgets(
            self.button_system_faults,
            self.indicator_system_faults,
            self.status_system_faults
        )

        # System faults table
        self.table_system_faults = ErrorTable()
        self.faults_vbox.addWidget(self.table_system_faults)

        for i in range(5):
            self.table_system_faults.insertError(i, f'Type {i}', f'Pretty long and unusefull description of error from state {i}')

        # Settings Group Box
        self.settings_group_box = QGroupBox('Settings')
        self.addWidget(self.settings_group_box)

        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.settings_group_box.setLayout(self.settings_hbox)

        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        # Amplifier Settings
        self.combobox_settings_amplifier = ComboBox()
        self.settings_grid.addWidgets(
            QLabel('Amplifier'),
            self.combobox_settings_amplifier
        )

        # Output Settings
        self.combobox_settings_output = ComboBox()
        self.status_settings_output = DisplayLabel(value=1, unit='Hz', alignment_flag=Qt.AlignmentFlag.AlignLeft)
        self.settings_grid.addWidgets(
            QLabel('Output'),
            self.combobox_settings_output,
            self.status_settings_output
        )

        # RF Level Settings
        self.spinbox_settings_rflvel = DoubleSpinBox(step_size=0.1, input_range=(0, 100), decimals=1, buttons=False)
        self.settings_grid.addWidgets(
            QLabel('RF Level'),
            self.spinbox_settings_rflvel
        )

        # Pulse Width Settings
        self.spinbox_settings_pulsewidth = DoubleSpinBox(step_size=0.1, input_range=(276, 10000), decimals=1, buttons=False)
        self.settings_grid.addWidgets(
            QLabel('Pulse Width'),
            self.spinbox_settings_pulsewidth
        )

        # TODO: remove this hardcoded value, but load it from settings and set comport on startup to last set comport
        # self.connect((169, 254, 21, 151), 23, False)

        self.reset()

    def updateLoop(self):
        """Called by timer; Updates actual voltages"""
        pass

    def updateAllValues(self):
        """Updates all values"""
        pass

    def connectionPreferences(self):
        """Open dialog to get user input on IP address and port number of laser"""

        ip_dialog = IPDialog(ip=self.ip, port=self.port, info='Monaco Laser')
        ip_dialog.exec()
        self.ip = ip_dialog.getIP()
        self.port = ip_dialog.getPort()

    def connect(self, ip: tuple[int, int, int, int] = None, port: int = None, messagebox: bool = True):
        """
        Connects to laser with given IP address and port number. If those are not provided, the current values are used.

        :param ip: IP address to connect to
        :param port: port number to connect to
        :param messagebox: show messagebox if failed
        """

        # TODO: sometimes it crashes or ConnectionError-Popup when disconnecting

        if ip is None or port is None:
            ip = self.ip
            port = self.port

        connect = self.threaded_connection.isDummy()

        self.unconnect()

        if connect:
            self.connection = MonacoConnection(
                host='.'.join(str(ip_i) for ip_i in ip),
                port=port
            )
            try:
                self.connection.open()
                self.threaded_connection = ThreadedConnection(self.connection)
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
                self.button_connection_settings.setEnabled(False)
                self.button_connection.setText('Disconnect')

            # TODO: probably add some socket connection errors
            except (ConnectionError) as error:
                try:
                    self.connection.close()
                except ConnectionError:
                    pass
                self.connection = None
                self.reset()

                GlobalConf.logger.info(
                    f'Connection error! Could not connect to Monaco Laser with IP "{ip}" and port "{port}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to Monaco Laser with IP "{ip}" and port "{port}"!',
                        f'<strong>Encountered Error:</strong><br>{error}',
                        expand_details=False
                    )
        else:
            self.button_connection_settings.setEnabled(True)
            self.button_connection.setText('Connect')

        self.updateAllValues()

    def unconnect(self):
        """Disconnect from any port"""

        self.threaded_connection.close()
        self.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def reset(self):
        """Resets everything to default"""
        pass

    def closeEvent(self):
        """Must be called when application is closed"""

        self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()
