#include <Arduino.h>
#include <ArduinoJson.h>
#include <FastAccelStepper.h>
#include <Preferences.h>
#include <Wire.h>

#include "sotm_config.h"

#if SOTM_S3_DIRECT_WIFI
#include <WiFi.h>
#endif

#include "angle_math.h"
#include "as5600_sensor.h"
#include "axis_controller.h"
#include "bno055_sensor.h"

namespace {

enum class OperatingMode : uint8_t { kManual, kAutomatic };

struct LineReader {
  char data[1024]{};
  size_t length = 0;
};

TwoWire primary_i2c(0);
TwoWire elevation_i2c(1);
As5600Sensor az_encoder(primary_i2c, sotm::kAs5600Address,
                        sotm::kAzEncoderReversed);
As5600Sensor el_encoder(elevation_i2c, sotm::kAs5600Address,
                        sotm::kElEncoderReversed);
Bno055Sensor imu(primary_i2c, sotm::kBno055Address);
FastAccelStepperEngine stepper_engine;
AxisController az_axis;
AxisController el_axis;
Preferences preferences;

HardwareSerial &bridge_uart = Serial1;
LineReader usb_reader;
LineReader bridge_reader;

#if SOTM_S3_DIRECT_WIFI
WiFiServer direct_server(sotm::kTcpPort);
WiFiClient direct_client;
LineReader direct_reader;
#endif

OperatingMode mode = OperatingMode::kManual;
BnoEuler euler{};
BnoCalibration calibration{};
sotm::Vec3 locked_world_vector{1.0F, 0.0F, 0.0F};

float azimuth_degrees = 0.0F;
float elevation_degrees = 0.0F;
float azimuth_zero_offset = 0.0F;
float elevation_zero_offset = 0.0F;
bool imu_ok = false;
bool az_encoder_ok = false;
bool el_encoder_ok = false;
bool motors_requested = false;
bool stopped = true;
bool fault_latched = false;
String fault_message;
uint8_t sensor_failure_count = 0;
uint32_t sequence_number = 0;
uint32_t last_control_ms = 0;
uint32_t last_telemetry_ms = 0;
uint32_t zero_button_started_ms = 0;
bool zero_button_handled = false;

const char *modeName() {
  return mode == OperatingMode::kAutomatic ? "otomatik" : "manuel";
}

void setLaser(bool enabled) {
  const bool safe_enable =
      enabled && !fault_latched && mode == OperatingMode::kAutomatic;
  digitalWrite(sotm::kLaserGatePin, safe_enable ? HIGH : LOW);
}

void stopMotion(bool emergency) {
  az_axis.stop(emergency);
  el_axis.stop(emergency);
  motors_requested = false;
  stopped = true;
  setLaser(false);
}

void setFault(const String &message) {
  if (!fault_latched) {
    fault_message = message;
  }
  fault_latched = true;
  digitalWrite(sotm::kFaultLedPin, HIGH);
  digitalWrite(sotm::kReadyLedPin, LOW);
  stopMotion(true);
}

bool safetyInputOk() {
  if (sotm::kEmergencyStopEnabled &&
      digitalRead(sotm::kEmergencyStopPin) != LOW) {
    return false;
  }
  if (sotm::kElevationLimitSwitchesEnabled) {
    if (digitalRead(sotm::kElevationMinLimitPin) == LOW &&
        el_axis.errorDegrees() < 0.0F) {
      return false;
    }
    if (digitalRead(sotm::kElevationMaxLimitPin) == LOW &&
        el_axis.errorDegrees() > 0.0F) {
      return false;
    }
  }
  return true;
}

void recoverI2cBus(uint8_t sda_pin, uint8_t scl_pin) {
  pinMode(sda_pin, INPUT_PULLUP);
  pinMode(scl_pin, OUTPUT_OPEN_DRAIN);
  digitalWrite(scl_pin, HIGH);
  delayMicroseconds(5);
  for (uint8_t pulse = 0; pulse < 9 && digitalRead(sda_pin) == LOW; ++pulse) {
    digitalWrite(scl_pin, LOW);
    delayMicroseconds(5);
    digitalWrite(scl_pin, HIGH);
    delayMicroseconds(5);
  }
  pinMode(sda_pin, OUTPUT_OPEN_DRAIN);
  digitalWrite(sda_pin, LOW);
  delayMicroseconds(5);
  digitalWrite(scl_pin, HIGH);
  delayMicroseconds(5);
  digitalWrite(sda_pin, HIGH);
  pinMode(sda_pin, INPUT_PULLUP);
}

void initializeI2cBuses() {
  recoverI2cBus(sotm::kPrimarySdaPin, sotm::kPrimarySclPin);
  recoverI2cBus(sotm::kElevationSdaPin, sotm::kElevationSclPin);
  primary_i2c.begin(sotm::kPrimarySdaPin, sotm::kPrimarySclPin,
                    sotm::kI2cFrequencyHz);
  elevation_i2c.begin(sotm::kElevationSdaPin, sotm::kElevationSclPin,
                      sotm::kI2cFrequencyHz);
  primary_i2c.setTimeOut(20);
  elevation_i2c.setTimeOut(20);
}

template <typename TDocument>
void broadcastJson(TDocument &document) {
  char buffer[1536];
  const size_t length = serializeJson(document, buffer, sizeof(buffer) - 2);
  if (length == 0 || length >= sizeof(buffer) - 2) {
    return;
  }
  buffer[length] = '\n';
  Serial.write(reinterpret_cast<const uint8_t *>(buffer), length + 1);
  bridge_uart.write(reinterpret_cast<const uint8_t *>(buffer), length + 1);
#if SOTM_S3_DIRECT_WIFI
  if (direct_client && direct_client.connected()) {
    direct_client.write(reinterpret_cast<const uint8_t *>(buffer), length + 1);
  }
#endif
}

void sendAck(const char *command, bool ok, const char *message) {
  JsonDocument response;
  response["type"] = "ack";
  response["protocol"] = 1;
  response["cmd"] = command;
  response["ok"] = ok;
  response["message"] = message;
  broadcastJson(response);
}

bool validGain(float value) {
  return isfinite(value) && value >= 0.0F && value <= 100.0F;
}

void savePid() {
  const PidGains az = az_axis.gains();
  const PidGains el = el_axis.gains();
  preferences.putFloat("az_p", az.p);
  preferences.putFloat("az_i", az.i);
  preferences.putFloat("az_d", az.d);
  preferences.putFloat("el_p", el.p);
  preferences.putFloat("el_i", el.i);
  preferences.putFloat("el_d", el.d);
}

void sendPid() {
  const PidGains az = az_axis.gains();
  const PidGains el = el_axis.gains();
  JsonDocument response;
  response["type"] = "pid";
  response["protocol"] = 1;
  JsonObject pid = response["pid"].to<JsonObject>();
  JsonObject azimuth = pid["azimut"].to<JsonObject>();
  azimuth["p"] = az.p;
  azimuth["i"] = az.i;
  azimuth["d"] = az.d;
  JsonObject elevation = pid["elevasyon"].to<JsonObject>();
  elevation["p"] = el.p;
  elevation["i"] = el.i;
  elevation["d"] = el.d;
  response["azimut_p"] = az.p;
  response["azimut_i"] = az.i;
  response["azimut_d"] = az.d;
  response["elevasyon_p"] = el.p;
  response["elevasyon_i"] = el.i;
  response["elevasyon_d"] = el.d;
  broadcastJson(response);
}

sotm::Mat3 currentBaseRotation() {
  return sotm::rotationFromYawPitchRoll(
      euler.yaw * sotm::kImuYawSign, euler.pitch * sotm::kImuPitchSign,
      euler.roll * sotm::kImuRollSign);
}

void captureWorldTarget(float azimuth, float elevation) {
  const sotm::Vec3 body_vector =
      sotm::vectorFromAzimuthElevation(azimuth, elevation);
  locked_world_vector = sotm::multiply(currentBaseRotation(), body_vector);
}

bool enterAutomaticMode() {
  const bool calibration_ready =
      calibration.gyro >= 2 && calibration.accelerometer >= 2;
  if (fault_latched || !imu_ok || !az_encoder_ok || !el_encoder_ok ||
      !calibration_ready) {
    return false;
  }
  captureWorldTarget(azimuth_degrees, elevation_degrees);
  mode = OperatingMode::kAutomatic;
  motors_requested = true;
  stopped = false;
  setLaser(true);
  return true;
}

void enterManualMode() {
  mode = OperatingMode::kManual;
  az_axis.setTarget(azimuth_degrees);
  el_axis.setTarget(elevation_degrees);
  stopMotion(false);
}

void calibrateZero() {
  if (motors_requested || mode != OperatingMode::kManual) {
    sendAck("sifirla", false, "Kalibrasyon için motorları durdurun.");
    return;
  }
  float az_raw = 0.0F;
  float el_raw = 0.0F;
  if (!az_encoder.readRaw(az_raw) || !el_encoder.readRaw(el_raw)) {
    setFault("Sıfır kalibrasyonunda enkoder okunamadı.");
    sendAck("sifirla", false, "Enkoder okunamadı.");
    return;
  }
  azimuth_zero_offset =
      sotm::kAzEncoderReversed ? sotm::normalize360(-az_raw) : az_raw;
  elevation_zero_offset =
      sotm::kElEncoderReversed ? sotm::normalize360(-el_raw) : el_raw;
  az_encoder.setZeroOffset(azimuth_zero_offset);
  el_encoder.setZeroOffset(elevation_zero_offset);
  preferences.putFloat("az_zero", azimuth_zero_offset);
  preferences.putFloat("el_zero", elevation_zero_offset);
  az_axis.setTarget(0.0F);
  el_axis.setTarget(0.0F);
  sendAck("sifirla", true, "Azimut/elevasyon sıfırı kaydedildi.");
}

void handleCommand(const char *line) {
  JsonDocument request;
  const DeserializationError error = deserializeJson(request, line);
  if (error) {
    sendAck("json", false, "Geçersiz JSON.");
    return;
  }

  const char *command = request["komut"] | "";

  if (strcmp(command, "ping") == 0) {
    sendAck(command, true, "pong");
    return;
  }
  if (strcmp(command, "dur") == 0) {
    enterManualMode();
    sendAck(command, true, "Motorlar ve lazer durduruldu.");
    return;
  }
  if (strcmp(command, "mod_degistir") == 0) {
    const char *requested_mode = request["mod"] | "";
    if (strcmp(requested_mode, "otomatik") == 0) {
      sendAck(command, enterAutomaticMode(),
              mode == OperatingMode::kAutomatic
                  ? "Otomatik stabilizasyon etkin."
                  : "Sensor kalibrasyonu veya guvenlik kosulu hazir degil.");
    } else if (strcmp(requested_mode, "manuel") == 0) {
      enterManualMode();
      sendAck(command, true, "Manuel mod etkin.");
    } else {
      sendAck(command, false, "Bilinmeyen mod.");
    }
    return;
  }
  if (strcmp(command, "git") == 0) {
    if (mode != OperatingMode::kManual || fault_latched) {
      sendAck(command, false, "Manuel mod veya hatasız durum gerekli.");
      return;
    }
    const float azimuth = request["azimut"] | NAN;
    const float elevation = request["elevasyon"] | NAN;
    if (!isfinite(azimuth) || !isfinite(elevation) || azimuth < 0.0F ||
        azimuth >= 360.0F || elevation < sotm::kElMinDeg ||
        elevation > sotm::kElMaxDeg) {
      sendAck(command, false, "Hedef hareket limitleri dışında.");
      return;
    }
    az_axis.setTarget(azimuth);
    el_axis.setTarget(elevation);
    preferences.putFloat("target_az", azimuth);
    preferences.putFloat("target_el", elevation);
    motors_requested = true;
    stopped = false;
    sendAck(command, true, "Hedef kabul edildi.");
    return;
  }
  if (strcmp(command, "duzelt") == 0) {
    if (mode != OperatingMode::kAutomatic || fault_latched) {
      sendAck(command, false, "Kamera düzeltmesi yalnız otomatik modda.");
      return;
    }
    const float delta_az = sotm::clampf(
        request["delta_azimuth"] | 0.0F, -sotm::kMaxCameraCorrectionDeg,
        sotm::kMaxCameraCorrectionDeg);
    const float delta_el = sotm::clampf(
        request["delta_elevation"] | 0.0F, -sotm::kMaxCameraCorrectionDeg,
        sotm::kMaxCameraCorrectionDeg);
    float body_az = az_axis.target() + delta_az;
    float body_el = sotm::clampf(el_axis.target() + delta_el, sotm::kElMinDeg,
                                 sotm::kElMaxDeg);
    captureWorldTarget(body_az, body_el);
    sendAck(command, true, "Görüntü düzeltmesi uygulandı.");
    return;
  }
  if (strcmp(command, "pid_oku") == 0) {
    sendPid();
    sendAck(command, true, "PID degerleri gonderildi.");
    return;
  }
  if (strcmp(command, "pid_uygula") == 0) {
    const JsonObjectConst az = request["azimut"].as<JsonObjectConst>();
    const JsonObjectConst el = request["elevasyon"].as<JsonObjectConst>();
    const PidGains az_gains{az["p"] | NAN, az["i"] | NAN, az["d"] | NAN};
    const PidGains el_gains{el["p"] | NAN, el["i"] | NAN, el["d"] | NAN};
    if (!validGain(az_gains.p) || !validGain(az_gains.i) ||
        !validGain(az_gains.d) || !validGain(el_gains.p) ||
        !validGain(el_gains.i) || !validGain(el_gains.d)) {
      sendAck(command, false, "PID değerleri 0..100 aralığında olmalı.");
      return;
    }
    az_axis.setGains(az_gains);
    el_axis.setGains(el_gains);
    if (request["kalici"] | false) {
      savePid();
    }
    sendAck(command, true, "PID değerleri uygulandı.");
    return;
  }
  if (strcmp(command, "sifirla") == 0) {
    calibrateZero();
    return;
  }
  if (strcmp(command, "hata_temizle") == 0) {
    if (!safetyInputOk()) {
      sendAck(command, false, "Acil dur girişi hâlâ açık.");
      return;
    }
    primary_i2c.end();
    elevation_i2c.end();
    initializeI2cBuses();
    imu_ok = imu.begin();
    az_encoder_ok = az_encoder.begin();
    el_encoder_ok = el_encoder.begin();
    if (!imu_ok || !az_encoder_ok || !el_encoder_ok) {
      setFault("Sensör yeniden başlatma öz testi başarısız.");
      sendAck(command, false, "Sensör öz testi başarısız.");
      return;
    }
    fault_latched = false;
    fault_message = "";
    sensor_failure_count = 0;
    digitalWrite(sotm::kFaultLedPin, LOW);
    sendAck(command, true, "Hata kilidi temizlendi; sensörler yeniden doğrulanıyor.");
    return;
  }
  sendAck(command[0] ? command : "bilinmeyen", false, "Bilinmeyen komut.");
}

void pollStream(Stream &stream, LineReader &reader) {
  while (stream.available() > 0) {
    const int value = stream.read();
    if (value < 0) {
      return;
    }
    const char character = static_cast<char>(value);
    if (character == '\n') {
      reader.data[reader.length] = '\0';
      if (reader.length > 0) {
        handleCommand(reader.data);
      }
      reader.length = 0;
    } else if (character != '\r') {
      if (reader.length < sizeof(reader.data) - 1) {
        reader.data[reader.length++] = character;
      } else {
        reader.length = 0;
        sendAck("json", false, "Komut satırı çok uzun.");
      }
    }
  }
}

void loadPersistentSettings() {
  preferences.begin("sotm-gozcu", false);
  azimuth_zero_offset = preferences.getFloat("az_zero", 0.0F);
  elevation_zero_offset = preferences.getFloat("el_zero", 0.0F);
  az_encoder.setZeroOffset(azimuth_zero_offset);
  el_encoder.setZeroOffset(elevation_zero_offset);

  const PidGains az{
      preferences.getFloat("az_p", sotm::kDefaultKp),
      preferences.getFloat("az_i", sotm::kDefaultKi),
      preferences.getFloat("az_d", sotm::kDefaultKd),
  };
  const PidGains el{
      preferences.getFloat("el_p", sotm::kDefaultKp),
      preferences.getFloat("el_i", sotm::kDefaultKi),
      preferences.getFloat("el_d", sotm::kDefaultKd),
  };
  az_axis.setGains(az);
  el_axis.setGains(el);
  az_axis.setTarget(preferences.getFloat("target_az", 0.0F));
  el_axis.setTarget(preferences.getFloat("target_el", 0.0F));
}

void updateSensorsAndControl(float delta_seconds) {
  az_encoder_ok = az_encoder.read(azimuth_degrees);
  float raw_elevation = 0.0F;
  el_encoder_ok = el_encoder.read(raw_elevation);
  elevation_degrees =
      raw_elevation > 180.0F ? raw_elevation - 360.0F : raw_elevation;
  imu_ok = imu.readEuler(euler);
  imu.readCalibration(calibration);

  if (!az_encoder_ok || !el_encoder_ok || !imu_ok) {
    sensor_failure_count =
        min<uint8_t>(static_cast<uint8_t>(sensor_failure_count + 1), 20);
  } else {
    sensor_failure_count = 0;
  }
  if (sensor_failure_count >= 5) {
    setFault("IMU veya enkoder iletişimi kaybedildi.");
  }
  if (!safetyInputOk()) {
    setFault("Acil dur veya elevasyon limit anahtarı etkin.");
  }

  if (mode == OperatingMode::kAutomatic && !fault_latched) {
    const sotm::Vec3 body_vector =
        sotm::multiply(sotm::transpose(currentBaseRotation()),
                       locked_world_vector);
    float target_azimuth = 0.0F;
    float target_elevation = 0.0F;
    sotm::azimuthElevationFromVector(body_vector, target_azimuth,
                                     target_elevation);
    az_axis.setTarget(target_azimuth);
    el_axis.setTarget(sotm::clampf(target_elevation, sotm::kElMinDeg,
                                   sotm::kElMaxDeg));
  }

  const bool can_move = motors_requested && !fault_latched &&
                        az_encoder_ok && el_encoder_ok && imu_ok;
  az_axis.update(azimuth_degrees, delta_seconds, can_move);
  el_axis.update(elevation_degrees, delta_seconds, can_move);
  setLaser(can_move && mode == OperatingMode::kAutomatic);

  digitalWrite(sotm::kReadyLedPin,
               !fault_latched && imu_ok && az_encoder_ok && el_encoder_ok);
  digitalWrite(sotm::kCalibrationLedPin,
               calibration.gyro < 2 || calibration.accelerometer < 2);
}

const char *stateName() {
  if (fault_latched) {
    return "fault";
  }
  if (stopped || !motors_requested) {
    return "stopped";
  }
  if (mode == OperatingMode::kAutomatic) {
    return "tracking";
  }
  return az_axis.atTarget() && el_axis.atTarget() ? "ready" : "moving";
}

void sendTelemetry() {
  JsonDocument telemetry;
  telemetry["type"] = "telemetry";
  telemetry["protocol"] = 1;
  telemetry["seq"] = sequence_number++;
  telemetry["uptime_ms"] = millis();
  telemetry["mode"] = modeName();
  telemetry["state"] = stateName();
  telemetry["azimut"] = azimuth_degrees;
  telemetry["elevasyon"] = elevation_degrees;
  telemetry["target_azimut"] = az_axis.target();
  telemetry["target_elevasyon"] = el_axis.target();
  telemetry["roll"] = euler.roll;
  telemetry["pitch"] = euler.pitch;
  telemetry["yaw"] = euler.yaw;
  telemetry["hata_acisi"] =
      hypotf(az_axis.errorDegrees(), el_axis.errorDegrees());
  telemetry["hedefe_ulasildi"] = az_axis.atTarget() && el_axis.atTarget();
  telemetry["imu_ok"] = imu_ok;
  telemetry["encoder_az_ok"] = az_encoder_ok;
  telemetry["encoder_el_ok"] = el_encoder_ok;
  telemetry["motors_enabled"] = az_axis.enabled() || el_axis.enabled();
  telemetry["laser_on"] = digitalRead(sotm::kLaserGatePin) == HIGH;
  telemetry["fault"] = fault_message;
  JsonObject calib = telemetry["calib"].to<JsonObject>();
  calib["sys"] = calibration.system;
  calib["gyro"] = calibration.gyro;
  calib["accel"] = calibration.accelerometer;
  calib["mag"] = calibration.magnetometer;
  broadcastJson(telemetry);
}

void handleZeroButton() {
  const bool pressed = digitalRead(sotm::kZeroButtonPin) == LOW;
  if (!pressed) {
    zero_button_started_ms = 0;
    zero_button_handled = false;
    return;
  }
  if (zero_button_started_ms == 0) {
    zero_button_started_ms = millis();
  }
  if (!zero_button_handled && millis() - zero_button_started_ms >= 1200) {
    zero_button_handled = true;
    calibrateZero();
  }
}

#if SOTM_S3_DIRECT_WIFI
void setupDirectWifi() {
  WiFi.mode(WIFI_AP);
  WiFi.setSleep(false);
  WiFi.softAP(sotm::kAccessPointSsid, sotm::kAccessPointPassword);
  direct_server.begin();
  direct_server.setNoDelay(true);
}

void pollDirectWifi() {
  if (!direct_client || !direct_client.connected()) {
    WiFiClient candidate = direct_server.available();
    if (candidate) {
      direct_client.stop();
      direct_client = candidate;
      direct_client.setNoDelay(true);
      direct_reader.length = 0;
    }
  }
  if (direct_client && direct_client.connected()) {
    pollStream(direct_client, direct_reader);
  }
}
#endif

}  // namespace

void setup() {
  pinMode(sotm::kLaserGatePin, OUTPUT);
  pinMode(sotm::kReadyLedPin, OUTPUT);
  pinMode(sotm::kCalibrationLedPin, OUTPUT);
  pinMode(sotm::kFaultLedPin, OUTPUT);
  pinMode(sotm::kZeroButtonPin, INPUT_PULLUP);
  pinMode(sotm::kEmergencyStopPin, INPUT_PULLUP);
  pinMode(sotm::kElevationMinLimitPin, INPUT_PULLUP);
  pinMode(sotm::kElevationMaxLimitPin, INPUT_PULLUP);
  setLaser(false);
  digitalWrite(sotm::kReadyLedPin, LOW);
  digitalWrite(sotm::kCalibrationLedPin, HIGH);
  digitalWrite(sotm::kFaultLedPin, LOW);

  Serial.begin(sotm::kUsbBaud);
  bridge_uart.begin(sotm::kBridgeUartBaud, SERIAL_8N1, sotm::kBridgeRxPin,
                    sotm::kBridgeTxPin);

  initializeI2cBuses();

  stepper_engine.init();
  const bool az_motor_ok =
      az_axis.begin(stepper_engine, sotm::kAzStepPin, sotm::kAzDirPin,
                    sotm::kAzEnablePin, sotm::kAzDirectionHighCountsUp, true,
                    sotm::kAzStepsPerAxisDegree);
  const bool el_motor_ok =
      el_axis.begin(stepper_engine, sotm::kElStepPin, sotm::kElDirPin,
                    sotm::kElEnablePin, sotm::kElDirectionHighCountsUp, false,
                    sotm::kElStepsPerAxisDegree);

  loadPersistentSettings();
  imu_ok = imu.begin();
  az_encoder_ok = az_encoder.begin();
  el_encoder_ok = el_encoder.begin();
  if (!az_motor_ok || !el_motor_ok) {
    setFault("Step motor darbe kanalı başlatılamadı.");
  } else if (!imu_ok || !az_encoder_ok || !el_encoder_ok) {
    setFault("Başlangıç sensör öz testi başarısız.");
  }

#if SOTM_S3_DIRECT_WIFI
  setupDirectWifi();
#endif

  JsonDocument hello;
  hello["type"] = "hello";
  hello["protocol"] = 1;
  hello["device"] = "ESP32-S3 SOTM Controller";
  hello["message"] = fault_latched ? fault_message : "Kontrolcü hazır.";
  broadcastJson(hello);
  last_control_ms = millis();
  last_telemetry_ms = millis();
}

void loop() {
  pollStream(Serial, usb_reader);
  pollStream(bridge_uart, bridge_reader);
#if SOTM_S3_DIRECT_WIFI
  pollDirectWifi();
#endif
  handleZeroButton();

  const uint32_t now = millis();
  if (now - last_control_ms >= sotm::kControlPeriodMs) {
    const uint32_t elapsed_ms = now - last_control_ms;
    last_control_ms = now;
    updateSensorsAndControl(static_cast<float>(elapsed_ms) / 1000.0F);
  }
  if (now - last_telemetry_ms >= sotm::kTelemetryPeriodMs) {
    last_telemetry_ms = now;
    sendTelemetry();
  }
  delay(1);
}
