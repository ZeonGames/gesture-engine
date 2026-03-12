import collections
import math
import os
import time
import threading

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController, Button as MouseButton

from gesture_utils import load_custom_gestures, match_custom_gesture

_mouse_ctl = MouseController()
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

_HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (0,17),(13,17),(17,18),(18,19),(19,20),
]

def _draw_hand_landmarks(frame, landmarks, w, h,
                         dot_color=(0,255,255), line_color=(0,200,255),
                         dot_radius=6, line_thickness=3):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in _HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], line_color, line_thickness)
    for pt in pts:
        cv2.circle(frame, pt, dot_radius, dot_color, -1)

_keyboard = KeyboardController()

def _finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def _thumb_up(lm, hand_label):
    return lm[4].x < lm[3].x if hand_label == "Right" else lm[4].x > lm[3].x

def _pinch_dist(lm):
    dx, dy = lm[4].x - lm[8].x, lm[4].y - lm[8].y
    return math.sqrt(dx * dx + dy * dy)

def classify_gesture(lm, hand_label: str) -> str:
    thumb  = _thumb_up(lm, hand_label)
    index  = _finger_up(lm, 8,  6)
    middle = _finger_up(lm, 12, 10)
    ring   = _finger_up(lm, 16, 14)
    pinky  = _finger_up(lm, 20, 18)
    fingers = [index, middle, ring, pinky]
    pinch   = _pinch_dist(lm) < 0.05

    if pinch and not index:                                  return "PINCH"
    if not any([thumb, index, middle, ring, pinky]):         return "FIST"
    if thumb and not any(fingers):                           return "THUMBS_UP"
    if index and not middle and not ring and not pinky:      return "POINT_UP"
    if index and middle and not ring and not pinky:
        return "OK" if _pinch_dist(lm) < 0.07 else "PEACE"
    if index and middle and ring and not pinky:              return "THREE"
    if all([index, middle, ring, pinky]):                    return "OPEN"
    return "NONE"


def _debounce(buf: list, gesture: str, window: int = 5) -> str:
    buf.append(gesture)
    if len(buf) > window:
        buf.pop(0)
    return max(set(buf), key=buf.count)

class GestureEngine:
    AIM_SMOOTH      = 0.65   # EMA alpha  (higher = more responsive)
    AIM_SENS        = 5.5    # base sensitivity multiplier
    AIM_ACCEL       = 1.8    # acceleration exponent (>1 = fast flicks amplified)
    AIM_MAX_PX      = 220    # max pixels per frame
    AIM_DEADZONE    = 0.002  # ignore jitter below this normalised threshold
    WASD_THRESH     = 0.08   # normalised dead-zone radius
    COOLDOWN        = 0.40   # seconds between key_tap repeats

    def __init__(self, profile: dict, profile_id: str, config: dict,
                 storage, tracker, overlay):
        self.profile    = profile
        self.profile_id = profile_id
        self.config     = config
        self.storage    = storage
        self.tracker    = tracker
        self.overlay    = overlay

        rec = config["recorder"]
        perms = config["permissions"]
        analytics_on       = perms.get("analytics") is True
        self.rec_enabled   = rec["enabled"] and analytics_on
        self.shots_enabled = rec["enabled"] and analytics_on
        self.rec_fps       = rec["fps"]
        self.rec_buf_secs  = rec["buffer_secs"]
        self.rec_res       = tuple(rec["resolution"])
        self.shot_interval = rec["screenshot_interval"]

        self._max_frames  = self.rec_buf_secs * self.rec_fps
        self._video_buf   = collections.deque(maxlen=self._max_frames)

        self.screen_w, self.screen_h = pyautogui.size()
        self._running         = False
        self._custom_gestures = load_custom_gestures()

        self._lmb_held   = False
        self._rmb_held   = False
        self._wasd_held  : set[str] = set()
        self._key_held   : dict[str, bool] = {}

        self._rmb_owner  : str | None = None
        self._lmb_owner  : str | None = None
        self._wasd_owner : str | None = None
        self._aim_owner  : str | None = None
        self._khold_owner: str | None = None

        self._aim_origin  = None
        self._smooth_tip  = None

        self._buf = {"right": [], "left": []}

        self._last_gesture = {"right": "NONE", "left": "NONE"}
        self._last_act_t   = {"right": 0.0,    "left": 0.0}

    def run(self):
        self._running = True
        if self.rec_enabled or self.shots_enabled:
            threading.Thread(target=self._record_loop, daemon=True).start()

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        import time
        time.sleep(0.5)

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.75,
            min_hand_presence_confidence=0.70,
        )

        with mp.tasks.vision.HandLandmarker.create_from_options(options) as landmarker:
            frame_ts = 0

            while self._running:
                ok, frame = cap.read()
                if not ok or frame is None or frame.size == 0:
                    break

                frame    = cv2.flip(frame, 1)
                rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                results  = landmarker.detect_for_video(mp_image, frame_ts)
                frame_ts += 33

                r_gesture = r_action = l_gesture = l_action = None
                fh, fw = frame.shape[:2]

                if results.hand_landmarks and results.handedness:
                    for lm, handedness in zip(
                        results.hand_landmarks, results.handedness
                    ):
                        label   = handedness[0].category_name
                        custom  = match_custom_gesture(lm, self._custom_gestures)
                        raw_g   = custom if custom else classify_gesture(lm, label)
                        gesture = _debounce(self._buf[label.lower()], raw_g)

                        if label == "Left":
                            r_gesture = gesture
                            r_action  = self._dispatch("right", gesture, lm)
                            self._last_gesture["right"] = gesture
                        else:
                            l_gesture = gesture
                            l_action  = self._dispatch("left", gesture, lm)
                            self._last_gesture["left"] = gesture

                        _draw_hand_landmarks(frame, lm, fw, fh)

                # Release held inputs when a hand leaves frame
                if not r_gesture:
                    self._release_hand_holds("right")
                if not l_gesture:
                    self._release_hand_holds("left")

                self.overlay.update(r_gesture, r_action, l_gesture, l_action)
                cv2.imshow("GestureEngine Camera", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    self._running = False
                    try:
                        self.overlay.root.after(0, self.overlay.root.destroy)
                    except Exception:
                        pass
                    break

        self._cleanup()
        cap.release()
        cv2.destroyAllWindows()

    def reload_profile(self, new_profile: dict):
        self.profile = new_profile

    def reload_custom_gestures(self, gestures: dict | None = None):
        self._custom_gestures = gestures if gestures is not None else load_custom_gestures()

    def stop(self, blocking: bool = False):
        self._running = False
        if self._video_buf:
            self.storage.save_clip(
                list(self._video_buf), self.rec_fps, self.rec_res,
                label=f"{self.profile_id}_session",
                blocking=blocking
            )

    def _dispatch(self, hand: str, gesture: str, lm) -> str | None:
        mapping      = self.profile["gestures"].get(hand, {}).get(gesture)
        action_type  = (mapping or {}).get("type", "disabled")
        needs_rmb    = action_type == "mouse_right_hold"
        needs_lmb    = action_type == "mouse_left_hold"
        needs_wasd   = action_type == "wasd"
        needs_aim    = action_type == "mouse_move"
        needs_khold  = action_type == "key_hold"

        if not needs_rmb   and self._rmb_owner   in (None, hand):
            self._release_rmb();        self._rmb_owner   = None
        if not needs_lmb   and self._lmb_owner   in (None, hand):
            self._release_lmb();        self._lmb_owner   = None
        if not needs_wasd  and self._wasd_owner  in (None, hand):
            self._release_wasd();       self._wasd_owner  = None
        if not needs_aim   and self._aim_owner   in (None, hand):
            self._aim_origin = None;    self._smooth_tip  = None;  self._aim_owner   = None
        if not needs_khold and self._khold_owner in (None, hand):
            self._release_held_keys();  self._khold_owner = None

        if not mapping or action_type == "disabled":
            return None

        label = mapping.get("label", action_type)
        key   = mapping.get("key", "")
        now   = time.time()

        try:
            mx, my = pyautogui.position()
            self.tracker.record(label, gesture, mx, my)
        except Exception:
            pass

        if action_type == "mouse_move":
            self._aim_owner = hand
            tip      = lm[9]
            sx, sy   = self._smooth_aim(tip.x, tip.y)
            if self._aim_origin is None:
                self._aim_origin = (sx, sy)
            raw_dx = (sx - self._aim_origin[0]) * self.screen_w * self.AIM_SENS
            raw_dy = (sy - self._aim_origin[1]) * self.screen_h * self.AIM_SENS
            dist = math.sqrt(raw_dx * raw_dx + raw_dy * raw_dy)
            if dist > self.AIM_DEADZONE * self.screen_w:
                accel = math.pow(dist, self.AIM_ACCEL) / (dist + 1e-9)
                dx = int(raw_dx / (dist + 1e-9) * accel)
                dy = int(raw_dy / (dist + 1e-9) * accel)
                dx = max(-self.AIM_MAX_PX, min(self.AIM_MAX_PX, dx))
                dy = max(-self.AIM_MAX_PX, min(self.AIM_MAX_PX, dy))
                _mouse_ctl.move(dx, dy)
            self._aim_origin = (sx, sy)

        elif action_type == "mouse_right_hold":
            if not self._rmb_held:
                _mouse_ctl.press(MouseButton.right)
                self._rmb_held = True
            self._rmb_owner = hand

        elif action_type == "mouse_left_hold":
            if not self._lmb_held:
                _mouse_ctl.press(MouseButton.left)
                self._lmb_held = True
            self._lmb_owner = hand

        elif action_type == "key_tap":
            if (gesture != self._last_gesture[hand]
                    or now - self._last_act_t[hand] > self.COOLDOWN):
                try:
                    _keyboard.press(key)
                    time.sleep(0.05)
                    _keyboard.release(key)
                    self._last_act_t[hand] = now
                except Exception:
                    pass

        elif action_type == "key_hold":
            if not self._key_held.get(key):
                try:
                    _keyboard.press(key)
                    self._key_held[key] = True
                    self._khold_owner = hand
                except Exception:
                    pass

        elif action_type == "wasd":
            self._wasd_owner = hand
            px, py = lm[9].x, lm[9].y
            self._update_wasd(px, py)
            keys   = "+".join(sorted(k.upper() for k in self._wasd_held))
            label  = keys if keys else "MOVE"

        elif action_type == "scroll":
            dy_hand   = lm[9].y - 0.5
            scroll_px = -int(dy_hand * 6)
            if abs(scroll_px) > 0:
                pyautogui.scroll(scroll_px)

        return label

    def _update_wasd(self, px: float, py: float):
        dx, dy  = px - 0.5, py - 0.5
        desired: set[str] = set()
        if dy < -self.WASD_THRESH: desired.add("w")
        if dy >  self.WASD_THRESH: desired.add("s")
        if dx < -self.WASD_THRESH: desired.add("a")
        if dx >  self.WASD_THRESH: desired.add("d")
        for k in self._wasd_held - desired:  _keyboard.release(k)
        for k in desired - self._wasd_held:  _keyboard.press(k)
        self._wasd_held = desired

    def _release_wasd(self):
        for k in self._wasd_held:
            try: _keyboard.release(k)
            except Exception: pass
        self._wasd_held = set()

    def _release_lmb(self):
        if self._lmb_held:
            _mouse_ctl.release(MouseButton.left)
            self._lmb_held = False

    def _release_rmb(self):
        if self._rmb_held:
            _mouse_ctl.release(MouseButton.right)
            self._rmb_held = False

    def _release_held_keys(self):
        for k, held in list(self._key_held.items()):
            if held:
                try: _keyboard.release(k)
                except Exception: pass
        self._key_held.clear()

    def _smooth_aim(self, x: float, y: float) -> tuple[float, float]:
        if self._smooth_tip is None:
            self._smooth_tip = (x, y)
        else:
            a = self.AIM_SMOOTH
            self._smooth_tip = (
                a * x + (1 - a) * self._smooth_tip[0],
                a * y + (1 - a) * self._smooth_tip[1]
            )
        return self._smooth_tip

    def _release_hand_holds(self, hand: str):
        if self._rmb_owner   == hand: self._release_rmb();        self._rmb_owner   = None
        if self._lmb_owner   == hand: self._release_lmb();        self._lmb_owner   = None
        if self._wasd_owner  == hand: self._release_wasd();       self._wasd_owner  = None
        if self._khold_owner == hand: self._release_held_keys();  self._khold_owner = None
        if self._aim_owner   == hand:
            self._aim_origin = None;  self._smooth_tip = None;    self._aim_owner   = None

    def _cleanup(self):
        self._release_lmb()
        self._release_rmb()
        self._release_wasd()
        self._release_held_keys()
        self._rmb_owner = self._lmb_owner = self._wasd_owner = self._aim_owner = self._khold_owner = None

    def _record_loop(self):
        interval      = 1.0 / self.rec_fps
        last_shot_t   = 0.0

        while self._running:
            t0 = time.time()
            try:
                pil   = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
                frame = cv2.resize(frame, self.rec_res)

                if self.rec_enabled:
                    self._video_buf.append(frame)

                if self.shots_enabled and self.shot_interval > 0 and (t0 - last_shot_t) >= self.shot_interval:
                    self.storage.save_screenshot(frame, label=self.profile_id)
                    last_shot_t = t0
            except Exception as e:
                pass

            sleep_t = interval - (time.time() - t0)
            if sleep_t > 0:
                time.sleep(sleep_t)
