from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QHBoxLayout, QLabel


from Config.StylesConf import Colors

from Utility.Layouts import IndicatorLed


class LaserVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        indicator_size = QSize(20, 20)

        # Connection
        self.connection_hbox = QHBoxLayout()
        self.connection_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.connection_gbox = QGroupBox('Connection')
        self.connection_gbox.setLayout(self.connection_hbox)
        self.addWidget(self.connection_gbox)

        self.indicator_connection = IndicatorLed(clickable=True, size=indicator_size, off_color=Colors.error)
        self.connection_hbox.addWidget(self.indicator_connection)
        self.label_connection = QLabel('Not connected to Laser')
        self.connection_hbox.addWidget(self.label_connection)

        # Key-switch
        self.key_switch_hbox = QHBoxLayout()
        self.key_switch_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.key_switch_gbox = QGroupBox('Key-Switch')
        self.key_switch_gbox.setLayout(self.key_switch_hbox)
        self.addWidget(self.key_switch_gbox)

        self.indicator_key_switch = IndicatorLed(clickable=True, size=indicator_size)
        self.key_switch_hbox.addWidget(self.indicator_key_switch)
        self.label_key_switch = QLabel('Key off')
        self.key_switch_hbox.addWidget(self.label_key_switch)

        # Shutter
        self.shutter_hbox = QHBoxLayout()
        self.shutter_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.shutter_gbox = QGroupBox('Shutter')
        self.shutter_gbox.setLayout(self.shutter_hbox)
        self.addWidget(self.shutter_gbox)

        self.indicator_shutter = IndicatorLed(clickable=True, size=indicator_size)
        self.shutter_hbox.addWidget(self.indicator_shutter)
        self.label_shutter = QLabel('Closed')
        self.shutter_hbox.addWidget(self.label_shutter)

        # Pulsing
        self.pulsing_hbox = QHBoxLayout()
        self.pulsing_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.pulsing_gbox = QGroupBox('Pulsing')
        self.pulsing_gbox.setLayout(self.pulsing_hbox)
        self.addWidget(self.pulsing_gbox)

        self.indicator_pulsing = IndicatorLed(clickable=True, size=indicator_size)
        self.pulsing_hbox.addWidget(self.indicator_pulsing)
        self.label_pulsing = QLabel('Off')
        self.pulsing_hbox.addWidget(self.label_pulsing)

        # System status
        self.system_status_hbox = QHBoxLayout()
        self.system_status_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.system_status_gbox = QGroupBox('System Status')
        self.system_status_gbox.setLayout(self.system_status_hbox)
        self.addWidget(self.system_status_gbox)

        self.indicator_system_status = IndicatorLed(clickable=True, size=indicator_size)
        self.system_status_hbox.addWidget(self.indicator_system_status)
        self.label_system_status = QLabel('Standby')
        self.system_status_hbox.addWidget(self.label_system_status)

        # System faults
        # Laser Settings
        # Chiller Temperature
        # Baseplate Temperature
        # Chiller Flow



