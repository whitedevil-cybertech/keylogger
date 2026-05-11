"""
Logs viewer panel for displaying captured keystroke logs.

Supports async loading of large files and background refresh during active capture.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class LogFileLoader(QThread):
    """Worker thread for loading large log files asynchronously."""

    finished = Signal(str)  # Content loaded
    error = Signal(str)     # Error occurred

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        """Load the file in this thread."""
        try:
            if not self.file_path.exists():
                raise FileNotFoundError(f"Log file not found: {self.file_path}")

            # Read file with error handling
            content = self.file_path.read_text(encoding="utf-8", errors="replace")
            self.finished.emit(content)

        except Exception as e:
            logger.exception("Error loading log file: %s", e)
            self.error.emit(str(e))


class LogsPanel(QWidget):
    """
    Panel for viewing and managing keystroke logs.

    Features:
    - Async file loading (no UI freeze on large files)
    - Search with highlighting
    - Auto-refresh during capture
    - Copy to clipboard
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_log_file: Path | None = None
        self._log_dir: Path | None = None  # remembered for auto-refresh discovery
        self._full_content: str = ""
        self._loader_thread: LogFileLoader | None = None
        self._refresh_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("📋 Keystroke Logs Viewer")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # File selection row
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Log File:"))
        self._file_path = QLineEdit()
        self._file_path.setReadOnly(True)
        file_layout.addWidget(self._file_path, 1)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_logs)
        file_layout.addWidget(btn_browse)

        btn_open_dir = QPushButton("📁 Open Directory")
        btn_open_dir.clicked.connect(self._open_log_directory)
        file_layout.addWidget(btn_open_dir)

        layout.addLayout(file_layout)

        # Search row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Enter text to search (case-insensitive)...")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input, 1)

        btn_clear_search = QPushButton("Clear")
        btn_clear_search.clicked.connect(self._clear_search)
        search_layout.addWidget(btn_clear_search)

        layout.addLayout(search_layout)

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximum(0)  # Indeterminate progress
        layout.addWidget(self._progress)

        # Text display with monospace font
        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setStyleSheet(
            "QTextEdit { font-family: 'Courier New', monospace; font-size: 9pt; }"
        )
        layout.addWidget(self._text_display)

        # Action buttons
        action_layout = QHBoxLayout()

        btn_reload = QPushButton("🔄 Reload")
        btn_reload.clicked.connect(self._reload_logs)
        action_layout.addWidget(btn_reload)

        btn_copy = QPushButton("📋 Copy All")
        btn_copy.clicked.connect(self._copy_logs)
        action_layout.addWidget(btn_copy)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("font-size: 10px; color: #666;")
        action_layout.addWidget(self._status_label)

        action_layout.addStretch()
        layout.addLayout(action_layout)

    def _browse_logs(self) -> None:
        """Browse for a log file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log File",
            str(Path.home() / ".keystroke_analytics"),
            "Log Files (*.log *.enc *.txt);;All Files (*)"
        )
        if file_path:
            self._load_file_async(Path(file_path))

    def _open_log_directory(self) -> None:
        """Open the log directory in file explorer."""
        log_dir = Path.home() / ".keystroke_analytics"
        if not log_dir.exists():
            QMessageBox.information(self, "No Logs", f"Log directory not found: {log_dir}")
            return

        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer "{log_dir}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_dir)])
            else:
                subprocess.Popen(["xdg-open", str(log_dir)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open directory: {e}")
            logger.exception("Error opening directory: %s", e)

    def _load_file_async(self, file_path: Path) -> None:
        """Load a log file asynchronously."""
        # Stop any existing loader
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait()

        self._current_log_file = file_path
        self._file_path.setText(str(file_path))
        self._progress.setVisible(True)
        self._status_label.setText("Loading...")

        # Create and start loader thread
        self._loader_thread = LogFileLoader(file_path)
        self._loader_thread.finished.connect(self._on_file_loaded)
        self._loader_thread.error.connect(self._on_load_error)
        self._loader_thread.start()

    @Slot(str)
    def _on_file_loaded(self, content: str) -> None:
        """Called when file loading completes."""
        self._full_content = content
        self._progress.setVisible(False)
        self._update_display()
        self._status_label.setText(f"Loaded {len(content)} bytes")

    @Slot(str)
    def _on_load_error(self, error_msg: str) -> None:
        """Called when file loading fails."""
        self._progress.setVisible(False)
        self._status_label.setText("Error loading file")
        QMessageBox.critical(self, "Error", f"Failed to read log file:\n{error_msg}")
        logger.exception("File load error: %s", error_msg)

    def _on_search_changed(self) -> None:
        """Called when search text changes (with minimal throttling)."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the text display based on current search term."""
        if not self._full_content:
            return

        search_term = self._search_input.text().lower()

        if search_term:
            # Filter lines by search term
            lines = self._full_content.split("\n")
            filtered_lines = [line for line in lines if search_term in line.lower()]
            display_text = f"[{len(filtered_lines)} matches found]\n\n" + "\n".join(filtered_lines)
        else:
            display_text = self._full_content

        self._text_display.setPlainText(display_text)
        self._highlight_matches(search_term)

    def _highlight_matches(self, search_term: str) -> None:
        """Highlight all occurrences of search_term in the text display."""
        if not search_term:
            return

        cursor = QTextCursor(self._text_display.document())
        format = QTextCharFormat()
        format.setBackground(QColor("#ffb300"))
        format.setForeground(QColor("#000000"))

        while not cursor.isNull():
            cursor = self._text_display.document().find(search_term, cursor)
            if not cursor.isNull():
                cursor.mergeCharFormat(format)
                cursor.movePosition(QTextCursor.Right)

    def _clear_search(self) -> None:
        """Clear the search input and display full logs."""
        self._search_input.clear()

    def _reload_logs(self) -> None:
        """Reload the current log file, or discover the newest one in the log directory."""
        # During active capture a new log file may have been created since the
        # last set_log_directory() call.  Always resolve to the most-recently
        # modified file in the directory so the live session log is shown.
        search_dir = (
            self._current_log_file.parent if self._current_log_file else self._log_dir
        )
        if search_dir and search_dir.exists():
            try:
                log_files = list(search_dir.glob("*.log")) + list(search_dir.glob("*.enc"))
                if log_files:
                    latest = max(log_files, key=lambda p: p.stat().st_mtime)
                    if latest != self._current_log_file:
                        self._current_log_file = latest
                        self._file_path.setText(str(latest))
            except Exception as e:
                logger.exception("Error finding latest log file: %s", e)

        if self._current_log_file:
            self._load_file_async(self._current_log_file)
        else:
            logger.debug("Auto-refresh: no log file available yet")

    def _copy_logs(self) -> None:
        """Copy logs to clipboard."""
        from PySide6.QtWidgets import QApplication

        text = self._text_display.toPlainText()
        if not text:
            QMessageBox.warning(self, "Nothing to Copy", "No logs loaded.")
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self._status_label.setText(f"Copied {len(text)} bytes to clipboard")

    def set_log_directory(self, log_dir: Path | None) -> None:
        """
        Set the default log directory and load the most recent log.

        Args:
            log_dir: Path to log directory
        """
        if not log_dir or not log_dir.exists():
            return

        self._log_dir = log_dir  # remember for auto-refresh

        try:
            # Find the most recent log file
            log_files = list(log_dir.glob("*.log")) + list(log_dir.glob("*.enc"))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                self._load_file_async(latest_log)
        except Exception as e:
            logger.exception("Error setting log directory: %s", e)

    def enable_auto_refresh(self, interval_ms: int = 2000) -> None:
        """
        Enable auto-refresh of logs at regular intervals (useful during capture).

        Args:
            interval_ms: Refresh interval in milliseconds
        """
        if not self._refresh_timer:
            self._refresh_timer = QTimer()
            self._refresh_timer.timeout.connect(self._reload_logs)

        self._refresh_timer.start(interval_ms)

    def disable_auto_refresh(self) -> None:
        """Disable auto-refresh."""
        if self._refresh_timer:
            self._refresh_timer.stop()

    def closeEvent(self, event) -> None:
        """Clean up before closing."""
        self.disable_auto_refresh()
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait()
        super().closeEvent(event)
