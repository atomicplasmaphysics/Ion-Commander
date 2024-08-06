from PyQt6.QtCore import QCoreApplication, QPoint
from PyQt6.QtGui import QCloseEvent, QGuiApplication
from PyQt6.QtWidgets import QMainWindow, QTabWidget


from Config.GlobalConf import GlobalConf

from Utility.Layouts import TabWidget

from Windows.Analyse import AnalyseWindow
from Windows.Control import ControlWindow
from Windows.Monitor import MonitorWindow
from Windows.Tips import TipsWindow


class MainWindow(QMainWindow):
    """
    Class used for main layout
    """

    # TODO: start CoboldPC
    # TODO: popout windows

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

        #
        # MENU BAR
        #

        # TODO: add meaningful menu bar

        '''
        # File
        self.menu = self.menuBar()
        self.menu_file = self.menu.addMenu('&File')
        self.menu_file.setToolTipsVisible(True)

        # Save all
        self.action_save_all = self.menu_file.addAction(QIcon(':/icons/save.png'), '&Save all')
        self.action_save_all.setToolTip('Save configuration for all tabs')
        self.action_save_all.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Key.Key_S))
        self.action_save_all.triggered.connect(lambda: self.menuSave())

        # Open all - not needed
        # self.action_open_all = self.menu_file.addAction(QIcon(':/icons/open.png'), 'Open all')
        # self.action_open_all.setToolTip('Open one configuration for all tabs')
        # self.action_open_all.setShortcut(QKeySequence(Qt.CTRL + Qt.ALT + Qt.Key_O))
        # self.action_open_all.triggered.connect(lambda: self.menuOpen())

        # Reset all
        self.action_reset_all = self.menu_file.addAction(QIcon(':/icons/refresh.png'), '&Reset all')
        self.action_reset_all.setToolTip('Resets configuration for all tabs')
        self.action_reset_all.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Key.Key_N))
        self.action_reset_all.triggered.connect(lambda: self.menuReset())

        self.menu_file.addSeparator()

        # Close all
        self.action_close_all = self.menu_file.addAction(QIcon(':/icons/close.png'), '&Close all tabs')
        self.action_close_all.setToolTip('Closes all tabs')
        self.action_close_all.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Key.Key_W))
        self.action_close_all.triggered.connect(lambda: self.menuCloseAll())

        self.menu_file.addSeparator()

        # Preferences
        self.action_preferences = self.menu_file.addAction(QIcon(':/icons/preferences.png'), '&Preferences')
        self.action_preferences.setToolTip('Open preferences dialog')
        self.action_preferences.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_H))
        self.action_preferences.triggered.connect(lambda: PreferencesDialog(self).open())

        self.menu_file.addSeparator()

        # Quit
        self.action_quit = self.menu_file.addAction('&Quit')
        self.action_quit.setToolTip('Quit the program')
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.triggered.connect(self.closeNone)

        # Simulation
        self.menu_simulation = self.menu.addMenu('&Simulation')
        self.menu_simulation.setToolTipsVisible(True)

        # Close current tab
        self.closeAction = self.menu_simulation.addAction(QIcon(':/icons/close.png'), '&Close current tab')
        self.closeAction.setToolTip('Closes currently active tab')
        self.closeAction.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_W))
        self.closeAction.setDisabled(True)
        self.closeAction.triggered.connect(lambda: self.menuClose())

        self.menu_simulation.addSeparator()

        # Run all tabs
        self.action_run_all = self.menu_simulation.addAction(QIcon(':/icons/play.png'), '&Run all tabs')
        self.action_run_all.setToolTip('Runs all opened tab')
        self.action_run_all.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Key.Key_R))
        self.action_run_all.triggered.connect(lambda: self.menuRun())

        # Run all tabs detached
        self.action_run_all_detached = self.menu_simulation.addAction(QIcon(':/icons/play_detached.png'), 'Run all tabs &detached')
        self.action_run_all_detached.setToolTip('Runs all opened tab in detached mode')
        self.action_run_all_detached.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Modifier.SHIFT | Qt.Key.Key_R))
        self.action_run_all_detached.triggered.connect(lambda: self.menuRun(detached=True))

        # Abort all tabs
        self.action_abort_all = self.menu_simulation.addAction(QIcon(':/icons/abort.png'), '&Abort all tabs')
        self.action_abort_all.setToolTip('Aborts all running tabs')
        self.action_abort_all.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Key.Key_P))
        self.action_abort_all.triggered.connect(lambda: self.menuAbort())

        # SSH
        self.menu_ssh = self.menu.addMenu('SS&H')
        self.menu_ssh.setToolTipsVisible(True)

        # Connections
        self.action_ssh_enable = self.menu_ssh.addAction(QIcon(':/icons/cloud.png'), 'Enable SSH')
        # self.action_ssh_enable.triggered.connect(self.enable_ssh())

        # Help
        self.menu_help = self.menu.addMenu('H&elp')
        self.menu_help.setToolTipsVisible(True)

        # Manual
        self.manual_path = QDir.currentPath()
        self.action_manual = self.menu_help.addAction(QIcon(':/icons/book.png'), '&Manual')
        self.action_manual.triggered.connect(self.openUserManual)

        # Manual
        self.action_manual = self.menu_help.addAction(QIcon(':/icons/help.png'), '&Quick Manual')
        self.action_manual.triggered.connect(lambda: ManualDialog(self).show())

        # About
        self.action_about = self.menu_help.addAction('&About')
        self.action_about.triggered.connect(lambda: AboutDialog(self).open())

        self.setMenuBar(self.menu)
        '''

        #
        # TABS FOR DIFFERENT SIMULATION PROGRAMS
        #

        self.tabs = QTabWidget(self)
        self.tabs.currentChanged.connect(lambda index: self.tabChanged(index))
        self.setCentralWidget(self.tabs)

        # TODO: Add control tab
        # TODO: Add laser-control tab
        # TODO: Add measure tab TAC
        # TODO: Add measure tab TDC
        # TODO: Add measure tab NDIGO

        # # Add control tab
        # self.control_window = ControlWindow(self)
        # self.addTab(self.control_window, 'Control')
        #
        # # Add monitor tab
        # self.monitor_window = MonitorWindow(self)
        # self.addTab(self.monitor_window, 'Control')
        #
        # # Add tips tab
        # self.tips_window = TipsWindow(self)
        # self.addTab(self.tips_window, 'Tips')

        # Add analyse tab
        self.analyse_window = AnalyseWindow(self)
        self.addTab(self.analyse_window, 'Analyse')

        #
        # STATUS BAR
        #

        self.statusBar()

        #
        # Setup window location and signals
        #

        width, height = GlobalConf.getWindowSize()
        x, y = GlobalConf.getWindowCenter()
        if width == height == -1:
            self.showMaximized()
        else:
            self.resize(width, height)
            frame_geometry = self.frameGeometry()
            center_point = QPoint(x, y)
            if x == y == 0:
                center_point = QGuiApplication.primaryScreen().availableVirtualGeometry().center()
            frame_geometry.moveCenter(center_point)
            self.move(frame_geometry.topLeft())

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

        # TODO: make some "closing connections" screen

        # send closing signal to all tabs
        for index in range(self.tabs.count()):
            self.tabs.widget(index).close()

        if self.isMaximized():
            dimensions = (-1, -1)
            center = (0, 0)
        else:
            dimensions = (self.width(), self.height())
            center = (int(self.pos().x() + self.width() / 2), int(self.pos().y() + self.height() / 2))
        GlobalConf.updateWindowSize(*dimensions)
        GlobalConf.updateWindowCenter(*center)

        event.accept()
