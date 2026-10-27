from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent, QColor
from storage.settings import get_mapping, save_mapping

BG_CARD    = "#111428"
BG_INPUT   = "#0d1030"
BORDER     = "#1a2040"
GOLD       = "#f0b429"
STAR_WHITE = "#e8f0ff"
BLUE_SOFT  = "#6a8fff"
TEXT_DIM   = "#3a4a6a"

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

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Click to assign")
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(110)
        self.setFixedHeight(32)
        self._waiting = False
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_INPUT};
                color: {STAR_WHITE};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 0 10px;
                font-size: 12px;
                text-align: center;
            }}
            QLineEdit:focus {{
                border-color: {GOLD};
                color: {GOLD};
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        self._waiting = True
        self.setPlaceholderText("Press a key...")
        self.clear()
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

        self.setText(display)
        self._waiting = False
        self.setPlaceholderText("Click to assign")
        self.key_captured.emit(display, pynput)

    def set_key(self, display: str, pynput: str):
        self._display = display
        self._pynput  = pynput
        self.setText(display)

    @property
    def pynput_name(self) -> str:
        return self._pynput if hasattr(self, '_pynput') else ""

    @property
    def display_name(self) -> str:
        return self._display if hasattr(self, '_display') else ""


class MappingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._next_key = {"key": "Right", "display": "→ Arrow"}
        self._prev_key = {"key": "Left",  "display": "← Arrow"}
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Volume UP row
        up_card = self._make_row("Volume UP")
        self._next_field = up_card[1]
        self._next_field.key_captured.connect(
            lambda d, p: self._on_capture("NEXT", d, p)
        )
        layout.addWidget(up_card[0])

        # Volume DOWN row
        down_card = self._make_row("Volume DOWN")
        self._prev_field = down_card[1]
        self._prev_field.key_captured.connect(
            lambda d, p: self._on_capture("PREV", d, p)
        )
        layout.addWidget(down_card[0])

        # Save button row
        save_row = QHBoxLayout()
        save_row.addStretch()

        self._save_btn = QPushButton("Save Mapping")
        self._save_btn.setFixedHeight(30)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {GOLD};
                border: 1px solid {GOLD};
                border-radius: 4px;
                padding: 0 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #1a1200; }}
        """)
        self._save_btn.clicked.connect(self._save)
        save_row.addWidget(self._save_btn)
        layout.addLayout(save_row)

    def _make_row(self, label_text: str) -> tuple:
        """Returns (container widget, key capture field)."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 5px;
            }}
        """)
        row = QHBoxLayout(container)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(0)

        label = QLabel(label_text)
        label.setStyleSheet(
            f"color: {STAR_WHITE}; font-size: 13px; "
            f"background: transparent; border: none;"
        )
        row.addWidget(label)
        row.addStretch()

        field = KeyCaptureField()
        row.addWidget(field)

        return container, field

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
        self._save_btn.setText("✓  Saved")
        QTimer.singleShot(2000, lambda: self._save_btn.setText("Save Mapping"))
