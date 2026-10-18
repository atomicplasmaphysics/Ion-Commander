from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QMessageBox, QScrollArea, QWidget
)


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import InsertingGridLayout
from Utility.Dialogs import showMessageBox


class SettingsDialog(QDialog):
    """
    Dialog to change the editable <DefaultParams> (update intervals, limits, laser address, CommandServer, ...).
    The values are stored in the settings and applied after restarting the application.

    :param parent: parent widget
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Preferences')
        self.setMinimumSize(650, 500)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        info = QLabel('Changes take effect after restarting the application. Hover over a field to see its default value.')
        info.setWordWrap(True)
        self.main_layout.addWidget(info)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(scroll_area)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        self.line_edits: dict[str, QLineEdit] = {}
        grids: dict[str, InsertingGridLayout] = {}

        for name, (group, description, unit, minimum, maximum) in DefaultParams.editable.items():
            if group not in grids:
                group_box = QGroupBox(group)
                grids[group] = InsertingGridLayout()
                group_box.setLayout(grids[group])
                scroll_layout.addWidget(group_box)

            default = DefaultParams.original.get(name, getattr(DefaultParams, name))
            tooltip = f'{description}\nDefault: {DefaultParams.toString(default)} {unit}'.strip()
            if minimum is not None and maximum is not None:
                tooltip += f'\nRange: {minimum} ... {maximum} {unit}'.rstrip()

            label = QLabel(description)
            label.setToolTip(tooltip)
            line_edit = QLineEdit(DefaultParams.toString(getattr(DefaultParams, name)))
            line_edit.setToolTip(tooltip)
            line_edit.setPlaceholderText(DefaultParams.toString(default))
            self.line_edits[name] = line_edit
            grids[group].addWidgets(label, line_edit, QLabel(unit))

        buttons_layout = QHBoxLayout()
        self.main_layout.addLayout(buttons_layout)

        self.button_defaults = QPushButton('Restore defaults')
        self.button_defaults.setToolTip('Fills in all default values (press "Save" to store them)')
        self.button_defaults.clicked.connect(self.restoreDefaults)
        buttons_layout.addWidget(self.button_defaults)

        buttons_layout.addStretch(1)

        self.button_cancel = QPushButton('Cancel')
        self.button_cancel.setToolTip('Close without saving')
        self.button_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.button_cancel)

        self.button_save = QPushButton('Save')
        self.button_save.setToolTip('Store the values, they are used after restarting the application')
        self.button_save.clicked.connect(self.save)
        buttons_layout.addWidget(self.button_save)

    def restoreDefaults(self):
        """Fills in the default values"""

        for name, line_edit in self.line_edits.items():
            line_edit.setText(DefaultParams.toString(DefaultParams.original.get(name, getattr(DefaultParams, name))))

    def save(self):
        """Checks and stores the values"""

        values = {name: line_edit.text() for name, line_edit in self.line_edits.items()}

        errors = []
        for name, value in values.items():
            try:
                DefaultParams.convert(name, value)
            except (TypeError, ValueError) as error:
                errors.append(str(error))
                self.line_edits[name].setStyleSheet('border: 1px solid red;')
            else:
                self.line_edits[name].setStyleSheet('')

        if errors:
            showMessageBox(
                self,
                QMessageBox.Icon.Warning,
                'Invalid values!',
                'Some values are invalid, nothing was saved.',
                '<br>'.join(errors)
            )
            return

        DefaultParams.saveOverrides(GlobalConf.settings, values, GlobalConf.default_params_group_name)
        GlobalConf.logger.info('Preferences saved, they are applied after restarting the application')
        showMessageBox(
            self,
            QMessageBox.Icon.Information,
            'Preferences saved',
            'The preferences are applied after restarting the application.'
        )
        self.accept()
