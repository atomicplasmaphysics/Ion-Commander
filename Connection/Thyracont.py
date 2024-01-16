from math import pow, log


from Connection.LucidControl import LucidControlConnection


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
        return pow(10, (voltage - 6.8) / 0.6)

    @staticmethod
    def pressureToVoltage(pressure: float) -> float:
        """Convert pressure in mbar to voltage"""
        return 0.6 * log(pressure, 10) + 6.8

    def getTemperature(self, channel: int) -> float:
        """Return pressure in mbar off one channel"""
        return self.voltageToPressure(self.ioGet(channel))

    def getTemperatureAll(self) -> tuple[float, ...]:
        """Return pressure in mbar off all channels"""
        voltages = self.ioGroupGet(tuple([True] * self.channels))
        pressure = []
        for voltage in voltages:
            if 1.2 < voltage < 8.7:
                pressure.append(self.voltageToPressure(voltage))
            else:
                pressure.append(0)
        return tuple(pressure)


def main():
    with ThyracontConnection('COM3') as thyracont:
        print(thyracont.getTemperatureAll())


if __name__ == '__main__':
    main()
