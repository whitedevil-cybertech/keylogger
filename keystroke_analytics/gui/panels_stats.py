"""Live statistics panel with compact real-time metrics and controls."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from .widgets import ICONS, CustomButton, MetricCard

logger = logging.getLogger(__name__)


class StatsPanel(QWidget):
    """Panel for displaying real-time statistics and capture preferences."""

    def __init__(self) -> None:
        super().__init__()
        self._metric_cards: dict[str, MetricCard] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        self._enc_checkbox = QCheckBox("AES Encryption")
        self._analytics_checkbox = QCheckBox("Biometrics Analysis")
        self._analytics_checkbox.setChecked(True)
        self._window_checkbox = QCheckBox("Window Tracking")
        self._special_checkbox = QCheckBox("Special Keys")
        self._special_checkbox.setChecked(True)

        self._log_dir_input = QLineEdit()
        self._log_dir_input.setReadOnly(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Live Stats")
        header.setProperty("role", "title")
        main_layout.addWidget(header)

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(8)

        metrics_config = [
            (ICONS.get("time", "⏱"), "00:00:00", "Session Time", "#f2b94b"),
            (ICONS.get("key", "⌨"), "0", "Total Keys", "#34d399"),
            (ICONS.get("speed", "⚡"), "0.0", "WPM", "#19c7c0"),
            ("⏳", "0 ms", "Avg Dwell", "#f59e0b"),
            ("⇄", "0 ms", "Avg Flight", "#a78bfa"),
            (ICONS.get("rhythm", "◍"), "0.00", "Rhythm", "#60a5fa"),
        ]

        for index, (icon, value, label, color) in enumerate(metrics_config):
            card = MetricCard(icon, value, label, color)
            self._metric_cards[label.lower().replace(" ", "_")] = card
            row, col = divmod(index, 3)
            metrics_grid.addWidget(card, row, col)

        main_layout.addLayout(metrics_grid)

        lower_row = QHBoxLayout()
        lower_row.setSpacing(8)

        realtime_frame = QFrame()
        realtime_frame.setProperty("role", "card")
        realtime_layout = QVBoxLayout(realtime_frame)
        realtime_layout.setContentsMargins(10, 10, 10, 10)
        realtime_layout.setSpacing(8)

        realtime_title = QLabel("Real-time Activity")
        realtime_title.setProperty("role", "subtitle")
        realtime_layout.addWidget(realtime_title)

        self._speed_bar = self._build_labeled_bar(realtime_layout, "Typing speed")
        self._keymix_bar = self._build_labeled_bar(realtime_layout, "Key frequency")
        self._activity_bar = self._build_labeled_bar(realtime_layout, "Session activity")

        lower_row.addWidget(realtime_frame, 2)

        settings_frame = QFrame()
        settings_frame.setProperty("role", "card")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(8)

        settings_title = QLabel("Capture Preferences")
        settings_title.setProperty("role", "subtitle")
        settings_layout.addWidget(settings_title)

        for checkbox in (
            self._enc_checkbox,
            self._analytics_checkbox,
            self._window_checkbox,
            self._special_checkbox,
        ):
            settings_layout.addWidget(checkbox)

        log_row = QHBoxLayout()
        log_row.setSpacing(6)
        log_row.addWidget(QLabel("Log Directory"))
        log_row.addWidget(self._log_dir_input, 1)
        settings_layout.addLayout(log_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_save = CustomButton("Save", role="secondary")
        btn_save.clicked.connect(self._save_settings)
        btn_row.addWidget(btn_save)

        btn_reset = CustomButton("Reset", role="secondary")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_reset)

        settings_layout.addLayout(btn_row)
        lower_row.addWidget(settings_frame, 1)

        main_layout.addLayout(lower_row)

    def _build_labeled_bar(self, parent_layout: QVBoxLayout, label_text: str) -> QProgressBar:
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(label_text)
        label.setProperty("role", "muted")
        label.setMinimumWidth(96)
        row.addWidget(label)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        bar.setFormat("%p%")
        row.addWidget(bar, 1)

        parent_layout.addLayout(row)
        return bar

    def _save_settings(self) -> None:
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings saved! These will apply to the next capture session.",
        )

    def _reset_defaults(self) -> None:
        self._enc_checkbox.setChecked(False)
        self._analytics_checkbox.setChecked(True)
        self._window_checkbox.setChecked(False)
        self._special_checkbox.setChecked(True)
        QMessageBox.information(self, "Reset", "Settings reset to defaults.")

    @Slot(dict)
    def update_stats(self, stats: dict) -> None:
        if not stats:
            return

        try:
            duration = stats.get("duration", 0)
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self._update_metric("session_time", time_str)

            total_keys = stats.get("total_keystrokes", 0)
            self._update_metric("total_keys", f"{int(total_keys):,}")

            wpm = float(stats.get("wpm", 0))
            self._update_metric("wpm", f"{wpm:.1f}")

            avg_dwell = stats.get("avg_dwell_ms", 0)
            self._update_metric("avg_dwell", f"{int(avg_dwell)} ms")

            avg_flight = stats.get("avg_flight_ms", 0)
            self._update_metric("avg_flight", f"{int(avg_flight)} ms")

            rhythm = float(stats.get("rhythm_score", 0))
            self._update_metric("rhythm", f"{rhythm:.2f}")

            # Lightweight visual indicators for live trends.
            self._speed_bar.setValue(max(0, min(int(wpm), 100)))
            alpha = int(stats.get("alpha_count", 0))
            numeric = int(stats.get("numeric_count", 0))
            special = int(stats.get("special_count", 0))
            distribution_total = alpha + numeric + special
            alpha_percentage = int((alpha / distribution_total) * 100) if distribution_total else 0
            self._keymix_bar.setValue(max(0, min(alpha_percentage, 100)))

            activity_pct = int(min((total_keys / 500) * 100, 100))
            self._activity_bar.setValue(activity_pct)

        except Exception as e:
            logger.exception("Error updating stats display: %s", e)

    def _update_metric(self, key: str, value: str) -> None:
        if key in self._metric_cards:
            self._metric_cards[key].setValue(value)

    def reset_display(self) -> None:
        self._update_metric("session_time", "00:00:00")
        self._update_metric("total_keys", "0")
        self._update_metric("wpm", "0.0")
        self._update_metric("avg_dwell", "0 ms")
        self._update_metric("avg_flight", "0 ms")
        self._update_metric("rhythm", "0.00")
        self._speed_bar.setValue(0)
        self._keymix_bar.setValue(0)
        self._activity_bar.setValue(0)

    def set_log_directory(self, log_dir: Path | None) -> None:
        if log_dir:
            self._log_dir_input.setText(str(log_dir))
        else:
            self._log_dir_input.setText(str(Path.home() / ".keystroke_analytics"))

    def get_settings(self) -> dict:
        return {
            "encrypt": self._enc_checkbox.isChecked(),
            "analytics": self._analytics_checkbox.isChecked(),
            "track_windows": self._window_checkbox.isChecked(),
            "log_special": self._special_checkbox.isChecked(),
        }

    def set_settings(self, settings: dict) -> None:
        self._enc_checkbox.setChecked(settings.get("encrypt", False))
        self._analytics_checkbox.setChecked(settings.get("analytics", True))
        self._window_checkbox.setChecked(settings.get("track_windows", False))
        self._special_checkbox.setChecked(settings.get("log_special", True))
