from colorsys import rgb_to_hls, hls_to_rgb


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
