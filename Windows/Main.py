from PyQt6.QtCore import QCoreApplication, QPoint, QTimer, QSize, Qt, QUrl
from PyQt6.QtGui import QCloseEvent, QPixmap, QDesktopServices
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QApplication, QSplashScreen, QLabel


from Config.GlobalConf import GlobalConf, DefaultParams

from DB.db import DB

from Socket.CommandServer import CommandServer

from Utility.Layouts import TabWidget, VBoxTitleLayout
from Utility.AutoReconnect import EventLog

from Windows.Control import ControlWindow
from Windows.Monitor import MonitorWindow
from Windows.History import HistoryWindow
from Windows.Scripts import ScriptsWindow
from Windows.Tips import TipsWindow
from Windows.Analyse import AnalyseWindow
from Windows.Simulation import SimulationWindow


class MainWindow(QMainWindow):
    """
    Class used for main layout
    """

    # TODO: start CoboldPC

    # TODO: Add tooltips to everything

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
        # TODO: Add measure tab TDC
        # TODO: Add measure tab NDIGO

        # Add control tab
        self.control_window = ControlWindow(self)
        self.addTab(self.control_window, 'Control')

        # Add monitor tab
        self.monitor_window = MonitorWindow(self)
        self.addTab(self.monitor_window, 'Monitor')

        # Add history tab
        self.history_window = HistoryWindow(self, self.database)
        self.addTab(self.history_window, 'History')

        # Add script tab
        self.scripts_window = ScriptsWindow(self)
        self.addTab(self.scripts_window, 'Scripts')

        # Add tips tab
        self.tips_window = TipsWindow(self)
        self.addTab(self.tips_window, 'Tips')

        # Add analyse tab
        self.analyse_window = AnalyseWindow(self)
        self.addTab(self.analyse_window, 'Analyse')

        # Add simulation tab
        self.simulation_window = SimulationWindow(self)
        self.addTab(self.simulation_window, 'Simulation')

        devices = {
            'PSU': self.control_window.psu_group_vbox.device_wrapper,
            'LASER': self.control_window.laser_group_vbox.device_wrapper,
            'PRESSURE': self.control_window.pressure_group_vbox.device_wrapper,
            'POWER': self.monitor_window.power_meter_group_vbox.device_wrapper
        }
        if self.control_window.ebis_enabled:
            devices['EBIS'] = self.control_window.ebis_group_vbox.device_wrapper
        self.server = CommandServer(devices)
        self.server.startServer()

        # store the current labels of the logged columns (rename-proof history)
        self.updateDatabaseLabels()

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
        self.menu_database.aboutToShow.connect(self.updateDatabaseSize)
        self.updateDatabaseSize()

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

    def updateDatabaseLabels(self):
        """Stores the current labels of the logged columns in the database (only changed labels are written)"""

        from Windows.Pressure import PressureVBoxLayout

        self.database.updateLabels(self.database.pressure_table.name, PressureVBoxLayout.databaseLabels())
        self.database.updateLabels(self.database.psu_table.name, self.control_window.psu_group_vbox.databaseLabels())

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

    def addTab(self, widget: TabWidget, title: str):
        """
        Add simulation tab

        :param widget: TabWidget to add in new tab
        :param title: title of tab
        """

        self.tabs.addTab(widget, title)
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
