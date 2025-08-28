#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cv2
import time
import math
import threading
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from flask import Flask, Response, render_template_string, request, redirect, url_for, jsonify

app = Flask(__name__)

# ----------------------- Configuration -----------------------
ESP8266_BASE_URL = os.environ.get("ESP8266_BASE_URL", "http://192.168.100.15")  # Change to your ESP8266 IP

# Camera index (int) or a path to a video file (str). If you pass an int, on Windows we use CAP_DSHOW.
CAMERA_SOURCE_ENV = os.environ.get("CAMERA_INDEX", "0")
DEFAULT_CAMERA_SOURCE = int(CAMERA_SOURCE_ENV) if CAMERA_SOURCE_ENV.isdigit() else CAMERA_SOURCE_ENV

MIN_CONTOUR_AREA = float(os.environ.get("MIN_CONTOUR_AREA", "500"))
DETECTION_COOLDOWN_S = float(os.environ.get("DETECTION_COOLDOWN_S", "2.0"))  # ✅ 2 seconds to avoid double-counts

# ----------------------- Shared state -----------------------
state_lock = threading.Lock()
shared = {
    "expected_shape": "Rectangle",
    "expected_area": 1000.0,
    "tolerance": 300.0,          # ±px² tolerance
    "camera_source": DEFAULT_CAMERA_SOURCE,  # ✅ track current camera (int or str)
    "last_shape": "N/A",
    "last_area": 0.0,
    "last_result": "N/A",        # "Good" or "Bad"
    "count_total": 0,
    "count_good": 0,
    "count_bad": 0,
    "last_detection_ts": 0.0,
}

# Shapes for dropdown
SHAPES = ["Triangle", "Carre", "Rectangle", "Cercle", "Ellipse/Polygone"]


# ----------------------- Shape detection -----------------------
def detect_shape(contour):
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

    if len(approx) == 3:
        return "Triangle"

    if len(approx) == 4:
        (x, y, w, h) = cv2.boundingRect(approx)
        ar = w / float(h) if h != 0 else 0
        return "Carre" if 0.95 <= ar <= 1.05 else "Rectangle"

    if len(approx) > 4:
        area = cv2.contourArea(contour)
        if area <= 0:
            return "Inconnu"
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return "Inconnu"
        circularity = 4 * math.pi * (area / (perimeter * perimeter))
        return "Cercle" if circularity > 0.75 else "Ellipse/Polygone"

    return "Inconnu"


# ----------------------- ESP8266 helpers -----------------------
def esp_get(path, params=None, timeout=3):
    """Call ESP8266 HTTP endpoint like /servo?angle=90"""
    try:
        url = ESP8266_BASE_URL.rstrip("/") + path
        if params:
            url += "?" + urlencode(params)
        req = Request(url, headers={"User-Agent": "shape-dashboard/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (URLError, HTTPError) as e:
        return f"ERR:{e}"


def action_bad_piece():
    esp_get("/servo", {"angle": 180})
    esp_get("/led", {"color": "red", "state": "on"})
    esp_get("/log", {"msg": "Piece rebu ou bruler detecter"})
    time.sleep(2)
    esp_get("/led", {"color": "red", "state": "off"})


def action_good_piece():
    esp_get("/servo", {"angle": 0})
    esp_get("/led", {"color": "green", "state": "on"})
    esp_get("/log", {"msg": "Piece Bonne detecter"})
    time.sleep(2)
    esp_get("/led", {"color": "green", "state": "off"})


# ----------------------- Video capture thread -----------------------
class CameraWorker:
    def __init__(self, src):
        # Use CAP_DSHOW for Windows webcams if src is index
        if isinstance(src, int):
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(src)

        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera source: {src}")
        self.frame = None
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            self.frame = frame

    def read(self):
        return self.frame

    def stop(self):
        self.running = False
        self.thread.join(timeout=1.0)
        try:
            self.cap.release()
        except Exception:
            pass


camera = None

def switch_camera(new_source):
    """Hot-swap the camera safely. Returns True if switched, False if failed."""
    global camera
    try:
        # Try to instantiate a new camera first
        test_worker = CameraWorker(new_source)
    except Exception as e:
        print(f"[camera] Switch failed for {new_source}: {e}")
        return False

    # Swap under lock
    with state_lock:
        old = camera
        camera = test_worker
        shared["camera_source"] = new_source

    # Stop old outside lock
    if old is not None:
        try:
            old.stop()
        except Exception:
            pass

    print(f"[camera] Switched to {new_source}")
    return True


def process_frame(frame):
    """Return (annotated_frame, decision or None if no new piece)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    annotated = frame.copy()
    selected = None
    selected_area = 0

    # pick largest contour above threshold
    for c in contours:
        area = cv2.contourArea(c)
        if area >= MIN_CONTOUR_AREA and area > selected_area:
            selected = c
            selected_area = area

    decision = None
    if selected is not None:
        shape = detect_shape(selected)
        M = cv2.moments(selected)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            cX, cY = 10, 10

        cv2.drawContours(annotated, [selected], -1, (0, 255, 0), 2)

        now = time.monotonic()
        with state_lock:
            cooldown_ok = (now - shared["last_detection_ts"]) >= DETECTION_COOLDOWN_S

        if cooldown_ok:
            # compare vs expected and update counters atomically
            with state_lock:
                exp_shape = shared["expected_shape"]
                exp_area = float(shared["expected_area"])
                tol = float(shared["tolerance"])
                area_diff = abs(selected_area - exp_area)
                is_bad = (shape != exp_shape) or (area_diff > tol)

                shared["last_shape"] = shape
                shared["last_area"] = float(selected_area)
                shared["last_detection_ts"] = now

                shared["count_total"] += 1
                if is_bad:
                    shared["last_result"] = "Bad"
                    shared["count_bad"] += 1
                else:
                    shared["last_result"] = "Good"
                    shared["count_good"] += 1

                decision = shared["last_result"]

            # fire servo/LED action in background
            threading.Thread(
                target=action_bad_piece if decision == "Bad" else action_good_piece,
                daemon=True,
            ).start()

        label = f"{shape} | Area: {int(selected_area)} px^2"
        cv2.putText(
            annotated,
            label,
            (max(cX - 80, 10), max(cY - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

    return annotated, decision


# ----------------------- Flask page -----------------------
PAGE = """
<!doctype html>
<html lang="en" data-bs-theme="light">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Shape & Area Dashboard</title>
  <!-- Bootstrap CSS -->
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    rel="stylesheet"
    integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
    crossorigin="anonymous">
  <style>
    .video { width: 100%; border-radius: .5rem; }
    .stat-label { color:#6c757d; font-size:.9rem; }
    .stat-value { font-weight:600; font-size:1.1rem; }
    .badge-good { background-color:#198754; }
    .badge-bad { background-color:#dc3545; }
    .kpi { font-size: 2rem; font-weight: 700; }
    .card-elev { box-shadow: 0 4px 16px rgba(0,0,0,.06); border:0; }
  </style>
</head>
<body class="bg-light">
  <!-- Topbar -->
  <nav class="navbar navbar-expand-lg bg-white border-bottom">
    <div class="container-fluid">
      <span class="navbar-brand d-flex align-items-center gap-2">
        <span class="badge text-bg-primary rounded-pill">Live</span>
        Shape & Area Dashboard
      </span>
      <div class="ms-auto d-flex align-items-center gap-2">
        <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('video_feed') }}" target="_blank">
          Open stream
        </a>
      </div>
    </div>
  </nav>

  <div class="container py-4">

    <div class="row g-4">
      <!-- Live Stream + Stats -->
      <div class="col-12 col-lg-7">
        <div class="card card-elev">
          <div class="card-header bg-white">
            <h5 class="mb-0">Camera Stream</h5>
          </div>
          <div class="card-body">
            <img class="video border" src="{{ url_for('video_feed') }}" alt="live stream"/>
            <div class="row mt-3">
              <div class="col-12 col-md-4">
                <div class="stat-label">Last shape</div>
                <div class="stat-value" id="last_shape">N/A</div>
              </div>
              <div class="col-12 col-md-4">
                <div class="stat-label">Last area</div>
                <div class="stat-value"><span id="last_area">0</span> px²</div>
              </div>
              <div class="col-12 col-md-4">
                <div class="stat-label">Last result</div>
                <div class="mt-1">
                  <span id="last_result" class="badge rounded-pill text-bg-secondary">N/A</span>
                </div>
              </div>
            </div>
          </div>
          <div class="card-footer bg-white">
            <small class="text-muted">
              Tip: Press <kbd>q</kbd> in the OpenCV window to quit (if you run headless, ignore).
            </small>
          </div>
        </div>
      </div>

      <!-- Controls + KPIs -->
      <div class="col-12 col-lg-5">
        <div class="card card-elev mb-4">
          <div class="card-header bg-white d-flex align-items-center justify-content-between">
            <h5 class="mb-0">Expected Parameters</h5>
          </div>
          <div class="card-body">
            <form class="row gy-3" method="POST" action="{{ url_for('config') }}">
              <div class="col-12">
                <label class="form-label">Expected Shape</label>
                <select class="form-select" name="expected_shape">
                  {% for s in shapes %}
                    <option value="{{s}}" {% if s == expected_shape %}selected{% endif %}>{{s}}</option>
                  {% endfor %}
                </select>
              </div>
              <div class="col-12">
                <label class="form-label">Expected Area (px²)</label>
                <div class="input-group">
                  <input type="number" class="form-control" name="expected_area" step="1" value="{{ expected_area }}" required/>
                  <span class="input-group-text">px²</span>
                </div>
              </div>
              <div class="col-12">
                <label class="form-label">Tolerance (± px²)</label>
                <div class="input-group">
                  <input type="number" class="form-control" name="tolerance" step="1" value="{{ tolerance }}" min="0" required/>
                  <span class="input-group-text">px²</span>
                </div>
                <div class="form-text">If |detected_area - expected_area| &gt; tolerance OR shape differs → Bad.</div>
              </div>
              <div class="col-12">
                <label class="form-label">Camera Index</label>
                <div class="input-group">
                  <input type="number" class="form-control" name="camera_index" step="1" min="0" value="{{ camera_index }}" />
                  <button class="btn btn-outline-primary" type="submit" name="action" value="switch_camera">Switch</button>
                </div>
                <div class="form-text">Current camera: <code>{{ camera_index }}</code>. Use 0 for built-in, 1/2 for USB cams.</div>
              </div>
              <div class="col-12 d-flex gap-2">
                <button type="submit" class="btn btn-primary" name="action" value="save_params">
                  <i class="bi bi-save me-1"></i> Save
                </button>
                <a href="/" class="btn btn-outline-secondary">Refresh</a>
              </div>
            </form>
          </div>
        </div>

        <div class="card card-elev">
          <div class="card-header bg-white">
            <h5 class="mb-0">Production Stats</h5>
          </div>
          <div class="card-body">
            <div class="row text-center">
              <div class="col-4">
                <div class="text-muted">Total</div>
                <div class="kpi"><span id="count_total">{{ count_total }}</span></div>
              </div>
              <div class="col-4">
                <div class="text-success">Good</div>
                <div class="kpi"><span id="count_good">0</span></div>
              </div>
              <div class="col-4">
                <div class="text-danger">Bad</div>
                <div class="kpi"><span id="count_bad">0</span></div>
              </div>
            </div>
          </div>
          <div class="card-footer bg-white text-center">
            <form method="POST" action="{{ url_for('reset_counter') }}">
              <button type="submit" class="btn btn-danger btn-sm">Reset all counters</button>
            </form>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Bootstrap JS -->
  <script
    src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
    integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
    crossorigin="anonymous"></script>

  <!-- Bootstrap Icons -->
  <link
    rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"/>

  <script>
    function setResultBadge(el, value){
      el.textContent = value;
      el.className = "badge rounded-pill";
      if(value === "Good"){ el.classList.add("badge-good","text-white"); }
      else if(value === "Bad"){ el.classList.add("badge-bad","text-white"); }
      else { el.classList.add("text-bg-secondary"); }
    }

    async function refreshStatus(){
      try{
        const r = await fetch("{{ url_for('status') }}");
        const data = await r.json();
        document.getElementById("last_shape").textContent = data.last_shape;
        document.getElementById("last_area").textContent = Math.round(data.last_area);
        setResultBadge(document.getElementById("last_result"), data.last_result);
        document.getElementById("count_total").textContent = data.count_total;
        document.getElementById("count_good").textContent = data.count_good;
        document.getElementById("count_bad").textContent = data.count_bad;
      }catch(e){ /* ignore */ }
    }
    setInterval(refreshStatus, 600);
    refreshStatus();
  </script>
</body>
</html>
"""


# ----------------------- Flask routes -----------------------
@app.route("/")
def index():
    with state_lock:
        # derive a numeric camera index for display; if path, show 0 by default
        cam_src = shared["camera_source"]
        cam_index_display = cam_src if isinstance(cam_src, int) else 0
        return render_template_string(
            PAGE,
            shapes=SHAPES,
            expected_shape=shared["expected_shape"],
            expected_area=int(shared["expected_area"]),
            tolerance=int(shared["tolerance"]),
            count_total=shared["count_total"],
            camera_index=cam_index_display,
        )


@app.route("/config", methods=["POST"])
def config():
    action = request.form.get("action", "save_params")

    if action == "switch_camera":
        # Switch camera safely
        cam_raw = request.form.get("camera_index", "").strip()
        if cam_raw != "":
            new_src = int(cam_raw) if cam_raw.isdigit() else cam_raw
            ok = switch_camera(new_src)
            # If switch fails, we simply keep the old camera; optional: flash messages/log prints
        return redirect(url_for("index"))

    # Else: save expected params
    shape = request.form.get("expected_shape", "Rectangle")
    try:
        area = float(request.form.get("expected_area", "1000"))
    except ValueError:
        area = 1000.0
    try:
        tol = float(request.form.get("tolerance", "300"))
        if tol < 0:
            tol = 0.0
    except ValueError:
        tol = 300.0

    with state_lock:
        shared["expected_shape"] = shape
        shared["expected_area"] = area
        shared["tolerance"] = tol
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset_counter():
    with state_lock:
        shared["count_total"] = 0
        shared["count_good"] = 0
        shared["count_bad"] = 0
    return redirect(url_for("index"))


@app.route("/status")
def status():
    with state_lock:
        # Report current camera index if it's an int; else 0 (for a path)
        cam_src = shared["camera_source"]
        cam_index = cam_src if isinstance(cam_src, int) else 0
        return jsonify(
            last_shape=shared["last_shape"],
            last_area=shared["last_area"],
            last_result=shared["last_result"],
            count_total=shared["count_total"],
            count_good=shared["count_good"],
            count_bad=shared["count_bad"],
            expected_shape=shared["expected_shape"],
            expected_area=shared["expected_area"],
            tolerance=shared["tolerance"],
            camera_index=cam_index,
        )


def mjpeg_generator():
    while True:
        if camera is None:
            time.sleep(0.01)
            continue
        frame = camera.read()
        if frame is None:
            time.sleep(0.005)
            continue
        annotated, _ = process_frame(frame)

        ret, jpg = cv2.imencode(".jpg", annotated)
        if not ret:
            continue
        b = jpg.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + b + b"\r\n")


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


def main():
    global camera
    # Start initial camera
    camera = CameraWorker(shared["camera_source"])
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        if camera:
            camera.stop()


if __name__ == "__main__":
    main()
