import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from ui.tray import TrayIcon


def main():
    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Lacerta Stardust")
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is hidden

    # Build main window
    window = MainWindow()

    # Build tray icon and wire it to the window's connection signals
    tray = TrayIcon(window)
    window.sig_connected.connect(lambda: tray.set_connected(True))
    window.sig_disconnected.connect(lambda: tray.set_connected(False))
    tray.show()

    # Show the window on first launch
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
