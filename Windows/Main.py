from datetime import datetime


from PyQt6.QtCore import QCoreApplication, QPoint, QTimer, QSize, Qt, QUrl
from PyQt6.QtGui import QCloseEvent, QPixmap, QDesktopServices
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QApplication, QSplashScreen, QLabel, QDialog


from Config.GlobalConf import GlobalConf, DefaultParams

from DB.db import DB

from Socket.CommandServer import CommandServer

from Utility.Layouts import TabWidget, VBoxTitleLayout
from Utility.AutoReconnect import EventLog

from Windows.Control import ControlWindow
from Windows.Monitor import MonitorWindow
# Measure tab (CoboldPC) is disabled for now
# from Windows.Measure import MeasureWindow
from Windows.History import HistoryWindow
from Windows.Scripts import ScriptsWindow
from Windows.Tips import TipsWindow
from Windows.Analyse import AnalyseWindow
from Windows.Simulation import SimulationWindow
from Windows.Settings import SettingsDialog
from Windows.GaugeNames import GaugeNamesDialog


class MainWindow(QMainWindow):
    """
    Class used for main layout
    """

    def __init__(self):
        super().__init__()
        GlobalConf()

        #
        # QCoreApplication Parameters
        #

        QCoreApplication.setOrganizationName('TUWien')
        QCoreApplication.setOrganizationDomain('www.tuwien.at')
        QCoreApplication.setApplicationName(GlobalConf.title)

        self.window_title = f'{GlobalConf.title} v{GlobalConf.version}'
        self.setWindowTitle(self.window_title)

        self.database = DB()

        # widgets without access to the database can log events (e.g. lost connections) via the EventLog
        EventLog.sink = self.database.insertEvent

        #
        # TABS FOR DIFFERENT SIMULATION PROGRAMS
        #

        self.tabs = QTabWidget(self)
        self.tabs.currentChanged.connect(lambda index: self.tabChanged(index))
        self.setCentralWidget(self.tabs)

        # TODO: Add measure tab TAC
        # TODO: Add measure tab NDIGO

        # Add control tab
        self.control_window = ControlWindow(self)
        self.addTab(self.control_window, 'Control', 'Control of the power supplies (PSU, EBIS), the laser and the pressure gauges')

        # Add monitor tab
        self.monitor_window = MonitorWindow(self)
        self.addTab(self.monitor_window, 'Monitor', 'Monitoring devices (power meter, electrometer, camera)')

        # Add measure tab (CoboldPC), disabled for now (the COBOLD device of the CommandServer below too)
        # self.measure_window = MeasureWindow(self, metadata_function=self.deviceSettings)
        # self.addTab(self.measure_window, 'Measure', 'Measurements with CoboldPC (fixed duration, measurement folder, device settings saved as JSON)')

        # Add history tab
        self.history_window = HistoryWindow(self, self.database)
        self.addTab(self.history_window, 'History', 'Plot and export the logged values of the database')

        # Add script tab
        self.scripts_window = ScriptsWindow(self)
        self.addTab(self.scripts_window, 'Scripts', 'Write and run scripts that control the devices via the CommandServer')

        # Add tips tab
        self.tips_window = TipsWindow(self)
        self.addTab(self.tips_window, 'Tips', 'Tips and notes for the lab')

        # Add analyse tab
        self.analyse_window = AnalyseWindow(self)
        self.addTab(self.analyse_window, 'Analyse', 'Analyse measured TOF data (histograms, fits)')

        # Add simulation tab
        self.simulation_window = SimulationWindow(self)
        self.addTab(self.simulation_window, 'Simulation', 'Mass/TOF calculators based on simulations')

        devices = {
            'PSU': self.control_window.psu_group_vbox.device_wrapper,
            'LASER': self.control_window.laser_group_vbox.device_wrapper,
            'PRESSURE': self.control_window.pressure_group_vbox.device_wrapper,
            'POWER': self.monitor_window.power_meter_group_vbox.device_wrapper,
            'CAMERA': self.monitor_window.camera_group_vbox.device_wrapper,
            'ELECTROMETER': self.monitor_window.electrometer_group_vbox.device_wrapper,
            # 'COBOLD': self.measure_window.cobold_group_vbox.device_wrapper
        }
        if self.control_window.ebis_enabled:
            devices['EBIS'] = self.control_window.ebis_group_vbox.device_wrapper
        self.server = CommandServer(devices)
        self.server.startServer()
        # autocomplete and check of the device functions in the script editor
        self.scripts_window.setDevices({name: wrapper.connection_class for name, wrapper in devices.items()})

        # store the current labels of the logged columns (rename-proof history)
        self.updateDatabaseLabels()
        self.control_window.pressure_group_vbox.gauges_changed.connect(self.updateDatabaseLabels)

        #
        # MENU BAR
        #

        self.menu_database = self.menuBar().addMenu('Database')
        self.menu_database.setToolTipsVisible(True)
        self.action_database_size = self.menu_database.addAction('Size: -')
        self.action_database_size.setEnabled(False)
        self.action_database_size.setToolTip('Size of the database file (including write-ahead log)')
        self.action_database_folder = self.menu_database.addAction('Open database folder')
        self.action_database_folder.setToolTip('Opens the folder of the database file in the file explorer')
        self.action_database_folder.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.database.database_path.parent)))
        )
        self.action_gauge_names = self.menu_database.addAction('Pressure gauge names...')
        self.action_gauge_names.setToolTip('Assign the readings of the pressure gauges to names (e.g. chambers) and delete names of tests')
        self.action_gauge_names.triggered.connect(self.editGaugeNames)
        self.menu_database.aboutToShow.connect(self.updateDatabaseSize)
        self.updateDatabaseSize()

        self.menu_settings = self.menuBar().addMenu('Settings')
        self.menu_settings.setToolTipsVisible(True)
        self.action_settings = self.menu_settings.addAction('Preferences...')
        self.action_settings.setToolTip('Change update intervals, limits, laser address, CommandServer port, ...')
        self.action_settings.triggered.connect(lambda: SettingsDialog(self).exec())

        #
        # STATUS BAR
        #

        self.statusBar()

        # permanent CommandServer status (running, connected clients)
        self.label_server_status = QLabel()
        self.label_server_status.setToolTip(
            'Status of the CommandServer that forwards commands from scripts/other programs to the devices\n'
            f'Devices: {", ".join(self.server.devices.keys())}'
        )
        self.statusBar().addPermanentWidget(self.label_server_status)
        self.updateServerStatus()

        #
        # Setup logging for tabs
        #

        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.logTabs)
        self.logging_timer.timeout.connect(self.updateServerStatus)
        self.logging_timer.setInterval(DefaultParams.update_timer_time)
        self.logging_timer.start()

        #
        # Setup window location and signals
        #

        width, height, center_x, center_y = GlobalConf.getWindowSizeCenter()
        maximized = width == height == GlobalConf.window_maximized_value
        if not maximized:
            self.resize(width, height)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(QPoint(center_x, center_y))
        self.move(frame_geometry.topLeft())
        if maximized:
            self.showMaximized()

        # restore popped out panels after the main window is shown
        QTimer.singleShot(0, self.restorePopouts)

    def restorePopouts(self):
        """Pops out the panels that were popped out when the application was closed"""

        popouts = GlobalConf.getPopouts()
        for layout in VBoxTitleLayout.popout_instances:
            if layout.title_str in popouts:
                layout.restorePopout(popouts[layout.title_str])

    def savePopouts(self):
        """Stores which panels are popped out (and where)"""

        GlobalConf.updatePopouts({layout.title_str: layout.popoutGeometry() for layout in VBoxTitleLayout.popout_instances})

    def deviceSettings(self) -> dict:
        """Returns the current values of all devices (stored with every measurement)"""

        control = self.control_window
        settings = {'time': datetime.now().isoformat(timespec='seconds')}

        psu = control.psu_group_vbox
        settings['PSU'] = {
            'connected': psu.indicator_connection.value(),
            'channels': {row.name: {'set_V': row.spinbox_voltage.value(), 'voltage_V': row.status_voltage.value, 'current_A': row.status_current.value, 'on': row.indicator.value()} for row in psu.channel_rows}
        }

        if control.ebis_enabled:
            ebis = control.ebis_group_vbox
            settings['EBIS'] = {
                'connected': ebis.indicator_connection.value(),
                'high_voltage': ebis.indicator_high_voltage.value(),
                'channels': {row.name: {'set_V': row.spinbox_voltage.value(), 'voltage_V': row.status_voltage.value, 'current_A': row.status_current.value if row.status_current is not None else None, 'on': row.indicator.value()} for row in ebis.channel_rows},
                'heating_current_set_A': ebis.spinbox_current_6.value(),
                'heating_current_A': ebis.status_current_6.value,
                'interlock': ebis.interlock.state.text(),
            }

        pressure = control.pressure_group_vbox
        settings['Pressure_mbar'] = pressure.getPressures()
        settings['Pressure_RS485_mbar'] = pressure.rs485.getPressures()

        laser = control.laser_group_vbox
        settings['Laser'] = {
            'connected': laser.indicator_connection.value(),
            'shutter_open': laser.indicator_shutter.value(),
            'pulsing': laser.indicator_pulsing.value(),
            'repetition_rate_set_Hz': laser.status_repetition_rate_set.value,
            'repetition_rate_measured_Hz': laser.status_repetition_rate_measured.value,
            'rf_level_percent': laser.status_settings_rflevel.value,
            'pulse_width_fs': laser.status_settings_pulsewidth.value,
        }

        electrometer = self.monitor_window.electrometer_group_vbox
        settings['Electrometer'] = {
            'connected': electrometer.indicator_connection.value(),
            'current_A': electrometer.currentForLog(),
            'range': electrometer.combobox_range.getValue(save=True),
            'nplc': electrometer.spinbox_nplc.value(),
        }

        power_meter = self.monitor_window.power_meter_group_vbox
        settings['PowerMeter'] = {
            'connected': power_meter.indicator_connection.value(),
            'power_W': power_meter.state_display_parameters[0],
            'wavelength_nm': power_meter.status_wavelength.value,
        }
        return settings

    def updateDatabaseLabels(self):
        """Stores the current labels of the logged columns in the database (only changed labels are written)"""

        pressure = self.control_window.pressure_group_vbox
        self.database.updateLabels(self.database.pressure_table.name, pressure.databaseLabels())
        self.database.updateLabels(self.database.pressure_rs485_table.name, pressure.rs485.databaseLabels())
        self.database.updateLabels(self.database.psu_table.name, self.control_window.psu_group_vbox.databaseLabels())
        self.database.updateLabels(self.database.electrometer_table.name, {'Current': ('Electrometer Current', 'A')})
        self.history_window.updateLabels()

    def editGaugeNames(self):
        """Opens the dialog to assign the readings of the pressure gauges to names"""

        pressure = self.control_window.pressure_group_vbox
        dialog = GaugeNamesDialog(self.database, pressure.databaseGauges())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pressure.setGaugeNames(dialog.currentNames())
            self.updateDatabaseLabels()

    def updateServerStatus(self):
        """Updates the CommandServer status in the status bar"""

        self.label_server_status.setText(self.server.status())

    def updateDatabaseSize(self):
        """Updates the size of the database shown in the menu"""

        size = float(self.database.getSize())
        for unit in ['B', 'kB', 'MB', 'GB', 'TB']:
            if size < 1024 or unit == 'TB':
                break
            size /= 1024
        self.action_database_size.setText(f'Size: {size:.1f} {unit}')

    def logTabs(self):
        """Loggs all tabs"""

        for index in range(self.tabs.count()):
            self.tabs.widget(index).log(self.database)

    def addTab(self, widget: TabWidget, title: str, tooltip: str = ''):
        """
        Add tab

        :param widget: TabWidget to add in new tab
        :param title: title of tab
        :param tooltip: tooltip of tab
        """

        index = self.tabs.addTab(widget, title)
        if tooltip:
            self.tabs.setTabToolTip(index, tooltip)
        self.tabs.setCurrentIndex(0)

    def tabChanged(self, index: int):
        """
        Called when tab is changed

        :param index: index of active tab
        """

        tab_widget = self.tabs.widget(index)

    def writeStatusBar(self, msg: str, visible_time: int = 3000):
        """
        Write to status bar

        :param msg: new text of status bar
        :param visible_time: (optional) time in ms until status bar is cleared again. If 0, then message will stay persistent
        """

        self.statusBar().showMessage(msg, visible_time)

    def writeWindowTitleTab(self, index: int):
        """
        Writes title to main window based on index of tab

        :param: index: index of tab
        """

        self.setWindowTitle(self.tabs.tabText(index))

    def closeEvent(self, event: QCloseEvent):
        """
        Executed when close button is pressed

        :param event: close event
        """

        # show splash screen while shutting down
        screen = QApplication.primaryScreen().availableVirtualGeometry()
        splash_size = QSize(int(min(766, screen.width() * 0.5)), int(min(383, screen.height() * 0.5)))
        pixmap = QPixmap('icons/splash_shutdown.png')
        pixmap = pixmap.scaled(splash_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(pixmap)
        splash.show()
        QApplication.processEvents()

        # must be stored before the tabs (and with them the popped out panels) are closed
        self.savePopouts()

        # send closing signal to all tabs
        for index in range(self.tabs.count()):
            self.tabs.widget(index).close()

        center = (int(self.pos().x() + self.width() / 2), int(self.pos().y() + self.height() / 2))
        dimensions = (self.width(), self.height())
        if self.isMaximized():
            dimensions = (GlobalConf.window_maximized_value, GlobalConf.window_maximized_value)

        GlobalConf.updateWindowSizeCenter(*dimensions, *center)

        self.database.close()
        self.server.stopServer()

        GlobalConf.logger.info('Shutting down')

        splash.close()
        event.accept()
