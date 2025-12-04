#!/usr/bin/env python3
"""
Author: Elie Hallermeier
Pan-tilt vision tracker for Raspberry Pi (educational version)

• Prioritizes face detection (SSD-ResNet10); falls back to person detection (MobileNet-SSD)
• Drives a pan-tilt rig via PCA9685 to keep the target near the image center
• When no target is visible for a while, performs a simple scan pattern
• Exposes a live MJPEG stream at:  http://<pi-ip>:5000/

DISCLAIMER
----------
This code is provided for educational and hobby robotics purposes only.
It is NOT intended to control any harmful, projectile-based, or safety-critical
hardware. If you adapt it to drive devices that can cause damage or injury,
you are solely responsible for ensuring safe design, testing, and operation.
The author assumes no liability for any misuse or consequences arising from
the use of this software.
"""

# ─── CONFIG ─────────────────────────────────────────────────────────────

# Servo channels on PCA9685
PAN_CH, TILT_CH = 0, 1

# Mechanical limits (tune for your rig)
PAN_MIN, PAN_MAX = 20, 160
TILT_MIN, TILT_MAX = 50, 130
PAN_CENTER, TILT_CENTER = 90, 90

# Flip tilt direction if your rig is inverted
TILT_DIR = -1

# Scan behavior when nothing is detected
SCAN_RANGE_PAN, SCAN_RANGE_TILT = 40, 30
SCAN_STEP = 1
SCAN_DELAY = 0.10
SCAN_WAVES = 4

# Tracking behavior
CENTER_TOL_X, CENTER_TOL_Y = 8, 8
GAIN_PAN, GAIN_TILT = 0.05, 0.05
LOST_TIMEOUT = 2.0  # seconds since last_seen → start scanning

# Camera resolution (kept modest for speed)
CAM_W, CAM_H = 300, 225

# Face detector (OpenCV DNN Caffe model)
FACE_PROTO = "deploy.prototxt"
FACE_MODEL = "res10_300x300_ssd_iter_140000_fp16.caffemodel"
FACE_CONF = 0.5
MIN_FACE_PIX = 225  # ~20×20 px
FACE_HOLD_SEC = 0.1  # keep face mode this long after loss

# Person detector (MobileNet-SSD)
PERSON_PROTO = "MobileNetSSD_deploy.prototxt"
PERSON_MODEL = "MobileNetSSD_deploy.caffemodel"
PERSON_CLASS = 15  # "person" class index
PERSON_CONF = 0.5
MIN_BODY_FRAC = 0.02  # discard <2% of frame area

# ────────────────────────────────────────────────────────────────────────

import math
import time
from pathlib import Path

import cv2
import numpy as np
import board
import busio
from picamera2 import Picamera2
from adafruit_pca9685 import PCA9685
from flask import Flask, Response, render_template_string, jsonify

# ─── Servo setup ───────────────────────────────────────────────────────

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50


def set_angle(ch: int, ang: float) -> None:
    """Clamp angle to [0, 180] and send to PCA9685."""
    ang = max(0.0, min(180.0, ang))
    pulse_us = 500.0 + (ang / 180.0) * 1900.0  # ~500-2400 µs
    duty = int(pulse_us * 65535.0 / 20000.0)
    pca.channels[ch].duty_cycle = duty


pan, tilt = PAN_CENTER, TILT_CENTER
set_angle(PAN_CH, pan)
set_angle(TILT_CH, tilt)

# ─── Camera ────────────────────────────────────────────────────────────

picam2 = Picamera2()
picam2.configure(
    picam2.create_video_configuration(
        main={"size": (CAM_W, CAM_H), "format": "RGB888"},
        buffer_count=1,
    )
)
picam2.start()
time.sleep(2.0)

CX, CY = CAM_W // 2, CAM_H // 2  # image center

# ─── Load DNNs ─────────────────────────────────────────────────────────

for f in (FACE_PROTO, FACE_MODEL, PERSON_PROTO, PERSON_MODEL):
    if not Path(f).exists():
        raise FileNotFoundError(f"Missing model file: {f}")

net_face = cv2.dnn.readNetFromCaffe(FACE_PROTO, FACE_MODEL)
net_person = cv2.dnn.readNetFromCaffe(PERSON_PROTO, PERSON_MODEL)

for net in (net_face, net_person):
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# ─── Flask UI ──────────────────────────────────────────────────────────

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
  <title>Pi Tracker</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    html, body {
      margin: 0;
      padding: 0;
      height: 100%;
      width: 100%;
      background: #000;
      overflow: hidden;
    }
    img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  </style>
</head>
<body>
  <img src="{{ url_for('video_feed') }}" alt="Video stream">
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/ping")
def api_ping():
    return jsonify(ok=True)


@app.route("/api/status")
def api_status():
    """Lightweight status endpoint for external tools."""
    return jsonify(
        last_conf=last_conf,
        tracking_mode=tracking_mode,
        last_seen=last_seen,
    )


# ─── Runtime state ─────────────────────────────────────────────────────

scan_dir = 1
last_seen = 0.0

last_face_time = 0.0
last_face_box = None

last_conf = 0.0
last_fx, last_fy = CX, CY

tracking_mode = "none"  # "face", "body", or "none"


# ─── Stream generator ──────────────────────────────────────────────────

def gen_frames():
    global pan, tilt, scan_dir, last_seen
    global last_face_time, last_face_box
    global last_conf, last_fx, last_fy, tracking_mode

    while True:
        t0 = time.perf_counter()
        try:
            frame = picam2.capture_array()
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] capture_array failed: {exc}")
            time.sleep(0.5)
            continue

        # ---- 1) FACE detection ---------------------------------------
        blob_f = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1.0,
            size=(300, 300),
            mean=(104.0, 177.0, 123.0),
        )
        net_face.setInput(blob_f)
        det_f = net_face.forward()

        best_face, best_fconf = None, 0.0
        for i in range(det_f.shape[2]):
            conf = float(det_f[0, 0, i, 2])
            if conf < FACE_CONF:
                continue
            x1, y1, x2, y2 = (
                det_f[0, 0, i, 3:7]
                * np.array([CAM_W, CAM_H, CAM_W, CAM_H])
            ).astype(int)
            if (x2 - x1) * (y2 - y1) < MIN_FACE_PIX:
                continue
            if conf > best_fconf:
                best_face, best_fconf = (x1, y1, x2, y2), conf

        if best_face is not None:
            last_face_box = best_face
            last_face_time = time.time()

        # Use a recently seen face if available
        use_face = (
            (time.time() - last_face_time) < FACE_HOLD_SEC
            and last_face_box is not None
        )
        tracking_mode = "face" if use_face else "none"
        best_box, best_conf = (
            (last_face_box, best_fconf) if use_face else (None, 0.0)
        )

        # ---- 2) BODY detection if no face ----------------------------
        if tracking_mode == "none":
            blob_p = cv2.dnn.blobFromImage(
                frame,
                scalefactor=0.007843,
                size=(300, 300),
                mean=127.5,
            )
            net_person.setInput(blob_p)
            det_p = net_person.forward()

            for i in range(det_p.shape[2]):
                conf = float(det_p[0, 0, i, 2])
                cls = int(det_p[0, 0, i, 1])
                if conf < PERSON_CONF or cls != PERSON_CLASS:
                    continue
                x1, y1, x2, y2 = (
                    det_p[0, 0, i, 3:7]
                    * np.array([CAM_W, CAM_H, CAM_W, CAM_H])
                ).astype(int)
                if (x2 - x1) * (y2 - y1) < MIN_BODY_FRAC * CAM_W * CAM_H:
                    continue
                if conf > best_conf:
                    best_box, best_conf = (x1, y1, x2, y2), conf

            if best_box is not None:
                tracking_mode = "body"

        detected = best_box is not None

        # ---- Track or scan -------------------------------------------
        if detected:
            x1, y1, x2, y2 = best_box
            fx, fy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Servo adjust
            err_x = fx - CX
            if abs(err_x) > CENTER_TOL_X:
                pan -= err_x * GAIN_PAN
                pan = max(PAN_MIN, min(PAN_MAX, pan))
                set_angle(PAN_CH, pan)

            err_y = fy - CY
            if abs(err_y) > CENTER_TOL_Y:
                tilt += TILT_DIR * err_y * GAIN_TILT
                tilt = max(TILT_MIN, min(TILT_MAX, tilt))
                set_angle(TILT_CH, tilt)

            last_seen = time.time()
            last_conf = best_conf
            last_fx, last_fy = fx, fy
        else:
            # No target → maybe scan
            now = time.time()
            if now - last_seen > LOST_TIMEOUT:
                pan += SCAN_STEP * scan_dir
                if pan > PAN_MAX or pan < PAN_MIN:
                    scan_dir *= -1
                    pan += SCAN_STEP * scan_dir

                t_norm = (pan - PAN_CENTER) / SCAN_RANGE_PAN
                tilt = (
                    TILT_CENTER
                    + SCAN_RANGE_TILT * math.sin(math.pi * SCAN_WAVES * t_norm)
                )
                tilt = max(TILT_MIN, min(TILT_MAX, tilt))

                set_angle(PAN_CH, pan)
                set_angle(TILT_CH, tilt)
                time.sleep(SCAN_DELAY)

        # ---- Overlay text & HUD --------------------------------------
        fps = 1.0 / (time.perf_counter() - t0 + 1e-9)
        cv2.putText(
            frame,
            f"{fps:4.1f} fps",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"Conf: {last_conf:.2f}",
            (5, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )
        cv2.putText(
            frame,
            f"Pos: ({last_fx},{last_fy})",
            (5, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"Mode: {tracking_mode}",
            (5, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
        )

        # Simple status text
        if detected:
            status = "Tracking"
        elif time.time() - last_seen < LOST_TIMEOUT:
            status = "Target lost (hold)"
        else:
            status = "Scanning"

        cv2.putText(
            frame,
            status,
            (5, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

        # Crosshair at last known target position
        cx, cy = last_fx, last_fy
        size, th = 20, 2
        cv2.line(frame, (cx - size, cy), (cx - 5, cy), (0, 255, 0), th)
        cv2.line(frame, (cx + 5, cy), (cx + size, cy), (0, 255, 0), th)
        cv2.line(frame, (cx, cy - size), (cx, cy - 5), (0, 255, 0), th)
        cv2.line(frame, (cx, cy + 5), (cx, cy + size), (0, 255, 0), th)
        cv2.circle(frame, (cx, cy), 8, (0, 255, 0), 1)

        # Encode JPEG and yield as MJPEG frame
        ret, jpeg = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg.tobytes()
            + b"\r\n"
        )


@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ─── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            threaded=True,
            use_reloader=False,
        )
    finally:
        # Graceful shutdown
        for ch in (PAN_CH, TILT_CH):
            pca.channels[ch].duty_cycle = 0
        pca.deinit()
        picam2.close()
        print("Clean shutdown.")
