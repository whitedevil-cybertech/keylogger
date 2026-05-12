"""Reusable widgets for a compact, consistent desktop UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class CustomButton(QPushButton):
    """Compact themed button with role-based styling."""

    def __init__(self, text: str = "", icon: str = "", role: str = "primary") -> None:
        super().__init__(text)
        self.setRole(role)
        self.setMinimumHeight(30)
        self.setCursor(Qt.PointingHandCursor)

    def setRole(self, role: str) -> None:
        self.setProperty("role", role)
        self.style().unpolish(self)
        self.style().polish(self)


class MetricCard(QFrame):
    """Compact metric card with icon/title/value."""

    def __init__(self, icon: str = "", value: str = "0", subtitle: str = "", accent_color: str = "") -> None:
        super().__init__()
        self.setProperty("role", "card")
        self._accent = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self._icon_label = QLabel(icon)
        self._icon_label.setProperty("role", "subtitle")
        top_row.addWidget(self._icon_label)

        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setProperty("role", "subtitle")
        top_row.addWidget(self._subtitle_label, 1)

        layout.addLayout(top_row)

        self._value_label = QLabel(str(value))
        self._value_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        self._value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._value_label)

        if accent_color:
            self.setAccent(accent_color)

    def setValue(self, value: str) -> None:
        self._value_label.setText(str(value))

    def setAccent(self, color: str) -> None:
        self._accent = color
        self._icon_label.setStyleSheet(f"color: {color};")
        self._value_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {color};"
        )


class StatusBadge(QLabel):
    """Status pill for capture state."""

    STATES = {
        "idle": {"text": "Idle", "bg": "rgba(242,185,75,0.14)", "fg": "#f2b94b"},
        "recording": {"text": "Recording", "bg": "rgba(52,211,153,0.16)", "fg": "#34d399"},
        "error": {"text": "Error", "bg": "rgba(227,93,106,0.16)", "fg": "#e35d6a"},
        "paused": {"text": "Paused", "bg": "rgba(130,145,163,0.16)", "fg": "#9aaec1"},
    }

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(26)
        self.setContentsMargins(10, 2, 10, 2)
        self.setStatus("idle")

    def setStatus(self, state: str) -> None:
        config = self.STATES.get(state, self.STATES["idle"])
        self.setText(f"● {config['text']}")
        self.setStyleSheet(
            "QLabel {"
            f"background: {config['bg']};"
            f"color: {config['fg']};"
            "border-radius: 12px;"
            "padding: 2px 10px;"
            "font-size: 11px;"
            "font-weight: 600;"
            "}"
        )


ICONS = {
    "start": "▶",
    "stop": "■",
    "folder": "📁",
    "stats": "📊",
    "report": "📋",
    "logs": "🧾",
    "key": "⌨",
    "time": "⏱",
    "speed": "⚡",
    "rhythm": "◍",
    "warning": "⚠",
    "shield": "🛡",
}
