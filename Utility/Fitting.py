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
supported_file_types = ['dat', 'cod', 'cod2']


def getTACFileData(filename: str, tac: int, delay: float = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts TAC-file (.dat) into x, y, y_max values

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
    Converts TDC-file (.cod) into x, y, y_max values

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


def getFileData(filename: str, tac: int = -1, delay: float = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts supported file into x, y

    :param filename: name of file (path)
    :param tac: (only required for .dat files) total TAC time in ns (50, 100, 200, ...)
    :param delay: (only required for .dat files) delay time before TAC signal in ns
    :return: x-array (in ns), y-array (counts)
    """

    filetype = filename.split('.')[-1]

    if filetype not in supported_file_types:
        raise ValueError(f'Not supported type of "{filetype}"!')

    if filetype == 'cod' or filetype == 'cod2':
        return getTDCFileData(filename)
    elif filetype == 'dat':
        return getTACFileData(filename, tac, delay)
    else:
        raise NotImplementedError(f'Not implemented type of "{filetype}"!')


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

        max_index = np.argmax(y_data_limit)
        mean0 = x_data_limit[max_index]
        c0 = y_data_limit[max_index]
        sigma0 = (x_data_limit[-1] - x_data_limit[0]) / 4

        limit0 = np.greater(y_data_limit, c0)
        if np.any(limit0):
            sigma0 = np.std(np.repeat(x_data_limit[limit0], y_data_limit[limit0]))

        p0 = [sigma0, mean0, c0]
        bounds = ([0, bar_values[0], 0], [bar_values[1] - bar_values[0], bar_values[1], c0 * 10])

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)
            # self.parameter = [sigma, mu, c, FWHM]
            self.parameter = [
                popt[0][0],
                popt[0][1],
                popt[0][2],
                2 * np.sqrt(2 * np.log(2)) * popt[0][0]
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

        # TODO: better limiting
        limit_distance = (view_range[0][1] - view_range[0][0]) * 0.1
        limit_x = (bar_values[0] - limit_distance, bar_values[0] + limit_distance)
        limit = np.logical_and(data[0] > limit_x[0], data[0] < limit_x[1])
        x_data_limit = data[0][limit]
        y_data_limit = data[1][limit]

        if not len(x_data_limit):
            self.parent.writeStatusBar('Not enough datapoints in given range')
            return

        if not x_data_limit[0] < bar_values[0] < x_data_limit[-1]:
            self.parent.writeStatusBar('Bar not in visible range')
            self.parameters = [0, 0, 0]
            return

        max_index = np.argmax(y_data_limit)
        mean0 = x_data_limit[max_index]
        c0 = y_data_limit[max_index]
        sigma0 = (view_range[0][1] - view_range[0][0]) / 16

        limit0 = np.greater(y_data_limit, c0)
        if np.any(limit0):
            sigma0 = np.std(np.repeat(x_data_limit[limit0], y_data_limit[limit0]))

        p0 = [sigma0, mean0, c0]
        bounds = ([0, limit_x[0], 0], [limit_x[1] - limit_x[0], limit_x[1], c0 * 10])

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)
            # self.parameter = [sigma, mu, c, FWHM]
            self.parameter = [
                popt[0][0],
                popt[0][1],
                popt[0][2],
                2 * np.sqrt(2 * np.log(2)) * popt[0][0]
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
    Method to log-norm-fit data from start to stop

    :param parent: parent widget
    """

    title = 'LogNorm (range)'
    tooltip = 'Makes LogNorm fit'

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if not self.no_qt:
            self.widget = FittingWidget({
                (0, 0): 'σ',
                (0, 1): 'μ',
                (0, 2): 'x0',
                (0, 3): 'c',
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
        :param sigma: sigma of log-norm
        :param mu: mu of log-norm
        :param x0: x0 of log-norm
        :param c: c of log-norm
        :return: y-values
        """

        xdata = (xdata - x0)
        ydata = c / (sigma * xdata * np.sqrt(2 * np.pi)) * np.exp(-np.square(np.log(xdata) - mu) / (2 * np.square(sigma)))
        return np.nan_to_num(ydata)

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

        max_index = np.argmax(y_data_limit)
        mean0 = 0
        x0 = x_data_limit[max_index]
        c0 = y_data_limit[max_index]
        sigma0 = (x_data_limit[-1] - x_data_limit[0]) / 4

        limit0 = np.greater(y_data_limit, c0)
        if np.any(limit0):
            sigma0 = np.std(np.repeat(x_data_limit[limit0], y_data_limit[limit0]))

        p0 = [sigma0, mean0, x0, c0]
        # TODO: better bounds for x0, mean0
        bounds = ([0, 0, bar_values[0], 0], [bar_values[1] - bar_values[0], bar_values[1], bar_values[1], c0 * 10])

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)
            # self.parameter = [sigma, mu, x0, c, mode, FWHM]
            self.parameter = [
                popt[0][0],
                popt[0][1],
                popt[0][2],
                popt[0][3],
                np.exp(popt[0][1] - np.square(popt[0][0])) + popt[0][2],
                np.exp(popt[0][1] - np.square(popt[0][0])) * (np.exp(np.sqrt(2 * np.log(2)) * popt[0][0]) - np.exp(-np.sqrt(2 * np.log(2)) * popt[0][0]))
            ]
            self.updateParameters()

        except (ValueError, TypeError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting LogNorm: {error}')
            GlobalConf.logger.info(f'Error in fitting LogNorm: {error}')


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

        max_index = np.argmax(y_data_limit)
        mean0 = x_data_limit[max_index]
        c0 = y_data_limit[max_index]
        sigma0 = (x_data_limit[-1] - x_data_limit[0]) / 4

        limit0 = np.greater(y_data_limit, c0)
        if np.any(limit0):
            sigma0 = np.std(np.repeat(x_data_limit[limit0], y_data_limit[limit0]))

        p0 = [sigma0, mean0, c0]
        bounds = ([0, bar_values[0], 0], [bar_values[1] - bar_values[0], bar_values[1], c0 * 10])

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0, bounds=bounds)
            # self.parameter = [sigma, mu, c, FWHM, Counts]
            self.parameter[0] = float(popt[0][0])
            self.parameter[1] = float(popt[0][1])
            self.parameter[2] = float(popt[0][2])
            self.parameter[3] = 2 * np.sqrt(2 * np.log(2)) * popt[0][0]

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
