"""Main GUI window with compact sidebar navigation and dense dashboard layout."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from keystroke_analytics.gui.controller import EngineController, GuiConfigOverrides
from keystroke_analytics.gui.dialogs import ConsentDialog, PassphraseDialog
from keystroke_analytics.gui.panels_logs import LogsPanel
from keystroke_analytics.gui.panels_report import ReportPanel
from keystroke_analytics.gui.panels_stats import StatsPanel

from .widgets import ICONS, CustomButton, MetricCard, StatusBadge

logger = logging.getLogger(__name__)

MAX_ACTIVE_WINDOW_LENGTH = 28
ACTIVE_WINDOW_TRUNCATE_LENGTH = 25


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_path: Path | None,
        log_dir: Path | None,
        encrypt: bool,
        analytics_enabled: bool,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Keystroke Analytics Pro")
        self.resize(1320, 840)
        self.setMinimumSize(960, 620)

        self._config_path = config_path
        self._log_dir = log_dir
        self._encrypt = encrypt
        self._analytics_enabled = analytics_enabled

        self._controller = EngineController()
        self._controller.started.connect(self._on_started)
        self._controller.stopped.connect(self._on_stopped)
        self._controller.error.connect(self._on_error)
        self._controller.stats_updated.connect(self._on_stats_updated)

        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        root_layout.addWidget(self._build_top_bar())

        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.West)
        self._tabs.setDocumentMode(True)
        self._tabs.setProperty("role", "panel")
        self._tabs.setStyleSheet(
            """
            QTabWidget::pane { margin-left: 0px; }
            QTabBar::tab {
                min-width: 148px;
                text-align: left;
                padding: 10px 12px;
                margin: 3px 5px;
            }
            """
        )

        self._capture_tab = self._create_capture_tab()
        self._tabs.addTab(self._capture_tab, f"{ICONS['stats']} Dashboard")

        self._stats_panel = StatsPanel()
        self._stats_panel.set_log_directory(log_dir)
        self._tabs.addTab(self._stats_panel, f"{ICONS['key']} Live Stats")

        self._report_panel = ReportPanel()
        self._tabs.addTab(self._report_panel, f"{ICONS['report']} Analytics")

        self._logs_panel = LogsPanel()
        self._logs_panel.set_log_directory(log_dir)
        self._tabs.addTab(self._logs_panel, f"{ICONS['logs']} Logs")

        root_layout.addWidget(self._tabs, 1)
        self.setCentralWidget(main_widget)

        self._panic = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        self._panic.setWhatsThis("Emergency stop capture")
        self._panic.activated.connect(self._stop_clicked)

        self._btn_start.setToolTip("Start keystroke analytics capture (requires consent)")
        self._btn_stop.setToolTip("Stop capture and generate final report")
        self._btn_choose_log.setToolTip("Select custom log directory")

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_panels)
        self._refresh_timer.setInterval(2000)

        self._refresh_dashboard_cards({})

    def _build_top_bar(self) -> QFrame:
        top = QFrame()
        top.setProperty("role", "panel")

        layout = QHBoxLayout(top)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        title = QLabel("Keystroke Analytics Pro")
        title.setProperty("role", "title")
        layout.addWidget(title)

        self._status_badge = StatusBadge()
        self._status_badge.setStatus("idle")
        layout.addWidget(self._status_badge)

        # Backward compatibility for smoke tests expecting this label.
        self._status = QLabel("Status: Idle")
        self._status.setProperty("role", "muted")
        layout.addWidget(self._status)

        layout.addSpacing(8)

        self._btn_start = CustomButton("Start Capture")
        self._btn_start.clicked.connect(self._start_clicked)
        layout.addWidget(self._btn_start)

        self._btn_stop = CustomButton("Stop Capture", role="danger")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_clicked)
        layout.addWidget(self._btn_stop)

        self._btn_choose_log = CustomButton(f"{ICONS['folder']} Log Directory", role="secondary")
        self._btn_choose_log.clicked.connect(self._choose_log_dir)
        layout.addWidget(self._btn_choose_log)

        self._btn_open_log_dir = CustomButton("Open Logs", role="secondary")
        self._btn_open_log_dir.clicked.connect(self._open_logs_directory)
        layout.addWidget(self._btn_open_log_dir)

        self._session_info = QLabel("Session: idle")
        self._session_info.setProperty("role", "subtitle")
        self._session_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self._session_info, 1)

        return top

    def _create_capture_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        heading = QLabel("Capture Dashboard")
        heading.setProperty("role", "title")
        layout.addWidget(heading)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(8)

        self._dashboard_cards = {
            "total_keys": MetricCard(ICONS["key"], "0", "Total Keys", "#34d399"),
            "wpm": MetricCard(ICONS["speed"], "0.0", "WPM", "#19c7c0"),
            "active_window": MetricCard("🪟", "N/A", "Active Window", "#9fb1c2"),
            "session_duration": MetricCard(ICONS["time"], "00:00:00", "Session Duration", "#f2b94b"),
            "special_keys": MetricCard("⌥", "0", "Special Keys", "#c084fc"),
            "encryption": MetricCard(ICONS["shield"], "Disabled", "Encryption", "#e35d6a"),
        }

        keys = list(self._dashboard_cards.keys())
        for idx, key in enumerate(keys):
            row, col = divmod(idx, 3)
            cards_grid.addWidget(self._dashboard_cards[key], row, col)

        layout.addLayout(cards_grid)

        info_row = QHBoxLayout()
        info_row.setSpacing(8)

        self._capture_info_card = self._build_info_card(
            "Session Configuration",
            [
                f"Log Directory: {self._log_dir or 'default'}",
                f"Encryption: {'Enabled' if self._encrypt else 'Disabled'}",
                f"Analytics: {'Enabled' if self._analytics_enabled else 'Disabled'}",
            ],
        )
        info_row.addWidget(self._capture_info_card, 1)

        quick_card = self._build_info_card(
            "Quick Start",
            [
                "1) Start Capture",
                "2) Monitor Live Stats",
                "3) Stop Capture to end session",
                "Emergency stop: Ctrl+Shift+Q",
            ],
        )
        info_row.addWidget(quick_card, 1)

        layout.addLayout(info_row)

        cap_card = self._build_info_card(
            "Capabilities",
            [
                "Real-time WPM and timing metrics",
                "Rhythm and key pattern analysis",
                "Encrypted log storage support",
                "Live session analytics updates",
            ],
        )
        layout.addWidget(cap_card)

        layout.addStretch(1)
        return widget

    def _build_info_card(self, title: str, lines: list[str]) -> QFrame:
        frame = QFrame()
        frame.setProperty("role", "card")
        box = QVBoxLayout(frame)
        box.setContentsMargins(10, 10, 10, 10)
        box.setSpacing(4)

        title_label = QLabel(title)
        title_label.setProperty("role", "subtitle")
        box.addWidget(title_label)

        labels: list[QLabel] = []
        for line in lines:
            lbl = QLabel(line)
            lbl.setProperty("role", "muted")
            lbl.setWordWrap(True)
            box.addWidget(lbl)
            labels.append(lbl)

        if title == "Session Configuration":
            self._log_dir_label, self._enc_label, self._analytics_label = labels[:3]

        return frame

    def _choose_log_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Log Directory")
        if directory:
            self._log_dir = Path(directory)
            self._stats_panel.set_log_directory(self._log_dir)
            self._logs_panel.set_log_directory(self._log_dir)
            self._log_dir_label.setText(f"Log Directory: {self._log_dir}")

    def _open_logs_directory(self) -> None:
        self._tabs.setCurrentWidget(self._logs_panel)
        self._logs_panel._open_log_directory()

    def _start_clicked(self) -> None:
        consent = ConsentDialog()
        if consent.exec() != QDialog.Accepted or not consent.accepted_with_consent():
            QMessageBox.warning(self, "Consent Required", "Consent not given.")
            return

        passphrase = None
        if self._encrypt:
            dlg = PassphraseDialog()
            if dlg.exec() != QDialog.Accepted:
                return
            passphrase = dlg.passphrase()
            if not passphrase:
                QMessageBox.warning(self, "Passphrase Required", "Passphrase is required.")
                return

        overrides = GuiConfigOverrides(
            config_path=self._config_path,
            log_dir=self._log_dir,
            encrypt=self._encrypt,
            analytics_enabled=self._analytics_enabled,
            passphrase=passphrase,
        )
        self._controller.start(overrides)

    def _stop_clicked(self) -> None:
        self._controller.stop()
        self._refresh_timer.stop()

    def _on_started(self) -> None:
        self._status_badge.setStatus("recording")
        self._status.setText("Status: Recording")
        self.setWindowTitle("Keystroke Analytics Pro - Recording")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_choose_log.setEnabled(False)

        self._logs_panel.enable_auto_refresh(interval_ms=2000)

    def _on_stopped(self) -> None:
        self._status_badge.setStatus("idle")
        self._status.setText("Status: Idle")
        self.setWindowTitle("Keystroke Analytics Pro")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_choose_log.setEnabled(True)
        self._refresh_timer.stop()

        self._logs_panel.disable_auto_refresh()
        self._stats_panel.reset_display()
        self._refresh_dashboard_cards({})
        self._session_info.setText("Session: idle")

        if self._log_dir:
            self._logs_panel.set_log_directory(self._log_dir)

    def _on_error(self, message: str) -> None:
        self._status_badge.setStatus("error")
        self._status.setText("Status: Error")
        logger.error("Capture error: %s", message)
        QMessageBox.critical(self, "Capture Error", f"An error occurred:\n\n{message}")

    def _on_stats_updated(self, stats: dict) -> None:
        if not stats:
            return

        try:
            logger.debug(
                "UI stats update received: ks=%d wpm=%.1f",
                stats.get("total_keystrokes", 0),
                stats.get("wpm", 0),
            )
            self._stats_panel.update_stats(stats)
            self._report_panel.update_report(stats)
            self._refresh_dashboard_cards(stats)
        except Exception as e:
            logger.exception("Error updating panels: %s", e)

    def _refresh_dashboard_cards(self, stats: dict) -> None:
        duration = float(stats.get("duration", 0)) if stats else 0.0
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        duration_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        total = int(stats.get("total_keystrokes", 0)) if stats else 0
        wpm = float(stats.get("wpm", 0)) if stats else 0.0

        active_window = (
            stats.get("active_window")
            or stats.get("current_window")
            or stats.get("window_title")
            or "N/A"
        )
        if len(str(active_window)) > MAX_ACTIVE_WINDOW_LENGTH:
            active_window = f"{str(active_window)[:ACTIVE_WINDOW_TRUNCATE_LENGTH]}..."

        special_keys = int(stats.get("special_count", 0)) if stats else 0

        self._dashboard_cards["total_keys"].setValue(f"{total:,}")
        self._dashboard_cards["wpm"].setValue(f"{wpm:.1f}")
        self._dashboard_cards["active_window"].setValue(str(active_window))
        self._dashboard_cards["session_duration"].setValue(duration_text)
        self._dashboard_cards["special_keys"].setValue(str(special_keys))
        self._dashboard_cards["encryption"].setValue("Enabled" if self._encrypt else "Disabled")

        if stats:
            self._session_info.setText(
                f"Session: {duration_text} • WPM {wpm:.1f} • Keys {total:,}"
            )

    def _refresh_panels(self) -> None:
        pass

    def closeEvent(self, event: QCloseEvent) -> None:
        try:
            if self._controller.running:
                logger.info("Stopping capture before exit...")
                self._controller.stop()

            self._logs_panel.disable_auto_refresh()
            self._refresh_timer.stop()
        except Exception as e:
            logger.exception("Error during cleanup: %s", e)

        event.accept()
