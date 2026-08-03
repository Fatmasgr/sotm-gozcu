#pragma once

#include <Arduino.h>
#include <Wire.h>

class As5600Sensor {
 public:
  As5600Sensor(TwoWire &wire, uint8_t address, bool reversed);

  bool begin();
  bool read(float &angle_degrees);
  bool readRaw(float &raw_degrees);
  bool magnetHealthy();
  void setZeroOffset(float zero_offset_degrees);
  float zeroOffset() const;
  bool healthy() const;

 private:
  bool readRegister(uint8_t reg, uint8_t *data, size_t length);

  TwoWire &wire_;
  uint8_t address_;
  bool reversed_;
  bool healthy_ = false;
  float zero_offset_degrees_ = 0.0F;
};

