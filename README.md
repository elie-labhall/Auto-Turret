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

```bash
git clone https://github.com/<your-username>/pi-vision-pan-tilt-tracker.git
cd pi-vision-pan-tilt-tracker
