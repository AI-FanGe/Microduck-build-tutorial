# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import numpy as np

MOTOR_TO_ID = {
    "right_hip_yaw": 5,
    "right_hip_roll": 4,
    "right_hip_pitch": 3,
    "right_knee": 2,
    "right_ankle": 1,
    "left_hip_yaw": 10,
    "left_hip_roll": 9,
    "left_hip_pitch": 8,
    "left_knee": 7,
    "left_ankle": 6,
    "neck_pitch": 12,
    "head_pitch": 11,
    "head_yaw": 13,
    "head_roll": 14,
}

ID_TO_MOTOR = {v: k for k, v in MOTOR_TO_ID.items()}

NEUTRAL_POSE = {
    "right_hip_yaw": float(np.deg2rad(0.0)),
    "right_hip_roll": 0.0873,
    "right_hip_pitch": 0.4579,
    "right_knee": 0.0049,
    "right_ankle": -0.4530,
    "left_hip_yaw": float(np.deg2rad(0.0)),
    "left_hip_roll": -0.0873,
    "left_hip_pitch": -0.4579,
    "left_knee": -0.0049,
    "left_ankle": 0.4530,
    "neck_pitch": 0.3491,
    "head_pitch": 0.3491,
    "head_yaw": float(np.deg2rad(0.0)),
    "head_roll": float(np.deg2rad(0.0)),
}

MOTOR_SIGN = {name: 1.0 for name in MOTOR_TO_ID}

# Hardware zero offsets, in radians. Hardware command = model target * sign + offset.
# These two fixed offsets are part of the user's real leg assembly and must stay.
MOTOR_OFFSET = {name: 0.0 for name in MOTOR_TO_ID}
MOTOR_OFFSET["right_knee"] = float(np.deg2rad(45.0))   # ID 2
MOTOR_OFFSET["left_knee"] = float(np.deg2rad(-45.0))   # ID 7

# Position P Gain (Dynamixel register value)
KP_DEFAULT: int = 400        # ~0.886 Nm/rad in MuJoCo
KP_RL: int = 125             # ~0.277 Nm/rad in MuJoCo
KP_GAIN_PRM: float = 0.0022  # Nm/rad per register unit (for Xl330)

# BAM motor model (bam package, XL330 m6)
BAM_VIN: float = 7.5
BAM_VIN_MIN: float = 6.0
BAM_VOLTAGE_DROP_GAIN: float = 0.2
BAM_MAX_CURRENT: float = 1.75 # XL330 firmware current limit [A]: clips motor torque to ±BAM_MAX_CURRENT * kt

# Overcurrent safety: emergency torque-off when the summed |present_current| of all
# motors stays above OVERCURRENT_CUTOFF_A for OVERCURRENT_DEBOUNCE_TICKS consecutive ticks.
# Goal: cut the robot before a current spike (e.g. all motors snapping during a fall) trips the BMS.
PRESENT_CURRENT_UNIT_A: float = 0.001   # XL330 present_current register unit (1.0 mA/LSB)
OVERCURRENT_CUTOFF_A: float = 15.0      # total pack current threshold (CALIBRATE: below BMS trip, above normal walk peak)
OVERCURRENT_DEBOUNCE_TICKS: int = 2     # consecutive over-threshold ticks before cutting

# Current proxy used when present_current is NOT read (Observer.observe_current = False), so the
# safety needs no extra bus transaction. Reproduces the bam XL330 m6 voltage-controlled model from
# data already read (present_position, present_velocity) and the command target:
#   duty = clip(PROXY_KP * PROXY_ERROR_GAIN * (target - q), ±PROXY_MAX_PWM)
#   I    = (PROXY_VIN * duty - PROXY_KT * dq) / PROXY_R      then |I| capped at BAM_MAX_CURRENT
PROXY_KT: float = 0.366                  # XL330 m6 torque constant [Nm/A]
PROXY_R: float = 2.811                   # XL330 m6 motor resistance [Ohm]
PROXY_VIN: float = BAM_VIN               # supply voltage [V]
PROXY_ERROR_GAIN: float = 0.0028773775   # duty cycle per (kp * rad), XL330 encoder/gain scaling
PROXY_MAX_PWM: float = 1.0               # max duty cycle magnitude
PROXY_KP: int = KP_RL                    # firmware P gain assumed by the proxy (walking regime)
OVERCURRENT_PROXY_DELAY_TICKS: int = 3   # number of ticks to delay the proxy current estimate

# Velocity command limits [m/s, m/s, rad/s], applied centrally to every input source.
# Input sources emit normalized commands in [-1, 1]; scale_velocity() maps them to these.
# Rotation gets a wider range when turning in place (vx = vy = 0) than while translating.
VX_MAX: float = 0.7
VX_MAX_BACKWARD: float = 0.5  # backward (vx < 0) is capped lower than forward
VY_MAX: float = 0.3
VTHETA_MAX_STATIONARY: float = 3.0
VTHETA_MAX_MOVING: float = 1.5

# IMU (GY-BNO080/BNO08x) I2C bus number on the Raspberry Pi
IMU_I2C_BUS: int = 1

# Rotation from trunk frame (body) to IMU sensor frame
IMU_MOUNT_QUAT: tuple[float, float, float, float] = (0.7071068, 0.0, 0.7071068, 0.0)

# Observation DoF ordering
OBSERVATION_DOF_ORDER = [
    "left_hip_yaw",
    "left_hip_roll",
    "left_hip_pitch",
    "left_knee",
    "left_ankle",
    "neck_pitch",
    "head_pitch",
    "head_yaw",
    "head_roll",
    "right_hip_yaw",
    "right_hip_roll",
    "right_hip_pitch",
    "right_knee",
    "right_ankle",
]