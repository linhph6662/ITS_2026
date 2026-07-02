import sys
import traceback
from typing import Callable, Any, Tuple
from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from utils.logger import logger

class WorkerSignals(QObject):
    """
    Defines the PySide6 signals available from a running background worker task.
    """
    finished = Signal()
    error = Signal(tuple)   # Emits (exctype, value, traceback_string)
    result = Signal(object)  # Emits returned function value
    progress = Signal(int)

class BackgroundWorker(QRunnable):
    """
    Runnable task wrapper to execute heavy computational, DB, or report generation tasks
    asynchronously inside the global QThreadPool without locking the Main UI window.
    """
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        logger.debug("BackgroundWorker prepared for function task: %s", fn.__name__)

    @Slot()
    def run(self) -> None:
        """Initializes the callback function with passed args and kwargs."""
        try:
            logger.debug("Executing task callback function asynchronously.")
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            exctype, value = sys.exc_info()[:2]
            tb_str = traceback.format_exc()
            logger.error("BackgroundWorker execution crashed: %s\n%s", e, tb_str)
            self.signals.error.emit((exctype, value, tb_str))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
