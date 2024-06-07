from sys import argv
from platform import system
import logging


from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon

from Config.GlobalConf import GlobalConf
from Config.StylesConf import Styles

from Windows.Main import MainWindow

from Utility.Layouts import SplashPixmap

from Log.Logger import setupLogging


def main():
    """
    Execute the GUI
    """

    # TODO: adjust logo and splashscreen
    # TODO: check if every dependency is installed, otherwise inform user

    # set up logging level
    setupLogging(logging.DEBUG)

    # ctypes.windll only works in Windows
    if system() == 'Windows':
        import ctypes
        # create unique app-id to show taskbar icon (Windows only)
        # in Linux this is not needed, the taskbar icon is set correctly
        app_id = f'TUWIEN.IAP.{GlobalConf.title.upper().replace(" ", ".")}.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    # start application
    app = QApplication(argv)
    app.setWindowIcon(QIcon('icons/logo.png'))

    app.setStyleSheet(Styles.global_style_sheet)

    # get splash size
    screen = app.primaryScreen().availableVirtualGeometry()
    splash_size = QSize(int(min(620, screen.width() * 0.5)), int(min(300, screen.height() * 0.5)))

    # show splashscreen on startup
    pixmap = SplashPixmap('icons/splash.png', 'v0.1.05', QRect(0, 265, 605, 50))
    pixmap = pixmap.scaled(splash_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()

    main_window = MainWindow()
    main_window.show()
    splash.finish(main_window)
    app.exec()


if __name__ == '__main__':
    main()
