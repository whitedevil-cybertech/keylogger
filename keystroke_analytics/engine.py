"""
Central analytics engine.

Wires together the capture, storage, analytics, and delivery subsystems
and runs the main event loop.  All cross-component coordination (e.g.
attaching dwell times from releases back to events, polling window
titles) happens here.
"""

import logging
from threading import Event, Timer, Lock

from keystroke_analytics.config import AppConfig
from keystroke_analytics.models import InputEvent
from keystroke_analytics.capture.keyboard import KeyboardCapture
from keystroke_analytics.capture.window import ActiveWindowDetector
from keystroke_analytics.storage.rotation import RotatingFileWriter
from keystroke_analytics.storage.encrypted_logger import EncryptedLogger
from keystroke_analytics.analytics.biometrics import TypingBiometrics
from keystroke_analytics.delivery.webhook import WebhookSender

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Orchestrates all subsystems for a single capture session.

    Typical usage::

        engine = AnalyticsEngine(AppConfig())
        engine.start()          # blocks until Ctrl-C
    """

    def __init__(self, config: AppConfig, on_stats: callable | None = None) -> None:
        self._config = config
        self._running = Event()
        self._on_stats = on_stats  # Callback for stats updates (called every ~500ms)
        self._last_stats_time = 0  # Track time of last stats emission

        # -- Storage --------------------------------------------------
        if config.storage.encrypt and config.storage.passphrase:
            self._enc_logger: EncryptedLogger | None = EncryptedLogger(
                log_dir=config.storage.log_dir,
                passphrase=config.storage.passphrase,
                prefix=config.storage.file_prefix,
            )
            self._writer: RotatingFileWriter | None = None
        else:
            self._enc_logger = None
            self._writer = RotatingFileWriter(
                log_dir=config.storage.log_dir,
                prefix=config.storage.file_prefix,
                max_size_mb=config.storage.max_file_size_mb,
            )

        # -- Analytics ------------------------------------------------
        self._biometrics = TypingBiometrics() if config.analytics.enabled else None
        self._stats_lock = Lock()  # Protect biometrics access from multiple threads

        # -- Delivery -------------------------------------------------
        self._webhook = WebhookSender(
            url=config.webhook.url,
            batch_size=config.webhook.batch_size,
            timeout_secs=config.webhook.timeout_secs,
        )

        # -- Window tracking ------------------------------------------
        self._window_detector = ActiveWindowDetector() if config.capture.track_windows else None
        self._current_window: str | None = None
        self._window_timer: Timer | None = None

        # -- Capture (created last so callback refs are valid) --------
        self._capture = KeyboardCapture(
            on_event=self._on_keystroke,
            log_special_keys=config.capture.log_special_keys,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start capture and block until interrupted."""
        import time
        
        self._running.set()
        self._print_banner()
        self._start_window_polling()
        self._capture.start()

        try:
            # Block the main thread; pynput listener runs in background.
            while self._running.is_set():
                # Periodically check for dwell updates.
                dwell = self._capture.last_dwell
                if dwell and self._biometrics:
                    self._biometrics.update_dwell(dwell[0], dwell[1])

                # Emit stats every 500ms (instead of via separate timer)
                current_time = time.time()
                if self._on_stats and (current_time - self._last_stats_time) >= 0.5:
                    stats = self.get_stats()
                    if stats:
                        try:
                            self._on_stats(stats)
                            logger.debug(
                                "Stats emitted from engine: ks=%d wpm=%.1f",
                                stats.get("total_keystrokes", 0),
                                stats.get("wpm", 0),
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.exception("Error in stats callback: %s", e)
                    self._last_stats_time = current_time

                self._running.wait(timeout=0.05)  # Reduced to 50ms for more frequent checks

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Gracefully shut down all subsystems."""
        print("\n[*] Shutting down...")
        self._running.clear()

        self._capture.stop()

        if self._window_timer:
            self._window_timer.cancel()

        self._webhook.flush()

        if self._writer:
            self._writer.close()
        if self._enc_logger:
            self._enc_logger.close()

        # Print analytics report.
        if self._biometrics and self._config.analytics.show_report_on_exit:
            stats = self._biometrics.report()
            print(stats.summary())

        log_path = (
            self._enc_logger.current_path if self._enc_logger
            else self._writer.current_path if self._writer
            else "N/A"
        )
        print(f"[*] Logs saved to: {log_path}")
        print("[*] Session ended.")

    def get_stats(self) -> dict:
        """Get current session statistics for GUI display (thread-safe)."""
        if not self._biometrics:
            return {}

        try:
            with self._stats_lock:
                report = self._biometrics.report()
                categories = report.category_distribution or {}
                return {
                    "duration": report.duration_secs,
                    "total_keystrokes": report.total_keystrokes,
                    "wpm": report.words_per_minute,
                    "avg_dwell_ms": report.avg_dwell_ms,
                    "avg_flight_ms": report.avg_flight_ms,
                    "rhythm_score": report.rhythm_consistency,
                    "alpha_count": categories.get("alpha", 0),
                    "numeric_count": categories.get("numeric", 0),
                    "special_count": categories.get("punctuation", 0),
                    "whitespace_count": categories.get("whitespace", 0),
                    "function_count": categories.get("function", 0),
                    "top_keys": list(report.top_keys) if report.top_keys else [],
                    "top_key": report.top_keys[0][0] if report.top_keys else "N/A",
                    "status": "Recording" if self._running.is_set() else "Idle",
                    "elapsed_time": report.duration_secs,
                }
        except Exception as e:
            logger.exception("Error getting stats: %s", e)
            return {}

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _on_keystroke(self, event: InputEvent) -> None:
        """Called by KeyboardCapture for each key press (from listener thread)."""
        # Attach current window title.
        event.window_title = self._current_window

        # Write to storage.
        line = event.to_log_line()
        if self._writer:
            self._writer.write(line)
        if self._enc_logger:
            self._enc_logger.write(line)

        # Feed analytics (with lock protection).
        if self._biometrics:
            with self._stats_lock:
                self._biometrics.record_event(event)
                logger.debug(
                    "Keystroke recorded: key=%s press_time=%s",
                    event.key,
                    event.timestamp,
                )

        # Buffer for webhook.
        self._webhook.add_event(event)

    # ------------------------------------------------------------------
    # Window polling
    # ------------------------------------------------------------------

    def _start_window_polling(self) -> None:
        if self._window_detector is None:
            return
        self._poll_window()

    def _poll_window(self) -> None:
        if not self._running.is_set():
            return
        if self._window_detector:
            self._current_window = self._window_detector.get_title()
        self._window_timer = Timer(
            self._config.capture.window_poll_interval,
            self._poll_window,
        )
        self._window_timer.daemon = True
        self._window_timer.start()

    # ------------------------------------------------------------------
    # Banner
    # ------------------------------------------------------------------

    def _print_banner(self) -> None:
        enc = "ON" if self._enc_logger else "OFF"
        whk = "ON" if self._webhook.enabled else "OFF"
        bio = "ON" if self._biometrics else "OFF"
        log_path = (
            self._enc_logger.current_path if self._enc_logger
            else self._writer.current_path if self._writer
            else "N/A"
        )

        print()
        print("  ╔═══════════════════════════════════════╗")
        print("  ║      KEYSTROKE  ANALYTICS  ENGINE     ║")
        print("  ╚═══════════════════════════════════════╝")
        print()
        print(f"  Log File   : {log_path}")
        print(f"  Encryption : {enc}")
        print(f"  Webhook    : {whk}")
        print(f"  Biometrics : {bio}")
        print()
        print("  Press Ctrl+C to stop and view your typing report.")
        print()
