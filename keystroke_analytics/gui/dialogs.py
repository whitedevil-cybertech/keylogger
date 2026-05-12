"""
GUI dialogs for consent and passphrase input.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .theme import Theme


class ConsentDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Consent Required")
        self.setProperty("role", "dialog")
        self._init_ui()
        self._apply_theme()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        message = QLabel(
            "This tool captures keystrokes. Use only with explicit authorization.\n\n"
            "By continuing, you confirm you have consent to monitor this device."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        self._check = QCheckBox("I understand and have authorization")
        self._check.setChecked(False)
        layout.addWidget(self._check)

        layout.addSpacing(16)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_theme(self) -> None:
        """Apply theme styling to dialog."""
        style = f"""
        QDialog {{
            background-color: {Theme.COLORS['bg_card']};
            color: {Theme.COLORS['text_primary']};
        }}
        QLabel {{
            color: {Theme.COLORS['text_primary']};
            font-size: 11pt;
        }}
        QCheckBox {{
            color: {Theme.COLORS['text_primary']};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        QDialogButtonBox {{
            button-spacing: 8px;
        }}
        QPushButton {{
            background-color: {Theme.COLORS['accent_soft']};
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Theme.COLORS['accent']};
        }}
        """
        self.setStyleSheet(style)

    def accepted_with_consent(self) -> bool:
        return self._check.isChecked()


class PassphraseDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Encryption Passphrase")
        self.setProperty("role", "dialog")
        self._init_ui()
        self._apply_theme()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        label = QLabel("Enter passphrase for encryption (not saved):")
        label.setWordWrap(True)
        layout.addWidget(label)

        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.Password)
        self._input.setPlaceholderText("Enter your passphrase...")
        layout.addWidget(self._input)

        layout.addSpacing(16)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_theme(self) -> None:
        """Apply theme styling to dialog."""
        style = f"""
        QDialog {{
            background-color: {Theme.COLORS['bg_card']};
            color: {Theme.COLORS['text_primary']};
        }}
        QLabel {{
            color: {Theme.COLORS['text_primary']};
            font-size: 11pt;
        }}
        QLineEdit {{
            background-color: {Theme.COLORS['bg_input']};
            color: {Theme.COLORS['text_primary']};
            border: 1px solid {Theme.COLORS['border']};
            border-radius: 4px;
            padding: 8px;
            selection-background-color: {Theme.COLORS['accent_soft']};
        }}
        QLineEdit:focus {{
            border: 1px solid {Theme.COLORS['accent']};
        }}
        QLineEdit::placeholder {{
            color: {Theme.COLORS['text_muted']};
        }}
        QDialogButtonBox {{
            button-spacing: 8px;
        }}
        QPushButton {{
            background-color: {Theme.COLORS['accent_soft']};
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Theme.COLORS['accent']};
        }}
        """
        self.setStyleSheet(style)

    def passphrase(self) -> str:
        return self._input.text().strip()