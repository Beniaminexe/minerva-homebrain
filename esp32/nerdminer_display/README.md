# NerdMiner TFT Display for Minerva

This is a minimal ESP32/Arduino sketch that polls Minerva's `GET /status/compact` endpoint and renders a small dashboard on a TFT (NerdMiner-style).

## Requirements
- Board: ESP32 (e.g., DOIT ESP32 DEVKIT V1)
- Libraries (install via Arduino Library Manager):
  - `TFT_eSPI`
  - `ArduinoJson`
- Configure `TFT_eSPI` `User_Setup.h` for your TFT wiring (pins, resolution). NerdMiner variants differ; see the NerdMiner/TFT docs for your board.

## Setup
1. Copy `config.example.h` to `config.h` (this file is gitignored) and set:
   - `WIFI_SSID`, `WIFI_PASS`
   - `MINERVA_HOST`, `MINERVA_PORT`
   - `TIMEZONE_OFFSET_SECONDS` (e.g., `0` for UTC, `3600` for UTC+1)
2. Open `nerdminer_display.ino` in Arduino IDE.
3. Select your ESP32 board and correct COM port.
4. Upload the sketch.

## What it does
- Connects to Wi‑Fi and syncs time via NTP (`pool.ntp.org`).
- Polls `http://<MINERVA_HOST>:<PORT>/status/compact` every ~45s.
- Shows:
  - Top: local time + date
  - Middle: up to 4 services with green/red icons and truncated names
  - Bottom: bottom_line text and word of the day
- If the API fetch fails, it shows "API offline" and keeps the last known data.

## Testing locally
- Start the backend: `uvicorn backend.app.main:app --reload`
- Hit `http://localhost:8000/status/compact` in a browser to verify JSON before flashing the ESP32.
