from typing import Callable


from PyQt6.QtCore import QObject, QTimer


from Config.GlobalConf import GlobalConf, DefaultParams


class EventLog:
    """
    Global sink for events (e.g. lost connections), so widgets without access to the database can log events.
    The main window sets <sink> to <DB.insertEvent>.
    """

    sink: Callable[[str, str, str, float], None] | None = None

    @staticmethod
    def log(source: str, event_type: str, message: str = '', value: float = 0.):
        """
        Logs an event to the database (if a sink is set)

        :param source: source of event (e.g. "PSU")
        :param event_type: type of event (e.g. "connection_lost")
        :param message: human readable message
        :param value: optional value
        """

        if EventLog.sink is None:
            return
        try:
            EventLog.sink(source, event_type, message, value)
        except Exception as error:
            GlobalConf.logger.error(f'Could not log event ({source}, {event_type}, {message}): {error}')


class AutoReconnect(QObject):
    """
    Tries to reconnect a device periodically after its connection was lost.
    Is stopped by a successful reconnect or by <stop> (e.g. when the user connects/disconnects manually).

    :param name: name of the device (for logging)
    :param reconnect_function: function that tries to connect silently and returns True if connected
    :param interval: time between attempts in ms
    """

    def __init__(self, name: str, reconnect_function: Callable[[], bool], interval: int = DefaultParams.reconnect_interval_time):
        super().__init__()
        self.name = name
        self.reconnect_function = reconnect_function
        self.attempts = 0
        self.in_attempt = False

        self.timer = QTimer()
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.attempt)

    @property
    def active(self) -> bool:
        """Returns if reconnecting is active"""
        return self.timer.isActive() or self.in_attempt

    def start(self):
        """Starts reconnecting (called when the connection was lost)"""

        if self.active:
            return

        self.attempts = 0
        GlobalConf.logger.warning(f'{self.name}: Connection lost, will try to reconnect every {self.timer.interval() / 1000:g} s')
        EventLog.log(self.name, 'connection_lost', 'Connection lost, trying to reconnect')
        self.timer.start()

    def stop(self):
        """Stops reconnecting (ignored while an attempt is running, because the attempt itself connects)"""

        if self.in_attempt:
            return
        self.timer.stop()

    def attempt(self):
        """One reconnect attempt"""

        self.timer.stop()
        self.attempts += 1
        self.in_attempt = True
        try:
            connected = self.reconnect_function()
        except Exception as error:
            GlobalConf.logger.error(f'{self.name}: Reconnect attempt {self.attempts} failed with error: {error}')
            connected = False
        finally:
            self.in_attempt = False

        if connected:
            GlobalConf.logger.info(f'{self.name}: Reconnected after {self.attempts} attempt{"" if self.attempts == 1 else "s"}')
            EventLog.log(self.name, 'reconnected', f'Reconnected after {self.attempts} attempts', self.attempts)
            return

        # do not flood the log
        if self.attempts == 1 or self.attempts % 10 == 0:
            GlobalConf.logger.info(f'{self.name}: Reconnect attempt {self.attempts} failed, will try again')
        self.timer.start()
