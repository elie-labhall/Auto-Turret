# Autonomous Vision Pan-Tilt Tracker (Raspberry Pi 5)

Real-time face and person tracking on a Raspberry Pi 5, driving a pan-tilt rig with a PCA9685 servo controller. The system uses OpenCV DNN models to detect faces first, then falls back to body detection, and keeps the target near the center of the frame. A Flask server provides a live MJPEG stream that can be viewed from any browser on the local network.

This repository contains an **educational and hobby-focused version** of the project that demonstrates:

- Vision-based tracking
- Closed-loop servo control
- A simple web-based viewer on top of a Raspberry Pi

> **Note**  
> This code does not include any firing, relay, or weapon control logic. It is intended for safe applications such as camera tracking, laser pointers, robotics demos, and human-robot interaction experiments.

---

## Features

- Real-time tracking on a Raspberry Pi 5 (4 GB)
- Face-priority detection (SSD-ResNet10) with fallback to person detection (MobileNet-SSD)
- Smooth pan-tilt tracking using a PCA9685 servo driver
- Autonomous scanning pattern when the target is lost
- Lightweight Flask server exposing a live MJPEG stream
- Simple status API (`/api/status`) for external tools

---

## Hardware Overview

The project is built around:

- **Raspberry Pi 5 (4 GB)**
- **PCA9685** 16-channel PWM driver
- **Two MG90S** servos for pan and tilt
- **Raspberry Pi Camera** (Picamera2)

Approximate total hardware cost: **under 100 USD**.

See `hardware/bill_of_materials.md` for details.

---

## Software Stack

- **Language:** Python 3
- **Vision:** OpenCV DNN (Caffe models for face and MobileNet-SSD for person)
- **Control:** Adafruit PCA9685 library for servo control
- **Camera:** Picamera2
- **Web server:** Flask (MJPEG streaming)
- **Platform:** Raspberry Pi OS on Raspberry Pi 5

---

## Getting Started

### 1. Clone the repo

bash:

git clone https://github.com/<your-username>/pi-vision-pan-tilt-tracker.git
cd pi-vision-pan-tilt-tracker

2. Install Python dependencies
On the Pi:

bash
Copy code
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
You may already have some of these installed via the system. The main Python packages are:

opencv-python

numpy

flask

adafruit-circuitpython-pca9685

RPi.GPIO

picamera2 (often installed via system packages)

See your distribution docs for Picamera2 installation if needed.

3. Place the DNN model files
Download the following models and place them in src/models or the same folder as tracker.py:

deploy.prototxt

res10_300x300_ssd_iter_140000_fp16.caffemodel

MobileNetSSD_deploy.prototxt

MobileNetSSD_deploy.caffemodel

Update paths in the config section of tracker.py if you store them under src/models.

4. Wire up the hardware
Basic connections:

PCA9685 SDA/SCL to Raspberry Pi SDA/SCL

PCA9685 VCC to 3.3 V, V+ to servo power supply (with common ground)

MG90S servos on channels 0 and 1 for pan and tilt

Raspberry Pi Camera connected and enabled

See hardware/wiring_diagram.png (if you add it) and the bill of materials for reference.

5. Run the tracker
From the project root (with venv activated):

bash
Copy code
cd src
python tracker.py
If everything is wired correctly:

The servos should center.

The Flask server will start on port 5000.

You can open the stream in a browser:

text
Copy code
http://<pi-ip-address>:5000/
How It Works
High-level flow:

Capture frames from Picamera2 at a modest resolution (300x225) for speed.

Run a face detector first (SSD-ResNet10).

If a face is not confidently detected, run a MobileNet-SSD person detector.

Pick the best bounding box and compute its center.

Apply proportional control to pan and tilt angles to keep the target near the image center.

When no target is detected for a while, run a scan pattern across pan and tilt angles.

Draw the bounding box and HUD overlays and stream the result as MJPEG via Flask.

See docs/how_it_works.md for a more detailed explanation.

Performance Notes
On a Raspberry Pi 5 (4 GB) with modest models and a resolution of 300x225, the system reaches:

Around 15 to 20 fps depending on lighting and scene complexity

Smooth tracking for normal human movement

Acceptable latency for interactive demos

More details and optimization notes are in docs/performance_notes.md.

Safety and Use Disclaimer
Important
This repository is intended for educational and hobby robotics purposes only.
It is not designed or reviewed for controlling any harmful, projectile-based, or safety-critical systems.
If you adapt this project for more advanced or risky applications, you are fully responsible for the design, testing, and safety of your system.

Suggested safe uses:

Camera tracking demos

Laser pointer tracking

Telepresence experiments

Human-robot interaction research and demos

Roadmap
Planned or potential future improvements (some of which are not in this open-source version):

Replace older DNN models with lighter, faster ones (for example YuNet or a smaller person detector)

Add proper configuration files for gains, tolerances, and scan ranges

Optional WebSocket or HTTP API for remote control and status

Additional visualization options in the web interface

Optional integration with an Android app for viewing the stream and controlling modes

About the Author
This project was designed and built by Elie Hallermeier as a full-stack robotics experiment:

Embedded control (PWM, Pi, servos)

Computer vision (OpenCV DNN)

Real-time tracking

Simple web interface for monitoring

If you use this project, tweak it, or build something on top of it, feel free to share it or open an issue. I would be happy to see what you build.

yaml
Copy code

---

## 3. `requirements.txt`

```text
opencv-python
numpy
flask
adafruit-circuitpython-pca9685
RPi.GPIO
picamera2
If picamera2 is managed by the system on your Pi, you can add a note in the README saying it may not be installable via pip on all platforms.
