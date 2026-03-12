import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk

from gesture_utils import (
    CUSTOM_GESTURES_PATH,
    MONO_FONT,
    extract_features,
    load_custom_gestures,
    save_custom_gestures,
)

RECORD_SECS  = 2.5
MIN_SAMPLES  = 15

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
                         dot_radius=5, line_thickness=2):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in _HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], line_color, line_thickness)
    for pt in pts:
        cv2.circle(frame, pt, dot_radius, dot_color, -1)

COLORS = {
    "bg":     "#08000e",
    "panel":  "#120020",
    "accent": "#e050ff",
    "green":  "#3dffa8",
    "blue":   "#6ea8ff",
    "text":   "#ffffff",
    "muted":  "#9977bb",
}

CAM_W, CAM_H = 440, 330


class GestureRecorder:
    def __init__(self, parent, on_save=None):
        self.on_save    = on_save
        self.gestures   = load_custom_gestures()

        self._running   = False
        self._recording = False
        self._samples: list[list] = []
        self._current_lm = None
        self._frame      = None

        self.win = tk.Toplevel(parent)
        self.win.title("Custom Gesture Trainer")
        self.win.configure(bg=COLORS["bg"])
        self.win.resizable(False, False)
        self.win.geometry("880x520")
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        self._build()

        self._running = True
        threading.Thread(target=self._cam_loop, daemon=True).start()
        self._update_canvas()

    def _build(self):
        w = self.win

        tk.Label(w, text="Custom Gesture Trainer",
                 fg=COLORS["accent"], bg=COLORS["bg"],
                 font=(MONO_FONT, 16, "bold")).pack(pady=(14, 4))
        tk.Label(w, text="Hold a hand pose  →  type a name  →  click Record",
                 fg=COLORS["muted"], bg=COLORS["bg"],
                 font=(MONO_FONT, 11)).pack()
        tk.Frame(w, bg=COLORS["accent"], height=2).pack(fill="x", padx=20, pady=10)

        body = tk.Frame(w, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=4)

        cam_frame = tk.Frame(body, bg="#000000", width=CAM_W, height=CAM_H)
        cam_frame.pack(side="left")
        cam_frame.pack_propagate(False)

        self._canvas = tk.Canvas(cam_frame, width=CAM_W, height=CAM_H,
                                  bg="#000000", highlightthickness=0)
        self._canvas.pack()

        self._hand_label = tk.Label(cam_frame, text="No hand detected",
                                     fg=COLORS["muted"], bg="#000000",
                                     font=(MONO_FONT, 10))
        self._hand_label.place(x=8, y=CAM_H - 24)

        right = tk.Frame(body, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(18, 0))

        tk.Label(right, text="Gesture Name:", fg=COLORS["muted"], bg=COLORS["bg"],
                 font=(MONO_FONT, 11), anchor="w").pack(anchor="w")
        self._name_var = tk.StringVar()
        tk.Entry(right, textvariable=self._name_var,
                 bg=COLORS["panel"], fg=COLORS["text"],
                 insertbackground="#fff", font=(MONO_FONT, 14),
                 relief="flat", width=20).pack(anchor="w", pady=(4, 8), ipady=6)

        self._status_var = tk.StringVar(value="Ready — show hand to camera")
        tk.Label(right, textvariable=self._status_var,
                 fg=COLORS["green"], bg=COLORS["bg"],
                 font=(MONO_FONT, 11), anchor="w", wraplength=340).pack(anchor="w")

        self._prog_canvas = tk.Canvas(right, width=280, height=14,
                                       bg=COLORS["panel"], highlightthickness=0)
        self._prog_canvas.pack(anchor="w", pady=(6, 10))
        self._prog_bar = self._prog_canvas.create_rectangle(
            0, 0, 0, 14, fill=COLORS["green"], outline=""
        )

        rec_btn = tk.Label(right, text="  Record Gesture  ",
                  bg=COLORS["accent"], fg="white",
                  font=(MONO_FONT, 13, "bold"),
                  padx=16, pady=8, cursor="hand2")
        rec_btn.bind("<Button-1>", lambda e: self._start_record())
        rec_btn.bind("<Enter>", lambda e: rec_btn.config(bg="#c030dd"))
        rec_btn.bind("<Leave>", lambda e: rec_btn.config(bg=COLORS["accent"]))
        rec_btn.pack(anchor="w", pady=(0, 12))

        tk.Frame(right, bg="#2a1040", height=1).pack(fill="x", pady=6)

        tk.Label(right, text="Saved Custom Gestures:",
                 fg=COLORS["muted"], bg=COLORS["bg"],
                 font=(MONO_FONT, 11)).pack(anchor="w")

        list_wrap = tk.Frame(right, bg=COLORS["panel"])
        list_wrap.pack(anchor="w", fill="x", pady=6)

        self._listbox = tk.Listbox(
            list_wrap, bg=COLORS["panel"], fg=COLORS["text"],
            selectbackground=COLORS["accent"],
            font=(MONO_FONT, 12), relief="flat",
            width=28, height=4, activestyle="none"
        )
        self._listbox.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(list_wrap, command=self._listbox.yview,
                          bg=COLORS["panel"], troughcolor=COLORS["panel"])
        sb.pack(side="right", fill="y")
        self._listbox.config(yscrollcommand=sb.set)

        del_btn = tk.Label(right, text="  Delete Selected  ",
                  bg="#2a1050", fg="white",
                  font=(MONO_FONT, 11),
                  padx=12, pady=6, cursor="hand2")
        del_btn.bind("<Button-1>", lambda e: self._delete())
        del_btn.bind("<Enter>", lambda e: del_btn.config(bg="#3d1870"))
        del_btn.bind("<Leave>", lambda e: del_btn.config(bg="#2a1050"))
        del_btn.pack(anchor="w", pady=6)

        self._refresh_list()

    def _cam_loop(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.70,
            min_hand_presence_confidence=0.65,
        )

        with mp.tasks.vision.HandLandmarker.create_from_options(options) as landmarker:
            frame_ts = 0
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    break
                frame    = cv2.flip(frame, 1)
                fh, fw   = frame.shape[:2]
                rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                results  = landmarker.detect_for_video(mp_image, frame_ts)
                frame_ts += 33

                self._current_lm = None

                if results.hand_landmarks:
                    lm               = results.hand_landmarks[0]
                    self._current_lm = lm

                    if self._recording:
                        self._samples.append(extract_features(lm))

                    _draw_hand_landmarks(frame, lm, fw, fh)

                if self._recording:
                    cv2.circle(frame, (frame.shape[1] - 18, 18), 10, (0, 0, 220), -1)

                self._frame = cv2.resize(frame, (CAM_W, CAM_H))

        cap.release()

    def _update_canvas(self):
        if self._frame is not None:
            rgb   = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self._canvas.imgtk = imgtk
            self._canvas.create_image(0, 0, anchor="nw", image=imgtk)

        detected = self._current_lm is not None
        self._hand_label.config(
            text="Hand detected" if detected else "No hand detected",
            fg=COLORS["green"] if detected else COLORS["muted"]
        )

        if self._running:
            self.win.after(33, self._update_canvas)

    def _start_record(self):
        name = self._name_var.get().strip().upper().replace(" ", "_")
        if not name:
            messagebox.showwarning("Name Required",
                                   "Enter a gesture name first.", parent=self.win)
            return
        if not self._current_lm:
            messagebox.showwarning("No Hand Detected",
                                   "Show your hand to the camera before recording.",
                                   parent=self.win)
            return
        if self._recording:
            return

        self._samples   = []
        self._recording = True
        self._status_var.set(f"Recording '{name}'  —  hold the pose...")
        self._prog_canvas.coords(self._prog_bar, 0, 0, 0, 14)

        prog_w = 280

        def _run():
            start = time.time()
            while time.time() - start < RECORD_SECS:
                elapsed = time.time() - start
                try:
                    self._prog_canvas.coords(
                        self._prog_bar, 0, 0,
                        int(prog_w * elapsed / RECORD_SECS), 14
                    )
                except Exception:
                    pass
                time.sleep(0.04)

            self._recording = False

            if len(self._samples) < MIN_SAMPLES:
                self._status_var.set("Too few samples — keep hand visible and try again.")
                self._prog_canvas.coords(self._prog_bar, 0, 0, 0, 14)
                return

            template = np.mean(self._samples, axis=0).tolist()
            self.gestures[name] = {
                "template": template,
                "samples":  len(self._samples)
            }
            save_custom_gestures(self.gestures)
            self._prog_canvas.coords(self._prog_bar, 0, 0, prog_w, 14)
            self._status_var.set(
                f"'{name}' saved  ({len(self._samples)} samples)  —  ready to use!"
            )
            self._refresh_list()
            if self.on_save:
                self.on_save(self.gestures)

        threading.Thread(target=_run, daemon=True).start()

    def _refresh_list(self):
        self._listbox.delete(0, tk.END)
        for name in sorted(self.gestures):
            n = self.gestures[name].get("samples", "?")
            self._listbox.insert(tk.END, f"{name}  ({n} samples)")

    def _delete(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        raw  = self._listbox.get(sel[0])
        name = raw.split("  (")[0]
        if messagebox.askyesno("Delete", f"Delete gesture '{name}'?", parent=self.win):
            self.gestures.pop(name, None)
            save_custom_gestures(self.gestures)
            self._refresh_list()
            if self.on_save:
                self.on_save(self.gestures)

    def _close(self):
        self._running = False
        self.win.destroy()
