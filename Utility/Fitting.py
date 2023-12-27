from typing import TYPE_CHECKING
from warnings import simplefilter


import numpy as np

from scipy.optimize import curve_fit, OptimizeWarning
from scipy.stats import lognorm, gausshyper

import pyqtgraph as pg


if TYPE_CHECKING:
    from Windows.Main import MainWindow

from Utility.Layouts import createFittingBars, FittingWidget


simplefilter('ignore', OptimizeWarning)
simplefilter('ignore', RuntimeWarning)


def getTACFileData(filename: str, tac: int, delay: float = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts TAC-file (.dat) into x, y, y_max values

    :param filename: filename of TAC file
    :param tac: total TAC time in ns (50, 100, 200, ...)
    :param delay: delay time before TAC signal in ns
    :return: x-array (in ns), y-array (counts)
    """

    x = np.linspace(delay, tac + delay, 8192)

    with open(filename, 'r') as file:
        y = [float(line) for line in file.readlines()]

    return x, np.array(y)


def getTDCFileData(filename: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts TDC-file (.cod) into x, y, y_max values

    :param filename: filename of TDC file
    :return: x-array (in ns), y-array (counts)
    """

    x = []
    y = []

    with open(filename, 'r') as file:
        for line in file.readlines():
            xi, yi = [float(s) for s in line.strip().split(',')]
            x.append(xi)
            y.append(yi)

    return np.array(x), np.array(y)


def getFileData(filename: str, tac: int = -1, delay: float = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Converts supported file into x, y

    :param filename: name of file (path)
    :param tac: (only required for .dat files) total TAC time in ns (50, 100, 200, ...)
    :param delay: (only required for .dat files) delay time before TAC signal in ns
    :return: x-array (in ns), y-array (counts)
    """

    filetype = filename.split('.')[-1]

    if filetype == 'cod':
        return getTDCFileData(filename)
    elif filetype == 'dat':
        return getTACFileData(filename, tac, delay)
    else:
        raise ValueError(f'Not supported type of "{filetype}"!')


class FitMethod:
    """
    General method to fit data

    :param parent: parent widget
    """

    title = 'No fit'
    tooltip = 'No fit at all'

    def __init__(self, parent):
        self.parent: MainWindow = parent
        self.widget = FittingWidget({}, parent)
        self.parameters = []
        self.bars: list[pg.InfiniteLine] = []

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
    def fitFunction(xdata: np.ndarray, *args) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param args: arguments for fitting function
        :return: y-values
        """

        return np.zeros(xdata.shape)

    def updateParameters(self):
        """Updates parameters"""
        self.widget.setValues(self.parameters)


class FitGaussRange(FitMethod):
    """
    Method to gauss-fit data from start to stop

    :param parent: parent widget
    """

    title = 'Gauss (range)'
    tooltip = 'Makes Gaussian fit in given range'

    def __init__(self, parent):
        super().__init__(parent)

        self.widget = FittingWidget({
            (0, 0): 'σ',
            (0, 1): 'μ',
            (0, 2): 'c'
        }, parent)
        self.parameters = [0, 0, 0]

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
    def fitFunction(xdata: np.ndarray, sigma: float, mu: float, c: float) -> np.ndarray:
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
        # TODO: better first approximation for sigma
        p0 = [(x_data_limit[-1] - x_data_limit[0]) / 4, x_data_limit[max_index], y_data_limit[max_index]]

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0)
            self.parameters = [abs(popt[0][0]), popt[0][1], popt[0][2]]
            self.updateParameters()

        except (ValueError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting Gauss: {error}')


class FitGaussCenter(FitMethod):
    """
    Method to gauss-fit data from start to stop

    :param parent: parent widget
    """

    title = 'Gauss (center)'
    tooltip = 'Makes Gaussian fit with provided center'

    def __init__(self, parent):
        super().__init__(parent)

        self.widget = FittingWidget({
            (0, 0): 'σ',
            (0, 1): 'μ',
            (0, 2): 'c'
        }, parent)
        self.parameters = [0, 0, 0]

        self.bars = createFittingBars([
            'Center'
        ])

    def setBarBounds(self, xrange: tuple[float, float]):
        """
        Sets boundary of bars

        :param xrange: tuple of xmin, xmax
        """

        self.bars[0].setBounds((xrange[0], xrange[1]))

    @staticmethod
    def fitFunction(xdata: np.ndarray, sigma: float, mu: float, c: float) -> np.ndarray:
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
        view_width = view_range[0][1] - view_range[0][0]
        limit = np.logical_and(data[0] > bar_values[0] - view_width * 0.1, data[0] < bar_values[0] + view_width * 0.1)
        x_data_limit = data[0][limit]
        y_data_limit = data[1][limit]

        if not len(x_data_limit):
            self.parent.writeStatusBar('Not enough datapoints in given range')
            return

        if not x_data_limit[0] < bar_values[0] < x_data_limit[-1]:
            self.parent.writeStatusBar('Bar not in visible range')
            self.parameters = [0, 0, 0]
            return

        max_index = (np.abs(x_data_limit - bar_values[0])).argmin()
        # TODO: better first approximation for sigma
        p0 = [(view_range[0][1] - view_range[0][0]) / 16, x_data_limit[max_index], y_data_limit[max_index]]

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0)
            self.parameters = [abs(popt[0][0]), popt[0][1], popt[0][2]]
            self.updateParameters()

        except (ValueError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting Gauss: {error}')


class FitLogNormRange(FitMethod):
    """
    Method to log-norm-fit data from start to stop

    :param parent: parent widget
    """

    title = 'LogNorm'
    tooltip = 'Makes LogNorm fit'

    def __init__(self, parent):
        super().__init__(parent)

        self.widget = FittingWidget({
            (0, 0): 'σ',
            (0, 1): 'μ',
            (0, 2): 'c'
        }, parent)
        self.parameters = [0, 0, 0]

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
    def fitFunction(xdata: np.ndarray, sigma: float, mu: float, c: float) -> np.ndarray:
        """
        Fitting function

        :param xdata: x-values for function
        :param sigma: sigma of log-norm
        :param mu: mu of log-norm
        :param c: c of log-norm
        :return: y-values
        """

        xdata = (xdata - mu) / c
        return 1. / (sigma * xdata * np.sqrt(2 * np.pi)) * np.exp(-np.square(np.log(xdata)) / (2 * np.square(sigma)))

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
        # TODO: better first approximation for sigma
        p0 = [(x_data_limit[-1] - x_data_limit[0]) / 4, x_data_limit[max_index], y_data_limit[max_index]]

        try:
            popt = curve_fit(self.fitFunction, x_data_limit, y_data_limit, p0=p0)
            self.parameters = [abs(popt[0][0]), popt[0][1], popt[0][2]]
            self.updateParameters()

        except (ValueError, TypeError, RuntimeError) as error:
            self.parent.writeStatusBar(f'Error in fitting Gauss: {error}')


fittingFunctions: list[type[FitMethod]] = [FitMethod, FitGaussRange, FitGaussCenter, FitLogNormRange]
