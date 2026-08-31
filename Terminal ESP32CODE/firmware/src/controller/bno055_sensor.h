#pragma once

#include <Arduino.h>
#include <Wire.h>

struct BnoEuler {
  float yaw = 0.0F;
  float roll = 0.0F;
  float pitch = 0.0F;
};

struct BnoCalibration {
  uint8_t system = 0;
  uint8_t gyro = 0;
  uint8_t accelerometer = 0;
  uint8_t magnetometer = 0;
};

class Bno055Sensor {
 public:
  Bno055Sensor(TwoWire &wire, uint8_t address);

  bool begin();
  bool readEuler(BnoEuler &euler);
  bool readCalibration(BnoCalibration &calibration);
  bool healthy() const;

 private:
  bool writeRegister(uint8_t reg, uint8_t value);
  bool readRegister(uint8_t reg, uint8_t *data, size_t length);

  TwoWire &wire_;
  uint8_t address_;
  bool healthy_ = false;
};

