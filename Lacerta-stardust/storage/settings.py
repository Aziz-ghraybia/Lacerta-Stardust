import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

DEFAULT_SETTINGS = {
    "mapping": {
        "NEXT": {"key": "Right", "display": "→ Arrow"},
        "PREV": {"key": "Left", "display": "← Arrow"},
    }
}


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except IOError as e:
        print(f"Failed to save settings: {e}")


def get_mapping() -> dict:
    return load_settings().get("mapping", DEFAULT_SETTINGS["mapping"])


def save_mapping(next_key: dict, prev_key: dict):
    settings = load_settings()
    settings["mapping"]["NEXT"] = next_key
    settings["mapping"]["PREV"] = prev_key
    save_settings(settings)
