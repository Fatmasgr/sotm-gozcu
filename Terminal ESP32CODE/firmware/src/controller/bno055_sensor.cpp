#include "bno055_sensor.h"

namespace {
constexpr uint8_t kChipIdRegister = 0x00;
constexpr uint8_t kExpectedChipId = 0xA0;
constexpr uint8_t kPageIdRegister = 0x07;
constexpr uint8_t kEulerHeadingLsbRegister = 0x1A;
constexpr uint8_t kCalibrationRegister = 0x35;
constexpr uint8_t kUnitSelectionRegister = 0x3B;
constexpr uint8_t kOperationModeRegister = 0x3D;
constexpr uint8_t kPowerModeRegister = 0x3E;
constexpr uint8_t kSystemTriggerRegister = 0x3F;
constexpr uint8_t kConfigMode = 0x00;
constexpr uint8_t kNdofMode = 0x0C;
}  // namespace

Bno055Sensor::Bno055Sensor(TwoWire &wire, uint8_t address)
    : wire_(wire), address_(address) {}

bool Bno055Sensor::writeRegister(uint8_t reg, uint8_t value) {
  wire_.beginTransmission(address_);
  wire_.write(reg);
  wire_.write(value);
  const bool ok = wire_.endTransmission() == 0;
  healthy_ = healthy_ && ok;
  return ok;
}

bool Bno055Sensor::readRegister(uint8_t reg, uint8_t *data, size_t length) {
  wire_.beginTransmission(address_);
  wire_.write(reg);
  if (wire_.endTransmission(false) != 0) {
    healthy_ = false;
    return false;
  }
  const size_t received =
      wire_.requestFrom(static_cast<int>(address_), static_cast<int>(length));
  if (received != length) {
    healthy_ = false;
    while (wire_.available()) {
      wire_.read();
    }
    return false;
  }
  for (size_t index = 0; index < length; ++index) {
    data[index] = static_cast<uint8_t>(wire_.read());
  }
  healthy_ = true;
  return true;
}

bool Bno055Sensor::begin() {
  delay(700);
  uint8_t chip_id = 0;
  if (!readRegister(kChipIdRegister, &chip_id, 1) ||
      chip_id != kExpectedChipId) {
    delay(1000);
    if (!readRegister(kChipIdRegister, &chip_id, 1) ||
        chip_id != kExpectedChipId) {
      healthy_ = false;
      return false;
    }
  }

  healthy_ = true;
  if (!writeRegister(kOperationModeRegister, kConfigMode)) {
    return false;
  }
  delay(30);
  if (!writeRegister(kPageIdRegister, 0x00) ||
      !writeRegister(kPowerModeRegister, 0x00) ||
      !writeRegister(kUnitSelectionRegister, 0x00)) {
    return false;
  }
  delay(10);
  // Dahili osilatör varsayılan ve en taşınabilir seçimdir.
  if (!writeRegister(kSystemTriggerRegister, 0x00)) {
    return false;
  }
  delay(10);
  if (!writeRegister(kOperationModeRegister, kNdofMode)) {
    return false;
  }
  delay(25);
  healthy_ = true;
  return true;
}

bool Bno055Sensor::readEuler(BnoEuler &euler) {
  uint8_t bytes[6]{};
  if (!readRegister(kEulerHeadingLsbRegister, bytes, sizeof(bytes))) {
    return false;
  }
  const int16_t heading =
      static_cast<int16_t>(static_cast<uint16_t>(bytes[1]) << 8U | bytes[0]);
  const int16_t roll =
      static_cast<int16_t>(static_cast<uint16_t>(bytes[3]) << 8U | bytes[2]);
  const int16_t pitch =
      static_cast<int16_t>(static_cast<uint16_t>(bytes[5]) << 8U | bytes[4]);
  euler.yaw = static_cast<float>(heading) / 16.0F;
  euler.roll = static_cast<float>(roll) / 16.0F;
  euler.pitch = static_cast<float>(pitch) / 16.0F;
  return true;
}

bool Bno055Sensor::readCalibration(BnoCalibration &calibration) {
  uint8_t value = 0;
  if (!readRegister(kCalibrationRegister, &value, 1)) {
    return false;
  }
  calibration.system = (value >> 6U) & 0x03U;
  calibration.gyro = (value >> 4U) & 0x03U;
  calibration.accelerometer = (value >> 2U) & 0x03U;
  calibration.magnetometer = value & 0x03U;
  return true;
}

bool Bno055Sensor::healthy() const { return healthy_; }

