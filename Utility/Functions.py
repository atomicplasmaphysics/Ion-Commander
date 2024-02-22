from colorsys import rgb_to_hls, hls_to_rgb


from PyQt6.QtGui import QColor


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


def getPrefix(number: float | int) -> tuple[float | int, str]:
    """
    Gets the prefix of a number and returns the converted number and the prefix

    :param number: input number
    :return: tuple of converted number and prefix
    """

    if not isinstance(number, float) and not isinstance(number, int):
        raise ValueError(f'Provided argument is of type {type(number)} not <float> or <int>')

    prefixes = ['Z', 'E', 'P', 'T', 'G', 'M', 'k', '', 'm', 'μ', 'n', 'p', 'f', 'a', 'z', 'y']
    # [21, 18, 15, 12, 9, 6, 3, 0, -3, -6, -9, -12, -15, -18, -21, -24]
    exponent = int(f'{number:.1E}'.split('E')[1]) + 1

    for i, prefix in enumerate(prefixes):
        prefix_exponent = (21 - i * 3)
        if exponent > prefix_exponent:
            return number / (10 ** prefix_exponent), prefix

    return number, ''
