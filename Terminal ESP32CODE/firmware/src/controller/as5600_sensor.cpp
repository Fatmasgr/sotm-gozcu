#include "as5600_sensor.h"

#include "angle_math.h"

namespace {
constexpr uint8_t kStatusRegister = 0x0B;
constexpr uint8_t kRawAngleRegister = 0x0C;
constexpr uint8_t kMagnetDetected = 1U << 5;
constexpr uint8_t kMagnetTooWeak = 1U << 4;
constexpr uint8_t kMagnetTooStrong = 1U << 3;
}  // namespace

As5600Sensor::As5600Sensor(TwoWire &wire, uint8_t address, bool reversed)
    : wire_(wire), address_(address), reversed_(reversed) {}

bool As5600Sensor::begin() {
  float ignored = 0.0F;
  healthy_ = readRaw(ignored) && magnetHealthy();
  return healthy_;
}

bool As5600Sensor::readRegister(uint8_t reg, uint8_t *data, size_t length) {
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
  return true;
}

bool As5600Sensor::readRaw(float &raw_degrees) {
  uint8_t bytes[2]{};
  if (!readRegister(kRawAngleRegister, bytes, sizeof(bytes))) {
    return false;
  }
  const uint16_t raw =
      (static_cast<uint16_t>(bytes[0] & 0x0F) << 8U) | bytes[1];
  raw_degrees = static_cast<float>(raw) * (360.0F / 4096.0F);
  healthy_ = true;
  return true;
}

bool As5600Sensor::read(float &angle_degrees) {
  float raw = 0.0F;
  if (!readRaw(raw) || !magnetHealthy()) {
    return false;
  }
  const float directed = reversed_ ? -raw : raw;
  angle_degrees = sotm::normalize360(directed - zero_offset_degrees_);
  return true;
}

bool As5600Sensor::magnetHealthy() {
  uint8_t status = 0;
  if (!readRegister(kStatusRegister, &status, 1)) {
    return false;
  }
  healthy_ = (status & kMagnetDetected) != 0 &&
             (status & (kMagnetTooWeak | kMagnetTooStrong)) == 0;
  return healthy_;
}

void As5600Sensor::setZeroOffset(float zero_offset_degrees) {
  zero_offset_degrees_ = sotm::normalize360(zero_offset_degrees);
}

float As5600Sensor::zeroOffset() const { return zero_offset_degrees_; }

bool As5600Sensor::healthy() const { return healthy_; }
