from typing import TYPE_CHECKING
from time import sleep


from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool


from Config.GlobalConf import GlobalConf

from Connection.ISEG import ISEGConnection
from Connection.Thyracont import ThyracontConnection
from Connection.Monaco import MonacoConnection


if TYPE_CHECKING:
    base_iseg = ISEGConnection
    base_thyracont = ThyracontConnection
    base_monaco = MonacoConnection
else:
    base_iseg = object
    base_thyracont = object
    base_monaco = object


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

    error = pyqtSignal(Exception)
    result = pyqtSignal(int, object)


class ConnectionWorker(QRunnable):
    """
    Threaded worker for handling a connection without lagging the input panel

    :param connection: any connection class
    """

    max_queue = 100

    def __init__(self, connection):
        super().__init__()
        self.connection: ISEGConnection | ThyracontConnection | MonacoConnection = connection
        self.signal = ConnectionWorkerSignals()
        self.running = True
        self.work = []

    @pyqtSlot()
    def run(self):
        """Called when worker is started"""

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
            except (AttributeError, ConnectionError, NameError, TypeError) as error:
                self.signal.error.emit(error)

    def execute(self, callback_id: int, name, *args, **kwargs):
        """
        Adds function call to connection

        :param callback_id: unique id of callback
        :param name: function name
        """

        if len(self.work) > self.max_queue:
            self.signal.error.emit(BufferError('Too many tasks in queue'))
            return -1

        if not self.running:
            self.signal.error.emit(ChildProcessError('Not running'))
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
        connection: ISEGConnection | ThyracontConnection | MonacoConnection | None
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

    @staticmethod
    def error(error):
        """
        Called when an exception in the worker thread occurs

        :param error: exception that occurred
        """

        GlobalConf.logger.exception(error)

    def callback(self, function, callback_id):
        """
        Calls function when second statement finishes

        :param function: function to be executed
        :param callback_id: every call of this class will be passed to the worker and return a unique id, which should be passed here
        """

        if self.connection is None:
            raise NotImplementedError('There should not be a callback happening')

        if not isinstance(callback_id, int):
            raise ValueError(f'Callback id must be int, received {type(callback_id)}')
        elif callback_id < 0:
            raise ValueError(f'Callback id is invalid')

        self.callbacks[callback_id] = function

    def executeCallback(self, callback_id, result):
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

        if self.worker.running:
            self.worker.execute(self.callback_id(), 'close')
            self.worker.running = False

    def __getattr__(self, name):
        """
        Gets name of accessed attribute on this class

        :param name: name of function
        """

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


class ThreadedMonacoConnection(ThreadedConnection, base_monaco):
    """
    Threaded connection for <MonacoConnection>

    :param connection: MonacoConnection
    """

    def __init__(self, connection: MonacoConnection):
        super().__init__(connection)


class ThreadedDummyConnection(ThreadedConnection):
    """
    Threaded dummy connection
    """

    def __init__(self):
        super().__init__(None)
