import os
import signal
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from config_manager    import load_config, save_config, list_profiles, load_profile, apply_custom_mappings
from gesture_utils     import MONO_FONT
from gesture_engine    import GestureEngine
from gesture_recorder  import GestureRecorder
from heatmap_generator import InteractionTracker
from mapping_editor    import MappingEditor
from storage_manager   import StorageManager
from ui_overlay        import GestureOverlay


COLORS = {
    "bg":     "#08000e",
    "panel":  "#120020",
    "accent": "#e050ff",
    "green":  "#3dffa8",
    "blue":   "#6ea8ff",
    "text":   "#ffffff",
    "muted":  "#9977bb",
}


class PermissionDialog:
    """
    Shows once when permissions haven't been set.
    Camera is required. 'Help Us Improve' is a single opt-in for all data capture.
    """

    def __init__(self, parent, config: dict):
        self.config = config
        self.win    = tk.Toplevel(parent)
        self.win.title("GestureEngine — Permissions")
        self.win.configure(bg=COLORS["bg"])
        self.win.resizable(False, False)
        self.win.geometry("580x440")
        self.win.grab_set()
        self._build()

    def _build(self):
        w = self.win
        tk.Label(w, text="GestureEngine — Permission Request",
                 fg=COLORS["accent"], bg=COLORS["bg"],
                 font=(MONO_FONT, 16, "bold")).pack(pady=(20, 6))

        tk.Label(w, text="Please review what this app will access on your machine.",
                 fg=COLORS["muted"], bg=COLORS["bg"],
                 font=(MONO_FONT, 11), wraplength=520).pack()

        tk.Frame(w, bg=COLORS["accent"], height=2).pack(fill="x", padx=24, pady=10)

        perms_frame = tk.Frame(w, bg=COLORS["bg"])
        perms_frame.pack(fill="x", padx=28)

        self._cam_var       = tk.BooleanVar(value=True)
        self._analytics_var = tk.BooleanVar(value=self.config["permissions"].get("analytics") is not False)

        self._perm_row(perms_frame,
                       "Camera Access  (required)",
                       "Webcam used for hand gesture detection only.\n"
                       "No camera footage is saved or transmitted.",
                       self._cam_var, required=True)

        self._perm_row(perms_frame,
                       "Help Us Improve  (optional)",
                       "Capture gesture data, heatmaps, and usage clips to help improve recognition.\n"
                       "Data is uploaded to our servers. Nothing is stored locally if upload fails.",
                       self._analytics_var)

        tk.Frame(w, bg="#1a0025", height=1).pack(fill="x", padx=24, pady=14)

        btn_row = tk.Frame(w, bg=COLORS["bg"])
        btn_row.pack(pady=6)
        self._make_btn(btn_row, "  Agree & Start  ", self._agree,
                       COLORS["accent"], "white", (MONO_FONT, 13, "bold")
                       ).pack(side="left", padx=10)
        self._make_btn(btn_row, "  Cancel  ", self._cancel,
                       "#1a0025", COLORS["muted"], (MONO_FONT, 12)
                       ).pack(side="left", padx=10)

    @staticmethod
    def _make_btn(parent, text, command, bg, fg, font):
        lbl = tk.Label(parent, text=text, bg=bg, fg=fg,
                       font=font, padx=20, pady=10, cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.config(bg="#c030dd" if bg != "#1a0025" else "#2a0040"))
        lbl.bind("<Leave>", lambda e: lbl.config(bg=bg))
        return lbl

    def _perm_row(self, parent, title, desc, var, required=False):
        frame = tk.Frame(parent, bg=COLORS["panel"], padx=14, pady=12)
        frame.pack(fill="x", pady=4)

        check_text = "\u2611" if var.get() else "\u2610"
        check_lbl = tk.Label(
            frame, text=check_text,
            fg="white", bg=COLORS["panel"],
            font=(MONO_FONT, 16), cursor="hand2"
        )
        check_lbl.pack(side="left")

        if not required:
            def toggle(e):
                var.set(not var.get())
                check_lbl.config(text="\u2611" if var.get() else "\u2610")
            check_lbl.bind("<Button-1>", toggle)

        info = tk.Frame(frame, bg=COLORS["panel"])
        info.pack(side="left", fill="x", expand=True, padx=(10, 0))

        tk.Label(info, text=title,
                 fg=COLORS["accent"] if required else "white",
                 bg=COLORS["panel"],
                 font=(MONO_FONT, 12, "bold"), anchor="w").pack(anchor="w")
        tk.Label(info, text=desc,
                 fg=COLORS["muted"], bg=COLORS["panel"],
                 font=(MONO_FONT, 10), justify="left", anchor="w",
                 wraplength=420).pack(anchor="w", pady=(2, 0))

    def _agree(self):
        self.config["permissions"]["camera"]    = True
        self.config["permissions"]["analytics"] = self._analytics_var.get()
        self.win.destroy()

    def _cancel(self):
        self.config["permissions"]["camera"] = False
        self.win.destroy()


class App:
    def __init__(self):
        self.config  = load_config()
        self._root   = tk.Tk()
        self._root.withdraw()   # hidden root, dialogs use Toplevel

    def run(self):
        pyautogui_import_guard()

        if not self._ensure_permissions():
            self._root.destroy()
            return

        profile_id = self._select_profile()
        if not profile_id:
            self._root.destroy()
            return

        try:
            profile = load_profile(profile_id)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Profile '{profile_id}' not found.")
            self._root.destroy()
            return

        apply_custom_mappings(profile, self.config["custom_mappings"], profile_id)

        storage = StorageManager(self.config)
        tracker = InteractionTracker()

        engine = GestureEngine(profile, profile_id, self.config, storage, tracker, None)
        self._engine     = engine
        self._profile_id = profile_id

        overlay = GestureOverlay(
            profile, self._root,
            on_remap   = lambda: self._open_mapping_editor(profile_id),
            on_trainer = lambda: self._open_trainer()
        )
        engine.overlay = overlay

        def _sigint(sig, frame):
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
        signal.signal(signal.SIGINT, _sigint)

        eng_thread = threading.Thread(target=engine.run, daemon=True)
        eng_thread.start()

        self._root.deiconify()
        try:
            overlay.run()       # blocks until window closed or Ctrl+C
        except (KeyboardInterrupt, tk.TclError):
            pass
        finally:
            self._shutdown(engine, tracker, storage, overlay)

    def _shutdown(self, engine, tracker, storage, overlay):
        engine.stop(blocking=True)

        storage.save_interactions(tracker.get_events(), blocking=True)
        
        heatmap_result = tracker.generate_heatmap(overlay.screen_w, overlay.screen_h)
        if heatmap_result:
            heatmap_data, filename = heatmap_result
            storage.save_heatmap(heatmap_data, filename, blocking=True)

        try:
            self._root.destroy()
        except Exception:
            pass

    def _ensure_permissions(self) -> bool:
        perms = self.config["permissions"]
        perms["camera"] = None
        perms["analytics"] = None
        
        dlg = PermissionDialog(self._root, self.config)
        self._root.wait_window(dlg.win)
        save_config(self.config)

        if not self.config["permissions"].get("camera"):
            messagebox.showerror(
                "Camera Access Denied",
                "Camera access is required for gesture detection.\n"
                "Please restart and grant camera permission."
            )
            return False
        return True

    def _select_profile(self) -> str | None:
        profiles = list_profiles()
        if not profiles:
            messagebox.showerror("No Profiles",
                                 "No profiles found in the profiles/ directory.")
            return None

        last = self.config.get("last_profile")
        if last and any(p["id"] == last for p in profiles):
            return last

        return profiles[0]["id"]

    def _open_mapping_editor(self, profile_id: str):
        try:
            fresh_profile = load_profile(profile_id)
        except Exception:
            messagebox.showerror("Error", "Could not reload profile.")
            return

        def on_save(custom_mappings):
            self.config["custom_mappings"] = custom_mappings
            save_config(self.config)
            updated = load_profile(profile_id)
            apply_custom_mappings(updated, custom_mappings, profile_id)
            self._engine.reload_profile(updated)

        MappingEditor(
            self._root, fresh_profile, profile_id,
            dict(self.config["custom_mappings"]),   # pass a copy so editor edits don't mutate live config
            on_save
        )

    def _open_trainer(self):
        def on_save(gestures):
            self._engine.reload_custom_gestures(gestures)

        GestureRecorder(self._root, on_save=on_save)


def pyautogui_import_guard():
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0


if __name__ == "__main__":
    print("""
+===============================================+
|      GESTURE ENABLEMENT LAYER                 |
|  Universal hand gesture controller            |
+-----------------------------------------------+
|  RIGHT HAND  ->  mouse / aim                  |
|  LEFT HAND   ->  keyboard / actions           |
+-----------------------------------------------+
|  Overlay buttons: KEY MAP | TRAIN             |
|  Close overlay window to quit                 |
+===============================================+
    """)
    App().run()
