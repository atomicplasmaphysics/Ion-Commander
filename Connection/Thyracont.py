from math import pow, log


from Connection.LucidControl import LucidControlConnection


def thyracontVoltageToPressure(voltage: float) -> float:
    """Convert voltage to pressure in mbar"""

    # check min range
    if voltage < 1.2:
        return 5E-10

    # check max range
    if voltage > 8.7:
        return 1000

    return pow(10, (voltage - 6.8) / 0.6)


def thyracontPressureToVoltage(pressure: float) -> float:
    """Convert pressure in mbar to voltage"""
    return 0.6 * log(pressure, 10) + 6.8


class ThyracontConnection(LucidControlConnection):
    def __init__(
        self,
        comport: str,
        timeout: float = 0.05,
        baudrate: int = 9600,
        channels: int = 4
    ):
        super().__init__(
            comport=comport,
            timeout=timeout,
            baudrate=baudrate,
            channels=channels
        )

    @staticmethod
    def voltageToPressure(voltage: float) -> float:
        """Convert voltage to pressure in mbar"""
        return thyracontVoltageToPressure(voltage)

    @staticmethod
    def pressureToVoltage(pressure: float) -> float:
        """Convert pressure in mbar to voltage"""
        return thyracontPressureToVoltage(pressure)

    def getPressure(self, channel: int) -> float:
        """Return pressure in mbar off one channel"""
        return self.voltageToPressure(self.ioGet(channel))

    def getPressureAll(self) -> tuple[float, ...]:
        """Return pressure in mbar off all channels"""
        return tuple([self.voltageToPressure(voltage) for voltage in self.ioGroupGet(tuple([True] * self.channels))])


def main():
    with ThyracontConnection('COM3') as thyracont:
        print(thyracont.ioGroupGet(tuple([True] * thyracont.channels)))
        print(thyracont.getPressureAll())


if __name__ == '__main__':
    main()
