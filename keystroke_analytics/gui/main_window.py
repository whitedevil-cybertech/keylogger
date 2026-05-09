"""
Main GUI window with tabbed interface for capture, logs, and reports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
    QTabWidget,
    QWidget,
    QFrame,
)

from .widgets import CustomButton, StatusBadge, MetricCard, ICONS
from .theme import Theme

from keystroke_analytics.gui.controller import EngineController, GuiConfigOverrides
from keystroke_analytics.gui.dialogs import ConsentDialog, PassphraseDialog
from keystroke_analytics.gui.panels_logs import LogsPanel
from keystroke_analytics.gui.panels_report import ReportPanel
from keystroke_analytics.gui.panels_stats import StatsPanel

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_path: Optional[Path],
        log_dir: Optional[Path],
        encrypt: bool,
        analytics_enabled: bool,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Keystroke Analytics Pro")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 700)

        self._config_path = config_path
        self._log_dir = log_dir
        self._encrypt = encrypt
        self._analytics_enabled = analytics_enabled

        self._controller = EngineController()
        self._controller.started.connect(self._on_started)
        self._controller.stopped.connect(self._on_stopped)
        self._controller.error.connect(self._on_error)
        self._controller.stats_updated.connect(self._on_stats_updated)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Modern control bar with StatusBadge and CustomButtons
        control_frame = QFrame()
        control_frame.setProperty("role", "card")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(16, 12, 16, 12)
        control_layout.setSpacing(12)

        # Status badge
        self._status_badge = StatusBadge()
        self._status_badge.setStatus("idle")
        control_layout.addWidget(self._status_badge)

        # Config info
        config_label = QLabel("Configuration Active")
        config_label.setProperty("role", "subtitle")
        config_label.setStyleSheet("font-size: 11px;")
        control_layout.addWidget(config_label)
        control_layout.addSpacing(12)

        # Log directory selector
        self._btn_choose_log = CustomButton(ICONS['folder'] + " Log Directory", role="secondary")
        self._btn_choose_log.clicked.connect(self._choose_log_dir)
        self._btn_choose_log.setMaximumHeight(32)
        control_layout.addWidget(self._btn_choose_log)

        # Primary action buttons
        btn_group = QHBoxLayout()
        btn_group.setSpacing(8)
        
        self._btn_start = CustomButton(ICONS['start'] + " Start Capture")
        self._btn_start.clicked.connect(self._start_clicked)
        self._btn_start.setMaximumHeight(32)
        btn_group.addWidget(self._btn_start)

        self._btn_stop = CustomButton(ICONS['stop'] + " Stop Capture", role="danger")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_clicked)
        self._btn_stop.setMaximumHeight(32)
        btn_group.addWidget(self._btn_stop)

        control_layout.addLayout(btn_group)
        control_layout.addStretch()

        main_layout.addWidget(control_frame)

        # Tabbed interface
        self._tabs = QTabWidget()

        # Capture tab
        # Enhanced tabbed interface with modern styling
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabBar::tab { height: 42px; padding: 12px 24px; font-weight: 500; }
            QTabWidget::pane { border: 1px solid #2a3443; border-radius: 12px; margin-top: 8px; }
        """)

        # Tabs
        self._capture_tab = self._create_capture_tab()
        self._tabs.addTab(self._capture_tab, ICONS['stats'] + " Dashboard")

        self._stats_panel = StatsPanel()
        self._stats_panel.set_log_directory(log_dir)
        self._tabs.addTab(self._stats_panel, ICONS['key'] + " Live Stats")

        self._report_panel = ReportPanel()
        self._tabs.addTab(self._report_panel, ICONS['report'] + " Analytics")

        self._logs_panel = LogsPanel()
        self._logs_panel.set_log_directory(log_dir)
        self._tabs.addTab(self._logs_panel, ICONS['logs'] + " Logs")

        main_layout.addWidget(self._tabs, 1)
        main_layout.setSpacing(0)

        self.setCentralWidget(main_widget)

        # Enhanced shortcuts with tooltips
        self._panic = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        self._panic.setWhatsThis("Emergency stop capture")
        self._panic.activated.connect(self._stop_clicked)

        self._btn_start.setToolTip("Start keystroke analytics capture (requires consent)")
        self._btn_stop.setToolTip("Stop capture and generate final report")
        self._btn_choose_log.setToolTip("Select custom log directory")

        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_panels)
        self._refresh_timer.setInterval(2000)  # 2s for smoother perf

    def _create_capture_tab(self) -> QWidget:
        """Create the main capture control tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("📝 Keystroke Capture Control")
        title.setProperty("role", "title")
        layout.addWidget(title)

        # Config Info Card - Compact
        config_frame = QFrame()
        config_frame.setProperty("role", "card")
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(6)
        config_layout.setContentsMargins(12, 10, 12, 10)

        self._log_dir_label = QLabel(f"📁 Log Directory: {self._log_dir or 'default'}")
        self._enc_label = QLabel(f"🔐 Encryption: {'Enabled' if self._encrypt else 'Disabled'}")
        self._analytics_label = QLabel(f"📊 Analytics: {'Enabled' if self._analytics_enabled else 'Disabled'}")

        for label in [self._log_dir_label, self._enc_label, self._analytics_label]:
            label.setProperty("role", "subtitle")
            label.setStyleSheet("font-size: 12px; padding: 2px;")
            config_layout.addWidget(label)

        layout.addWidget(config_frame)

        # Instructions Card - Compact
        instructions_frame = QFrame()
        instructions_frame.setProperty("role", "card")
        instructions_layout = QVBoxLayout(instructions_frame)
        instructions_layout.setSpacing(4)
        instructions_layout.setContentsMargins(12, 10, 12, 10)

        instructions_title = QLabel("📋 Quick Start")
        instructions_title.setProperty("role", "subtitle")
        instructions_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        instructions_layout.addWidget(instructions_title)

        instructions = QLabel(
            "1. Click 'Start Capture' to begin • 2. View stats in Live Stats tab\n"
            "3. Stop capture when done • 4. Press Ctrl+Shift+Q to emergency stop"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-size: 11px; padding: 2px;")
        instructions_layout.addWidget(instructions)

        layout.addWidget(instructions_frame)

        # Features Card - Compact
        features_frame = QFrame()
        features_frame.setProperty("role", "card")
        features_layout = QVBoxLayout(features_frame)
        features_layout.setSpacing(4)
        features_layout.setContentsMargins(12, 10, 12, 10)

        features_title = QLabel("✨ Capabilities")
        features_title.setProperty("role", "subtitle")
        features_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        features_layout.addWidget(features_title)

        features = QLabel(
            "⚡ Real-time WPM • 🎵 Rhythm Analysis • 📈 Key Patterns • 💾 Encrypted Logs"
        )
        features.setWordWrap(True)
        features.setStyleSheet("font-size: 11px; padding: 2px;")
        features_layout.addWidget(features)

        layout.addWidget(features_frame)

        layout.addStretch()

        return widget

    def _choose_log_dir(self) -> None:
        """Update log directory and refresh panels."""
        directory = QFileDialog.getExistingDirectory(self, "Select Log Directory")
        if directory:
            self._log_dir = Path(directory)
            self._stats_panel.set_log_directory(self._log_dir)
            self._logs_panel.set_log_directory(self._log_dir)

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
        self._refresh_timer.start(1000)  # Update every second

    def _stop_clicked(self) -> None:
        self._controller.stop()
        self._refresh_timer.stop()

    def _on_started(self) -> None:
        """Called when capture starts."""
        self._status_badge.setStatus("recording")
        self.setWindowTitle("Keystroke Analytics Pro - 🔴 Recording")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_choose_log.setEnabled(False)
        
        # Enable auto-refresh of logs during capture
        self._logs_panel.enable_auto_refresh(interval_ms=2000)
        
        # Start stats polling timer
        self._refresh_timer.start(500)  # Update stats every 500ms for smooth display

    def _on_stopped(self) -> None:
        """Called when capture stops."""
        self._status_badge.setStatus("idle")
        self.setWindowTitle("Keystroke Analytics Pro")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_choose_log.setEnabled(True)
        self._refresh_timer.stop()
        
        # Disable auto-refresh of logs
        self._logs_panel.disable_auto_refresh()
        
        # Reset stats display
        self._stats_panel.reset_display()
        
        # Reload logs to show final session
        if self._log_dir:
            self._logs_panel.set_log_directory(self._log_dir)

    def _on_error(self, message: str) -> None:
        """Called when an error occurs."""
        self._status_badge.setStatus("error")
        logger.error("Capture error: %s", message)
        QMessageBox.critical(self, "Capture Error", f"An error occurred:\n\n{message}")

    def _on_stats_updated(self, stats: dict) -> None:
        """
        Handle stats update signal from controller.
        
        Called periodically during capture to update UI with live statistics.
        """
        if not stats:
            return
        
        try:
            self._stats_panel.update_stats(stats)
            if self._report_panel:
                self._report_panel.update_report(stats)
        except Exception as e:
            logger.exception("Error updating panels: %s", e)

    def _refresh_panels(self) -> None:
        """
        Periodic refresh of stats during capture.
        
        Called by _refresh_timer to poll engine for latest stats.
        """
        if self._controller.running:
            try:
                stats = self._controller.get_current_stats()
                if stats:
                    self._on_stats_updated(stats)
            except Exception as e:
                logger.exception("Error refreshing stats: %s", e)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up before closing window."""
        try:
            # Stop capture if running
            if self._controller.running:
                logger.info("Stopping capture before exit...")
                self._controller.stop()
            
            # Disable auto-refresh
            self._logs_panel.disable_auto_refresh()
            self._refresh_timer.stop()
            
        except Exception as e:
            logger.exception("Error during cleanup: %s", e)
        
        event.accept()