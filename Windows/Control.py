from PyQt6.QtWidgets import QSplitter, QWidget, QBoxLayout
from PyQt6.QtCore import Qt, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import TabWidget, VBoxTitleLayout

from DB.db import DB

from Windows.PSU import PSUVBoxLayout
from Windows.EBIS import EBISVBoxLayout
from Windows.Laser import LaserVBoxLayout
from Windows.Pressure import PressureVBoxLayout


class ControlWindow(TabWidget):
    """
    Widget for controlling hardware

    :param parent: parent widget
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.setLayout(self.main_layout)

        # local timers
        self.pressure_check_timer = QTimer()
        self.pressure_check_timer.timeout.connect(self.pressureCheck)
        self.pressure_check_timer.setInterval(DefaultParams.update_timer_time)
        self.pressure_check_timer.start()

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
        if self.ebis_enabled:
            if self.pressure_group_vbox.pressure_widget_1.pressure > 1E-7:
                self.ebis_group_vbox.setCurrent(5, 0)

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
