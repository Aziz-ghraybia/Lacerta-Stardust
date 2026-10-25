from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from storage.settings import get_mapping, save_mapping

BG_CARD  = "#111428"
BG_INPUT = "#0d1030"
BORDER   = "#1a2040"
GOLD     = "#f0b429"
STAR_WHITE = "#e8f0ff"
BLUE_SOFT  = "#6a8fff"
TEXT_DIM   = "#3a4a6a"
GREEN      = "#4caf82"

QT_KEY_MAP = {
    Qt.Key.Key_Right:     ("→ Arrow",   "Right"),
    Qt.Key.Key_Left:      ("← Arrow",   "Left"),
    Qt.Key.Key_Up:        ("↑ Arrow",   "Up"),
    Qt.Key.Key_Down:      ("↓ Arrow",   "Down"),
    Qt.Key.Key_Space:     ("Space",     "Space"),
    Qt.Key.Key_Return:    ("Enter",     "Enter"),
    Qt.Key.Key_Escape:    ("Escape",    "Escape"),
    Qt.Key.Key_Backspace: ("Backspace", "Backspace"),
    Qt.Key.Key_Tab:       ("Tab",       "Tab"),
    Qt.Key.Key_F5:        ("F5",        "F5"),
    Qt.Key.Key_F1:        ("F1",        "F1"),
    Qt.Key.Key_F2:        ("F2",        "F2"),
    Qt.Key.Key_PageUp:    ("Page Up",   "Page_Up"),
    Qt.Key.Key_PageDown:  ("Page Down", "Page_Down"),
}


class KeyCaptureField(QLineEdit):
    key_captured = pyqtSignal(str, str)

    def __init__(self, placeholder="Click then press a key"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._waiting = False
        self._display = ""
        self._pynput  = ""
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_INPUT};
                color: {STAR_WHITE};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {GOLD};
                color: {GOLD};
            }}
        """)

    def mousePressEvent(self, event):
        self._waiting = True
        self.setPlaceholderText("Press any key...")
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._waiting:
            return
        qt_key = Qt.Key(event.key())
        if qt_key in QT_KEY_MAP:
            display, pynput = QT_KEY_MAP[qt_key]
        else:
            text = event.text().upper()
            if not text:
                return
            display = text
            pynput  = text

        self._display = display
        self._pynput  = pynput
        self.setText(display)
        self._waiting = False
        self.setPlaceholderText("Click then press a key")
        self.key_captured.emit(display, pynput)

    def set_key(self, display: str, pynput: str):
        self._display = display
        self._pynput  = pynput
        self.setText(display)

    @property
    def pynput_name(self) -> str:
        return self._pynput

    @property
    def display_name(self) -> str:
        return self._display


class MappingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._next_key = {"key": "Right", "display": "→ Arrow"}
        self._prev_key = {"key": "Left",  "display": "← Arrow"}
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        def make_row(icon: str, label: str) -> tuple:
            row = QHBoxLayout()
            row.setSpacing(10)

            lbl = QLabel(f"{icon}  {label}")
            lbl.setStyleSheet(
                f"color: {BLUE_SOFT}; font-size: 12px; min-width: 120px;"
            )
            lbl.setFixedWidth(130)
            row.addWidget(lbl)

            field = KeyCaptureField()
            row.addWidget(field)

            return row, field

        up_row,   self._next_field = make_row("▲", "Volume UP")
        down_row, self._prev_field = make_row("▼", "Volume DOWN")

        self._next_field.key_captured.connect(
            lambda d, p: self._on_capture("NEXT", d, p)
        )
        self._prev_field.key_captured.connect(
            lambda d, p: self._on_capture("PREV", d, p)
        )

        layout.addLayout(up_row)
        layout.addLayout(down_row)

        self._save_btn = QPushButton("Save Mapping")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {GOLD};
                border: 1px solid {GOLD};
                border-radius: 6px;
                padding: 7px 20px;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: #1a1200; }}
        """)
        self._save_btn.clicked.connect(self._save)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_row.addWidget(self._save_btn)
        layout.addLayout(save_row)

    def _load(self):
        mapping = get_mapping()
        self._next_key = mapping["NEXT"]
        self._prev_key = mapping["PREV"]
        self._next_field.set_key(mapping["NEXT"]["display"], mapping["NEXT"]["key"])
        self._prev_field.set_key(mapping["PREV"]["display"], mapping["PREV"]["key"])

    def _on_capture(self, signal: str, display: str, pynput: str):
        if signal == "NEXT":
            self._next_key = {"key": pynput, "display": display}
        else:
            self._prev_key = {"key": pynput, "display": display}

    def _save(self):
        if not self._next_key.get("key") or not self._prev_key.get("key"):
            QMessageBox.warning(self, "Mapping", "Please assign both keys before saving.")
            return
        save_mapping(self._next_key, self._prev_key)
        self._save_btn.setText("✓ Saved")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._save_btn.setText("Save Mapping"))
