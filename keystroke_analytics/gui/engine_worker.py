"""
Engine worker thread for running AnalyticsEngine on a background QThread.

This module implements proper Qt threading for the keystroke capture engine,
ensuring the main GUI thread remains responsive during capture.

Architecture:
    Main GUI Thread → EngineController (QObject) → EngineWorker (QObject)
                                                       ↓
                                               EngineWorkerThread (QThread)
                                                       ↓
                                           AnalyticsEngine.start() [blocking]

Signals flow back to GUI via Qt queued connections (thread-safe).
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, QTimer, Slot, Qt

from keystroke_analytics.config import AppConfig
from keystroke_analytics.engine import AnalyticsEngine

logger = logging.getLogger(__name__)


class EngineWorker(QObject):
    """
    Worker object that runs the AnalyticsEngine on a background thread.

    Signals:
        started: Emitted when engine starts successfully
        stopped: Emitted when engine stops
        error: Emitted if an error occurs (passes error message)
        stats_updated: Emitted periodically with current stats dict
    """

    # Signals
    started = Signal()
    stopped = Signal()
    error = Signal(str)
    stats_updated = Signal(dict)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._engine: Optional[AnalyticsEngine] = None
        self._running = False
        self._stats_timer: Optional[QTimer] = None

    @Slot()
    def run(self) -> None:
        """
        Main worker routine: start the engine and run until stop() is called.

        This runs on the background worker thread; the engine.start() call
        will block, but does not block the GUI thread since this runs elsewhere.
        """
        try:
            logger.debug("EngineWorker.run() starting on thread %s", QThread.currentThread())

            # Create engine with provided config
            self._engine = AnalyticsEngine(self._config)
            self._running = True

            # Emit started signal to notify GUI
            self.started.emit()
            logger.info("Engine worker started successfully")

            # Set up stats timer to emit updates periodically
            self._setup_stats_timer()

            # Start the engine (blocking call, but on worker thread)
            logger.debug("Calling engine.start() - will block worker thread")
            self._engine.start()

        except Exception as e:  # noqa: BLE001
            logger.exception("Engine error: %s", e)
            self.error.emit(str(e))

        finally:
            # Clean up
            self._running = False
            if self._stats_timer:
                self._stats_timer.stop()
            logger.debug("EngineWorker.run() completed")
            self.stopped.emit()

    @Slot()
    def stop(self) -> None:
        """
        Stop the engine gracefully.

        Safe to call from any thread (typically main GUI thread).
        """
        try:
            if not self._running or not self._engine:
                logger.warning("Engine not running; nothing to stop")
                return

            logger.info("EngineWorker.stop() called; signaling engine shutdown")
            self._engine.stop()
            self._running = False

        except Exception as e:  # noqa: BLE001
            logger.exception("Error stopping engine: %s", e)
            self.error.emit(f"Stop error: {str(e)}")

    def _setup_stats_timer(self) -> None:
        """Set up a timer to emit stats periodically to the GUI."""
        self._stats_timer = QTimer()
        # Set timer to run on this (worker) thread
        self._stats_timer.moveToThread(QThread.currentThread())
        # Connect timeout signal to emit_stats slot
        self._stats_timer.timeout.connect(self._emit_stats, Qt.DirectConnection)
        self._stats_timer.start(500)  # Emit stats every 500ms
        logger.debug("Stats timer started on worker thread: 500ms interval")

    @Slot()
    def _emit_stats(self) -> None:
        """
        Poll current stats from engine and emit via signal.

        Called by stats timer; runs on worker thread.
        Stats signal is received by main thread via queued connection.
        """
        if not self._running or not self._engine:
            return

        try:
            stats = self._engine.get_stats()
            if stats:
                logger.debug(
                    "Emitting stats: ks=%d wpm=%.1f dwell=%.1f flight=%.1f",
                    stats.get("total_keystrokes", 0),
                    stats.get("wpm", 0),
                    stats.get("avg_dwell_ms", 0),
                    stats.get("avg_flight_ms", 0),
                )
                self.stats_updated.emit(stats)
        except Exception as e:  # noqa: BLE001
            logger.exception("Error getting stats: %s", e)
            # Don't emit error here; this is just stats collection


class EngineWorkerThread(QThread):
    """
    Manages a QThread for the engine worker.

    This is the recommended way to run long-lived workers in Qt.
    Usage:
        worker_thread = EngineWorkerThread(config)
        worker_thread.started.connect(...)
        worker_thread.stopped.connect(...)
        worker_thread.error.connect(...)
        worker_thread.stats_updated.connect(...)
        worker_thread.start()
        # ... later ...
        worker_thread.stop()
        worker_thread.wait()
    """

    # Expose worker signals through thread
    started = Signal()
    stopped = Signal()
    error = Signal(str)
    stats_updated = Signal(dict)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._worker: Optional[EngineWorker] = None

    def run(self) -> None:
        """Run the worker on this thread."""
        logger.debug("EngineWorkerThread.run() starting")
        self._worker = EngineWorker(self._config)

        # Connect worker signals to this thread's signals for re-emission
        self._worker.started.connect(self.started.emit)
        self._worker.stopped.connect(self.stopped.emit)
        self._worker.error.connect(self.error.emit)
        self._worker.stats_updated.connect(self.stats_updated.emit)

        # Run worker (blocks until stop() is called)
        self._worker.run()
        logger.debug("EngineWorkerThread.run() completed")

    def stop(self) -> None:
        """Stop the worker gracefully."""
        if self._worker:
            self._worker.stop()
