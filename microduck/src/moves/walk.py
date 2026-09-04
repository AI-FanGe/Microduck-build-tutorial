# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import onnxruntime as ort
import numpy as np

from constants import MOTOR_TO_ID, KP_DEFAULT, KP_RL, OBSERVATION_DOF_ORDER
from controller import ControllerProtocol
from imu_reader import quat_apply_inverse
from observer import Observation
from moves.move import MotorCommand, Move, MoveState


# Set to True to log motor positions and voltages during the walk move
# Note: requires to set observe_voltage = True in the Observer to log voltages
LOGGING = False

# Policy name
AGENT_NAME = "walk.onnx"


class WalkMove(Move):
    """Walk using a RL policy trained in simulation."""

    def __init__(self, controller: ControllerProtocol | None = None) -> None:
        super().__init__()
        self._controller = controller
        self._last_action = [0.0] * len(OBSERVATION_DOF_ORDER)
        self._startup_duration_s = 1.5
        self._startup_start_s: float | None = None
        self._startup_pose: dict[str, float] = {}

        # Load ONNX policy
        self._ort_session = ort.InferenceSession(f"src/agents/{AGENT_NAME}")

        self.action_scale = 1.0

        # Reference pose: read from ONNX metadata
        meta = self._ort_session.get_modelmeta().custom_metadata_map
        names = meta["joint_names"].split(",")
        positions = [float(v) for v in meta["default_joint_pos"].split(",")]
        if names != OBSERVATION_DOF_ORDER:
            raise ValueError(
                "ONNX joint_names order does not match OBSERVATION_DOF_ORDER: "
                f"{names} != {OBSERVATION_DOF_ORDER}"
            )
        self._default_pose: dict[str, float] = dict(zip(names, positions))
        self._startup_joint_names = [name for name in MOTOR_TO_ID if name in self._default_pose]

        # Detect reference phase from model input size:
        # base_obs = gyro(3) + proj_grav(3) + pos(N) + vel(N) + action(N) + cmd(3)
        # phase_obs = base_obs + phase(2)
        base_obs_size = 3 + 3 + 3 * len(OBSERVATION_DOF_ORDER) + 3
        self._use_reference_phase: bool = self._ort_session.get_inputs()[0].shape[1] > base_obs_size
        self._phase_step = 0
        self._phase_total_steps = 20

        # Safety parameters
        self._projected_gravity_z_threshold = -0.5  # Threshold for detecting a fall based on projected gravity

        # Logging
        self.position = {name: [] for name in MOTOR_TO_ID}
        self.voltage = {name: [] for name in MOTOR_TO_ID}
        
    def on_start(self, obs: Observation, command: MotorCommand) -> None:
        if self._startup_start_s is None:
            self._startup_start_s = obs.robot_state.time_s
            self._startup_pose = {
                name: obs.robot_state.motor_positions.get(name, command.target_angles.get(name, 0.0))
                for name in self._startup_joint_names
            }
            self._last_action = [0.0] * len(OBSERVATION_DOF_ORDER)
            self._phase_step = 0

        elapsed_s = max(0.0, obs.robot_state.time_s - self._startup_start_s)
        progress = min(elapsed_s / self._startup_duration_s, 1.0)
        smooth_progress = progress * progress * (3.0 - 2.0 * progress)

        for name in self._startup_joint_names:
            start = self._startup_pose[name]
            target = self._default_pose[name]
            command.target_angles[name] = start + (target - start) * smooth_progress

        if progress >= 1.0:
            if self._controller is not None:
                ids = list(MOTOR_TO_ID.values())
                self._controller.sync_write_kp(ids, [KP_RL] * len(ids))
            self._startup_start_s = None
            self._startup_pose = {}
            self.state = MoveState.ACTIVE

    def step(self, obs: Observation, command: MotorCommand) -> None:
        # Update reference phase
        if self._use_reference_phase:
            commanded_vel = np.mean([np.abs(obs.user_input.velocity["vx"]), np.abs(obs.user_input.velocity["vy"]), np.abs(obs.user_input.velocity["vtheta"])])
            if commanded_vel > 0.01:
                self._phase_step += 1
            else:
                self._phase_step = 0

        # Safety check is in body frame. The policy projected_gravity is in the
        # mounted IMU frame, where upright z is not expected to be -1.
        body_projected_gravity = obs.robot_state.projected_gravity
        if obs.robot_state.body_quat:
            body_projected_gravity = quat_apply_inverse(obs.robot_state.body_quat, [0.0, 0.0, -1.0])
        if body_projected_gravity[2] > self._projected_gravity_z_threshold:
            return
        
        # Run policy
        input_obs = self.build_observation(obs)
        ort_inputs = {self._ort_session.get_inputs()[0].name: [input_obs]}
        ort_outs = self._ort_session.run(None, ort_inputs)
        action = ort_outs[0][0]
        self._last_action = action.tolist()

        # Update command
        for i, name in enumerate(OBSERVATION_DOF_ORDER):
            command.target_angles[name] = self._default_pose[name] + action[i] * self.action_scale

        # Log positions and voltages
        if LOGGING:
            for name in MOTOR_TO_ID.keys():
                self.position[name].append(obs.robot_state.motor_positions[name])
                self.voltage[name].append(obs.robot_state.motor_voltages[name])

    def build_observation(self, obs: Observation) -> list[float]:
        """Build policy observation from robot state."""
        input_obs = []
        
        # IMU data: gyroscope and projected gravity in the policy IMU frame
        input_obs.extend(obs.robot_state.gyro)
        input_obs.extend(obs.robot_state.projected_gravity)
        
        # Motor positions
        for name in OBSERVATION_DOF_ORDER:
            input_obs.append(obs.robot_state.motor_positions[name] - self._default_pose[name])
        
        # Motor velocities
        for name in OBSERVATION_DOF_ORDER:
            input_obs.append(obs.robot_state.motor_velocities[name])
        
        # Last action
        input_obs.extend(self._last_action)

        # Command
        input_obs.append(obs.user_input.velocity["vx"])
        input_obs.append(obs.user_input.velocity["vy"])
        input_obs.append(obs.user_input.velocity["vtheta"])

        # Reference phase
        if self._use_reference_phase:
            reference_phase = (self._phase_step % self._phase_total_steps) / self._phase_total_steps * 2 * np.pi
            input_obs.append(np.cos(reference_phase))
            input_obs.append(np.sin(reference_phase))

        return input_obs

    def on_stop(self, obs: Observation, command: MotorCommand) -> None:
        self._startup_start_s = None
        self._startup_pose = {}
        if self._controller is not None:
            ids = list(MOTOR_TO_ID.values())
            self._controller.sync_write_kp(ids, [KP_DEFAULT] * len(ids))
        self.state = MoveState.INACTIVE

        # Save json logs
        if LOGGING:
            import json
            with open("walk_log.json", "w") as f:
                json.dump({
                    "position": self.position,
                    "voltage": self.voltage,
                }, f, indent=4)