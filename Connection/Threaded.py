from typing import TYPE_CHECKING, Callable
from time import time, sleep


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

    error: callback_id, any occurring error
    result: callback_id, result
    """

    error = pyqtSignal(int, Exception)
    result = pyqtSignal(int, object)


class ConnectionWorker(QRunnable):
    """
    Threaded worker for handling a connection without lagging the input panel

    :param connection: any connection class
    :param auto_delete: auto delete after x time has passed
    """

    max_queue = 100

    def __init__(self, connection, auto_delete: int | None = max_queue // 2):
        super().__init__()
        self.connection: ISEGConnection | ThyracontConnection | MonacoConnection | TLPMxConnection = connection
        self.signal = ConnectionWorkerSignals()
        self.running = True
        self.close_called = False
        self.started = False
        self.auto_delete = auto_delete
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

            callback_id, _, name, args, kwargs = self.work.pop(0)

            try:
                obj_func = getattr(self.connection, name)
                result = obj_func(*args, **kwargs)
                self.signal.result.emit(callback_id, result)
            except Exception as error:
                self.signal.error.emit(callback_id, error)

            if name == 'close':
                self.close_called = True
                self.running = False
                self.work = []

    def execute(self, callback_id: int, name, *args, **kwargs):
        """
        Adds function call to connection

        :param callback_id: unique id of callback
        :param name: function name
        """

        if name == 'close':
            self.work.insert(0, (callback_id, time(), name, args, kwargs))
            return callback_id

        if len(self.work) > self.max_queue:
            if self.auto_delete is None:
                self.signal.error.emit(-1, BufferError('Too many tasks in queue'))
                return -1

            self.signal.error.emit(-1, BufferError('Too many tasks in queue, will delete possible oldest ones'))
            auto_delete_time = time() - self.auto_delete
            deleted_callback_ids = []
            for _ in range(len(self.work)):
                try:
                    work = self.work.pop(0)
                    if work[1] > auto_delete_time:
                        work.append(work)
                    else:
                        deleted_callback_ids.append(work[0])
                except IndexError:
                    pass
            return deleted_callback_ids

        if not self.running:
            if self.close_called:
                return -10

            self.signal.error.emit(-1, ChildProcessError('Not running'))
            return -1

        self.work.append((callback_id, time(), name, args, kwargs))
        return callback_id


class ThreadedConnection(QObject):
    """
    Baseclass for threaded connections

    :param connection: Connection class
    :param connection_aborted_function: function to be called on aborted or lost connection
    """

    def __init__(
        self,
        connection: ISEGConnection | ThyracontConnection | TPG300Connection | MixedPressureConnection | MonacoConnection | TLPMxConnection | None,
        connection_aborted_function: Callable = None
    ):
        super().__init__()
        self.connection = connection
        self.connection_aborted_function = connection_aborted_function

        self.worker = ConnectionWorker(connection)
        self.worker.signal.error.connect(self.handleError)
        self.worker.signal.result.connect(self.executeCallback)

        self.threadpool = QThreadPool.globalInstance()
        if self.connection is not None:
            self.threadpool.start(self.worker)

        self.callback_id = CallbackId()
        self.callbacks = {}

    def isDummy(self) -> bool:
        """Returns if it is a dummy <ThreadedConnection>"""

        return self.connection is None

    @pyqtSlot(int, Exception)
    def handleError(self, callback_id: int, error: Exception):
        """
        Called when an exception in the worker thread occurs

        :param callback_id: unique id for which the callback will be performed on
        :param error: exception that occurred
        """

        GlobalConf.logger.error(error)

        if isinstance(error, ConnectionAbortedError):
            if self.connection_aborted_function is not None:
                self.connection_aborted_function()
            return

        function = self.callbacks.get(callback_id)
        if function is None:
            return

        try:
            function(error)
        except (ValueError, AttributeError, TypeError):
            pass

        del self.callbacks[callback_id]

    def callback(self, function, callback_id):
        """
        Calls function when second statement finishes. Expects a callback_id, which is a positive integer if successfull,
        a negative integer if not successfull and a list of integers of deleted callback_ids if queue is already too long

        Example: callback(func_to_execute_on_callback, threaded_connection.func_for_device(args))

        :param function: function to be executed
        :param callback_id: every call of this class will be passed to the worker and return a unique id, which should be passed here
        """

        if self.connection is None:
            raise NotImplementedError('There should not be a callback happening')

        if isinstance(callback_id, list):
            for i in callback_id:
                del self.callbacks[i]

        if not isinstance(callback_id, int):
            raise ValueError(f'Callback id must be <int>, received {type(callback_id)}')
        elif callback_id == -10:
            return
        elif callback_id < 0:
            raise ValueError(f'Callback id "{callback_id}" is invalid')

        self.callbacks[callback_id] = function

    @pyqtSlot(int, object)
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

        def func(*args, **kwargs):
            return self.worker.execute(self.callback_id(), name, *args, **kwargs)

        return func


class ThreadedISEGConnection(ThreadedConnection, base_iseg):
    """
    Threaded connection for <ISEGConnection>

    :param connection: ISEGConnection
    """

    def __init__(self, connection: ISEGConnection, *args, **kwargs):
        super().__init__(connection, *args, **kwargs)


class ThreadedThyracontConnection(ThreadedConnection, base_thyracont):
    """
    Threaded connection for <ThyracontConnection>

    :param connection: ThyracontConnection
    """

    def __init__(self, connection: ThyracontConnection, *args, **kwargs):
        super().__init__(connection, *args, **kwargs)


class ThreadedTPG300Connection(ThreadedConnection, base_tpg300):
    """
    Threaded connection for <TPG300Connection>

    :param connection: TPG300Connection
    """

    def __init__(self, connection: TPG300Connection, *args, **kwargs):
        super().__init__(connection, *args, **kwargs)


class ThreadedMixedPressureConnection(ThreadedConnection, base_mixedpressure):
    """
    Threaded connection for <MixedPressureConnection>

    :param connection: MixedPressureConnection
    """

    def __init__(self, connection: MixedPressureConnection, *args, **kwargs):
        super().__init__(connection, *args, **kwargs)


class ThreadedMonacoConnection(ThreadedConnection, base_monaco):
    """
    Threaded connection for <MonacoConnection>

    :param connection: MonacoConnection
    """

    def __init__(self, connection: MonacoConnection, *args, **kwargs):
        super().__init__(connection, *args, **kwargs)


class ThreadedTLPMxConnection(ThreadedConnection, base_tlpmx):
    """
    Threaded connection for <TLPMxConnection>

    :param connection: TLPMxConnection
    """

    def __init__(self, connection: TLPMxConnection, *args, **kwargs):
        super().__init__(connection, *args, **kwargs)


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
