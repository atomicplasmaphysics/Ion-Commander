"""
Fits of pressure curves to predict the final pressure (e.g. after pumping down or baking out).

Two models with a constant offset p_inf (= predicted final pressure):
- Exponential:  p(t) = p_inf + A * exp(-t / tau)
  pumping of the gas volume (pump speed S, volume V: tau = V / S)
- Power law:    p(t) = p_inf + A * (t + t1)^(-n)
  outgassing of the walls (n ~ 1 for metals, n ~ 0.5 for elastomers), usually better for long times

The pressure spans several decades, so the fits use relative errors (each point weighted with 1 / p).
"""

from dataclasses import dataclass, field
from typing import Callable


import numpy as np

from scipy.optimize import curve_fit, OptimizeWarning
from warnings import catch_warnings, simplefilter


def exponentialOffset(t: np.ndarray, p_inf: float, amplitude: float, tau: float) -> np.ndarray:
    """p(t) = p_inf + A * exp(-t / tau)"""
    return p_inf + amplitude * np.exp(-np.asarray(t, dtype=float) / tau)


def powerLawOffset(t: np.ndarray, p_inf: float, amplitude: float, exponent: float, t1: float) -> np.ndarray:
    """p(t) = p_inf + A * (t + t1)^(-n)"""
    return p_inf + amplitude * np.power(np.asarray(t, dtype=float) + t1, -exponent)


@dataclass
class PressureFitResult:
    """
    Result of a pressure fit

    :param model: name of model
    :param p_inf: predicted final pressure
    :param parameters: all fit parameters (as dictionary)
    :param function: fitted function of the time in s since <t_start>
    :param t_start: timestamp of the first data point
    :param relative_rms: rms of the relative residuals (quality of the fit)
    :param description: human readable result
    """

    model: str
    p_inf: float
    parameters: dict[str, float]
    function: Callable[[np.ndarray], np.ndarray]
    t_start: float
    relative_rms: float
    description: str = ''
    extra: dict = field(default_factory=dict)

    def predict(self, timestamps: np.ndarray) -> np.ndarray:
        """Predicted pressure at the given timestamps"""
        return self.function(np.asarray(timestamps, dtype=float) - self.t_start)

    def timeToReach(self, pressure: float) -> float | None:
        """Timestamp when the given pressure is reached (None if never, i.e. below the final pressure)"""

        if pressure <= self.p_inf:
            return None
        t = np.linspace(0, self.extra.get('t_span', 3600) * 1000, 200001)
        p = self.function(t)
        reached = np.nonzero(p <= pressure)[0]
        if not len(reached):
            return None
        return float(self.t_start + t[reached[0]])


def formatDuration(seconds: float) -> str:
    """Formats a duration in s, min, h or d"""

    if seconds < 120:
        return f'{seconds:.0f} s'
    if seconds < 7200:
        return f'{seconds / 60:.1f} min'
    if seconds < 172800:
        return f'{seconds / 3600:.1f} h'
    return f'{seconds / 86400:.1f} d'


def _prepare(timestamps: np.ndarray, pressures: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Removes invalid values and returns (t since start, p, start timestamp)"""

    timestamps = np.asarray(timestamps, dtype=float)
    pressures = np.asarray(pressures, dtype=float)
    valid = np.isfinite(timestamps) & np.isfinite(pressures) & (pressures > 0)
    timestamps = timestamps[valid]
    pressures = pressures[valid]
    order = np.argsort(timestamps)
    timestamps = timestamps[order]
    pressures = pressures[order]
    if len(timestamps) < 5:
        raise ValueError('At least 5 valid data points are needed for the fit')
    if timestamps[-1] - timestamps[0] <= 0:
        raise ValueError('The data points must cover a time range')
    return timestamps - timestamps[0], pressures, float(timestamps[0])


def _limitWarning(at_limit: bool) -> str:
    """Warning text if a fit parameter ended at its limit (the model probably does not describe the data)"""
    return ' (parameter at its limit - model probably not suitable)' if at_limit else ''


def fitExponential(timestamps: np.ndarray, pressures: np.ndarray) -> PressureFitResult:
    """
    Fits p(t) = p_inf + A * exp(-t / tau)

    :param timestamps: timestamps in s
    :param pressures: pressures (> 0)
    """

    t, p, t_start = _prepare(timestamps, pressures)
    span = float(t[-1])

    p_min = float(np.min(p))
    best = None
    with catch_warnings():
        simplefilter('ignore', OptimizeWarning)
        simplefilter('ignore', RuntimeWarning)
        for tau0 in (span / 10, span / 3, span, span * 3):
            p0 = [p_min * 0.5, max(float(p[0]) - p_min * 0.5, p_min * 1E-3), tau0]
            bounds = ([0, 0, span * 1E-4], [p_min * 1.5, np.inf, span * 1E3])
            try:
                popt = curve_fit(exponentialOffset, t, p, p0=p0, bounds=bounds, sigma=p, maxfev=10000)[0]
            except (RuntimeError, ValueError):
                continue
            rms = float(np.sqrt(np.mean(np.square((exponentialOffset(t, *popt) - p) / p))))
            if best is None or rms < best[0]:
                best = (rms, popt)

    if best is None:
        raise RuntimeError('Exponential fit did not converge')

    rms, (p_inf, amplitude, tau) = best
    warning = _limitWarning(p_inf <= p_min * 1E-6 or tau >= span * 999)
    return PressureFitResult(
        model='Exponential',
        p_inf=float(p_inf),
        parameters={'p_inf': float(p_inf), 'A': float(amplitude), 'tau': float(tau)},
        function=lambda x, popt=tuple(best[1]): exponentialOffset(x, *popt),
        t_start=t_start,
        relative_rms=rms,
        description=f'p∞ = {p_inf:.2E} mbar, τ = {formatDuration(tau)}, rms {rms * 100:.1f} %{warning}',
        extra={'t_span': span}
    )


def fitPowerLaw(timestamps: np.ndarray, pressures: np.ndarray) -> PressureFitResult:
    """
    Fits p(t) = p_inf + A * (t + t1)^(-n)

    :param timestamps: timestamps in s
    :param pressures: pressures (> 0)
    """

    t, p, t_start = _prepare(timestamps, pressures)
    span = float(t[-1])

    p_min = float(np.min(p))
    best = None
    with catch_warnings():
        simplefilter('ignore', OptimizeWarning)
        simplefilter('ignore', RuntimeWarning)
        for exponent0 in (0.5, 1.0, 2.0):
            for t10 in (span / 100, span / 10, span):
                amplitude0 = max(float(p[0]) - p_min * 0.5, p_min * 1E-3) * t10 ** exponent0
                p0 = [p_min * 0.5, amplitude0, exponent0, t10]
                bounds = ([0, 0, 0.05, span * 1E-6], [p_min * 1.5, np.inf, 5, span * 100])
                try:
                    popt = curve_fit(powerLawOffset, t, p, p0=p0, bounds=bounds, sigma=p, maxfev=20000)[0]
                except (RuntimeError, ValueError):
                    continue
                rms = float(np.sqrt(np.mean(np.square((powerLawOffset(t, *popt) - p) / p))))
                if best is None or rms < best[0]:
                    best = (rms, popt)

    if best is None:
        raise RuntimeError('Power law fit did not converge')

    rms, (p_inf, amplitude, exponent, t1) = best
    warning = _limitWarning(p_inf <= p_min * 1E-6 or exponent >= 4.99 or exponent <= 0.051)
    return PressureFitResult(
        model='Power law',
        p_inf=float(p_inf),
        parameters={'p_inf': float(p_inf), 'A': float(amplitude), 'n': float(exponent), 't1': float(t1)},
        function=lambda x, popt=tuple(best[1]): powerLawOffset(x, *popt),
        t_start=t_start,
        relative_rms=rms,
        description=f'p∞ = {p_inf:.2E} mbar, n = {exponent:.2f}, rms {rms * 100:.1f} %{warning}',
        extra={'t_span': span}
    )


FIT_MODELS = {
    'Exponential': fitExponential,
    'Power law': fitPowerLaw,
}


def test():
    """Tests the fits with synthetic data"""

    rng = np.random.default_rng(0)
    t = np.arange(0, 6 * 3600, 30.)

    p = exponentialOffset(t, 2E-9, 5E-7, 3600) * (1 + 0.02 * rng.standard_normal(len(t)))
    result = fitExponential(t + 1.7E9, p)
    print(result.model, result.description)
    assert abs(result.p_inf / 2E-9 - 1) < 0.1 and abs(result.parameters['tau'] / 3600 - 1) < 0.1

    p = powerLawOffset(t, 1E-9, 1E-4, 1.0, 600) * (1 + 0.02 * rng.standard_normal(len(t)))
    result = fitPowerLaw(t, p)
    print(result.model, result.description)
    assert abs(result.p_inf / 1E-9 - 1) < 0.3 and abs(result.parameters['n'] - 1) < 0.2

    reach = result.timeToReach(5E-9)
    print('5E-9 mbar reached after', formatDuration(reach - result.t_start))

    try:
        fitExponential([0, 1], [1, 2])
        raise AssertionError('should fail')
    except ValueError as error:
        print('too few points:', error)
    print('All pressure fit tests passed')


if __name__ == '__main__':
    test()
