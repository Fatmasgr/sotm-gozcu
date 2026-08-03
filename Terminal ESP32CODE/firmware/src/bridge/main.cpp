#include <Arduino.h>
#include <WiFi.h>

#include "sotm_config.h"

namespace {
HardwareSerial &controller_uart = Serial2;
WiFiServer server(sotm::kTcpPort);
WiFiClient client;

void startAccessPoint() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  WiFi.setSleep(false);
  WiFi.softAPConfig(IPAddress(192, 168, 4, 1), IPAddress(192, 168, 4, 1),
                    IPAddress(255, 255, 255, 0));
  WiFi.softAP(sotm::kAccessPointSsid, sotm::kAccessPointPassword, 6, false, 4);
  server.begin();
  server.setNoDelay(true);
}

void acceptClient() {
  WiFiClient candidate = server.available();
  if (!candidate) {
    return;
  }
  if (client) {
    client.stop();
  }
  client = candidate;
  client.setNoDelay(true);
  client.setTimeout(0);
}

void forward(Stream &source, Print &destination) {
  uint8_t buffer[512];
  while (source.available() > 0) {
    const size_t count =
        source.readBytes(buffer, min<size_t>(source.available(), sizeof(buffer)));
    if (count == 0) {
      return;
    }
    destination.write(buffer, count);
  }
}
}  // namespace

void setup() {
  Serial.begin(sotm::kUsbBaud);
  controller_uart.begin(sotm::kBridgeUartBaud, SERIAL_8N1, 16, 17);
  startAccessPoint();
  Serial.printf("SOTM bridge AP: %s, TCP: %s:%u\n", sotm::kAccessPointSsid,
                WiFi.softAPIP().toString().c_str(), sotm::kTcpPort);
}

void loop() {
  acceptClient();
  if (client && client.connected()) {
    forward(client, controller_uart);
    forward(controller_uart, client);
  } else {
    while (controller_uart.available() > 0) {
      controller_uart.read();
    }
  }
  delay(1);
}

