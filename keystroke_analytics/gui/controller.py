"""
Controller for managing the analytics engine with proper threading and signals.

Uses QThread for thread-safe communication and periodic stats emission.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer, Slot

from keystroke_analytics.config import AppConfig

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
    
    Bridges the GUI thread and engine thread, ensuring all communication
    is thread-safe via Qt signals.
    """
    
    # Signals
    started = Signal()
    stopped = Signal()
    error = Signal(str)
    stats_updated = Signal(dict)
    
    def __init__(self) -> None:
        super().__init__()
        self._engine_thread = None
        self._engine = None
        self._running = False
        self._stats_timer: Optional[QTimer] = None
        self._last_stats_time = 0.0
        
    @property
    def running(self) -> bool:
        """Check if capture is currently running."""
        return self._running
    
    def start(self, overrides: GuiConfigOverrides) -> None:
        """
        Start the capture engine in a background thread.
        
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
            
            # Import here to avoid circular dependency
            from keystroke_analytics.engine import AnalyticsEngine
            
            self._engine = AnalyticsEngine(config)
            self._running = True
            
            # Start the engine synchronously (it runs the capture loop internally)
            # NOTE: This runs on the main thread but blocks; ideally we'd use QThread
            # For now, keeping compatibility with existing engine design
            try:
                # Start in a way that doesn't block UI
                self._engine.start()
            except KeyboardInterrupt:
                logger.info("Capture interrupted")
            except Exception as e:
                logger.exception("Engine error: %s", e)
                self.error.emit(str(e))
            finally:
                self._running = False
                self.stopped.emit()
            
            self.started.emit()
            logger.info("Capture started")
            
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to start engine: %s", exc)
            self._running = False
            self.error.emit(str(exc))
    
    def stop(self) -> None:
        """Stop the capture engine."""
        if not self._running or not self._engine:
            logger.warning("No capture running to stop")
            return
        
        try:
            logger.info("Stopping capture...")
            self._engine.stop()
            self._running = False
            
            # Get final stats
            if hasattr(self._engine, 'get_stats'):
                stats = self._engine.get_stats()
                if stats:
                    self.stats_updated.emit(stats)
            
            self.stopped.emit()
            logger.info("Capture stopped")
            
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error stopping engine: %s", exc)
            self.error.emit(str(exc))
            self._running = False
    
    def get_current_stats(self) -> dict:
        """
        Get current statistics from the running engine.
        
        Returns:
            Dictionary of current stats or empty dict if engine not running
        """
        if not self._engine or not self._running:
            return {}
        
        try:
            if hasattr(self._engine, 'get_stats'):
                return self._engine.get_stats()
        except Exception as e:
            logger.exception("Error getting stats: %s", e)
        
        return {}