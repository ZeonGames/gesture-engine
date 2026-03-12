import sys
import tkinter as tk
import pyautogui

from gesture_utils import MONO_FONT

COLORS = {
    "bg":      "#08000e",
    "panel":   "#120020",
    "accent":  "#e050ff",
    "right":   "#6ea8ff",
    "left":    "#3dffa8",
    "text":    "#ffffff",
    "muted":   "#9977bb",
    "dim":     "#aa88cc",
    "divider": "#2a1040",
    "btn_bg":  "#2a1050",
    "btn_hover": "#3d1870",
}


class GestureOverlay:
    def __init__(self, profile: dict, root: tk.Tk,
                 on_remap=None, on_trainer=None):
        self.screen_w, self.screen_h = pyautogui.size()
        self.on_remap   = on_remap
        self.on_trainer = on_trainer

        self.root = root
        self.root.title("GestureEngine")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        if sys.platform == "darwin":
            self.root.attributes("-alpha", 0.93)
        else:
            self.root.attributes("-alpha", 0.92)
        self.root.configure(bg=COLORS["bg"])

        self._build_ui(profile)
        self._setup_drag()
        self._blink = True
        self._animate()

    def _build_ui(self, profile: dict):
        root = self.root
        icon = profile.get("icon", "?")
        name = profile.get("name", "GestureEngine").upper()

        title_bar = tk.Frame(root, bg=COLORS["bg"])
        title_bar.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(
            title_bar,
            text=f"[{icon}]  GESTURE ENGINE  ·  {name}",
            fg=COLORS["accent"], bg=COLORS["bg"],
            font=(MONO_FONT, 16, "bold")
        ).pack(anchor="w")
        tk.Frame(root, bg=COLORS["accent"], height=2).pack(fill="x", padx=16, pady=(6, 0))

        rh_frame = tk.Frame(root, bg=COLORS["panel"], padx=16, pady=10)
        rh_frame.pack(fill="x", padx=14, pady=(10, 0))

        tk.Label(
            rh_frame, text="RIGHT HAND  →  MOUSE",
            fg=COLORS["right"], bg=COLORS["panel"],
            font=(MONO_FONT, 13, "bold"), anchor="w"
        ).pack(fill="x")

        row_rg = tk.Frame(rh_frame, bg=COLORS["panel"])
        row_rg.pack(fill="x", pady=(6, 0))
        tk.Label(row_rg, text="GESTURE", fg=COLORS["dim"], bg=COLORS["panel"],
                 font=(MONO_FONT, 11), width=10, anchor="w").pack(side="left")
        self._r_gesture_lbl = tk.Label(
            row_rg, text="---", fg=COLORS["text"], bg=COLORS["panel"],
            font=(MONO_FONT, 18, "bold"), anchor="w"
        )
        self._r_gesture_lbl.pack(side="left", padx=(8, 0))

        row_ra = tk.Frame(rh_frame, bg=COLORS["panel"])
        row_ra.pack(fill="x", pady=(2, 0))
        tk.Label(row_ra, text="ACTION", fg=COLORS["dim"], bg=COLORS["panel"],
                 font=(MONO_FONT, 11), width=10, anchor="w").pack(side="left")
        self._r_action_lbl = tk.Label(
            row_ra, text="---", fg=COLORS["right"], bg=COLORS["panel"],
            font=(MONO_FONT, 18, "bold"), anchor="w"
        )
        self._r_action_lbl.pack(side="left", padx=(8, 0))

        lh_frame = tk.Frame(root, bg=COLORS["panel"], padx=16, pady=10)
        lh_frame.pack(fill="x", padx=14, pady=(6, 0))

        tk.Label(
            lh_frame, text="LEFT HAND  →  KEYBOARD",
            fg=COLORS["left"], bg=COLORS["panel"],
            font=(MONO_FONT, 13, "bold"), anchor="w"
        ).pack(fill="x")

        row_lg = tk.Frame(lh_frame, bg=COLORS["panel"])
        row_lg.pack(fill="x", pady=(6, 0))
        tk.Label(row_lg, text="GESTURE", fg=COLORS["dim"], bg=COLORS["panel"],
                 font=(MONO_FONT, 11), width=10, anchor="w").pack(side="left")
        self._l_gesture_lbl = tk.Label(
            row_lg, text="---", fg=COLORS["text"], bg=COLORS["panel"],
            font=(MONO_FONT, 18, "bold"), anchor="w"
        )
        self._l_gesture_lbl.pack(side="left", padx=(8, 0))

        row_la = tk.Frame(lh_frame, bg=COLORS["panel"])
        row_la.pack(fill="x", pady=(2, 0))
        tk.Label(row_la, text="ACTION", fg=COLORS["dim"], bg=COLORS["panel"],
                 font=(MONO_FONT, 11), width=10, anchor="w").pack(side="left")
        self._l_action_lbl = tk.Label(
            row_la, text="---", fg=COLORS["left"], bg=COLORS["panel"],
            font=(MONO_FONT, 18, "bold"), anchor="w"
        )
        self._l_action_lbl.pack(side="left", padx=(8, 0))

        status_frame = tk.Frame(root, bg=COLORS["bg"])
        status_frame.pack(fill="x", padx=16, pady=(10, 0))

        self._status_dot = tk.Canvas(
            status_frame, width=14, height=14,
            bg=COLORS["bg"], highlightthickness=0
        )
        self._status_dot.pack(side="left")
        self._dot_oval = self._status_dot.create_oval(1, 1, 13, 13,
                                                       fill=COLORS["left"], outline="")

        tk.Label(
            status_frame, text="  ACTIVE  │  ESC in camera window to quit",
            fg=COLORS["muted"], bg=COLORS["bg"],
            font=(MONO_FONT, 11)
        ).pack(side="left")

        rec_frame = tk.Frame(root, bg=COLORS["bg"])
        rec_frame.pack(fill="x", padx=16, pady=(4, 0))

        self._rec_dot = tk.Canvas(
            rec_frame, width=14, height=14,
            bg=COLORS["bg"], highlightthickness=0
        )
        self._rec_dot.pack(side="left")
        self._rec_oval = self._rec_dot.create_oval(1, 1, 13, 13,
                                                    fill=COLORS["accent"], outline="")

        tk.Label(
            rec_frame, text="  REC  (last 20s rolling buffer)",
            fg=COLORS["accent"], bg=COLORS["bg"],
            font=(MONO_FONT, 10, "bold")
        ).pack(side="left")

        tk.Frame(root, bg=COLORS["divider"], height=1).pack(fill="x", padx=14, pady=(10, 0))

        btn_frame = tk.Frame(root, bg=COLORS["bg"])
        btn_frame.pack(fill="x", padx=14, pady=(10, 0))

        for text, cmd, color in [
            ("  KEY MAP  ",  self._open_remap,   COLORS["right"]),
            ("   TRAIN   ",  self._open_trainer, COLORS["accent"]),
        ]:
            bg = COLORS["btn_bg"]
            btn = tk.Label(
                btn_frame, text=text,
                bg=bg, fg="white",
                font=(MONO_FONT, 12, "bold"),
                padx=12, pady=6, cursor="hand2"
            )
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=COLORS["btn_hover"]))
            btn.bind("<Leave>", lambda e, b=btn, bg_=bg: b.config(bg=bg_))
            btn.pack(side="left", expand=True, fill="x", padx=3)

        tk.Frame(root, bg=COLORS["divider"], height=1).pack(fill="x", padx=14, pady=(10, 0))

        legend = tk.Frame(root, bg=COLORS["bg"])
        legend.pack(fill="x", padx=16, pady=(6, 10))
        tk.Label(
            legend,
            text="OPEN=4+  PEACE=2  THREE=3  FIST=0  POINT=1  THUMB",
            fg=COLORS["muted"], bg=COLORS["bg"],
            font=(MONO_FONT, 9), anchor="w"
        ).pack(anchor="w")
        tk.Label(
            legend,
            text="PINCH=thumb+index   OK=2+pinch   TRAIN=your own",
            fg=COLORS["muted"], bg=COLORS["bg"],
            font=(MONO_FONT, 9), anchor="w"
        ).pack(anchor="w")

    def _setup_drag(self):
        self.root.bind("<ButtonPress-1>",  self._drag_start)
        self.root.bind("<B1-Motion>",      self._drag_move)
        self._drag_x = 0
        self._drag_y = 0

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _animate(self):
        self._blink = not self._blink
        dot_c = COLORS["left"]   if self._blink else "#0a3322"
        rec_c = COLORS["accent"] if self._blink else "#2a0040"
        self._status_dot.itemconfig(self._dot_oval, fill=dot_c)
        self._rec_dot.itemconfig(self._rec_oval,    fill=rec_c)
        self.root.after(800, self._animate)

    def update(self, r_gesture: str, r_action, l_gesture: str, l_action):
        def fmt_g(g): return g if g and g != "NONE" else "---"
        def fmt_a(a): return a.replace("_", " ").upper() if a else "---"

        self._r_gesture_lbl.config(text=fmt_g(r_gesture))
        self._r_action_lbl.config(text=fmt_a(r_action))
        self._l_gesture_lbl.config(text=fmt_g(l_gesture))
        self._l_action_lbl.config(text=fmt_a(l_action))

    def run(self):
        self.root.mainloop()

    def _open_remap(self):
        if self.on_remap:
            self.on_remap()

    def _open_trainer(self):
        if self.on_trainer:
            self.on_trainer()
