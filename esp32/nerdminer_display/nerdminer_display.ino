#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <SPI.h>
#include <time.h>

#include "config.h"  // Provide WIFI_* and MINERVA_* defines

TFT_eSPI tft = TFT_eSPI();

struct ServiceItem {
  String name;
  bool is_up;
};

struct StatusState {
  String bottom_line;
  String word;
  ServiceItem services[4];
  size_t service_count = 0;
  time_t server_time = 0;
  String expr_state;
  String expr_message;
};

StatusState last_state;

const char* NTP_SERVER = "pool.ntp.org";
const int   JSON_BUF_SIZE = 4096;
unsigned long last_poll = 0;
const unsigned long POLL_INTERVAL_MS = 45000; // ~45 seconds

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  if (MINERVA_DEBUG) Serial.printf("Connecting to WiFi SSID: %s\n", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    if (MINERVA_DEBUG) Serial.print(".");
  }
  if (MINERVA_DEBUG) {
    Serial.printf("\nWiFi connected, IP: %s\n", WiFi.localIP().toString().c_str());
  }
}

void syncTime() {
  configTime(TIMEZONE_OFFSET_SECONDS, 0, NTP_SERVER);
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 5000)) {
    if (MINERVA_DEBUG) Serial.println("Failed to obtain time");
  } else {
    if (MINERVA_DEBUG) {
      Serial.printf("Time synced: %04d-%02d-%02d %02d:%02d:%02d\n",
                    timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                    timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    }
  }
}

String formatTwo(int v) {
  if (v < 10) return "0" + String(v);
  return String(v);
}

void drawScreen(const StatusState& state, bool offline = false) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);

  // Top: time/date
  struct tm timeinfo;
  if (state.server_time != 0) {
    time_t now = state.server_time + (time(nullptr) - state.server_time); // approx drift correction
    localtime_r(&now, &timeinfo);
    String timestr = formatTwo(timeinfo.tm_hour) + ":" + formatTwo(timeinfo.tm_min);
    String datestr = formatTwo(timeinfo.tm_mday) + "/" + formatTwo(timeinfo.tm_mon + 1);
    tft.drawString(timestr, 5, 5, 4);
    tft.drawString(datestr, 120, 5, 2);
  } else {
    tft.drawString("No time", 5, 5, 2);
  }

  // Expression icon (top-right)
  auto drawFace = [&](const String& stateName) {
    int cx = tft.width() - 20;
    int cy = 15;
    tft.drawCircle(cx, cy, 12, TFT_WHITE);
    if (stateName == "warning" || stateName == "error") {
      tft.drawString(":O", cx - 7, cy - 6, 2);
    } else if (stateName == "thinking") {
      tft.drawString(":|", cx - 7, cy - 6, 2);
    } else if (stateName == "happy") {
      tft.drawString(":)", cx - 7, cy - 6, 2);
    } else {
      tft.drawString("._", cx - 7, cy - 6, 2);
    }
  };
  drawFace(state.expr_state);

  // Middle: services
  int y = 40;
  size_t count = state.service_count;
  for (size_t i = 0; i < count && i < 4; i++) {
    const ServiceItem& svc = state.services[i];
    String icon = svc.is_up ? "UP" : "DN";
    uint16_t color = svc.is_up ? TFT_GREEN : TFT_RED;
    tft.setTextColor(color, TFT_BLACK);
    tft.drawString(icon, 5, y, 2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    String name = svc.name;
    int maxChars = 16;
    if ((int)name.length() > maxChars) name = name.substring(0, maxChars);
    tft.drawString(name, 35, y, 2);
    y += 20;
  }
  if (count == 0) {
    tft.drawString("No services", 5, y, 2);
    y += 20;
  }

  // Bottom: bottom_line and word
  String bottom = offline ? "API offline" : state.bottom_line;
  if ((int)bottom.length() > 22) bottom = bottom.substring(0, 22);
  tft.drawString(bottom, 5, y + 10, 2);
  String wordline = "Word: " + state.word;
  int maxWord = 22;
  if ((int)wordline.length() > maxWord) wordline = wordline.substring(0, maxWord);
  tft.drawString(wordline, 5, y + 30, 2);

  // Debug footer
  if (MINERVA_DEBUG) {
    y += 50;
    String footer1 = offline ? "IP: API offline" : ("IP: " + WiFi.localIP().toString());
    time_t now = time(nullptr);
    struct tm t;
    localtime_r(&now, &t);
    String footer2 = "Upd: " + formatTwo(t.tm_hour) + ":" + formatTwo(t.tm_min) + ":" + formatTwo(t.tm_sec);
    tft.drawString(footer1, 5, y, 2);
    tft.drawString(footer2, 5, y + 15, 2);
  }
}

bool fetchStatus(StatusState& out) {
  WiFiClient client;
  HTTPClient http;
  String url = String("http://") + MINERVA_HOST + ":" + String(MINERVA_PORT) + "/status/compact";

  if (MINERVA_DEBUG) {
    Serial.printf("HTTP GET: %s\n", url.c_str());
  }

  if (!http.begin(client, url)) {
    if (MINERVA_DEBUG) Serial.println("HTTP begin failed");
    return false;
  }

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    if (MINERVA_DEBUG) Serial.printf("HTTP error: %d\n", code);
    http.end();
    return false;
  }

  WiFiClient* stream = http.getStreamPtr();
  int len = http.getSize();
  if (MINERVA_DEBUG) Serial.printf("HTTP status: %d, length: %d\n", code, len);

  DynamicJsonDocument doc(JSON_BUF_SIZE);
  DeserializationError err = deserializeJson(doc, *stream);
  if (err) {
    if (MINERVA_DEBUG) Serial.printf("JSON error: %s\n", err.c_str());
    http.end();
    return false;
  }

  out.bottom_line = doc["bottom_line"] | "All good";
  out.word = doc["word_of_day"]["word"] | "None";
  out.expr_state = doc["expression"]["state"] | "idle";
  out.expr_message = doc["expression"]["message"] | "";

  out.service_count = 0;
  JsonArray services = doc["services"].as<JsonArray>();
  for (JsonObject svc : services) {
    if (out.service_count >= 4) break;
    out.services[out.service_count].name = String((const char*)svc["name"]);
    out.services[out.service_count].is_up = svc["is_up"] | false;
    out.service_count++;
  }

  const char* server_time = doc["server_time"];
  if (server_time) {
    // crude parse for YYYY-MM-DDTHH:MM:SS
    int year, mon, mday, hour, min, sec;
    if (sscanf(server_time, "%d-%d-%dT%d:%d:%d", &year, &mon, &mday, &hour, &min, &sec) == 6) {
      struct tm t = {};
      t.tm_year = year - 1900;
      t.tm_mon = mon - 1;
      t.tm_mday = mday;
      t.tm_hour = hour;
      t.tm_min = min;
      t.tm_sec = sec;
      out.server_time = mktime(&t);
    }
  }

  http.end();
  return true;
}

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);

  connectWiFi();
  syncTime();

  drawScreen(last_state, true);
}

void loop() {
  unsigned long now_ms = millis();
  if (now_ms - last_poll > POLL_INTERVAL_MS) {
    bool ok = fetchStatus(last_state);
    drawScreen(last_state, !ok);
    last_poll = now_ms;
  }
  delay(200);
}
