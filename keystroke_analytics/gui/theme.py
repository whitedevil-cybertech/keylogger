"""Shared UI theme for a compact, professional dark desktop interface."""

from __future__ import annotations

from PySide6.QtGui import QFont


class Theme:
    """Centralized colors, spacing and QSS for GUI widgets."""

    COLORS = {
        "bg_app": "#0b1118",
        "bg_panel": "#111a24",
        "bg_card": "#162230",
        "bg_card_alt": "#1a2736",
        "bg_input": "#0f1925",
        "bg_hover": "#1f3044",
        "bg_pressed": "#243a53",
        "accent": "#19c7c0",
        "accent_soft": "#1c8f97",
        "danger": "#e35d6a",
        "warning": "#f2b94b",
        "success": "#34d399",
        "text_primary": "#e6edf4",
        "text_secondary": "#9fb1c2",
        "text_muted": "#70859a",
        "border": "#25384d",
        "border_soft": "#1d2c3c",
    }

    SPACING = {
        "xs": 4,
        "sm": 8,
        "md": 12,
        "lg": 16,
        "xl": 20,
    }

    @classmethod
    def stylesheet(cls) -> str:
        c = cls.COLORS
        return f"""
        QWidget {{
            color: {c['text_primary']};
            background: {c['bg_app']};
            font-size: 12px;
            font-family: 'Segoe UI', 'Inter', sans-serif;
        }}

        QMainWindow {{
            background: {c['bg_app']};
        }}

        QLabel[role="title"] {{
            font-size: 16px;
            font-weight: 600;
            color: {c['text_primary']};
        }}

        QLabel[role="subtitle"] {{
            font-size: 11px;
            font-weight: 500;
            color: {c['text_secondary']};
        }}

        QLabel[role="muted"] {{
            color: {c['text_muted']};
            font-size: 11px;
        }}

        QFrame[role="panel"] {{
            background: {c['bg_panel']};
            border: 1px solid {c['border_soft']};
            border-radius: 10px;
        }}

        QFrame[role="card"] {{
            background: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 10px;
        }}

        QFrame[role="card-alt"] {{
            background: {c['bg_card_alt']};
            border: 1px solid {c['border']};
            border-radius: 10px;
        }}

        QPushButton {{
            background: {c['accent_soft']};
            color: white;
            border: 1px solid transparent;
            border-radius: 8px;
            min-height: 28px;
            padding: 4px 12px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            background: {c['accent']};
        }}

        QPushButton:pressed {{
            background: {c['bg_pressed']};
        }}

        QPushButton:disabled {{
            background: {c['bg_input']};
            color: {c['text_muted']};
            border-color: {c['border_soft']};
        }}

        QPushButton[role="secondary"] {{
            background: {c['bg_input']};
            border: 1px solid {c['border']};
            color: {c['text_primary']};
        }}

        QPushButton[role="secondary"]:hover {{
            background: {c['bg_hover']};
            border-color: {c['accent_soft']};
        }}

        QPushButton[role="danger"] {{
            background: #6d2f3c;
            border: 1px solid #8e4350;
        }}

        QPushButton[role="danger"]:hover {{
            background: {c['danger']};
            border-color: {c['danger']};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            background: {c['bg_input']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            color: {c['text_primary']};
            selection-background-color: {c['accent_soft']};
        }}

        QLineEdit {{
            padding: 6px 8px;
            min-height: 24px;
        }}

        QTextEdit, QPlainTextEdit {{
            padding: 8px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c['accent']};
        }}

        QProgressBar {{
            background: {c['bg_input']};
            border: 1px solid {c['border']};
            border-radius: 5px;
            text-align: center;
            min-height: 10px;
            color: {c['text_secondary']};
        }}

        QProgressBar::chunk {{
            background: {c['accent']};
            border-radius: 4px;
        }}

        QCheckBox {{
            spacing: 6px;
            color: {c['text_primary']};
        }}

        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
            border: 1px solid {c['border']};
            background: {c['bg_input']};
        }}

        QCheckBox::indicator:checked {{
            background: {c['accent']};
            border-color: {c['accent']};
        }}

        QTabWidget::pane {{
            border: 1px solid {c['border']};
            border-radius: 10px;
            top: -1px;
            background: {c['bg_panel']};
        }}

        QTabBar::tab {{
            background: transparent;
            color: {c['text_secondary']};
            padding: 8px 14px;
            margin: 2px;
            border-radius: 8px;
            min-height: 20px;
        }}

        QTabBar::tab:selected {{
            color: {c['text_primary']};
            background: {c['bg_hover']};
            border: 1px solid {c['border']};
        }}

        QTabBar::tab:hover:!selected {{
            background: {c['bg_input']};
            color: {c['text_primary']};
        }}

        QScrollBar:vertical {{
            width: 10px;
            background: {c['bg_panel']};
            margin: 2px;
        }}

        QScrollBar::handle:vertical {{
            border-radius: 5px;
            background: {c['border']};
            min-height: 24px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {c['accent_soft']};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            border: none;
            background: none;
        }}

        QToolTip {{
            background: {c['bg_card_alt']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            padding: 4px 6px;
        }}
        """

    @classmethod
    def font(cls, role: str) -> QFont:
        font = QFont("Segoe UI")
        if role == "mono":
            return QFont("JetBrains Mono")
        return font
