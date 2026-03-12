import tkinter as tk
from tkinter import ttk, messagebox

from gesture_utils import MONO_FONT, load_custom_gestures

BUILTIN_GESTURES = ["OPEN", "FIST", "POINT_UP", "PEACE", "THREE", "THUMBS_UP", "PINCH", "OK"]


def _all_gestures() -> list[str]:
    """Built-in gestures + any custom gestures recorded by the user."""
    custom = sorted(load_custom_gestures().keys())
    return BUILTIN_GESTURES + custom

ACTION_TYPES = [
    "mouse_move",
    "mouse_left_hold",
    "mouse_right_hold",
    "key_tap",
    "key_hold",
    "wasd",
    "scroll",
    "disabled"
]

COLORS = {
    "bg":       "#08000e",
    "panel":    "#120020",
    "row_a":    "#0e0018",
    "row_b":    "#140022",
    "accent":   "#e050ff",
    "right":    "#6ea8ff",
    "left":     "#3dffa8",
    "text":     "#ffffff",
    "muted":    "#9977bb",
    "key_col":  "#e0aaff",
}


class MappingEditor:
    def __init__(self, parent, profile: dict, profile_id: str,
                 custom_mappings: dict, on_save):
        self.profile         = profile
        self.profile_id      = profile_id
        self.custom_mappings = custom_mappings
        self.on_save         = on_save
        self._rows: list[dict] = []

        self.win = tk.Toplevel(parent)
        self.win.title(f"Gesture Mapper  —  {profile['name']}")
        self.win.configure(bg=COLORS["bg"])
        self.win.resizable(True, True)
        self.win.geometry("820x640")
        self._build()

    def _build(self):
        win = self.win

        tk.Label(
            win, text=f"Gesture Key Mapper  ·  {self.profile['name']}",
            fg=COLORS["accent"], bg=COLORS["bg"], font=(MONO_FONT, 16, "bold")
        ).pack(pady=(14, 4))

        tk.Label(
            win,
            text="Edit Action Type and Key columns.  'disabled' removes a mapping.",
            fg=COLORS["muted"], bg=COLORS["bg"], font=(MONO_FONT, 11)
        ).pack(pady=(0, 8))

        tk.Frame(win, bg=COLORS["accent"], height=2).pack(fill="x", padx=16, pady=(0, 6))

        outer = tk.Frame(win, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=16)

        canvas = tk.Canvas(outer, bg=COLORS["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        table = tk.Frame(canvas, bg=COLORS["bg"])
        canvas.create_window((0, 0), window=table, anchor="nw")
        table.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        self._build_table(table)

        btn_frame = tk.Frame(win, bg=COLORS["bg"])
        btn_frame.pack(pady=12)

        self._btn(btn_frame, "  Save Mappings  ",  self._save,  COLORS["accent"]).pack(side="left", padx=8)
        self._btn(btn_frame, " Reset to Default ", self._reset, "#2a1050").pack(side="left", padx=8)
        self._btn(btn_frame, "      Close      ",  win.destroy, "#1a0025").pack(side="left", padx=8)

    def _build_table(self, frame):
        cols   = ["Hand", "Gesture", "Label", "Action Type", "Key"]
        widths = [7,       14,        18,       18,            10]

        for col, (h, w) in enumerate(zip(cols, widths)):
            tk.Label(
                frame, text=h, fg=COLORS["muted"], bg=COLORS["panel"],
                font=(MONO_FONT, 11, "bold"), width=w, anchor="w",
                padx=6, pady=6
            ).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        self._rows.clear()
        row_num = 1

        for hand in ("right", "left"):
            hand_gestures = self.profile["gestures"].get(hand, {})
            for gesture in _all_gestures():
                mapping = hand_gestures.get(gesture)

                ckey = f"{self.profile_id}:{hand}:{gesture}"
                if ckey in self.custom_mappings:
                    override = self.custom_mappings[ckey]
                    if override is None:
                        mapping = None
                    else:
                        mapping = {**(mapping or {}), **override}

                m         = mapping or {}
                label_var = tk.StringVar(value=m.get("label", ""))
                type_var  = tk.StringVar(value=m.get("type", "disabled"))
                key_var   = tk.StringVar(value=m.get("key", ""))

                bg = COLORS["row_a"] if row_num % 2 == 0 else COLORS["row_b"]
                hc = COLORS["right"] if hand == "right" else COLORS["left"]

                tk.Label(
                    frame, text=hand.upper(), fg=hc, bg=bg,
                    font=(MONO_FONT, 11, "bold"), width=7, anchor="w", padx=6
                ).grid(row=row_num, column=0, sticky="nsew", padx=1, pady=1)

                tk.Label(
                    frame, text=gesture, fg=COLORS["text"], bg=bg,
                    font=(MONO_FONT, 11), width=14, anchor="w", padx=6
                ).grid(row=row_num, column=1, sticky="nsew", padx=1, pady=1)

                tk.Entry(
                    frame, textvariable=label_var, bg=bg, fg=COLORS["text"],
                    insertbackground="#fff", font=(MONO_FONT, 11),
                    width=18, relief="flat"
                ).grid(row=row_num, column=2, sticky="nsew", padx=1, pady=1)

                type_cb = ttk.Combobox(
                    frame, textvariable=type_var, values=ACTION_TYPES,
                    width=18, font=(MONO_FONT, 11), state="readonly"
                )
                type_cb.grid(row=row_num, column=3, sticky="nsew", padx=1, pady=1)

                tk.Entry(
                    frame, textvariable=key_var, bg=bg, fg=COLORS["key_col"],
                    insertbackground="#fff", font=(MONO_FONT, 11),
                    width=10, relief="flat"
                ).grid(row=row_num, column=4, sticky="nsew", padx=1, pady=1)

                self._rows.append({
                    "hand":      hand,
                    "gesture":   gesture,
                    "label_var": label_var,
                    "type_var":  type_var,
                    "key_var":   key_var
                })
                row_num += 1

    def _save(self):
        for row in self._rows:
            ckey = f"{self.profile_id}:{row['hand']}:{row['gesture']}"
            t    = row["type_var"].get()
            if t == "disabled":
                self.custom_mappings[ckey] = None
            else:
                self.custom_mappings[ckey] = {
                    "label": row["label_var"].get(),
                    "type":  t,
                    "key":   row["key_var"].get()
                }
        self.on_save(self.custom_mappings)
        messagebox.showinfo("Saved", "Gesture mappings saved and applied immediately.",
                            parent=self.win)

    def _reset(self):
        keys = [k for k in self.custom_mappings if k.startswith(f"{self.profile_id}:")]
        for k in keys:
            del self.custom_mappings[k]
        self.on_save(self.custom_mappings)
        self.win.destroy()
        messagebox.showinfo("Reset", "Mappings reset to profile defaults.")

    @staticmethod
    def _btn(parent, text, cmd, bg):
        lbl = tk.Label(
            parent, text=text, bg=bg, fg="white",
            font=(MONO_FONT, 12, "bold"), padx=16, pady=8, cursor="hand2"
        )
        lbl.bind("<Button-1>", lambda e: cmd())
        lbl.bind("<Enter>", lambda e: lbl.config(bg="#3d1870"))
        lbl.bind("<Leave>", lambda e: lbl.config(bg=bg))
        return lbl
