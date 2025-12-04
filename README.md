# Autonomous Vision Pan-Tilt Tracker (Raspberry Pi 5)



https://github.com/user-attachments/assets/3721efa2-5bd6-4499-8468-93d212292350



Real-time face and person tracking on a Raspberry Pi 5, driving a pan-tilt rig with a PCA9685 servo controller. The system uses OpenCV DNN models to detect faces first, then falls back to body detection for robust human following.

This repository contains an **educational and hobby-focused version** of the project that demonstrates:

- Vision-based tracking
- Closed-loop servo control
- A simple web-based viewer on top of a Raspberry Pi

> **Note**  
> This code does not include any firing, relay, or weapon control logic. It is intended for safe applications such as camera tracking, laser pointers, robotics demos, and human-robot interaction experiments.

---

## Features

- **Real-time tracking** on a Raspberry Pi 5 (4 GB)
- **Face-priority detection** (SSD-ResNet10) with fallback to person detection (MobileNet-SSD)
- **Smooth pan-tilt tracking** using a PCA9685 servo driver
- **Autonomous scanning** pattern when the target is lost
- **Lightweight Flask server** exposing a live MJPEG stream
- **Simple status API** (`/api/status`) for external tools

---

## Hardware Overview

The project is built around:

- **Raspberry Pi 5 (4 GB)**
- **PCA9685** 16-channel PWM driver
- **Two MG90S** servos for pan and tilt
- **Raspberry Pi Camera** (Picamera2)

> **Approximate total hardware cost:** _under 100 USD_

See [`hardware/bill_of_materials.md`](hardware/bill_of_materials.md) for details.

---

## Software Stack

- **Language:** Python 3
- **Vision:** OpenCV DNN (Caffe models for face, MobileNet-SSD for person)
- **Control:** Adafruit PCA9685 library for servo control
- **Camera:** Picamera2
- **Web server:** Flask (MJPEG streaming)
- **Platform:** Raspberry Pi OS on Raspberry Pi 5

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/pi-vision-pan-tilt-tracker.git
cd pi-vision-pan-tilt-tracker
```

### 2. Install Python dependencies

On the Raspberry Pi:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

_You may already have some of these installed via the system. The main Python packages are:_

- `opencv-python`
- `numpy`
- `flask`
- `adafruit-circuitpython-pca9685`
- `RPi.GPIO`
- `picamera2` (often installed system-wide; see distribution docs for installation)

### 3. Place the DNN model files

Download the following models and place them in `src/models` or the same folder as `tracker.py`:

- `deploy.prototxt`
- `res10_300x300_ssd_iter_140000_fp16.caffemodel`
- `MobileNetSSD_deploy.prototxt`
- `MobileNetSSD_deploy.caffemodel`

_Update paths in the config section of `tracker.py` if you store them under `src/models`._

### 4. Wire up the hardware

**Basic connections:**

- PCA9685 **SDA/SCL** → Pi SDA/SCL
- PCA9685 **VCC** → Pi 3.3V, **V+** → servo power supply _(with common ground)_
- MG90S servos on **channels 0 and 1** (pan and tilt)
- Raspberry Pi Camera connected and enabled

_See `hardware/wiring_diagram.png` (if available) and the bill of materials for reference._

### 5. Run the tracker

From the project root (with `venv` activated):

```bash
cd src
python tracker.py
```

**If everything is wired correctly:**

- The servos should center.
- The Flask server will start on port **5000**.

Open the stream in your browser:

```
http://<pi-ip-address>:5000/
```

---

## How It Works

**High-level flow:**

1. Capture frames from Picamera2 at a modest resolution (e.g., 300x225) for speed.
2. Run a face detector first (SSD-ResNet10).
3. If a face is not confidently detected, run MobileNet-SSD for person detection.
4. Pick the best bounding box and compute its center.
5. Apply proportional control to adjust pan/tilt angles, keeping the target centered.
6. When no target is detected for a while, execute a scan pattern across pan/tilt axes.
7. Draw bounding boxes and overlays, stream the result as MJPEG via Flask.

See [`docs/how_it_works.md`](docs/how_it_works.md) for a detailed explanation.

---

## Performance Notes

On a Raspberry Pi 5 (4 GB) with modest models/resolution (300x225):

- **~15–20 fps** depending on lighting/scene
- **Smooth tracking** for normal human movement
- **Acceptable latency** for demos

_More details and optimization tips: [`docs/performance_notes.md`](docs/performance_notes.md)._

---

## Safety and Use Disclaimer

> **Important**  
> This repository is **for educational and hobby robotics** purposes only.  
> It is **NOT** designed/reviewed for controlling any harmful, projectile-based, or safety-critical systems.  
> If you adapt this for more advanced or risky applications, **you are fully responsible for the design, testing, and safety of your system**.

**Suggested safe uses:**

- Camera tracking demos
- Laser pointer tracking
- Telepresence experiments
- Human-robot interaction research and demos

---

## Roadmap

Planned or potential future improvements:

- Replace legacy DNN models with lighter/faster alternatives (e.g., YuNet)
- Add configuration files for gains, tolerances, scan ranges
- Optional **WebSocket/HTTP API** for remote control/reporting
- Additional web visualization options
- Integration with Android app for stream viewing/remote modes

---

## About the Author

This project was designed and built by **Elie Hallermeier** as a full-stack robotics experiment:

- Embedded control (PWM, Pi, servos)
- Computer vision (OpenCV DNN)
- Real-time tracking
- Simple web interface for monitoring

_If you use, tweak, or extend this project, I'd love to see it! Feel free to share or open an issue._

---

## Requirements

`requirements.txt`:

```text
opencv-python
numpy
flask
adafruit-circuitpython-pca9685
RPi.GPIO
picamera2
```
