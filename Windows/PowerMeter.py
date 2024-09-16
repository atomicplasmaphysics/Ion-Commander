from math import log10, sqrt, pi


from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QMessageBox, QApplication


from Config.GlobalConf import GlobalConf, DefaultParams
from Config.StylesConf import Colors

from DB.db import DB

from Utility.Layouts import InsertingGridLayout, IndicatorLed, DoubleSpinBox, DisplayLabel, SpinBox, ComboBox, LatexLabel
from Utility.Functions import getPrefix
from Utility.Dialogs import showMessageBox

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
        self.indicator_connection = IndicatorLed(off_color=Colors.color_red)
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
        self.combobox_display_parameter_table = [
            ('Power', 'W'),
            ('Power dBm', 'dBm'),
            ('Current', 'A'),
            ('Irradiance', 'W/cm²')
        ]
        self.display_parameter_unit = self.combobox_display_parameter_table[0][1]
        self.combobox_display_parameter = ComboBox(entries=[cdp[0] for cdp in self.combobox_display_parameter_table])
        self.combobox_display_parameter.currentIndexChanged.connect(lambda: self.updateDisplayParameter())
        self.settings_grid.addWidgets(
            self.label_display_parameter,
            self.combobox_display_parameter
        )

        # device wavelength
        self.label_wavelength = QLabel('Wavelength [nm]')
        self.spinbox_wavelength = SpinBox(default=0, input_range=(0, 1024), buttons=False)
        self.spinbox_wavelength.editingFinished.connect(lambda: self.setWavelength(self.spinbox_wavelength.value()))
        self.status_wavelength = DisplayLabel(value=0, unit='nm', target_value=0, deviation=0.1, decimals=0)
        self.settings_grid.addWidgets(
            self.label_wavelength,
            self.spinbox_wavelength,
            self.status_wavelength
        )

        # device attenuation
        self.label_attenuation = QLabel('Attenuation [dB]')
        self.spinbox_attenuation = DoubleSpinBox(default=0, step_size=0.01, decimals=2, input_range=(-60, 60), buttons=False)
        self.spinbox_attenuation.editingFinished.connect(lambda: self.setAttenuation(self.spinbox_attenuation.value()))
        self.status_attenuation = DisplayLabel(value=0, unit='dB', target_value=0, deviation=0.1, decimals=2)
        self.settings_grid.addWidgets(
            self.label_attenuation,
            self.spinbox_attenuation,
            self.status_attenuation
        )

        # device averaging
        self.label_averaging = QLabel('Averaging')
        self.spinbox_averaging = SpinBox(default=1, input_range=(1, 1024), buttons=False)
        self.spinbox_averaging.editingFinished.connect(lambda: self.setAveraging(self.spinbox_averaging.value()))
        self.status_averaging = DisplayLabel(value=1, target_value=1, deviation=0.1, decimals=0)
        self.settings_grid.addWidgets(
            self.label_averaging,
            self.spinbox_averaging,
            self.status_averaging
        )

        # beam diameter
        self.label_beam_diameter = QLabel('Beam diameter [mm]')
        self.spinbox_beam_diameter = DoubleSpinBox(default=0, decimals=2, step_size=0.1, input_range=(0, 9.5), buttons=False)
        self.spinbox_beam_diameter.editingFinished.connect(lambda: self.setBeamDiameter(self.spinbox_beam_diameter.value()))
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

        # power / power_dbm / irradiance / current
        self.display_hbox = QHBoxLayout()
        self.display_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox)

        self.display_power = 0
        self.state_display_parameters = [0, 0, 0, 0]
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
        self.status_display_power_max = DisplayLabel(value=0, unit='W', enable_prefix=True, deviation=0, decimals=2)
        self.display_grid_min_max.addWidgets(
            self.status_display_power_min,
            self.status_display_power_max
        )

        # reset min/max
        self.display_hbox_reset = QHBoxLayout()
        self.display_hbox_reset.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.display_vbox.addLayout(self.display_hbox_reset)

        self.button_display_power_reset_min_max = QPushButton('Reset min/max')
        self.button_display_power_reset_min_max.pressed.connect(lambda: self.resetMinMax())
        self.display_hbox_reset.addWidget(self.button_display_power_reset_min_max)

        self.reset()
        self.combobox_display_parameter.setCurrentIndex(GlobalConf.getPowerMeterDisplayParameter())
            
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

        irradiance = 0
        beam_area = (self.status_beam_diameter.value / sqrt(2) / 10) ** 2 / 4 * pi
        if beam_area != 0:
            irradiance = values[0] / beam_area

        self.state_display_parameters = [
            values[0],
            10 * log10(1000 * values[0]),
            values[1],
            irradiance
        ]

        return self.state_display_parameters[combobox_parameter]

    def updateLoop(self, set_startup: bool = False):
        """Called by timer; Updates all values"""

        if not self.checkConnection(False):
            return

        # get wavelength
        def setWavelength(wavelength: float):
            self.status_wavelength.setValue(wavelength)
            if set_startup:
                self.status_wavelength.setTargetValue(wavelength)
                self.spinbox_wavelength.setValue(round(wavelength))

        self.threaded_connection.callback(setWavelength, self.threaded_connection.getWavelength(TLPMxValues.Attribute.SetValue))

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

        # get beam diameter
        def setBeamDiameter(diameter: float):
            diameter *= sqrt(2)  # conversion from gauss circular beam
            self.status_beam_diameter.setValue(diameter)
            if set_startup:
                self.status_beam_diameter.setTargetValue(diameter)
                self.spinbox_beam_diameter.setValue(diameter)

        self.threaded_connection.callback(setBeamDiameter, self.threaded_connection.getBeamDiameter(TLPMxValues.Attribute.SetValue))

        # get display value
        def setDisplayValue(values: [float, float]):
            value = self.getDisplayParameter(values)
            self.status_display_power_min.setValue(min(self.status_display_power_min.value, value))
            self.status_display_power_max.setValue(max(self.status_display_power_max.value, value))
            self.display_power = value
            self.updateDisplayPowerLabel()
            if self.reset_min_max_next_update:
                self.reset_min_max_next_update = False
                self.resetMinMax()

        self.threaded_connection.callback(setDisplayValue, self.threaded_connection.measure())

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

    def setWavelength(self, wavelength: int):
        """
        Sets the laser wavelength

        :param wavelength: wavelength in nm
        """

        if not self.checkConnection():
            return

        self.status_wavelength.setTargetValue(wavelength)
        self.threaded_connection.setWavelength(wavelength)

    def setAttenuation(self, attenuation: float):
        """
        Sets the attenuation

        :param attenuation: attenuation in dBm
        """

        if not self.checkConnection():
            return

        self.threaded_connection.setAttenuation(attenuation)
        self.status_attenuation.setTargetValue(attenuation)

    def setAveraging(self, average_count: int):
        """
        Sets the average count

        :param average_count: average count per measurement
        """

        if not self.checkConnection():
            return

        self.threaded_connection.setAverageCount(average_count)
        self.status_averaging.setTargetValue(average_count)

    def setBeamDiameter(self, diameter: float):
        """
        Sets the beam diameter

        :param diameter: diameter in mm
        """

        if not self.checkConnection():
            return

        diameter_set = diameter / sqrt(2)  # conversion from gauss circular beam
        self.threaded_connection.setBeamDiameter(diameter_set)
        self.status_beam_diameter.setTargetValue(diameter)

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

        if not port:
            port = self.combobox_connection.getValue(save=True)
        self.setPort(port)

        connect = self.threaded_connection.isDummy()

        self.unconnect()

        if connect:
            try:
                self.connection = TLPMxConnection(
                    port,
                    id_query=True,
                    reset_device=False
                )

                self.connection.open()
                self.threaded_connection = ThreadedTLPMxConnection(self.connection)
                self.indicator_connection.setValue(True)
                self.status_connection.setText('Connected')
                self.combobox_connection.setEnabled(False)
                self.button_connection_refresh.setEnabled(False)
                self.button_connection.setText('Disconnect')

                self.threaded_connection.setAutoRange((1, 1))

            except (ConnectionError, AttributeError, FileNotFoundError) as error:
                try:
                    self.connection.close()
                except (ConnectionError, AttributeError):
                    pass

                self.connection = None
                self.reset()

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

        self.setPortsComboBox()

    def setPortsComboBox(self):
        """Sets available ports in the comports combobox"""

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        resources = getResources()

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

        QApplication.restoreOverrideCursor()

    def closeEvent(self):
        """Must be called when application is closed"""

        self.threaded_connection.close()
        if self.connection is not None:
            self.connection.close()

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
