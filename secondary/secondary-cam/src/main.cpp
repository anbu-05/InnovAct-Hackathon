// SecondaryESP_CAM_StreamToPrimary.ino
#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include "esp_wifi.h"

// camera model - AI_THINKER pinout used here; change if different board
#define CAMERA_MODEL_AI_THINKER
#include "esp_camera.h"

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// primary AP (softAP) info
const char* AP_SSID = "ESP32_PRIMARY_AP";
const char* AP_PASS = "esp32pass";
const char* PRIMARY_IP = "192.168.4.1"; // primary softAP default
const uint16_t PRIMARY_PORT = 8000;

// manual MAC for secondary
uint8_t SECONDARY_MAC[] = {0x02,0x66,0x77,0x88,0x99,0xAA};

WiFiClient client;

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed 0x%x\n", err);
    while (true) delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  esp_wifi_set_mode(WIFI_MODE_STA);
  esp_wifi_set_mac(WIFI_IF_STA, SECONDARY_MAC);

  setupCamera();

  WiFi.begin(AP_SSID, AP_PASS);
  Serial.print("Connecting to primary AP");
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Connected to AP, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Failed to join primary AP");
  }

  // try connect to primary feed server
  if (client.connect(PRIMARY_IP, PRIMARY_PORT)) {
    Serial.println("Connected to primary feed server");
  } else {
    Serial.println("Primary feed connect failed (will retry in loop)");
  }
}

void sendFrameToPrimary(const uint8_t* data, size_t len) {
  // send 4-byte big-endian length then bytes
  uint8_t hdr[4];
  hdr[0] = (len >> 24) & 0xFF;
  hdr[1] = (len >> 16) & 0xFF;
  hdr[2] = (len >> 8) & 0xFF;
  hdr[3] = (len) & 0xFF;
  if (!client.connected()) return;
  client.write(hdr, 4);
  client.write(data, len);
  client.flush();
}

void loop() {
  if (!client.connected()) {
    client.stop();
    if (client.connect(PRIMARY_IP, PRIMARY_PORT)) {
      Serial.println("Reconnected to primary feed server");
    } else {
      // can't send frames without feed connection
      delay(500);
    }
  }

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    delay(100);
    return;
  }

  // fb may already be JPEG
  if (fb->format == PIXFORMAT_JPEG) {
    if (client.connected()) sendFrameToPrimary(fb->buf, fb->len);
  } else {
    // convert to jpeg if not already (rare with config above)
    uint8_t * jpg = NULL;
    size_t jpglen = 0;
    if (frame2jpg(fb, 80, &jpg, &jpglen)) {
      if (client.connected()) sendFrameToPrimary(jpg, jpglen);
      free(jpg);
    }
  }

  esp_camera_fb_return(fb);
  // adjust delay to tune frame-rate / bandwidth
  delay(100); // ~10 fps control
}
