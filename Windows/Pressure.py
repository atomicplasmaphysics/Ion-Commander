from PyQt6.QtWidgets import QVBoxLayout, QGroupBox

from Utility.Layouts import PressureWidget


class PressureVBoxLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # PITBUL
        self.group_box_pitbul = QGroupBox('PITBUL')
        self.pressure_widget_pitbul = PressureWidget()
        self.layout_pitbul = QVBoxLayout()
        self.layout_pitbul.addWidget(self.pressure_widget_pitbul)
        self.group_box_pitbul.setLayout(self.layout_pitbul)
        self.addWidget(self.group_box_pitbul)

        # LSD
        self.group_box_lsd = QGroupBox('LSD')
        self.pressure_widget_lsd = PressureWidget()
        self.layout_lsd = QVBoxLayout()
        self.layout_lsd.addWidget(self.pressure_widget_lsd)
        self.group_box_lsd.setLayout(self.layout_lsd)
        self.addWidget(self.group_box_lsd)

        # TODO: remove this lines
        self.pressure_widget_pitbul.setPressure(4.175E-10)
        self.pressure_widget_lsd.setPressure(2.985E-7)
