import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import QSize, Qt


def _make_status_icon(base_icon: QIcon, connected: bool) -> QIcon:
    """Overlay a small green or grey dot on the base icon to show status."""
    size = 32
    pixmap = base_icon.pixmap(QSize(size, size))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#2a9d2a") if connected else QColor("#888888")
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    # Small dot in bottom-right corner
    painter.drawEllipse(22, 22, 9, 9)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._window = main_window

        # Load app icon from assets folder
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png"
        )
        if os.path.exists(icon_path):
            self._base_icon = QIcon(icon_path)
        else:
            # Fallback if icon file not found
            pixmap = QPixmap(QSize(32, 32))
            pixmap.fill(QColor("#0a0d1f"))
            self._base_icon = QIcon(pixmap)

        self._icon_disconnected = _make_status_icon(self._base_icon, False)
        self._icon_connected    = _make_status_icon(self._base_icon, True)

        self.setIcon(self._icon_disconnected)
        self.setToolTip("Lacerta Stardust — Disconnected")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()

        self._toggle_action = menu.addAction("Open")
        self._toggle_action.triggered.connect(self._toggle_window)

        menu.addSeparator()

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()

    def _toggle_window(self):
        if self._window.isVisible():
            self._window.hide()
            self._toggle_action.setText("Open")
        else:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()
            self._toggle_action.setText("Hide")

    def set_connected(self, connected: bool):
        if connected:
            self.setIcon(self._icon_connected)
            self.setToolTip("Lacerta Stardust — Connected")
        else:
            self.setIcon(self._icon_disconnected)
            self.setToolTip("Lacerta Stardust — Disconnected")
