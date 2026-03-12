import json
import os
import time


class InteractionTracker:
    def __init__(self):
        self._events: list[dict] = []

    def record(self, action: str, gesture: str, x: int | None = None, y: int | None = None):
        self._events.append({
            "t":       time.time(),
            "action":  action,
            "gesture": gesture,
            "x":       x,
            "y":       y
        })

    def get_events(self) -> list[dict]:
        return list(self._events)

    def generate_heatmap(self, screen_w: int, screen_h: int) -> tuple[bytes, str] | None:
        if not self._events:
            return None
        
        if screen_w <= 0 or screen_h <= 0:
            return None
        
        try:
            import numpy as np
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from scipy.ndimage import gaussian_filter
            import io
        except ImportError:
            return None

        try:
            points = [
                (e["x"], e["y"])
                for e in self._events
                if e.get("x") is not None and e.get("y") is not None
            ]
            if not points or len(points) == 0:
                return None

            grid = np.zeros((screen_h, screen_w), dtype=np.float32)
            for x, y in points:
                if x is None or y is None:
                    continue
                gx = int(max(0, min(screen_w - 1, x)))
                gy = int(max(0, min(screen_h - 1, y)))
                grid[gy, gx] += 1.0

            if grid.max() == 0:
                return None

            sigma = max(screen_w, screen_h) // 40
            if sigma < 1:
                sigma = 1
            grid = gaussian_filter(grid, sigma=sigma)

            fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
            ax.imshow(grid, cmap="hot", origin="upper", aspect="auto", interpolation="bilinear")
            ax.set_title(
                f"Interaction Heatmap  ({len(points)} events)",
                color="white", fontsize=13, pad=10
            )
            ax.axis("off")
            fig.patch.set_facecolor("#0a0a0f")

            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#0a0a0f", dpi=120)
            plt.close(fig)
            
            heatmap_data = buf.getvalue()
            buf.close()
            
            if not heatmap_data or len(heatmap_data) == 0:
                return None
            
            filename = f"heatmap_{time.strftime('%Y%m%d_%H%M%S')}.png"
            return (heatmap_data, filename)
        except Exception:
            return None

    def get_gesture_summary(self) -> dict:
        summary: dict[str, int] = {}
        for e in self._events:
            g = e.get("gesture", "NONE")
            summary[g] = summary.get(g, 0) + 1
        return summary
