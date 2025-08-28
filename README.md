# ESP8266 Shape & Area Dashboard

A Flask + OpenCV web dashboard that detects parts on a moving belt, identifies their **shape** and **area**, and controls an **ESP8266** (servo + LEDs) to sort **good** vs **bad** pieces.  
Includes a live camera stream, production counters, adjustable tolerance, and quick camera switching.

![screenshot-dashboard](docs/screenshot-dashboard.png) <!-- Replace with your screenshot path -->

---

## ✨ Features

- **Live video stream** (MJPEG) with contour overlay
- **Shape detection** (triangle, carré/square, rectangle, circle, ellipse/polygon)
- **Area calculation** (px²) and **tolerance** check (±px²)
- **Good/Bad decision** → ESP8266:
  - Bad: servo → 180°, red LED 2s, log “Bad”
  - Good: servo → 0°, green LED 2s, log “Good”
- **Counters:** Total, Good, Bad (with reset)
- **Camera switcher:** swap between camera indices (0, 1, 2, …) from the UI
- **Bootstrap UI**: clean responsive dashboard

---

## 🧱 Project Structure (suggested)

├── app_detect_dashboard.py # Main Flask app
├── requirements.txt # Python deps
├── README.md # This file
├── .gitignore
├── esp8266/
│ └── esp8266_controller.ino # Matching ESP8266 firmware (HTTP endpoints)
└── docs/
└── screenshot-dashboard.png # Add your screenshot(s)


---

## ✅ Requirements

- **Python 3.9+** (tested on Windows; works elsewhere too)
- Webcam(s) or USB camera(s)
- ESP8266 (NodeMCU, etc.) with the provided Arduino sketch
- Network access between the PC and the ESP8266

---

## 🚀 Quick Start

```bash
# 1) Create & activate a virtual env (Windows)
python -m venv .venv
.\.venv\Scripts\activate

# 2) Install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3) Run the app
python app_detect_dashboard.py