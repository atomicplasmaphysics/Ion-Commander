from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QLCDNumber, QApplication, QMessageBox


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, SpinBox, ComboBox
from Utility.Dialogs import showMessageBox

from Connection.TLPMx import TLPMxConnection, TLPMxValues, getResources
from Connection.Threaded import ThreadedTLPMxConnection, ThreadedDummyConnection


class PowerMeterVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(GlobalConf.update_timer_time)
        self.update_timer.start()

        self.active_message_box = False

        self.connection: None | TLPMxConnection = None
        self.threaded_connection: ThreadedDummyConnection | ThreadedTLPMxConnection = ThreadedDummyConnection()

        # Connection Group Box
        self.connection_group_box = QGroupBox('Connection and Status')
        self.addWidget(self.connection_group_box)

        self.connection_vbox = QVBoxLayout()
        self.connection_group_box.setLayout(self.connection_vbox)

        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox)

        self.label_connection = QLabel('Connection')
        self.connection_hbox.addWidget(self.label_connection)
        self.indicator_connection = IndicatorLed(off_color=Colors.cooperate_error)
        self.connection_hbox.addWidget(self.indicator_connection)
        self.status_connection = QLabel('Not connected')
        self.connection_hbox.addWidget(self.status_connection)

        self.connection_hbox_selection = QHBoxLayout()
        self.connection_hbox_selection.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox_selection)

        self.combobox_connection = ComboBox()
        self.connection_hbox_selection.addWidget(self.combobox_connection)
        self.button_connection = QPushButton('Connect')
        self.button_connection.pressed.connect(self.connect)
        self.connection_hbox_selection.addWidget(self.button_connection)

        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(QIcon('icons/refresh.png'))
        self.button_connection_refresh.pressed.connect(self.setPortsComboBox)
        self.connection_hbox_selection.addWidget(self.button_connection_refresh)

        # Settings Group Box
        self.settings_group_box = QGroupBox('Settings')
        self.addWidget(self.settings_group_box)

        self.settings_hbox = QHBoxLayout()
        self.settings_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.settings_group_box.setLayout(self.settings_hbox)

        self.settings_grid = InsertingGridLayout()
        self.settings_hbox.addLayout(self.settings_grid)

        # display parameter
        self.label_display_parameter = QLabel('Display parameter')
        self.combobox_display_parameter = ComboBox(entries=[
            'Power',
            'Power dBm',
            'Current',
            'Irradiance'
        ])
        self.settings_grid.addWidgets(
            self.label_display_parameter,
            self.combobox_display_parameter
        )

        # device wavelength
        self.label_wavelength = QLabel('Wavelength [nm]')
        self.spinbox_wavelength = SpinBox(default=0, input_range=(0, 1024), buttons=False)
        #self.spinbox_wavelength.editingFinished.connect(lambda: self.)
        self.status_wavelength = DisplayLabel(value=0, unit='nm', target_value=0, deviation=0.1, decimals=0)
        self.settings_grid.addWidgets(
            self.label_wavelength,
            self.spinbox_wavelength,
            self.status_wavelength
        )

        # device auto range
        self.label_auto_range = QLabel('Auto Range')
        self.indicator_auto_range = IndicatorLed()
        self.button_auto_range = QPushButton('On')
        self.settings_grid.addWidgets(
            self.label_auto_range,
            self.indicator_auto_range,
            self.button_auto_range
        )

        # device range
        self.label_device_range = QLabel('Range')
        self.combobox_device_range = ComboBox()
        self.settings_grid.addWidgets(
            self.label_device_range,
            self.combobox_device_range
        )

        # device attenuation
        self.label_attenuation = QLabel('Attenuation [dB]')
        self.spinbox_attenuation = DoubleSpinBox(default=0, step_size=0.01, decimals=2, input_range=(-60, 60), buttons=False)
        # self.spinbox_attenuation.editingFinished.connect(lambda: self.)
        self.status_attenuation = DisplayLabel(value=0, unit='dB', target_value=0, deviation=0.1, decimals=2)
        self.settings_grid.addWidgets(
            self.label_attenuation,
            self.spinbox_attenuation,
            self.status_attenuation
        )

        # device averaging
        self.label_averaging = QLabel('Averaging')
        self.spinbox_averaging = SpinBox(default=1, input_range=(1, 1024), buttons=False)
        # self.spinbox_averaging.editingFinished.connect(lambda: self.)
        self.status_averaging = DisplayLabel(value=1, target_value=0, deviation=0.1, decimals=0)
        self.settings_grid.addWidgets(
            self.label_averaging,
            self.spinbox_averaging,
            self.status_averaging
        )
        
        # device zero adjust
        self.label_zero_adjust = QLabel('Zero Adjust')
        self.button_zero_adjust = QPushButton('Adjust')
        self.status_zero_adjust = DisplayLabel(value=0, unit='W', target_value=0, deviation=0, decimals=2)
        self.settings_grid.addWidgets(
            self.label_zero_adjust,
            self.button_zero_adjust,
            self.status_zero_adjust
        )

        # beam diameter
        self.label_beam_diameter = QLabel('Beam diameter [mm]')
        self.spinbox_beam_diameter = DoubleSpinBox(default=0, decimals=2, step_size=0.1, input_range=(0, 9.5), buttons=False)
        # self.spinbox_beam_diameter.editingFinished.connect(lambda: self.)
        self.spinbox_beam_diameter.setToolTip('Assuming Gaussian profile')
        self.status_beam_diameter = DisplayLabel(value=0, unit='mm', target_value=0, deviation=0.1, decimals=2)
        self.settings_grid.addWidgets(
            self.label_beam_diameter,
            self.spinbox_beam_diameter,
            self.status_beam_diameter
        )

        # Display Group Box
        self.display_group_box = QGroupBox('Display')
        self.addWidget(self.display_group_box)

        self.display_vbox = QVBoxLayout()
        self.display_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.display_group_box.setLayout(self.display_vbox)

        # power
        self.display_hbox = QHBoxLayout()
        self.display_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox)

        self.display_grid = InsertingGridLayout()
        self.display_hbox.addLayout(self.display_grid)

        self.label_display_power = QLabel('Current')
        self.display_grid.addWidgets(
            self.label_display_power
        )
        self.lcd_number_display_power = QLCDNumber()
        self.display_grid.addWidgets(
            self.lcd_number_display_power
        )

        # min/max
        self.display_hbox_min_max = QHBoxLayout()
        self.display_hbox_min_max.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox_min_max)

        self.display_grid_min_max = InsertingGridLayout()
        self.display_hbox_min_max.addLayout(self.display_grid_min_max)

        self.label_display_power_min = QLabel('min')
        self.label_display_power_max = QLabel('max')
        self.display_grid_min_max.addWidgets(
            self.label_display_power_min,
            self.label_display_power_max
        )

        self.status_display_power_min = DisplayLabel(value=0, unit='W', target_value=0, deviation=0.1, decimals=2)
        self.status_display_power_max = DisplayLabel(value=0, unit='W', target_value=0, deviation=0.1, decimals=2)
        self.display_grid_min_max.addWidgets(
            self.status_display_power_min,
            self.status_display_power_max
        )

        # reset min/max
        self.display_hbox_reset = QHBoxLayout()
        self.display_hbox_reset.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox_reset)

        self.button_display_power_reset_min_max = QPushButton('Reset min/max')
        self.display_hbox_reset.addWidget(self.button_display_power_reset_min_max)

        self.reset()

        last_connection = GlobalConf.getConnection('powermeter')
        if last_connection:
            self.connect(last_connection, False)
            
    def getDisplayParameter(self, values: tuple[float, float, float]) -> float:
        """
        Selects the parameter to display from values
        
        :param values: tuple of (Power, Current, Vo
        """

    def updateLoop(self, set_startup: bool = False):
        """Called by timer; Updates all values"""

        if not self.checkConnection(False):
            return
        
        self.combobox_display_parameter.currentIndex()
        # 0: Power
        # 1: Power dBm
        # 2: Current
        # 3: Irradiance

        # get wavelength
        def setWavelength(wavelength: float):
            self.status_wavelength.setValue(wavelength)
            if set_startup:
                self.status_wavelength.setTargetValue(wavelength)
                self.spinbox_wavelength.setValue(round(wavelength))

        self.threaded_connection.callback(setWavelength, self.threaded_connection.getWavelength(TLPMxValues.Attribute.SetValue))

        # get autorange
        def setAutorange(autoranges: tuple[float, float, float]):
            power, current, voltage = autoranges
            # TODO: convert properly
            
            ...

        self.threaded_connection.callback(setAutorange, self.threaded_connection.getAutoRange())

        # get range
        def setRange(ranges: tuple[float, float, float]):
            power, current, voltage = ranges
            ...

        self.threaded_connection.callback(setRange, self.threaded_connection.getRange(TLPMxValues.Attribute.SetValue))

        # get attenuation
        def setAttenuation(attenuation: float):
            self.status_attenuation.setValue(attenuation)
            if set_startup:
                self.status_attenuation.setTargetValue(attenuation)
                self.spinbox_attenuation.setValue(attenuation)

        self.threaded_connection.callback(setAttenuation, self.threaded_connection.getAttenuation(TLPMxValues.Attribute.SetValue))

        # get averaging
        def setAveraging(averaging: int):
            self.status_averaging.setValue(averaging)
            if set_startup:
                self.status_averaging.setTargetValue(averaging)
                self.spinbox_averaging.setValue(averaging)

        self.threaded_connection.callback(setAveraging, self.threaded_connection.getAverageCount())

        # get zero adjust
        def setZeroAdjust(zero_adjust: int):
            self.status_zero_adjust.setTargetValue(zero_adjust)
            self.status_zero_adjust.setValue(zero_adjust)

        self.threaded_connection.callback(setZeroAdjust, self.threaded_connection.getDarkAdjustState())

        # get beam diameter
        def setBeamDiameter(diameter: float):
            self.status_beam_diameter.setValue(diameter)
            if set_startup:
                self.status_beam_diameter.setTargetValue(diameter)
                self.spinbox_beam_diameter.setValue(diameter)

        self.threaded_connection.callback(setBeamDiameter, self.threaded_connection.getBeamDiameter(TLPMxValues.Attribute.SetValue))

        # get display value
        def setDisplayValue(values: [float, float, float]):
            power, current, voltage = values
            # TODO: also set min and max
            self.lcd_number_display_power.display(str(power))

        self.threaded_connection.callback(setDisplayValue, self.threaded_connection.measurePower())

    def updateAllValues(self):
        """Updates all values"""
        # TODO: get display parameter
        self.status_display_power_min.setValue(0)
        self.status_display_power_max.setValue(0)
        self.updateLoop(set_startup=True)

    def checkConnection(self, messagebox: bool = True) -> bool:
        """
        Checks if connection is established and pops up messagebox if it does not

        :param messagebox: enable popup of infobox
        """

        if self.indicator_connection.value():
            return True

        if messagebox and not self.active_message_box:
            self.active_message_box = True
            showMessageBox(
                None,
                QMessageBox.Icon.Warning,
                'Connection warning!',
                'ThorLabs Power Meter is not connected, please connect first!'
            )
            self.active_message_box = False

        return False

    def connect(self, port: str = '', messagebox: bool = True):
        """
        Connect to given comport. If no comport is given, the current selected comport will be connected to

        :param port: port to connect to
        :param messagebox: show messagebox if failed
        """

        # TODO: sometimes it crashes or ConnectionError-Popup when disconnecting

        if not port:
            port = self.combobox_connection.getValue(text=True)
        self.setPort(port)

        connect = self.threaded_connection.isDummy()

        self.unconnect()

        if connect:
            self.connection = TLPMxConnection(
                port,
                id_query=True,
                reset_device=False
            )
            try:
                self.connection.open()
                self.threaded_connection = ThreadedTLPMxConnection(self.connection)
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
                self.combobox_connection.setEnabled(False)
                self.button_connection_refresh.setEnabled(False)
                self.button_connection.setText('Disconnect')

            except ConnectionError as error:
                try:
                    self.connection.close()
                except ConnectionError:
                    pass
                self.connection = None
                self.reset()

                GlobalConf.logger.info(f'Connection error! Could not connect to ThorLabs Power Meter on port "{port}", because of: {error}')

                if messagebox:
                    showMessageBox(
                        None,
                        QMessageBox.Icon.Critical,
                        'Connection error!',
                        f'Could not connect to ThorLabs Power Meter on port "{pot}"!',
                        f'<strong>Encountered Error:</strong><br>{error}',
                        expand_details=False
                    )
        else:
            self.combobox_connection.setEnabled(True)
            self.button_connection_refresh.setEnabled(True)
            self.button_connection.setText('Connect')

        self.updateAllValues()

    def unconnect(self):
        """Disconnect from any port"""

        self.threaded_connection.close()
        self.threaded_connection = ThreadedDummyConnection()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

        comport = self.combobox_connection.getValue(text=True)
        self.reset()
        self.setPort(comport)

    def setPort(self, port: str):
        """
        Selects the port in the list of ports

        :param port: port to be selected
        """

        port = port.lower()

        entries = {p.lower(): i for i, p in enumerate(self.combobox_connection.entries)}
        if port in entries.keys():
            self.combobox_connection.setCurrentIndex(entries[port])

    def reset(self):
        """Resets everything to default"""

        self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        # TODO: reset default values of all input/output boxes

        self.setPortsComboBox()

    def setPortsComboBox(self):
        """Sets available ports in the comports combobox"""

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        resources = getResources()

        names = []
        resource_names = []
        descriptions = []

        for resource, resource_info in resources.items():
            # TODO: decoding/encoding type in GlobalConfig
            names.append(resource_info[0].decode('utf-8'))
            resource_names.append(resource)
            descriptions.append(f'{resource_info[0].decode("utf-8")}: {resource_info[2].decode("utf-8")} [SN: {resource_info[1].decode("utf-8")}]')

        self.combobox_connection.reinitialize(
            entries=names,
            entries_save=resource_names,
            tooltips=descriptions
        )

        QApplication.restoreOverrideCursor()

    def closeEvent(self):
        """Must be called when application is closed"""
        pass
