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

