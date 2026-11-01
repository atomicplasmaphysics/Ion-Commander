from typing import Callable


from PyQt6.QtWidgets import QLabel


from Config.GlobalConf import GlobalConf
from Config.StylesConf import Colors

from Utility.Layouts import InsertingGridLayout, IndicatorLed, LedButton, DoubleSpinBox, DisplayLabel, PolarityButton


class VoltageChannelRow:
    """
    One row of a high voltage channel (used by PSU and EBIS):
    name | (polarity) | set voltage | measured voltage | measured current | output led (button) | (current limit | limit reached)

    :param grid: grid layout where the row is inserted
    :param name: name of the channel
    :param channel: index of the channel (passed to the functions)
    :param set_voltage: function(channel, voltage) called when the set voltage was edited
    :param set_output: function(channel, state) called when the output led is clicked
    :param set_polarity: function(channel, polarity) called when the polarity is changed (None: no polarity button)
    :param limit_row: current limit of the channel, shown at the end of the row (None: no current limit)
    :param voltage_maximum: maximum of the set voltage
    :param voltage_deviation: allowed deviation of the measured voltage
    :param current_maximum: allowed current (shown in red above)
    :param voltage_decimals: decimals of the set voltage
    :param voltage_step: step size of the set voltage
    :param voltage_unit: unit of voltage
    :param show_current: show measured current
    :param current_decimals: decimals of the measured current (None: default)
    :param current_prefix: show measured current with SI prefix
    """

    def __init__(
        self,
        grid: InsertingGridLayout,
        name: str,
        channel: int,
        set_voltage: Callable[[int, float], None],
        set_output: Callable[[int, bool], None],
        set_polarity: Callable[[int, bool], None] | None = None,
        limit_row: 'CurrentLimitRow | None' = None,
        voltage_maximum: float = 1000,
        voltage_deviation: float = 1,
        current_maximum: float = 1E-4,
        voltage_decimals: int = 1,
        voltage_step: float = 0.1,
        voltage_unit: str = 'V',
        show_current: bool = True,
        current_decimals: int | None = None,
        current_prefix: bool = True
    ):
        self.name = name
        self.channel = channel
        self.voltage_unit = voltage_unit

        self.label = QLabel(name)

        self.button_polarity: PolarityButton | None = None
        if set_polarity is not None:
            self.button_polarity = PolarityButton(connected_buttons=False)
            self.button_polarity.setToolTip(f'Polarity of {name} (can only be changed if the output is off)')
            self.button_polarity.pressed.connect(lambda state: set_polarity(self.channel, state))

        self.spinbox_voltage = DoubleSpinBox(default=0, step_size=voltage_step, input_range=(0, voltage_maximum), decimals=voltage_decimals, buttons=False)
        self.spinbox_voltage.setToolTip(f'Set voltage of {name} in {voltage_unit} (press enter to apply)')
        self.spinbox_voltage.editingFinished.connect(lambda: set_voltage(self.channel, self.spinbox_voltage.value()))

        self.status_voltage = DisplayLabel(value=0, unit=voltage_unit, target_value=0, deviation=voltage_deviation)
        self.status_voltage.setToolTip(f'Measured voltage of {name} (red if it deviates more than {voltage_deviation} {voltage_unit} from the set voltage)')

        self.status_current: DisplayLabel | None = None
        if show_current:
            current_kwargs = {} if current_decimals is None else {'decimals': current_decimals}
            self.status_current = DisplayLabel(value=0, unit='A', target_value=0, deviation=current_maximum, enable_prefix=current_prefix, **current_kwargs)
            self.status_current.setToolTip(f'Measured current of {name}')

        self.indicator = LedButton()
        self.indicator.setToolTip(f'Output of {name} is on (green) or off. Click to switch it on/off')
        self.indicator.clicked.connect(lambda: set_output(self.channel, not self.indicator.value()))

        widgets = [self.label]
        if self.button_polarity is not None:
            widgets.append(self.button_polarity)
        widgets.extend([self.spinbox_voltage, self.status_voltage, self.status_current, self.indicator])
        if limit_row is not None:
            widgets.extend([limit_row.spinbox_limit, limit_row.indicator_limit])
        grid.addWidgets(*widgets)

    def setVoltageMaximum(self, maximum: float):
        """
        Sets the maximum of the set voltage (e.g. the nominal voltage of the channel reported by the device)

        :param maximum: maximum voltage
        """

        self.spinbox_voltage.setMaximum(maximum)
        self.spinbox_voltage.setToolTip(f'Set voltage of {self.name} in {self.voltage_unit} (press enter to apply, maximum {maximum:g} {self.voltage_unit})')

    def setOutputState(self, state: bool):
        """
        Shows the output state

        :param state: output on
        """

        self.indicator.setValue(state)
        if not state:
            self.status_voltage.setTargetValue(0)

    def reset(self):
        """Resets the row to its default values"""

        self.indicator.setValue(False)
        if self.button_polarity is not None:
            self.button_polarity.reset()
        self.spinbox_voltage.reset()
        self.status_voltage.setValue(0)
        self.status_voltage.setTargetValue(0)
        if self.status_current is not None:
            self.status_current.setValue(0)
            self.status_current.setTargetValue(0)


class CurrentLimitRow:
    """
    Current limit of a channel (used by PSU and EBIS): current limit [mA] | limit reached indicator.
    The widgets are shown in the <VoltageChannelRow> of the channel.

    :param name: name of the channel
    :param channel: index of the channel (passed to the function)
    :param set_current_limit: function(channel, current in mA) called when the limit was edited
    :param input_range: range of the limit in mA
    """

    def __init__(
        self,
        name: str,
        channel: int,
        set_current_limit: Callable[[int, float], None],
        input_range: tuple[float, float] = (0.002, 2)
    ):
        self.name = name
        self.channel = channel

        self.spinbox_limit =DoubleSpinBox(default=input_range[0], step_size=0.001, input_range=input_range, decimals=3, buttons=False)
        self.spinbox_limit.setToolTip(f'Current limit of {name} in mA (range {input_range[0]} ... {input_range[1]} mA)')
        self.spinbox_limit.editingFinished.connect(lambda: set_current_limit(self.channel, self.spinbox_limit.value()))
        self.indicator_limit = IndicatorLed(on_color=Colors.color_red)
        self.indicator_limit.setToolTip(f'Red if the measured current of {name} reached the limit')

    def setLimitMaximum(self, maximum: float):
        """
        Sets the maximum of the current limit (e.g. the nominal current of the channel reported by the device)

        :param maximum: maximum in mA
        """

        self.spinbox_limit.setMaximum(maximum)
        self.spinbox_limit.setToolTip(f'Current limit of {self.name} in mA (range {self.spinbox_limit.minimum():g} ... {maximum:g} mA)')

    def updateCurrent(self, current: float):
        """
        Shows if the measured current reached the limit

        :param current: measured current in A
        """

        self.indicator_limit.setValue(current >= self.spinbox_limit.value() / 1000)

    def reset(self):
        """Resets the row to its default values"""

        self.spinbox_limit.reset()
        self.indicator_limit.setValue(False)


def nominalMaxima(nominals, count: int, maxima: list[float], factor: float = 1) -> list[float] | None:
    """
    Maxima of the input fields from the nominal values of the channels (:READ:VOLT:NOM?, :READ:CURR:NOM?): the smaller
    one of the maximum from the preferences and the absolute nominal value (negative channels report negative values)

    :param nominals: nominal values reported by the device (list, one per channel)
    :param count: expected number of channels
    :param maxima: maxima from the preferences, one per channel
    :param factor: unit conversion of the nominal values (e.g. 1000 for A -> mA)
    :returns: maxima or None if the answer is not valid
    """

    if not isinstance(nominals, list) or len(nominals) != count:
        GlobalConf.logger.error(f'Nominal values cannot be used, expected {count} values, got {nominals!r}')
        return None
    # invalid answers (-1) or 0 keep the maximum of the preferences
    return [min(maximum, abs(nominal) * factor) if abs(nominal) > 0 and nominal != -1 else maximum for nominal, maximum in zip(nominals, maxima)]
