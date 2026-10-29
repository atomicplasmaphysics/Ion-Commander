from math import log10, sqrt, pi, nan


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox, QApplication


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Socket.CommandServer import DeviceTLPMxWrapper

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, SpinBox, ComboBox, LatexLabel, ReadingAgeLabel
from Utility.Functions import getPrefix, isSaneNumber
from Utility.AutoReconnect import AutoReconnect
from Utility.Dialogs import showMessageBox
from Utility.Icons import getIcon
from Utility.Background import BackgroundRunner

from Connection.TLPMx import TLPMxConnection, TLPMxValues, getResources
from Connection.Threaded import ThreadedTLPMxConnection, ThreadedDummyConnection


class PowerMeterVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # local variables
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateLoop)
        self.update_timer.setInterval(DefaultParams.update_timer_time)
        self.update_timer.start()

        self.active_message_box = False

        # automatic reconnect after a lost connection
        self.last_port = ''
        self.auto_reconnect = AutoReconnect('Power Meter', self.reconnect)

        self.device_wrapper = DeviceTLPMxWrapper()
        self.connection: None | TLPMxConnection = None
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()

        # searching the power meters (~6 s) and opening the connection (~1.3 s) block, so they run in the background
        # (one after another, both use the DLL of Thorlabs)
        self.background = BackgroundRunner(self)
        self.connecting = False
        self.closing = False

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
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
        self.indicator_connection.setToolTip('Green if the device is connected')
        self.connection_hbox.addWidget(self.indicator_connection)
        self.status_connection = QLabel('Not connected')
        self.connection_hbox.addWidget(self.status_connection)
        self.status_reading_age = ReadingAgeLabel()
        self.connection_hbox.addWidget(self.status_reading_age)

        self.connection_hbox_selection = QHBoxLayout()
        self.connection_hbox_selection.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_vbox.addLayout(self.connection_hbox_selection)

        self.combobox_connection = ComboBox()
        self.combobox_connection.setToolTip('Port of the device (refresh the list with the button on the right)')
        self.connection_hbox_selection.addWidget(self.combobox_connection)
        self.button_connection = QPushButton('Connect')
        self.button_connection.setToolTip('Connect to / disconnect from the selected port')
        self.button_connection.pressed.connect(self.manualConnect)
        self.connection_hbox_selection.addWidget(self.button_connection)

        self.button_connection_refresh = QPushButton()
        self.button_connection_refresh.setToolTip('Refresh connections list')
        self.button_connection_refresh.setIcon(getIcon('refresh.svg'))
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
        self.combobox_display_parameter_table = [
            ('Power', 'W'),
            ('Power dBm', 'dBm'),
            ('Current', 'A'),
            ('Irradiance', 'W/cm²')
        ]
        self.display_parameter_unit = self.combobox_display_parameter_table[0][1]
        self.combobox_display_parameter = ComboBox(entries=[cdp[0] for cdp in self.combobox_display_parameter_table])
        self.combobox_display_parameter.setToolTip('Value that is shown in the large display')
        self.combobox_display_parameter.currentIndexChanged.connect(lambda: self.updateDisplayParameter())
        self.label_presets = QLabel('Preset')
        self.label_presets.setToolTip('Wavelengths of the laser (fundamental, second and fourth harmonic, see the preferences)')
        self.settings_grid.addWidgets(
            self.label_display_parameter,
            self.combobox_display_parameter,
            None,
            self.label_presets
        )

        # device wavelength
        self.label_wavelength = QLabel('Wavelength [nm]')
        self.spinbox_wavelength = SpinBox(default=0, input_range=(0, 2000), buttons=False)
        self.spinbox_wavelength.setToolTip('Wavelength for the sensor calibration in nm (press enter to apply)')
        self.spinbox_wavelength.editingFinished.connect(lambda: self.setWavelength(self.spinbox_wavelength.value()))
        self.status_wavelength = DisplayLabel(value=0, unit='nm', target_value=0, deviation=0.1, decimals=0)
        self.status_wavelength.setToolTip('Wavelength set in the power meter')
        # presets below each other in the column "Preset"
        self.button_wavelength_ir = QPushButton('IR')
        self.button_wavelength_ir.setToolTip(f'Set the wavelength to the IR wavelength of the laser ({DefaultParams.laser_ir_wavelength} nm)')
        self.button_wavelength_ir.pressed.connect(lambda: self.setWavelength(DefaultParams.laser_ir_wavelength, update_spinbox=True))
        self.button_wavelength_green = QPushButton('Green')
        self.button_wavelength_green.setToolTip(f'Set the wavelength to the green wavelength of the laser ({DefaultParams.laser_green_wavelength} nm)')
        self.button_wavelength_green.pressed.connect(lambda: self.setWavelength(DefaultParams.laser_green_wavelength, update_spinbox=True))
        self.button_wavelength_uv = QPushButton('UV')
        self.button_wavelength_uv.setToolTip(f'Set the wavelength to the UV wavelength of the laser ({DefaultParams.laser_uv_wavelength} nm)')
        self.button_wavelength_uv.pressed.connect(lambda: self.setWavelength(DefaultParams.laser_uv_wavelength, update_spinbox=True))
        self.settings_grid.addWidgets(
            self.label_wavelength,
            self.spinbox_wavelength,
            self.status_wavelength,
            self.button_wavelength_ir
        )

        # device attenuation
        self.label_attenuation = QLabel('Attenuation [dB]')
        self.spinbox_attenuation = DoubleSpinBox(default=0, step_size=0.01, decimals=2, input_range=(-60, 60), buttons=False)
        self.spinbox_attenuation.setToolTip('Attenuation (e.g. of a filter) in dB that is corrected for (press enter to apply)')
        self.spinbox_attenuation.editingFinished.connect(lambda: self.setAttenuation(self.spinbox_attenuation.value()))
        self.status_attenuation = DisplayLabel(value=0, unit='dB', target_value=0, deviation=0.1, decimals=2)
        self.status_attenuation.setToolTip('Attenuation set in the power meter')
        self.settings_grid.addWidgets(
            self.label_attenuation,
            self.spinbox_attenuation,
            self.status_attenuation,
            self.button_wavelength_green
        )

        # device averaging
        self.label_averaging = QLabel('Averaging')
        self.spinbox_averaging = SpinBox(default=1, input_range=(1, 1024), buttons=False)
        self.spinbox_averaging.setToolTip('Number of measurements that are averaged (press enter to apply)')
        self.spinbox_averaging.editingFinished.connect(lambda: self.setAveraging(self.spinbox_averaging.value()))
        self.status_averaging = DisplayLabel(value=1, target_value=1, deviation=0.1, decimals=0)
        self.status_averaging.setToolTip('Averaging set in the power meter')
        self.settings_grid.addWidgets(
            self.label_averaging,
            self.spinbox_averaging,
            self.status_averaging,
            self.button_wavelength_uv
        )

        # beam diameter
        self.label_beam_diameter = QLabel('Beam diameter [mm]')
        self.spinbox_beam_diameter = DoubleSpinBox(default=0, decimals=2, step_size=0.1, input_range=(0, 9.5), buttons=False)
        self.spinbox_beam_diameter.editingFinished.connect(lambda: self.setBeamDiameter(self.spinbox_beam_diameter.value()))
        self.spinbox_beam_diameter.setToolTip('Assuming Gaussian profile')
        self.status_beam_diameter = DisplayLabel(value=0, unit='mm', target_value=0, deviation=0.1, decimals=2)
        self.status_beam_diameter.setToolTip('Beam diameter set in the power meter (used for the irradiance)')
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

        # power / power_dbm / irradiance / current
        self.display_hbox = QHBoxLayout()
        self.display_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox)

        self.display_power = 0
        self.state_display_parameters = [0, 0, 0, 0]

        # larger values are treated as out of range (e.g. 9.9E37 is returned for overrange)
        self.power_maximum = 100
        self.current_maximum = 0.1
        self.display_power_label = LatexLabel(
            font_size=QFont().pointSizeF() * 4.5,
            font_color='white'
        )
        self.display_power_label.setFixedWidth(300)
        self.display_hbox.addWidget(self.display_power_label)
        self.updateDisplayPowerLabel()

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

        self.reset_min_max_next_update = False
        self.status_display_power_min = DisplayLabel(value=0, unit='W', enable_prefix=True, deviation=0, decimals=2)
        self.status_display_power_min.setToolTip('Minimum since the last reset')
        self.status_display_power_max = DisplayLabel(value=0, unit='W', enable_prefix=True, deviation=0, decimals=2)
        self.status_display_power_max.setToolTip('Maximum since the last reset')
        self.display_grid_min_max.addWidgets(
            self.status_display_power_min,
            self.status_display_power_max
        )

        # reset min/max
        self.display_hbox_reset = QHBoxLayout()
        self.display_hbox_reset.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox_reset)

        self.button_display_power_reset_min_max = QPushButton('Reset min/max')
        self.button_display_power_reset_min_max.setToolTip('Reset the minimum and maximum values')
        self.button_display_power_reset_min_max.pressed.connect(lambda: self.resetMinMax())
        self.display_hbox_reset.addWidget(self.button_display_power_reset_min_max)

        self.reset()
        self.combobox_display_parameter.setCurrentIndex(GlobalConf.getPowerMeterDisplayParameter())

        # search first, then connect (both in the background, one after another): while the power meter is open, the
        # search returns it without serial number ("USB0::0x1313::0x8072::::INSTR")
        self.setPortsComboBox()
        last_connection = GlobalConf.getConnection('power_meter')
        if last_connection:
            self.last_port = last_connection
            self.connect(last_connection, False)
            
    def getDisplayParameter(self, values: tuple[float, float]) -> float:
        """
        Selects the parameter to display from values
        
        :param values: tuple of (Power, Current)
        """

        combobox_parameter = self.combobox_display_parameter.currentIndex()
        # 0: Power
        # 1: Power dBm
        # 2: Current
        # 3: Irradiance

        power, current = values

        # values outside of the valid range (nan, inf, overrange) are stored as nan
        if not isSaneNumber(power) or abs(power) > self.power_maximum:
            power = nan
        if not isSaneNumber(current) or abs(current) > self.current_maximum:
            current = nan

        irradiance = 0
        beam_area = (self.status_beam_diameter.value / sqrt(2) / 10) ** 2 / 4 * pi
        if beam_area != 0:
            irradiance = power / beam_area

        self.state_display_parameters = [
            power,
            10 * log10(1000 * power) if isSaneNumber(power) and power > 0 else nan,  # dBm only defined for positive powers
            current,
            irradiance
        ]

        return self.state_display_parameters[combobox_parameter]

    def updateLoop(self, set_startup: bool = False):
        """Called by timer; Updates all values"""

        self.status_reading_age.setAge(self.device_wrapper.threaded_connection.secondsSinceLastResult(), self.indicator_connection.value())

        if not self.checkConnection(False):
            return

        # get wavelength
        def setWavelength(wavelength: float):
            self.status_wavelength.setValue(wavelength)
            if set_startup:
                self.status_wavelength.setTargetValue(wavelength)
                self.spinbox_wavelength.setValue(round(wavelength))

        self.device_wrapper.threaded_connection.callback(
            setWavelength,
            self.device_wrapper.threaded_connection.getWavelength(TLPMxValues.Attribute.SetValue)
        )

        # get attenuation
        def setAttenuation(attenuation: float):
            self.status_attenuation.setValue(attenuation)
            if set_startup:
                self.status_attenuation.setTargetValue(attenuation)
                self.spinbox_attenuation.setValue(attenuation)

        self.device_wrapper.threaded_connection.callback(
            setAttenuation,
            self.device_wrapper.threaded_connection.getAttenuation(TLPMxValues.Attribute.SetValue)
        )

        # get averaging
        def setAveraging(averaging: int):
            self.status_averaging.setValue(averaging)
            if set_startup:
                self.status_averaging.setTargetValue(averaging)
                self.spinbox_averaging.setValue(averaging)

        self.device_wrapper.threaded_connection.callback(
            setAveraging,
            self.device_wrapper.threaded_connection.getAverageCount()
        )

        # get beam diameter
        def setBeamDiameter(diameter: float):
            diameter *= sqrt(2)  # conversion from gauss circular beam
            self.status_beam_diameter.setValue(diameter)
            if set_startup:
                self.status_beam_diameter.setTargetValue(diameter)
                self.spinbox_beam_diameter.setValue(diameter)

        self.device_wrapper.threaded_connection.callback(
            setBeamDiameter,
            self.device_wrapper.threaded_connection.getBeamDiameter(TLPMxValues.Attribute.SetValue)
        )

        # get display value
        def setDisplayValue(values: [float, float]):
            if not isinstance(values, (tuple, list)) or len(values) != 2:
                GlobalConf.logger.error(f'Power meter: invalid measurement {values}')
                return

            value = self.getDisplayParameter(values)
            self.display_power = value
            self.updateDisplayPowerLabel()

            # invalid/out of range values are not used for min/max
            if not isSaneNumber(value):
                return
            self.status_display_power_min.setValue(min(self.status_display_power_min.value, value))
            self.status_display_power_max.setValue(max(self.status_display_power_max.value, value))
            if self.reset_min_max_next_update:
                self.reset_min_max_next_update = False
                self.resetMinMax()

        self.device_wrapper.threaded_connection.callback(
            setDisplayValue,
            self.device_wrapper.threaded_connection.measure()
        )

    def updateAllValues(self):
        """Updates all values"""
        self.status_display_power_min.setValue(0)
        self.status_display_power_max.setValue(0)
        self.updateLoop(set_startup=True)

    def updateDisplayParameterUnit(self):
        """Updates the display parameter unit"""

        self.display_parameter_unit = self.combobox_display_parameter_table[self.combobox_display_parameter.currentIndex()][1]
        self.status_display_power_min.setUnit(self.display_parameter_unit)
        self.status_display_power_max.setUnit(self.display_parameter_unit)

    def updateDisplayPowerLabel(self):
        """Updates the display power label based on the display power"""

        if self.display_power is None:
            return
        if not isSaneNumber(self.display_power):
            self.display_power_label.setText(r'$\mathrm{Out\ of\ range}$')
            self.display_power_label.setToolTip('The power meter returned an invalid or out of range value (e.g. sensor saturated, negative power for dBm)')
            return
        self.display_power_label.setToolTip('')
        display_power, prefix = getPrefix(self.display_power, use_latex=True)
        display_parameter_unit = f'{prefix} {self.display_parameter_unit}'
        if '/' in display_parameter_unit:
            display_parameter_unit_split = display_parameter_unit.split('/')
            if len(display_parameter_unit_split) != 2:
                # we should not be here
                return
            display_parameter_unit = fr'\frac{{ {display_parameter_unit_split[0]} }}{{ {display_parameter_unit_split[1]} }}'

        self.display_power_label.setText(f'${display_power:.2f} {display_parameter_unit}$')

    def updateDisplayParameter(self):
        """Updates display parameters"""

        self.updateDisplayParameterUnit()
        self.display_power = 0
        self.updateDisplayPowerLabel()
        self.display_power = None
        self.reset_min_max_next_update = True

    def setWavelength(self, wavelength: int, update_spinbox: bool = False):
        """
        Sets the laser wavelength

        :param wavelength: wavelength in nm
        :param update_spinbox: update the according spinbox
        """

        if not self.checkConnection():
            return

        self.status_wavelength.setTargetValue(wavelength)
        self.device_wrapper.threaded_connection.setWavelength(wavelength)

        if update_spinbox:
            self.spinbox_wavelength.setValue(wavelength)

    def setAttenuation(self, attenuation: float):
        """
        Sets the attenuation

        :param attenuation: attenuation in dBm
        """

        if not self.checkConnection():
            return

        self.status_attenuation.setTargetValue(attenuation)
        self.device_wrapper.threaded_connection.setAttenuation(attenuation)

    def setAveraging(self, average_count: int):
        """
        Sets the average count

        :param average_count: average count per measurement
        """

        if not self.checkConnection():
            return

        self.status_averaging.setTargetValue(average_count)
        self.device_wrapper.threaded_connection.setAverageCount(average_count)

    def setBeamDiameter(self, diameter: float):
        """
        Sets the beam diameter

        :param diameter: diameter in mm
        """

        if not self.checkConnection():
            return

        diameter_set = diameter / sqrt(2)  # conversion from gauss circular beam
        self.status_beam_diameter.setTargetValue(diameter)
        self.device_wrapper.threaded_connection.setBeamDiameter(diameter_set)

    def resetMinMax(self):
        """Resets the min and max values"""

        value = self.display_power
        if value is None:
            value = 0

        self.status_display_power_min.setValue(value)
        self.status_display_power_max.setValue(value)

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

        if self.connecting:
            return

        if not port:
            port = self.combobox_connection.getValue(save=True)
        self.setPort(port)

        connect = self.device_wrapper.threaded_connection.isDummy()

        self.unconnect()

        if not connect:
            self.combobox_connection.setEnabled(True)
            self.button_connection_refresh.setEnabled(not self.background.isBusy())
            self.button_connection.setText('Connect')
            self.updateAllValues()
            return

        # the resource name is needed as bytes (the settings store it as text, an empty list gives "-1")
        if isinstance(port, str):
            port = port.encode(DefaultParams.TLPMx_encoding)
        port = bytes(port)
        if port in (b'', b'-1'):
            if messagebox:
                showMessageBox(None, QMessageBox.Icon.Warning, 'No power meter!', 'No ThorLabs Power Meter was found, please refresh the list first!')
            return

        # opening takes ~1.3 s (identification query), the GUI must not hang
        self.connecting = True
        self.status_connection.setText('Connecting...')
        self.button_connection.setEnabled(False)
        self.combobox_connection.setEnabled(False)
        self.button_connection_refresh.setEnabled(False)
        self.background.run(
            lambda: TLPMxConnection(port, id_query=True, reset_device=False).open(),
            lambda connection: self.connectFinished(connection, port),
            lambda error: self.connectFailed(error, port, messagebox)
        )

    def connectFinished(self, connection: TLPMxConnection, port: str):
        """
        Called in the GUI thread when the connection was opened in the background

        :param connection: opened connection
        :param port: port of the connection
        """

        self.connecting = False
        self.button_connection.setEnabled(True)
        if self.closing:
            connection.close()
            return

        self.connection = connection
        self.device_wrapper.threaded_connection = ThreadedTLPMxConnection(
            self.connection,
            self.connectionLost
        )
        self.indicator_connection.setValue(True)
        self.status_connection.setText('Connected')
        self.last_port = port
        self.combobox_connection.setEnabled(False)
        self.button_connection_refresh.setEnabled(False)
        self.button_connection.setText('Disconnect')

        self.device_wrapper.threaded_connection.setAutoRange((1, 1))
        self.auto_reconnect.reconnected()
        self.updateAllValues()

    def connectFailed(self, error: Exception, port: str, messagebox: bool):
        """
        Called in the GUI thread when the connection could not be opened in the background

        :param error: exception of the connection
        :param port: port of the connection
        :param messagebox: show a message box
        """

        self.connecting = False
        self.button_connection.setEnabled(True)
        if self.closing:
            return

        self.connection = None
        self.reset()
        self.combobox_connection.setEnabled(True)
        self.button_connection_refresh.setEnabled(not self.background.isBusy())

        GlobalConf.logger.info(f'{type(error).__name__}! Could not connect to ThorLabs Power Meter on port "{port}", because of: {error}')

        if messagebox:
            showMessageBox(
                None,
                QMessageBox.Icon.Critical,
                f'{type(error).__name__}!',
                f'Could not connect to ThorLabs Power Meter on port "{port}"!',
                f'<strong>Encountered Error:</strong><br>{error}',
                expand_details=False
            )
        self.updateAllValues()

    def manualConnect(self):
        """Connect/disconnect button pressed by the user (stops automatic reconnecting)"""

        self.auto_reconnect.stop()
        self.connect()

    def connectionLost(self):
        """Called if the connection to the device was lost: disconnects and tries to reconnect periodically"""

        GlobalConf.logger.warning('Power Meter: Connection lost')
        self.unconnect()
        if self.last_port:
            self.auto_reconnect.start()

    def reconnect(self) -> bool:
        """Tries to reconnect silently to the last port, returns True if connected"""

        if not self.device_wrapper.threaded_connection.isDummy():
            return True
        # the connection is opened in the background, a successful attempt calls auto_reconnect.reconnected()
        if not self.connecting:
            self.connect(self.last_port, False)
        return False

    def unconnect(self):
        """Disconnect from any port (closing the DLL session takes ~2 s, so it is done in the background)"""

        threaded_connection = self.device_wrapper.threaded_connection
        connection = self.connection
        self.device_wrapper.threaded_connection = ThreadedDummyConnection()
        self.connection = None

        def close():
            # the worker closes the connection itself if it is running
            threaded_connection.close()
            if connection is not None and not threaded_connection.worker.close_called:
                connection.close()

        if connection is not None or not threaded_connection.isDummy():
            self.background.run(close, on_failed=lambda error: GlobalConf.logger.error(f'Power Meter: error while closing the connection: {error}'))

        comport = self.combobox_connection.getValue(text=True)
        self.reset()
        self.setPort(comport)

    def setPort(self, port: str | bytes):
        """
        Selects the power meter in the list

        :param port: resource name (bytes or text) or name of the power meter
        """

        def text(value) -> str:
            if isinstance(value, (bytes, bytearray)):
                return bytes(value).decode(DefaultParams.TLPMx_encoding, errors='replace').lower()
            return str(value).lower()

        port = text(port)
        names = [self.combobox_connection.entries or [], self.combobox_connection.entries_save or []]
        for entries in names:
            for index, entry in enumerate(entries):
                if text(entry) == port:
                    self.combobox_connection.setCurrentIndex(index)
                    return

    def reset(self):
        """Resets everything to default"""

        self.device_wrapper.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

        self.indicator_connection.setValue(False)
        self.status_connection.setText('Not connected')
        self.button_connection.setText('Connect')

        self.spinbox_wavelength.reset()
        self.status_wavelength.setValue(0)
        self.status_wavelength.setTargetValue(0)

        self.spinbox_attenuation.reset()
        self.status_attenuation.setValue(0)
        self.status_attenuation.setTargetValue(0)

        self.spinbox_averaging.reset()
        self.status_averaging.setValue(1)
        self.status_averaging.setTargetValue(1)

        self.spinbox_beam_diameter.reset()
        self.status_beam_diameter.setValue(0)
        self.status_beam_diameter.setTargetValue(0)

        self.display_power = 0
        self.updateDisplayPowerLabel()
        
        self.resetMinMax()

    def setPortsComboBox(self):
        """Searches the power meters in the background (~6 s) and shows them in the combobox"""

        self.button_connection_refresh.setEnabled(False)
        self.background.run(getResources, self.setPortsComboBoxFinished, self.setPortsComboBoxFailed)

    def setPortsComboBoxFailed(self, error: Exception):
        """Called in the GUI thread if the power meters could not be searched"""

        GlobalConf.logger.error(f'Power Meter: could not search the power meters: {error}')
        if not self.closing:
            self.button_connection_refresh.setEnabled(self.device_wrapper.threaded_connection.isDummy() and not self.connecting)

    def setPortsComboBoxFinished(self, resources: dict[bytearray, tuple[bytearray, bytearray, bytearray, int]]):
        """
        Called in the GUI thread with the found power meters

        :param resources: result of <getResources>
        """

        if self.closing:
            return

        names = []
        resource_names = []
        descriptions = []

        for resource, resource_info in resources.items():
            names.append(resource_info[0].decode(DefaultParams.TLPMx_encoding))
            resource_names.append(resource)
            descriptions.append(f'{resource_info[0].decode(DefaultParams.TLPMx_encoding)}: {resource_info[2].decode(DefaultParams.TLPMx_encoding)} [SN: {resource_info[1].decode(DefaultParams.TLPMx_encoding)}]')

        self.combobox_connection.reinitialize(
            entries=names,
            entries_save=resource_names,
            tooltips=descriptions
        )
        if self.last_port:
            self.setPort(self.last_port)

        connected = not self.device_wrapper.threaded_connection.isDummy()
        self.combobox_connection.setEnabled(not connected and not self.connecting)
        self.button_connection_refresh.setEnabled(not connected and not self.connecting)

    def closeEvent(self):
        """Must be called when application is closed"""

        # a connection that is opened in the background is closed again when it is finished
        self.closing = True
        self.background.waitForDone()

        self.device_wrapper.threaded_connection.close()

        # remember the port if connected or if the connection was lost (not if the user disconnected)
        last_connection = ''
        if self.connection is not None or self.auto_reconnect.active:
            last_connection = self.last_port
            if isinstance(last_connection, (bytes, bytearray)):
                last_connection = bytes(last_connection).decode(DefaultParams.TLPMx_encoding)
        self.auto_reconnect.stop()

        if self.connection is not None:
            self.connection.close()

        GlobalConf.updateConnections(power_meter=last_connection)
        GlobalConf.updatePowerMeterDisplayParameter(self.combobox_display_parameter.currentIndex())

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        if not self.checkConnection(False):
            return

        db.insertPowerMeter(
            self.state_display_parameters[0],
            self.state_display_parameters[1],
            self.state_display_parameters[2],
            self.state_display_parameters[3],
            self.status_beam_diameter.value,
            self.status_attenuation.value,
            int(self.status_averaging.value),
            int(self.status_wavelength.value),
        )


def main():
    import sys
    from PyQt6.QtWidgets import QApplication, QWidget

    app = QApplication(sys.argv)
    window = QWidget()
    layout = PowerMeterVBoxLayout()
    window.setLayout(layout)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
