import json
import math
import os
import sys

import numpy as np

MONO_FONT = (
    "Menlo" if sys.platform == "darwin" else
    "Consolas" if sys.platform == "win32" else
    "DejaVu Sans Mono"
)

CUSTOM_GESTURES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "custom_gestures.json"
)

MATCH_THRESHOLD = 0.92   # cosine similarity required to recognise a custom gesture


def extract_features(lm) -> list:
    wx, wy = lm[0].x, lm[0].y
    scale  = math.sqrt((lm[9].x - wx) ** 2 + (lm[9].y - wy) ** 2) + 1e-6
    features = []
    for p in lm:
        features.append((p.x - wx) / scale)
        features.append((p.y - wy) / scale)
    return features


def cosine_sim(a, b) -> float:
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / (denom + 1e-6))


def match_custom_gesture(lm, custom_gestures: dict,
                         threshold: float = MATCH_THRESHOLD) -> str | None:
    if not custom_gestures:
        return None
    feats     = extract_features(lm)
    best_name = None
    best_sim  = threshold
    for name, data in custom_gestures.items():
        sim = cosine_sim(feats, data["template"])
        if sim > best_sim:
            best_sim  = sim
            best_name = name
    return best_name


def load_custom_gestures() -> dict:
    if os.path.exists(CUSTOM_GESTURES_PATH):
        with open(CUSTOM_GESTURES_PATH) as f:
            return json.load(f)
    return {}


def save_custom_gestures(gestures: dict):
    with open(CUSTOM_GESTURES_PATH, "w") as f:
        json.dump(gestures, f, indent=2)
