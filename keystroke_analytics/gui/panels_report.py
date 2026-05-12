"""Analytics report panel with compact overview cards and structured report tabs."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .widgets import ICONS, CustomButton, MetricCard

logger = logging.getLogger(__name__)


class ReportPanel(QWidget):
    """Panel for displaying typing analytics reports and session statistics."""

    def __init__(self) -> None:
        super().__init__()
        self._session_stats: dict | None = None
        self._init_ui()
        self._update_summary_text()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Analytics")
        title.setProperty("role", "title")
        layout.addWidget(title)

        self._hero_frame = QFrame()
        self._hero_frame.setProperty("role", "card")
        hero_layout = QGridLayout(self._hero_frame)
        hero_layout.setContentsMargins(10, 10, 10, 10)
        hero_layout.setSpacing(8)

        self._wpm_card = MetricCard(ICONS.get("speed", "⚡"), "0.0", "Words per Minute", "#19c7c0")
        self._rhythm_card = MetricCard(ICONS.get("rhythm", "◍"), "0.00", "Rhythm Score", "#60a5fa")
        self._keystrokes_card = MetricCard(ICONS.get("key", "⌨"), "0", "Total Keystrokes", "#34d399")

        hero_layout.addWidget(self._wpm_card, 0, 0)
        hero_layout.addWidget(self._rhythm_card, 0, 1)
        hero_layout.addWidget(self._keystrokes_card, 0, 2)
        layout.addWidget(self._hero_frame)

        distribution_frame = QFrame()
        distribution_frame.setProperty("role", "card")
        distribution_layout = QVBoxLayout(distribution_frame)
        distribution_layout.setContentsMargins(10, 10, 10, 10)
        distribution_layout.setSpacing(8)

        distribution_title = QLabel("Key Distribution")
        distribution_title.setProperty("role", "subtitle")
        distribution_layout.addWidget(distribution_title)

        self._progress_bars: dict[str, tuple[QLabel, QProgressBar]] = {}
        for category in ("Alpha", "Numeric", "Special", "Whitespace"):
            row = QHBoxLayout()
            row.setSpacing(8)
            label = QLabel(f"{category}: 0")
            label.setMinimumWidth(120)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFormat("%p%")
            row.addWidget(label)
            row.addWidget(bar, 1)
            distribution_layout.addLayout(row)
            self._progress_bars[category.lower()] = (label, bar)

        layout.addWidget(distribution_frame)

        self._report_tabs = QTabWidget()
        self._report_tabs.setDocumentMode(True)

        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._report_tabs.addTab(self._summary_text, "Summary")

        self._metrics_text = QTextEdit()
        self._metrics_text.setReadOnly(True)
        self._report_tabs.addTab(self._metrics_text, "Detailed Metrics")

        self._topkeys_text = QTextEdit()
        self._topkeys_text.setReadOnly(True)
        self._report_tabs.addTab(self._topkeys_text, "Top Keys")

        layout.addWidget(self._report_tabs, 1)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self._btn_refresh = CustomButton("Refresh", role="secondary")
        self._btn_refresh.clicked.connect(self._refresh_report)
        action_layout.addWidget(self._btn_refresh)

        self._btn_export = CustomButton("Export Report")
        self._btn_export.clicked.connect(self._export_report)
        action_layout.addWidget(self._btn_export)
        layout.addLayout(action_layout)

    def _update_summary_text(self) -> None:
        self._summary_text.setPlainText(
            "No active session.\n\n"
            "Start a capture session to view analytics summaries, distribution, and top keys."
        )
        self._metrics_text.setPlainText("Detailed metrics will appear during capture.")
        self._topkeys_text.setPlainText("Top key frequency list will appear during capture.")

    def _refresh_report(self) -> None:
        QMessageBox.information(self, "Info", "Report auto-updates during active capture.")

    def _export_report(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            "",
            "Text Files (*.txt);;All Files (*)",
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
        self._session_stats = session_stats

        duration = float(session_stats.get("duration", 0))
        total_keystrokes = int(session_stats.get("total_keystrokes", 0))
        wpm = float(session_stats.get("wpm", 0))
        avg_dwell = float(session_stats.get("avg_dwell_ms", 0))
        avg_flight = float(session_stats.get("avg_flight_ms", 0))
        rhythm_score = float(session_stats.get("rhythm_score", 0))

        self._wpm_card.setValue(f"{wpm:.1f}")
        self._rhythm_card.setValue(f"{rhythm_score:.2f}")
        self._keystrokes_card.setValue(f"{total_keystrokes:,}")

        alpha = int(session_stats.get("alpha_count", 0))
        numeric = int(session_stats.get("numeric_count", 0))
        special = int(session_stats.get("special_count", 0))
        whitespace = int(session_stats.get("whitespace_count", 0))
        distribution_total = max(alpha + numeric + special + whitespace, 1)

        distribution_map = {
            "alpha": alpha,
            "numeric": numeric,
            "special": special,
            "whitespace": whitespace,
        }
        for key, count in distribution_map.items():
            label, bar = self._progress_bars[key]
            pct = int((count / distribution_total) * 100)
            label.setText(f"{key.title()}: {count}")
            bar.setValue(pct)

        top_keys = session_stats.get("top_keys", [])

        summary_lines = [
            "SESSION OVERVIEW",
            "----------------",
            f"Duration: {duration:.1f} seconds",
            f"Total Keystrokes: {total_keystrokes}",
            "",
            "TYPING DYNAMICS",
            "---------------",
            f"WPM: {wpm:.1f}",
            f"Average Dwell: {avg_dwell:.1f} ms",
            f"Average Flight: {avg_flight:.1f} ms",
            f"Rhythm Score: {rhythm_score:.2f}",
            "",
            "TOP KEYS",
            "--------",
        ]
        if top_keys:
            for i, (key, count) in enumerate(top_keys[:10], 1):
                summary_lines.append(f"{i:2d}. {key:<14} {count:>6}")
        else:
            summary_lines.append("No key data available yet.")

        self._summary_text.setPlainText("\n".join(summary_lines))

        metrics_text = (
            "DETAILED METRICS\n"
            "================\n\n"
            f"Session Duration: {duration:.2f} seconds\n"
            f"Total Events: {total_keystrokes}\n\n"
            "Typing Dynamics\n"
            "---------------\n"
            f"WPM: {wpm:.2f}\n"
            f"Average Dwell Time: {avg_dwell:.2f} ms\n"
            f"Average Flight Time: {avg_flight:.2f} ms\n"
            f"Rhythm Consistency: {rhythm_score:.3f}\n\n"
            "Key Distribution\n"
            "----------------\n"
            f"Alphabetic: {alpha}\n"
            f"Numeric: {numeric}\n"
            f"Special/Punctuation: {special}\n"
            f"Whitespace: {whitespace}\n"
            f"Function/Control: {int(session_stats.get('function_count', 0))}\n"
        )
        self._metrics_text.setPlainText(metrics_text)

        topkeys_lines = ["TOP KEYS BY FREQUENCY", "====================="]
        if top_keys:
            topkeys_lines.extend(
                f"{i:2d}. {key:<20} {count:>6}"
                for i, (key, count) in enumerate(top_keys, 1)
            )
        else:
            topkeys_lines.append("No key data available yet.")

        self._topkeys_text.setPlainText("\n".join(topkeys_lines))
