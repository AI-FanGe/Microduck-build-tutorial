# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

"""MeshCat viewer controller using placo kinematics — never deployed to the robot."""

import math

import numpy as np
import placo
from placo_utils.visualization import robot_viz

from constants import ID_TO_MOTOR, NEUTRAL_POSE, KP_DEFAULT


class PlacoViewerController:
    """Physics-free controller that displays the robot in a MeshCat browser window."""

    def __init__(self, model_path: str, dt: float) -> None:

        # Load robot and set neutral pose
        self._robot = placo.RobotWrapper(model_path, placo.Flags.mjcf)

        for name, angle in NEUTRAL_POSE.items():
            self._robot.set_joint(name, angle)

        T_left_foot = np.eye(4)
        self._robot.set_T_world_frame("left_foot", T_left_foot)
        self._robot.update_kinematics()

        # Open MeshCat viewer
        self._viz = robot_viz(self._robot)
        self._viz.display(self._robot.state.q)

        # Track commanded angles
        self._current_angles: dict[str, float] = dict(NEUTRAL_POSE)
        self._last_angles: dict[str, float] = dict(NEUTRAL_POSE)
        self._dt = dt

    def sync_write_goal_position(self, ids: list[int], positions: list[float]) -> None:
        for motor_id, pos in zip(ids, positions):
            self._current_angles[ID_TO_MOTOR[motor_id]] = pos
            self._robot.set_joint(ID_TO_MOTOR[motor_id], pos)

        self._robot.set_T_world_frame("left_foot", np.eye(4))
        self._robot.update_kinematics()

        self._viz.display(self._robot.state.q)

    def sync_read_present_position(self, ids: list[int]) -> list[float]:
        return [self._current_angles.get(ID_TO_MOTOR.get(mid, ""), 0.0) for mid in ids]

    def read_present_position(self, motor_id: int) -> float:
        name = ID_TO_MOTOR.get(motor_id, "")
        return self._current_angles.get(name, 0.0)

    def sync_read_present_velocity(self, ids: list[int]) -> list[float]:
        return [(self._last_angles.get(ID_TO_MOTOR.get(mid, ""), 0.0) - self._current_angles.get(ID_TO_MOTOR.get(mid, ""), 0.0)) / self._dt for mid in ids]
    
    def read_present_velocity(self, motor_id: int) -> float:
        name = ID_TO_MOTOR.get(motor_id, "")
        return (self._last_angles.get(name, 0.0) - self._current_angles.get(name, 0.0)) / self._dt

    def sync_read_present_current(self, ids: list[int]) -> list[float]:
        return [0.0] * len(ids)

    def sync_read_present_input_voltage(self, ids: list[int]) -> list[float]:
        return [80.0] * len(ids)

    def read_present_input_voltage(self, motor_id: int) -> float:  # noqa: ARG002
        return 80.0

    def sync_read_kp(self, ids: list[int]) -> list[int]:
        return [KP_DEFAULT] * len(ids)

    def sync_write_kp(self, ids: list[int], gains: list[int]) -> None:
        pass

    def sync_write_torque_enable(self, ids: list[int], values: list[bool]) -> None:
        pass

    def read_acc(self) -> tuple[float, float, float]:
        """Return pseudo-accelerometer (ax, ay, az) in g from IMU site gravity direction via FK."""
        R = self._robot.get_T_world_frame("imu")[:3, :3]
        # gravity in world frame is (0, 0, -1) g; express in IMU frame
        g_imu = R.T @ [0.0, 0.0, -1.0]
        return float(g_imu[0]), float(g_imu[1]), float(g_imu[2])

    def read_gyro(self) -> tuple[float, float, float]:
        """No gyro available in the MeshCat viewer — return zeros."""
        return 0.0, 0.0, 0.0

    def read_quat(self, dt: float) -> tuple[float, float, float, float]:
        """Return orientation quaternion (w, x, y, z) from the IMU site frame via FK."""
        T = self._robot.get_T_world_frame("imu")
        R = T[:3, :3]
        # Rotation matrix to quaternion
        trace = R[0, 0] + R[1, 1] + R[2, 2]
        if trace > 0:
            s = 0.5 / math.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
        return float(w), float(x), float(y), float(z)

    def sync_write_status_return_level(self, ids: list[int], levels: list[int]) -> None:
        pass