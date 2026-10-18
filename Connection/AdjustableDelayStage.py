from enum import Enum, auto


from Config.GlobalConf import GlobalConf

from Connection.USBPorts import COMConnection



class AdjustableDelayStage(COMConnection):
    """
    Context manager for Adjustable Delay Stage Serial connection, built on top of the COMConnection context manager

    :param comport: COM Port
    :param timeout: Timeout [in s]
    :param encoding: Encoding
    :param baudrate: Baudrate [in Bd/s]
    :param cleaning: If output cache should be cleared when entering and exiting
    :param strict: If identification string should contain <strict>-string
    """

    class MicrostepMode(Enum):
        FULL = 1
        HALF = 2
        QUARTER = 4
        EIGHTH = 8
        SIXTEENTH = 16

        @property
        def steps_per_rotation(self) -> int:
            return 200 * self.value

    class LimitSwitch(Enum):
        LOW = auto()
        HIGH = auto()

    def __init__(
        self,
        comport: str,
        timeout: float = 1,
        encoding: str = 'utf-8',
        baudrate: int = 115200,
        cleaning: bool = True,
        strict: str = ''
    ):
        self.strict = strict

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
        super().open()

        # detect if it is AdjustableDelayStage device
        identification = self.identification()
        if self.strict and self.strict not in identification:
            GlobalConf.logger.warning(f'<AdjustableDelayStage> on port "{self.comport}" does not identify with "{self.strict}". Identification is {identification!r}')
            raise ConnectionError(f'Device identification {identification!r} does not contain {self.strict!r}')

        return self

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

    def help(self) -> None:
        """Print the firmware command list"""
        self._queryAndReturn('HELP')

    def getMode(self) -> MicrostepMode:
        """Return the current microstepping mode"""
        return AdjustableDelayStage.MicrostepMode[self._queryAndReturn('STATUS MODE')]

    def getEnable(self) -> bool:
        """Return the current enabling status"""
        return self._queryAndReturnBool('STATUS ENABLE')

    def getSpeed(self) -> int:
        """Return the current speed [in 16th-steps/sec]"""
        return self._queryAndReturnInt('STATUS SPEED')

    def getAccel(self) -> int:
        """Return the current acceleration [in 16th-steps/sec²]"""
        return self._queryAndReturnInt('STATUS ACCEL')

    def getPos(self) -> int:
        """Return the current position [in 16th-steps]"""
        return self._queryAndReturnInt('STATUS POS')

    def getTarget(self) -> int:
        """Return the current target position [in 16th-steps]"""
        return self._queryAndReturnInt('STATUS TARGET')

    def getMoving(self) -> bool:
        """Return the current moving status"""
        return self._queryAndReturnBool('STATUS MOVING')

    def getLimit(self) -> list[LimitSwitch]:
        """Return what limit switch is hit"""
        res = self._queryAndReturnInt('STATUS LIMIT')
        limits = []
        if res & 1:
            limits.append(AdjustableDelayStage.LimitSwitch.LOW)
        if res & 2:
            limits.append(AdjustableDelayStage.LimitSwitch.HIGH)
        return limits

    def setMode(self, mode: MicrostepMode):
        """Sets the current microstepping mode"""
        self._queryAndReturn(f'MODE {mode.name}')

    def setEnable(self, enable: bool = True):
        """Sets the current enabling status"""
        self._queryAndReturn(f'ENABLE {int(enable)}')

    def setDisable(self, disable: bool = True):
        """Sets the current disabling status"""
        self.setEnable(not disable)

    def move(self, steps: int):
        """Sets the step count [in 16th-steps]. Sign dictates the direction"""
        self._queryAndReturn(f'MOVE {steps}')

    def moveZero(self):
        """Return to home position"""
        self._queryAndReturn('MOVE ZERO')

    def setSpeed(self, speed: int):
        """Sets the speed [in 16th-steps/sec]"""
        self._queryAndReturn(f'SPEED {speed}')

    def setAccel(self, accel: int):
        """Sets the acceleration [in 16th-steps/sec²]"""
        self._queryAndReturn(f'ACCEL {accel}')

    def halt(self):
        """Halts the motor immediately"""
        self._queryAndReturn('HALT')

    def setZero(self):
        """Sets current position as zero-position"""
        self._queryAndReturn('ZERO')


def main():
    from time import sleep

    with AdjustableDelayStage(
        comport='COM3',
        strict='AdjustableDelayStage by Alexander Redl'
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

        print('***** CHANGING MODE *****')
        print(f'{ads.setMode(AdjustableDelayStage.MicrostepMode.FULL) = }')

        print('***** ENABLE MOTOR *****')
        print(f'{ads.setEnable(True) = }')

        print('***** MOVE MOTOR *****')
        print(f'{ads.move(200) = }')
        sleep(1)
        print(f'{ads.moveZero() = }')


if __name__ == '__main__':
    main()
