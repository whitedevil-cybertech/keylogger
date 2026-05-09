"""
Centralized application state manager for the GUI.

Manages capture state, validates state transitions, and emits change signals.
All GUI components should listen to state changes rather than managing state independently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class CaptureState(Enum):
    """Enumeration of valid capture states."""
    IDLE = auto()          # No capture in progress
    RECORDING = auto()      # Actively capturing keystrokes
    PAUSED = auto()        # Capture paused (optional for future)
    STOPPED = auto()       # Capture was running, now stopped
    ERROR = auto()         # Capture stopped due to error


@dataclass
class AppStateSnapshot:
    """Immutable snapshot of application state."""
    capture_state: CaptureState
    recording: bool
    error_message: Optional[str] = None
    log_directory: Optional[str] = None
    
    def is_capturing(self) -> bool:
        """Check if actively capturing."""
        return self.capture_state == CaptureState.RECORDING


class AppState(QObject):
    """
    Centralized application state manager.
    
    Emits signals when state changes, allowing all GUI components
    to react consistently to state transitions.
    """
    
    # Signals
    state_changed = Signal(object)  # Emits AppStateSnapshot
    capture_started = Signal()
    capture_stopped = Signal()
    capture_paused = Signal()
    error_occurred = Signal(str)
    log_directory_changed = Signal(str)
    
    def __init__(self) -> None:
        super().__init__()
        self._state = CaptureState.IDLE
        self._error_message: Optional[str] = None
        self._log_directory: Optional[str] = None
        
    @property
    def capture_state(self) -> CaptureState:
        """Get current capture state."""
        return self._state
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._state == CaptureState.RECORDING
    
    @property
    def is_stopped(self) -> bool:
        """Check if stopped."""
        return self._state == CaptureState.STOPPED
    
    @property
    def error_message(self) -> Optional[str]:
        """Get last error message."""
        return self._error_message
    
    @property
    def log_directory(self) -> Optional[str]:
        """Get current log directory."""
        return self._log_directory
    
    def set_recording(self) -> None:
        """Transition to RECORDING state."""
        if self._state in (CaptureState.IDLE, CaptureState.PAUSED, CaptureState.STOPPED):
            self._state = CaptureState.RECORDING
            self._error_message = None
            logger.debug(f"State transition: {self._state.name}")
            self._emit_changes()
            self.capture_started.emit()
    
    def set_stopped(self) -> None:
        """Transition to STOPPED state."""
        if self._state == CaptureState.RECORDING:
            self._state = CaptureState.STOPPED
            logger.debug(f"State transition: {self._state.name}")
            self._emit_changes()
            self.capture_stopped.emit()
    
    def set_paused(self) -> None:
        """Transition to PAUSED state."""
        if self._state == CaptureState.RECORDING:
            self._state = CaptureState.PAUSED
            logger.debug(f"State transition: {self._state.name}")
            self._emit_changes()
            self.capture_paused.emit()
    
    def set_error(self, message: str) -> None:
        """Set ERROR state with message."""
        self._state = CaptureState.ERROR
        self._error_message = message
        logger.error(f"State error: {message}")
        self._emit_changes()
        self.error_occurred.emit(message)
    
    def set_idle(self) -> None:
        """Reset to IDLE state."""
        self._state = CaptureState.IDLE
        self._error_message = None
        logger.debug(f"State transition: {self._state.name}")
        self._emit_changes()
    
    def set_log_directory(self, directory: str) -> None:
        """Update log directory."""
        if self._log_directory != directory:
            self._log_directory = directory
            logger.debug(f"Log directory changed: {directory}")
            self.log_directory_changed.emit(directory)
            self._emit_changes()
    
    def _emit_changes(self) -> None:
        """Emit state_changed signal with snapshot."""
        snapshot = AppStateSnapshot(
            capture_state=self._state,
            recording=self.is_recording,
            error_message=self._error_message,
            log_directory=self._log_directory,
        )
        self.state_changed.emit(snapshot)
    
    def get_snapshot(self) -> AppStateSnapshot:
        """Get immutable snapshot of current state."""
        return AppStateSnapshot(
            capture_state=self._state,
            recording=self.is_recording,
            error_message=self._error_message,
            log_directory=self._log_directory,
        )


class StateManager:
    """Singleton state manager accessible globally."""
    _instance: Optional[AppState] = None
    
    @classmethod
    def get(cls) -> AppState:
        """Get or create the global state manager."""
        if cls._instance is None:
            cls._instance = AppState()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset state manager (for testing)."""
        cls._instance = None