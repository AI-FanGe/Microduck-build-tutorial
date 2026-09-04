# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import math

from observer import Observation
from moves.move import MotorCommand, Move, MoveState


# Set to True to log head angle and velocity readings during the rotate head move
LOGGING = False 


class RotateHeadMove(Move):
    """
    Generate a sinusoidal head rotation between +/- *amplitude_rad* with a frequency *frequency*.

    Transitions (on_start / on_stop) lerp the head to 0 over *lerp_duration* seconds
    so the move starts and stops smoothly.

    :param frequency: Frequency of the head rotation in Hz.
    :param amplitude_rad: Half amplitude of the head rotation in radians.
    :param lerp_duration: Duration of the transition to/from the head rotation in seconds.
    """

    def __init__(
        self,
        frequency: float = 0.35,
        amplitude_rad: float = math.pi / 4,
        lerp_duration: float = 0.5,
    ) -> None:
        super().__init__()
        self.frequency = frequency
        self.amplitude_rad = amplitude_rad
        self.lerp_duration = lerp_duration

        self._lerp_start_time_s: float | None = None
        self._lerp_start_angle: float = 0.0
        self._active_start_time_s: float = 0.0

        # Logging
        self._obs_head_angle: list[float] = []
        self._obs_head_velocity: list[float] = []
        self._target_head_angle: list[float] = []
        self._target_head_velocity: list[float] = []

    def on_start(self, obs: Observation, command: MotorCommand) -> None:
        if self._lerp_start_time_s is None:
            self._lerp_start_time_s = obs.robot_state.time_s
            self._lerp_start_angle = obs.robot_state.motor_positions.get("head", 0.0)

        t = (obs.robot_state.time_s - self._lerp_start_time_s) / self.lerp_duration
        t = min(t, 1.0)
        command.target_angles["head"] = self._lerp_start_angle * (1.0 - t)

        if t >= 1.0:
            self._lerp_start_time_s = None
            self._active_start_time_s = obs.robot_state.time_s
            self.state = MoveState.ACTIVE

    def step(self, obs: Observation, command: MotorCommand) -> None:
        t = obs.robot_state.time_s - self._active_start_time_s
        head_angle = self.amplitude_rad * math.sin(2.0 * math.pi * self.frequency * t)
        command.target_angles["head"] = head_angle

        if LOGGING:
            self._obs_head_angle.append(obs.robot_state.motor_positions.get("head", 0.0))
            self._obs_head_velocity.append(obs.robot_state.motor_velocities.get("head", 0.0))
            self._target_head_angle.append(head_angle)
            self._target_head_velocity.append(2.0 * math.pi * self.frequency * self.amplitude_rad * math.cos(2.0 * math.pi * self.frequency * t))

    def on_stop(self, obs: Observation, command: MotorCommand) -> None:
        if LOGGING:
            import json
            with open("rotate_head_log.json", "w") as f:
                json.dump({
                    "obs_head_angle": self._obs_head_angle,
                    "obs_head_velocity": self._obs_head_velocity,
                    "target_head_angle": self._target_head_angle,
                    "target_head_velocity": self._target_head_velocity,
                }, f, indent=2)

        if self._lerp_start_time_s is None:
            self._lerp_start_time_s = obs.robot_state.time_s
            self._lerp_start_angle = obs.robot_state.motor_positions.get("head", 0.0)

        t = (obs.robot_state.time_s - self._lerp_start_time_s) / self.lerp_duration
        t = min(t, 1.0)
        command.target_angles["head"] = self._lerp_start_angle * (1.0 - t)

        if t >= 1.0:
            self._lerp_start_time_s = None
            self.state = MoveState.INACTIVE