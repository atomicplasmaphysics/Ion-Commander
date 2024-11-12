from enum import Enum

import numpy as np

from Connection.LucidControl import LucidControlConnection


class TPG300TypeTuple(tuple):
    def __new__(cls, voltage, pressure):
        return super().__new__(cls, (voltage, pressure))

    def __eq__(self, other):
        if not isinstance(other, TPG300TypeTuple):
            return NotImplemented
        return np.array_equal(self[0], other[0]) and np.array_equal(self[1], other[1])

    def __hash__(self):
        return hash((self[0].tobytes(), self[1].tobytes()))


class TPG300Type(Enum):
    Pirani = TPG300TypeTuple(
        np.array([
            0.02962962962962985,
            0.059259259259259275,
            0.16296296296296334,
            0.37037037037037057,
            0.6074074074074077,
            0.8888888888888892,
            1.1259259259259258,
            2,
            2.4888888888888885,
            2.8592592592592587,
            3.155555555555555,
            3.5259259259259257,
            4.192592592592591,
            4.785185185185186,
            5.17037037037037,
            5.481481481481482,
            5.7185185185185174,
            6.237037037037036,
            6.8,
            7.422222222222222,
            7.851851851851851,
            8.192592592592591,
            9.007407407407406,
            9.466666666666667,
            9.644444444444446,
            9.73333333333333,
            9.792592592592591,
            9.896296296296294,
            9.955555555555554,
            10
        ]),
        np.array([
            0.0006222298630985855,
            0.0010131437683304654,
            0.0020418268175934097,
            0.003991482371169771,
            0.006114900771473868,
            0.008293055193029742,
            0.010264602953068568,
            0.02006584563450912,
            0.04043945490751564,
            0.06195273610577905,
            0.0790534094136901,
            0.10399518516287912,
            0.20958541581523885,
            0.40970981734230366,
            0.6088342207196876,
            0.8257036351902484,
            1.0220021180200143,
            2.059679383558003,
            4.1509494826416775,
            6.168365966684872,
            8.114518597179018,
            10.354350770925143,
            21.51311078097202,
            40.79303437375055,
            60.61898993497572,
            82.21173949733593,
            101.75633037273475,
            205.07336738330955,
            400.8894014193037,
            543.6879610181503
        ])
    )

    ColdCathod = TPG300TypeTuple(
        np.array([
            0,
            0.02249718785151856,
            0.23622047244094488,
            0.47244094488188976,
            0.7199100112485939,
            1.001124859392576,
            1.4060742407199098,
            1.8672665916760405,
            2.1822272215973,
            2.5084364454443193,
            2.9021372328458943,
            3.3183352080989876,
            3.7570303712035993,
            4.094488188976378,
            4.4206974128233965,
            4.758155230596175,
            5.174353205849268,
            5.568053993250843,
            5.961754780652418,
            6.287964004499437,
            6.591676040494938,
            6.929133858267716,
            7.300337457817772,
            7.637795275590551,
            7.941507311586052,
            8.222722159730033,
            8.571428571428571,
            8.920134983127108,
            9.20134983127109,
            9.437570303712036,
            9.640044994375703,
            9.83127109111361,
            10
        ]),
        np.array([
            3.9917605636037305e-9,
            5.1670896545795e-9,
            8.657829416541583e-9,
            1.4170423304950787e-8,
            2.1616677204297902e-8,
            4.0728471122364385e-8,
            6.511524490330894e-8,
            1.041039597602197e-7,
            1.8281369794495676e-7,
            2.992144290662471e-7,
            4.5644520200985057e-7,
            6.192251929928391e-7,
            8.599987432529078e-7,
            0.000001546067780929117,
            0.00000319959208856828,
            0.000004996776867506682,
            0.000007104416009727966,
            0.000010101056776718584,
            0.00001540894573617466,
            0.000027059166221453183,
            0.000044288218350019794,
            0.0000659940975842446,
            0.00010306244392187128,
            0.00014653415511939585,
            0.00019418228488130753,
            0.00026968625122110316,
            0.0003745484514313345,
            0.0005849292616265948,
            0.0009351642983969761,
            0.0014604384572156712,
            0.00244706941067378,
            0.0048320777715791016,
            0.01
        ])
    )


def tpg300VoltageToPressure(voltage: float, sensor_type: TPG300Type) -> float:
    """Convert voltage to pressure in mbar"""
    return float(np.interp(voltage, sensor_type.value[0], sensor_type.value[1]))


def tpg300PressureToVoltage(pressure: float, sensor_type: TPG300Type) -> float:
    """Returns an interpolated pressure based on the given voltage input."""
    return float(np.interp(pressure, sensor_type.value[1], sensor_type.value[2]))


class TPG300Connection(LucidControlConnection):
    def __init__(
        self,
        comport: str,
        sensor_type: TPG300Type,
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
        self.sensor_type = sensor_type

    def voltageToPressure(self, voltage: float | str) -> float:
        """Convert voltage to pressure in mbar"""
        return tpg300VoltageToPressure(float(voltage), self.sensor_type)

    def pressureToVoltage(self, pressure: float | str) -> float:
        """Returns an interpolated pressure based on the given voltage input."""
        return tpg300PressureToVoltage(float(pressure), self.sensor_type)

    def getPressure(self, channel: int | str) -> float:
        """Return pressure in mbar off one channel"""
        return self.voltageToPressure(self.ioGet(int(channel)))

    def getPressureAll(self) -> tuple[float, ...]:
        """Return pressure in mbar off all channels"""
        return tuple([self.voltageToPressure(voltage) for voltage in self.ioGroupGet(tuple([True] * self.channels))])


def main():
    with TPG300Connection('COM3', TPG300Type.Pirani) as tpg300:
        print(tpg300.getPressureAll())


if __name__ == '__main__':
    main()
