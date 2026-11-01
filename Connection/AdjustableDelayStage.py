from dataclasses import dataclass
from enum import Enum, auto
from time import monotonic


from serial import Serial


from Config.GlobalConf import GlobalConf, DefaultParams

from Connection.USBPorts import COMConnection


# speed of light in vacuum [in mm/ps]
SPEED_OF_LIGHT = 0.299792458

# identification of the firmware (Firmware/IR_delay_stage_A4988/IR_delay_stage_A4988.ino)
IDENTIFICATION = 'AdjustableDelayStage by Alexander Redl'

# full steps per rotation of the motor
FULL_STEPS_PER_ROTATION = 200


class MicrostepMode(Enum):
    """Microstepping modes, the value is the number of steps per full step. Which ones can be used depends on the driver"""

    FULL = 1
    HALF = 2
    QUARTER = 4
    EIGHTH = 8
    SIXTEENTH = 16

    @property
    def steps_per_rotation(self) -> int:
        return FULL_STEPS_PER_ROTATION * self.value


@dataclass(frozen=True)
class StepperDriver:
    """
    Driver board of the stepper motor and its firmware

    :param name: name of the driver
    :param modes: microstepping modes of the driver, from coarse to fine
    :param units_per_full_step: unit of position, speed and acceleration of the firmware in parts of a full step (the same in every mode)
    """

    name: str
    modes: tuple[MicrostepMode, ...]
    units_per_full_step: int = 16

    @property
    def units_per_rotation(self) -> int:
        """Position units per rotation of the motor"""
        return FULL_STEPS_PER_ROTATION * self.units_per_full_step

    def unitsPerStep(self, mode: MicrostepMode) -> int:
        """
        Returns the position units of one step

        :param mode: microstepping mode
        """

        return self.units_per_full_step // mode.value

    def positionToLength(self, position: float) -> float:
        """
        Returns the distance of the slide [in mm] of a position

        :param position: position [in position units]
        """

        return position * DefaultParams.delay_stage_lead / self.units_per_rotation

    def positionToTime(self, position: float) -> float:
        """
        Returns the delay [in ps] of a position

        :param position: position [in position units]
        """

        direction = -1 if DefaultParams.delay_stage_invert else 1
        return direction * self.positionToLength(position) * DefaultParams.delay_stage_path_factor / SPEED_OF_LIGHT

    def timeToPosition(self, time: float) -> int:
        """
        Returns the position [in position units] of a delay

        :param time: delay [in ps]
        """

        return round(time / self.positionToTime(1))


A4988 = StepperDriver('A4988', (MicrostepMode.FULL, MicrostepMode.HALF, MicrostepMode.QUARTER, MicrostepMode.EIGHTH, MicrostepMode.SIXTEENTH))


@dataclass
class DelayStageStatus:
    """
    Status of the delay stage

    :param position: position [in position units of the driver, 16th-steps for the A4988]
    :param moving: motor is moving
    :param enabled: motor is enabled
    :param limits: active limit switches
    """

    position: int
    moving: bool
    enabled: bool
    limits: list


class AdjustableDelayStage(COMConnection):
    """
    Context manager for Adjustable Delay Stage Serial connection, built on top of the COMConnection context manager

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param baudrate: Baudrate [in Bd/s]
    :param cleaning: If output cache should be cleared when entering and exiting
    :param strict: If identification string should contain <strict>-string
    :param startup_time: Time for answering after opening the port [in s], an Arduino may restart when the port is opened
    :param driver: Driver board of the motor, only its microstepping modes can be set
    """

    class LimitSwitch(Enum):
        """Limit switches: LIMIT1 blocks moves with positive steps, LIMIT2 moves with negative steps"""
        LIMIT1 = auto()
        LIMIT2 = auto()

    def __init__(
        self,
        comport: str,
        timeout: float = 0.3,
        encoding: str = 'utf-8',
        baudrate: int = 115200,
        cleaning: bool = True,
        strict: str = '',
        startup_time: float = 3,
        driver: StepperDriver = A4988
    ):
        self.driver = driver
        self.strict = strict
        self.startup_time = startup_time
        self.identified = False

        super().__init__(
            comport,
            timeout=timeout,
            encoding=encoding,
            baudrate=baudrate,
            tx_term='\r\n',
            echo=True,
            cleaning=cleaning
        )

    def open(self):
        """Opens the connection"""

        # without DTR the Arduino does not restart when the port is opened, it would lose its position
        if self.serial is None and self.comport != 'virtual':
            self.serial = Serial()
            self.serial.port = self.comport
            self.serial.baudrate = self.baudrate
            self.serial.timeout = self.timeout
            self.serial.dtr = False
            self.serial.rts = False
            self.serial.open()

        super().open()

        # detect if it is AdjustableDelayStage device (it does not answer yet if it restarted anyway)
        start_time = monotonic()
        while True:
            try:
                identification = self.identification()
                break
            except (ConnectionError, UnicodeDecodeError) as error:
                if monotonic() - start_time > self.startup_time:
                    raise ConnectionError(f'No answer of a delay stage on port "{self.comport}": {error}')

        if self.strict and self.strict not in identification:
            GlobalConf.logger.warning(f'<AdjustableDelayStage> on port "{self.comport}" does not identify with "{self.strict}". Identification is {identification!r}')
            raise ConnectionError(f'Device identification {identification!r} does not contain {self.strict!r}')

        self.identified = True
        return self

    def close(self):
        """Stops the motor, switches it off and closes the connection"""

        if self.serial is not None and self.identified:
            try:
                self.halt()
                self.setEnable(False)
            except (ConnectionError, OSError) as error:
                GlobalConf.logger.debug(f'<AdjustableDelayStage> could not stop the motor on closing: {error}')
        self.identified = False

        super().close()

    def _queryAndReturn(self, cmd: str) -> str:
        """Queries command and returns striped result"""
        self.write(cmd)
        return self.readline().strip()

    def _queryAndReturnInt(self, cmd: str) -> int:
        """Queries command and returns integer"""
        try:
            return int(self._queryAndReturn(cmd))
        except ValueError:
            return -1

    def _queryAndReturnBool(self, cmd: str) -> bool:
        """Queries command and returns boolean"""
        return bool(self._queryAndReturnInt(cmd))

    def identification(self) -> str:
        """Returns identification"""
        return self._queryAndReturn('IDN?')

    def help(self) -> str:
        """Returns the firmware command list"""
        self.write('HELP')
        lines = []
        while line := self.readline():
            lines.append(line.strip())
        return '\n'.join(lines)

    def getMode(self) -> MicrostepMode:
        """Return the current microstepping mode"""
        return MicrostepMode[self._queryAndReturn('STATUS MODE')]

    def getEnable(self) -> bool:
        """Return the current enabling status"""
        return self._queryAndReturnBool('STATUS ENABLE')

    def getSpeed(self) -> int:
        """Return the current speed [in position units of the driver/sec]"""
        return self._queryAndReturnInt('STATUS SPEED')

    def getAccel(self) -> int:
        """Return the current acceleration [in position units of the driver/sec²]"""
        return self._queryAndReturnInt('STATUS ACCEL')

    def getPos(self) -> int:
        """Return the current position [in position units of the driver]"""
        return self._queryAndReturnInt('STATUS POS')

    def getTarget(self) -> int:
        """Return the current target position [in position units of the driver]"""
        return self._queryAndReturnInt('STATUS TARGET')

    def getMoving(self) -> bool:
        """Return the current moving status"""
        return self._queryAndReturnBool('STATUS MOVING')

    def getLimit(self) -> list[LimitSwitch]:
        """
        Return what limit switch is active: the NC switch is activated or its wire is disconnected (not distinguishable).
        An invalid answer counts as both active, the same as both wires disconnected.
        """
        res = self._queryAndReturnInt('STATUS LIMIT')
        limits = []
        if res & 1:
            limits.append(AdjustableDelayStage.LimitSwitch.LIMIT1)
        if res & 2:
            limits.append(AdjustableDelayStage.LimitSwitch.LIMIT2)
        return limits

    def getZeroed(self) -> bool:
        """Return if the zero-position was set since the start of the Arduino (the position is lost on a restart)"""
        return self._queryAndReturnInt('STATUS ZEROED') == 1

    def getTime(self) -> float:
        """Return the current delay relative to the zero-position [in ps]"""
        return self.driver.positionToTime(self.getPos())

    def getStatus(self) -> DelayStageStatus:
        """Return position, moving status, enabling status and active limit switches"""
        return DelayStageStatus(self.getPos(), self.getMoving(), self.getEnable(), self.getLimit())

    def setMode(self, mode: MicrostepMode | str) -> str:
        """Sets the current microstepping mode (also as text for scripts, e.g. 'SIXTEENTH'), returns the answer ("OK" or "ERR ...")"""
        name = mode if isinstance(mode, str) else mode.name
        if name not in [driver_mode.name for driver_mode in self.driver.modes]:
            return f'ERR mode_{name}_not_available_on_{self.driver.name}'
        return self._queryAndReturn(f'MODE {name}')

    def setEnable(self, enable: bool = True) -> str:
        """Sets the current enabling status, returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn(f'ENABLE {int(enable)}')

    def setDisable(self, disable: bool = True) -> str:
        """Sets the current disabling status, returns the answer ("OK" or "ERR ...")"""
        return self.setEnable(not disable)

    def move(self, steps: int) -> str:
        """Moves by a step count [in steps of the current mode], sign dictates the direction. Returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn(f'MOVE {steps}')

    def moveZero(self) -> str:
        """Return to home position, returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn('MOVE ZERO')

    def moveTime(self, time: float) -> str:
        """Moves by a delay [in ps], rounded to steps of the current mode. Returns the answer ("OK" or "ERR ...")"""
        return self.move(round(self.driver.timeToPosition(time) / self.driver.unitsPerStep(self.getMode())))

    def moveToTime(self, time: float) -> str:
        """Moves to a delay relative to the zero-position [in ps], rounded to steps of the current mode. Returns the answer ("OK" or "ERR ...")"""
        return self.moveTime(time - self.getTime())

    def setSpeed(self, speed: int) -> str:
        """Sets the speed [in position units of the driver/sec], returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn(f'SPEED {speed}')

    def setAccel(self, accel: int) -> str:
        """Sets the acceleration [in position units of the driver/sec²], 0: no ramp. Returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn(f'ACCEL {accel}')

    def halt(self) -> str:
        """Halts the motor immediately, returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn('HALT')

    def setZero(self) -> str:
        """Sets current position as zero-position, returns the answer ("OK" or "ERR ...")"""
        return self._queryAndReturn('ZERO')


def main():
    from time import sleep

    with AdjustableDelayStage(
        comport='COM3',
        strict=IDENTIFICATION
    ) as ads:
        print('***** GENERAL VALUES *****')
        print(f'{ads.identification() = }')
        print('\n')

        print('***** STATUS PARAMETERS *****')
        print(f'{ads.getMode() = }')
        print(f'{ads.getEnable() = }')
        print(f'{ads.getSpeed() = }')
        print(f'{ads.getAccel() = }')
        print(f'{ads.getPos() = }')
        print(f'{ads.getTarget() = }')
        print(f'{ads.getMoving() = }')
        print(f'{ads.getLimit() = }')
        print(f'{ads.getZeroed() = }')

        print('***** CHANGING MODE *****')
        print(f'{ads.setMode(MicrostepMode.FULL) = }')

        print('***** ENABLE MOTOR *****')
        print(f'{ads.setEnable(True) = }')

        print('***** MOVE MOTOR *****')
        print(f'{ads.move(200) = }')
        sleep(1)
        print(f'{ads.moveZero() = }')


if __name__ == '__main__':
    main()
