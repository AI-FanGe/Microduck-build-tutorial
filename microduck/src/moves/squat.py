# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import math
import placo

import numpy as np

from observer import Observation
from moves.move import MotorCommand, Move, MoveState
from constants import NEUTRAL_POSE

_LOWER_JOINTS = [
    "left_hip_yaw", "left_hip_roll", "left_hip_pitch",
    "left_knee", "left_ankle_pitch", "left_ankle_roll",
    "right_hip_yaw", "right_hip_roll", "right_hip_pitch",
    "right_knee", "right_ankle_pitch", "right_ankle_roll",
]

_UPPER_JOINTS = [
    "left_shoulder_pitch", "left_shoulder_roll", "left_elbow",
    "right_shoulder_pitch", "right_shoulder_roll", "right_elbow",
]


# Set to True to log IMU and COM data during the squat move
LOGGING = False 


class SquatMove(Move):
    """Squat motion using placo IK."""

    def __init__(
        self,
        frequency: float = 0.3,
        amplitude: float = 0.02,
        lerp_duration: float = 1.0,
    ) -> None:
        super().__init__()
        self._model_path = "src/model/urdf"
        self.frequency = frequency
        self.amplitude = amplitude
        self.lerp_duration = lerp_duration

        self._start_lerp_time_s: float | None = None
        self._start_lerp_angles: list[float] = []
        self._stop_lerp_time_s: float | None = None
        self._stop_lerp_angles: list[float] = []
        self._active_start_time_s: float = 0.0

        self._placo_ready = False

        # Logging
        self._initialiation_delay_s = 5.0
        self._target_com_z: list[float] = []
        self._obs_projected_gravity_x: list[float] = []
        self._obs_projected_gravity_y: list[float] = []
        self._obs_projected_gravity_z: list[float] = []
        self._obs_gyro_roll: list[float] = []
        self._obs_gyro_pitch: list[float] = []
        self._obs_gyro_yaw: list[float] = []

    def preload(self) -> None:
        self._initialize()

    def _initialize(self) -> None:
        """Lazy initialization of placo model and IK solver (deferred to first activation)."""
        if self._placo_ready:
            return

        self._robot = placo.RobotWrapper(self._model_path)
        self._solver = placo.KinematicsSolver(self._robot)

        for name, angle in NEUTRAL_POSE.items():
            self._robot.set_joint(name, angle)
        self._T_left_foot = np.eye(4)
        self._robot.set_T_world_frame("left_foot", self._T_left_foot)
        self._robot.update_kinematics()

        self._com_initial = self._robot.com_world()
        T_right_foot = self._robot.get_T_world_frame("right_foot").copy()
        T_right_foot[2, 3] = 0.0

        self._left_foot_task = self._solver.add_frame_task("left_foot", self._T_left_foot)
        self._left_foot_task.configure("left_foot", "hard", 1.0)
        self._right_foot_task = self._solver.add_frame_task("right_foot", T_right_foot)
        self._right_foot_task.configure("right_foot", "hard", 1.0)

        self._com_task = self._solver.add_com_task(self._com_initial)
        self._com_task.configure("com", "soft", 100.0)

        trunk_task = self._solver.add_orientation_task("trunk", np.eye(3))
        trunk_task.configure("trunk_orient", "soft", 1.0)

        joints_task = self._solver.add_joints_task()
        joints_task.set_joints({name: NEUTRAL_POSE[name] for name in _UPPER_JOINTS})
        joints_task.configure("upper_body", "soft", 1.0)

        joints_task = self._solver.add_joints_task()
        joints_task.set_joints({name: NEUTRAL_POSE[name] for name in _LOWER_JOINTS})
        joints_task.configure("lower_body", "soft", 1e-3)

        self._solver.add_regularization_task(1e-6)

        for _ in range(50):
            self._solver.solve(True)
            self._robot.update_kinematics()

        self._start_target_angles = [self._robot.get_joint(name) for name in _LOWER_JOINTS + _UPPER_JOINTS]
        self._placo_ready = True

    def on_start(self, obs: Observation, command: MotorCommand) -> None:
        self._initialize()
        if self._start_lerp_time_s is None:
            self._start_lerp_time_s = obs.robot_state.time_s
            self._start_lerp_angles = [obs.robot_state.motor_positions.get(name, 0.0) for name in _LOWER_JOINTS + _UPPER_JOINTS]

        t = (obs.robot_state.time_s - self._start_lerp_time_s) / self.lerp_duration
        t = min(t, 1.0)
        for i, name in enumerate(_LOWER_JOINTS + _UPPER_JOINTS):
            command.target_angles[name] = self._start_lerp_angles[i] * (1.0 - t) + self._start_target_angles[i] * t

        if t >= 1.0:
            for i, name in enumerate(_LOWER_JOINTS + _UPPER_JOINTS):
                self._robot.set_joint(name, self._start_target_angles[i])
            self._robot.set_T_world_frame("left_foot", self._T_left_foot)
            self._robot.update_kinematics()
            self._com_task.target_world = self._com_initial.copy()

            
            if LOGGING and self._initialiation_delay_s > 0.0:
                self.save_state(obs)
                self._initialiation_delay_s -= 0.02
                return
            
            self._start_lerp_time_s = None
            self._active_start_time_s = obs.robot_state.time_s

            self.state = MoveState.ACTIVE

    def save_state(self, obs: Observation) -> None:
        self._obs_projected_gravity_x.append(obs.robot_state.projected_gravity[0])
        self._obs_projected_gravity_y.append(obs.robot_state.projected_gravity[1])
        self._obs_projected_gravity_z.append(obs.robot_state.projected_gravity[2])
        self._obs_gyro_roll.append(obs.robot_state.gyro[0])
        self._obs_gyro_pitch.append(obs.robot_state.gyro[1])
        self._obs_gyro_yaw.append(obs.robot_state.gyro[2])
        self._target_com_z.append(self._com_task.target_world[2])

    def step(self, obs: Observation, command: MotorCommand) -> None:
        t = obs.robot_state.time_s - self._active_start_time_s
        p_com = self._com_initial.copy()
        p_com[2] -= self.amplitude * (1.0 - math.cos(2.0 * math.pi * self.frequency * t))
        self._com_task.target_world = p_com

        self._solver.solve(True)
        self._robot.update_kinematics()

        for name in _LOWER_JOINTS + _UPPER_JOINTS:
            command.target_angles[name] = self._robot.get_joint(name)

        if LOGGING:
            self.save_state(obs)

    def on_stop(self, obs: Observation, command: MotorCommand) -> None:
        if LOGGING:
            import json
            with open("squat_log.json", "w") as f:
                json.dump({
                    "obs_projected_gravity_x": self._obs_projected_gravity_x,
                    "obs_projected_gravity_y": self._obs_projected_gravity_y,
                    "obs_projected_gravity_z": self._obs_projected_gravity_z,
                    "obs_gyro_roll": self._obs_gyro_roll,
                    "obs_gyro_pitch": self._obs_gyro_pitch,
                    "obs_gyro_yaw": self._obs_gyro_yaw,
                    "target_com_z": self._target_com_z,
                }, f, indent=2)

        if self._stop_lerp_time_s is None:
            self._stop_lerp_time_s = obs.robot_state.time_s
            self._stop_lerp_angles = [obs.robot_state.motor_positions.get(name, 0.0) for name in _LOWER_JOINTS + _UPPER_JOINTS]

        t = (obs.robot_state.time_s - self._stop_lerp_time_s) / self.lerp_duration
        t = min(t, 1.0)
        for i, name in enumerate(_LOWER_JOINTS + _UPPER_JOINTS):
            command.target_angles[name] = self._stop_lerp_angles[i] * (1.0 - t) + NEUTRAL_POSE[name] * t

        if t >= 1.0:
            self._stop_lerp_time_s = None
            self._start_lerp_time_s = None
            self.state = MoveState.INACTIVE