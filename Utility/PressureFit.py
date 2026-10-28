"""
Fits of pressure curves to predict the final pressure (e.g. after pumping down or baking out).

Two models with a constant offset p_inf (= predicted final pressure):
- Exponential:  p(t) = p_inf + A * exp(-t / tau)
  pumping of the gas volume (pump speed S, volume V: tau = V / S)
- Power law:    p(t) = p_inf + A * (t + t1)^(-n)
  outgassing of the walls (n ~ 1 for metals, n ~ 0.5 for elastomers), usually better for long times

The pressure spans several decades, so the fits use relative errors (each point weighted with 1 / p).

General fits for any curve of the History tab (also negative values):
- Linear:       y(t) = a + b * t (drift, slope per hour)
- Gaussian:     y(t) = c + A * exp(-(t - t0)^2 / (2 sigma^2)) (peaks)
- Log-normal:   y(t) = c + A * exp(-ln((t - t0) / w)^2 / (2 s^2)) for t > t0 (asymmetric peaks with a long tail)

Exponential, power law and linear are extrapolated into the future (prediction), the peaks only cover the fitted range.
"""

from dataclasses import dataclass, field
from datetime import datetime
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
    # if the fit is extrapolated into the future (False: only drawn over the fitted range)
    prediction: bool = True

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


def fitExponential(timestamps: np.ndarray, pressures: np.ndarray, unit: str = 'mbar') -> PressureFitResult:
    """
    Fits p(t) = p_inf + A * exp(-t / tau)

    :param timestamps: timestamps in s
    :param pressures: pressures (> 0)
    :param unit: unit of the values (for the description)
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
        description=f'p∞ = {p_inf:.2E} {unit}, τ = {formatDuration(tau)}, rms {rms * 100:.1f} %{warning}',
        extra={'t_span': span}
    )


def fitPowerLaw(timestamps: np.ndarray, pressures: np.ndarray, unit: str = 'mbar') -> PressureFitResult:
    """
    Fits p(t) = p_inf + A * (t + t1)^(-n)

    :param timestamps: timestamps in s
    :param pressures: pressures (> 0)
    :param unit: unit of the values (for the description)
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
        description=f'p∞ = {p_inf:.2E} {unit}, n = {exponent:.2f}, rms {rms * 100:.1f} %{warning}',
        extra={'t_span': span}
    )


def linear(t: np.ndarray, offset: float, slope: float) -> np.ndarray:
    """y(t) = a + b * t"""
    return offset + slope * np.asarray(t, dtype=float)


def gaussian(t: np.ndarray, offset: float, amplitude: float, center: float, sigma: float) -> np.ndarray:
    """y(t) = c + A * exp(-(t - t0)^2 / (2 sigma^2))"""
    return offset + amplitude * np.exp(-np.square(np.asarray(t, dtype=float) - center) / (2 * sigma ** 2))


def logNormal(t: np.ndarray, offset: float, amplitude: float, t0: float, width: float, shape: float) -> np.ndarray:
    """y(t) = c + A * exp(-ln((t - t0) / w)^2 / (2 s^2)) for t > t0, else c (maximum at t = t0 + w)"""

    x = (np.asarray(t, dtype=float) - t0) / width
    result = np.full(x.shape, float(offset))
    positive = x > 0
    result[positive] += amplitude * np.exp(-np.square(np.log(x[positive])) / (2 * shape ** 2))
    return result


def _prepareAny(timestamps: np.ndarray, values: np.ndarray, minimum_points: int = 5) -> tuple[np.ndarray, np.ndarray, float]:
    """Removes invalid values (negative values are allowed) and returns (t since start, y, start timestamp)"""

    timestamps = np.asarray(timestamps, dtype=float)
    values = np.asarray(values, dtype=float)
    valid = np.isfinite(timestamps) & np.isfinite(values)
    order = np.argsort(timestamps[valid])
    timestamps = timestamps[valid][order]
    values = values[valid][order]
    if len(timestamps) < minimum_points:
        raise ValueError(f'At least {minimum_points} valid data points are needed for the fit')
    if timestamps[-1] - timestamps[0] <= 0:
        raise ValueError('The data points must cover a time range')
    return timestamps - timestamps[0], values, float(timestamps[0])


def _rms(model: np.ndarray, values: np.ndarray) -> float:
    """rms of the residuals relative to the range of the values"""

    span = float(np.ptp(values)) or float(np.max(np.abs(values))) or 1.
    return float(np.sqrt(np.mean(np.square(model - values)))) / span


def _timeText(t_start: float, t: float) -> str:
    """Timestamp as time of day (with date if it is not today)"""

    moment = datetime.fromtimestamp(t_start + t)
    return f'{moment:%H:%M:%S}' if moment.date() == datetime.now().date() else f'{moment:%Y-%m-%d %H:%M}'


def fitLinear(timestamps: np.ndarray, values: np.ndarray, unit: str = '') -> PressureFitResult:
    """
    Fits y(t) = a + b * t

    :param timestamps: timestamps in s
    :param values: values
    :param unit: unit of the values (for the description)
    """

    t, y, t_start = _prepareAny(timestamps, values, 2)
    slope, offset = np.polyfit(t, y, 1)
    rms = _rms(linear(t, offset, slope), y)
    return PressureFitResult(
        model='Linear',
        p_inf=float('nan'),
        parameters={'a': float(offset), 'b': float(slope)},
        function=lambda x, popt=(float(offset), float(slope)): linear(x, *popt),
        t_start=t_start,
        relative_rms=rms,
        description=f'slope {slope * 3600:.3E} {unit}/h, start {offset:.3E} {unit}, rms {rms * 100:.1f} % of the range',
        extra={'t_span': float(t[-1])}
    )


def fitGaussian(timestamps: np.ndarray, values: np.ndarray, unit: str = '') -> PressureFitResult:
    """
    Fits y(t) = c + A * exp(-(t - t0)^2 / (2 sigma^2)) (peak or dip)

    :param timestamps: timestamps in s
    :param values: values
    :param unit: unit of the values (for the description)
    """

    t, y, t_start = _prepareAny(timestamps, values)
    span = float(t[-1])
    offset0 = float(np.median(y))
    peak = int(np.argmax(np.abs(y - offset0)))
    amplitude0 = float(y[peak] - offset0)
    # width from the points above half of the peak
    above = np.nonzero(np.abs(y - offset0) >= abs(amplitude0) / 2)[0]
    sigma0 = max(float(t[above[-1]] - t[above[0]]) / 2.355, span / 100) if len(above) else span / 10

    with catch_warnings():
        simplefilter('ignore', OptimizeWarning)
        simplefilter('ignore', RuntimeWarning)
        try:
            popt = curve_fit(
                gaussian, t, y, p0=[offset0, amplitude0, float(t[peak]), sigma0],
                bounds=([-np.inf, -np.inf, -span, span * 1E-5], [np.inf, np.inf, 2 * span, 10 * span]),
                maxfev=20000
            )[0]
        except (RuntimeError, ValueError) as error:
            raise RuntimeError(f'Gaussian fit did not converge: {error}')

    offset, amplitude, center, sigma = (float(value) for value in popt)
    rms = _rms(gaussian(t, *popt), y)
    return PressureFitResult(
        model='Gaussian',
        p_inf=offset,
        parameters={'c': offset, 'A': amplitude, 't0': center, 'sigma': sigma},
        function=lambda x, popt=tuple(popt): gaussian(x, *popt),
        t_start=t_start,
        relative_rms=rms,
        description=f'peak {offset + amplitude:.3E} {unit} at {_timeText(t_start, center)}, FWHM {formatDuration(2.355 * sigma)}, '
                    f'background {offset:.3E} {unit}, rms {rms * 100:.1f} % of the range',
        extra={'t_span': span},
        prediction=False
    )


def fitLogNormal(timestamps: np.ndarray, values: np.ndarray, unit: str = '') -> PressureFitResult:
    """
    Fits y(t) = c + A * exp(-ln((t - t0) / w)^2 / (2 s^2)) (asymmetric peak, maximum at t0 + w)

    :param timestamps: timestamps in s
    :param values: values
    :param unit: unit of the values (for the description)
    """

    t, y, t_start = _prepareAny(timestamps, values)
    span = float(t[-1])
    offset0 = float(np.median(y))
    peak = int(np.argmax(np.abs(y - offset0)))
    amplitude0 = float(y[peak] - offset0)

    best = None
    with catch_warnings():
        simplefilter('ignore', OptimizeWarning)
        simplefilter('ignore', RuntimeWarning)
        for rise in (0.1, 0.3, 1.):
            width0 = max(float(t[peak]) * rise, span * 1E-3)
            t00 = float(t[peak]) - width0
            for shape0 in (0.3, 0.7):
                try:
                    popt = curve_fit(
                        logNormal, t, y, p0=[offset0, amplitude0, t00, width0, shape0],
                        bounds=([-np.inf, -np.inf, -span, span * 1E-5, 0.02], [np.inf, np.inf, span, 10 * span, 5]),
                        maxfev=20000
                    )[0]
                except (RuntimeError, ValueError):
                    continue
                rms = _rms(logNormal(t, *popt), y)
                if best is None or rms < best[0]:
                    best = (rms, popt)

    if best is None:
        raise RuntimeError('Log-normal fit did not converge')

    rms, popt = best
    offset, amplitude, t0, width, shape = (float(value) for value in popt)
    return PressureFitResult(
        model='Log-normal',
        p_inf=offset,
        parameters={'c': offset, 'A': amplitude, 't0': t0, 'w': width, 's': shape},
        function=lambda x, popt=tuple(popt): logNormal(x, *popt),
        t_start=t_start,
        relative_rms=rms,
        description=f'peak {offset + amplitude:.3E} {unit} at {_timeText(t_start, t0 + width)}, start {_timeText(t_start, t0)}, '
                    f's = {shape:.2f}, background {offset:.3E} {unit}, rms {rms * 100:.1f} % of the range',
        extra={'t_span': span},
        prediction=False
    )


FIT_MODELS = {
    'Exponential': fitExponential,
    'Power law': fitPowerLaw,
    'Linear': fitLinear,
    'Gaussian': fitGaussian,
    'Log-normal': fitLogNormal,
}
# models that predict a final value p∞ (time to reach 1.1·p∞ is shown)
FINAL_VALUE_MODELS = ('Exponential', 'Power law')


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

    y = linear(t, -2E-12, 1E-16) + 1E-14 * rng.standard_normal(len(t))
    result = fitLinear(t + 1.7E9, y, 'A')
    print(result.model, result.description)
    assert abs(result.parameters['b'] / 1E-16 - 1) < 0.05

    y = gaussian(t, 1E-13, -5E-12, 3 * 3600, 600) + 2E-14 * rng.standard_normal(len(t))
    result = fitGaussian(t, y, 'A')
    print(result.model, result.description)
    assert abs(result.parameters['t0'] / (3 * 3600) - 1) < 0.01 and abs(result.parameters['sigma'] / 600 - 1) < 0.05

    y = logNormal(t, 0, 3E-9, 1800, 2400, 0.5) + 2E-11 * rng.standard_normal(len(t))
    result = fitLogNormal(t, y, 'A')
    print(result.model, result.description)
    assert abs((result.parameters['t0'] + result.parameters['w']) / 4200 - 1) < 0.05
    print('All pressure fit tests passed')


if __name__ == '__main__':
    test()
