import numpy as np


class CyclicList(list):
    """Cyclic list"""

    def __getitem__(self, index):
        if not len(self):
            raise IndexError(f'Cannot access elements in an empty list')
        return super().__getitem__(index % len(self))


def getPrefix(number: float | int, use_latex: bool = False) -> tuple[float | int, str]:
    """
    Gets the prefix of a number and returns the converted number and the prefix

    :param number: input number
    :param use_latex: use latex prefixes
    :return: tuple of converted number and prefix
    """

    if not isinstance(number, float) and not isinstance(number, int):
        raise ValueError(f'Provided argument is of type {type(number)} not <float> or <int>')

    prefixes = ['Z', 'E', 'P', 'T', 'G', 'M', 'k', '', 'm', 'μ', 'n', 'p', 'f', 'a', 'z', 'y']
    if use_latex:
        prefixes = ['Z', 'E', 'P', 'T', 'G', 'M', 'k', '', 'm', r'\mu', 'n', 'p', 'f', 'a', 'z', 'y']
    #          [21,  18,  15,  12,   9,   6,    3,  0,  -3,  -6,  -9, -12, -15, -18, -21, -24]
    exponent = int(f'{number:.1E}'.split('E')[1]) + 1

    for i, prefix in enumerate(prefixes):
        prefix_exponent = (21 - i * 3)
        if exponent > prefix_exponent:
            return number / (10 ** prefix_exponent), prefix

    return number, ''


def getSignificantDigits(number: float, digits: int = 3) -> float:
    """
    Rounds number to amount of significant digits

    :param number: input number
    :param digits: number of significant digits
    :return: input number cut off at significant digits
    """

    return float(f'{number:.{digits}G}')


def getIntIfInt(number: float) -> float | int:
    """
    Returns an integer if number can be converted into an integer without loss, otherwise the number will be returned

    :param number: input number
    :return: input number converted into integer or input number
    """

    if int(number) == number:
        return int(number)
    return number


def mergeArraysFirstColumn(arrays: list[np.ndarray], missing_value: float = np.nan):
    """
    Merge numpy arrays in one, where first column will be the same (only integer steps)

    :param arrays: list of numpy arrays to merge
    :param missing_value: default replacement for missing values
    """

    min_x = int(min(arr[:, 0].min() for arr in arrays))
    max_x = int(max(arr[:, 0].max() for arr in arrays))
    x_range = np.arange(min_x, max_x + 1)

    result = np.full((len(x_range), sum(arr.shape[1] - 1 for arr in arrays) + 1), missing_value)
    result[:, 0] = x_range

    offset = 1
    for array in arrays:
        result[(array[:, 0] - min_x).astype(int), offset:offset + array.shape[1] - 1] = array[:, 1:]
        offset += array.shape[1] - 1

    return result


def assertionTests():
    def getPrefixTest():
        assert getPrefix(1E-24) == (1, 'y')
        assert getPrefix(1E-21) == (1, 'z')
        assert getPrefix(1E-18) == (1, 'a')
        assert getPrefix(1E-15) == (1, 'f')
        assert getPrefix(1E-12) == (1, 'p')
        assert getPrefix(1E-9) == (1, 'n')
        assert getPrefix(1E-6) == (1, 'μ')
        assert getPrefix(1E-3) == (1, 'm')
        assert getPrefix(1E0) == (1, '')
        assert getPrefix(1E3) == (1, 'k')
        assert getPrefix(1E6) == (1, 'M')
        assert getPrefix(1E9) == (1, 'G')
        assert getPrefix(1E12) == (1, 'T')
        assert getPrefix(1E15) == (1, 'P')
        assert getPrefix(1E18) == (1, 'E')
        assert getPrefix(1E21) == (1, 'Z')
        assert getPrefix(2200) == (2.2, 'k')
        assert getPrefix(123456789) == (123.456789, 'M')

    def getSignificantDigitsTest():
        assert getSignificantDigits(10/9) == 1.11
        assert getSignificantDigits(10/8) == 1.25
        assert getSignificantDigits(10/7) == 1.43
        assert getSignificantDigits(10/6) == 1.67
        assert getSignificantDigits(10/5) == 2
        assert getSignificantDigits(10/4) == 2.5
        assert getSignificantDigits(10/3) == 3.33
        assert getSignificantDigits(10/2) == 5

        assert getSignificantDigits(10/9, digits=5) == 1.1111
        assert getSignificantDigits(10/8, digits=5) == 1.25
        assert getSignificantDigits(10/7, digits=5) == 1.4286
        assert getSignificantDigits(10/6, digits=5) == 1.6667
        assert getSignificantDigits(10/5, digits=5) == 2
        assert getSignificantDigits(10/4, digits=5) == 2.5
        assert getSignificantDigits(10/3, digits=5) == 3.3333
        assert getSignificantDigits(10/2, digits=5) == 5

    def getIntIfIntTest():
        assert getIntIfInt(1.0) == 1
        assert getIntIfInt(111.0) == 111
        assert getIntIfInt(1.1) == 1.1
        assert getIntIfInt(111.1) == 111.1

    getPrefixTest()
    getSignificantDigitsTest()
    getIntIfIntTest()


if __name__ == '__main__':
    assertionTests()
