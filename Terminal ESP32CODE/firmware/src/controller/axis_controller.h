#pragma once

#include <Arduino.h>
#include <FastAccelStepper.h>

struct PidGains {
  float p;
  float i;
  float d;
};

class AxisController {
 public:
  bool begin(FastAccelStepperEngine &engine, uint8_t step_pin, uint8_t dir_pin,
             uint8_t enable_pin, bool direction_high_counts_up,
             bool continuous_axis, float steps_per_axis_degree);
  void setGains(const PidGains &gains);
  PidGains gains() const;
  void setTarget(float target_degrees);
  float target() const;
  void update(float position_degrees, float delta_seconds, bool allowed_to_move);
  void stop(bool emergency);
  void enable();
  void disable();
  bool enabled() const;
  bool atTarget() const;
  float errorDegrees() const;
  float measuredVelocityDegreesPerSecond() const;

 private:
  void commandVelocity(float step_hz);

  FastAccelStepper *stepper_ = nullptr;
  PidGains gains_{};
  bool continuous_axis_ = false;
  bool enabled_ = false;
  bool initialized_ = false;
  float target_degrees_ = 0.0F;
  float integral_ = 0.0F;
  float previous_error_ = 0.0F;
  float error_degrees_ = 0.0F;
  float previous_position_ = 0.0F;
  float measured_velocity_dps_ = 0.0F;
  float speed_integral_ = 0.0F;
  int8_t commanded_direction_ = 0;
  uint32_t commanded_hz_ = 0;
  float steps_per_axis_degree_ = 1.0F;
};
