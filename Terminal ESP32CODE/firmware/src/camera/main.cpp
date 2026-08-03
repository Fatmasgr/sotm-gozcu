#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_http_server.h>
#include <ESPmDNS.h>
#include <img_converters.h>

#include "sotm_config.h"

namespace {
// AI-Thinker ESP32-CAM pin eşlemesi.
constexpr int kPwmChannel = 0;
constexpr int kPwmTimer = 0;
constexpr int kPwdn = 32;
constexpr int kReset = -1;
constexpr int kXclk = 0;
constexpr int kSiod = 26;
constexpr int kSioc = 27;
constexpr int kY9 = 35;
constexpr int kY8 = 34;
constexpr int kY7 = 39;
constexpr int kY6 = 36;
constexpr int kY5 = 21;
constexpr int kY4 = 19;
constexpr int kY3 = 18;
constexpr int kY2 = 5;
constexpr int kVsync = 25;
constexpr int kHref = 23;
constexpr int kPclk = 22;

httpd_handle_t stream_server = nullptr;
constexpr char kBoundary[] = "\r\n--sotmframe\r\n";

esp_err_t statusHandler(httpd_req_t *request) {
  const String json =
      String("{\"device\":\"ESP32-CAM\",\"ok\":true,\"ip\":\"") +
      WiFi.localIP().toString() + "\",\"stream\":\"http://" +
      sotm::kCameraHostname + ".local:81/stream\"}";
  httpd_resp_set_type(request, "application/json");
  httpd_resp_set_hdr(request, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(request, json.c_str(), json.length());
}

esp_err_t rootHandler(httpd_req_t *request) {
  static constexpr char page[] =
      "<!doctype html><meta charset='utf-8'><title>SOTM-CAM</title>"
      "<style>body{font-family:sans-serif;background:#111;color:#eee}"
      "img{max-width:100%;height:auto}</style><h1>SOTM-Gozcu Kamera</h1>"
      "<img src='/stream'>";
  httpd_resp_set_type(request, "text/html");
  return httpd_resp_send(request, page, HTTPD_RESP_USE_STRLEN);
}

esp_err_t streamHandler(httpd_req_t *request) {
  esp_err_t result =
      httpd_resp_set_type(request, "multipart/x-mixed-replace;boundary=sotmframe");
  if (result != ESP_OK) {
    return result;
  }
  httpd_resp_set_hdr(request, "Access-Control-Allow-Origin", "*");

  while (true) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (frame == nullptr) {
      return ESP_FAIL;
    }

    uint8_t *jpeg_buffer = frame->buf;
    size_t jpeg_length = frame->len;
    bool allocated = false;
    if (frame->format != PIXFORMAT_JPEG) {
      allocated = frame2jpg(frame, 80, &jpeg_buffer, &jpeg_length);
    }

    if (!allocated && frame->format != PIXFORMAT_JPEG) {
      esp_camera_fb_return(frame);
      return ESP_FAIL;
    }

    char header[96];
    const int header_length =
        snprintf(header, sizeof(header),
                 "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                 static_cast<unsigned>(jpeg_length));
    result = httpd_resp_send_chunk(request, kBoundary, strlen(kBoundary));
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(request, header, header_length);
    }
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(
          request, reinterpret_cast<const char *>(jpeg_buffer), jpeg_length);
    }

    if (allocated) {
      free(jpeg_buffer);
    }
    esp_camera_fb_return(frame);
    if (result != ESP_OK) {
      return result;
    }
  }
}

bool initializeCamera() {
  camera_config_t config{};
  config.ledc_channel = static_cast<ledc_channel_t>(kPwmChannel);
  config.ledc_timer = static_cast<ledc_timer_t>(kPwmTimer);
  config.pin_d0 = kY2;
  config.pin_d1 = kY3;
  config.pin_d2 = kY4;
  config.pin_d3 = kY5;
  config.pin_d4 = kY6;
  config.pin_d5 = kY7;
  config.pin_d6 = kY8;
  config.pin_d7 = kY9;
  config.pin_xclk = kXclk;
  config.pin_pclk = kPclk;
  config.pin_vsync = kVsync;
  config.pin_href = kHref;
  config.pin_sccb_sda = kSiod;
  config.pin_sccb_scl = kSioc;
  config.pin_pwdn = kPwdn;
  config.pin_reset = kReset;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = psramFound() ? FRAMESIZE_VGA : FRAMESIZE_QVGA;
  config.jpeg_quality = psramFound() ? 12 : 16;
  config.fb_count = psramFound() ? 2 : 1;
  config.grab_mode = CAMERA_GRAB_LATEST;
  return esp_camera_init(&config) == ESP_OK;
}

void connectWifi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setHostname(sotm::kCameraHostname);
  WiFi.begin(sotm::kAccessPointSsid, sotm::kAccessPointPassword);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void startServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.ctrl_port = 32769;
  config.max_uri_handlers = 4;
  config.stack_size = 8192;
  if (httpd_start(&stream_server, &config) != ESP_OK) {
    return;
  }
  httpd_uri_t root_uri{};
  root_uri.uri = "/";
  root_uri.method = HTTP_GET;
  root_uri.handler = rootHandler;
  httpd_uri_t status_uri{};
  status_uri.uri = "/status";
  status_uri.method = HTTP_GET;
  status_uri.handler = statusHandler;
  httpd_uri_t stream_uri{};
  stream_uri.uri = "/stream";
  stream_uri.method = HTTP_GET;
  stream_uri.handler = streamHandler;
  httpd_register_uri_handler(stream_server, &root_uri);
  httpd_register_uri_handler(stream_server, &status_uri);
  httpd_register_uri_handler(stream_server, &stream_uri);
}
}  // namespace

void setup() {
  Serial.begin(sotm::kUsbBaud);
  if (!initializeCamera()) {
    Serial.println("ESP32-CAM başlatılamadı; yeniden başlatılıyor.");
    delay(2000);
    ESP.restart();
  }
  connectWifi();
  if (MDNS.begin(sotm::kCameraHostname)) {
    MDNS.addService("http", "tcp", 81);
  }
  startServer();
  Serial.printf("Kamera akışı: http://%s.local:81/stream\n",
                sotm::kCameraHostname);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.disconnect();
    connectWifi();
  }
  delay(1000);
}
