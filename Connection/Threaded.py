from typing import TYPE_CHECKING
from time import sleep


from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool


from Config.GlobalConf import GlobalConf

from Connection.ISEG import ISEGConnection
from Connection.TPG300 import TPG300Connection
from Connection.Thyracont import ThyracontConnection
from Connection.MixedPressure import MixedPressureConnection
from Connection.Monaco import MonacoConnection
from Connection.TLPMx import TLPMxConnection


if TYPE_CHECKING:
    base_iseg = ISEGConnection
    base_thyracont = ThyracontConnection
    base_tpg300 = TPG300Connection
    base_mixedpressure = MixedPressureConnection
    base_monaco = MonacoConnection
    base_tlpmx = TLPMxConnection
else:
    base_iseg = object
    base_thyracont = object
    base_tpg300 = object
    base_mixedpressure = object
    base_monaco = object
    base_tlpmx = object


class CallbackId:
    """
    Class that increased itself everytime it is called
    """

    def __init__(self):
        self.id = 0

    def increment(self):
        """Increments itself by one"""
        self.id += 1

    def __call__(self) -> int:
        """Executed when instance of class is run"""
        self.increment()
        return self.id


class ConnectionWorkerSignals(QObject):
    """
    Signals for connection worker

    error: any occurring error
    result: callback_id, result
    """

    error = pyqtSignal(int, Exception)
    result = pyqtSignal(int, object)


class ConnectionWorker(QRunnable):
    """
    Threaded worker for handling a connection without lagging the input panel

    :param connection: any connection class
    """

    max_queue = 100

    def __init__(self, connection):
        super().__init__()
        self.connection: ISEGConnection | ThyracontConnection | MonacoConnection | TLPMxConnection = connection
        self.signal = ConnectionWorkerSignals()
        self.running = True
        self.started = False
        self.work = []

    @pyqtSlot()
    def run(self):
        """Called when worker is started"""

        self.started = True

        while True:
            if not self.running:
                break

            if not self.work:
                sleep(0.1)
                continue

            callback_id, name, args, kwargs = self.work.pop(0)

            try:
                obj_func = getattr(self.connection, name)
                result = obj_func(*args, **kwargs)
                self.signal.result.emit(callback_id, result)
            except (AttributeError, ConnectionError, NameError, TypeError, ValueError) as error:
                self.signal.error.emit(callback_id, error)

            if name == 'close':
                self.running = False
                self.work = []

    def execute(self, callback_id: int, name, *args, **kwargs):
        """
        Adds function call to connection

        :param callback_id: unique id of callback
        :param name: function name
        """

        if name == 'close':
            self.work.insert(0, (callback_id, name, args, kwargs))
            return callback_id

        if len(self.work) > self.max_queue:
            self.signal.error.emit(-1, BufferError('Too many tasks in queue'))
            return -1

        if not self.running:
            self.signal.error.emit(-1, ChildProcessError('Not running'))
            return -1

        self.work.append((callback_id, name, args, kwargs))
        return callback_id


class ThreadedConnection:
    """
    Baseclass for threaded connections

    :param connection: Connection class
    """

    def __init__(
        self,
        connection: ISEGConnection | ThyracontConnection | TPG300Connection | MixedPressureConnection | MonacoConnection | TLPMxConnection | None
    ):
        self.connection = connection

        self.worker = ConnectionWorker(connection)
        self.worker.signal.error.connect(self.error)
        self.worker.signal.result.connect(self.executeCallback)

        self.threadpool = QThreadPool.globalInstance()
        if self.connection is not None:
            self.threadpool.start(self.worker)

        self.callback_id = CallbackId()
        self.callbacks = {}

    def isDummy(self) -> bool:
        """Returns if it is a dummy <ThreadedConnection>"""

        return self.connection is None

    def error(self, callback_id: int, error: Exception):
        """
        Called when an exception in the worker thread occurs

        :param callback_id: unique id for which the callback will be performed on
        :param error: exception that occurred
        """

        # TODO: maybe just close connection on ConnectionError (e.g. Laser: [WinError 10054] Eine vorhandene Verbindung wurde vom Remotehost geschlossen)
        GlobalConf.logger.exception(error)

        function = self.callbacks.get(callback_id)
        if function is None:
            return

        try:
            function(error)
        except (ValueError, AttributeError):
            pass

        del self.callbacks[callback_id]

    def callback(self, function, callback_id):
        """
        Calls function when second statement finishes

        :param function: function to be executed
        :param callback_id: every call of this class will be passed to the worker and return a unique id, which should be passed here
        """

        if self.connection is None:
            raise NotImplementedError('There should not be a callback happening')

        if not isinstance(callback_id, int):
            raise ValueError(f'Callback id must be <int>, received {type(callback_id)}')
        elif callback_id < 0:
            raise ValueError(f'Callback id "{callback_id}" is invalid')

        self.callbacks[callback_id] = function

    def executeCallback(self, callback_id: int, result):
        """
        Executes callback function with given result

        :param callback_id: unique id for which the callback will be performed on
        :param result: result from worker
        """

        if self.connection is None:
            raise NotImplementedError('There should not be a callback happening')

        function = self.callbacks.get(callback_id)
        if function is None:
            return
        function(result)
        del self.callbacks[callback_id]

    def close(self):
        """Closes the worker"""

        if not self.worker.started or not self.worker.running:
            return

        self.worker.execute(self.callback_id(), 'close')

        while True:
            if not self.worker.running:
                break
            sleep(0.1)

    def __getattr__(self, name):
        """
        Gets name of accessed attribute on this class

        :param name: name of function
        """

        if self.connection is None:
            raise ConnectionError('No connection established')

        getattr(self.connection, name)

        def func(*args, **kwargs):
            return self.worker.execute(self.callback_id(), name, *args, **kwargs)

        return func


class ThreadedISEGConnection(ThreadedConnection, base_iseg):
    """
    Threaded connection for <ISEGConnection>

    :param connection: ISEGConnection
    """

    def __init__(self, connection: ISEGConnection):
        super().__init__(connection)


class ThreadedThyracontConnection(ThreadedConnection, base_thyracont):
    """
    Threaded connection for <ThyracontConnection>

    :param connection: ThyracontConnection
    """

    def __init__(self, connection: ThyracontConnection):
        super().__init__(connection)


class ThreadedTPG300Connection(ThreadedConnection, base_tpg300):
    """
    Threaded connection for <TPG300Connection>

    :param connection: TPG300Connection
    """

    def __init__(self, connection: TPG300Connection):
        super().__init__(connection)


class ThreadedMixedPressureConnection(ThreadedConnection, base_mixedpressure):
    """
    Threaded connection for <MixedPressureConnection>

    :param connection: MixedPressureConnection
    """

    def __init__(self, connection: MixedPressureConnection):
        super().__init__(connection)


class ThreadedMonacoConnection(ThreadedConnection, base_monaco):
    """
    Threaded connection for <MonacoConnection>

    :param connection: MonacoConnection
    """

    def __init__(self, connection: MonacoConnection):
        super().__init__(connection)


class ThreadedTLPMxConnection(ThreadedConnection, base_tlpmx):
    """
    Threaded connection for <TLPMxConnection>

    :param connection: TLPMxConnection
    """

    def __init__(self, connection: TLPMxConnection):
        super().__init__(connection)


class ThreadedDummyConnection(ThreadedConnection):
    """
    Threaded dummy connection
    """

    def __init__(self):
        super().__init__(None)


def stresstest_iseg():
    from serial import SerialException
    from Connection.USBPorts import getComports
    from Connection.ISEG import ISEGConnection
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QWidget
    import sys

    class TestISEG(QWidget):
        def __init__(self, comport: str = 'COM4', update_time: int = 500, connect_time: int = 1100):
            super().__init__()
            self.comport = comport
            self.connection: None | ISEGConnection = None
            self.threaded_connection: ThreadedDummyConnection | ThreadedISEGConnection = ThreadedDummyConnection()

            self.counter_global = 1

            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.do_update)
            self.update_timer.setInterval(update_time)
            self.update_timer.start()

            self.connect_timer = QTimer()
            self.connect_timer.timeout.connect(self.toggle_connect)
            self.connect_timer.setInterval(connect_time)
            self.connect_timer.start()

        def do_update(self):
            if self.connection is None:
                return

            def readVoltage0(voltage: float, i_glob: int, i_loc: int):
                print(f'INFO: {i_glob=}, {i_loc=}: voltage @ channel 0 = {voltage}')

            for i in range(10):
                print(f'INFO: queuing i_glob={self.counter_global}, i_loc={i}')
                self.threaded_connection.callback(
                    lambda x, j_glob=self.counter_global, j_loc=i: readVoltage0(x, j_glob, j_loc),
                    self.threaded_connection.readVoltage(0)
                )

            self.counter_global += 1

        def toggle_connect(self):
            if self.threaded_connection.isDummy():
                print('INFO: toggling connection -> connect')
                self.do_connect()
            else:
                print('INFO: toggling connection -> disconnect')
                self.do_unconnect()

        def do_unconnect(self):
            self.threaded_connection.close()
            self.threaded_connection = ThreadedDummyConnection()

            if self.connection is not None:
                self.connection.close()
                self.connection = None
            self.do_reset()

        def do_connect(self):
            connect = self.threaded_connection.isDummy()

            self.do_unconnect()

            if connect:
                self.connection = ISEGConnection(
                    self.comport,
                    echo=ISEGConnection.EchoMode.ECHO_AUTO,
                    cleaning=True,
                    strict='iseg Spezialelektronik GmbH,NR040060r4050000200,8200005,1.74'
                )
                try:
                    self.connection.open()
                    self.threaded_connection = ThreadedISEGConnection(self.connection)

                except (SerialException, ConnectionError) as error:
                    try:
                        self.connection.close()
                    except ConnectionError:
                        pass
                    self.connection = None
                    self.do_reset()

                    print(f'Connection error! Could not connect to ISEG crate power supply on port "{self.comport}", because of: {error}')

        def do_reset(self):
            self.threaded_connection.close()
            if self.connection is not None:
                self.connection.close()

            comports = getComports(not_available_entry=True)

    # do test application
    app = QApplication(sys.argv)
    test = TestISEG()
    test.do_connect()
    test.do_unconnect()
    test.show()
    app.exec()


if __name__ == '__main__':
    stresstest_iseg()
