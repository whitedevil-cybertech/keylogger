"""
Statistics panel for displaying real-time analytics and session info.

This panel is updated via signals from the controller and engine,
ensuring thread-safe updates without blocking the UI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QLabel,
    QCheckBox,
    QFrame,
    QLineEdit,
    QMessageBox,
)

from .widgets import CustomButton, MetricCard, ICONS
from .theme import Theme

logger = logging.getLogger(__name__)


class StatsPanel(QWidget):
    """
    Panel for displaying real-time statistics and configuration.
    
    Updates are driven by signals from the engine controller,
    not by polling or timers.
    """

    def __init__(self) -> None:
        super().__init__()
        self._metric_cards: dict = {}
        self._init_ui()
        self._setup_styles()

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        # Encryption and analysis checkboxes
        self._enc_checkbox = QCheckBox("🔒 AES Encryption")
        self._analytics_checkbox = QCheckBox("📊 Biometrics Analysis")
        self._analytics_checkbox.setChecked(True)
        self._window_checkbox = QCheckBox("🪟 Window Tracking")
        self._special_checkbox = QCheckBox("⌨️ Special Keys")
        self._special_checkbox.setChecked(True)
        
        # Log directory input
        self._log_dir_input = QLineEdit()
        self._log_dir_input.setReadOnly(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(32, 32, 32, 32)

        # Header
        header = QLabel("📊 Live Analytics Dashboard")
        header.setProperty("role", "title")
        main_layout.addWidget(header)

        # Metrics grid - dashboard cards (3 columns)
        metrics_frame = QFrame()
        metrics_frame.setProperty("role", "card")
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setSpacing(20)

        # Define metrics: (icon, initial_value, label, color)
        metrics_config = [
            (ICONS.get('time', '⏱️'), "00:00:00", "Session Time", "#00d4aa"),
            (ICONS.get('key', '⌨️'), "0", "Total Keys", "#2ed573"),
            ("⚡", "0.0", "WPM", "#ffb300"),
            ("⏱️", "0 ms", "Avg Dwell", "#ff6b6b"),
            ("✈️", "0 ms", "Avg Flight", "#747d8c"),
            ("🎵", "0.00", "Rhythm", "#00d4aa"),
        ]

        row, col = 0, 0
        for icon, value, label, color in metrics_config:
            card = MetricCard(icon, value, label, color)
            self._metric_cards[label.lower().replace(' ', '_')] = card
            metrics_layout.addWidget(card, row, col)
            col += 1
            if col == 3:
                col = 0
                row += 1

        main_layout.addWidget(metrics_frame)

        # Settings card
        settings_frame = QFrame()
        settings_frame.setProperty("role", "card")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setSpacing(16)

        settings_title = QLabel("⚙️ Capture Preferences")
        settings_title.setProperty("role", "title")
        settings_layout.addWidget(settings_title)

        # Checkboxes for settings
        for checkbox in [
            self._enc_checkbox,
            self._analytics_checkbox,
            self._window_checkbox,
            self._special_checkbox,
        ]:
            settings_layout.addWidget(checkbox)

        # Log directory
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("📁 Log Directory:"))
        log_layout.addWidget(self._log_dir_input, 1)
        settings_layout.addLayout(log_layout)

        main_layout.addWidget(settings_frame)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        btn_save = CustomButton("💾 Save Preferences", role="secondary")
        btn_save.clicked.connect(self._save_settings)
        action_layout.addWidget(btn_save)

        btn_reset = CustomButton("🔄 Reset", role="secondary")
        btn_reset.clicked.connect(self._reset_defaults)
        action_layout.addWidget(btn_reset)

        main_layout.addLayout(action_layout)
        main_layout.addStretch()

    def _setup_styles(self) -> None:
        """Apply theme and styling."""
        pass

    def _save_settings(self) -> None:
        """Save the current settings."""
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings saved! These will apply to the next capture session.",
        )

    def _reset_defaults(self) -> None:
        """Reset settings to defaults."""
        self._enc_checkbox.setChecked(False)
        self._analytics_checkbox.setChecked(True)
        self._window_checkbox.setChecked(False)
        self._special_checkbox.setChecked(True)
        QMessageBox.information(self, "Reset", "Settings reset to defaults.")

    @Slot(dict)
    def update_stats(self, stats: dict) -> None:
        """
        Update metric cards with live data from the engine.
        
        Called via signal from the controller whenever stats are available.
        
        Args:
            stats: Dictionary of current statistics
        """
        if not stats:
            return
        
        try:
            # Session time formatting (duration in seconds)
            duration = stats.get('duration', 0)
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self._update_metric('session_time', time_str)
            
            # Total keystrokes
            total_keys = stats.get('total_keystrokes', 0)
            self._update_metric('total_keys', f"{int(total_keys):,}")
            
            # Words per minute
            wpm = stats.get('wpm', 0)
            self._update_metric('wpm', f"{float(wpm):.1f}")
            
            # Average dwell time
            avg_dwell = stats.get('avg_dwell_ms', 0)
            self._update_metric('avg_dwell', f"{int(avg_dwell)} ms")
            
            # Average flight time
            avg_flight = stats.get('avg_flight_ms', 0)
            self._update_metric('avg_flight', f"{int(avg_flight)} ms")
            
            # Rhythm consistency score
            rhythm = stats.get('rhythm_score', 0)
            self._update_metric('rhythm', f"{float(rhythm):.2f}")
            
        except Exception as e:
            logger.exception("Error updating stats display: %s", e)

    def _update_metric(self, key: str, value: str) -> None:
        """Update a single metric card."""
        if key in self._metric_cards:
            self._metric_cards[key].setValue(value)

    def reset_display(self) -> None:
        """Reset all metrics to initial state (between sessions)."""
        self._update_metric('session_time', "00:00:00")
        self._update_metric('total_keys', "0")
        self._update_metric('wpm', "0.0")
        self._update_metric('avg_dwell', "0 ms")
        self._update_metric('avg_flight', "0 ms")
        self._update_metric('rhythm', "0.00")

    def set_log_directory(self, log_dir: Optional[Path]) -> None:
        """Set the log directory display."""
        if log_dir:
            self._log_dir_input.setText(str(log_dir))
        else:
            self._log_dir_input.setText(str(Path.home() / ".keystroke_analytics"))

    def get_settings(self) -> dict:
        """Get current settings from checkboxes."""
        return {
            "encrypt": self._enc_checkbox.isChecked(),
            "analytics": self._analytics_checkbox.isChecked(),
            "track_windows": self._window_checkbox.isChecked(),
            "log_special": self._special_checkbox.isChecked(),
        }

    def set_settings(self, settings: dict) -> None:
        """Apply settings to checkboxes."""
        self._enc_checkbox.setChecked(settings.get("encrypt", False))
        self._analytics_checkbox.setChecked(settings.get("analytics", True))
        self._window_checkbox.setChecked(settings.get("track_windows", False))
        self._special_checkbox.setChecked(settings.get("log_special", True))

