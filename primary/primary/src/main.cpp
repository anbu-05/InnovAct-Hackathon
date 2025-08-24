#include <Arduino.h>
#include <WiFi.h>
#include "esp_wifi.h"

const char* AP_SSID = "ESP32_PRIMARY_AP";
const char* AP_PASS = "esp32pass";
const uint16_t SERVER_PORT = 8000;
const int MAX_CLIENTS = 6;

// manual MAC for primary (must be unique)
uint8_t PRIMARY_MAC[] = {0x02, 0x11, 0x22, 0x33, 0x44, 0x55};

WiFiServer server(SERVER_PORT);
WiFiClient clients[MAX_CLIENTS];

void setup() {
  Serial.begin(115200);

  // set custom MAC on softAP interface
  esp_wifi_set_mode(WIFI_MODE_AP);
  esp_wifi_set_mac(WIFI_IF_AP, PRIMARY_MAC);

  WiFi.softAP(AP_SSID, AP_PASS);
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());

  server.begin();
  server.setNoDelay(true);
}

void loop() {
  WiFiClient newClient = server.available();
  if (newClient) {
    for (int i = 0; i < MAX_CLIENTS; ++i) {
      if (!clients[i] || !clients[i].connected()) {
        clients[i] = newClient;
        Serial.print("Client in slot ");
        Serial.println(i);
        break;
      }
    }
  }

  for (int i = 0; i < MAX_CLIENTS; ++i) {
    if (clients[i] && clients[i].connected() && clients[i].available()) {
      uint8_t buf[256];
      int len = clients[i].read(buf, sizeof(buf));
      if (len > 0) {
        for (int j = 0; j < MAX_CLIENTS; ++j) {
          if (j == i) continue;
          if (clients[j] && clients[j].connected()) {
            clients[j].write(buf, len);
            clients[j].flush();
          }
        }
        Serial.print("Relayed ");
        Serial.print(len);
        Serial.println(" bytes");
      }
    }
    if (clients[i] && !clients[i].connected()) {
      clients[i].stop();
    }
  }
}
