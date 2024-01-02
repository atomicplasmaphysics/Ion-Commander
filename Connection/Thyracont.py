from math import pow, log


from Connection.LucidControl import LucidControl


class Thyracont(LucidControl):
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
    def voltage_to_pressure(voltage: float) -> float:
        """Convert voltage to pressure in mbar"""
        return pow(10, (voltage - 6.8) / 0.6)

    @staticmethod
    def pressure_to_voltage(pressure: float) -> float:
        """Convert pressure in mbar to voltage"""
        return 0.6 * log(pressure, 10) + 6.8

    def get_temperature(self, channel: int) -> float:
        """Return pressure in mbar off one channel"""
        return self.voltage_to_pressure(self.io_get(channel))

    def get_temperature_all(self) -> tuple[float, ...]:
        """Return pressure in mbar off all channels"""
        voltages = self.io_group_get(tuple([True] * self.channels))
        pressure = []
        for voltage in voltages:
            if 1.2 < voltage < 8.7:
                pressure.append(self.voltage_to_pressure(voltage))
            else:
                pressure.append(0)
        return tuple(pressure)


def main():
    with Thyracont('COM3') as thyracont:
        print(thyracont.get_temperature_all())


if __name__ == '__main__':
    main()
