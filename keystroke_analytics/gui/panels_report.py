"""Analytics report panel with compact overview cards and structured report tabs."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Slot
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
_DISTRIBUTION_LABEL_MIN_WIDTH = 104


class ReportPanel(QWidget):
    """Panel for displaying typing analytics reports and session statistics."""

    def __init__(self) -> None:
        super().__init__()
        self._session_stats: dict | None = None
        self._progress_bars: dict[str, tuple[QLabel, QProgressBar]] = {}
        self._init_ui()
        self._set_placeholder_text()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Analytics")
        title.setProperty("role", "title")
        main_layout.addWidget(title)

        cards_frame = QFrame()
        cards_frame.setProperty("role", "card")
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(10, 10, 10, 10)
        cards_layout.setSpacing(8)

        self._wpm_card = MetricCard(ICONS.get("speed", "⚡"), "0.0", "Words per Minute", "#19c7c0")
        self._rhythm_card = MetricCard(ICONS.get("rhythm", "◍"), "0.00", "Rhythm Score", "#60a5fa")
        self._keystrokes_card = MetricCard(ICONS.get("key", "⌨"), "0", "Total Keystrokes", "#34d399")

        cards_layout.addWidget(self._wpm_card, 0, 0)
        cards_layout.addWidget(self._rhythm_card, 0, 1)
        cards_layout.addWidget(self._keystrokes_card, 0, 2)
        main_layout.addWidget(cards_frame)

        main_layout.addWidget(self._build_distribution_frame())

        self._report_tabs = QTabWidget()
        self._report_tabs.setDocumentMode(True)
        self._summary_text = self._create_report_text()
        self._metrics_text = self._create_report_text()
        self._topkeys_text = self._create_report_text()
        self._report_tabs.addTab(self._summary_text, "Summary")
        self._report_tabs.addTab(self._metrics_text, "Detailed Metrics")
        self._report_tabs.addTab(self._topkeys_text, "Top Keys")
        main_layout.addWidget(self._report_tabs, 1)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self._btn_refresh = CustomButton("Refresh", role="secondary")
        self._btn_refresh.clicked.connect(self._refresh_report)
        action_layout.addWidget(self._btn_refresh)

        self._btn_export = CustomButton("Export Report")
        self._btn_export.clicked.connect(self._export_report)
        action_layout.addWidget(self._btn_export)
        main_layout.addLayout(action_layout)

    def _build_distribution_frame(self) -> QFrame:
        frame = QFrame()
        frame.setProperty("role", "card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Key Distribution")
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        for category in ("Alpha", "Numeric", "Special", "Whitespace"):
            row = QHBoxLayout()
            row.setSpacing(8)

            label = QLabel(f"{category}: 0")
            label.setMinimumWidth(_DISTRIBUTION_LABEL_MIN_WIDTH)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFormat("%p%")

            row.addWidget(label)
            row.addWidget(bar, 1)
            layout.addLayout(row)
            self._progress_bars[category.lower()] = (label, bar)

        return frame

    def _create_report_text(self) -> QTextEdit:
        text = QTextEdit()
        text.setReadOnly(True)
        return text

    def _set_placeholder_text(self) -> None:
        self._summary_text.setPlainText(
            "No active session.\n\n"
            "Start a capture session to view analytics summaries, distribution, and top keys."
        )
        self._metrics_text.setPlainText("Detailed metrics will appear during capture.")
        self._topkeys_text.setPlainText("Top key frequency list will appear during capture.")

    def _refresh_report(self) -> None:
        if self._session_stats:
            self.update_report(self._session_stats)
            return
        QMessageBox.information(
            self,
            "Info",
            "No session data yet. Report auto-updates during active capture.",
        )

    def _export_report(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return

        try:
            if Path(file_path).exists():
                overwrite = QMessageBox.question(
                    self,
                    "Overwrite File?",
                    f"The file already exists:\n{file_path}\n\nDo you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if overwrite != QMessageBox.Yes:
                    return

            with open(file_path, "w", encoding="utf-8") as file_handle:
                file_handle.write(self._summary_text.toPlainText())
            QMessageBox.information(self, "Success", f"Report exported to:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to export report: {exc}")
            logger.exception("Error exporting report")

    @Slot(dict)
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
        function_count = int(session_stats.get("function_count", 0))
        distribution_total = max(alpha + numeric + special + whitespace, 1)

        distribution_map = {
            "alpha": alpha,
            "numeric": numeric,
            "special": special,
            "whitespace": whitespace,
        }
        for key, count in distribution_map.items():
            label, bar = self._progress_bars[key]
            label.setText(f"{key.title()}: {count}")
            bar.setValue(int((count / distribution_total) * 100))

        top_keys_raw = session_stats.get("top_keys", [])
        top_keys: list[tuple[str, int]] = []
        for item in top_keys_raw:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                top_keys.append((str(item[0]), int(item[1])))

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
            for index, (key, count) in enumerate(top_keys[:10], 1):
                summary_lines.append(f"{index:2d}. {key:<14} {count:>6}")
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
            f"Function/Control: {function_count}\n"
        )
        self._metrics_text.setPlainText(metrics_text)

        topkeys_lines = ["TOP KEYS BY FREQUENCY", "====================="]
        if top_keys:
            topkeys_lines.extend(
                f"{index:2d}. {key:<20} {count:>6}"
                for index, (key, count) in enumerate(top_keys, 1)
            )
        else:
            topkeys_lines.append("No key data available yet.")
        self._topkeys_text.setPlainText("\n".join(topkeys_lines))
