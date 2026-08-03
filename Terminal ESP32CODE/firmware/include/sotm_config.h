#pragma once

#include <Arduino.h>

namespace sotm {

// Ortak erişim noktası: klasik ESP32 köprüsü AP'yi açar; PC ve ESP32-CAM bağlanır.
inline constexpr char kAccessPointSsid[] = "SOTM-Gozcu";
inline constexpr char kAccessPointPassword[] = "Gozcu-2026!";
inline constexpr uint16_t kTcpPort = 8080;
inline constexpr char kCameraHostname[] = "sotm-cam";

inline constexpr uint32_t kUsbBaud = 115200;
inline constexpr uint32_t kBridgeUartBaud = 921600;
inline constexpr uint32_t kControlPeriodMs = 5;       // 200 Hz
inline constexpr uint32_t kTelemetryPeriodMs = 100;   // 10 Hz

// ESP32-S3-DevKitC-1 N16R8 pinleri. GPIO35/36/37 dahili Octal PSRAM için
// kullanılmaz; GPIO0/3/45/46 strapping, GPIO19/20 USB pinleridir.
inline constexpr uint8_t kAzStepPin = 4;
inline constexpr uint8_t kAzDirPin = 5;
inline constexpr uint8_t kAzEnablePin = 6;
inline constexpr uint8_t kElStepPin = 7;
inline constexpr uint8_t kElDirPin = 15;
inline constexpr uint8_t kElEnablePin = 16;

inline constexpr uint8_t kPrimarySdaPin = 8;   // BNO055 + Azimut AS5600
inline constexpr uint8_t kPrimarySclPin = 9;
inline constexpr uint8_t kElevationSdaPin = 10;  // Elevasyon AS5600 (ayrı bus)
inline constexpr uint8_t kElevationSclPin = 11;

inline constexpr uint8_t kLaserGatePin = 13;
inline constexpr uint8_t kZeroButtonPin = 14;
inline constexpr uint8_t kBridgeTxPin = 17;
inline constexpr uint8_t kBridgeRxPin = 18;
inline constexpr uint8_t kEmergencyStopPin = 21;
inline constexpr uint8_t kElevationMinLimitPin = 1;
inline constexpr uint8_t kElevationMaxLimitPin = 2;
inline constexpr uint8_t kReadyLedPin = 40;
inline constexpr uint8_t kCalibrationLedPin = 41;
inline constexpr uint8_t kFaultLedPin = 42;

inline constexpr bool kEmergencyStopEnabled = true;
inline constexpr bool kElevationLimitSwitchesEnabled = false;
inline constexpr bool kMotorEnableActiveLow = false;  // NPN open-collector arayüz
inline constexpr bool kAzDirectionHighCountsUp = true;
inline constexpr bool kElDirectionHighCountsUp = true;
inline constexpr bool kAzEncoderReversed = false;
inline constexpr bool kElEncoderReversed = false;

inline constexpr float kAzMinDeg = 0.0F;
inline constexpr float kAzMaxDeg = 360.0F;
inline constexpr float kElMinDeg = 0.0F;
inline constexpr float kElMaxDeg = 90.0F;
inline constexpr float kPositionToleranceDeg = 0.25F;
inline constexpr float kTargetReachedToleranceDeg = 0.50F;
inline constexpr float kMaxCameraCorrectionDeg = 2.0F;

inline constexpr uint32_t kMinStepHz = 80;
inline constexpr uint32_t kMaxStepHz = 2000;
inline constexpr uint32_t kStepAcceleration = 3000;
inline constexpr float kMicrostepsPerRevolution = 1600.0F;  // 200 * 1/8
// Motor devri / çıkış ekseni devri. Dişli veya kayış oranı varsa gerçek
// mekanik oranı burada girin (ör. motor 3 tur, eksen 1 tur => 3.0).
inline constexpr float kAzGearRatio = 1.0F;
inline constexpr float kElGearRatio = 1.0F;
inline constexpr float kAzStepsPerAxisDegree =
    kMicrostepsPerRevolution * kAzGearRatio / 360.0F;
inline constexpr float kElStepsPerAxisDegree =
    kMicrostepsPerRevolution * kElGearRatio / 360.0F;

inline constexpr float kDefaultKp = 3.65F;
inline constexpr float kDefaultKi = 0.58F;
inline constexpr float kDefaultKd = 0.92F;
inline constexpr float kSpeedLoopKp = 0.35F;
inline constexpr float kSpeedLoopKi = 0.45F;

inline constexpr uint8_t kBno055Address = 0x28;
inline constexpr uint8_t kAs5600Address = 0x36;
inline constexpr uint32_t kI2cFrequencyHz = 400000;

// IMU kartı anten kaidesine X=ileri, Y=sağ, Z=yukarı olacak şekilde monte
// edilmelidir. Saha testinde ters tepki görülürse yalnız bu işaretleri değiştirin.
inline constexpr float kImuRollSign = 1.0F;
inline constexpr float kImuPitchSign = 1.0F;
inline constexpr float kImuYawSign = 1.0F;

}  // namespace sotm

// Normal mimaride Wi-Fi klasik ESP32 köprüsündedir. 1 yapılırsa S3 ayrıca
// kendi AP/TCP sunucusunu da açar.
#ifndef SOTM_S3_DIRECT_WIFI
#define SOTM_S3_DIRECT_WIFI 0
#endif
