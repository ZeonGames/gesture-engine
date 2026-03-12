<p align="center">
  <a href="https://gamesbyzeon.com">
    <img src="./profiles/content/banner.png" width="100%" alt="GestureEngine" />
  </a>
</p>

<p align="center">
  <strong>🎮 GestureEngine — Universal Gesture Enablement Layer for Games</strong>
</p>

<p align="center">
  <strong>Language isn't enough to understand the world. Building Zeon, AI that learns from games, gestures, and human behaviour in motion.</strong>
</p>

<br />

<p align="center">
  <a href="https://github.com/ZeonGames/gesture-engine">Repository</a> •
  <a href="https://gamesbyzeon.com">Website</a> •
  <a href="https://discord.gg/UwWRqgREXj">Discord</a> •
  <a href="https://chat.whatsapp.com/HaAV7ahK8ItCtJmM2CN5p6">WhatsApp Group</a> •
  <a href="https://www.linkedin.com/company/zeonai/">LinkedIn</a> •
  <a href="https://www.youtube.com/@zeongamesandstudio">YouTube</a> •
  <a href="https://x.com/ZeonGamesStudio">Twitter</a> •
  <a href="https://www.instagram.com/gamesbyzeon/">Instagram</a>
</p>

---

## Quick Start

Control your PC with hand gestures — no controllers, no buttons, just your hands and a webcam.

GestureEngine uses your webcam and MediaPipe to recognize hand gestures in real time and translate them into keyboard and mouse inputs. It works with any application through configurable profiles.

**Installation:**

```bash
git clone https://github.com/ZeonGames/gesture-engine.git
cd gesture-engine
pip install -r requirements.txt
```

**Running:**

Double-click `START.bat` (Windows) or run from terminal:

```bash
python main.py
```

On first launch you will be asked for:
- **Camera access** — required for gesture detection
- **Help improve gestures** — optional anonymous data sharing to improve recognition accuracy

---

## Demo

See GestureEngine in action:

<a href="https://gamesbyzeon.com">
  <img src="./profiles/content/geDemo.gif" width="100%" alt="GestureEngine Demo" />
</a>

Control your PC with natural hand gestures and interact with any application seamlessly.

---

## Features

- **Real-time hand gesture recognition** via webcam using MediaPipe
- **Universal compatibility** — works with any application through configurable profiles
- **Independent hand mappings** — configure left and right hands separately
- **Draggable HUD overlay** — see active gestures in real-time
- **In-app gesture remapper** — no config file editing needed
- **Custom gesture recorder** — train your own hand poses
- **Optional anonymous analytics** — help improve recognition accuracy
- **Cross-platform** — macOS 12+ and Windows 10/11

---

## Supported Gestures

| Gesture     | Description                  |
|-------------|------------------------------|
| `OPEN`      | All five fingers extended    |
| `FIST`      | All fingers closed           |
| `POINT_UP`  | Index finger raised          |
| `PEACE`     | Index and middle raised      |
| `THREE`     | Index, middle, ring raised   |
| `THUMBS_UP` | Thumb extended upward        |
| `PINCH`     | Thumb and index pinched      |
| `OK`        | OK sign                      |

Each gesture can be independently mapped per hand per profile.

---

## Profiles

Profiles live in the `profiles/` directory as JSON files. A default profile is included and can be duplicated and customized for any use case.

### Profile Structure

```json
{
  "name": "My Profile",
  "description": "What this profile does",
  "icon": "P",
  "gestures": {
    "right": {
      "OPEN":     { "type": "mouse_move",       "label": "Aim / Look" },
      "PINCH":    { "type": "mouse_right_hold", "label": "Right Click" }
    },
    "left": {
      "FIST":     { "type": "wasd",             "label": "Move" },
      "POINT_UP": { "type": "mouse_left_hold",  "label": "Left Click" },
      "PEACE":    { "type": "key_tap", "key": "e", "label": "Action E" }
    }
  }
}
```

### Action Types

| Type               | Description                              |
|--------------------|------------------------------------------|
| `mouse_move`       | Move the mouse cursor                    |
| `mouse_left_hold`  | Hold left mouse button                   |
| `mouse_right_hold` | Hold right mouse button                  |
| `key_tap`          | Tap a keyboard key                       |
| `key_hold`         | Hold a keyboard key                      |
| `wasd`             | WASD movement driven by hand tilt        |
| `scroll`           | Scroll wheel                             |
| `disabled`         | Ignore this gesture                      |

To create a new profile, copy `profiles/default.json`, rename it, customize the mappings, and restart.

---

## Remapping Gestures

Click **KEY MAP** in the overlay to open the mapping editor. Changes are saved per profile and applied live without restarting.

---

## Custom Gestures

Click **TRAIN** in the overlay to open the gesture recorder. Hold your hand pose steady and record samples — the engine will match it from then on.

---

## Analytics (Optional)

When you enable "Help Improve Gestures" on the permissions screen, anonymous gesture data (heatmaps, screenshots) is sent to our servers to improve recognition accuracy over time. This data may eventually be open-sourced as a training dataset to benefit the broader community.

---

## Requirements

- macOS 12+ or Windows 10/11
- Python 3.10+
- Webcam

---

## Project Structure

```
main.py               Entry point
gesture_engine.py     Core loop: camera -> classify -> dispatch input
ui_overlay.py         Transparent HUD overlay
mapping_editor.py     Gesture remapping UI
gesture_recorder.py   Custom gesture training UI
config_manager.py     Load/save config and profiles
storage_manager.py    Analytics API upload
heatmap_generator.py  Heatmap rendering
api_config.py         API endpoint configuration
profiles/             Profile JSONs
```

---

## Contributing

Contributions are welcome! To contribute:

1. **Issues:** [Report bugs or request features](https://github.com/ZeonGames/gesture-engine/issues)
2. **Pull Requests:** [Submit changes](https://github.com/ZeonGames/gesture-engine/pulls)
   - To add a new profile, create a JSON file in `profiles/` following the structure above
   - Ensure code follows existing style and patterns
   - Test your changes before submitting

**Community:**

- Join our [Discord](https://discord.gg/UwWRqgREXj) for discussions
- Follow updates on [LinkedIn](https://www.linkedin.com/company/zeonai/)
- Check out [Zeon Games & Studio](https://gamesbyzeon.com) for more projects

---

## About Zeon

Zeon is building the AI infrastructure to understand human behavior in interactive worlds. We believe the future is gesture-driven and interactive, and games provide the perfect training ground for systems that understand space, time, and human decision-making.

**Learn more:**
- [Website](https://gamesbyzeon.com)
- [LinkedIn](https://www.linkedin.com/company/zeonai/)
- [YouTube](https://www.youtube.com/@zeongamesandstudio)
- [Twitter](https://x.com/ZeonGamesStudio)
- [Instagram](https://www.instagram.com/gamesbyzeon/)

---

<p align="center">
  <strong>Built with ❤️ by <a href="https://gamesbyzeon.com">Zeon Games & Studio</a></strong>
</p>