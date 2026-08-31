#include "axis_controller.h"

#include <math.h>

#include "angle_math.h"
#include "sotm_config.h"

bool AxisController::begin(FastAccelStepperEngine &engine, uint8_t step_pin,
                           uint8_t dir_pin, uint8_t enable_pin,
                           bool direction_high_counts_up,
                           bool continuous_axis,
                           float steps_per_axis_degree) {
  if (!isfinite(steps_per_axis_degree) || steps_per_axis_degree <= 0.0F) {
    return false;
  }
  continuous_axis_ = continuous_axis;
  steps_per_axis_degree_ = steps_per_axis_degree;
  gains_ = {sotm::kDefaultKp, sotm::kDefaultKi, sotm::kDefaultKd};
  stepper_ = engine.stepperConnectToPin(step_pin);
  if (stepper_ == nullptr) {
    return false;
  }
  stepper_->setDirectionPin(dir_pin, direction_high_counts_up, 5);
  stepper_->setEnablePin(enable_pin, sotm::kMotorEnableActiveLow);
  stepper_->setAutoEnable(false);
  stepper_->setAcceleration(sotm::kStepAcceleration);
  stepper_->disableOutputs();
  return true;
}

void AxisController::setGains(const PidGains &gains) {
  gains_ = gains;
  integral_ = 0.0F;
  speed_integral_ = 0.0F;
  previous_error_ = 0.0F;
}

PidGains AxisController::gains() const { return gains_; }

void AxisController::setTarget(float target_degrees) {
  target_degrees_ = continuous_axis_ ? sotm::normalize360(target_degrees)
                                     : target_degrees;
}

float AxisController::target() const { return target_degrees_; }

void AxisController::enable() {
  if (stepper_ != nullptr && !enabled_) {
    stepper_->enableOutputs();
    enabled_ = true;
  }
}

void AxisController::disable() {
  if (stepper_ != nullptr) {
    stepper_->disableOutputs();
  }
  enabled_ = false;
}

void AxisController::stop(bool emergency) {
  if (stepper_ == nullptr) {
    return;
  }
  if (emergency) {
    stepper_->forceStopAndNewPosition(stepper_->getCurrentPosition());
  } else {
    stepper_->stopMove();
  }
  commanded_direction_ = 0;
  commanded_hz_ = 0;
  integral_ = 0.0F;
  speed_integral_ = 0.0F;
  if (emergency) {
    disable();
  }
}

void AxisController::commandVelocity(float step_hz) {
  if (stepper_ == nullptr) {
    return;
  }
  const int8_t direction = step_hz > 0.0F ? 1 : (step_hz < 0.0F ? -1 : 0);
  const uint32_t frequency =
      static_cast<uint32_t>(lroundf(fabsf(step_hz)));

  if (direction == 0 || frequency < sotm::kMinStepHz) {
    if (commanded_direction_ != 0) {
      stepper_->stopMove();
      commanded_direction_ = 0;
      commanded_hz_ = 0;
    }
    return;
  }

  const uint32_t limited =
      min<uint32_t>(frequency, static_cast<uint32_t>(sotm::kMaxStepHz));
  if (direction == commanded_direction_ &&
      abs(static_cast<int32_t>(limited) -
          static_cast<int32_t>(commanded_hz_)) < 5) {
    return;
  }
  stepper_->setSpeedInHz(limited);
  stepper_->setAcceleration(sotm::kStepAcceleration);
  if (direction > 0) {
    stepper_->runForward();
  } else {
    stepper_->runBackward();
  }
  commanded_direction_ = direction;
  commanded_hz_ = limited;
}

void AxisController::update(float position_degrees, float delta_seconds,
                            bool allowed_to_move) {
  if (delta_seconds <= 0.0F || !isfinite(position_degrees)) {
    return;
  }

  if (!initialized_) {
    previous_position_ = position_degrees;
    previous_error_ = continuous_axis_
                          ? sotm::wrap180(target_degrees_ - position_degrees)
                          : target_degrees_ - position_degrees;
    initialized_ = true;
  }

  float position_delta = position_degrees - previous_position_;
  if (continuous_axis_) {
    position_delta = sotm::wrap180(position_delta);
  }
  const float raw_velocity = position_delta / delta_seconds;
  measured_velocity_dps_ =
      0.75F * measured_velocity_dps_ + 0.25F * raw_velocity;
  previous_position_ = position_degrees;

  error_degrees_ = continuous_axis_
                       ? sotm::wrap180(target_degrees_ - position_degrees)
                       : target_degrees_ - position_degrees;
  if (!allowed_to_move) {
    stop(true);
    previous_error_ = error_degrees_;
    return;
  }

  enable();
  if (fabsf(error_degrees_) <= sotm::kPositionToleranceDeg) {
    integral_ *= 0.9F;
    speed_integral_ *= 0.8F;
    commandVelocity(0.0F);
    previous_error_ = error_degrees_;
    return;
  }

  integral_ += error_degrees_ * delta_seconds;
  integral_ = sotm::clampf(integral_, -250.0F, 250.0F);
  const float derivative = (error_degrees_ - previous_error_) / delta_seconds;
  previous_error_ = error_degrees_;

  const float target_step_hz = sotm::clampf(
      gains_.p * error_degrees_ + gains_.i * integral_ +
          gains_.d * derivative,
      -static_cast<float>(sotm::kMaxStepHz),
      static_cast<float>(sotm::kMaxStepHz));
  const float measured_step_hz =
      measured_velocity_dps_ * steps_per_axis_degree_;
  const float speed_error = target_step_hz - measured_step_hz;
  speed_integral_ += speed_error * delta_seconds;
  speed_integral_ = sotm::clampf(
      speed_integral_, -static_cast<float>(sotm::kMaxStepHz),
      static_cast<float>(sotm::kMaxStepHz));
  const float commanded = sotm::clampf(
      target_step_hz + sotm::kSpeedLoopKp * speed_error +
          sotm::kSpeedLoopKi * speed_integral_,
      -static_cast<float>(sotm::kMaxStepHz),
      static_cast<float>(sotm::kMaxStepHz));
  commandVelocity(commanded);
}

bool AxisController::enabled() const { return enabled_; }

bool AxisController::atTarget() const {
  return fabsf(error_degrees_) <= sotm::kTargetReachedToleranceDeg;
}

float AxisController::errorDegrees() const { return error_degrees_; }

float AxisController::measuredVelocityDegreesPerSecond() const {
  return measured_velocity_dps_;
}
