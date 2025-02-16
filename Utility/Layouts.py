from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from math import log10, inf
from time import time
from datetime import datetime
from os import path, listdir, rename as os_rename, remove as os_remove
from shutil import copy
from io import BytesIO
from enum import Enum, auto
import logging


import numpy as np

from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QSize, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QIcon, QPainter, QPixmap, QColor, QBrush, QLinearGradient, QPainterPath, QAction, QFont, QFontMetrics, QTextCursor,
    QPen, QTextFormat, QPalette
)
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QApplication, QStyleOption, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QGridLayout, QLCDNumber, QFrame, QTextEdit, QMenuBar, QMessageBox, QInputDialog, QMenu, QColorDialog, QDialog,
    QGroupBox, QDateTimeEdit, QCalendarWidget, QDial, QHeaderView, QPlainTextEdit
)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtSvg import QSvgRenderer

import pyqtgraph as pg

import matplotlib.pyplot as plt


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors, Styles, Forms

from Log.Logger import matplotlibLogLevel

from DB.db import DB

from Utility.ModifyWidget import setWidgetBackground
from Utility.Functions import CyclicList, getPrefix
from Utility.Color import hexToRgb, linearInterpolateColor, qColorToHex
from Utility.FileDialogs import selectFileDialog

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

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        pass


class PopoutWidget(QDialog):
    """
    Popout widget used in VBoxTitleLayout if popout is requested

    :param vbox_title_layout: parent VBoxTitleLayout
    """

    def __init__(
        self,
        vbox_title_layout: VBoxTitleLayout
    ):
        self.vbox_title_layout = vbox_title_layout
        super().__init__(self.vbox_title_layout.parent)

        self.setWindowTitle(self.vbox_title_layout.title_str)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)

        self.vbox_layout = QVBoxLayout()
        self.setLayout(self.vbox_layout)

        self.vbox_title_layout.body_widget.setParent(self)
        self.vbox_layout.addWidget(self.vbox_title_layout.body_widget)

    def closeEvent(self, event):
        """Called when close button is pressed"""
        self.vbox_title_layout.restoreMainWidget()
        event.accept()


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
        popout_enable: bool = False,
        spacing: int = 0,
        add_stretch: bool | int = 0
    ):
        super().__init__(parent)
        self.parent = parent
        self.title_str = title
        self.title_style = title_style
        self.title_style_busy = title_style_busy
        self.busy_symbol = busy_symbol
        self.popout_enable = popout_enable

        self.setSpacing(spacing)
        self.header_layout = QHBoxLayout()

        self.title = QLabel(self.title_str, self.parent)
        self.title.setStyleSheet(title_style)
        self.header_layout.addWidget(self.title)

        self.popout_button: QPushButton | None = None
        self.popout_widget: PopoutWidget | None = None

        if self.popout_enable:
            self.popout_button = QPushButton(self.parent)
            self.popout_button.setToolTip('Popout widget')
            self.popout_button.setIcon(QIcon('icons/open_external.png'))
            self.popout_button.setStyleSheet(title_style)
            self.popout_button.clicked.connect(self._popout)
            self.header_layout.addWidget(self.popout_button)

        if isinstance(add_stretch, bool) and add_stretch:
            self.header_layout.addStretch(1)
        elif isinstance(add_stretch, int):
            self.header_layout.addSpacing(add_stretch)

        self.addLayout(self.header_layout)

        self.body_widget = QGroupBox(self.parent)
        self.addWidget(self.body_widget)

        self.body_replacement_widget = QGroupBox(self.parent)
        self.body_replacement_layout = QVBoxLayout(self.parent)
        self.body_replacement_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label_popped_out = QLabel('Widget is popped out.', self.parent)
        self.body_replacement_layout.addWidget(self.label_popped_out)
        self.body_replacement_widget.setLayout(self.body_replacement_layout)
        self.addWidget(self.body_replacement_widget)
        self.body_replacement_widget.setVisible(False)

    def setBodyLayout(self, layout):
        """Sets the layout of the body"""
        self.body_widget.setLayout(layout)

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

    def _popout(self):
        """Removes all widgets from this QVBoxTitleLayout and stores them in the popout widget"""

        if self.popout_widget is None:
            self.removeWidget(self.body_widget)
            self.body_widget.setParent(None)

            self.popout_widget = PopoutWidget(self)
            self.popout_widget.show()
            self.body_replacement_widget.setVisible(True)

        else:
            self.restoreMainWidget()

    def restoreMainWidget(self):
        """Restores all widgets inside this VBoxTitleLayout"""

        self.body_replacement_widget.setVisible(False)

        if self.popout_widget:
            self.popout_widget.close()
            self.popout_widget = None
        self.addWidget(self.body_widget)


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


class FilePath(QWidget):
    """
    Extension of QLineEdit for selecting and displaying a file path local and remote

    :param placeholder: (optional) placeholder text
    :param function: (optional) function that will be called when local button is pressed.
                                Return value of the function will be displayed.
    :param icon: (optional) icon of pushbutton for local file
    """

    def __init__(
        self,
        placeholder: str = None,
        function: Callable = None,
        icon: QIcon = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.path = ''
        self.path_display = QLineEdit()
        if placeholder is not None:
            self.path_display.setPlaceholderText(placeholder)
        self.path_display.setReadOnly(True)
        self.path_display.setMinimumWidth(300)
        self.layout.addWidget(self.path_display, Qt.AlignmentFlag.AlignLeft)

        self.function = function
        self.button = QPushButton()
        if self.function is not None:
            if icon is None:
                icon = QIcon('icons/open.png')
            self.button.setIcon(icon)
            self.button.setMinimumSize(40, 10)
            self.button.setMaximumSize(40, 30)
            self.layout.addWidget(self.button, Qt.AlignmentFlag.AlignRight)

            self.button.clicked.connect(self.selectPath)

    def setPath(self, new_path: str):
        """Sets a path"""
        self.path = new_path
        self.displayPath()

    def displayPath(self):
        """Displays the path in QLineEdit"""
        if not self.path:
            self.path_display.setText('')
            return
        self.path_display.setText(self.path)

    def selectPath(self):
        """Sets a new local path"""
        returned_path = self.function()
        if returned_path is not None:
            self.path = returned_path
            self.displayPath()


class ClockDial(QDial):
    """
    Class extending the QDial as Clock interface

    :param clock_type: type of clock <ClockType>
    :param size: size of clock
    """

    clockValueChanged = pyqtSignal(int)

    class ClockType(Enum):
        """
        Supported clock types
        """

        Hour12 = auto()
        Hour24 = auto()
        Minute = auto()
        Second = auto()

    def __init__(
        self,
        clock_type: ClockType,
        *args,
        size: int | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.clock_type = clock_type
        self.size = size

        if self.clock_type == ClockDial.ClockType.Hour12:
            self.max_value = 12
            self.division = 1
        elif self.clock_type == ClockDial.ClockType.Hour24:
            self.max_value = 24
            self.division = 2
        elif self.clock_type == ClockDial.ClockType.Minute or self.clock_type == ClockDial.ClockType.Second:
            self.max_value = 60
            self.division = 5
        else:
            raise NotImplementedError(f'ClockDial of type {self.clock_type} is not implemented.')

        self.setRange(0, self.max_value)
        self.setNotchesVisible(False)
        self.setWrapping(True)

        if self.size is None:
            self.size = 100
        self.setMinimumSize(self.size, self.size)
        self.setPageStep(1)
        self.setValue(0)

        self.valueChanged.connect(lambda: self.clockValueChanged.emit(self.value()))

    def setValue(self, value: int):
        """Sets the value"""
        super().setValue(int(value + self.max_value / 2) % self.max_value)

    def value(self):
        """Gets the value"""
        return int(super().value() + self.max_value / 2) % self.max_value

    def paintEvent(self, event):
        """Custom paint event to draw the labels around the QDial"""

        painter_notches = QPainter(self)

        rect = self.rect()
        # somehow the center is not really the center of the QDial for whyever this might be
        center_x, center_y = rect.center().x() + 2, rect.center().y() + 2
        size = min(rect.width(), rect.height())
        radius = size / 2

        # draw notches
        for i in range(0, self.max_value):
            angle = (i / self.max_value) * 2 * np.pi

            if i % self.division == 0:
                notch_end_radius = radius
                pen = QPen(Qt.GlobalColor.black, 1.5)
            else:
                notch_end_radius = radius * 0.9
                pen = QPen(Qt.GlobalColor.darkGray, 1)

            painter_notches.setPen(pen)

            notch_end_x = int(center_x + (notch_end_radius * np.cos(angle)))
            notch_end_y = int(center_y + (notch_end_radius * np.sin(angle)))

            painter_notches.drawLine(center_x, center_y, notch_end_x, notch_end_y)

        # draw dial
        super().paintEvent(event)

        painter_label = QPainter(self)

        font = QFont()
        font_size = size // 12
        font.setPointSize(font_size)
        painter_label.setFont(font)

        radius_label = radius - font_size * 1.75

        # draw text
        divisions = self.max_value // self.division
        for i in range(0, divisions):
            angle = (i / divisions) * 2 * np.pi

            label_x = center_x - radius_label * 0.8 * np.sin(angle)
            label_y = center_y - radius_label * 0.8 * np.cos(angle)

            text_rect = QRectF(QPointF(label_x - font_size, label_y - font_size),
                               QPointF(label_x + font_size, label_y + font_size))
            painter_label.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(self.max_value - i * self.division))


class Clock(QWidget):
    """
    Clock widget to select a time

    :param am_pm: select between am and pm OR have a 24 hour clock
    :param seconds_flag: show seconds
    :clock_size: size of ClockDial Widget
    :timestamp: time to be displayed
    """

    def __init__(
        self,
        *args,
        am_pm: bool = False,
        seconds_flag: bool = True,
        clock_size: int | None = None,
        timestamp: datetime | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.am_pm = am_pm
        self.seconds_flag = seconds_flag
        self.clock_size = clock_size

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        if self.am_pm:
            self.hour_dial = ClockDial(ClockDial.ClockType.Hour12)
            self.hour_spinbox = SpinBox(input_range=(0, 11), buttons=True)

            self.am_pm_vbox = QVBoxLayout()
            self.am_pm_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.am_button = QPushButton('AM')
            self.am_button.setToolTip('Swith to AM')
            self.am_button.setCheckable(True)
            self.am_button.setChecked(True)
            self.am_button.clicked.connect(lambda: self._amClicked(True))
            self.am_pm_vbox.addWidget(self.am_button)
            self.pm_button = QPushButton('PM')
            self.pm_button.setToolTip('Swith to PM')
            self.pm_button.setCheckable(True)
            self.pm_button.setChecked(False)
            self.pm_button.clicked.connect(lambda: self._amClicked(False))
            self.am_pm_vbox.addWidget(self.pm_button)
            self.main_layout.addLayout(self.am_pm_vbox)
        else:
            self.hour_dial = ClockDial(ClockDial.ClockType.Hour24)
            self.hour_spinbox = SpinBox(input_range=(0, 23), buttons=True)
        self.hour_dial.setToolTip('Select hour')
        self.hour_spinbox.setToolTip('Select hour')
        self.hour_dial.clockValueChanged.connect(self.hour_spinbox.setValue)
        self.hour_spinbox.valueChanged.connect(self.hour_dial.setValue)
        self.hour_vbox = QVBoxLayout()
        self.hour_vbox.addWidget(self.hour_dial)
        self.hour_hbox = QHBoxLayout()
        self.hour_vbox.addLayout(self.hour_hbox)
        self.hour_hbox.addWidget(QLabel('Hour:'))
        self.hour_hbox.addWidget(self.hour_spinbox)
        self.main_layout.addLayout(self.hour_vbox)

        self.minute_dial = ClockDial(ClockDial.ClockType.Minute)
        self.minute_spinbox = SpinBox(input_range=(0, 59), buttons=True)
        self.minute_dial.setToolTip('Select minute')
        self.minute_spinbox.setToolTip('Select minute')
        self.minute_dial.clockValueChanged.connect(self.minute_spinbox.setValue)
        self.minute_spinbox.valueChanged.connect(self.minute_dial.setValue)
        self.minute_vbox = QVBoxLayout()
        self.minute_vbox.addWidget(self.minute_dial)
        self.minute_hbox = QHBoxLayout()
        self.minute_vbox.addLayout(self.minute_hbox)
        self.minute_hbox.addWidget(QLabel('Minute:'))
        self.minute_hbox.addWidget(self.minute_spinbox)
        self.main_layout.addLayout(self.minute_vbox)

        if self.seconds_flag:
            self.second_dial = ClockDial(ClockDial.ClockType.Second)
            self.second_spinbox = SpinBox(input_range=(0, 59), buttons=True)
            self.second_dial.setToolTip('Select second')
            self.second_spinbox.setToolTip('Select second')
            self.second_dial.clockValueChanged.connect(self.second_spinbox.setValue)
            self.second_spinbox.valueChanged.connect(self.second_dial.setValue)
            self.second_vbox = QVBoxLayout()
            self.second_vbox.addWidget(self.second_dial)
            self.second_hbox = QHBoxLayout()
            self.second_vbox.addLayout(self.second_hbox)
            self.second_hbox.addWidget(QLabel('Second:'))
            self.second_hbox.addWidget(self.second_spinbox)
            self.main_layout.addLayout(self.second_vbox)

        if timestamp is None:
            timestamp = datetime.now()
        self.setTime(timestamp)

    def _amClicked(self, state):
        """AM button is clicked"""

        self.am_button.setChecked(state)
        self.pm_button.setChecked(not state)

    def setTime(self, timestamp: datetime):
        """
        Set the time to given datetime

        :param timestamp: datetime object
        """

        if self.am_pm:
            self._amClicked(timestamp.hour < 12)

        self.hour_dial.setValue(timestamp.hour)
        self.minute_dial.setValue(timestamp.minute)

        if self.seconds_flag:
            self.second_dial.setValue(timestamp.second)

    def getTime(self) -> datetime:
        """
        Get the time of clock widget

        :returns: datetime object
        """

        hour = self.hour_dial.value()
        if self.am_pm and self.pm_button.isChecked():
            hour += 12

        second = 0
        if self.seconds_flag:
            second = self.second_dial.value()

        return datetime(2000, 1, 1, hour, self.minute_dial.value(), second)


class DateTimeWidget(QWidget):
    """
    Date time widget

    :param am_pm: select between am and pm OR have a 24 hour clock
    :param seconds_flag: show seconds
    :clock_size: size of ClockDial Widget
    :timestamp: time to be displayed
    """

    def __init__(
        self,
        *args,
        am_pm: bool = False,
        seconds_flag: bool = True,
        clock_size: int | None = None,
        timestamp: datetime | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.calendar_widget = QCalendarWidget()
        self.main_layout.addWidget(QLabel('Pick date:'), alignment=Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addWidget(self.calendar_widget)

        self.clock_widget = Clock(am_pm=am_pm, seconds_flag=seconds_flag, clock_size=clock_size)
        self.main_layout.addWidget(QLabel('Pick time:'), alignment=Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addWidget(self.clock_widget)

        self.selection_hbox = QHBoxLayout()
        self.main_layout.addLayout(self.selection_hbox)

        self.now_button = QPushButton('Set date-time to now')
        self.now_button.setToolTip('Update the date-time to current date-time')
        self.now_button.clicked.connect(self.setNow)
        self.selection_hbox.addWidget(self.now_button)

        if timestamp is None:
            timestamp = datetime.now()
        self.setTime(timestamp)

    def setNow(self):
        """Set the time to now"""
        self.setTime(datetime.now())

    def setTime(self, timestamp: datetime):
        """
        Set the time to given datetime

        :param timestamp: datetime object
        """

        self.calendar_widget.setSelectedDate(timestamp)
        self.clock_widget.setTime(timestamp)

    def getTime(self) -> datetime:
        """
        Get the time of clock widget

        :returns: datetime object
        """

        calendar = self.calendar_widget.selectedDate()
        clock = self.clock_widget.getTime()

        return datetime(
            year=calendar.year(),
            month=calendar.month(),
            day=calendar.day(),
            hour=clock.hour,
            minute=clock.minute,
            second=clock.second
        )


class DateTimeDialog(QDialog):
    """
    Dialog to select date and time

    :param title: title of widget
    :param am_pm: select between am and pm OR have a 24 hour clock
    :param seconds_flag: show seconds
    :clock_size: size of ClockDial Widget
    :timestamp: time to be displayed
    """

    def __init__(
        self,
        *args,
        title: str,
        am_pm: bool = False,
        seconds_flag: bool = True,
        clock_size: int | None = None,
        timestamp: datetime | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if timestamp is None:
            timestamp = datetime.now()
        self.timestamp = timestamp

        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.Dialog)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.date_time_widget = DateTimeWidget(am_pm=am_pm, seconds_flag=seconds_flag, clock_size=clock_size,
                                               timestamp=timestamp)
        self.main_layout.addWidget(self.date_time_widget)

        self.button_hbox = QHBoxLayout()
        self.main_layout.addLayout(self.button_hbox)

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setToolTip('Cancel date-time selection')
        self.cancel_button.clicked.connect(self.accept)
        self.button_hbox.addWidget(self.cancel_button)
        self.ok_button = QPushButton('OK')
        self.ok_button.setToolTip('Apply changes')
        self.ok_button.clicked.connect(self._okButton)
        self.button_hbox.addWidget(self.ok_button)

        self.exec()

    def _okButton(self):
        self.timestamp = self.date_time_widget.getTime()
        self.accept()


class DateTimeEdit(QWidget):
    """
    Select date time, like in QDateTimeEdit, but with time also selectable easily

    :param popup_title: title displayed on popup
    :param am_pm: select between am and pm OR have a 24 hour clock
    :param seconds_flag: show seconds
    :clock_size: size of ClockDial Widget
    :timestamp: time to be displayed
    :now_button: show now button
    """

    def __init__(
        self,
        *args,
        popup_title: str = 'Select date and time',
        am_pm: bool = False,
        seconds_flag: bool = True,
        clock_size: int | None = None,
        timestamp: datetime | None = None,
        now_button: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.popup_title = popup_title
        self.am_pm = am_pm
        self.seconds_flag = seconds_flag
        self.clock_size = clock_size
        if timestamp is None:
            timestamp = datetime.now()
        self.now_button = now_button

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        self.date_time_edit = QDateTimeEdit()
        self.display_format = 'dd.MM.yyyy HH:mm'
        if self.seconds_flag:
            self.display_format += ':ss'
        self.date_time_edit.setDisplayFormat(self.display_format)
        self.date_time_edit.setDateTime(timestamp)
        self.main_layout.addWidget(self.date_time_edit, stretch=1)

        self.calendar_button = QPushButton()
        self.calendar_button.setIcon(QIcon('icons/calendar.png'))
        self.calendar_button.setToolTip('Select Date and Time')
        self.calendar_button.clicked.connect(self._selectionPopup)
        self.main_layout.addWidget(self.calendar_button, stretch=0)

        if self.now_button:
            self.now_button = QPushButton('now')
            self.now_button.setToolTip('Select Date and Time as now')
            self.now_button.clicked.connect(lambda: self.setTime(datetime.now()))
            self.main_layout.addWidget(self.now_button, stretch=0)

    def _selectionPopup(self):
        """Open an easier selection popup"""
        self.date_time_selection = DateTimeDialog(
            title=self.popup_title,
            am_pm=self.am_pm,
            seconds_flag=self.seconds_flag,
            clock_size=self.clock_size,
            timestamp=self.date_time_edit.dateTime().toPyDateTime()
        )
        self.date_time_edit.setDateTime(self.date_time_selection.timestamp)

    def setTime(self, timestamp: datetime):
        """
        Set the datetime of the widget

        :param timestamp: datetime object
        """

        self.date_time_edit.setDateTime(timestamp)

    def getTime(self) -> datetime:
        """
        Get the datetime of the widget

        :returns: datetime object
        """
        return self.date_time_edit.dateTime().toPyDateTime()


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
        on_color: str = Colors.color_green,
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

    :param input_range: input range as tuple of (maximum, minimum)
    """

    def __init__(
        self,
        input_range: tuple[float, float] = (1E3, 5E-10),
        **kwargs
    ):
        super().__init__(**kwargs)

        self.input_range = input_range
        self.input_range_exponents = [int(log10(ir)) for ir in input_range]

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.main_layout)

        self.stack_widget = StackWidget(
            color_top=Colors.color_green,
            color_bottom=Colors.color_red,
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
        stack_widget_value = -self.input_range_exponents[0] - 1

        self.stack_widget.enableDigit(bool(pressure))
        if pressure:
            pressure_string_split = f'{self.pressure:E}'.split('E')
            exponent = int(pressure_string_split[1])
            label_text = f'{pressure_string_split[0]} x 10<sup>{exponent}</sup> mbar'

            percentage = 1 - (log10(pressure) - self.input_range_exponents[0]) / (self.input_range_exponents[1] - self.input_range_exponents[0])
            percentage = max(percentage, 0)
            percentage = min(percentage, 1)

            stack_widget_value = -exponent
            if pressure >= self.input_range[0]:
                stack_widget_value = 'OR'
            elif pressure <= self.input_range[1]:
                stack_widget_value = 'UR'

        self.pressure_label.setText(label_text)
        self.stack_widget.changePercentage(percentage)
        self.stack_widget.setValue(stack_widget_value)


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
        color_top: QColor | Qt.GlobalColor | str = Colors.color_green,
        color_bottom: QColor | Qt.GlobalColor | str = Colors.color_red,
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
    :param deviation_percent: deviation in percentage
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
        deviation_percent: bool = False,
        unit: str = '',
        decimals: int = 2,
        enable_prefix: bool = False,
        alignment_flag: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight,
        antialiased: bool = True,
        color_good: QColor | Qt.GlobalColor | str = Colors.color_green,
        color_bad: QColor | Qt.GlobalColor | str = Colors.color_red,
        color_grayed: QColor | Qt.GlobalColor | str = Colors.app_background_event,
        tooltip: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.value = value
        self.target_value = target_value
        self.target_value_sign = target_value_sign
        self.deviation = deviation
        self.deviation_percent = deviation_percent
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

    def setUnit(self, unit: str, enable_prefix: bool | None = None):
        """
        Set a new deviation

        :param unit: unit to be displayed
        :param enable_prefix: enable prefixing
        """

        self.unit = unit
        if isinstance(enable_prefix, bool):
            self.enable_prefix = enable_prefix
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
            deviation = self.deviation
            if self.deviation_percent:
                deviation = deviation * abs(self.value)
            if deviation != 0:
                percentage = min(abs(difference) / deviation, 1)
            new_color = linearInterpolateColor(self.color_good, self.color_bad, percentage)
            new_color.setAlpha(90)
            brush.setColor(new_color)
        painter.setBrush(brush)

        painter.drawRect(QRectF(0, 0, self.width(), self.height()))

        super().paintEvent(event)


class LatexLabel(QSvgWidget):
    """
    Class for displaying latex inside Label widget

    :param text: text to display
    :param font_size: font size to display
    """

    def __init__(self, text: str = '', font_size: float | None = None, font_color: str = 'black'):
        super().__init__()

        self.text = text
        if font_size is None:
            font_size = QFont().pointSizeF()
        self.font_size = font_size
        self.font_color = font_color

        self._writeText()

    def setText(self, text: str):
        """Sets text"""
        self.text = text
        self._writeText()

    def setFontSize(self, font_size: float):
        """Sets font size"""
        self.font_size = font_size
        self._writeText()

    def setFontColor(self, font_color: float):
        """Sets font color"""
        self.font_color = font_color
        self._writeText()

    def _writeText(self):
        """Writes text as latex"""

        # Get height of widget
        font = QFont()
        font.setPointSizeF(self.font_size)
        self.setMinimumHeight(QFontMetrics(font).height())

        # Save the figure to a BytesIO object in SVG format
        buf = BytesIO()

        # Create matplotlib text with given text and fontsize
        with matplotlibLogLevel(logging.WARNING):
            fig, ax = plt.subplots(figsize=(4, 1))
            ax.text(0.5, 0.5, self.text, fontsize=self.font_size, color=self.font_color, ha='center', va='center')
            ax.axis('off')

            plt.tight_layout()
            plt.savefig(buf, format='svg', bbox_inches='tight', transparent=True)
            plt.close(fig)
        buf.seek(0)

        # Read the SVG data from the buffer into the widget
        self.load(buf.read())
        buf.close()


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
        color_positive: QColor | Qt.GlobalColor | str = Colors.color_green,
        color_negative: QColor | Qt.GlobalColor | str = Colors.color_red,
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
        char_width = QFontMetrics(QFont()).boundingRect('0').width()
        self.setColumnWidth(0, char_width * 3)
        self.setColumnWidth(1, char_width * 7)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
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

        error_code_widget = QTableWidgetItem(str(error_code))
        error_code_widget.setToolTip(f'Error #: {error_code}')
        self.setItem(self.actual_row, 0, error_code_widget)

        error_type_widget = QTableWidgetItem(error_type)
        error_type_widget.setToolTip(f'Error type: {error_type}')
        self.setItem(self.actual_row, 1, error_type_widget)

        error_description_widget = QTableWidgetItem(error_description)
        error_description_widget.setToolTip(f'Error description: {error_description}')
        self.setItem(self.actual_row, 2, error_description_widget)

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

    :param placeholder: placeholder text when nothing is displayed
    """

    checkedChanged = pyqtSignal()
    itemDeleted = pyqtSignal()

    def __init__(
        self,
        *args,
        placeholder: str = 'Noting selected',
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSpacing(0)

        self.info_text = placeholder
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

        self.itemDeleted.emit()

    def clearAll(self):
        """Clears all items in this list"""

        self.clear()
        self.addInfoItem()
        self.itemDeleted.emit()

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

    :param path_str: title of Widget
    :param data: dict to store data
    :param default_background_color: background color
    :param checkbox_visible: make checkbox visible
    """

    deleted = pyqtSignal()
    checkedChanged = pyqtSignal()

    def __init__(
        self,
        path_str: str,
        *args,
        data: dict = None,
        default_background_color: str = '#ffffff',
        checkbox_visible: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.path = path_str
        if data is None:
            data = dict()
        self.data = data
        self.checkbox_time = 0
        self.default_background_color = default_background_color

        self.setToolTip(self.path)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.delete_button = QPushButton(self)
        self.delete_button.setIcon(QIcon('icons/delete.png'))
        self.delete_button.setIconSize(QSize(10, 10))
        self.delete_button.setContentsMargins(0, 0, 0, 0)
        self.delete_button.clicked.connect(lambda: self.deleted.emit())
        self.main_layout.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.checkbox = QCheckBox()
        self.setBackgroundColor(self.default_background_color)
        self.main_layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignLeft)
        self.checkbox.stateChanged.connect(self.checkboxClicked)
        self.checkbox.setVisible(checkbox_visible)

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
        for (row, col), label in labels.items():
            item = {label: col}
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

            for label, pos in sorted(row.items(), key=lambda v: v[1]):
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

    buttonPressedIdx = pyqtSignal(int)
    buttonPressedName = pyqtSignal(str)

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
            button.clicked.connect(lambda _, i=index: self.buttonPressedIdx.emit(i))
            button.clicked.connect(lambda _, i=label: self.buttonPressedName.emit(i))
            self.addWidget(button, row, column)

    def newLabels(self, labels: list[str]):
        """Resets the buttons and initializes them with the provided new labels"""

        self.labels = labels
        self.clearGrid()
        self.fillGrid()


class FilesList(QListWidget):
    """
    List of files in a given folder, files can be renamed and deleted

    :param folder: folder for displaying files
    :param extensions: file extension or list of file extensions
    """

    def __init__(self, folder: str, extensions: str | list[str] ):
        super().__init__()

        if not path.isdir(folder):
            raise OSError(f'Provided folder "{folder}" is not a folder')

        self.folder = folder
        if not isinstance(extensions, list):
            extensions = [extensions]
        self.extensions = extensions
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        self.currentRowChanged.connect(self._setSelectedFile)

        self.selected_file = None
        self.listFiles()

    def _setSelectedFile(self, row_idx: int):
        """Set selected file based on row index"""
        if row_idx < 0 or row_idx >= self.count():
            return
        self.selected_file = self.item(row_idx).text()

    def listFiles(self):
        """Reload view and list all files"""

        self.clear()
        one_selected = False

        for file in listdir(self.folder):
            if not file.split('.')[-1] in self.extensions:
                continue

            item = QListWidgetItem()

            layout = QHBoxLayout()
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            widget = QWidget()
            widget.setLayout(layout)

            item.setData(100, file)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            button_delete = QPushButton()
            button_delete.setToolTip('Delete Script')
            button_delete.setIcon(QIcon('icons/delete.png'))
            button_delete.setIconSize(QSize(10, 10))
            button_delete.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(button_delete, alignment=Qt.AlignmentFlag.AlignLeft)
            button_delete.clicked.connect(lambda _, i=item: self._deleteFile(i))

            button_rename = QPushButton()
            button_rename.setToolTip('Rename Script')
            button_rename.setIcon(QIcon('icons/rename.png'))
            button_rename.setIconSize(QSize(10, 10))
            button_rename.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(button_rename, alignment=Qt.AlignmentFlag.AlignLeft)
            button_rename.clicked.connect(lambda _, i=item: self._renameFile(i))

            layout.addWidget(QLabel(file))

            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)

            self.addItem(item)
            self.setItemWidget(item, widget)

            if file == self.selected_file:
                one_selected = True
                self.setCurrentItem(item)

        if not one_selected:
            if self.count():
                self.selected_file = self.item(0).text()
                self.setCurrentRow(0)
            else:
                self.selected_file = None

    def _renameFile(self, item: QListWidgetItem):
        """
        Prompt user for new file name and rename the file.

        :param item: item of file to be modified
        """

        self.setCurrentItem(item)
        old_name = item.data(100)
        new_name, ok = QInputDialog.getText(self, f'Rename Script "{old_name}"', 'New name:', text=old_name)
        if ok and new_name:
            old_path = path.join(self.folder, old_name)

            if not new_name.split('.')[-1] in self.extensions:
                new_name += f'.{self.extensions[0]}'

            new_path = path.join(self.folder, new_name)

            if path.exists(new_path):
                QMessageBox.warning(self, 'Error', 'File with this name already exists!')
                return

            os_rename(old_path, new_path)
            self.selected_file = new_name
            self.listFiles()

    def _deleteFile(self, item: QListWidgetItem):
        """
        Delete the selected file

        :param item: item of file to be deleted
        """
        self.setCurrentItem(item)
        name = item.data(100)
        confirm = QMessageBox.question(self, 'Confirm Delete', f'Delete "{name}"?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            os_remove(path.join(self.folder, name))
            self.listFiles()


class TextEdit(QWidget):
    """
    Text editor, which is a QTextEdit with a menu bar

    :param menu: display menu
    :parm image_directors: directory of images
    :param save_button: if save button should be displayed
    :param load_button: if load button should be displayed
    :param file_extensions: list of possible file extensions
    :param encoding: encoding of file
    :param html_save: read and write as html files
    """

    def __init__(
        self,
        menu: bool = True,
        image_directory: str = None,
        save_button: bool = True,
        load_button: bool = True,
        file_extensions: list[str] | None = None,
        encoding: str = 'utf-8',
        html_save: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.image_directory = image_directory
        if file_extensions is None or not file_extensions:
            self.file_filter = 'All Files (*)'
        else:
            self.file_filter = 'Text Files (' + ', '.join([f'.{file_extension}' for file_extension in file_extensions]) + ')'
        self.encoding = encoding
        self.html_save = html_save

        # add menu bar
        if menu:
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

    def saveFile(self, file_name: str = '') -> int:
        """
        Save the file

        :parm file_name: if provided, this will be used for saving, otherwise file dialog will appear
        """

        if not file_name:
            file_name = selectFileDialog(self, True, 'Save File', '', self.file_filter)

        if not file_name:
            return 1

        try:
            with open(file_name, 'w', encoding=self.encoding, errors='ignore') as file:
                if self.html_save:
                    file.write(self.text_editor.toHtml())
                else:
                    file.write(self.text_editor.toPlainText())
        except (OSError, FileNotFoundError, FileExistsError) as e:
            QMessageBox.warning(self, 'Error', f'Failed to save file: {e}')
            return 2

        return 0

    def openFile(self, file_name: str = '') -> int:
        """
        Opens a file

        :parm file_name: if provided, this will be used for opening, otherwise file dialog will appear
        """

        if not file_name:
            file_name = selectFileDialog(self, False, 'Open File', '', self.file_filter)

        if not file_name:
            return 1

        try:
            with open(file_name, 'r', encoding=self.encoding, errors='ignore') as file:
                if self.html_save:
                    self.text_editor.setHtml(file.read())
                else:
                    self.text_editor.setText(file.read())
        except (OSError, FileNotFoundError, FileExistsError) as e:
            QMessageBox.warning(self, 'Error', f'Failed to open file: {e}')
            return 2

        return 0

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


class LineNumberArea(QWidget):
    """
    Line number area of FileEditor

    :param editor: FileEditor
    """

    def __init__(self, editor: FileEditor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        """Returns size of line number area"""
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        """Called when a paint event happens"""
        self.editor.lineNumberAreaPaintEvent(event)


class FileEditor(QPlainTextEdit):
    """
    QPlainTextEdit with line numbers and marks current line when clicked

    :param parent: parent widget
    :param line_numbering: (optional) if textbox should have line numbering
    :param readonly: (optional) if textbox should be readonly
    :param mono: (optional) if textbox should have mono font
    :param offset: (optional) offset for line numbers
    :param highlighting: (optional) enables highlighting of current selected line
    :param color_line_number: (optional) color of line number area
    :param color_highlight: (optional) color of highlighting line
    """

    def __init__(
        self,
        parent = None,
        line_numbering: bool = True,
        readonly: bool = True,
        mono: bool = True,
        offset: int = 0,
        highlighting: bool = True,
        color_line_number: str | None = None,
        color_highlight: str | None = None,
    ):
        super().__init__(parent)
        self.line_numbering = line_numbering
        self.offset = offset

        palette = self.palette()

        self.pen_color = palette.color(QPalette.ColorRole.Text)

        if color_highlight is None:
            self.color_highlight = palette.color(QPalette.ColorRole.Highlight)
            hsv = self.color_highlight.getHsv()
            self.color_highlight.setHsv(
                (hsv[0] + 128) % 256,
                hsv[1],
                hsv[2],
                hsv[3],
            )
        else:
            self.color_highlight = QColor(color_highlight)

        if color_line_number is None:
            self.color_line_number = palette.color(QPalette.ColorRole.Light)
        else:
            self.color_line_number = QColor(color_line_number)

        self.line_number_area = LineNumberArea(self)

        self.updateLineNumberAreaWidth()

        self.blockCountChanged.connect(lambda _: self.updateLineNumberAreaWidth())
        self.updateRequest.connect(self.updateLineNumberArea)
        if highlighting:
            self.cursorPositionChanged.connect(self.highlightCurrentLine)

        if readonly:
            self.setReadOnly(True)

        if mono:
            mono_font = QFont('Courier New')
            mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
            self.setFont(mono_font)

    def updateOffset(self, offset: int):
        """Updates the offset of the line numbers"""
        self.offset = offset

    def lineNumberAreaWidth(self):
        """Returns the width of the line number area"""
        digits = len(str(self.blockCount() + self.offset))
        space = 5 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self):
        """Updates width of line number area"""
        if not self.line_numbering:
            return

        self.setViewportMargins(self.lineNumberAreaWidth() + 5, 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        """Updates line number area"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth()

    def resizeEvent(self, event):
        """On resize"""
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        """Called when a paint event happens"""
        if not self.line_numbering:
            return

        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), self.color_line_number)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # make sure to use the right font
        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                painter.setPen(self.pen_color)
                painter.drawText(
                    0,
                    int(top),
                    int(self.line_number_area.width()),
                    int(height),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1 + self.offset)
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlightCurrentLine(self):
        """Highlight current line"""
        selections = []

        text_cursor = self.textCursor()
        block = text_cursor.block()
        cursor_position = block.position()
        while True:
            new_text_cursor = QTextCursor(text_cursor)
            new_text_cursor.setPosition(cursor_position)
            cursor_position += 1
            if new_text_cursor.atBlockEnd():
                break

            selection = QTextEdit.ExtraSelection()
            selection.cursor = new_text_cursor
            selections.append(selection)

        for selection in selections:
            selection.format.setBackground(self.color_highlight)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)

        self.setExtraSelections(selections)


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


class Canvas(pg.PlotWidget):
    """
    Extends the PlotWidget of pyqtgraph

    :param data: data of plot
    :param grid: show grid
    :param legend: show legend
    """

    def __init__(
        self,
        data: list[tuple[np.ndarray, np.ndarray]],
        grid: bool = False,
        legend: bool | tuple[int, int] = True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.data = data
        self.grid = grid

        self.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.setMouseEnabled(x=True, y=False)

        self.graph_curves: list[pg.PlotDataItem] = []
        self.graph_colors = CyclicList(Colors.colors)

        if self.grid:
            '''
            GRID CAUSES DISPLACEMENT OF SELECTED ZOOM AREA AND IS A KNOWN BUG BY THE DEVELOPERS:
            https://github.com/pyqtgraph/pyqtgraph/pull/2034
            (Solution: https://github.com/pyqtgraph/pyqtgraph/pull/2034/commits/530a5913c414bb0217188b7828a768c68e47865f)
            -> 'pyqtgraph/graphicsItems/ViewBox/ViewBox.py' HAS TO BE UPDATED TO GET RIGHT RESULTS
            '''
            self.showGrid(y=True, x=True)

        if legend is True:
            legend = (-10, 10)
        if legend is not False:
            self.addLegend(offset=legend)

    def plot(self, x: np.ndarray, y: np.ndarray, label: str | None = None, plot_params: dict | None = None):
        """
        Plots data (x, y) with given label

        :param x: numpy array of x values
        :param y: numpy array of y values
        :param label: label of data
        :param plot_params: additional plot parameters
        """

        if plot_params is None:
            plot_params = dict()
        plot_params.update({
            'pen': pg.mkPen(color=self.graph_colors[len(self.data)], width=1)
        })
        if label is not None:
            plot_params.update({
                'name': label
            })
        self.data.append((x, y))
        self.graph_curves.append(self.plotItem.plot(x, y, **plot_params))

    def clean(self):
        """Clears whole plot"""

        self.data = []
        for graph_curve in self.graph_curves:
            graph_curve.clear()
            self.plotItem.removeItem(graph_curve)
        self.graph_curves = []

    def setLogX(self, state: bool):
        """
        Sets the x-axis to logarithmic or normal

        :param state: True: logarithmic; False: normal
        """

        view_range: list[list[float, float]] = self.getViewBox().viewRange()
        self.plotItem.setLogMode(x=state)
        self.setYRange(view_range[1][0], view_range[1][1], padding=0)

    def setLogY(self, state: bool):
        """
        Sets the y-axis to logarithmic or normal

        :param state: True: logarithmic; False: normal
        """

        view_range: list[list[float, float]] = self.getViewBox().viewRange()
        self.plotItem.setLogMode(y=state)
        self.setXRange(view_range[0][0], view_range[0][1], padding=0)


class TOFCanvas(Canvas):
    """
    Extends the PlotWidget of pyqtgraph for a TOF display

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
        super().__init__(data, *args, **kwargs)

        self.setLabel('left', 'Counts')
        self.setLabel('bottom', 'TOF [ns]')

        self.fit_class = fit_class

        self.sigRangeChanged.connect(self.updateLimits)

        self.graph_curve_fit: pg.PlotDataItem = self.plotItem.plot(pen=pg.mkPen(color=Colors.color_orange, width=2))
        self.setLimits(yMin=0, xMin=0)

        self.bars: list[pg.InfiniteLine] = []

    def updateFitClass(self, fit_class: FitMethod):
        """Updates the fitting method"""
        self.fit_class = fit_class
        self.setBars(self.fit_class.bars)

    def plotTOF(self, data: list[tuple[np.ndarray, np.ndarray]], view_all: bool = False, fill_histogram: bool = True):
        """
        Plots data if available

        :param data: data as tuple of x and y data in np.array form
        :param view_all: force all x axes to be shown
        :param fill_histogram: fills the histogram
        """

        view_range: list[list[float, float]] = self.getViewBox().viewRange()
        self.clean()
        self.data = data

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
            graph_curve = self.plotItem.plot(pen=pg.mkPen(color=self.graph_colors[i], width=1))
            graph_curve.setData(**data_dict)
            self.graph_curves.append(graph_curve)
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


class TimeCanvas(Canvas):
    """
    Extends the PlotWidget of pyqtgraph for a Time display

    :param data: data of plot
    :param time_fmt: format of time axis
    """

    def __init__(
        self,
        data: list[tuple[np.ndarray, np.ndarray]],
        *args,
        time_fmt: str = '%Y-%m-%d\n%H:%M:%S',
        **kwargs
    ):
        self.time_fmt = time_fmt
        self.time_axis = TimeAxisItem(fmt=self.time_fmt, orientation='bottom')

        super().__init__(data=data, *args, axisItems={'bottom': self.time_axis}, **kwargs)


class TimeAxisItem(pg.AxisItem):
    """
    Extension of the AxisItem for the PlotWidget of pyqtgraph to display values as time

    :param fmt: format string
    """

    def __init__(
        self,
        *args,
        fmt: str = '%H:%M:%S',
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.fmt = fmt
        self.setHeight(self.height() * (self.fmt.count('\n') + 1))

    def tickStrings(self, values, scale, spacing):
        """Convert UNIX timestamps into given format"""
        ticks = []

        for value in values:
            try:
                ticks.append(datetime.fromtimestamp(value).strftime(self.fmt))
            except (OverflowError, ValueError, OSError):
                ticks.append('infinity')

        return ticks


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
            'labelOpts': {'color': Colors.color_green, 'position': label_position},
            'pen': pg.mkPen(color=Colors.color_green, width=2),
            'hoverPen': pg.mkPen(color=Colors.color_red, width=3),
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
