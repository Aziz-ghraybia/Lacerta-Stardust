from pynput.keyboard import Controller, Key
from storage.settings import get_mapping

keyboard = Controller()

# Map string key names to pynput Key objects for special keys
SPECIAL_KEYS = {
    "Right": Key.right,
    "Left": Key.left,
    "Up": Key.up,
    "Down": Key.down,
    "Space": Key.space,
    "Enter": Key.enter,
    "Escape": Key.esc,
    "Backspace": Key.backspace,
    "Tab": Key.tab,
    "F5": Key.f5,
    "F1": Key.f1,
    "F2": Key.f2,
    "Page_Up": Key.page_up,
    "Page_Down": Key.page_down,
}


def _resolve_key(key_str: str):
    """Return a pynput Key or a character depending on the key string."""
    if key_str in SPECIAL_KEYS:
        return SPECIAL_KEYS[key_str]
    # Single character key
    return key_str.lower()[0] if key_str else Key.right


def handle_signal(signal: str):
    """
    Receive a BLE signal ('NEXT' or 'PREV') and simulate the mapped keystroke.
    """
    print(f"[MAPPER] handle_signal called with: '{signal}'")

    mapping = get_mapping()
    print(f"[MAPPER] Current mapping: {mapping}")

    if signal == "NEXT":
        raw_key = mapping["NEXT"]["key"]
        key = _resolve_key(raw_key)
        print(f"[MAPPER] NEXT → raw='{raw_key}' resolved='{key}'")
    elif signal == "PREV":
        raw_key = mapping["PREV"]["key"]
        key = _resolve_key(raw_key)
        print(f"[MAPPER] PREV → raw='{raw_key}' resolved='{key}'")
    else:
        print(f"[MAPPER] Unknown signal: '{signal}'")
        return

    try:
        keyboard.press(key)
        keyboard.release(key)
        print(f"[MAPPER] ✓ Keystroke simulated: '{key}'")
    except Exception as e:
        print(f"[MAPPER] ✗ Keystroke failed: {e}")
