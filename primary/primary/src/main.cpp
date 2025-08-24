#include <WiFi.h>
#include "esp_wifi.h"

const char* PRIMARY_AP_SSID = "ESP32_PRIMARY_AP";
const char* PRIMARY_AP_PASS = "esp32pass";

// IMPORTANT: set this to your laptop's IPv4 (from ipconfig). Example from your output: 10.95.16.88
const char* LAPTOP_SSID = "Laptop";
const char* LAPTOP_PASS = "avadhani";
const char* LAPTOP_IP = "192.168.137.1"; // <-- replace if your laptop IP differs
const uint16_t LAPTOP_PORT = 9000;

const uint16_t SERVER_PORT = 8000; // primary's softAP server port for secondaries
const int MAX_CLIENTS = 6;

WiFiServer server(SERVER_PORT);
WiFiClient clients[MAX_CLIENTS];
WiFiClient laptopClient;

// manual MACs (must be unique)
uint8_t PRIMARY_AP_MAC[]  = {0x02, 0x11, 0x22, 0x33, 0x44, 0x55}; // softAP
uint8_t PRIMARY_STA_MAC[] = {0x02, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE}; // STA

void printWiFiStatus() {
  Serial.print("WiFi status: ");
  int s = WiFi.status();
  if (s == WL_CONNECTED) Serial.print("WL_CONNECTED");
  else if (s == WL_NO_SSID_AVAIL) Serial.print("WL_NO_SSID_AVAIL");
  else if (s == WL_CONNECT_FAILED) Serial.print("WL_CONNECT_FAILED");
  else if (s == WL_DISCONNECTED) Serial.print("WL_DISCONNECTED");
  else Serial.print(s);
  Serial.print("  SSID: ");
  Serial.print(WiFi.SSID());
  Serial.print("  IP: ");
  Serial.print(WiFi.localIP());
  Serial.print("  GW: ");
  Serial.print(WiFi.gatewayIP());
  Serial.print("  RSSI: ");
  Serial.println(WiFi.RSSI());
}

void setup() {
  Serial.begin(115200);
  delay(200);

  esp_wifi_set_mode(WIFI_MODE_APSTA);
  esp_wifi_set_mac(WIFI_IF_AP, PRIMARY_AP_MAC);
  esp_wifi_set_mac(WIFI_IF_STA, PRIMARY_STA_MAC);

  WiFi.softAP(PRIMARY_AP_SSID, PRIMARY_AP_PASS);
  Serial.print("Primary softAP IP: ");
  Serial.println(WiFi.softAPIP());

  // start server for secondaries
  server.begin();
  server.setNoDelay(true);

  // connect to laptop's WiFi (STA)
  Serial.print("Connecting to laptop AP '");
  Serial.print(LAPTOP_SSID);
  Serial.println("'");
  WiFi.begin(LAPTOP_SSID, LAPTOP_PASS);
  unsigned long start = millis();
  while (millis() - start < 20000) { // wait up to 20s for initial connect
    delay(500);
    Serial.print(".");
    if (WiFi.status() == WL_CONNECTED) break;
  }
  Serial.println();
  printWiFiStatus();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Initial STA connect failed. Will continue and keep trying in loop.");
  }
}

void tryConnectLaptop() {
  if (laptopClient && laptopClient.connected()) return;
  if (WiFi.status() != WL_CONNECTED) {
    // attempt to (re)connect to STA network
    static unsigned long lastWiFiTry = 0;
    if (millis() - lastWiFiTry > 5000) {
      lastWiFiTry = millis();
      Serial.println("STA not connected — attempting WiFi.reconnect()");
      WiFi.disconnect();
      WiFi.begin(LAPTOP_SSID, LAPTOP_PASS);
    }
    return;
  }

  Serial.print("Attempting TCP connect to laptop ");
  Serial.print(LAPTOP_IP);
  Serial.print(":");
  Serial.println(LAPTOP_PORT);

  laptopClient.stop();
  bool ok = laptopClient.connect(LAPTOP_IP, LAPTOP_PORT);
  if (ok) {
    Serial.println("Connected to laptop server");
  } else {
    Serial.println("Failed to connect to laptop server (will retry)");
  }
}

void loop() {
  // accept secondaries
  WiFiClient newClient = server.available();
  if (newClient) {
    for (int i = 0; i < MAX_CLIENTS; ++i) {
      if (!clients[i] || !clients[i].connected()) {
        clients[i] = newClient;
        Serial.print("Secondary in slot ");
        Serial.println(i);
        break;
      }
    }
  }

  tryConnectLaptop();

  // relay data from secondaries to laptop
  for (int i = 0; i < MAX_CLIENTS; ++i) {
    if (clients[i] && clients[i].connected() && clients[i].available()) {
      uint8_t buf[512];
      int len = clients[i].read(buf, sizeof(buf));
      if (len > 0) {
        if (laptopClient && laptopClient.connected()) {
          laptopClient.write(buf, len);
          laptopClient.flush();
          Serial.print("Relayed ");
          Serial.print(len);
          Serial.println(" bytes to laptop");
        } else {
          Serial.println("Laptop not connected; buffering not implemented (dropping packet)");
        }
      }
    }
    if (clients[i] && !clients[i].connected()) clients[i].stop();
  }

  // small delay so serial prints are readable
  delay(50);
}
