from __future__ import annotations
from typing import TYPE_CHECKING
from math import log10, inf
from time import time
from os import path
from shutil import copy


import numpy as np

from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QSize, QRect, QRectF
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor, QBrush, QLinearGradient, QPainterPath, QAction, QFont, QTextCursor, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QApplication, QStyleOption, QTableWidget, QTableWidgetItem, QAbstractItemView, QGridLayout,
    QLCDNumber, QFrame, QTextEdit, QMenuBar, QMessageBox, QInputDialog, QMenu, QColorDialog
)
from PyQt6.QtSvg import QSvgRenderer

import pyqtgraph as pg


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors, Styles, Forms

from Utility.ModifyWidget import setWidgetBackground
from Utility.Functions import hexToRgb, linearInterpolateColor, getPrefix, qColorToHex, selectFileDialog

if TYPE_CHECKING:
    from Windows.Main import MainWindow
    from Utility.Fitting import FitMethod


class SplashPixmap(QPixmap):
    """
    Class that extends the QPixmap for generating Splash Screen Images

    :param image: image path
    :param text: text string
    :param box: rectangular position for text
    :param align: alignment for text
    :param color: color for text
    :param font_size: font size for text
    """

    def __init__(
        self,
        image: str,
        text: str,
        box: QRect,
        *args,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight,
        color: Qt.GlobalColor | QColor = Qt.GlobalColor.black,
        font_size: int = 20,
        **kwargs
    ):
        super().__init__(image, *args, **kwargs)

        self.painter = QPainter(self)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.font = QApplication.font()
        self.font.setPixelSize(font_size)
        self.painter.setFont(self.font)
        self.painter.setPen(color)
        self.painter.drawText(box, align, text)
        self.painter.end()


class TabWidget(QWidget):
    """
    TabWidgets that acts as extended QWidget

    :param parent: parent widget
    """

    def __init__(
        self,
        parent: MainWindow,
        *args,
        **kwargs
    ):
        super().__init__(*args, parent=parent, **kwargs)
        self.main_window = parent

    def checkClosable(self) -> bool:
        """Checks if this tab is currently closeable"""
        return True

    def writeStatusBar(self, msg: str, visible_time: int = 3000):
        """
        Write to status bar of main window

        :param msg: new text of status bar
        :param visible_time: (optional) time in ms until status bar is cleared again. If 0, then message will stay persistent
        """

        self.main_window.writeStatusBar(msg, visible_time)


class VBoxTitleLayout(QVBoxLayout):
    """
    Class providing a QVBoxLayout with a title and style

    :param title: title of top line
    :param parent: parent widget
    :param title_style: style of title line
    :param title_style_busy: style of title line in busy mode
    :param busy_symbol: symbol when busy
    :param spacing: spacing of widgets
    :param add_stretch: if bool: addStretch(1) after title if True, else do nothing
                        if integer: addSpacing(addStretch) after title
    """

    def __init__(
        self,
        title: str,
        parent=None,
        title_style: str = Styles.title_style_sheet,
        title_style_busy: str = Styles.title_style_sheet,
        busy_symbol: str = '⧖',
        spacing: int = 0,
        add_stretch: bool | int = 0
    ):
        super().__init__(parent)
        self.parent = parent
        self.title_str = title
        self.title_style = title_style
        self.title_style_busy = title_style_busy
        self.busy_symbol = busy_symbol

        self.setSpacing(spacing)
        self.hl = QHBoxLayout()

        self.title = QLabel(self.title_str, self.parent)
        self.title.setStyleSheet(title_style)
        self.hl.addWidget(self.title)

        if isinstance(add_stretch, bool) and add_stretch:
            self.hl.addStretch(1)
        elif isinstance(add_stretch, int):
            self.hl.addSpacing(add_stretch)

        self.addLayout(self.hl)

    def busy(self, busy: bool = True, busy_text: str = ''):
        """
        Title changes when busy

        :param busy: is busy or not
        :param busy_text: additional busy text displayed in title
        """

        if busy:
            if not busy_text:
                self.title.setText(f'{self.title_str} {self.busy_symbol}')
            else:
                self.title.setText(f'{self.title_str} {self.busy_symbol} ({busy_text})')
            self.title.setStyleSheet(self.title_style_busy)

        else:
            self.title.setText(self.title_str)
            self.title.setStyleSheet(self.title_style)


class InsertingGridLayout(QGridLayout):
    """
    Extends the QGridLayout such that a row of items can be inserted at once
    """

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.lines: list[tuple[QFrame, int]] = []
        self.max_width = 0

    def _resizeHorizontalLines(self):
        """Resizes all horizontal lines to fit the widest row"""

        for line, row in self.lines:
            self.addWidget(line, row, 0, 1, self.max_width)

    def addHorizontalLine(
        self,
        fixed_columns: int = 0,
        frame_shadow: QFrame.Shadow = QFrame.Shadow.Sunken,
        color: QColor | Qt.GlobalColor | str = Colors.app_background_event
    ):
        """
        Adds a horizontal line

        :param fixed_columns: sets a fixed colum size
        :param frame_shadow: frame shadow mode
        :param color: color of line
        """

        row = self.rowCount()

        enable_rescaling = bool(fixed_columns)
        if not enable_rescaling:
            fixed_columns = self.max_width

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(frame_shadow)
        line.setStyleSheet(f'background-color: {qColorToHex(QColor(color))};')

        if enable_rescaling:
            self.lines.append((line, row))

        self.addWidget(line, row, 0, 1, fixed_columns)

    def addWidgets(self, *widgets: QWidget | tuple[QWidget, int] | None):
        """
        Adds Widgets as new row

        :param widgets: widget - widget that takes one column
                        tuple[widget, columns] - widget that spans over multiple columns
                        None - left out column
        """

        row = self.rowCount()
        width = 0

        for widget in widgets:
            width += 1
            if widget is None:
                continue

            if isinstance(widget, tuple):
                self.addWidget(widget[0], row, width - 1, 1, widget[1])
                width += widget[1] - 1
            else:
                self.addWidget(widget, row, width - 1)

        self.max_width = max(self.max_width, width)
        self._resizeHorizontalLines()


class InputHBoxLayout(QHBoxLayout):
    """
    Quick horizontal layout for checkbox, label and input. Extends the QHBoxLayout.

    :param label: text of label for widget
    :param widget: widget to be displayed
    :param split: (optional) percentage split between label and widget
    :param disabled: (optional) enable/disable input
    :param hidden: (optional) hide input and label
    :param checkbox: (optional) add checkbox before label. set to True/False if it should be checked on startup
    :param checkbox_connected: (optional) determines if the widget should be enabled/disabled depending on the checkbox state
    """

    def __init__(
        self,
        label: str,
        widget: QWidget | None,
        *args,
        tooltip: str = None,
        split: int = 50,
        disabled: bool = False,
        hidden: bool = False,
        checkbox: bool = None,
        checkbox_connected: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.checkbox = None
        self.default_checkbox = checkbox
        self.label = None
        self.widget = widget

        # Label without checkbox
        if not isinstance(checkbox, bool):
            if widget is None:
                label = f'<b>{label}</b>'
            self.label = QLabel(label)
            if hidden:
                self.label.hide()
            if tooltip is not None:
                self.label.setToolTip(tooltip)
            self.label.mouseReleaseEvent = lambda _: self.mark(False)

            self.addWidget(self.label, stretch=split)
            if widget is None:
                return

        # Label with checkbox
        else:
            self.checkbox = QCheckBox(label)
            self.checkbox.setChecked(checkbox)
            if checkbox_connected and widget is not None:
                self.checkbox.toggled.connect(lambda state: self.widget.setEnabled(state))
            if hidden:
                self.checkbox.hide()
            if tooltip is not None:
                self.checkbox.setToolTip(tooltip)
            self.checkbox.clicked.connect(lambda _: self.mark(False))

            self.addWidget(self.checkbox, stretch=split)
            if widget is None:
                return

        # Widget
        self.widget = widget
        if tooltip is not None:
            self.widget.setToolTip(tooltip)
        if checkbox is False or disabled:
            self.widget.setEnabled(False)
        if hidden:
            self.widget.hide()
        self.addWidget(self.widget, stretch=100 - split)

        self.widget.mouseReleaseEvent = lambda _: self.mark(False)

        if isinstance(self.widget, QSpinBox) or isinstance(self.widget, QDoubleSpinBox):
            self.widget.valueChanged.connect(lambda _: self.mark(False))

    def setEnabled(self, state: bool):
        """
        Enables widget and checkbox

        :param state: True - enable; False - disable
        """

        if self.widget is not None:
            self.widget.setEnabled(state)
        if self.checkbox is not None:
            self.checkbox.setEnabled(state)

    def setHidden(self, state: bool = True):
        """
        Hides/Shows widget

        :param state: True - hide; False - show
        """

        self.label.setHidden(state)
        if self.widget is not None:
            self.widget.setHidden(state)
        if self.checkbox is not None:
            self.checkbox.setHidden(state)

    def mark(self, enable: bool = True):
        """
        Enables/disables widget background color

        :param enable: True - show background; False - no background
        """

        if self.widget is not None:
            setWidgetBackground(self.widget, enable)

    def reset(self):
        """Resets the widget and clears mark"""
        self.mark(False)
        if hasattr(self.widget, 'reset'):
            self.widget.reset()
        if self.checkbox is not None:
            self.checkbox.setChecked(self.default_checkbox)


class SpinBoxRange:
    """
    Special input ranges for SpinBox and DoubleSpinBox
    """

    INF = 2147483647
    NEG_INF = -2147483648
    INF_INF = (NEG_INF, INF)
    ZERO_INF = (0, INF)
    ONE_INF = (1, INF)
    NEG_INF_ZERO = (NEG_INF, 0)
    NEG_ONE_INF = (-1, INF)


class SpinBox(QSpinBox):
    """
    Extension of QSpinBox.

    :param default: default value to start with and reset
    :param step_size: (optional) step size for increasing/decreasing
    :param input_range: (optional) valid input range
    :param buttons: (optional) if buttons for increasing/decreasing should be displayed
    """

    def __init__(
        self,
        *args,
        default: float | int = 0,
        step_size: int = None,
        input_range: tuple[float, float] = None,
        scroll: bool = False,
        buttons: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.setMinimumSize(50, 20)

        default = int(default)
        self.default = default

        if step_size is not None:
            self.setSingleStep(step_size)

        if input_range is not None:
            self.setRange(int(input_range[0]), int(input_range[1]))

        if buttons is False:
            self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        if not scroll:
            self.wheelEvent = lambda event: None

        self.setValue(default)

    def reset(self):
        """Resets itself to its default value"""
        self.setValue(self.default)


class DoubleSpinBox(QDoubleSpinBox):
    """
    Extension of QDoubleSpinBox.

    :param default: default value to start with and reset
    :param step_size: (optional) step size for increasing/decreasing
    :param input_range: (optional) valid input range
    :param decimals: (optional) number of decimal places
    :param buttons: (optional) if buttons for increasing/decreasing should be displayed
    :param readonly: (optional) read only allowed - automatically disables buttons
    :param click_copy: (optional) copies its data into the clipboard - automatically sets readonly
    """

    def __init__(
        self,
        *args,
        default: float = 0,
        step_size: float = None,
        input_range: tuple[float, float] = None,
        scroll: bool = False,
        decimals: int = None,
        buttons: bool = False,
        readonly: bool = False,
        click_copy: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.setMinimumSize(50, 20)

        self.default = default
        self.click_copy = click_copy
        self.decimals_min = 1

        if step_size is not None:
            self.setSingleStep(step_size)

        if input_range is not None:
            self.setRange(input_range[0], input_range[1])

        if decimals is not None:
            self.setDecimals(decimals)

        if not buttons or readonly or click_copy:
            self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        if readonly or click_copy:
            self.setReadOnly(True)

        if click_copy:
            self.setToolTip('Click to copy')
            self.setLineEdit(LineEdit(click_copy=True))

        if not scroll:
            self.wheelEvent = lambda event: None

        self.setValue(default)

    def reset(self):
        """Resets itself to its default value"""
        self.setValue(self.default)

    def textFromValue(self, value: float) -> str:
        """Removes unnecessary long tailing zeros in input field"""
        decimals_total = decimals = self.decimals()
        value_str = f'{value:.{decimals_total}f}'
        for char in value_str[::-1]:
            if char != '0':
                break
            decimals -= 1
        decimals = max(decimals, self.decimals_min)
        decimals_remove = decimals_total - decimals
        value_formatted_str = super().textFromValue(value)
        if decimals_remove:
            value_formatted_str = value_formatted_str[:-decimals_remove]
        return value_formatted_str


class LineEdit(QLineEdit):
    """
    Extension of QLineEdit

    :param default: default value to start with and reset
    :param placeholder: (optional) placeholder text
    :param max_length: (optional) maximum input length
    :param readonly: (optional) read only allowed - automatically disables buttons
    :param click_copy: (optional) copies its data into the clipboard - automatically sets readonly
    """

    def __init__(
        self,
        *args,
        default: str = '',
        placeholder: str = None,
        max_length: int = None,
        readonly: bool = False,
        click_copy: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.default = default
        self.setText(default)
        self.click_copy = click_copy

        if placeholder is not None:
            self.setPlaceholderText(placeholder)

        if max_length is not None:
            self.setMaxLength(max_length)

        if readonly or click_copy:
            self.setReadOnly(True)

        if click_copy:
            self.setToolTip('Click to copy')

    def reset(self):
        """Resets itself to its default value"""
        self.setText(self.default)

    def mousePressEvent(self, event):
        """On mouse press event"""
        if self.click_copy:
            QApplication.clipboard().setText(self.text())
        super().mousePressEvent(event)


class ComboBox(QComboBox):
    """
    Extension of QComboBox

    :param default: default selected element
    :param entries: list of possible choices
    :param tooltips: (optional) list of tooltips when hovered over one choice
    :param entries_save: (optional) list of entries for saving
    :param numbering: (optional) numbers entries (starting from this index)
    :param label_default: (optional) labels the default selected
    :param disabled_list: (optional) enable/disable choices
    :param scroll: (optional) enable/disable scrolling
    """

    def __init__(
        self,
        *args,
        default: int = 0,
        entries: list[str] = None,
        tooltips: list[str] = None,
        entries_save: list = None,
        numbering: int = None,
        label_default: bool = False,
        disabled_list: list[int] = None,
        scroll: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.default = default
        self.entries_save = entries_save

        if entries is None:
            entries = []
        self.entries = entries

        if numbering is not None:
            if default:
                self.default -= numbering
            entries = [f'{i + numbering}: {entry}' for i, entry in enumerate(entries)]

        if label_default:
            entries[self.default] = f'{entries[self.default]} (default)'

        self.addItems(entries)
        self.setCurrentIndex(self.default)

        if tooltips is not None and len(tooltips) == len(entries):
            for i, tip in enumerate(tooltips):
                self.setItemData(i, tip, Qt.ItemDataRole.ToolTipRole)

        if disabled_list is not None:
            for i in disabled_list:
                self.model().item(i, 0).setEnabled(False)

        if not scroll:
            self.wheelEvent = lambda event: None

    def reinitialize(
        self,
        default: int = 0,
        entries: list[str] = None,
        tooltips: list[str] = None,
        entries_save: list = None,
        numbering: int = None,
        label_default: bool = False,
        disabled_list: list[int] = None,
        scroll: bool = False
    ):
        """
        Reinitializes itself

        :param default: default selected element
        :param entries: list of possible choices
        :param tooltips: (optional) list of tooltips when hovered over one choice
        :param entries_save: (optional) list of entries for saving
        :param numbering: (optional) numbers entries (starting from this index)
        :param label_default: (optional) labels the default selected
        :param disabled_list: (optional) enable/disable choices
        :param scroll: (optional) enable/disable scrolling
        """

        self.clear()

        self.default = default
        self.entries_save = entries_save

        if entries is None:
            entries = []
        self.entries = entries

        if numbering is not None:
            if default:
                self.default -= numbering
            entries = [f'{i + numbering}: {entry}' for i, entry in enumerate(entries)]

        if label_default:
            entries[self.default] = f'{entries[self.default]} (default)'

        self.addItems(entries)
        self.setCurrentIndex(self.default)

        if tooltips is not None and len(tooltips) == len(entries):
            for i, tip in enumerate(tooltips):
                self.setItemData(i, tip, Qt.ItemDataRole.ToolTipRole)

        if disabled_list is not None:
            for i in disabled_list:
                self.model().item(i, 0).setEnabled(False)

        if not scroll:
            self.wheelEvent = lambda event: None

    def reset(self):
        """Resets itself to its default value"""
        self.setCurrentIndex(self.default)

    def getValue(self, text: bool = False, save: bool = False):
        """
        Returns value of widget

        :param text: return text of selected choice
        :param save: return save element of selected choice
        """

        current_index = self.currentIndex()
        if text:
            if current_index == -1:
                return '-1'
            return self.entries[current_index]
        if save and self.entries_save is not None:
            if current_index == -1:
                return '-1'
            return self.entries_save[current_index]
        return current_index

    def setValue(self, value, from_entries_save: bool = False):
        """
        Sets value of widget

        :param value: value to be set
        :param from_entries_save: value is element of entries_save list
        """

        if from_entries_save:
            value = self.entries_save.index(value)
        return self.setCurrentIndex(value)

    def getDefaultSave(self):
        """Returns default from entry_save"""
        if self.default in range(len(self.entries_save)):
            return self.entries_save[self.default]
        return None

    def updateDisabledList(self, disabled_list: list[int] = None):
        """
        Update the disabled list

        :param disabled_list: new disabled list
        """

        if disabled_list is None:
            disabled_list = []

        for i in range(len(self.entries)):
            enable = True
            if i in disabled_list:
                enable = False
            self.model().item(i, 0).setEnabled(enable)


class IndicatorLed(QWidget):
    """
    Indicating Led that extends the QWidget class

    :param state: initial state of indicator
    :param clickable: if indicator can be toggled via click
    :param on_color: color if indicator is on
    :param off_color: color if indicator is off
    :param size: wanted QSize
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        *args,
        state: bool = False,
        clickable: bool = False,
        on_color: str = Colors.cooperate_lime,
        off_color: str = Colors.app_background,
        size: QSize | None = Styles.indicator_size,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.state = state
        self.clickable = clickable
        self.on_color = on_color
        self.off_color = off_color
        self.size = size

        self.pressed = False
        self.renderer = QSvgRenderer()

    def value(self) -> bool:
        """Returns its state"""

        return self.state

    def setValue(self, state: bool):
        """
        Sets its state
        :param state: new state
        """

        self.state = state
        self.update()

    def toggleValue(self):
        """Toggles state"""

        self.state = not self.state
        self.update()

    def sizeHint(self) -> QSize:
        """Returns its size hint"""

        if self.size is not None:
            return self.size
        return QSize(48, 48)

    def minimumSizeHint(self) -> QSize:
        """Returns minimum size hint"""

        return self.sizeHint()

    def paintEvent(self, event):
        """Paints widget"""

        option = QStyleOption()
        option.initFrom(self)

        h = option.rect.height()
        w = option.rect.width()
        size = min(w, h)
        x = abs(size - w) / 2.0
        y = abs(size - h) / 2.0
        bounds = QRectF(x, y, size, size)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = self.on_color
        if not self.state:
            color = self.off_color

        svg = Forms.svgIndicatorLed(color)

        self.renderer.load(QByteArray(svg.encode('utf8')))
        self.renderer.render(painter, bounds)

    def mousePressEvent(self, event):
        """When mouse is pressed"""

        self.pressed = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """When mouse is released"""

        if self.pressed:
            self.pressed = False
            if self.clickable:
                self.toggleValue()
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class IndicatorLedButton(QWidget):
    """
    Extends the IndicatorLed with some Label in the same line to the right

    :param label: label for the indicator
    :param initial_state: initial state (default: False)
    """

    clicked = pyqtSignal()

    def __init__(self, label: str, *args, initial_state: bool = False, **kwargs):
        super().__init__(*args, **kwargs)

        self.hbox_layout = QHBoxLayout()
        self.hbox_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.hbox_layout)

        self.indicator_led = IndicatorLed(**kwargs, clickable=True, state=initial_state)
        self.indicator_led.clicked.connect(lambda: self.clicked.emit())
        self.hbox_layout.addWidget(self.indicator_led)

        self.label = QLabel(label)
        self.hbox_layout.addWidget(self.label)

    def value(self) -> bool:
        """Returns its state"""
        return self.indicator_led.value()


class PressureWidget(QWidget):
    """
    Widget that extends the QWidget to display the pressure

    :param input_range: input range as tuple of (maximum exponent, minimum exponent)
    """

    def __init__(
        self,
        input_range: tuple[float, float] = (-2, -10),
        **kwargs
    ):
        super().__init__(**kwargs)

        self.input_range = input_range

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.main_layout)

        self.stack_widget = StackWidget(
            color_top=Colors.cooperate_lime,
            color_bottom=Colors.cooperate_strawberry,
            color_grayed=Colors.app_background_event
        )
        self.main_layout.addWidget(self.stack_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.pressure = 0
        self.pressure_label = QLabel('', self)
        self.main_layout.addWidget(self.pressure_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setPressure(self.pressure)

    def setPressure(self, pressure: float):
        """
        Sets the pressure

        :param pressure: pressure in mbar
        """

        self.pressure = pressure
        percentage = 1
        label_text = 'No pressure available'
        exponent = self.input_range[0] + 1

        self.stack_widget.enableDigit(bool(pressure))
        if pressure:
            pressure_string_split = f'{self.pressure:E}'.split('E')
            exponent = int(pressure_string_split[1])
            label_text = f'{pressure_string_split[0]} x 10<sup>{exponent}</sup> mbar'

            percentage = 1 - (log10(pressure) - self.input_range[0]) / (self.input_range[1] - self.input_range[0])
            percentage = max(percentage, 0)
            percentage = min(percentage, 1)

        self.pressure_label.setText(label_text)
        self.stack_widget.changePercentage(percentage)

        self.stack_widget.setValue('OR' if percentage == 1 else -exponent)


class StackWidget(QLCDNumber):
    """
    Graphical widget that extends the QLCDNumber to display a LCD-styled number inside a colored stack.
    The color of the spack can be set in relation with how "good" the number is

    :param layers: number of layers
    :param antialiased: antialiasing enabled
    :param size: size of widget
    :param border_radius: radius of borders
    :param color_top: top color
    :param color_bottom: bottom color
    :param color_grayed: grayed out color
    :param percentage_grey: greyed out percentage
    :param enable_digits: display digit
    """

    def __init__(
        self,
        *args,
        layers: int = 8,
        antialiased: bool = True,
        size: QSize = QSize(100, 100),
        border_radius: float = 5,
        spacing: float = 1,
        color_top: QColor | Qt.GlobalColor | str = Colors.cooperate_lime,
        color_bottom: QColor | Qt.GlobalColor | str = Colors.cooperate_strawberry,
        color_grayed: QColor | Qt.GlobalColor | str = Colors.app_background_event,
        percentage_grey: float = 0,
        enable_digits: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.layers = layers
        self.antialiased = antialiased
        self.size = size
        self.border_radius = border_radius
        self.spacing = spacing
        self.color_top = QColor(color_top)
        self.color_bottom = QColor(color_bottom)
        self.color_grayed = QColor(color_grayed)
        self.enable_digits = enable_digits

        self.layer_height = (self.size.height() - (self.layers - 1) * self.spacing) / self.layers
        self.percentage_grey = 0
        self.percentage_offset = 0.001
        self.color_middle = self.color_top
        self.changePercentage(percentage_grey)

        self.setAutoFillBackground(True)

    def sizeHint(self) -> QSize:
        """Returns the optimal size of the widget"""

        return self.size

    def minimumSizeHint(self) -> QSize:
        """Returns the minimum size of the widget"""

        return self.size

    def setValue(self, value: int | str):
        """
        Sets its own value

        :param value: value to be displayed
        """

        self.setDigitCount(len(str(value)))
        self.display(value)

    def enableDigit(self, enable_digits: bool):
        """
        Enables digits to be displayed

        :param enable_digits: if digits should be displayed
        """

        self.enable_digits = enable_digits

    def changePercentage(self, percentage_grey: float):
        """
        Changes the greyed out percentage level

        :param percentage_grey: greyed out percentage
        """

        self.color_middle = linearInterpolateColor(self.color_top, self.color_bottom, percentage_grey)
        self.percentage_grey = percentage_grey

    def paintEvent(self, event):
        """
        Called when Widget is drawn

        :param event: draw event
        """

        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.antialiased)

        gradient = QLinearGradient(0, 0, 0, self.size.height())
        gradient.setColorAt(0, self.color_grayed)
        gradient.setColorAt(self.percentage_grey - self.percentage_offset, self.color_grayed)
        gradient.setColorAt(self.percentage_grey, self.color_middle)
        gradient.setColorAt(1, self.color_bottom)

        brush = QBrush(gradient)
        painter.setBrush(brush)

        for i in range(self.layers):
            path = QPainterPath()
            path.addRoundedRect(
                QRectF(0, i * (self.layer_height + self.spacing), self.size.width(), self.layer_height),
                self.border_radius,
                self.border_radius
            )
            painter.drawPath(path)

        if self.enable_digits:
            super().paintEvent(event)


class DisplayLabel(QLabel):
    """
    Graphical widget that extends the QLabel to display a value and color it how far the current value is away from the target value

    :param value: current value
    :param target_value: target value
    :param target_value_sign: if sign of target_value matters
    :param deviation: deviation value
    :param unit: unit to be displayed
    :param decimals: decimals to be shown
    :param enable_prefix: enable prefixing
    :param alignment_flag: alignment flag
    :param antialiased: antialiasing enabled
    :param color_good: top color
    :param color_bad: bottom color
    :param color_grayed: grayed out color
    :param tooltip: set target value as tooltip
    """

    def __init__(
        self,
        *args,
        value: float | None = 0,
        target_value: float = 1,
        target_value_sign: bool = False,
        deviation: float = 1,
        unit: str = '',
        decimals: int = 2,
        enable_prefix: bool = False,
        alignment_flag: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight,
        antialiased: bool = True,
        color_good: QColor | Qt.GlobalColor | str = Colors.cooperate_lime,
        color_bad: QColor | Qt.GlobalColor | str = Colors.cooperate_strawberry,
        color_grayed: QColor | Qt.GlobalColor | str = Colors.app_background_event,
        tooltip: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.value = value
        self.target_value = target_value
        self.target_value_sign = target_value_sign
        self.deviation = deviation
        self.unit = unit
        self.decimals = decimals
        self.enable_prefix = enable_prefix
        self.antialiased = antialiased
        self.color_good = QColor(color_good)
        self.color_bad = QColor(color_bad)
        self.color_grayed = QColor(color_grayed)
        self.tooltip = tooltip

        self.setAlignment(alignment_flag)
        self.setContentsMargins(5, 5, 5, 5)
        self._writeOwnText()

    def _writeOwnText(self):
        """Writes its own text"""

        text = 'xxx'
        value = self.value
        addon = self.unit

        if addon.lower() == 'min' and not self.enable_prefix:
            text = f'{int(value)}:{int(value * 60) % 60:02d}'

        elif addon.lower() == 'h' and not self.enable_prefix:
            text = f'{int(value)}:{int(value * 60) % 60:02d}:{int(value * 3600) % 60:02d}'

        else:
            if value is not None and (isinstance(value, float) or isinstance(value, int)):
                if self.enable_prefix:
                    value, prefix = getPrefix(value)
                    addon = prefix + addon
                text = f'{value:.{self.decimals}f}'
            if addon:
                text += ' ' + addon

        self.setText(text)

        if self.tooltip:
            tooltip = 'No tooltip available'
            target_value = self.target_value
            addon = self.unit

            if addon.lower() == 'min' and not self.enable_prefix:
                tooltip = f'{int(value)}:{round((value * 60) % 60)}'

            elif addon.lower() == 'h' and not self.enable_prefix:
                tooltip = f'{int(value)}:{int((value * 60) % 60)}:{round((value * 3600) % 60)}'

            else:
                if target_value is not None and (isinstance(target_value, float) or isinstance(target_value, int)):
                    if self.enable_prefix:
                        target_value, prefix = getPrefix(target_value)
                        addon = prefix + addon
                    tooltip = f'{target_value:.{self.decimals}f}'
                if addon:
                    tooltip += ' ' + addon

            self.setToolTip(f'Target value: {tooltip}')

    def setValue(self, value: float):
        """
        Set a new value

        :param value: new value
        """

        if not isinstance(value, float) and not isinstance(value, int):
            GlobalConf.logger.warning(f'Error during setValue() in DisplayLabel. Argument must be of type <float> or <int>, got "{type(value)}"')
            return

        self.value = value
        self._writeOwnText()

    def setTargetValue(self, target_value: float):
        """
        Set a new target value

        :param target_value: new target value
        """

        self.target_value = target_value
        self._writeOwnText()

    def setTargetValueSign(self, target_value_sign: bool):
        """
        Set a new target value

        :param target_value_sign: if target_value sign matters
        """

        self.target_value_sign = target_value_sign
        self._writeOwnText()

    def setDeviation(self, deviation: float):
        """
        Set a new deviation

        :param deviation: new deviation
        """

        self.deviation = deviation
        self._writeOwnText()

    def paintEvent(self, event):
        """
        Called when Widget is drawn

        :param event: draw event
        """

        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.antialiased)

        brush = QBrush(self.color_grayed)
        if self.value is not None:
            if self.target_value_sign:
                difference = self.value - self.target_value
            else:
                difference = abs(self.value) - abs(self.target_value)
            percentage = 0
            if self.deviation != 0:
                percentage = min(abs(difference) / self.deviation, 1)
            new_color = linearInterpolateColor(self.color_good, self.color_bad, percentage)
            new_color.setAlpha(90)
            brush.setColor(new_color)
        painter.setBrush(brush)

        painter.drawRect(QRectF(0, 0, self.width(), self.height()))

        super().paintEvent(event)


class PolarityButton(QWidget):
    """
    Combination of two Buttons for controlling positive and negative polarity

    :param color_positive: positive enabled color
    :param color_negative: negative enabled color
    :param color_grayed: grayed out color
    :param connected_buttons: buttons are connected to color change
    """

    pressed = pyqtSignal(bool)

    def __init__(
        self,
        *args,
        color_positive: QColor | Qt.GlobalColor | str = Colors.cooperate_lime,
        color_negative: QColor | Qt.GlobalColor | str = Colors.cooperate_strawberry,
        color_grayed: QColor | Qt.GlobalColor | str = Colors.app_background_event,
        connected_buttons: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.color_positive = qColorToHex(QColor(color_positive))
        self.color_negative = qColorToHex(QColor(color_negative))
        self.color_grayed = qColorToHex(QColor(color_grayed))

        self.state = None

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.positive_button = QPushButton(self)
        self.positive_button.setIcon(QIcon('icons/positive.png'))
        self.main_layout.addWidget(self.positive_button)

        self.negative_button = QPushButton(self)
        self.negative_button.setIcon(QIcon('icons/negative.png'))
        self.main_layout.addWidget(self.negative_button)

        if connected_buttons:
            self.positive_button.pressed.connect(lambda: self.polarityChange(True))
            self.negative_button.pressed.connect(lambda: self.polarityChange(False))

        self.positive_button.pressed.connect(lambda: self.pressed.emit(True))
        self.negative_button.pressed.connect(lambda: self.pressed.emit(False))

        self._setButtonColors()

    def polarityChange(self, polarity: bool):
        """
        Called when the polarity has changed

        :param polarity: polarity of button (True = positive; False = negative)
        """

        self.state = polarity
        self._setButtonColors()

    def reset(self):
        """Resets both buttons"""

        self.state = None
        self._setButtonColors()

    def _setButtonColors(self):
        """Sets colors of buttons"""

        self.positive_button.setStyleSheet(f'background-color: {self.color_grayed};')
        self.negative_button.setStyleSheet(f'background-color: {self.color_grayed};')

        if self.state is True:
            self.positive_button.setStyleSheet(f'background-color: {self.color_positive};')
        elif self.state is False:
            self.negative_button.setStyleSheet(f'background-color: {self.color_negative};')


class ErrorTable(QTableWidget):
    """
    Simple table that extends the QTableWidget.

    :param default_rows: number of rows to be displayed
    """

    def __init__(
        self,
        *args,
        default_rows: int = 3,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.actual_row = 0
        self.default_rows = default_rows

        self.setColumnCount(3)
        self.setRowCount(self.default_rows)
        self.verticalHeader().setVisible(False)
        self.setHorizontalHeaderLabels(['#', 'Type', 'Description'])
        self.setColumnWidth(0, 50)
        self.setColumnWidth(1, 100)
        self.horizontalHeader().setStretchLastSection(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

    def insertError(self, error_code: int, error_type: str, error_description: str):
        """
        Inserts new row into the table

        :param error_code: code of error
        :param error_type: type of error
        :param error_description: description of error
        """

        if self.rowCount() <= self.actual_row:
            self.insertRow(self.actual_row)
        self.setItem(self.actual_row, 0, QTableWidgetItem(str(error_code)))
        self.setItem(self.actual_row, 1, QTableWidgetItem(error_type))
        self.setItem(self.actual_row, 2, QTableWidgetItem(error_description))
        self.actual_row += 1

    def getErrorList(self) -> list[int]:
        """Returns list of errors"""

        errors = []
        for row_id in range(self.rowCount()):
            item = self.item(row_id, 0)
            if item is not None:
                errors.append(int(item.text()))
        return errors

    def resetTable(self):
        """Resets the table"""

        self.setRowCount(0)
        self.setRowCount(self.default_rows)
        self.actual_row = 0

    def sizeHint(self) -> QSize:
        """Returns an optimal size for itself"""

        size = super().sizeHint()
        size.setHeight(self.horizontalHeader().height() + self.rowHeight(0) * 3)
        return size

    def minimumSizeHint(self) -> QSize:
        """Returns a minimum size for itself"""

        return self.sizeHint()


class DeleteWidgetList(QListWidget):
    """
    Extends the QListWidget for deletable Items
    """

    checkedChanged = pyqtSignal()

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSpacing(0)

        self.info_text = 'Select files first'
        self.addInfoItem()

    def addItem(self, aitem: DeleteWidgetListItem):
        """
        Adds DeleteWidgetListItem to list

        :param aitem: DeleteWidgetListItem to be added
        """

        if self.count() == 1 and self.item(0).text() == self.info_text:
            self.takeItem(0)

        item = QListWidgetItem(self)
        item.setSizeHint(aitem.sizeHint())
        self.setItemWidget(item, aitem)
        aitem.deleted.connect(lambda ditem=item: self.deleteItem(ditem))
        aitem.checkedChanged.connect(lambda: self.checkedChanged.emit())

        if not len(self.selectedItems()):
            self.setCurrentRow(0)

    def deleteItem(self, ditem: QListWidgetItem):
        """
        Deletes Item from list

        :param ditem: item to delete
        """

        self.takeItem(self.row(ditem))

        if not self.count():
            self.addInfoItem()

    def clearAll(self):
        """Clears all items in this list"""

        self.clear()
        self.addInfoItem()

    def checkAll(self):
        """Checks all items"""

        for row in range(self.count()):
            item = self.itemWidget(self.item(row))
            if isinstance(item, DeleteWidgetListItem):
                item.setChecked(True)

    def uncheckAll(self):
        """Unchecks all items"""

        for row in range(self.count()):
            item = self.itemWidget(self.item(row))
            if isinstance(item, DeleteWidgetListItem):
                item.setChecked(False)

    def resetColors(self):
        """Resets all colors of items"""

        for row in range(self.count()):
            item = self.itemWidget(self.item(row))
            if isinstance(item, DeleteWidgetListItem):
                item.setBackgroundColor(item.default_background_color)

    def checkedRows(self) -> list[int]:
        """Returns the checked rows"""

        checked = []
        checked_time = []
        for row in range(self.count()):
            item = self.itemWidget(self.item(row))
            if isinstance(item, DeleteWidgetListItem):
                if item.checked():
                    checked.append(row)
                    checked_time.append(item.checked())

        return [check for _, check in sorted(zip(checked_time, checked))]

    def addInfoItem(self):
        """Adds info item to the list"""

        item_info = QListWidgetItem(self.info_text, self)
        item_info.setFlags(Qt.ItemFlag.NoItemFlags)
        super().addItem(item_info)

    def containedItems(self) -> list[DeleteWidgetListItem]:
        """Returns a list of contained DeleteWidgetListItem"""

        delete_widgets = []
        for row in range(self.count()):
            widget = self.itemWidget(self.item(row))
            if isinstance(widget, DeleteWidgetListItem):
                delete_widgets.append(widget)
        return delete_widgets


class DeleteWidgetListItem(QWidget):
    """
    A Widget that acts as deletable ListWidgetItem for the list DeleteWidgetList

    :param path: title of Widget
    :param tac: tac time
    :param delay: delay time
    """

    deleted = pyqtSignal()
    checkedChanged = pyqtSignal()

    def __init__(
        self,
        path: str,
        *args,
        tac: int = -1,
        delay: float = 0,
        default_background_color: str = '#ffffff',
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.path = path
        self.tac = tac
        self.delay = delay
        self.checkbox_time = 0
        self.default_background_color = default_background_color

        self.setToolTip(self.path)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.delete_button = QPushButton(self)
        self.delete_button.setIcon(QIcon('icons/delete.png'))
        self.delete_button.clicked.connect(lambda: self.deleted.emit())
        self.main_layout.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.checkbox = QCheckBox()
        self.setBackgroundColor(self.default_background_color)
        self.main_layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignLeft)
        self.checkbox.stateChanged.connect(self.checkboxClicked)

        self.label = QLabel(self.path, self)
        self.main_layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft)

    def __str__(self) -> str:
        """Represents itself as string by returning its path"""
        return self.path

    def checkboxClicked(self):
        """Called when checkbox is clicked"""

        self.checkbox_time = 0
        if self.checkbox.isChecked():
            self.checkbox_time = time()
        else:
            self.setBackgroundColor(self.default_background_color)

        self.checkedChanged.emit()

    def checked(self) -> float:
        """Returns state of checkbox"""
        return self.checkbox_time

    def setChecked(self, state: bool):
        """Set checked state"""
        self.checkbox.setChecked(state)

    def setBackgroundColor(self, color: str):
        """Sets background color of the checkbox"""

        self.checkbox.setStyleSheet(f'''
            QCheckBox::indicator {{ background-color: {color}; }}
            QCheckBox::indicator::unchecked {{ background-color: {color}; }}
            QCheckBox::indicator::checked {{ background-color: {color}; }}
        ''')


class StackedVBoxLayout(QVBoxLayout):
    """
    Creates some sort of GridBoxLayout for DoubleSpinBoxes based on the provided labels
    Extends the QVBoxLayout

    :param labels: dictionary of {(position_row, position_column): label}
    :param click_copy: (optional) copies its contents
    """

    def __init__(
        self,
        labels: dict[tuple[int, int], str],
        *args,
        click_copy: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.mapping = {}
        self.rows: dict[int, dict[int, tuple[str, int]]] = {}

        # add to rows dictionary
        for pos, ((row, col), label) in enumerate(labels.items()):
            item = {label: pos}
            row_list = self.rows.get(row)
            if row_list is None:
                self.rows[row] = item
                continue
            row_list.update(item)

        # sort rows
        self.rows = dict(sorted(self.rows.items()))
        for row in self.rows.values():
            hbox = QHBoxLayout()
            hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.addLayout(hbox)

            for label, pos in sorted(row.items(), reverse=True):
                hbox.addWidget(QLabel(label))
                spinbox = DoubleSpinBox(
                    input_range=SpinBoxRange.INF_INF,
                    decimals=4,
                    click_copy=click_copy
                )
                self.mapping[pos] = spinbox
                hbox.addWidget(spinbox)

        self.mapping = list(dict(sorted(self.mapping.items())).values())

    def setValues(self, values: list[float]):
        """
        Sets values to all instanciated DoubleSpinBoxes

        :param values: list of values for DoubleSpinBoxes
        """

        for val, spinbox in zip(values, self.mapping, strict=True):
            spinbox.setValue(val)


class ButtonGridLayout(QGridLayout):
    """
    Class that creates Buttons with labels in a grid layout

    :param labels: list of strings for each button
    :param max_rows: maximum rows (-1 means no limit)
    :param max_columns: maximum columns (-1 means no limit)
    """

    buttonPressed = pyqtSignal(int)

    def __init__(
        self,
        labels: list[str],
        max_rows: int = 10,
        max_columns: int = 10,
    ):
        self.labels = labels
        if max_rows <= 0:
            max_rows = inf
        self.max_rows = max_rows
        if max_columns <= 0:
            max_columns = inf
        self.max_columns = max_columns

        super().__init__()

        self.fillGrid()

    def clearGrid(self):
        """Clears the grid"""

        for i in range(self.count() - 1, -1, -1):
            self.itemAt(i).widget().deleteLater()
        
    def fillGrid(self):
        """Fills the grid with buttons of provided labels"""

        if self.max_rows != -1 and self.max_columns != -1:
            if len(self.labels) > self.max_rows * self.max_columns:
                raise ValueError(f'more labels provided ({len(self.labels):.0f}) than max number of rows ({self.max_rows:.0f}) and columns ({self.max_columns:.0f})')

        for index, label in enumerate(self.labels):
            row, column = divmod(index, self.max_columns)
            button = QPushButton(label)
            button.setToolTip(f'Tip #{index}')
            button.clicked.connect(lambda x, i=index: self.buttonPressed.emit(i))
            self.addWidget(button, row, column)

    def newLabels(self, labels: list[str]):
        """Resets the buttons and initializes them with the provided new labels"""

        self.labels = labels
        self.clearGrid()
        self.fillGrid()


class TextEdit(QWidget):
    """
    Text editor, which is a QTextEdit with an menu bar

    :parm
    """

    def __init__(
        self,
        image_directory: str = None,
        save_button: bool = True,
        load_button: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.image_directory = image_directory

        # add menu bar
        self.menu = QMenuBar(self)
        self.main_layout.setMenuBar(self.menu)

        self.menu_file = self.menu.addMenu('File')

        if save_button:
            self.menu_file_save = QAction('Save', self)
            self.menu_file_save.setShortcut('Ctrl+S')
            self.menu_file_save.triggered.connect(self.saveFile)
            self.menu_file.addAction(self.menu_file_save)

        if load_button:
            self.menu_file_load = QAction('Open', self)
            self.menu_file_load.setShortcut('Ctrl+O')
            self.menu_file_load.triggered.connect(self.openFile)
            self.menu_file.addAction(self.menu_file_load)

        self.menu_file_insert_image = QAction('Insert Image', self)
        self.menu_file_insert_image.setShortcut('Ctrl+G')
        self.menu_file_insert_image.triggered.connect(self.insertImage)
        self.menu_file.addAction(self.menu_file_insert_image)

        self.menu_format = self.menu.addMenu('Format')

        self.menu_format_bold = QAction('Bold', self)
        self.menu_format_bold.setShortcut('Ctrl+B')
        self.menu_format_bold.triggered.connect(self.setBold)
        self.menu_format.addAction(self.menu_format_bold)

        self.menu_format_italic = QAction('Italic', self)
        self.menu_format_italic.setShortcut('Ctrl+I')
        self.menu_format_italic.triggered.connect(self.setItalic)
        self.menu_format.addAction(self.menu_format_italic)

        self.menu_format_underline = QAction('Underline', self)
        self.menu_format_underline.setShortcut('Ctrl+U')
        self.menu_format_underline.triggered.connect(self.setUnderline)
        self.menu_format.addAction(self.menu_format_underline)

        self.menu_format_increase_font = QAction('Increase Font', self)
        self.menu_format_increase_font.setShortcut('Ctrl++')
        self.menu_format_increase_font.triggered.connect(lambda: self.increaseFontSize(1))
        self.menu_format.addAction(self.menu_format_increase_font)

        self.menu_format_decrease_font = QAction('Decrease Font', self)
        self.menu_format_decrease_font.setShortcut('Ctrl+-')
        self.menu_format_decrease_font.triggered.connect(lambda: self.increaseFontSize(-1))
        self.menu_format.addAction(self.menu_format_decrease_font)

        self.menu_format_red = QAction('Change Color', self)
        self.menu_format_red.setShortcut('Ctrl+Q')
        self.menu_format_red.triggered.connect(self.changeColor)
        self.menu_format.addAction(self.menu_format_red)

        # actual text editor
        self.text_editor = QTextEdit(self)
        self.text_editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_editor.customContextMenuRequested.connect(self.showContextMenu)
        self.main_layout.addWidget(self.text_editor)

    def clearContents(self):
        """Clears contents"""
        self.text_editor.setHtml('')

    def saveFile(self, file_name: str = ''):
        """
        Save the file

        :parm file_name: if provided, this will be used for saving, otherwise file dialog will appear
        """

        if not file_name:
            file_name = selectFileDialog(self, True, 'Save File', '', 'Text Files (*.txt);;All Files (*)')

        if not file_name:
            return 1

        try:
            with open(file_name, 'w') as file:
                file.write(self.text_editor.toHtml())
        except (OSError, FileNotFoundError, FileExistsError) as e:
            QMessageBox.warning(self, 'Error', f'Failed to save file: {e}')
            return 2

    def openFile(self, file_name: str = ''):
        """
        Opens a file

        :parm file_name: if provided, this will be used for opening, otherwise file dialog will appear
        """

        if not file_name:
            file_name = selectFileDialog(self, False, 'Open File', '', 'Text Files (*.txt);;All Files (*)')

        if not file_name:
            return 1

        try:
            with open(file_name, 'r') as file:
                self.text_editor.setHtml(file.read())
        except (OSError, FileNotFoundError, FileExistsError) as e:
            QMessageBox.warning(self, 'Error', f'Failed to open file: {e}')
            return 2

    def insertImage(self):
        """Insert an image"""

        file_name = selectFileDialog(self, False, 'Open Image File', '', 'Image Files (*.png *.jpg *.bmp *.gif)')

        if not file_name:
            return

        # get width and heights
        width, ok = QInputDialog.getInt(self, 'Image Width', 'Enter width:', value=500, min=1)
        if not ok:
            return
        height, ok = QInputDialog.getInt(self, 'Image Height', 'Enter height:', value=500, min=1)
        if not ok:
            return

        # copy image if needed
        image_path = file_name
        if self.image_directory is not None:
            image_path = path.join(self.image_directory, f'{time()}_{path.basename(file_name)}')
            copy(file_name, image_path)
            image_path = path.relpath(image_path)

        cursor = self.text_editor.textCursor()
        cursor.insertHtml(f'<img src="{image_path}" width="{width}" height="{height}" />')

    def setBold(self):
        """Sets text to bold"""

        if self.text_editor.fontWeight() != QFont.Weight.Bold:
            self.text_editor.setFontWeight(QFont.Weight.Bold)
        else:
            self.text_editor.setFontWeight(QFont.Weight.Normal)

    def setItalic(self):
        """Sets text to italic"""
        self.text_editor.setFontItalic(not self.text_editor.fontItalic())

    def setUnderline(self):
        """Sets text to underline"""
        self.text_editor.setFontUnderline(not self.text_editor.fontUnderline())

    def increaseFontSize(self, increment: int):
        """Increase font size"""

        font = self.text_editor.currentFont()
        size = font.pointSize() + increment
        if size < 1:
            size = 1
        font.setPointSize(size)
        self.text_editor.setCurrentFont(font)

    def changeColor(self):
        """Change font color"""

        color = QColorDialog.getColor()
        if color.isValid():
            self.text_editor.setTextColor(color)

    def showContextMenu(self, position):
        """Shows a context menu"""

        cursor = self.text_editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)

        menu = QMenu(self)
        if '<img ' in cursor.selection().toHtml():
            resize_image = QAction('Resize Image', self)
            resize_image.triggered.connect(self.resizeImage)
            menu.addAction(resize_image)
        menu.exec(self.text_editor.viewport().mapToGlobal(position))

    def resizeImage(self):
        cursor = self.text_editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        html = cursor.selection().toHtml()

        if '<img ' not in html:
            return

        # Find the width attribute in the HTML
        width_start = html.find('width="') + 7
        width_end = html.find('"', width_start)
        width = html[width_start:width_end]
        try:
            width = int(width)
        except ValueError:
            width = 500

        # Find the height attribute in the HTML
        height_start = html.find('height="') + 8
        height_end = html.find('"', height_start)
        height = html[height_start:height_end]
        try:
            height = int(height)
        except ValueError:
            height = 500

        width, ok = QInputDialog.getInt(self, 'Image Width', 'Enter new width:', value=width, min=1)
        if not ok:
            return
        height, ok = QInputDialog.getInt(self, 'Image Height', 'Enter new height:', value=height, min=1)
        if not ok:
            return

        # Find the src attribute in the HTML
        src_start = html.find('src="') + 5
        src_end = html.find('"', src_start)
        src = html[src_start:src_end]

        # Replace the existing image HTML with new dimensions
        new_img_html = f'<img src="{src}" width="{width}" height="{height}" />'
        cursor.insertHtml(new_img_html)


class FittingWidget(QWidget):
    """
    Creates some sort of GridBoxLayout for DoubleSpinBoxes based on the provided labels
    Extends the QVBoxLayout

    :param labels: dictionary of {(position_row, position_column): label}
    :param click_copy: (optional) copies its contents
    """

    def __init__(
        self,
        labels: dict[tuple[int, int], str],
        *args,
        click_copy: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.main_layout = StackedVBoxLayout(labels, *args, click_copy=click_copy, **kwargs)
        self.setLayout(self.main_layout)
        self.setContentsMargins(0, 0, 0, 0)

    def setValues(self, values: list[float]):
        """
        Sets values to all instanciated DoubleSpinBoxes

        :param values: list of values for DoubleSpinBoxes
        """

        self.main_layout.setValues(values)


class TOFCanvas(pg.PlotWidget):
    """
    Extends the PlotWidget of pyqtgraph

    :param data: data of plot
    :param fit_class: fitting method
    """

    def __init__(
        self,
        data: list[tuple[np.ndarray, np.ndarray]],
        fit_class: FitMethod,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.data = data
        self.fit_class = fit_class

        self.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.setMouseEnabled(x=True, y=False)
        self.setLabel('left', 'Counts')
        self.setLabel('bottom', 'TOF [ns]')
        self.sigRangeChanged.connect(self.updateLimits)

        self.graph_colors = [
            Colors.cooperate_tu_blue,
            Colors.cooperate_orange,
            Colors.cooperate_maroon,
            Colors.cooperate_lime,
            Colors.cooperate_strawberry,
            Colors.cooperate_petrol,
            Colors.cooperate_violett_darker,
            Colors.cooperate_rosa,
            Colors.cooperate_error,
            Colors.cooperate_turquoise,
            Colors.cooperate_violett,
            Colors.cooperate_nude
        ]

        if len(data) > len(self.graph_colors):
            raise AttributeError('Data length can not exceed color length')

        self.graph_curves: list[pg.PlotDataItem] = [self.plotItem.plot(pen=pg.mkPen(color=color, width=1)) for color in self.graph_colors]
        self.graph_curve_fit: pg.PlotDataItem = self.plotItem.plot(pen=pg.mkPen(color=Colors.cooperate_orange, width=2))
        self.setLimits(yMin=0, xMin=0)

        self.bars: list[pg.InfiniteLine] = []

        '''
        GRID CAUSES DISPLACEMENT OF SELECTED ZOOM AREA AND IS A KNOWN BUG BY THE DEVELOPERS:
        https://github.com/pyqtgraph/pyqtgraph/pull/2034
        (Solution: https://github.com/pyqtgraph/pyqtgraph/pull/2034/commits/530a5913c414bb0217188b7828a768c68e47865f)
        -> 'pyqtgraph/graphicsItems/ViewBox/ViewBox.py' HAS TO BE UPDATED TO GET RIGHT RESULTS
        '''
        self.showGrid(y=True, x=True)

    def updateFitClass(self, fit_class: FitMethod):
        """Updates the fitting method"""
        self.fit_class = fit_class
        self.setBars(self.fit_class.bars)

    def plotData(self, data: list[tuple[np.ndarray, np.ndarray]], view_all: bool = False, fill_histogram: bool = True):
        """
        Plots data if available

        :param data: data as tuple of x and y data in np.array form
        :param view_all: force all x axes to be shown
        :param fill_histogram: fills the histogram
        """

        view_range: list[list[float, float]] = self.getViewBox().viewRange()

        if len(data) > len(self.graph_colors):
            raise AttributeError('Data length can not exceed color length')

        self.data = data

        for graph_curve in self.graph_curves:
            graph_curve.setData(x=[], y=[])

        for i, d in enumerate(data):
            data_dict = {
                'x': d[0],
                'y': d[1],
                'stepMode': 'left',
                'fillLevel': None
            }
            if fill_histogram:
                data_dict.update({
                    'connect': 'all',
                    'fillLevel': 0,
                    'brush': (*hexToRgb(self.graph_colors[i]), 80)
                })
            self.graph_curves[i].setData(**data_dict)
        self.graph_curve_fit.setData(x=[], y=[])

        xdata = [d[0] for d in self.data]

        if not any([len(xd) for xd in xdata]):
            return

        minx = min([np.min(x) for x in xdata])
        maxx = max([np.max(x) for x in xdata])

        self.setLimits(
            xMin=minx,
            xMax=maxx
        )

        # update if y range in selection would be too big and update x range if needed
        selected_ydata_min = []
        selected_ydata_max = []
        for d in self.data:
            selected_xrange = np.logical_and(d[0] > view_range[0][0], d[0] < view_range[0][1])
            selected_ydata = d[1][selected_xrange]
            if len(selected_ydata):  # and np.max(selected_ydata) > view_range[1][1]:
                selected_ydata_min.append(np.min(selected_ydata))
                selected_ydata_max.append(np.max(selected_ydata))

        if selected_ydata_min and selected_ydata_max:
            self.setYRange(min(selected_ydata_min), max(selected_ydata_max))

        if view_all:
            self.setXRange(minx, maxx)
        else:
            self.setXRange(max(minx, view_range[0][0]), min(maxx, view_range[0][1]), padding=0)

        self.limitBars()

    def limitBars(self, in_visible_range: bool = False):
        """
        Limits the bars to the possible range

        :param in_visible_range: distributes bars in visible range
        """

        if in_visible_range:
            view_range: list[list[float, float]] = self.getViewBox().viewRange()
            distance = (view_range[0][1] - view_range[0][0]) / (len(self.bars) + 1)
            for i, bar in enumerate(self.bars):
                bar.setValue(view_range[0][0] + (i + 1) * distance)

        xdata = [d[0] for d in self.data]

        if not any([len(xd) for xd in xdata]):
            return

        minx = min([np.min(x) for x in xdata])
        maxx = max([np.max(x) for x in xdata])
        xspan = maxx - minx

        for bar in self.bars:
            if bar.value() > maxx:
                bar.setValue(maxx - 0.1 * xspan)
            elif bar.value() < minx:
                bar.setValue(minx + 0.1 * xspan)

        self.draggedBar()

    def setBars(self, bars: list[pg.InfiniteLine]):
        """
        Sets bars to the plot

        :param bars: list of InfiniteLines
        """

        while len(self.bars):
            self.removeItem(self.bars.pop())

        for bar in bars:
            self.bars.append(bar)
            self.addItem(bar)
            bar.sigDragged.connect(self.draggedBar)

        self.limitBars(in_visible_range=True)

    def draggedBar(self):
        """Bar is dragged; Adapt bar boundaries, fit to data and display fit"""

        view_range: list[list[float, float]] = self.getViewBox().viewRange()

        xdata = [d[0] for d in self.data]

        if any([len(xd) for xd in xdata]):
            self.fit_class.setBarBounds((
                min([np.min(x) for x in xdata]),
                max([np.max(x) for x in xdata])
            ))
        else:
            self.fit_class.setBarBounds((view_range[0][0], view_range[0][1]))

        # only do fitting if we have one data set available
        if len(self.data) == 1:
            self.fit_class.fitting([bar.value() for bar in self.bars], self.data[0], view_range)

            if self.fit_class.parameters:
                self.graph_curve_fit.setData(
                    x=self.data[0][0],
                    y=self.fit_class.fitFunction(self.data[0][0], *self.fit_class.parameter[0:self.fit_class.parameters])
                )
            else:
                self.graph_curve_fit.setData(x=[], y=[])
        else:
            self.graph_curve_fit.setData(x=[], y=[])

    def updateLimits(self, plot_widget: pg.PlotWidget = None, view_range: list[list[float, float]] = None):
        """
        Updates the y limit of the plot depending on the selected x range

        :param plot_widget: PlotWidget from where this is called
        :param view_range: ranges for x and y: [[x_min, x_max], [y_min, y_max]]
        """

        self.draggedBar()

        # default plot widget
        if plot_widget is None:
            plot_widget = self

        # default view range
        if view_range is None:
            view_range = plot_widget.getViewBox().viewRange()

        selected_ydata_min = []
        selected_ydata_max = []
        for d in self.data:
            selected_xrange = np.logical_and(d[0] > view_range[0][0], d[0] < view_range[0][1])
            selected_ydata = d[1][selected_xrange]
            if len(selected_ydata):  # and np.max(selected_ydata) > view_range[1][1]:
                selected_ydata_min.append(np.min(selected_ydata))
                selected_ydata_max.append(np.max(selected_ydata))

        if not selected_ydata_min or not selected_ydata_max:
            return

        selected_ydata_min = min(selected_ydata_min)
        selected_ydata_max = max(selected_ydata_max)

        # check if logY is selected... this is stupidly implemented in pyqtgraph
        if self.plotItem.ctrl.logYCheck.isChecked():
            if selected_ydata_min != 0:
                selected_ydata_min = np.log10(selected_ydata_min)
            selected_ydata_max = np.log10(selected_ydata_max)

        plot_widget.setYRange(selected_ydata_min, selected_ydata_max)

    def setLogY(self, state: bool):
        """
        Sets the y-axis to logarithmic or normal

        :param state: True: logarithmic; False: normal
        """

        view_range: list[list[float, float]] = self.getViewBox().viewRange()
        self.plotItem.setLogMode(y=state)
        self.setXRange(view_range[0][0], view_range[0][1], padding=0)


class FittingBar(pg.InfiniteLine):
    """
    Acts as Fitting bar; Extends the InfiniteLine

    :param name: name of fitting bar
    :param pos: position of fitting bar
    :param label_position: position of label
    """

    def __init__(
        self,
        name: str,
        pos: float,
        *args,
        label_position: float = 0.9,
        **kwargs
    ):
        super_dict = {
            'pos': pos,
            'movable': True,
            'label': name,
            'labelOpts': {'color': Colors.cooperate_lime, 'position': label_position},
            'pen': pg.mkPen(color=Colors.cooperate_lime, width=2),
            'hoverPen': pg.mkPen(color=Colors.cooperate_strawberry, width=3),
        }
        super_dict.update(kwargs)

        super().__init__(*args, **super_dict)


def createFittingBars(names: list[str]) -> list[FittingBar]:
    """
    Creates fitting bars with specified names

    :param names: list of names for fitting bars
    """

    bars = []
    for i, name in enumerate(names):
        bar = FittingBar(name, i * 10, label_position=(0.9 - i * 0.05))
        bars.append(bar)
    return bars
