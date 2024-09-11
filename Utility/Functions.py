from colorsys import rgb_to_hls, hls_to_rgb


from PyQt6.QtGui import QColor
from PyQt6.QtCore import QFileInfo
from PyQt6.QtWidgets import QFileDialog


def selectFileDialog(
    parent,
    for_saving: bool,
    instruction: str,
    start_dir: str,
    file_filter: str = '',
    multiple: bool = False
) -> None | str | list[str]:
    """
    Dialog window for selecting a file

    :param parent: parent widget
    :param for_saving: save (True) or open (False)
    :param instruction: instruction text
    :param start_dir: starting directory
    :param file_filter: (optional) filter for allowed files
    :param multiple: (optional) multiple files allowed

    :return: path as string (one file) or list of strings (multiple files) or None (no files)
    """

    full_file_paths = []

    if for_saving:
        full_file_path, _ = QFileDialog.getSaveFileName(parent, instruction, start_dir, file_filter)
        full_file_paths.append(full_file_path)

    else:
        if multiple:
            full_file_paths, _ = QFileDialog.getOpenFileNames(parent, instruction, start_dir, file_filter)

        else:
            full_file_path, _ = QFileDialog.getOpenFileName(parent, instruction, start_dir, file_filter)
            full_file_paths.append(full_file_path)

    file_names = []

    for full_file_path in full_file_paths:
        file_names.append(QFileInfo(full_file_path).filePath())
    if len(file_names) == 0:
        return None
    if len(file_names) == 1 and not multiple:
        return file_names[0]
    else:
        return file_names


def hexToRgb(code: str) -> tuple[int, int, int]:
    """
    Converts hex code into tuple of rgb

    :param code: hex code
    :return: (r, g, b)
    """

    color = code.lstrip('#')
    return int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16)


def rgbToHex(red: int, green: int, blue: int) -> str:
    """
    Converts tuple of rgb into hex code

    :param red: value of red
    :param green: value of green
    :param blue: value of blue
    :return: hex code
    """

    return f'#{red:02x}{green:02x}{blue:02x}'


def qColorToHex(color: QColor) -> str:
    """
    Converts QColor into hex code

    :param color: QColor
    :return: hex code
    """

    return f'#{color.red():02x}{color.green():02x}{color.blue():02x}'


def brightingColor(color: str) -> str:
    """
    Makes color brighter

    :param color: input color
    :return: brighter color
    """

    r, g, b = hexToRgb(color)

    def normalise(x: float) -> float:
        return x / 255.0

    def deNormalise(x: float) -> int:
        return int(x * 255.0)

    (h, l, s) = rgb_to_hls(normalise(r), normalise(g), normalise(b))
    (nr, ng, nb) = hls_to_rgb(h, l * 1.5, s)

    return rgbToHex(deNormalise(nr), deNormalise(ng), deNormalise(nb))


def linearInterpolateColor(start: QColor, end: QColor, percentage: float) -> QColor:
    """
    Interpolates a color between start color and end color

    :param start: start color
    :param end: end color
    :param percentage: percentage from start (0) to end (1)
    :return: middle
    """

    if not 0 <= percentage <= 1:
        raise ValueError('percentage should be in range [0, 1]')

    return QColor(
        int(start.red() * (1 - percentage) + percentage * end.red()),
        int(start.green() * (1 - percentage) + percentage * end.green()),
        int(start.blue() * (1 - percentage) + percentage * end.blue())
    )


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
