from PyQt6.QtWidgets import QSplitter, QWidget, QBoxLayout
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import TabWidget, VBoxTitleLayout

from DB.db import DB

from Windows.PSU import PSUVBoxLayout
from Windows.EBIS import EBISVBoxLayout
from Windows.Laser import LaserVBoxLayout
from Windows.Pressure import PressureVBoxLayout
from Windows.DelayStage import DelayStageVBoxLayout


class ControlWindow(TabWidget):
    """
    Widget for controlling hardware

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        # SPLITTER
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        # PSU CONTROL
        self.psu_vbox = VBoxTitleLayout('PSU', parent=self, add_stretch=True, popout_enable=True)
        self.psu_group_vbox = PSUVBoxLayout()

        # Stretch to bottom
        self.psu_group_vbox.addStretch(1)
        self.psu_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.psu_vbox_parent = QWidget(self)
        self.psu_vbox.setBodyLayout(self.psu_group_vbox)
        self.psu_vbox_parent.setLayout(self.psu_vbox)

        # DELAY STAGE CONTROL
        self.delay_stage_vbox = VBoxTitleLayout('Delay Stage', parent=self, add_stretch=True, popout_enable=True)
        self.delay_stage_group_vbox = DelayStageVBoxLayout()

        # Stretch to bottom
        self.delay_stage_group_vbox.addStretch(1)
        self.delay_stage_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.delay_stage_parent = QWidget(self)
        self.delay_stage_vbox.setBodyLayout(self.delay_stage_group_vbox)
        self.delay_stage_parent.setLayout(self.delay_stage_vbox)

        # the delay stage uses the free space below the PSU, another column would not fit on the screen
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.addWidget(self.psu_vbox_parent)
        self.left_splitter.addWidget(self.delay_stage_parent)
        self.left_splitter.setStretchFactor(0, 0)
        self.left_splitter.setStretchFactor(1, 1)
        self.splitter.addWidget(self.left_splitter)

        self.ebis_enabled = True
        if self.ebis_enabled:
            # EBIS CONTROL
            self.ebis_vbox = VBoxTitleLayout('EBIS', parent=self, add_stretch=True, popout_enable=True, fit_content=True)
            self.ebis_group_vbox = EBISVBoxLayout()

            # Stretch to bottom
            self.ebis_group_vbox.addStretch(1)
            self.ebis_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

            # Add a parent to the simulationConfigurationListLayout and add that to the splitter
            self.ebis_parent = QWidget(self)
            self.ebis_vbox.setBodyLayout(self.ebis_group_vbox)
            self.ebis_parent.setLayout(self.ebis_vbox)
            self.splitter.addWidget(self.ebis_parent)

            # Pressure check timer
            self.pressure_check_timer = QTimer()
            self.pressure_check_timer.timeout.connect(self.pressureCheck)
            self.pressure_check_timer.setInterval(DefaultParams.update_timer_time)
            self.pressure_check_timer.start()

        # LASER CONTROL
        self.laser_vbox = VBoxTitleLayout('LASER', parent=self, add_stretch=True, popout_enable=True, fit_content=True)
        self.laser_group_vbox = LaserVBoxLayout()

        # Stretch to bottom
        self.laser_group_vbox.addStretch(1)
        self.laser_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the simulationConfigurationListLayout and add that to the splitter
        self.laser_parent = QWidget(self)
        self.laser_vbox.setBodyLayout(self.laser_group_vbox)
        self.laser_parent.setLayout(self.laser_vbox)
        self.splitter.addWidget(self.laser_parent)

        # PRESSURE CONTROL
        # the pressures are always fully visible in width (no horizontal scrollbar)
        self.pressure_vbox = VBoxTitleLayout('Pressure', parent=self, add_stretch=True, popout_enable=True, scroll_horizontal=False, fit_content=True)
        self.pressure_group_vbox = PressureVBoxLayout()

        # Stretch to bottom
        self.pressure_group_vbox.addStretch(1)
        self.pressure_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the simulationConfigurationListLayout and add that to the splitter
        self.pressure_parent = QWidget(self)
        self.pressure_vbox.setBodyLayout(self.pressure_group_vbox)
        self.pressure_parent.setLayout(self.pressure_vbox)
        self.splitter.addWidget(self.pressure_parent)
        self.pressure_group_vbox.setTitleLayout(self.pressure_vbox)

        # the interlock follows renamed gauges and its gauge can not be removed
        if self.ebis_enabled:
            self.pressure_group_vbox.interlock_gauge_function = lambda: self.ebis_group_vbox.combobox_pressure_gauge.getValue(text=True)
            self.pressure_group_vbox.gauges_changed.connect(self.pressureGaugesChanged)

        # Division between columns: no panel gets wider than its content, only the leftmost panel takes the remaining width
        self.title_layouts = [self.psu_vbox, self.ebis_vbox, self.laser_vbox, self.pressure_vbox] if self.ebis_enabled else [self.psu_vbox, self.laser_vbox, self.pressure_vbox]
        for index, title_layout in enumerate(self.title_layouts):
            title_layout.updateBodyMinimumWidth()
            self.splitter.setStretchFactor(index, 1 if index == 0 else 0)
        self.splitter_moved = False
        self.splitter.splitterMoved.connect(self.splitterMoved)
        self.left_splitter.splitterMoved.connect(self.splitterMoved)

    def splitterMoved(self):
        """The user changed the width of the panels: they are not fitted automatically anymore"""
        self.splitter_moved = True

    def resizeEvent(self, event):
        """The panels fit the window until the user changes their widths (the window gets its final size after it is shown)"""

        super().resizeEvent(event)
        if not self.splitter_moved:
            QTimer.singleShot(0, self.fitPanels)

    def fitPanels(self):
        """All panels get the width of their content and the leftmost one the rest. If the window is too narrow, the panels that can scroll get smaller."""

        widths = [title_layout.contentWidth() for title_layout in self.title_layouts]
        widths[0] += sum(self.splitter.sizes()) - sum(widths)
        if widths[0] < self.psu_vbox.contentWidth():
            # the pressure panel (last one) keeps its width
            missing = self.psu_vbox.contentWidth() - widths[0]
            widths[0] += missing
            for index in range(len(widths) - 1):
                widths[index] -= missing // (len(widths) - 1)
        self.splitter.setSizes(widths)

        height = sum(self.left_splitter.sizes())
        psu_height = min(self.psu_vbox.contentHeight(), height - self.delay_stage_parent.minimumSizeHint().height())
        self.left_splitter.setSizes([psu_height, height - psu_height])

    def pressureGaugesChanged(self, old_name: str, new_name: str):
        """
        The pressure gauges changed: updates the selection of the EBIS pressure interlock

        :param old_name: old name of a renamed gauge
        :param new_name: new name of a renamed gauge
        """

        selected = self.ebis_group_vbox.combobox_pressure_gauge.getValue(text=True)
        self.ebis_group_vbox.setPressureGauges(self.pressure_group_vbox.gaugeNames(), new_name if selected == old_name else selected)

    def pressureCheck(self):
        """Feeds the EBIS pressure interlock periodically and logs every trip to the database"""

        if not self.ebis_enabled:
            return

        gauge_name = self.ebis_group_vbox.combobox_pressure_gauge.getValue(text=True)
        pressure = self.pressure_group_vbox.getPressure(gauge_name)
        reading_age = self.pressure_group_vbox.secondsSinceLastUpdate()

        result = self.ebis_group_vbox.checkInterlock(pressure, reading_age)
        if result is None or not result.new_trip:
            return

        message = f'{result.state.text()} ({gauge_name}): {result.message}, heating current limited to {result.target_current} A'
        self.writeStatusBar(f'EBIS pressure interlock: {message}', 0)
        database = getattr(self.main_window, 'database', None)
        if database is not None:
            database.insertEvent('EBIS', f'interlock_{result.state.name.lower()}', message, result.value)

    def closeEvent(self, event):
        """Closes all connections"""
        self.psu_group_vbox.closeEvent()
        self.delay_stage_group_vbox.closeEvent()
        if self.ebis_enabled:
            self.ebis_group_vbox.closeEvent()
        self.laser_group_vbox.closeEvent()
        self.pressure_group_vbox.closeEvent()

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        self.psu_group_vbox.log(db)
        self.delay_stage_group_vbox.log(db)
        self.laser_group_vbox.log(db)
        self.pressure_group_vbox.log(db)
        if self.ebis_enabled:
            self.ebis_group_vbox.log(db)
