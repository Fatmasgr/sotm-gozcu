#pragma once

#include <Arduino.h>
#include <math.h>

namespace sotm {

inline float clampf(float value, float minimum, float maximum) {
  return value < minimum ? minimum : (value > maximum ? maximum : value);
}

inline float normalize360(float angle_deg) {
  float value = fmodf(angle_deg, 360.0F);
  if (value < 0.0F) {
    value += 360.0F;
  }
  return value;
}

inline float wrap180(float angle_deg) {
  float value = normalize360(angle_deg + 180.0F) - 180.0F;
  return value == -180.0F ? 180.0F : value;
}

inline float degreesToRadians(float degrees) {
  return degrees * static_cast<float>(M_PI) / 180.0F;
}

inline float radiansToDegrees(float radians) {
  return radians * 180.0F / static_cast<float>(M_PI);
}

struct Vec3 {
  float x;
  float y;
  float z;
};

struct Mat3 {
  float m[3][3];
};

inline Mat3 multiply(const Mat3 &a, const Mat3 &b) {
  Mat3 result{};
  for (uint8_t row = 0; row < 3; ++row) {
    for (uint8_t column = 0; column < 3; ++column) {
      for (uint8_t index = 0; index < 3; ++index) {
        result.m[row][column] += a.m[row][index] * b.m[index][column];
      }
    }
  }
  return result;
}

inline Vec3 multiply(const Mat3 &matrix, const Vec3 &vector) {
  return {
      matrix.m[0][0] * vector.x + matrix.m[0][1] * vector.y +
          matrix.m[0][2] * vector.z,
      matrix.m[1][0] * vector.x + matrix.m[1][1] * vector.y +
          matrix.m[1][2] * vector.z,
      matrix.m[2][0] * vector.x + matrix.m[2][1] * vector.y +
          matrix.m[2][2] * vector.z,
  };
}

inline Mat3 transpose(const Mat3 &matrix) {
  Mat3 result{};
  for (uint8_t row = 0; row < 3; ++row) {
    for (uint8_t column = 0; column < 3; ++column) {
      result.m[row][column] = matrix.m[column][row];
    }
  }
  return result;
}

// X=ileri/kuzey, Y=sağ/doğu, Z=yukarı. Yaw kuzeyden saat yönünde pozitiftir.
inline Mat3 rotationFromYawPitchRoll(float yaw_deg, float pitch_deg,
                                     float roll_deg) {
  const float yaw = degreesToRadians(yaw_deg);
  const float pitch = degreesToRadians(-pitch_deg);
  const float roll = degreesToRadians(roll_deg);
  const float cy = cosf(yaw);
  const float sy = sinf(yaw);
  const float cp = cosf(pitch);
  const float sp = sinf(pitch);
  const float cr = cosf(roll);
  const float sr = sinf(roll);

  const Mat3 rz{{{cy, -sy, 0.0F}, {sy, cy, 0.0F}, {0.0F, 0.0F, 1.0F}}};
  const Mat3 ry{{{cp, 0.0F, sp}, {0.0F, 1.0F, 0.0F}, {-sp, 0.0F, cp}}};
  const Mat3 rx{{{1.0F, 0.0F, 0.0F}, {0.0F, cr, -sr}, {0.0F, sr, cr}}};
  return multiply(multiply(rz, ry), rx);
}

inline Vec3 vectorFromAzimuthElevation(float azimuth_deg,
                                       float elevation_deg) {
  const float azimuth = degreesToRadians(azimuth_deg);
  const float elevation = degreesToRadians(elevation_deg);
  const float horizontal = cosf(elevation);
  return {horizontal * cosf(azimuth), horizontal * sinf(azimuth),
          sinf(elevation)};
}

inline void azimuthElevationFromVector(const Vec3 &vector, float &azimuth_deg,
                                       float &elevation_deg) {
  const float horizontal = sqrtf(vector.x * vector.x + vector.y * vector.y);
  azimuth_deg = normalize360(radiansToDegrees(atan2f(vector.y, vector.x)));
  elevation_deg = radiansToDegrees(atan2f(vector.z, horizontal));
}

}  // namespace sotm

