from functools import cache
from pathlib import Path


from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer


# folder of the icons (independent of the working directory)
ICON_FOLDER = Path(__file__).parents[1] / 'icons'
# color of the monochrome icons (Lucide icons with stroke="#000000"), colored icons (play, abort, delete) are kept
ICON_BLACK = '#000000'
# sizes of the rendered pixmaps (QIcon picks the best one, also for high DPI screens)
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128)


def isDarkTheme() -> bool:
    """True if the application uses a dark palette (e.g. dark mode of Windows), i.e. the text is lighter than the window"""

    app = QGuiApplication.instance()
    if app is None:
        return False
    palette = app.palette()
    return palette.color(QPalette.ColorRole.Window).lightness() < palette.color(QPalette.ColorRole.WindowText).lightness()


def iconColor() -> str:
    """Color of the monochrome icons: black, or the text color of the buttons in a dark theme"""

    if not isDarkTheme():
        return ICON_BLACK
    return QGuiApplication.instance().palette().color(QPalette.ColorRole.ButtonText).name()


@cache
def coloredIcon(name: str, color: str) -> QIcon:
    """
    Renders an SVG icon of the icon folder with <color> instead of black

    :param name: file name in the icon folder
    :param color: color (e.g. "#ffffff") that replaces the black of the icon
    """

    svg = (ICON_FOLDER / name).read_text(encoding='utf-8').replace(ICON_BLACK, color)
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    icon = QIcon()
    for size in ICON_SIZES:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def getIcon(name: str) -> QIcon:
    """
    Icon of the icon folder. Monochrome SVG icons are drawn in the text color of the palette in a dark theme
    (the theme is checked when the icon is created, i.e. at startup)

    :param name: file name in the icon folder, e.g. "refresh.svg"
    """

    path = ICON_FOLDER / name
    color = iconColor()
    if path.suffix.lower() != '.svg' or color == ICON_BLACK or not path.exists():
        return QIcon(str(path))
    return coloredIcon(name, color)
