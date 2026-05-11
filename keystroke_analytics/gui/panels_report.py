"""
Report viewer panel for displaying typing analytics reports and statistics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QLabel,
    QPushButton,
    QProgressBar,
    QFrame,
    QTextEdit,
    QMessageBox,
)

from .widgets import CustomButton, MetricCard, ICONS
from .theme import Theme

logger = logging.getLogger(__name__)


class ReportPanel(QWidget):
    """Panel for displaying typing analytics reports and session statistics."""

    def __init__(self) -> None:
        super().__init__()
        self._session_stats = None
        self._init_ui()
        self._update_summary_text()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)

        # Hero title
        title = QLabel("📋 Session Analytics Report")
        title.setProperty("role", "title")
        layout.addWidget(title)

        # Hero metrics row
        self._hero_frame = QFrame()
        self._hero_frame.setProperty("role", "card")
        hero_layout = QGridLayout(self._hero_frame)
        hero_layout.setSpacing(20)

        self._wpm_card = MetricCard("⚡", "0 WPM", "Words per Minute", "#00d4aa")
        self._rhythm_card = MetricCard("🎵", "0.00", "Rhythm Score", "#2ed573")
        self._keystrokes_card = MetricCard(ICONS.get('key', '⌨️'), "0", "Total Keystrokes", "#ffb300")

        hero_layout.addWidget(self._wpm_card, 0, 0)
        hero_layout.addWidget(self._rhythm_card, 0, 1)
        hero_layout.addWidget(self._keystrokes_card, 0, 2)

        layout.addWidget(self._hero_frame)

        # Progress bars for key categories (modern replacement for ASCII)
        progress_frame = QFrame()
        progress_frame.setProperty("role", "card")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setSpacing(12)

        progress_title = QLabel("Key Distribution")
        progress_title.setProperty("role", "title")
        progress_layout.addWidget(progress_title)

        self._progress_bars = {}
        categories = [
            ("Alpha", 0, "#00d4aa"),
            ("Numeric", 0, "#ffb300"),
            ("Special", 0, "#ff6b6b"),
            ("Whitespace", 0, "#747d8c"),
        ]

        for name, value, color in categories:
            bar_layout = QHBoxLayout()
            label = QLabel(f"{name}: 0")
            label.setMinimumWidth(100)
            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(0)
            bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
            bar_layout.addWidget(label)
            bar_layout.addWidget(bar, 1)
            progress_layout.addLayout(bar_layout)
            self._progress_bars[name.lower()] = (label, bar)

        layout.addWidget(progress_frame)

        # Summary text display
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setProperty("role", "text-display")
        layout.addWidget(self._summary_text)

        # Metrics text display
        self._metrics_text = QTextEdit()
        self._metrics_text.setReadOnly(True)
        self._metrics_text.setProperty("role", "text-display")
        layout.addWidget(self._metrics_text)

        # Top keys text display
        self._topkeys_text = QTextEdit()
        self._topkeys_text.setReadOnly(True)
        self._topkeys_text.setProperty("role", "text-display")
        layout.addWidget(self._topkeys_text)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self._btn_refresh = CustomButton("🔄 Refresh", role="secondary")
        self._btn_refresh.clicked.connect(self._refresh_report)
        action_layout.addWidget(self._btn_refresh)

        self._btn_export = CustomButton("📤 Export Report")
        self._btn_export.clicked.connect(self._export_report)
        action_layout.addWidget(self._btn_export)
        layout.addLayout(action_layout)

        layout.addStretch()



    def _update_summary_text(self) -> None:
        """Update the summary tab with placeholder data."""
        summary = """
╔════════════════════════════════════════════════════╗
║       TYPING ANALYTICS REPORT - SUMMARY           ║
╚════════════════════════════════════════════════════╝

📊 SESSION OVERVIEW
─────────────────────────────────────────────────────

  Status              : No Active Session
  Duration            : -- seconds
  Total Keystrokes    : 0

⌨️  TYPING SPEED & TIMING
─────────────────────────────────────────────────────

  Words Per Minute    : -- WPM
  Avg Dwell Time      : -- ms (key hold duration)
  Avg Flight Time     : -- ms (key-to-key interval)
  Rhythm Consistency  : -- / 1.0

📈 KEY STATISTICS
─────────────────────────────────────────────────────

  Alphabet Keys       : 0
  Number Keys         : 0
  Special Keys        : 0
  Whitespace          : 0
  
🎯 TOP KEYS
─────────────────────────────────────────────────────

  • No data available

ℹ️  Notes:
  • Start a capture session to see live analytics
  • Report updates in real-time during capture
  • Session ends when you stop the capture
"""
        self._summary_text.setText(summary)

    def _refresh_report(self) -> None:
        """Refresh the report using current session stats, if available."""
        if self._session_stats:
            self.update_report(self._session_stats)
            return
        QMessageBox.information(self, "Info", "No session data yet. Start capture to view analytics.")

    def _export_report(self) -> None:
        """Export the report to a file."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Report", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self._summary_text.toPlainText())
                QMessageBox.information(self, "Success", f"Report exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export report: {e}")
                logger.exception("Error exporting report")

    def update_report(self, session_stats: dict) -> None:
        """Update the report with new session statistics."""
        self._session_stats = session_stats

        # Generate summary
        duration = session_stats.get("duration", 0)
        total_keystrokes = session_stats.get("total_keystrokes", 0)
        wpm = session_stats.get("wpm", 0)
        avg_dwell = session_stats.get("avg_dwell_ms", 0)
        avg_flight = session_stats.get("avg_flight_ms", 0)
        rhythm_score = session_stats.get("rhythm_score", 0)

        summary = f"""
╔════════════════════════════════════════════════════╗
║       TYPING ANALYTICS REPORT - LIVE             ║
╚════════════════════════════════════════════════════╝

📊 SESSION OVERVIEW
─────────────────────────────────────────────────────

  Duration            : {duration:.1f} seconds
  Total Keystrokes    : {total_keystrokes}

⌨️  TYPING SPEED & TIMING
─────────────────────────────────────────────────────

  Words Per Minute    : {wpm:.1f} WPM
  Avg Dwell Time      : {avg_dwell:.1f} ms
  Avg Flight Time     : {avg_flight:.1f} ms
  Rhythm Consistency  : {rhythm_score:.2f} / 1.0

📈 KEY DISTRIBUTION
─────────────────────────────────────────────────────

  Alphabet Keys       : {session_stats.get("alpha_count", 0)}
  Number Keys         : {session_stats.get("numeric_count", 0)}
  Special Keys        : {session_stats.get("special_count", 0)}
  Whitespace          : {session_stats.get("whitespace_count", 0)}

🎯 TOP 10 KEYS
─────────────────────────────────────────────────────

"""
        top_keys = session_stats.get("top_keys", [])
        top_ten = top_keys[:10]
        max_count = max((count for _, count in top_ten), default=1)
        for i, (key, count) in enumerate(top_ten, 1):
            bar_length = int((count / max_count) * 30)
            bar = "█" * bar_length
            summary += f"  {i:2d}. {str(key):15s} : {int(count):5d}  {bar}\n"

        summary += "\nℹ️  Report generated during active capture session."

        self._summary_text.setText(summary)

        # Update metrics tab
        metrics = f"""
DETAILED METRICS ANALYSIS
════════════════════════════════════════════════════════

Session Duration      : {duration:.2f} seconds
Total Events Recorded : {total_keystrokes}

TYPING DYNAMICS
─────────────────────────────────────────────────────
Words Per Minute (WPM)     : {wpm:.2f}
Average Dwell Time         : {avg_dwell:.2f} ms
Average Flight Time        : {avg_flight:.2f} ms
Rhythm Consistency Score   : {rhythm_score:.3f}

KEY FREQUENCY DISTRIBUTION
─────────────────────────────────────────────────────
Alphabetic Characters      : {session_stats.get("alpha_count", 0)}
Numeric Characters         : {session_stats.get("numeric_count", 0)}
Special/Punctuation        : {session_stats.get("special_count", 0)}
Whitespace (Space/Tab)     : {session_stats.get("whitespace_count", 0)}
Function/Control Keys      : {session_stats.get("function_count", 0)}

CALCULATION NOTES
─────────────────────────────────────────────────────
• WPM = (Character Count / 5) / (Duration in minutes)
• Dwell Time = Time key is held down (press to release)
• Flight Time = Time between consecutive key presses
• Rhythm Score = 1 / (1 + Coefficient of Variation)
  - Score close to 1.0 = Consistent typing rhythm
  - Score close to 0.0 = Erratic typing pattern
"""
        self._metrics_text.setText(metrics)

        # Update top keys tab
        topkeys_text = "TOP KEYS BY FREQUENCY\n" + "=" * 50 + "\n\n"
        for i, (key, count) in enumerate(top_keys, 1):
            topkeys_text += f"{i:2d}. {str(key):20s} {int(count):6d} times\n"

        self._topkeys_text.setText(topkeys_text)
