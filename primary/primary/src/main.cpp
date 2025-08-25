// PrimaryESP_RehostStream.ino
#include <WiFi.h>
#include "esp_wifi.h"
#include "esp_http_server.h"

const char* PRIMARY_AP_SSID = "ESP32_PRIMARY_AP";
const char* PRIMARY_AP_PASS = "esp32pass";

// If you want Primary to join your laptop hotspot so the laptop can reach it:
// set these to your laptop/hotspot SSID/pass (optional but recommended).
const char* LAPTOP_SSID = "Laptop";
const char* LAPTOP_PASS = "avadhani";

const uint16_t FEED_PORT = 8000; // secondary connects here and sends frames
const uint16_t HTTP_PORT = 80;

WiFiServer feedServer(FEED_PORT);
WiFiClient feedClient;

// manual MACs (unique)
uint8_t PRIMARY_AP_MAC[]  = {0x02,0x11,0x22,0x33,0x44,0x55};
uint8_t PRIMARY_STA_MAC[] = {0x02,0xAA,0xBB,0xCC,0xDD,0xEE};

// frame storage
static uint8_t * latest_frame = NULL;
static size_t latest_len = 0;
SemaphoreHandle_t frameMutex;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char _STREAM_CONTENT_TYPE[] = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char _STREAM_BOUNDARY[] = "\r\n--" PART_BOUNDARY "\r\n";
static const char _STREAM_PART[] = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static const char INDEX_HTML[] PROGMEM = R"rawliteral(
<html><head><title>Primary Stream</title></head>
<body>
<h3>Primary ESP32 Stream Rehost</h3>
<img id="camera" src="/stream" style="max-width:100%;height:auto;" />
</body></html>
)rawliteral";

static esp_err_t index_handler(httpd_req_t *req){
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, (const char*)INDEX_HTML, strlen(INDEX_HTML));
}

static esp_err_t stream_handler(httpd_req_t *req){
  esp_err_t res = ESP_OK;
  char part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  while (true) {
    // get a snapshot of latest_frame
    uint8_t * tmpbuf = NULL;
    size_t tmplen = 0;
    if (xSemaphoreTake(frameMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
      if (latest_frame && latest_len > 0) {
        tmplen = latest_len;
        tmpbuf = (uint8_t*)malloc(tmplen);
        if (tmpbuf) memcpy(tmpbuf, latest_frame, tmplen);
      }
      xSemaphoreGive(frameMutex);
    }

    if (!tmpbuf) {
      // no frame yet, wait a bit and continue
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }

    // send header
    int hlen = snprintf(part_buf, sizeof(part_buf), _STREAM_PART, (unsigned)tmplen);
    res = httpd_resp_send_chunk(req, part_buf, hlen);
    if (res != ESP_OK) { free(tmpbuf); break; }

    // send jpeg bytes
    res = httpd_resp_send_chunk(req, (const char*)tmpbuf, tmplen);
    if (res != ESP_OK) { free(tmpbuf); break; }

    // send boundary
    res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    free(tmpbuf);

    if (res != ESP_OK) break;

    // small pacing
    vTaskDelay(pdMS_TO_TICKS(10));
  }

  return res;
}

void startHTTPServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = HTTP_PORT;
  httpd_handle_t server = NULL;
  if (httpd_start(&server, &config) == ESP_OK) {
    httpd_uri_t index_uri = { .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL };
    httpd_register_uri_handler(server, &index_uri);
    httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };
    httpd_register_uri_handler(server, &stream_uri);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  frameMutex = xSemaphoreCreateMutex();

  esp_wifi_set_mode(WIFI_MODE_APSTA);
  esp_wifi_set_mac(WIFI_IF_AP, PRIMARY_AP_MAC);
  esp_wifi_set_mac(WIFI_IF_STA, PRIMARY_STA_MAC);

  WiFi.softAP(PRIMARY_AP_SSID, PRIMARY_AP_PASS);
  Serial.print("Primary softAP IP: ");
  Serial.println(WiFi.softAPIP());

  // optional: join laptop hotspot so laptop can reach Primary via STA IP
  Serial.printf("Connecting to hotspot '%s'\n", LAPTOP_SSID);
  WiFi.begin(LAPTOP_SSID, LAPTOP_PASS);
  unsigned long t0 = millis();
  while (millis() - t0 < 20000 && WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Primary STA IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Primary STA not connected (will retry in loop)");
  }

  feedServer.begin();
  feedServer.setNoDelay(true);

  startHTTPServer();
  Serial.println("HTTP server started, stream available at /stream");
}

void handleFeedClient() {
  if (!feedServer.hasClient()) return;
  WiFiClient c = feedServer.available();
  if (!c) return;
  Serial.print("Feed client connected: ");
  Serial.println(c.remoteIP());

  // read frames: 4-byte big-endian length then JPEG bytes
  while (c.connected()) {
    // read 4 bytes length
    uint8_t lenb[4];
    int got = c.readBytes(lenb, 4);
    if (got != 4) break;
    uint32_t len = ((uint32_t)lenb[0] << 24) | ((uint32_t)lenb[1] << 16) | ((uint32_t)lenb[2] << 8) | (uint32_t)lenb[3];
    if (len == 0 || len > 5*1024*1024) { // sanity
      Serial.printf("Bad frame length %u, closing\n", len);
      break;
    }
    uint8_t *buf = (uint8_t*)malloc(len);
    if (!buf) {
      Serial.println("malloc failed");
      break;
    }
    int r = 0;
    while (r < (int)len) {
      int rr = c.readBytes(buf + r, len - r);
      if (rr <= 0) { r = -1; break; }
      r += rr;
    }
    if (r != (int)len) { free(buf); break; }

    // store as latest_frame
    if (xSemaphoreTake(frameMutex, pdMS_TO_TICKS(200)) == pdTRUE) {
      if (latest_frame) free(latest_frame);
      latest_frame = buf;
      latest_len = len;
      xSemaphoreGive(frameMutex);
    } else {
      free(buf);
    }
  }

  Serial.println("Feed client disconnected");
  c.stop();
}

void loop() {
  // accept a feed client (only one sender expected)
  handleFeedClient();

  // keep STA alive / reconnect if necessary
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastTry = 0;
    if (millis() - lastTry > 5000) {
      lastTry = millis();
      Serial.println("STA not connected - trying WiFi.reconnect()");
      WiFi.reconnect();
    }
  }

  delay(10);
}
