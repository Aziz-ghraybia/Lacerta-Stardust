# Lacerta Stardust

Turn your Android phone's volume buttons into a wireless presentation clicker — connected to your Windows PC via Bluetooth.

No extra hardware. No looking at your screen. Just press volume up or down and your slides advance.

---

## Download

| Platform | Download | Requirements |
|----------|----------|--------------|
| Android | [Lacerta-Stardust.apk](https://github.com/Aziz-ghraybia/Lacerta-Stardust/releases/download/v1.1.0/Lacerta-Stardust.apk) | Android 8.0+ |
| Windows | [LacertaStardust.exe](https://github.com/Aziz-ghraybia/Lacerta-Stardust/releases/download/v1.1.0/LacertaStardust.exe) | Windows 10+, Bluetooth |

---

## How It Works

```
Windows clicks Connect
        ↓
Phone receives a connection request → Accept
        ↓
Phone goes in pocket, screen on
        ↓
Volume UP   →  Next slide
Volume DOWN →  Previous slide
        ↓
Pull down notification → Disconnect
```

The Windows app simulates keystrokes — so it works with any presentation software: PowerPoint, Google Slides, Canva, LibreOffice, and more.

---

## Getting Started

### Windows App

1. Download and run `LacertaStardust.exe`
2. The app appears in your system tray
3. Click the tray icon to open the window
4. Click **Scan** to find your phone
5. Select it and click **Connect**

### Android App

1. Download and install `LacertaStardust.apk`
   - Enable **Install from unknown sources** if prompted
2. Open the app
3. Grant **Bluetooth** and **Notification** permissions
4. Enable the **Accessibility Service** when prompted
   - Settings → Accessibility → Installed Apps → Lacerta Stardust → ON
5. Samsung users: go to **Settings → Apps → Lacerta Stardust → Battery → Unrestricted**

### Connecting

1. Make sure Bluetooth is on on both devices
2. Click **Scan** on the Windows app — your phone will appear
3. Select your phone and click **Connect**
4. A connection request appears on your phone → tap **Accept**
5. A persistent notification pins to your phone — you are ready to present

---

## Input Mapping

By default:
- Volume UP → Right Arrow
- Volume DOWN → Left Arrow

You can remap to any key in the Windows app under **Input Mapping** — click the field and press the key you want. Works for any key including Space, Escape, F5, Page Up/Down, etc.

---

## Disconnecting

From the **phone**: pull down the notification shade → tap **Disconnect**

From the **PC**: click **Disconnect** in the app window

From the **notification**: tap **Stop** to fully close the Android app

---

## Built With

| Side | Stack |
|------|-------|
| Windows | Python, PyQt6, Bleak (BLE) |
| Android | Kotlin, Android BLE API, Accessibility Service |
| Protocol | Bluetooth Low Energy (BLE) — custom GATT service |

---

## Building from Source

### Windows
```bash
pip install PyQt6 bleak pynput pyinstaller
cd lacerta-stardust
build.bat
# Output: dist/LacertaStardust.exe
```

### Android
Open `lacerta-stardust-m` in Android Studio, sync Gradle, and run on your device. See [BUILD.md](lacerta-stardust-m/BUILD.md) for building a signed release APK.

---

## Repository Structure

```
├── lacerta-stardust/          # Windows app (Python + PyQt6)
│   ├── core/                  # BLE client, input mapper
│   ├── ui/                    # Main window, tray, mapping UI
│   ├── storage/               # Settings persistence
│   ├── assets/                # App icons
│   ├── main.py                # Entry point
│   └── build.bat              # Build script
│
└── lacerta-stardust-m/        # Android app (Kotlin)
    └── app/src/main/
        ├── java/com/lacertastardust/
        │   ├── ble/           # BLE peripheral / GATT server
        │   ├── services/      # Foreground service, accessibility
        │   └── ui/            # Activities, layouts
        └── res/               # Layouts, drawables, strings
```

---

## Notes

- The Android app needs the **Accessibility Service** enabled to intercept volume buttons. This is the only way to suppress the default volume change behavior.
- On Samsung devices, set the app battery usage to **Unrestricted** to prevent the Accessibility Service from being killed in the background.
- The app works best with the phone screen on during the presentation. Screen-off use depends on your device's battery optimization settings.

---

## License

MIT License — free to use, modify, and distribute.
