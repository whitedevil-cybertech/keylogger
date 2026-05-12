"""Logs viewer panel for displaying captured keystroke logs."""

from __future__ import annotations

import itertools
import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .widgets import CustomButton

logger = logging.getLogger(__name__)


class LogFileLoader(QThread):
    """Worker thread for loading large log files asynchronously."""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            if not self.file_path.exists():
                raise FileNotFoundError(f"Log file not found: {self.file_path}")

            content = self.file_path.read_text(encoding="utf-8", errors="replace")
            self.finished.emit(content)
        except Exception as e:
            logger.exception("Error loading log file: %s", e)
            self.error.emit(str(e))


class LogsPanel(QWidget):
    """Panel for viewing and managing keystroke logs."""

    def __init__(self) -> None:
        super().__init__()
        self._current_log_file: Path | None = None
        self._log_dir: Path | None = None
        self._full_content: str = ""
        self._loader_thread: LogFileLoader | None = None
        self._refresh_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Logs")
        title.setProperty("role", "title")
        layout.addWidget(title)

        controls = QFrame()
        controls.setProperty("role", "card")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(8)

        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        file_row.addWidget(QLabel("File"))

        self._file_path = QLineEdit()
        self._file_path.setReadOnly(True)
        self._file_path.setPlaceholderText("No log file selected")
        file_row.addWidget(self._file_path, 1)

        btn_browse = CustomButton("Browse", role="secondary")
        btn_browse.clicked.connect(self._browse_logs)
        file_row.addWidget(btn_browse)

        btn_open_dir = CustomButton("Open Directory", role="secondary")
        btn_open_dir.clicked.connect(self._open_log_directory)
        file_row.addWidget(btn_open_dir)

        controls_layout.addLayout(file_row)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        search_row.addWidget(QLabel("Search"))

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter logs (case-insensitive)")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_input, 1)

        btn_clear_search = CustomButton("Clear", role="secondary")
        btn_clear_search.clicked.connect(self._clear_search)
        search_row.addWidget(btn_clear_search)

        controls_layout.addLayout(search_row)
        layout.addWidget(controls)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximum(0)
        layout.addWidget(self._progress)

        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setStyleSheet(
            "QTextEdit {"
            "font-family: 'JetBrains Mono', 'Cascadia Code', 'Courier New', monospace;"
            "font-size: 11px; line-height: 1.2;"
            "}"
        )
        layout.addWidget(self._text_display, 1)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(6)

        btn_reload = CustomButton("Reload", role="secondary")
        btn_reload.clicked.connect(self._reload_logs)
        footer_row.addWidget(btn_reload)

        btn_copy = CustomButton("Copy All", role="secondary")
        btn_copy.clicked.connect(self._copy_logs)
        footer_row.addWidget(btn_copy)

        self._status_label = QLabel("Ready")
        self._status_label.setProperty("role", "muted")
        footer_row.addWidget(self._status_label)

        footer_row.addStretch()
        layout.addLayout(footer_row)

    def _browse_logs(self) -> None:
        start_dir = self._log_dir or (Path.home() / ".keystroke_analytics")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log File",
            str(start_dir),
            "Log Files (*.log *.enc *.txt);;All Files (*)",
        )
        if file_path:
            self._load_file_async(Path(file_path))

    def _open_log_directory(self) -> None:
        log_dir = self._log_dir or (Path.home() / ".keystroke_analytics")
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
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait()

        self._current_log_file = file_path
        self._file_path.setText(str(file_path))
        self._progress.setVisible(True)
        self._status_label.setText("Loading...")

        self._loader_thread = LogFileLoader(file_path)
        self._loader_thread.finished.connect(self._on_file_loaded)
        self._loader_thread.error.connect(self._on_load_error)
        self._loader_thread.start()

    @Slot(str)
    def _on_file_loaded(self, content: str) -> None:
        self._full_content = content
        self._progress.setVisible(False)
        self._update_display()
        self._status_label.setText(f"Loaded {len(content)} bytes")

    @Slot(str)
    def _on_load_error(self, error_msg: str) -> None:
        self._progress.setVisible(False)
        self._status_label.setText("Error loading file")
        QMessageBox.critical(self, "Error", f"Failed to read log file:\n{error_msg}")
        logger.exception("File load error: %s", error_msg)

    def _on_search_changed(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        if not self._full_content:
            self._text_display.clear()
            return

        search_term = self._search_input.text().strip().lower()

        if search_term:
            lines = self._full_content.split("\n")
            filtered_lines = [line for line in lines if search_term in line.lower()]
            display_text = f"[{len(filtered_lines)} matches]\n\n" + "\n".join(filtered_lines)
        else:
            display_text = self._full_content

        self._text_display.setPlainText(display_text)
        self._highlight_matches(search_term)

    def _highlight_matches(self, search_term: str) -> None:
        if not search_term:
            return

        cursor = QTextCursor(self._text_display.document())
        char_format = QTextCharFormat()
        char_format.setBackground(QColor("#f2b94b"))
        char_format.setForeground(QColor("#111827"))

        while not cursor.isNull():
            cursor = self._text_display.document().find(search_term, cursor)
            if not cursor.isNull():
                cursor.mergeCharFormat(char_format)
                cursor.movePosition(QTextCursor.Right)

    def _clear_search(self) -> None:
        self._search_input.clear()

    def _reload_logs(self) -> None:
        search_dir = self._current_log_file.parent if self._current_log_file else self._log_dir
        if search_dir and search_dir.exists():
            try:
                log_files = list(
                    itertools.chain(search_dir.glob("*.log"), search_dir.glob("*.enc"))
                )
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
            logger.debug(
                "Auto-refresh: no log file available (current_log_file=%s, log_dir=%s)",
                self._current_log_file,
                self._log_dir,
            )

    def _copy_logs(self) -> None:
        text = self._text_display.toPlainText()
        if not text:
            QMessageBox.warning(self, "Nothing to Copy", "No logs loaded.")
            return

        QApplication.clipboard().setText(text)
        self._status_label.setText(f"Copied {len(text)} bytes")

    def set_log_directory(self, log_dir: Path | None) -> None:
        if not log_dir or not log_dir.exists():
            return

        self._log_dir = log_dir
        try:
            log_files = list(itertools.chain(log_dir.glob("*.log"), log_dir.glob("*.enc")))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                self._load_file_async(latest_log)
        except Exception as e:
            logger.exception("Error setting log directory: %s", e)

    def enable_auto_refresh(self, interval_ms: int = 2000) -> None:
        if not self._refresh_timer:
            self._refresh_timer = QTimer()
            self._refresh_timer.timeout.connect(self._reload_logs)

        self._refresh_timer.start(interval_ms)

    def disable_auto_refresh(self) -> None:
        if self._refresh_timer:
            self._refresh_timer.stop()

    def closeEvent(self, event) -> None:
        self.disable_auto_refresh()
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait()
        super().closeEvent(event)
