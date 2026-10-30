from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QMessageBox, QScrollArea, QWidget
)


from Config.GlobalConf import GlobalConf, DefaultParams

from Utility.Layouts import InsertingGridLayout
from Utility.Dialogs import showMessageBox
from Utility.PotentialDifferences import PotentialDifferenceTable


class SettingsDialog(QDialog):
    """
    Dialog to change the editable <DefaultParams> (update intervals, limits, laser address, CommandServer, ...).
    The values are stored in the settings and applied after restarting the application, the allowed potential
    differences of the EBIS are applied immediately.

    :param parent: parent widget
    :param section: section that is shown when the dialog opens (<section_ebis_differences>), '' for the top
    """

    section_ebis_differences = 'ebis_differences'

    def __init__(self, parent=None, section: str = ''):
        super().__init__(parent)

        self.setWindowTitle('Preferences')
        self.setMinimumSize(650, 500)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        info = QLabel(
            'Changes take effect after restarting the application (the EBIS potential differences immediately). '
            'Hover over a field to see its default value.'
        )
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

        # allowed potential differences between the EBIS channels (applied immediately)
        self.group_ebis_differences = QGroupBox('EBIS potential differences')
        group_ebis_differences_layout = QVBoxLayout()
        self.group_ebis_differences.setLayout(group_ebis_differences_layout)
        enabled, limits = GlobalConf.getEBISDifferences()
        self.table_ebis_differences = PotentialDifferenceTable(DefaultParams.ebis_channel_names, enabled, limits)
        group_ebis_differences_layout.addWidget(self.table_ebis_differences)
        scroll_layout.addWidget(self.group_ebis_differences)

        if section == self.section_ebis_differences:
            self.setWindowTitle('Preferences - EBIS potential differences')
            # after the layout is done, otherwise the position of the group is not known yet
            QTimer.singleShot(0, lambda: scroll_area.ensureWidgetVisible(self.group_ebis_differences, 0, 0))
            QTimer.singleShot(0, self.table_ebis_differences.table.setFocus)

        buttons_layout = QHBoxLayout()
        self.main_layout.addLayout(buttons_layout)

        self.button_defaults = QPushButton('Restore defaults')
        self.button_defaults.setToolTip('Fills in all default values (press "Save" to store them), the EBIS potential differences are kept')
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

        difference_limits, difference_errors = self.table_ebis_differences.limits()
        errors.extend(difference_errors)

        if errors:
            showMessageBox(
                self,
                QMessageBox.Icon.Warning,
                'Invalid values!',
                'Some values are invalid, nothing was saved.',
                '<br>'.join(errors)
            )
            return

        changed = any(
            DefaultParams.convert(name, value) != getattr(DefaultParams, name) for name, value in values.items()
        )
        DefaultParams.saveOverrides(GlobalConf.settings, values, GlobalConf.default_params_group_name)
        GlobalConf.updateEBISDifferences(self.table_ebis_differences.enabled(), difference_limits)
        GlobalConf.logger.info(
            f'Preferences saved, EBIS potential differences: check {"on" if self.table_ebis_differences.enabled() else "off"}, '
            f'limits {difference_limits}'
        )
        if changed:
            showMessageBox(
                self,
                QMessageBox.Icon.Information,
                'Preferences saved',
                'The preferences are applied after restarting the application.',
                'The EBIS potential differences are used immediately.'
            )
        self.accept()
