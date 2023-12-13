from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QGraphicsColorizeEffect


def setWidgetBackground(widget: QWidget, enabled: bool, color: QColor = QColor(144, 12, 63, 255)):
    """
    Sets widget background to some color

    :param widget: widget to highlight
    :param enabled: enable/disable background
    :param color: (optional) color of background - default(rbg(144, 12, 63): darkish red)
    """

    if not enabled:
        widget.setGraphicsEffect(None)
        return
    colorize_effect = QGraphicsColorizeEffect()
    colorize_effect.setColor(color)
    widget.setGraphicsEffect(colorize_effect)
