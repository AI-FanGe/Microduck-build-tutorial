# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

from dataclasses import dataclass, field
import time

from controller import ControllerProtocol
from input.input_source import UserInput
from constants import MOTOR_TO_ID
from imu_reader import imu_quat_to_body, quat_apply_inverse


@dataclass
class RobotState:
    """Hardware sensor readings for one scheduler iteration."""

    time_s: float = 0.0

    # IMU data
    acc: list[float] = field(default_factory=list) # accelerometer readings in g (ax, ay, az)
    gyro: list[float] = field(default_factory=list) # gyroscope readings in rad/s (gx, gy, gz)
    quat: list[float] = field(default_factory=list) # IMU orientation as a quaternion (w, x, y, z)
    body_quat: list[float] = field(default_factory=list) # body frame orientation as a quaternion (w, x, y, z)
    projected_gravity: list[float] = field(default_factory=list) # gravity vector projected in the policy IMU frame
    
    # Motor states
    motor_positions: dict[str, float] = field(default_factory=dict)
    motor_velocities: dict[str, float] = field(default_factory=dict)
    motor_currents: dict[str, float] = field(default_factory=dict)  # Amps, signed (overcurrent safety)

    # Logging
    motor_voltages: dict[str, float] = field(default_factory=dict)


@dataclass
class Observation:
    """Full observation passed through the move pipeline each tick."""

    robot_state: RobotState = field(default_factory=RobotState)
    user_input: UserInput = field(default_factory=UserInput)


class Observer:
    def __init__(self, controller: ControllerProtocol):
        self.controller = controller
        self._last_imu_warn_s: float = 0.0
        self._imu_warn_interval_s: float = 1.0

        self.observe_voltage: bool = False
        
        # When True, reads present_current each tick and the overcurrent safety uses the measured
        # current. When False (default), no extra bus read — the safety falls back to the cheaper
        # position-error proxy in the scheduler, keeping the IMU read latency low.
        self.observe_current: bool = False

    def read_state(self, dt: float) -> RobotState:
        """Read current motor positions from the controller."""
        state = RobotState(time_s=time.perf_counter())

        motor_names = list(MOTOR_TO_ID.keys())
        motor_ids = list(MOTOR_TO_ID.values())
        angles = self.controller.sync_read_present_position(motor_ids)
        state.motor_positions = dict(zip(motor_names, angles))

        velocities = self.controller.sync_read_present_velocity(motor_ids)
        state.motor_velocities = dict(zip(motor_names, velocities))

        if self.observe_current:
            currents = self.controller.sync_read_present_current(motor_ids)
            state.motor_currents = dict(zip(motor_names, currents))

        if self.observe_voltage:
            voltages = self.controller.sync_read_present_input_voltage(motor_ids)
            state.motor_voltages = dict(zip(motor_names, voltages))

        try:
            state.acc = list(self.controller.read_acc())
            state.gyro = list(self.controller.read_gyro())
            state.quat = list(self.controller.read_quat(dt))

            # Keep body_quat for diagnostics, but feed the policy gravity in the
            # mounted IMU frame. Training applies IMU_MOUNT_QUAT to body gravity,
            # which is equivalent to using the real BNO08x sensor-frame gravity.
            state.body_quat = list(imu_quat_to_body(state.quat))
            state.projected_gravity = list(quat_apply_inverse(state.quat, [0.0, 0.0, 1.0]))

        except Exception as exc:
            now = time.perf_counter()
            if (now - self._last_imu_warn_s) >= self._imu_warn_interval_s:
                print(f"Warning: observer IMU read failed: {exc}", end="\r\n", flush=True)
                self._last_imu_warn_s = now

        return state