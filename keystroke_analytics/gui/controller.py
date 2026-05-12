"""
Controller for managing the analytics engine with proper threading and signals.

Uses QThread for thread-safe communication and periodic stats emission.
Delegates engine execution to EngineWorkerThread to keep GUI responsive.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from keystroke_analytics.config import AppConfig
from keystroke_analytics.gui.engine_worker import EngineWorkerThread

logger = logging.getLogger(__name__)


@dataclass
class GuiConfigOverrides:
    """Configuration overrides from GUI settings."""
    config_path: Optional[Path]
    log_dir: Optional[Path]
    encrypt: bool
    analytics_enabled: bool
    passphrase: Optional[str]


class EngineController(QObject):
    """
    Controller managing engine lifecycle and signal emission.

    Runs engine on a dedicated QThread via EngineWorkerThread.
    All communication with the engine happens via Qt signals (thread-safe).

    The engine blocks on its start() method, but since it runs on a worker
    thread, the main GUI thread remains responsive.

    Signals:
        started: Emitted when engine starts successfully
        stopped: Emitted when engine stops (cleanly or due to error)
        error: Emitted if an error occurs (passes error message)
        stats_updated: Emitted periodically with current stats dict
    """

    # Signals
    started = Signal()
    stopped = Signal()
    error = Signal(str)
    stats_updated = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._worker_thread: Optional[EngineWorkerThread] = None
        self._running = False

    @property
    def running(self) -> bool:
        """Check if capture is currently running."""
        return self._running

    def start(self, overrides: GuiConfigOverrides) -> None:
        """
        Start the capture engine in a background thread.

        Loads config, applies GUI overrides, then starts EngineWorkerThread.
        Does not block the main thread; returns immediately.

        Args:
            overrides: Configuration overrides from GUI
        """
        if self._running:
            logger.warning("Capture already running")
            return

        try:
            # Load or create configuration
            if overrides.config_path and overrides.config_path.exists():
                config = AppConfig.from_file(overrides.config_path)
            else:
                config = AppConfig()

            # Apply overrides
            if overrides.log_dir:
                config.storage.log_dir = overrides.log_dir
            if overrides.encrypt:
                config.storage.encrypt = True
                config.storage.passphrase = overrides.passphrase
            if not overrides.analytics_enabled:
                config.analytics.enabled = False

            # Validate encryption configuration
            if config.storage.encrypt and not config.storage.passphrase:
                raise ValueError("Encryption enabled but no passphrase provided.")

            logger.info("Starting capture engine in background thread")

            # Disconnect stale signals from any previous session's thread.
            if self._worker_thread is not None:
                try:
                    self._worker_thread.started.disconnect(self._on_worker_started)
                    self._worker_thread.stopped.disconnect(self._on_worker_stopped)
                    self._worker_thread.error.disconnect(self._on_worker_error)
                    self._worker_thread.stats_updated.disconnect(self._on_stats_updated)
                except RuntimeError:
                    pass  # Already disconnected or thread already gone

            # Create and configure worker thread
            self._worker_thread = EngineWorkerThread(config)

            # Connect worker signals to controller signals (queued, thread-safe)
            self._worker_thread.started.connect(self._on_worker_started)
            self._worker_thread.stopped.connect(self._on_worker_stopped)
            self._worker_thread.error.connect(self._on_worker_error)
            self._worker_thread.stats_updated.connect(self._on_stats_updated)

            self._running = True

            # Start the worker thread (engine runs there, not on main thread)
            self._worker_thread.start()
            logger.info("Capture started on worker thread")

        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to start engine: %s", exc)
            self._running = False
            self.error.emit(str(exc))

    def stop(self) -> None:
        """Stop the capture engine gracefully."""
        if not self._running or not self._worker_thread:
            logger.warning("No capture running to stop")
            return

        try:
            logger.info("Stopping capture engine...")
            self._worker_thread.stop()

            # Wait for thread to finish (blocks, but worker is already stopping)
            if self._worker_thread.isRunning():
                self._worker_thread.wait(5000)  # 5 second timeout (Qt uses positional arg)
                logger.debug("Worker thread stopped")

            self._running = False
            logger.info("Capture stopped")

        except Exception as exc:  # noqa: BLE001
            logger.exception("Error stopping engine: %s", exc)
            self.error.emit(str(exc))
            self._running = False

    @Slot()
    def _on_worker_started(self) -> None:
        """Called when worker thread signals that engine started."""
        logger.debug("Engine started signal received in controller")
        self.started.emit()

    @Slot()
    def _on_worker_stopped(self) -> None:
        """Called when worker thread signals that engine stopped."""
        logger.debug("Engine stopped signal received in controller")
        self.stopped.emit()

    @Slot(str)
    def _on_worker_error(self, message: str) -> None:
        """Called when worker thread signals an error."""
        logger.error("Engine error signal received: %s", message)
        self.error.emit(message)

    @Slot(dict)
    def _on_stats_updated(self, stats: dict) -> None:
        """Called when worker thread emits updated stats."""
        self.stats_updated.emit(stats)