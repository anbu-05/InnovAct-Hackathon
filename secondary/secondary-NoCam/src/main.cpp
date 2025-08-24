#include <Arduino.h>
#include <WiFi.h>
#include "esp_wifi.h"

const char* AP_SSID = "ESP32_PRIMARY_AP";
const char* AP_PASS = "esp32pass";
const char* PRIMARY_IP = "192.168.4.1";
const uint16_t PRIMARY_PORT = 8000;

// manual MAC for secondary (must differ from primary)
uint8_t SECONDARY_MAC[] = {0x02, 0x66, 0x77, 0x88, 0x99, 0xAA};

WiFiClient client;

uint8_t payload[] = {0xDE, 0xAD, 0xBE, 0xEF};

void setup() {
  Serial.begin(115200);

  // set custom MAC for STA interface
  esp_wifi_set_mode(WIFI_MODE_STA);
  esp_wifi_set_mac(WIFI_IF_STA, SECONDARY_MAC);

  WiFi.begin(AP_SSID, AP_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected to AP, IP: ");
  Serial.println(WiFi.localIP());

  if (!client.connect(PRIMARY_IP, PRIMARY_PORT)) {
    Serial.println("Connect to primary failed");
  } else {
    Serial.println("Connected to primary");
  }
}

void loop() {
  if (!client.connected()) {
    client.stop();
    if (client.connect(PRIMARY_IP, PRIMARY_PORT)) {
      Serial.println("Reconnected to primary");
    } else {
      delay(1000);
      return;
    }
  }

  client.write(payload, sizeof(payload));
  client.flush();
  Serial.println("Sent payload");
  delay(5000);
}
