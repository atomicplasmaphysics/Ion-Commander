from typing import Callable


from Connection.LucidControl import LucidControlConnection


class MixedPressureConnection(LucidControlConnection):
    def __init__(
        self,
        comport: str,
        voltage_to_pressure_fct: list[Callable[[float], float]],
        timeout: float = 0.05,
        baudrate: int = 9600,
        channels: int = 4
    ):
        if len(voltage_to_pressure_fct) != channels:
            raise ValueError(f'Length of voltage_to_pressure_fct({len(voltage_to_pressure_fct)}) and number of channels({channels}) do not match!')

        super().__init__(
            comport=comport,
            timeout=timeout,
            baudrate=baudrate,
            channels=channels
        )

        self.voltage_to_pressure_fct = voltage_to_pressure_fct

    def getPressure(self, channel: int | str) -> float:
        """Return pressure in mbar off one channel"""
        channel = int(channel)
        return self.voltage_to_pressure_fct[channel](self.ioGet(channel))

    def getPressureAll(self) -> tuple[float, ...]:
        """Return pressure in mbar off all channels"""
        return tuple([self.voltage_to_pressure_fct[channel](voltage) for channel, voltage in enumerate(self.ioGroupGet(tuple([True] * self.channels)))])


def main():
    from Connection.Thyracont import thyracontVoltageToPressure
    from Connection.TPG300 import tpg300VoltageToPressure, TPG300Type

    with MixedPressureConnection('COM3', [
        thyracontVoltageToPressure,
        thyracontVoltageToPressure,
        lambda voltage: tpg300VoltageToPressure(voltage, TPG300Type.Pirani),
        lambda voltage: 0
    ]) as mixed_pressure:
        print(mixed_pressure.getPressure(0))
        print(mixed_pressure.getPressure(1))
        print(mixed_pressure.getPressure(2))
        print(mixed_pressure.getPressure(3))
        print(mixed_pressure.getPressureAll())


if __name__ == '__main__':
    main()
