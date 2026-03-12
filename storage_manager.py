import json
import os
import threading
import time
import tempfile
import cv2

try:
    from api_config import API_ENDPOINTS, API_TIMEOUT
except ImportError:
    API_ENDPOINTS = {}
    API_TIMEOUT = 10


class StorageManager:
    def __init__(self, config: dict):
        self._config  = config
        self._analytics_ok = config["permissions"].get("analytics") is True

    def save_screenshot(self, frame, label: str = "screenshot") -> str:
        if not self._analytics_ok:
            return ""
        ok, buf = cv2.imencode(".png", frame)
        if ok:
            filename = f"{label}_{time.strftime('%Y%m%d_%H%M%S')}.png"
            threading.Thread(
                target=self._upload_bytes,
                args=(buf.tobytes(), filename, "screenshot"),
                daemon=True
            ).start()
        return ""

    def save_clip(self, frames: list, fps: int, resolution: tuple,
                  label: str = "clip", blocking: bool = False) -> str | None:
        if not self._analytics_ok or not frames:
            return None
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".mp4", prefix="gesture_", dir=tempfile.gettempdir())
            os.close(fd)
            
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(temp_path, fourcc, fps, resolution)
            for frm in frames:
                out.write(frm)
            out.release()
            
            with open(temp_path, "rb") as f:
                video_data = f.read()
            
            filename = f"{label}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            if blocking:
                self._upload_bytes(video_data, filename, "video")
            else:
                threading.Thread(
                    target=self._upload_bytes,
                    args=(video_data, filename, "video"),
                    daemon=True
                ).start()
            
            try:
                os.remove(temp_path)
            except Exception:
                pass
        except Exception:
            pass
        return None

    def save_heatmap(self, heatmap_data: bytes, filename: str, blocking: bool = False):
        if not self._analytics_ok:
            return
        if not heatmap_data or len(heatmap_data) == 0:
            return
        if blocking:
            self._upload_bytes(heatmap_data, filename, "heatmap")
        else:
            threading.Thread(
                target=self._upload_bytes,
                args=(heatmap_data, filename, "heatmap"),
                daemon=True
            ).start()

    def save_interactions(self, events: list, blocking: bool = False):
        if not self._analytics_ok or not events:
            return
        try:
            json_data = json.dumps(events, indent=2).encode()
            filename = f"interactions_{time.strftime('%Y%m%d_%H%M%S')}.json"
            if blocking:
                self._upload_bytes(json_data, filename, "interactions")
            else:
                threading.Thread(
                    target=self._upload_bytes,
                    args=(json_data, filename, "interactions"),
                    daemon=True
                ).start()
        except Exception:
            pass

    def _upload_bytes(self, data: bytes, filename: str, data_type: str):
        endpoint = API_ENDPOINTS.get(data_type)
        if not endpoint:
            return
        
        for attempt in range(2):
            try:
                import urllib.request
                boundary = "----GestureEngineUpload"
                body_parts = [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
                    f"Content-Type: application/octet-stream\r\n\r\n".encode(),
                    data,
                    f"\r\n--{boundary}--\r\n".encode()
                ]
                body = b"".join(body_parts)
                
                req = urllib.request.Request(
                    endpoint, data=body, method="POST"
                )
                req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
                req.add_header("User-Agent", "GestureEngine/1.0")
                
                urllib.request.urlopen(req, timeout=API_TIMEOUT)
                return
            except Exception:
                if attempt == 0:
                    import time
                    time.sleep(2)
                pass
