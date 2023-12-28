from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget, QGroupBox, QBoxLayout
from PyQt6.QtCore import Qt


from Utility.Layouts import TabWidget, VBoxTitleLayout

from Windows.Laser import LaserVBoxLayout


class ControlWindow(TabWidget):
    """
    Widget for Analysis

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

        # MCP CONTROL
        self.mcp_vbox = VBoxTitleLayout(self, 'MCP', add_stretch=True)
        self.mcp_group_vbox = QVBoxLayout()

        # Stretch to bottom
        self.mcp_group_vbox.addStretch(1)
        self.mcp_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.mcp_vbox_parent = QWidget(self)
        self.mcp_group = QGroupBox(self)
        self.mcp_group.setLayout(self.mcp_group_vbox)
        self.mcp_vbox.addWidget(self.mcp_group)
        self.mcp_vbox_parent.setLayout(self.mcp_vbox)
        self.splitter.addWidget(self.mcp_vbox_parent)

        # EBIS CONTROL
        self.ebis_vbox = VBoxTitleLayout(self, 'EBIS', add_stretch=True)
        self.ebis_group_vbox = QVBoxLayout()

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
        self.laser_vbox = VBoxTitleLayout(self, 'LASER', add_stretch=True)
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
        self.pressure_vbox = VBoxTitleLayout(self, 'Pressure', add_stretch=True)
        self.pressure_group_vbox = QVBoxLayout()

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
