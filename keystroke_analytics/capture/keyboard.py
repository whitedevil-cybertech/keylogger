"""
Keyboard event capture with dwell-time measurement.

Listens for both key-press and key-release events via pynput so that
the biometrics analyzer can compute dwell time (key held duration) and
flight time (gap between consecutive presses).  Each captured press is
emitted as an ``InputEvent`` through a caller-supplied callback.
"""

import time
import logging
from typing import Callable
from threading import Lock

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from keystroke_analytics.models import InputEvent, KeyCategory
from datetime import datetime

logger = logging.getLogger(__name__)

# Map pynput Key constants to readable labels and categories.
_SPECIAL_KEY_MAP: dict[Key, tuple[str, KeyCategory]] = {
    Key.space: ("[SPACE]", KeyCategory.WHITESPACE),
    Key.enter: ("[ENTER]", KeyCategory.WHITESPACE),
    Key.tab: ("[TAB]", KeyCategory.WHITESPACE),
    Key.backspace: ("[BACKSPACE]", KeyCategory.NAVIGATION),
    Key.delete: ("[DELETE]", KeyCategory.NAVIGATION),
    Key.shift: ("[SHIFT]", KeyCategory.MODIFIER),
    Key.shift_r: ("[SHIFT_R]", KeyCategory.MODIFIER),
    Key.ctrl_l: ("[CTRL]", KeyCategory.MODIFIER),
    Key.ctrl_r: ("[CTRL_R]", KeyCategory.MODIFIER),
    Key.alt_l: ("[ALT]", KeyCategory.MODIFIER),
    Key.alt_r: ("[ALT_R]", KeyCategory.MODIFIER),
    Key.cmd: ("[CMD]", KeyCategory.MODIFIER),
    Key.cmd_r: ("[CMD_R]", KeyCategory.MODIFIER),
    Key.caps_lock: ("[CAPSLOCK]", KeyCategory.MODIFIER),
    Key.esc: ("[ESC]", KeyCategory.NAVIGATION),
    Key.up: ("[UP]", KeyCategory.NAVIGATION),
    Key.down: ("[DOWN]", KeyCategory.NAVIGATION),
    Key.left: ("[LEFT]", KeyCategory.NAVIGATION),
    Key.right: ("[RIGHT]", KeyCategory.NAVIGATION),
    Key.home: ("[HOME]", KeyCategory.NAVIGATION),
    Key.end: ("[END]", KeyCategory.NAVIGATION),
    Key.page_up: ("[PGUP]", KeyCategory.NAVIGATION),
    Key.page_down: ("[PGDN]", KeyCategory.NAVIGATION),
    Key.insert: ("[INSERT]", KeyCategory.NAVIGATION),
}

# Add function keys F1–F12.
for _i in range(1, 13):
    _fkey = getattr(Key, f"f{_i}", None)
    if _fkey is not None:
        _SPECIAL_KEY_MAP[_fkey] = (f"[F{_i}]", KeyCategory.FUNCTION)

# Characters that count as punctuation.
_PUNCTUATION = set("!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~\\")


def classify_char(ch: str) -> KeyCategory:
    """Return the category for a single character."""
    if ch.isalpha():
        return KeyCategory.ALPHA
    if ch.isdigit():
        return KeyCategory.NUMERIC
    if ch in _PUNCTUATION:
        return KeyCategory.PUNCTUATION
    return KeyCategory.UNKNOWN


class KeyboardCapture:
    """
    Captures keystrokes and measures per-key dwell time.

    Parameters:
        on_event: Called with each ``InputEvent`` when a key is pressed.
        log_special_keys: If False, modifier / function keys are silently ignored.
    """

    def __init__(
        self,
        on_event: Callable[[InputEvent], None],
        log_special_keys: bool = True,
    ) -> None:
        self._on_event = on_event
        self._log_special = log_special_keys
        self._listener: keyboard.Listener | None = None

        # Dwell-time tracking: maps key -> press timestamp (monotonic).
        self._press_times: dict[str, float] = {}
        self._press_lock = Lock()

        # Flight-time tracking: timestamp of last key-press.
        self._last_press_time: float | None = None

        # Last dwell measurement (key, dwell_ms) - protected by lock
        self._last_dwell: tuple[str, float] | None = None
        self._dwell_lock = Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin listening for keyboard events in a background thread."""
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()
        logger.info("Keyboard capture started")

    def stop(self) -> None:
        """Stop the listener and release resources."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        logger.info("Keyboard capture stopped")

    def is_alive(self) -> bool:
        """Return True if the listener thread is running."""
        return self._listener is not None and self._listener.is_alive()

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _resolve_key(
        self, key: Key | KeyCode
    ) -> tuple[str, KeyCategory] | None:
        """Convert a pynput key to (label, category).  Returns None to skip."""
        if isinstance(key, Key):
            mapped = _SPECIAL_KEY_MAP.get(key)
            if mapped:
                return mapped
            # Unmapped special key — use its name.
            return f"[{key.name.upper()}]", KeyCategory.UNKNOWN

        if hasattr(key, "char") and key.char:
            return key.char, classify_char(key.char)

        return None  # unresolvable virtual key

    def _handle_press(self, key: Key | KeyCode) -> None:
        """Record press timestamp and emit an InputEvent."""
        resolved = self._resolve_key(key)
        if resolved is None:
            return

        label, category = resolved

        # Skip special keys when configured to do so.
        if not self._log_special and category in (
            KeyCategory.MODIFIER,
            KeyCategory.FUNCTION,
            KeyCategory.NAVIGATION,
        ):
            return

        now_mono = time.monotonic()

        # Compute flight time from previous press.
        flight_ms: float | None = None
        if self._last_press_time is not None:
            flight_ms = (now_mono - self._last_press_time) * 1000.0
        self._last_press_time = now_mono

        # Store press time for dwell calculation on release.
        with self._press_lock:
            self._press_times[label] = now_mono

        event = InputEvent(
            timestamp=datetime.now(),
            key_label=label,
            category=category,
            flight_ms=flight_ms,
            # dwell_ms is filled in on release via the engine.
        )
        self._on_event(event)

    def _handle_release(self, key: Key | KeyCode) -> None:
        """Calculate dwell time on key release."""
        resolved = self._resolve_key(key)
        if resolved is None:
            return

        label, _ = resolved
        now_mono = time.monotonic()

        with self._press_lock:
            press_time = self._press_times.pop(label, None)

        if press_time is not None:
            dwell_ms = (now_mono - press_time) * 1000.0
            # Store dwell measurement with lock protection
            with self._dwell_lock:
                self._last_dwell = (label, dwell_ms)

    @property
    def last_dwell(self) -> tuple[str, float] | None:
        """Return and clear the most recent (key, dwell_ms) pair."""
        with self._dwell_lock:
            val = self._last_dwell
            self._last_dwell = None
        return val
