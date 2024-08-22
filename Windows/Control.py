from PyQt6.QtWidgets import QSplitter, QWidget, QGroupBox, QBoxLayout
from PyQt6.QtCore import Qt


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

        # SPLITTER
        self.splitter = QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.main_layout.addWidget(self.splitter)

        # TODO: Add tooltips to everything

        # PSU CONTROL
        self.psu_vbox = VBoxTitleLayout('PSU', parent=self, add_stretch=True)
        self.psu_group_vbox = PSUVBoxLayout()

        # Stretch to bottom
        self.psu_group_vbox.addStretch(1)
        self.psu_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.psu_vbox_parent = QWidget(self)
        self.psu_group = QGroupBox(self)
        self.psu_group.setLayout(self.psu_group_vbox)
        self.psu_vbox.addWidget(self.psu_group)
        self.psu_vbox_parent.setLayout(self.psu_vbox)
        self.splitter.addWidget(self.psu_vbox_parent)

        # EBIS CONTROL
        self.ebis_vbox = VBoxTitleLayout('EBIS', parent=self, add_stretch=True)
        self.ebis_group_vbox = EBISVBoxLayout()

        # Stretch to bottom
        self.ebis_group_vbox.addStretch(1)
        self.ebis_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the simulationConfigurationListLayout and add that to the splitter
        self.ebis_parent = QWidget(self)
        self.ebis_group = QGroupBox(self)
        self.ebis_group.setLayout(self.ebis_group_vbox)
        self.ebis_vbox.addWidget(self.ebis_group)
        self.ebis_parent.setLayout(self.ebis_vbox)
        self.splitter.addWidget(self.ebis_parent)

        # LASER CONTROL
        self.laser_vbox = VBoxTitleLayout('LASER', parent=self, add_stretch=True)
        self.laser_group_vbox = LaserVBoxLayout()

        # Stretch to bottom
        self.laser_group_vbox.addStretch(1)
        self.laser_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the simulationConfigurationListLayout and add that to the splitter
        self.laser_parent = QWidget(self)
        self.laser_group = QGroupBox(self)
        self.laser_group.setLayout(self.laser_group_vbox)
        self.laser_vbox.addWidget(self.laser_group)
        self.laser_parent.setLayout(self.laser_vbox)
        self.splitter.addWidget(self.laser_parent)

        # PRESSURE CONTROL
        self.pressure_vbox = VBoxTitleLayout('Pressure', parent=self, add_stretch=True)
        self.pressure_group_vbox = PressureVBoxLayout()

        # Stretch to bottom
        self.pressure_group_vbox.addStretch(1)
        self.pressure_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the simulationConfigurationListLayout and add that to the splitter
        self.pressure_parent = QWidget(self)
        self.pressure_group = QGroupBox(self)
        self.pressure_group.setLayout(self.pressure_group_vbox)
        self.pressure_vbox.addWidget(self.pressure_group)
        self.pressure_parent.setLayout(self.pressure_vbox)
        self.splitter.addWidget(self.pressure_parent)

        # Division between columns
        # TODO: does not work properly
        self.splitter.setStretchFactor(0, 30)
        self.splitter.setStretchFactor(1, 30)
        self.splitter.setStretchFactor(2, 30)
        self.splitter.setStretchFactor(3, 10)

    def closeEvent(self, event):
        """Closes all connections"""
        self.psu_group_vbox.closeEvent()
        self.ebis_group_vbox.closeEvent()
        self.laser_group_vbox.closeEvent()
        self.pressure_group_vbox.closeEvent()

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        self.pressure_group_vbox.log(db)
