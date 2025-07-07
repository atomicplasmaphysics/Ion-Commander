from PyQt6.QtWidgets import QSplitter, QWidget, QBoxLayout
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import TabWidget, VBoxTitleLayout

from DB.db import DB

from Windows.PSU import PSUVBoxLayout
from Windows.EBIS import EBISVBoxLayout
from Windows.Laser import LaserVBoxLayout
from Windows.Pressure import PressureVBoxLayout

from math import ceil
from statistics import median


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
        self.splitter.addWidget(self.psu_vbox_parent)

        self.ebis_enabled = True
        if self.ebis_enabled:
            # EBIS CONTROL
            self.ebis_vbox = VBoxTitleLayout('EBIS', parent=self, add_stretch=True, popout_enable=True)
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
            self.pressure_buffer=[]

        # LASER CONTROL
        self.laser_vbox = VBoxTitleLayout('LASER', parent=self, add_stretch=True, popout_enable=True)
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
        self.pressure_vbox = VBoxTitleLayout('Pressure', parent=self, add_stretch=True, popout_enable=True)
        self.pressure_group_vbox = PressureVBoxLayout()

        # Stretch to bottom
        self.pressure_group_vbox.addStretch(1)
        self.pressure_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the simulationConfigurationListLayout and add that to the splitter
        self.pressure_parent = QWidget(self)
        self.pressure_vbox.setBodyLayout(self.pressure_group_vbox)
        self.pressure_parent.setLayout(self.pressure_vbox)
        self.splitter.addWidget(self.pressure_parent)

        # Division between columns
        splitter_count = self.splitter.count() - 1
        splitter_width_last = 10
        splitter_width = int((100 - splitter_width_last) / splitter_count)
        for c in range(splitter_count):
            self.splitter.setStretchFactor(c, splitter_width)
        self.splitter.setStretchFactor(splitter_count, int(100 - splitter_width * splitter_count))

    def pressureCheck(self):
        """Checks pressure periodically"""

        # disable EBIS heating current if pressure is too high
        if not self.ebis_enabled or not self.ebis_group_vbox.indicator_connection.value():
            return

        last_pressure = self.pressure_group_vbox.pressure_widget_1.pressure

        # Hard limit : turn off immediately if pressure is above hard limit
        if last_pressure > self.ebis_group_vbox.hard_pmax_val:
            self.ebis_group_vbox.setCurrent(5, self.ebis_group_vbox.hard_current_val)
            self.ebis_group_vbox.spinbox_current_6.setValue(self.ebis_group_vbox.hard_current_val)
            return

        # Soft limit : turn off if average pressure is above soft limit
        pressure_buffer_length = ceil(1000 * self.ebis_group_vbox.soft_time_val / DefaultParams.update_timer_time)
        self.pressure_buffer.append(self.pressure_group_vbox.pressure_widget_1.pressure)
        self.pressure_buffer = self.pressure_buffer[-pressure_buffer_length:]
        # average_pressure = sum(self.pressure_buffer) / len(self.pressure_buffer)
        if median(self.pressure_buffer) > self.ebis_group_vbox.soft_pmax_val:
            self.ebis_group_vbox.setCurrent(5, self.ebis_group_vbox.soft_current_val)
            self.ebis_group_vbox.spinbox_current_6.setValue(self.ebis_group_vbox.soft_current_val)
            return

    def closeEvent(self, event):
        """Closes all connections"""
        self.psu_group_vbox.closeEvent()
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
        self.laser_group_vbox.log(db)
        self.pressure_group_vbox.log(db)
        if self.ebis_enabled:
            self.ebis_group_vbox.log(db)
