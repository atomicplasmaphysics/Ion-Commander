from __future__ import annotations
from typing import TYPE_CHECKING
from math import log10


import numpy as np

from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QSize, QRect, QRectF
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor, QBrush, QLinearGradient, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QApplication, QStyleOption, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QGridLayout, QLCDNumber
)
from PyQt6.QtSvg import QSvgRenderer

import pyqtgraph as pg


from Config.StylesConf import Colors, Styles, Forms

from Utility.ModifyWidget import setWidgetBackground
from Utility.Functions import hexToRgb
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
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight,
        color: Qt.GlobalColor | QColor = Qt.GlobalColor.black,
        font_size: int = 20
    ):
        super().__init__(image)

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

    def __init__(self, parent: MainWindow):
        super().__init__(parent)
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

    :param parent: parent widget
    :param title: title of top line
    :param title_style: style of title line
    :param title_style_busy: style of title line in busy mode
    :param busy_symbol: symbol when busy
    :param spacing: spacing of widgets
    :param add_stretch: if bool: addStretch(1) after title if True, else do nothing
                        if integer: addSpacing(addStretch) after title
    """

    def __init__(self, parent, title: str, title_style: str = Styles.title_style_sheet,
                 title_style_busy: str = Styles.title_style_sheet, busy_symbol: str = '⧖',
                 spacing: int = 0, add_stretch: bool | int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def addWidgets(self, *widgets: QWidget | None):
        row = self.rowCount()

        for col, widget in enumerate(widgets):
            if widget is not None:
                super().addWidget(widget, row, col)


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

    def __init__(self, label: str, widget: QWidget | None, tooltip: str = None, split: int = 50,
                 disabled: bool = False, hidden: bool = False,
                 checkbox: bool = None, checkbox_connected: bool = True, **kwargs):
        super().__init__(**kwargs)

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

    def __init__(self, default: float | int = 0, step_size: int = None, input_range: tuple[float, float] = None,
                 scroll: bool = False, buttons: bool = False, **kwargs):
        super().__init__(**kwargs)

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

    def __init__(self, default: float = 0, step_size: float = None, input_range: tuple[float, float] = None,
                 scroll: bool = False, decimals: int = None, buttons: bool = False, readonly: bool = False,
                 click_copy: bool = False, **kwargs):
        super().__init__(**kwargs)

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

    def __init__(self, default: str = '', placeholder: str = None, max_length: int = None, readonly: bool = False,
                 click_copy: bool = False, **kwargs):
        super().__init__(**kwargs)

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
    """

    def __init__(self, default: int = 0, entries: list[str] = None, tooltips: list[str] = None,
                 entries_save: list = None, numbering: int = None, label_default: bool = False,
                 disabled_list: list[int] = None, scroll: bool = False, **kwargs):
        super().__init__(**kwargs)

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
            return self.entries[current_index]
        if save and self.entries_save is not None:
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
    :param parent: parent widget
    :param state: initial state of indicator
    :param clickable: if indicator can be toggled via click
    :param on_color: color if indicator is on
    :param off_color: color if indicator is off
    :param size: wanted QSize
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        parent=None,
        state: bool = False,
        clickable: bool = False,
        on_color: str = Colors.cooperate_lime,
        off_color: str = Colors.app_background,
        size: QSize | None = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

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

    def setValue(self, state):
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


class PressureWidget(QWidget):
    """
    Widget that extends the QWidget to display the pressure

    :param input_range: input range as tuple of (maximum exponent, minimum exponent)
    """

    def __init__(self, input_range: tuple[float, float] = (-2, -10)):
        super().__init__()

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

        if pressure:
            pressure_string_split = f'{self.pressure:E}'.split('E')
            exponent = int(pressure_string_split[1])
            label_text = f'{pressure_string_split[0]} x 10<sup>{exponent}</sup> mbar'

            percentage = 1 - (log10(pressure) - self.input_range[0]) / (self.input_range[1] - self.input_range[0])
            percentage = max(percentage, 0)
            percentage = min(percentage, 1)

        self.pressure_label.setText(label_text)
        self.stack_widget.changePercentage(percentage)

        if exponent > self.input_range[0]:
            self.stack_widget.enableDigit(False)
        else:
            self.stack_widget.enableDigit(True)
            self.stack_widget.setValue(-exponent)


class StackWidget(QLCDNumber):
    """
    Graphical widget that extends the QLCDNumber to display a value

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
        layers: int = 8,
        antialiased: bool = True,
        size: QSize = QSize(100, 100),
        border_radius: float = 5,
        spacing: float = 1,
        color_top: QColor | Qt.GlobalColor | str = '#FF0000',
        color_bottom: QColor | Qt.GlobalColor | str = '#FFFF00',
        color_grayed: QColor | Qt.GlobalColor | str = '#555555',
        percentage_grey: float = 0,
        enable_digits: bool = False
    ):
        super().__init__(1)

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

    def setValue(self, value: int):
        """
        Sets its own value

        :param value: integer to be displayed
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

        if not 0 <= percentage_grey <= 1:
            raise ValueError('percentage_grey should be in range [0, 1]')

        self.color_middle = QColor(
            int(self.color_top.red() * (1 - percentage_grey) + percentage_grey * self.color_bottom.red()),
            int(self.color_top.green() * (1 - percentage_grey) + percentage_grey * self.color_bottom.green()),
            int(self.color_top.blue() * (1 - percentage_grey) + percentage_grey * self.color_bottom.blue())
        )
        self.percentage_grey = percentage_grey

    def paintEvent(self, event):
        """Called when Widget is drawn"""

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


class ErrorTable(QTableWidget):
    """
    Simple table that extends the QTableWidget.

    :param default_rows: number of rows to be displayed
    """

    def __init__(self, default_rows: int = 3):
        super().__init__()

        self.actual_row = 0
        self.default_rows = default_rows

        self.setColumnCount(3)
        self.setRowCount(self.default_rows)
        self.verticalHeader().setVisible(False)
        self.setHorizontalHeaderLabels(['#', 'Type', 'Description'])
        self.setColumnWidth(0, 40)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 300)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
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

    :param parent: parent of Widget
    """

    def __init__(self, parent):
        super().__init__(parent)

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

    :param parent: parent of Widget
    :param path: title of Widget
    :param tac: tac time
    :param delay: delay time
    """

    deleted = pyqtSignal()

    def __init__(self, parent, path: str, *args, tac: int = -1, delay: float = 0, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.parent = parent
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.delete_button = QPushButton(self)
        self.delete_button.setIcon(QIcon('icons/delete.png'))
        self.delete_button.clicked.connect(lambda: self.deleted.emit())
        self.main_layout.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.path = path
        self.label = QLabel(self.path, self)
        self.main_layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.tac = tac
        self.delay = delay

    def __str__(self) -> str:
        """Represents itself as string by returning its path"""
        return self.path


class StackedVBoxLayout(QVBoxLayout):
    """
    Creates some sort of GridBoxLayout for DoubleSpinBoxes based on the provided labels
    Extends the QVBoxLayout

    :param labels: dictionary of {(position_row, position_column): label}
    :param click_copy: (optional) copies its contents
    """

    def __init__(self, labels: dict[tuple[int, int], str], *args, click_copy: bool = True, **kwargs):
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


class FittingWidget(QWidget):
    """
    Creates some sort of GridBoxLayout for DoubleSpinBoxes based on the provided labels
    Extends the QVBoxLayout

    :param labels: dictionary of {(position_row, position_column): label}
    :param click_copy: (optional) copies its contents
    """

    def __init__(self, labels: dict[tuple[int, int], str], *args, click_copy: bool = True, **kwargs):
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

    :param parent: parent widget
    :param data: data of plot
    :param fit_class: fitting method
    """

    def __init__(self, parent, data: tuple[np.ndarray, np.ndarray], fit_class: FitMethod, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.data = data
        self.fit_class = fit_class

        self.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.setMouseEnabled(x=True, y=False)
        self.setLabel('left', 'Counts')
        self.setLabel('bottom', 'TOF [ns]')
        self.sigRangeChanged.connect(self.updateLimits)

        self.graph_curve: pg.PlotDataItem = self.plotItem.plot(pen=pg.mkPen(color=Colors.cooperate_tu_blue, width=1))
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

    def plotData(self, data: tuple[np.ndarray, np.ndarray], view_all: bool = False):
        """
        Plots data if available

        :param data: data as tuple of x and y data in np.array form
        :param view_all: force all x axes to be shown
        """

        self.data = data

        self.graph_curve.setData(
            x=self.data[0],
            y=self.data[1],
            stepMode='left',
            fillLevel=0,
            brush=(*hexToRgb(Colors.cooperate_tu_blue), 80)
        )
        self.graph_curve_fit.setData(x=[], y=[])

        if not len(self.data[0]):
            return

        minx = np.min(self.data[0])
        maxx = np.max(self.data[0])

        self.setLimits(
            xMin=minx,
            xMax=maxx
        )

        # update if y range in selection would be too big and update x range if needed
        view_range: list[list[float, float]] = self.getViewBox().viewRange()
        selected_xrange = np.logical_and(self.data[0] > view_range[0][0], self.data[0] < view_range[0][1])
        selected_ydata = self.data[1][selected_xrange]
        if len(selected_ydata) and np.max(selected_ydata) > view_range[1][1]:
            self.setYRange(np.min(selected_ydata), np.max(selected_ydata))
        if view_all:
            self.setXRange(minx, maxx)
        else:
            self.setXRange(max(minx, view_range[0][0]), min(maxx, view_range[0][1]))

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

        if not len(self.data[0]):
            return

        minx = np.min(self.data[0])
        maxx = np.max(self.data[0])
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
        if len(self.data[0]):
            self.fit_class.setBarBounds((np.min(self.data[0]), np.max(self.data[0])))
        else:
            self.fit_class.setBarBounds((view_range[0][0], view_range[0][1]))

        if len(self.fit_class.parameters):
            self.fit_class.fitting([bar.value() for bar in self.bars], self.data, view_range)

            self.graph_curve_fit.setData(
                x=self.data[0],
                y=self.fit_class.fitFunction(self.data[0], *self.fit_class.parameters)
            )
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

        selected_range = np.logical_and(self.data[0] > view_range[0][0], self.data[0] < view_range[0][1])
        selected_ydata = self.data[1][selected_range]
        if not len(selected_ydata):
            return
        plot_widget.setYRange(np.min(selected_ydata), np.max(selected_ydata))


class FittingBar(pg.InfiniteLine):
    """
    Acts as Fitting bar; Extends the InfiniteLine

    :param name: name of fitting bar
    :param pos: position of fitting bar
    :param label_position: position of label
    """

    def __init__(self, name: str, pos: float, label_position: float = 0.9, **kwargs):
        super_dict = {
            'pos': pos,
            'movable': True,
            'label': name,
            'labelOpts': {'color': Colors.cooperate_lime, 'position': label_position},
            'pen': pg.mkPen(color=Colors.cooperate_lime, width=2),
            'hoverPen': pg.mkPen(color=Colors.cooperate_strawberry, width=3),
        }
        super_dict.update(kwargs)

        super().__init__(**super_dict)


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
