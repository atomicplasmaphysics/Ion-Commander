from PyQt6.QtCore import QCoreApplication, QPoint, QTimer, QSize, Qt
from PyQt6.QtGui import QCloseEvent, QPixmap
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QApplication, QSplashScreen


from Config.GlobalConf import GlobalConf, DefaultParams

from DB.db import DB

from Socket.CommandServer import CommandServer

from Utility.Layouts import TabWidget

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

        self.window_title = GlobalConf.title

        self.database = DB()

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

        # TODO: PowerMeter not implemented yet
        # TODO: EBIS not implemented yet - probably not needed anyways
        self.server = CommandServer({
            'PSU': self.control_window.psu_group_vbox.device_wrapper,
            'LASER': self.control_window.laser_group_vbox.device_wrapper,
            'PRESSURE': self.control_window.pressure_group_vbox.device_wrapper,
            'POWER': self.monitor_window.power_meter_group_vbox.device_wrapper
        })
        self.server.startServer()

        #
        # STATUS BAR
        #

        self.statusBar()

        #
        # Setup logging for tabs
        #

        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.logTabs)
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

        splash.close()
        event.accept()
