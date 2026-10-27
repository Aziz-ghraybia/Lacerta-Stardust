import asyncio
import threading
from bleak import BleakScanner
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QCloseEvent, QColor
from ui.mapping_window import MappingWidget
from core.ble_client import BleClient
from core.input_mapper import handle_signal


SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"

BG          = "#0a0d1f"
BG_CARD     = "#111428"
BG_INPUT    = "#0d1030"
BORDER      = "#1a2040"
GOLD        = "#f0b429"
GOLD_DIM    = "#c48a00"
STAR_WHITE  = "#e8f0ff"
BLUE_SOFT   = "#6a8fff"
RED         = "#e05252"
GREEN       = "#4caf82"
TEXT_DIM    = "#3a4a6a"

GLOBAL_STYLE = f"""
    QMainWindow, QWidget {{
        background: {BG};
        color: {STAR_WHITE};
        font-family: 'Segoe UI', sans-serif;
    }}
    QStatusBar {{
        background: {BG};
        color: {TEXT_DIM};
        font-size: 11px;
        border-top: 1px solid {BORDER};
    }}
    QScrollBar:vertical {{
        background: {BG_CARD};
        width: 5px;
        border-radius: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 2px;
    }}
"""


class DeviceScanner(QObject):
    devices_found = pyqtSignal(list)
    scan_error    = pyqtSignal(str)
    finished      = pyqtSignal()

    def run(self):
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self._scan())
        except Exception as e:
            result = []
            self.scan_error.emit(str(e))
        finally:
            loop.close()
        self.devices_found.emit(result)
        self.finished.emit()

    async def _scan(self) -> list[tuple[str, str]]:
        seen: dict[str, tuple[str, str]] = {}

        def on_advertisement(device, advertisement_data):
            uuids = [str(u).lower() for u in (advertisement_data.service_uuids or [])]
            if SERVICE_UUID.lower() in uuids:
                name = (
                    advertisement_data.local_name
                    or device.name
                    or "Lacerta Stardust Device"
                )
                seen[device.address] = (name, device.address)

        async with BleakScanner(detection_callback=on_advertisement):
            await asyncio.sleep(5.0)

        return list(seen.values())


class MainWindow(QMainWindow):
    sig_connected    = pyqtSignal()
    sig_disconnected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("✦ Lacerta Stardust")
        self.setFixedWidth(380)
        self.setMinimumHeight(560)
        self.setStyleSheet(GLOBAL_STYLE)

        self._ble: BleClient | None = None
        self._scan_thread: QThread | None = None
        self._connected_device_name = ""

        self.sig_connected.connect(self._on_connected)
        self.sig_disconnected.connect(self._on_disconnected)

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI                                                                 #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(16, 16, 16, 16)

        # App name
        title = QLabel("LACERTA STARDUST")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {BLUE_SOFT}; font-size: 11px; font-weight: bold; "
            f"letter-spacing: 3px; padding-bottom: 12px;"
        )
        layout.addWidget(title)

        # Status banner
        self._status_banner = QLabel("AWAITING ALIGNMENT")
        self._status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_banner.setStyleSheet(self._disconnected_banner_style())
        layout.addWidget(self._status_banner)
        layout.addSpacing(16)

        # Section label
        layout.addWidget(self._section_label("CONSTELLATIONS NEARBY"))
        layout.addSpacing(6)

        # Device list
        self._device_list = QListWidget()
        self._device_list.setFixedHeight(140)
        self._device_list.setStyleSheet(f"""
            QListWidget {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {STAR_WHITE};
                font-size: 13px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background: #1a2550;
                color: {GOLD};
            }}
            QListWidget::item:hover:!selected {{
                background: #131929;
            }}
        """)
        self._device_list.itemClicked.connect(self._on_device_selected)
        self._show_empty_state()
        layout.addWidget(self._device_list)
        layout.addSpacing(10)

        # Scan + Connect buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setFixedHeight(36)
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG_CARD};
                color: {BLUE_SOFT};
                border: 1px solid {BLUE_SOFT};
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #131929; color: {STAR_WHITE}; }}
            QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}
        """)
        self._scan_btn.clicked.connect(self._scan_devices)
        btn_row.addWidget(self._scan_btn)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedHeight(36)
        self._connect_btn.setEnabled(False)
        self._connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._connect_btn.setStyleSheet(self._connect_style())
        self._connect_btn.clicked.connect(self._connect)
        btn_row.addWidget(self._connect_btn)

        layout.addLayout(btn_row)

        # Status text
        self._scan_status = QLabel("")
        self._scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scan_status.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 11px; padding-top: 5px;"
        )
        layout.addWidget(self._scan_status)
        layout.addSpacing(16)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {BORDER}; background: {BORDER}; max-height: 1px;")
        layout.addWidget(line)
        layout.addSpacing(14)

        # Input mapping section
        layout.addWidget(self._section_label("INPUT MAPPING"))
        layout.addSpacing(8)

        self._mapping_widget = MappingWidget()
        layout.addWidget(self._mapping_widget)

        layout.addStretch()
        self.statusBar().showMessage("Ready")

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {GOLD}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        return lbl

    # ------------------------------------------------------------------ #
    #  Banner and button styles                                           #
    # ------------------------------------------------------------------ #

    def _disconnected_banner_style(self) -> str:
        return (
            f"color: {TEXT_DIM}; font-size: 13px; font-weight: bold; "
            f"letter-spacing: 3px; padding: 12px; border-radius: 6px; "
            f"background: {BG_CARD}; border: 1px solid {BORDER};"
        )

    def _connected_banner_style(self) -> str:
        return (
            f"color: {GOLD}; font-size: 13px; font-weight: bold; "
            f"letter-spacing: 3px; padding: 12px; border-radius: 6px; "
            f"background: #1a1200; border: 1px solid {GOLD_DIM};"
        )

    def _connect_style(self) -> str:
        return f"""
            QPushButton:enabled {{
                background: {GOLD};
                color: #0a0d1f;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:enabled:hover {{ background: #ffc93d; }}
            QPushButton:disabled {{
                background: {BG_CARD};
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 5px;
                font-size: 13px;
            }}
        """

    def _disconnect_style(self) -> str:
        return f"""
            QPushButton {{
                background: {RED};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #c04040; }}
        """

    # ------------------------------------------------------------------ #
    #  Device list helpers                                                #
    # ------------------------------------------------------------------ #

    def _show_empty_state(self):
        self._device_list.clear()
        empty = QListWidgetItem("No devices discovered. Click Scan to search.")
        empty.setFlags(Qt.ItemFlag.NoItemFlags)
        font = empty.font()
        font.setItalic(True)
        empty.setFont(font)
        empty.setForeground(QColor(TEXT_DIM))
        self._device_list.addItem(empty)

    # ------------------------------------------------------------------ #
    #  Scanning                                                           #
    # ------------------------------------------------------------------ #

    def _scan_devices(self):
        self._device_list.clear()
        self._connect_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._scan_status.setStyleSheet(
            f"color: {BLUE_SOFT}; font-size: 11px; padding-top: 5px;"
        )
        self._scan_status.setText("Scanning for Lacerta Stardust devices...")

        self._scan_thread = QThread()
        self._scanner     = DeviceScanner()
        self._scanner.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scanner.run)
        self._scanner.devices_found.connect(self._on_devices_found)
        self._scanner.scan_error.connect(self._on_scan_error)
        self._scanner.finished.connect(self._scan_thread.quit)
        self._scan_thread.start()

    def _on_devices_found(self, devices: list):
        self._scan_btn.setEnabled(True)
        self._device_list.clear()

        if not devices:
            self._show_empty_state()
            self._scan_status.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 11px; padding-top: 5px;"
            )
            self._scan_status.setText("Bluetooth radio active • 0 devices found")
            return

        self._scan_status.setStyleSheet(
            f"color: {GREEN}; font-size: 11px; padding-top: 5px;"
        )
        self._scan_status.setText(f"{len(devices)} device(s) found")

        for name, address in devices:
            item = QListWidgetItem(f"  •  {name}")
            item.setData(Qt.ItemDataRole.UserRole, address)
            self._device_list.addItem(item)

    def _on_scan_error(self, error: str):
        self._scan_btn.setEnabled(True)
        self._show_empty_state()
        self._scan_status.setStyleSheet(
            f"color: {RED}; font-size: 11px; padding-top: 5px;"
        )
        self._scan_status.setText("Bluetooth is off or unavailable")

    def _on_device_selected(self, item: QListWidgetItem):
        if item.flags() & Qt.ItemFlag.ItemIsEnabled:
            self._connect_btn.setEnabled(True)

    # ------------------------------------------------------------------ #
    #  BLE connect / disconnect                                           #
    # ------------------------------------------------------------------ #

    def _connect(self):
        selected = self._device_list.currentItem()
        if not selected or not (selected.flags() & Qt.ItemFlag.ItemIsEnabled):
            return

        address = selected.data(Qt.ItemDataRole.UserRole)
        self._connected_device_name = selected.text().replace("  •  ", "").strip()
        self._connect_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self.statusBar().showMessage("Connecting...")

        if self._ble is None:
            self._ble = BleClient(
                on_signal=handle_signal,
                on_connected=self.sig_connected.emit,
                on_disconnected=self.sig_disconnected.emit,
            )
        self._ble.connect(address)

    def _on_connected(self):
        self._status_banner.setText("STARS ALIGNED")
        self._status_banner.setStyleSheet(self._connected_banner_style())
        self._connect_btn.setText("Disconnect")
        self._connect_btn.setEnabled(True)
        self._connect_btn.setStyleSheet(self._disconnect_style())
        try:
            self._connect_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._connect_btn.clicked.connect(self._disconnect)
        self._scan_status.setStyleSheet(
            f"color: {GREEN}; font-size: 11px; padding-top: 5px;"
        )
        self._scan_status.setText(
            f"Connected to {self._connected_device_name} • Link active"
        )
        self.statusBar().showMessage("Connected — volume buttons are active")

    def _disconnect(self):
        if self._ble:
            self._connect_btn.setEnabled(False)
            self._ble.disconnect()

    def _on_disconnected(self):
        self._status_banner.setText("AWAITING ALIGNMENT")
        self._status_banner.setStyleSheet(self._disconnected_banner_style())
        self._connect_btn.setText("Connect")
        self._connect_btn.setEnabled(False)
        self._connect_btn.setStyleSheet(self._connect_style())
        try:
            self._connect_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._connect_btn.clicked.connect(self._connect)
        self._scan_btn.setEnabled(True)
        self._scan_status.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 11px; padding-top: 5px;"
        )
        self._scan_status.setText("")
        self.statusBar().showMessage("Disconnected")

    # ------------------------------------------------------------------ #
    #  Window close → hide to tray                                        #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()