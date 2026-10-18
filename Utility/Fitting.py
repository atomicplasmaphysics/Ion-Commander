from typing import TYPE_CHECKING
from warnings import simplefilter


import numpy as np

from scipy.optimize import curve_fit, OptimizeWarning

import pyqtgraph as pg


from Config.GlobalConf import GlobalConf

if TYPE_CHECKING:
    from Windows.Main import MainWindow

from Utility.Layouts import createFittingBars, FittingWidget


simplefilter('ignore', OptimizeWarning)
simplefilter('ignore', RuntimeWarning)
supported_file_types = ['dat', 'cod', 'cod2', 'lmftxt']


def getTACFileData(filename: str, tac: int, delay: float = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts TAC-file (.dat) into x, y values

    :param filename: filename of TAC file
    :param tac: total TAC time in ns (50, 100, 200, ...)
    :param delay: delay time before TAC signal in ns
    :return: x-array (in ns), y-array (counts(int))
    """

    x = np.linspace(delay, tac + delay, 8192)

    with open(filename, 'r', encoding='utf-8') as file:
        y = [float(line) for line in file.readlines()]

    return x, np.array(y).astype(int)


def getTDCFileData(filename: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts TDC-file (.cod) into x, y values

    :param filename: filename of TDC file
    :return: x-array (in ns), y-array (counts(int))
    """

    x = []
    y = []

    with open(filename, 'r', encoding='utf-8') as file:
        for line in file.readlines():
            xi, yi = [float(s) for s in line.strip().split(',')]
            x.append(xi)
            y.append(yi)

    return np.array(x), np.array(y).astype(int)


def getLMFTXTFileData(filename: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts LMFTXT-file (.lmftxt) into x, y values

    :param filename: filename of TDC file
    :return: x-array (in ns), y-array (counts(int))
    """

    tofs = []
    falling = []

    resolution = np.nan
    range_start = np.nan
    range_end = np.nan

    with open(filename, 'r', encoding='utf-8') as file:
        for line in file.readlines():
            line = line.strip()
            if 'TDC resolution' in line:
                resolution = float(line.split('=')[-1].split('ps')[0]) / 1000
            if 'Group range start' in line:
                range_start = float(line.split('=')[-1].split('ns')[0])
            if 'Group range end' in line:
                range_end = float(line.split('=')[-1].split('ns')[0])
            split = line.split('\t')
            if len(split) < 4:
                continue

            try:
                tofs.append(float(split[3]))
                falling.append(int(split[4]))
            except (ValueError, IndexError):
                continue

    if resolution == np.nan:
        raise IOError('Resolution not set')

    if range_start == np.nan or range_end == np.nan:
        raise IOError('Range start or end not set')

    tofs = np.array(tofs)
    falling = np.array(falling)

    if len(falling):
        if len(tofs) != len(falling):
            raise IOError('Number of "falling" values do not match "tofs".')
        tofs = tofs[falling == True]

    bins = np.arange(range_start, range_end + resolution, resolution)
    y, _ = np.histogram(tofs, bins)
    x = (bins[1:] + bins[:-1]) / 2

    return x, y.astype(int)


def getFileData(filename: str, tac: int = -1, delay: float = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts supported file into x, y

    :param filename: name of file (path)
    :param tac: (only required for .dat (=TAC) files) total TAC time in ns (50, 100, 200, ...)
    :param delay: (only required for .dat (=TAC) files) delay time before TAC signal in ns
    :return: x-array (in ns), y-array (counts)
    """

    filetype = filename.split('.')[-1]

    if filetype not in supported_file_types:
        raise ValueError(f'Not supported type of "{filetype}"!')

    if filetype == 'cod' or filetype == 'cod2':
        return getTDCFileData(filename)
    elif filetype == 'dat':
        return getTACFileData(filename, tac, delay)
    elif filetype == 'lmftxt':
        return getLMFTXTFileData(filename)
    else:
        raise NotImplementedError(f'Not implemented type of "{filetype}"! Should not happen!')


def estimateGauss(x_data: np.ndarray, y_data: np.ndarray) -> tuple[float, float, float]:
    """
    Robust start values (sigma, mu, c) for a Gaussian peak: position and height of the maximum,
    sigma from the width at half maximum around the maximum (falls back to a quarter of the range).

    :param x_data: sorted x-values
    :param y_data: y-values
    """

    max_index = int(np.argmax(y_data))
    mu0 = float(x_data[max_index])
    c0 = float(y_data[max_index])
    sigma0 = float(x_data[-1] - x_data[0]) / 4

    # walk from the maximum to both sides until the half maximum is reached
    half = c0 / 2
    left = max_index
    while left > 0 and y_data[left] > half:
        left -= 1
    right = max_index
    while right < len(y_data) - 1 and y_data[right] > half:
        right += 1
    fwhm = float(x_data[right] - x_data[left])
    if fwhm > 0:
        sigma0 = fwhm / (2 * np.sqrt(2 * np.log(2)))

    return sigma0, mu0, c0


def gaussBounds(x_data: np.ndarray, c0: float, x_range: tuple[float, float]) -> tuple[list[float], list[float]]:
    """
    Bounds (sigma, mu, c) for a Gaussian fit: sigma between a tenth of the bin width and the range width,
    mu inside the range and c between 0 and 10 times the maximum

    :param x_data: sorted x-values
    :param c0: maximum of y-values
    :param x_range: (start, end) of the fit range
    """

    bin_width = float(np.min(np.diff(x_data))) if len(x_data) > 1 else 1E-12
    sigma_min = max(bin_width / 10, 1E-12)
    sigma_max = max(float(x_range[1] - x_range[0]), sigma_min * 2)
    c_max = max(c0 * 10, 1E-12)
    return [sigma_min, x_range[0], 0], [sigma_max, x_range[1], c_max]


def clipToBounds(p0: list[float], bounds: tuple[list[float], list[float]]) -> list[float]:
    """Moves start values inside the bounds (curve_fit raises a ValueError otherwise)"""

    return [float(np.clip(value, low, high)) for value, low, high in zip(p0, bounds[0], bounds[1])]


class FitMethod:
    """
    General method to fit data

    :param parent: parent widget
    :param no_qt: disable Qt related stuff
    """

    title = 'No fit'
    tooltip = 'No fit at all'

    def __init__(self, parent, no_qt: bool = False):
        self.parent: MainWindow = parent
        self.no_qt = no_qt
        if self.no_qt:
            self.widget = None
        else:
            self.widget = FittingWidget({}, parent)
        self.parameter: list[float] = []
        self.parameters = 0
        self.bars: list[pg.InfiniteLine] = []
        self.copy_info = ''

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        pass

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        pass

    @staticmethod
    def fitFunction(xdata, *args) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param args: arguments for fitting function
        :return: y-values
        """

        return np.zeros(xdata.shape)

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        return ''

    def updateParameters(self):
        """Updates parameters"""
        if self.widget is not None:
            self.widget.setValues(self.parameter)


class FitGaussRange(FitMethod):
    """
    Method to gauss-fit data from start to stop

    :param parent: parent widget
    """

    title = 'Gauss (range)'
    tooltip = 'Makes Gaussian fit in given range'

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'σ',
                (0, 1): 'μ',
                (0, 2): 'c',
                (0, 3): 'FWHM'
            }, parent)
        self.parameter = [0, 0, 0, 0]
        self.parameters = 3

        if not self.no_qt:
            self.bars = createFittingBars([
                'Start',
                'End'
            ])

        self.copy_info = '(mu, c, fwhm)'

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], self.bars[1].value()))
        self.bars[1].setBounds((self.bars[0].value(), xrange[1]))

    @staticmethod
    def fitFunction(xdata, sigma: float, mu: float, c: float) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param sigma: sigma of gauss
        :param mu: mu of gauss
        :param c: c of gauss
        :return: y-values
        """

        return c * np.exp(-(xdata - mu) ** 2 / (2 * sigma ** 2))

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        limit = np.logical_and(data[0] > bar_values[0], data[0] < bar_values[1])
        x_data_limit = data[0][limit]
        y_data_limit = data[1][limit]

        if not len(x_data_limit):
            self.parent.writeStatusBar('Not enough datapoints in given range')
            return

        if len(x_data_limit) < 4:
            self.parent.writeStatusBar('Not enough datapoints in given range (at least 4 needed)')
            return

        sigma0, mean0, c0 = estimateGauss(x_data_limit, y_data_limit)
        bounds = gaussBounds(x_data_limit, c0, (bar_values[0], bar_values[1]))
        p0 = clipToBounds([sigma0, mean0, c0], bounds)

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)[0]
            # self.parameter = [sigma, mu, c, FWHM]
            self.parameter = [
                popt[0],
                popt[1],
                popt[2],
                2 * np.sqrt(2 * np.log(2)) * popt[0]
            ]
            self.updateParameters()

        except (ValueError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting Gauss: {error}')
            GlobalConf.logger.info(f'Error in fitting Gauss (edge-bars): {error}')

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        # (mu, c, fwhm)
        return f'({self.parameter[1]}, {self.parameter[2]}, {self.parameter[3]})'


class FitGaussCenter(FitMethod):
    """
    Method to gauss-fit data from start to stop

    :param parent: parent widget
    """

    title = 'Gauss (center)'
    tooltip = 'Makes Gaussian fit with provided center'

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'σ',
                (0, 1): 'μ',
                (0, 2): 'c',
                (0, 3): 'FWHM'
            }, parent)
        self.parameter = [0, 0, 0, 0]
        self.parameters = 3

        if not self.no_qt:
            self.bars = createFittingBars([
                'Center'
            ])

        self.copy_info = '(mu, c, fwhm)'

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], xrange[1]))

    @staticmethod
    def fitFunction(xdata, sigma: float, mu: float, c: float) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param sigma: sigma of gauss
        :param mu: mu of gauss
        :param c: c of gauss
        :return: y-values
        """

        return c * np.exp(-(xdata - mu) ** 2 / (2 * sigma ** 2))

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        # first guess of the window: 10 % of the visible range around the bar ...
        limit_distance = (view_range[0][1] - view_range[0][0]) * 0.1
        limit_x = (bar_values[0] - limit_distance, bar_values[0] + limit_distance)
        limit = np.logical_and(data[0] > limit_x[0], data[0] < limit_x[1])
        x_data_limit = data[0][limit]
        y_data_limit = data[1][limit]

        # ... then +-3 FWHM around the peak, so wide peaks are not cut and narrow peaks are not disturbed by neighbours
        if len(x_data_limit) >= 4:
            sigma_estimate, _, _ = estimateGauss(x_data_limit, y_data_limit)
            fwhm_estimate = 2 * np.sqrt(2 * np.log(2)) * sigma_estimate
            limit_distance = float(np.clip(3 * fwhm_estimate, limit_distance / 4, (view_range[0][1] - view_range[0][0]) / 2))
            limit_x = (bar_values[0] - limit_distance, bar_values[0] + limit_distance)
            limit = np.logical_and(data[0] > limit_x[0], data[0] < limit_x[1])
            x_data_limit = data[0][limit]
            y_data_limit = data[1][limit]

        if not len(x_data_limit):
            self.parent.writeStatusBar('Not enough datapoints in given range')
            return

        if not x_data_limit[0] < bar_values[0] < x_data_limit[-1]:
            self.parent.writeStatusBar('Bar not in visible range')
            return

        if len(x_data_limit) < 4:
            self.parent.writeStatusBar('Not enough datapoints around the bar (at least 4 needed)')
            return

        sigma0, mean0, c0 = estimateGauss(x_data_limit, y_data_limit)
        bounds = gaussBounds(x_data_limit, c0, limit_x)
        p0 = clipToBounds([sigma0, mean0, c0], bounds)

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)[0]
            # self.parameter = [sigma, mu, c, FWHM]
            self.parameter = [
                popt[0],
                popt[1],
                popt[2],
                2 * np.sqrt(2 * np.log(2)) * popt[0]
            ]
            self.updateParameters()

        except (ValueError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting Gauss: {error}')
            GlobalConf.logger.info(f'Error in fitting Gauss (center-bar): {error}')

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        # (mu, c, fwhm)
        return f'({self.parameter[1]}, {self.parameter[2]}, {self.parameter[3]})'


class FitLogNormRange(FitMethod):
    """
    Method to fit a shifted log-normal distribution from start to stop (for asymmetric peaks with a tail to larger x):

        y = A / (sigma * (x - x0) * sqrt(2 pi)) * exp(-(ln(x - x0) - mu)^2 / (2 sigma^2))   for x > x0, else 0

    A is the area of the peak, x0 the shift. The fit is started with several skewness values (sigma) from a Gaussian
    pre-fit and the best result (smallest squared residuals) is used.

    :param parent: parent widget
    """

    title = 'LogNorm (range)'
    tooltip = 'Makes a shifted log-normal fit in given range (for peaks with a tail)'

    # start values for sigma (skewness) that are tried
    sigma_starts = (0.05, 0.15, 0.3, 0.6, 1.0)

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'σ',
                (0, 1): 'μ',
                (0, 2): 'x0',
                (0, 3): 'A',
                (0, 4): 'mode',
                (0, 5): 'FWHM'
            }, parent)
        self.parameter = [0, 0, 0, 0, 0, 0]
        self.parameters = 4

        if not self.no_qt:
            self.bars = createFittingBars([
                'Start',
                'End'
            ])

        self.copy_info = '(mode, A, fwhm)'

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], self.bars[1].value()))
        self.bars[1].setBounds((self.bars[0].value(), xrange[1]))

    @staticmethod
    def fitFunction(xdata, sigma: float, mu: float, x0: float, c: float) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param sigma: sigma of log-norm (skewness)
        :param mu: mu of log-norm (log of the scale)
        :param x0: shift of log-norm (function is 0 for x <= x0)
        :param c: area of the peak
        :return: y-values
        """

        xdata = np.asarray(xdata, dtype=float)
        ydata = np.zeros(xdata.shape)
        x = xdata - x0
        valid = x > 0
        if sigma <= 0 or not np.any(valid):
            return ydata
        ydata[valid] = c / (sigma * x[valid] * np.sqrt(2 * np.pi)) * np.exp(-np.square(np.log(x[valid]) - mu) / (2 * np.square(sigma)))
        return ydata

    @staticmethod
    def mode(sigma: float, mu: float, x0: float) -> float:
        """Position of the maximum"""
        return float(np.exp(mu - np.square(sigma)) + x0)

    @staticmethod
    def fwhm(sigma: float, mu: float) -> float:
        """Full width at half maximum"""
        return float(np.exp(mu - np.square(sigma)) * 2 * np.sinh(np.sqrt(2 * np.log(2)) * sigma))

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        limit = np.logical_and(data[0] > bar_values[0], data[0] < bar_values[1])
        x_data_limit = np.asarray(data[0][limit], dtype=float)
        y_data_limit = np.asarray(data[1][limit], dtype=float)

        if len(x_data_limit) < 6:
            self.parent.writeStatusBar('Not enough datapoints in given range (at least 6 needed)')
            return

        # start values from the peak: mode, width and area
        sigma_gauss, mode0, c0 = estimateGauss(x_data_limit, y_data_limit)
        if c0 <= 0:
            self.parent.writeStatusBar('No peak in given range')
            return
        area0 = c0 * sigma_gauss * np.sqrt(2 * np.pi)
        x_first = float(x_data_limit[0])
        width = float(x_data_limit[-1] - x_data_limit[0])

        best = None
        for sigma0 in self.sigma_starts:
            # scale exp(mu) so that the FWHM matches the Gaussian estimate, x0 so that the mode matches
            fwhm_gauss = 2 * np.sqrt(2 * np.log(2)) * sigma_gauss
            scale = fwhm_gauss / (np.exp(-np.square(sigma0)) * 2 * np.sinh(np.sqrt(2 * np.log(2)) * sigma0))
            mu0 = float(np.log(scale))
            x00 = mode0 - scale * np.exp(-np.square(sigma0))

            # x0 (onset of the peak) must be before the maximum; the function is 0 for all points before x0
            bounds = (
                [1E-3, mu0 - 10, x_first - 100 * max(width, 1E-12), 0],
                [5, mu0 + 10, mode0 - 1E-9 * max(abs(mode0), 1), area0 * 20]
            )
            p0 = clipToBounds([sigma0, mu0, x00, area0], bounds)

            try:
                popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds, maxfev=5000)[0]
            except (ValueError, TypeError, RuntimeError) as error:
                GlobalConf.logger.debug(f'LogNorm fit with sigma0 = {sigma0} failed: {error}')
                continue

            residual = float(np.sum(np.square(self.fitFunction(x_data_limit, *popt) - y_data_limit)))
            if best is None or residual < best[0]:
                best = (residual, popt)

        if best is None:
            self.parent.writeStatusBar('Error in fitting LogNorm: no start value converged')
            GlobalConf.logger.info('Error in fitting LogNorm: no start value converged')
            return

        sigma, mu, x0, area = best[1]
        # self.parameter = [sigma, mu, x0, A, mode, FWHM]
        self.parameter = [
            float(sigma),
            float(mu),
            float(x0),
            float(area),
            self.mode(sigma, mu, x0),
            self.fwhm(sigma, mu)
        ]
        self.updateParameters()

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        # (mode, A, fwhm)
        return f'({self.parameter[4]}, {self.parameter[3]}, {self.parameter[5]})'


class FitCountsRange(FitMethod):
    """
    Method to sum up counts from start to stop

    :param parent: parent widget
    """

    title = 'Counts (range)'
    tooltip = 'Counts in given range'

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'Counts'
            }, parent)
        self.parameter = [0]
        self.parameters = 0

        if not self.no_qt:
            self.bars = createFittingBars([
                'Start',
                'End'
            ])

        self.copy_info = '(counts)'

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], self.bars[1].value()))
        self.bars[1].setBounds((self.bars[0].value(), xrange[1]))

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        limit = np.logical_and(data[0] > bar_values[0], data[0] < bar_values[1])
        y_data_limit = data[1][limit]

        self.parameter = [np.sum(y_data_limit)]
        self.updateParameters()

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        # counts
        return f'{self.parameter[0]}'


class FitGaussCountsRange(FitMethod):
    """
    Method combining FitGaussRange and FitCountsRange

    :param parent: parent widget
    """

    title = 'Gauss & Count (range)'
    tooltip = 'Makes Gaussian fit in given range and also outputs counts'

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'σ',
                (0, 1): 'μ',
                (0, 2): 'c',
                (0, 3): 'FWHM',
                (0, 4): 'Counts'
            }, parent)
        self.parameter = [0.0, 0.0, 0.0, 0.0, 0]
        self.parameters = 3

        if not self.no_qt:
            self.bars = createFittingBars([
                'Start',
                'End'
            ])

        self.copy_info = '(mu, c, fwhm, counts)'

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], self.bars[1].value()))
        self.bars[1].setBounds((self.bars[0].value(), xrange[1]))

    @staticmethod
    def fitFunction(xdata, sigma: float, mu: float, c: float) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param sigma: sigma of gauss
        :param mu: mu of gauss
        :param c: c of gauss
        :return: y-values
        """

        return c * np.exp(-(xdata - mu) ** 2 / (2 * sigma ** 2))

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        limit = np.logical_and(data[0] > bar_values[0], data[0] < bar_values[1])
        x_data_limit = data[0][limit]
        y_data_limit = data[1][limit]

        if not len(x_data_limit):
            self.parent.writeStatusBar('Not enough datapoints in given range')
            return

        # self.parameter = [sigma, mu, c, FWHM, Counts]
        self.parameter[4] = np.sum(y_data_limit)

        if len(x_data_limit) < 4:
            self.parent.writeStatusBar('Not enough datapoints in given range (at least 4 needed)')
            return

        sigma0, mean0, c0 = estimateGauss(x_data_limit, y_data_limit)
        bounds = gaussBounds(x_data_limit, c0, (bar_values[0], bar_values[1]))
        p0 = clipToBounds([sigma0, mean0, c0], bounds)

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)[0]
            # self.parameter = [sigma, mu, c, FWHM, Counts]
            self.parameter[0] = float(popt[0])
            self.parameter[1] = float(popt[1])
            self.parameter[2] = float(popt[2])
            self.parameter[3] = 2 * np.sqrt(2 * np.log(2)) * popt[0]

        except (ValueError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting Gauss: {error}')
            GlobalConf.logger.info(f'Error in fitting Gauss (edge-bars): {error}')

        self.updateParameters()

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        # (mu, c, fwhm, counts)
        return f'({self.parameter[1]}, {self.parameter[2]}, {self.parameter[3]}, {self.parameter[4]})'


class FitBarsX(FitMethod):
    """
    Method to get x values of bars

    :param parent: parent widget
    """

    title = 'Bars (range)'
    tooltip = 'Get x values of bars'

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'x₁',
                (0, 1): 'x₂',
                (0, 2): '∆x'
            }, parent)
        self.parameter = [0.0, 0.0, 0.0]
        self.parameters = 0

        if not self.no_qt:
            self.bars = createFittingBars([
                'x₁',
                'x₂'
            ])

        self.copy_info = '(x₁, x₂, ∆x)'

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], self.bars[1].value()))
        self.bars[1].setBounds((self.bars[0].value(), xrange[1]))

    def fitting(self, bar_values: list[float], data: tuple[np.ndarray, np.ndarray], view_range: list[list[float, float]]):
        """
        Fitting function to determine parameters

        :param bar_values: values of bars
        :param data: x and y data as np.arrays
        :param view_range: ranges for visible field [[xmin, xmax], [ymin, ymax]]
        """

        # self.parameter = [x2, x1]
        self.parameter[0] = bar_values[0]
        self.parameter[1] = bar_values[1]
        self.parameter[2] = abs(bar_values[1] - bar_values[0])
        self.updateParameters()

    def copyParameters(self) -> str:
        """Returns string that will be copied when copy button is pressed"""

        # (x₁, x₂, ∆x)
        return f'({self.parameter[0]}, {self.parameter[1]}, {self.parameter[2]})'


fittingFunctionsSingle: list[type[FitMethod]] = [FitGaussRange, FitGaussCenter, FitLogNormRange, FitCountsRange, FitGaussCountsRange, FitBarsX]
fittingFunctionsMultiple: list[type[FitMethod]] = [FitBarsX]
