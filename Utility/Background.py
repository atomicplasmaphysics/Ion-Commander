from typing import Any, Callable


from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot


class BackgroundTaskSignals(QObject):
    """
    Signals of <BackgroundTask> (delivered in the thread where they were connected, i.e. the GUI thread)

    finished: result of the function
    failed: exception of the function
    """

    finished = pyqtSignal(object)
    failed = pyqtSignal(object)


class BackgroundTask(QRunnable):
    """
    Executes a blocking function (e.g. opening a slow device) in a thread pool, so the GUI does not hang

    :param function: function without arguments that is executed in the background
    """

    def __init__(self, function: Callable[[], Any]):
        super().__init__()
        self.function = function
        self.signals = BackgroundTaskSignals()

    @pyqtSlot()
    def run(self):
        """Executed in the thread pool"""

        try:
            result = self.function()
        except Exception as error:
            self.signals.failed.emit(error)
            return
        self.signals.finished.emit(result)


class BackgroundRunner(QObject):
    """
    Runs blocking functions one after another in a background thread (e.g. all calls of one device DLL) and calls
    the callbacks in the GUI thread

    :param parent: parent object
    :param max_threads: number of functions that may run at the same time
    """

    def __init__(self, parent: QObject | None = None, max_threads: int = 1):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(max_threads)
        # keep the tasks (and their signals) alive until the callbacks were called
        self.tasks: list[BackgroundTask] = []

    def run(
        self,
        function: Callable[[], Any],
        on_finished: Callable[[Any], None] | None = None,
        on_failed: Callable[[Exception], None] | None = None
    ):
        """
        Runs the function in the background

        :param function: function without arguments
        :param on_finished: called in the GUI thread with the result
        :param on_failed: called in the GUI thread with the exception
        """

        task = BackgroundTask(function)
        self.tasks.append(task)

        def finished(result):
            self._remove(task)
            if on_finished is not None:
                on_finished(result)

        def failed(error):
            self._remove(task)
            if on_failed is not None:
                on_failed(error)

        task.signals.finished.connect(finished)
        task.signals.failed.connect(failed)
        self.pool.start(task)

    def _remove(self, task: BackgroundTask):
        """Forgets a finished task"""

        if task in self.tasks:
            self.tasks.remove(task)

    def isBusy(self) -> bool:
        """True if a function is running or waiting"""
        return bool(self.tasks)

    def waitForDone(self, timeout_ms: int = 15000) -> bool:
        """Waits until all functions are done (e.g. before closing the device), returns False on timeout"""
        return self.pool.waitForDone(timeout_ms)
