# NerdMiner Display Bring-up Checklist

Use this checklist to diagnose Wi-Fi, time sync, API fetch, JSON parsing, and TFT wiring issues.

1) Wi-Fi
- Fill `config.h` with your `WIFI_SSID` and `WIFI_PASS`.
- Open Serial Monitor at 115200 baud.
- Verify it prints the SSID and acquires an IP (e.g., `192.168.x.x`).

2) NTP Time
- Ensure internet/LAN access to `pool.ntp.org`.
- On boot, the sketch should print that time is synced.
- With `MINERVA_DEBUG` enabled, it prints epoch and formatted time.

3) HTTP Fetch
- Confirm `MINERVA_HOST` and `MINERVA_PORT` are reachable from ESP32.
- Watch Serial for the GET URL, HTTP status, and payload size.
- Test the endpoint in a browser: `http://<host>:<port>/status/compact`.

4) JSON Parse
- If the payload is malformed or too big, ArduinoJson will report an error.
- Serial output shows the JSON error string when `MINERVA_DEBUG` is enabled.

5) Display Wiring
- Check TFT backlight pin (often tied to 3.3V or controlled via a GPIO).
- SPI pins: verify SCK/MOSI/MISO/CS/DC/RESET wiring matches your `User_Setup.h`.
- Run a TFT_eSPI example (e.g., `TFT_graphicstest`) to confirm wiring before using this sketch.

Common Failure Modes
- Stuck on Wi-Fi connect: SSID/PASS wrong or 2.4GHz disabled.
- NTP not syncing: network blocks NTP or wrong time zone offset.
- HTTP 0 / connection errors: wrong MINERVA_HOST/PORT or server offline.
- JSON errors: backend not returning valid JSON or payload too large (increase buffer cautiously).
- Blank screen: backlight off, wrong driver in `User_Setup.h`, or miswired SPI pins.
