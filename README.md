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
python app_detect_dashboard.py.

🧭 Using the Dashboard

Expected Parameters panel:

Set Expected Shape, Expected Area (px²), and Tolerance (±px²), then Save

Camera Index: enter 0 for built-in, 1/2 for USB cams → click Switch

Production Stats: live counters for Total / Good / Bad; Reset to clear

Last result badge turns green (Good) or red (Bad)

Cooldown between detections is 2 seconds by default (configurable by env var)

🔌 ESP8266 Firmware

A minimal Arduino sketch exposes HTTP endpoints used by the Python app:

GET /servo?angle=0..180

GET /led?color=red|green&state=on|off

GET /log?msg=... → prints to Serial

Important wiring notes:

Set servo to 90° in setup() (neutral start position).

Power the servo from a proper 5V supply, not from the 3.3V pin (common GND with ESP).

Use resistors (220–330Ω) for LEDs.

Place your sketch in esp8266/esp8266_controller.ino.
(If you want, include the full code in this repo so others can flash it easily.)

🔧 Troubleshooting

Camera not opening (Windows):

App uses cv2.CAP_DSHOW for indices. Try other indices: 0, 1, 2.

Ensure no other program is using the webcam.

Double counting: increase DETECTION_COOLDOWN_S (e.g. 2.5 or 3.0).

No contours: raise MIN_CONTOUR_AREA (e.g. 1200) or improve lighting/contrast.

ESP not reacting: confirm ESP IP matches ESP8266_BASE_URL and test in a browser:

http://<ESP-IP>/servo?angle=90

http://<ESP-IP>/led?color=red&state=on

📝 .gitignore (recommended)
# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
*.log

# OS
.DS_Store
Thumbs.db

📸 Screenshots

Add screenshots in docs/ and update references above.

Dashboard home: docs/screenshot-dashboard.png

Good piece example: docs/screenshot-good.png

Bad piece example: docs/screenshot-bad.png

📄 License

MIT (or your preferred license).

🙌 Credits

OpenCV for image processing

Flask for the web app

Bootstrap for styling

ESP8266 for control I/O