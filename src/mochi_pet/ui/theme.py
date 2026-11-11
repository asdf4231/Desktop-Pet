"""The application-wide stylesheet.

Kept as one string so every Qt widget surface (chat, settings, training) shares the
same warm, rounded, soft-shadowed look as the hand-painted pet artwork.
"""

from mochi_pet.ui.palette import (
    CARD,
    CORAL,
    CORAL_DEEP,
    CREAM,
    CREAM_DEEP,
    GOLD,
    INK,
    INK_FAINT,
    INK_SOFT,
    LINE,
    LINE_SOFT,
    MINT,
    MINT_DEEP,
    PEACH,
    PEACH_DEEP,
    SHELL,
    SHELL_DEEP,
)

APP_STYLESHEET = f"""
QWidget {{
    color: {INK};
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", "Aptos", sans-serif;
    font-size: 10pt;
}}

QMainWindow, QDialog {{ background: {CREAM}; }}

QWidget#chatWindow, QWidget#settingsDialog, QWidget#trainingWindow {{
    background: {CREAM};
}}
QWidget#settingsContent {{ background: {CREAM}; }}
QWidget#chatBody {{ background: {CREAM}; }}

/* ---------------------------------------------------------------- typoscale */
QLabel#eyebrow {{
    color: {CORAL};
    font-size: 8pt;
    font-weight: 800;
    letter-spacing: 2px;
}}
QLabel#pageTitle {{
    color: {INK};
    font-size: 21pt;
    font-weight: 800;
}}
QLabel#sectionTitle {{
    color: {INK};
    font-size: 11pt;
    font-weight: 800;
}}
QLabel#fieldLabel {{ color: {INK}; font-size: 9pt; font-weight: 700; }}
QLabel#helperText {{ color: {INK_FAINT}; font-size: 8pt; }}
QLabel#muted {{ color: {INK_SOFT}; font-size: 9pt; }}
QLabel#faint {{ color: {INK_FAINT}; font-size: 8pt; }}

/* -------------------------------------------------------------- settings rail */
QFrame#settingsRail {{
    background: qlineargradient(x1:0, y1:0, x2:0.4, y2:1,
                stop:0 #FFF4E7, stop:0.55 #FCE6D3, stop:1 #F9D9C0);
    border-right: 1px solid {LINE};
}}
QLabel#railBrand {{
    color: #B4703F;
    font-size: 8pt;
    font-weight: 800;
    letter-spacing: 2px;
}}
QLabel#railTitle {{ color: {INK}; font-size: 19pt; font-weight: 800; }}
QLabel#railCopy {{ color: {INK_SOFT}; font-size: 8.5pt; }}
QLabel#railStep {{
    color: #8A5A2E;
    background: #FFEBD4;
    border: 1px solid #F8D9B4;
    border-radius: 11px;
    padding: 8px 11px;
    font-size: 8.5pt;
    font-weight: 700;
}}
QLabel#railNote {{
    color: {INK_SOFT};
    background: rgba(255, 255, 255, 160);
    border: 1px solid #F2DCC6;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 8pt;
}}

QLabel#connectionStatus {{
    color: {MINT_DEEP};
    background: #E4F3EC;
    border: 1px solid #CBE7DA;
    border-radius: 11px;
    padding: 4px 12px;
    font-size: 8pt;
    font-weight: 700;
}}
QLabel#connectionStatus[state="demo"] {{
    color: #9A6A16;
    background: #FDF1D8;
    border: 1px solid #F6E0B2;
}}

/* ------------------------------------------------------------------- cards */
QFrame#card {{
    background: {CARD};
    border: 1px solid {LINE};
    border-radius: 16px;
}}
QFrame#softCard {{
    background: {CREAM_DEEP};
    border: 1px solid {LINE_SOFT};
    border-radius: 14px;
}}
QFrame#divider {{ background: {LINE_SOFT}; border: 0; max-height: 1px; }}
QLabel#trainingMetric {{
    color: {INK};
    font-size: 27pt;
    font-weight: 800;
    letter-spacing: 1px;
}}

/* ------------------------------------------------------------------ inputs */
QLineEdit, QPlainTextEdit, QTextEdit {{
    color: {INK};
    background: {CARD};
    border: 1.4px solid {LINE};
    border-radius: 12px;
    padding: 9px 12px;
    selection-background-color: {PEACH};
    selection-color: {INK};
}}
QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover {{ border-color: {SHELL_DEEP}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1.6px solid {MINT};
    background: #FFFFFE;
}}
QLineEdit:disabled, QPlainTextEdit:disabled {{ background: {SHELL}; color: {INK_FAINT}; }}

/* ----------------------------------------------------------------- buttons */
QPushButton {{
    color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {PEACH_DEEP}, stop:1 {CORAL});
    border: 0;
    border-radius: 12px;
    padding: 9px 18px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F79C83, stop:1 {PEACH_DEEP});
}}
QPushButton:pressed {{ background: {CORAL_DEEP}; }}
QPushButton:disabled {{ background: {SHELL_DEEP}; color: #FFFFFF; }}

QPushButton#schulteCell {{
    color: {INK};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #FFF7EC);
    border: 1.4px solid {LINE};
    border-radius: 16px;
    padding: 4px;
    font-size: 23pt;
    font-weight: 800;
}}
QPushButton#schulteCell:hover {{
    background: #FFF1E3;
    border-color: {PEACH_DEEP};
}}
QPushButton#schulteCell[state="correct"] {{
    color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A6E1CE, stop:1 {MINT_DEEP});
    border-color: {MINT_DEEP};
}}
QPushButton#schulteCell[state="wrong"] {{
    color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F6A08A, stop:1 {CORAL_DEEP});
    border-color: {CORAL_DEEP};
}}
QPushButton#schulteCell:disabled {{
    color: {INK_FAINT};
    background: {CREAM_DEEP};
    border-color: {LINE_SOFT};
}}

/* ------------------------------------------------------------------- menus */
QMenu {{
    background: #FFFDFA;
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 7px;
}}
QMenu::item {{
    padding: 7px 20px 7px 14px;
    border-radius: 8px;
    color: {INK};
}}
QMenu::item:selected {{ background: {CREAM_DEEP}; }}
QMenu::item:disabled {{ color: {INK_FAINT}; }}
QMenu::separator {{ height: 1px; background: {LINE_SOFT}; margin: 6px 10px; }}
QMenu::icon {{ padding-left: 6px; }}

QToolTip {{
    color: {INK};
    background: #FFFDFA;
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 6px 9px;
}}

/* -------------------------------------------------------------- scrollbars */
QScrollArea {{ border: 0; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {SHELL_DEEP};
    border-radius: 5px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{ background: #DCC3A6; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {SHELL_DEEP};
    border-radius: 5px;
    min-width: 40px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ----------------------------------------------------------- chat specifics */
QFrame#chatHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #FFF3E4, stop:0.55 #FDE7D6, stop:1 #FBD9C6);
    border: 0;
    border-bottom: 1px solid {LINE};
}}
QLabel#chatTitle {{ color: {INK}; font-size: 16pt; font-weight: 800; }}
QLabel#chatSubtitle {{ color: {INK_SOFT}; font-size: 8pt; }}
QLabel#chatStatusDot {{ font-size: 9pt; }}

QFrame#composer {{
    background: {CARD};
    border: 1.6px solid {LINE};
    border-radius: 18px;
}}
QFrame#composer[focused="true"] {{ border: 1.6px solid {MINT}; }}

QPushButton#suggestionChip {{
    color: {INK_SOFT};
    background: {CARD};
    border: 1.3px solid {LINE};
    border-radius: 13px;
    padding: 6px 13px;
    font-size: 8.5pt;
    font-weight: 600;
}}
QPushButton#suggestionChip:hover {{
    color: {CORAL_DEEP};
    border-color: {PEACH};
    background: #FFF6EF;
}}

/* --------------------------------------------------------- settings pages */
QPushButton#railNav {{
    color: {INK_SOFT};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 11px;
    padding: 9px 14px;
    font-size: 9.5pt;
    font-weight: 700;
    text-align: left;
}}
QPushButton#railNav:hover {{ background: rgba(255, 255, 255, 150); color: {INK}; }}
QPushButton#railNav:checked {{
    background: #FFFFFF;
    color: {INK};
    border: 1px solid #F0DCC6;
}}

QToolButton#themeSwatch {{
    color: {INK_SOFT};
    background: {CARD};
    border: 1.6px solid {LINE};
    border-radius: 14px;
    padding: 8px 6px 6px 6px;
    font-size: 8pt;
    font-weight: 700;
}}
QToolButton#themeSwatch:hover {{ border-color: {PEACH}; background: #FFF8F2; }}
QToolButton#themeSwatch:checked {{
    color: {INK};
    border: 2px solid {CORAL};
    background: #FFF4EC;
}}

QGroupBox {{
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 14px;
    background: {CARD};
    margin-top: 14px;
    padding: 14px 14px 10px 14px;
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: {INK_SOFT};
    font-size: 8.5pt;
}}

QCheckBox {{ color: {INK}; spacing: 9px; padding: 3px 0; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border-radius: 6px;
    border: 1.4px solid {LINE};
    background: {CARD};
}}
QCheckBox::indicator:hover {{ border-color: {PEACH}; }}
QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F79C83, stop:1 {CORAL});
    border-color: {CORAL_DEEP};
}}

QSlider::groove:horizontal {{
    height: 6px;
    border-radius: 3px;
    background: {SHELL_DEEP};
}}
QSlider::sub-page:horizontal {{
    height: 6px;
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {GOLD}, stop:1 {PEACH_DEEP});
}}
QSlider::handle:horizontal {{
    width: 17px;
    margin: -6px 0;
    border-radius: 8px;
    background: #FFFFFF;
    border: 1.6px solid {PEACH_DEEP};
}}
QSlider::handle:horizontal:hover {{ border-color: {CORAL}; }}

QComboBox {{
    color: {INK};
    background: {CARD};
    border: 1.4px solid {LINE};
    border-radius: 11px;
    padding: 7px 11px;
    min-height: 20px;
}}
QComboBox:hover {{ border-color: {SHELL_DEEP}; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 4px;
    selection-background-color: {CREAM_DEEP};
    selection-color: {INK};
    outline: 0;
}}

/* -------------------------------------------------------------- misc bits */
QProgressBar {{
    background: {SHELL};
    border: 0;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {GOLD}, stop:1 {PEACH_DEEP});
    border-radius: 5px;
}}

QSplitter::handle {{ background: {LINE_SOFT}; }}
"""

__all__ = ["APP_STYLESHEET"]
