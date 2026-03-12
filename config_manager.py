import json
import os

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
CONFIG_PATH  = os.path.join(BASE_DIR, "user_config.json")

DEFAULT_CONFIG = {
    "permissions": {
        "camera":    None,
        "analytics": None
    },
    "last_profile": "default",
    "always_ask_profile": True,
    "recorder": {
        "enabled":             True,
        "buffer_secs":         10,
        "fps":                 8,
        "screenshot_interval": 30,
        "resolution":          [1280, 720]
    },
    "custom_mappings": {}
}


def _deep_merge(defaults: dict, target: dict):
    for key, val in defaults.items():
        if key not in target:
            target[key] = val
        elif isinstance(val, dict) and isinstance(target.get(key), dict):
            _deep_merge(val, target[key])


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        _deep_merge(DEFAULT_CONFIG, cfg)
        return cfg
    return {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def list_profiles() -> list:
    os.makedirs(PROFILES_DIR, exist_ok=True)
    profiles = []
    for fname in sorted(os.listdir(PROFILES_DIR)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(PROFILES_DIR, fname)) as f:
                    p = json.load(f)
                profiles.append({
                    "id":          fname[:-5],
                    "name":        p.get("name", fname[:-5]),
                    "description": p.get("description", ""),
                    "icon":        p.get("icon", "?")
                })
            except Exception:
                pass
    return profiles


def load_profile(profile_id: str) -> dict:
    path = os.path.join(PROFILES_DIR, f"{profile_id}.json")
    with open(path) as f:
        return json.load(f)


def apply_custom_mappings(profile: dict, custom_mappings: dict, profile_id: str) -> dict:
    for ckey, override in custom_mappings.items():
        parts = ckey.split(":")
        if len(parts) != 3 or parts[0] != profile_id:
            continue
        _, hand, gesture = parts
        if hand not in profile["gestures"]:
            continue
        if override is None:
            profile["gestures"][hand][gesture] = None
        else:
            base = dict(profile["gestures"][hand].get(gesture) or {})
            base.update(override)
            profile["gestures"][hand][gesture] = base
    return profile
