from dataclasses import dataclass, asdict, fields
from enum import Enum
from math import isfinite, ceil
from statistics import median


class InterlockState(Enum):
    """
    States of the pressure interlock, ordered by severity (higher value = more severe)
    """

    DISABLED = 0
    ARMED = 1
    TRIPPED_SOFT = 2
    TRIPPED_NO_READING = 3
    TRIPPED_HARD = 4

    def isTripped(self) -> bool:
        """Returns if the state is a tripped state"""
        return self.value >= InterlockState.TRIPPED_SOFT.value

    def text(self) -> str:
        """Returns a human readable text of the state"""
        return {
            InterlockState.DISABLED: 'Disabled (EBIS not connected)',
            InterlockState.ARMED: 'Armed',
            InterlockState.TRIPPED_SOFT: 'Tripped (soft limit)',
            InterlockState.TRIPPED_NO_READING: 'Tripped (no valid pressure)',
            InterlockState.TRIPPED_HARD: 'Tripped (hard limit)',
        }[self]


@dataclass
class InterlockLimits:
    """
    Limits of the pressure interlock. All pressures in mbar, all currents in A, all times in s.

    :param hard_pressure: if the pressure is above this value, the heating current is lowered immediately
    :param hard_current: heating current after a hard trip
    :param soft_pressure: if the median pressure over <soft_time> is above this value, the heating current is lowered
    :param soft_time: duration for the soft limit
    :param soft_current: heating current after a soft trip
    :param watchdog_time: if there is no valid pressure reading for this time, the heating current is lowered to <hard_current>
    """

    hard_pressure: float = 1E-7
    hard_current: float = 0.
    soft_pressure: float = 1E-7
    soft_time: float = 3.
    soft_current: float = 0.
    watchdog_time: float = 5.

    def toDict(self) -> dict[str, float]:
        """Returns limits as dictionary"""
        return asdict(self)

    @classmethod
    def fromDict(cls, values: dict) -> 'InterlockLimits':
        """
        Creates limits from dictionary, invalid or missing values are replaced by the default values

        :param values: dictionary of limits
        """

        limits = cls()
        for field in fields(cls):
            try:
                value = float(values.get(field.name, getattr(limits, field.name)))
            except (TypeError, ValueError):
                continue
            if not isfinite(value) or value < 0:
                continue
            setattr(limits, field.name, value)
        return limits


@dataclass
class InterlockResult:
    """
    Result of one interlock check

    :param state: state of the interlock after the check
    :param target_current: maximum allowed heating current (None if no restriction)
    :param new_trip: True if the interlock just tripped (or escalated to a more severe trip) - should be logged
    :param message: human readable description of the trip
    :param value: pressure that caused the trip (0 if not available)
    """

    state: InterlockState
    target_current: float | None = None
    new_trip: bool = False
    message: str = ''
    value: float = 0.


class PressureInterlock:
    """
    Fail-safe pressure interlock for the EBIS cathode heating.

    - Hard limit: pressure above <hard_pressure> -> heating current is lowered to <hard_current> immediately
    - Soft limit: median pressure over <soft_time> above <soft_pressure> -> heating current is lowered to <soft_current>
    - Watchdog: no valid pressure reading (gauge disconnected, pressure 0/negative/nan or readings not updating) for longer than
      <watchdog_time> -> heating current is lowered to <hard_current>

    A trip is latched: the interlock keeps the heating current limited until <reset> is called.
    The class does not know anything about the GUI or the devices, so it can be tested without hardware.

    :param limits: limits of interlock
    :param check_interval: interval in seconds in which <check> is called (used for the length of the soft limit buffer)
    """

    def __init__(self, limits: InterlockLimits = None, check_interval: float = 1.):
        if limits is None:
            limits = InterlockLimits()
        self.limits = limits
        self.check_interval = max(check_interval, 1E-3)

        self.state = InterlockState.DISABLED
        self.trip_message = ''
        self.trip_value = 0.
        self.trip_time: float | None = None

        self.pressure_buffer: list[tuple[float, float]] = []
        self.invalid_since: float | None = None

    def isTripped(self) -> bool:
        """Returns if the interlock is tripped"""
        return self.state.isTripped()

    def tripCurrent(self) -> float | None:
        """Returns the maximum allowed heating current of the current state (None if not tripped)"""

        if self.state == InterlockState.TRIPPED_SOFT:
            return self.limits.soft_current
        if self.state in [InterlockState.TRIPPED_HARD, InterlockState.TRIPPED_NO_READING]:
            return self.limits.hard_current
        return None

    def reset(self):
        """Resets (re-arms) the interlock after a trip"""

        self.state = InterlockState.ARMED
        self.trip_message = ''
        self.trip_value = 0.
        self.trip_time = None
        self.pressure_buffer = []
        self.invalid_since = None

    def disable(self):
        """Disables the interlock (EBIS not connected). A latched trip stays latched."""

        if not self.isTripped():
            self.state = InterlockState.DISABLED
        self.pressure_buffer = []
        self.invalid_since = None

    def softBufferLength(self) -> int:
        """Number of readings needed for the soft limit"""
        return max(1, ceil(self.limits.soft_time / self.check_interval))

    @staticmethod
    def isValidPressure(pressure: float | None) -> bool:
        """Returns if pressure is a valid reading (connected gauges never read exactly 0)"""

        if pressure is None:
            return False
        try:
            pressure = float(pressure)
        except (TypeError, ValueError):
            return False
        return isfinite(pressure) and pressure > 0

    def _trip(self, state: InterlockState, message: str, value: float, now: float) -> InterlockResult:
        """Trips the interlock (only escalates, never de-escalates a latched trip)"""

        new_trip = state.value > self.state.value
        if new_trip:
            self.state = state
            self.trip_message = message
            self.trip_value = value
            self.trip_time = now
        return InterlockResult(self.state, self.tripCurrent(), new_trip, self.trip_message, self.trip_value)

    def check(self, pressure: float | None, reading_age: float | None, now: float) -> InterlockResult:
        """
        Checks the pressure, should be called every <check_interval> seconds while the EBIS is connected

        :param pressure: last pressure in mbar (None or 0 if not available)
        :param reading_age: seconds since the last successful pressure reading (None if there was no reading yet)
        :param now: current (monotonic) time in seconds
        :returns: result of check
        """

        if self.state == InterlockState.DISABLED:
            self.state = InterlockState.ARMED

        valid = self.isValidPressure(pressure) and reading_age is not None and reading_age <= self.limits.watchdog_time

        # watchdog: no valid pressure reading
        if not valid:
            self.pressure_buffer = []
            if self.invalid_since is None:
                self.invalid_since = now
            # a stale reading already tells how long there was no new reading
            invalid_time = max(now - self.invalid_since, reading_age if reading_age is not None else 0.)
            if invalid_time >= self.limits.watchdog_time:
                if reading_age is None:
                    reason = 'no pressure reading (gauge/ADC not connected)'
                elif reading_age > self.limits.watchdog_time:
                    reason = f'pressure reading not updated for {reading_age:.1f} s'
                else:
                    reason = f'invalid pressure reading ({pressure})'
                return self._trip(
                    InterlockState.TRIPPED_NO_READING,
                    f'No valid pressure for {invalid_time:.1f} s: {reason}',
                    0.,
                    now
                )
            return InterlockResult(self.state, self.tripCurrent())

        self.invalid_since = None
        pressure = float(pressure)

        # hard limit
        if pressure > self.limits.hard_pressure:
            return self._trip(
                InterlockState.TRIPPED_HARD,
                f'Pressure {pressure:.2E} mbar above hard limit {self.limits.hard_pressure:.2E} mbar',
                pressure,
                now
            )

        # soft limit
        self.pressure_buffer.append((now, pressure))
        self.pressure_buffer = self.pressure_buffer[-self.softBufferLength():]
        if len(self.pressure_buffer) >= self.softBufferLength():
            median_pressure = median([p for _, p in self.pressure_buffer])
            if median_pressure > self.limits.soft_pressure:
                return self._trip(
                    InterlockState.TRIPPED_SOFT,
                    f'Median pressure {median_pressure:.2E} mbar over {self.limits.soft_time:g} s above soft limit {self.limits.soft_pressure:.2E} mbar',
                    median_pressure,
                    now
                )

        return InterlockResult(self.state, self.tripCurrent())


def test():
    """Simple tests of the interlock logic (no hardware needed)"""

    limits = InterlockLimits(hard_pressure=1E-6, hard_current=0., soft_pressure=1E-7, soft_time=3, soft_current=1., watchdog_time=5)

    # normal operation
    interlock = PressureInterlock(limits)
    for t in range(10):
        result = interlock.check(5E-8, 0.5, t)
        assert result.state == InterlockState.ARMED and result.target_current is None, result

    # hard trip and latching
    result = interlock.check(2E-6, 0.5, 10)
    assert result.state == InterlockState.TRIPPED_HARD and result.new_trip and result.target_current == 0, result
    result = interlock.check(5E-8, 0.5, 11)
    assert result.state == InterlockState.TRIPPED_HARD and not result.new_trip and result.target_current == 0, result
    interlock.reset()
    assert interlock.check(5E-8, 0.5, 12).state == InterlockState.ARMED

    # soft trip needs the full window
    interlock = PressureInterlock(limits)
    assert not interlock.check(2E-7, 0.5, 0).new_trip
    assert not interlock.check(2E-7, 0.5, 1).new_trip
    result = interlock.check(2E-7, 0.5, 2)
    assert result.state == InterlockState.TRIPPED_SOFT and result.new_trip and result.target_current == 1, result

    # soft trip escalates to hard trip
    result = interlock.check(2E-6, 0.5, 3)
    assert result.state == InterlockState.TRIPPED_HARD and result.new_trip and result.target_current == 0, result

    # single spike does not trip soft limit (median)
    interlock = PressureInterlock(limits)
    for t, p in enumerate([5E-8, 5E-7, 5E-8, 5E-8]):
        assert interlock.check(p, 0.5, t).state == InterlockState.ARMED

    # disconnected gauge (pressure 0) trips after watchdog time
    interlock = PressureInterlock(limits)
    for t in range(5):
        assert interlock.check(0, 0.5, t).state == InterlockState.ARMED
    result = interlock.check(0, 0.5, 5)
    assert result.state == InterlockState.TRIPPED_NO_READING and result.new_trip and result.target_current == 0, result

    # stale readings trip after watchdog time
    interlock = PressureInterlock(limits)
    interlock.check(5E-8, 0.5, 0)
    assert interlock.check(5E-8, 4, 1).state == InterlockState.ARMED
    assert interlock.check(5E-8, 6, 2).state == InterlockState.TRIPPED_NO_READING

    # never connected gauge, nan values
    interlock = PressureInterlock(limits)
    interlock.check(None, None, 0)
    assert interlock.check(None, None, 5).state == InterlockState.TRIPPED_NO_READING
    interlock = PressureInterlock(limits)
    interlock.check(float('nan'), 0.5, 0)
    assert interlock.check(float('nan'), 0.5, 5).state == InterlockState.TRIPPED_NO_READING

    # limits from dictionary (e.g. QSettings returns strings)
    limits = InterlockLimits.fromDict({'hard_pressure': '2e-7', 'soft_time': 'nonsense', 'hard_current': -1})
    assert limits.hard_pressure == 2E-7 and limits.soft_time == 3 and limits.hard_current == 0, limits

    print('All interlock tests passed')


if __name__ == '__main__':
    test()
