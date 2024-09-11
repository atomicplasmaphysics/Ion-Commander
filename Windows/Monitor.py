from PyQt6.QtWidgets import QSplitter, QWidget, QGroupBox, QBoxLayout
from PyQt6.QtCore import Qt


from Utility.Layouts import TabWidget, VBoxTitleLayout


from Windows.PowerMeter import PowerMeterVBoxLayout


class MonitorWindow(TabWidget):
    """
    Widget for monitoring hardware

    :param parent: parent widget
    """

    # TODO: implement powermeter
    # TODO: implement camera

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

        # Division between columns
        # TODO: does not work properly
        self.splitter.setStretchFactor(0, 30)

    def closeEvent(self, event):
        """Closes all connections"""
        self.power_meter_group_vbox.closeEvent()
