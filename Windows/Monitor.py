from PyQt6.QtWidgets import QSplitter, QWidget, QBoxLayout
from PyQt6.QtCore import Qt


from DB.db import DB

from Utility.Layouts import TabWidget, VBoxTitleLayout

from Windows.PowerMeter import PowerMeterVBoxLayout
from Windows.Camera import CameraVBoxLayout
from Windows.Electrometer import ElectrometerVBoxLayout


class MonitorWindow(TabWidget):
    """
    Widget for monitoring hardware

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
        self.power_meter_vbox = VBoxTitleLayout('Power Meter', parent=self, add_stretch=True, popout_enable=True)
        self.power_meter_group_vbox = PowerMeterVBoxLayout()

        # Stretch to bottom
        self.power_meter_group_vbox.addStretch(1)
        self.power_meter_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add a parent to the basic_control_vbox and add that to the splitter
        self.power_meter_vbox_parent = QWidget(self)
        self.power_meter_vbox.setBodyLayout(self.power_meter_group_vbox)
        self.power_meter_vbox_parent.setLayout(self.power_meter_vbox)
        self.splitter.addWidget(self.power_meter_vbox_parent)

        # ELECTROMETER (Keithley 6514)
        self.electrometer_vbox = VBoxTitleLayout('Electrometer', parent=self, add_stretch=True, popout_enable=True)
        self.electrometer_group_vbox = ElectrometerVBoxLayout()
        self.electrometer_group_vbox.addStretch(1)
        self.electrometer_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.electrometer_vbox_parent = QWidget(self)
        self.electrometer_vbox.setBodyLayout(self.electrometer_group_vbox)
        self.electrometer_vbox_parent.setLayout(self.electrometer_vbox)
        self.splitter.addWidget(self.electrometer_vbox_parent)

        # CAMERA
        self.camera_vbox = VBoxTitleLayout('Camera', parent=self, add_stretch=True, popout_enable=True)
        self.camera_group_vbox = CameraVBoxLayout()
        self.camera_group_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.camera_vbox_parent = QWidget(self)
        self.camera_vbox.setBodyLayout(self.camera_group_vbox)
        self.camera_vbox_parent.setLayout(self.camera_vbox)
        self.splitter.addWidget(self.camera_vbox_parent)

        # Division between columns
        self.splitter.setStretchFactor(0, 30)
        self.splitter.setStretchFactor(1, 30)
        self.splitter.setStretchFactor(2, 40)

    def closeEvent(self, event):
        """Closes all connections"""
        self.power_meter_group_vbox.closeEvent()
        self.camera_group_vbox.closeEvent()
        self.electrometer_group_vbox.closeEvent()

    def log(self, db: DB):
        """
        Called to log all important value

        :param db: database class
        """

        self.power_meter_group_vbox.log(db)
        self.electrometer_group_vbox.log(db)
