# Copyright 2026 Marc Duclusaud

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:

#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from mjlab.entity import Entity
from mjlab.envs.manager_based_rl_env import ManagerBasedRlEnv
from mjlab.managers.curriculum_manager import CurriculumTermCfg
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.utils.lab_api.math import quat_apply, quat_apply_inverse
from mjlab.tasks.velocity.mdp.velocity_command import (
    UniformVelocityCommand,
    UniformVelocityCommandCfg,
)


############################ COMMANDS #############################

class UniformVelocityCommandWithRotation(UniformVelocityCommand):
    """Extends UniformVelocityCommand with a `rel_rotation_envs` fraction.

    Rotation-only environments receive zero linear velocity and a non-zero angular 
    velocity in [`cfg.rotation_env_ang_vel_range[0]`, `cfg.rotation_env_ang_vel_range[1]`], 
    with an absolute value of at least `cfg.rotation_min_ang_vel`.
    """

    cfg: "UniformVelocityCommandWithRotationCfg"

    def __init__(self, cfg: "UniformVelocityCommandWithRotationCfg", env: ManagerBasedRlEnv):
        super().__init__(cfg, env)
        self.is_rotation_env = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

    def _resample_command(self, env_ids: torch.Tensor) -> None:
        super()._resample_command(env_ids)

        rel_rotation_envs = getattr(self.cfg, "rel_rotation_envs", 0.0)

        r = torch.empty(len(env_ids), device=self.device)
        self.is_rotation_env[env_ids] = r.uniform_(0.0, 1.0) <= rel_rotation_envs

        rot_ids = env_ids[self.is_rotation_env[env_ids]]
        if len(rot_ids) == 0:
            return

        self.vel_command_b[rot_ids, 0] = 0.0
        self.vel_command_b[rot_ids, 1] = 0.0

        # Sample angular velocity from the rotation-specific range if provided,
        # otherwise reuse what the parent sampled from cfg.ranges.ang_vel_z.
        if self.cfg.rotation_env_ang_vel_range is not None:
            ang = torch.empty(len(rot_ids), device=self.device).uniform_(
                *self.cfg.rotation_env_ang_vel_range
            )
        else:
            ang = self.vel_command_b[rot_ids, 2]

        # Ensure non-zero angular velocity.
        min_abs_ang = self.cfg.rotation_min_ang_vel
        too_small = ang.abs() < min_abs_ang
        if too_small.any():
            signs = torch.where(
                torch.rand(too_small.sum(), device=self.device) > 0.5,
                torch.ones(too_small.sum(), device=self.device),
                -torch.ones(too_small.sum(), device=self.device),
            )
            ang[too_small] = signs * min_abs_ang
        self.vel_command_b[rot_ids, 2] = ang

@dataclass(kw_only=True)
class UniformVelocityCommandWithRotationCfg(UniformVelocityCommandCfg):
    """Configuration for UniformVelocityCommandWithRotation."""

    rel_rotation_envs: float = 0.0
    """Fraction of environments that receive pure-rotation commands
    (zero linear velocity, non-zero angular velocity)."""

    rotation_min_ang_vel: float = 0.3
    """Minimum absolute angular velocity assigned to rotation-only environments."""

    rotation_env_ang_vel_range: tuple[float, float] | None = None
    """Angular velocity range for rotation-only environments.
    If None, uses cfg.ranges.ang_vel_z (same range as normal environments)."""

    def build(self, env: ManagerBasedRlEnv) -> UniformVelocityCommandWithRotation:
        return UniformVelocityCommandWithRotation(self, env)
    

############################ REWARDS ##############################

_DEFAULT_ASSET_CFG = SceneEntityCfg("robot")


def _mount_quat_tensor(
    env: ManagerBasedRlEnv,
    mount_quat: tuple[float, float, float, float],
    dtype: torch.dtype,
) -> torch.Tensor:
    """Return a per-env quaternion tensor for a fixed physical IMU mount."""
    q = torch.tensor(mount_quat, dtype=dtype, device=env.device)
    q = q / q.norm().clamp(min=1e-8)
    return q.unsqueeze(0).expand(env.num_envs, -1)


def mounted_projected_gravity(
    env: ManagerBasedRlEnv,
    mount_quat: tuple[float, float, float, float],
    asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
    """Projected gravity as seen in the physically mounted IMU frame.

    The measured GY-BNO080 mount is modeled at the observation layer because the
    policy uses generated observation terms, not the XML IMU site directly.
    """
    asset: Entity = env.scene[asset_cfg.name]
    gravity_b = asset.data.projected_gravity_b
    q = _mount_quat_tensor(env, mount_quat, gravity_b.dtype)
    return quat_apply(q, gravity_b)


def mounted_base_ang_vel(
    env: ManagerBasedRlEnv,
    mount_quat: tuple[float, float, float, float],
    asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
    """Base angular velocity as seen in the same mounted IMU frame."""
    asset: Entity = env.scene[asset_cfg.name]
    ang_vel_b = asset.data.root_link_ang_vel_b
    q = _mount_quat_tensor(env, mount_quat, ang_vel_b.dtype)
    return quat_apply(q, ang_vel_b)


def mounted_body_projected_gravity(
    env: ManagerBasedRlEnv,
    mount_quat: tuple[float, float, float, float],
    asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
    """Projected up-vector in the frame of a physical IMU mounted on a body.

    Deployment computes quat_apply_inverse(real_imu_quat, [0, 0, 1]). MjLab's
    gravity vector points downward, so negate it here to keep train/deploy
    observation signs identical.
    """
    asset: Entity = env.scene[asset_cfg.name]
    if asset_cfg.body_ids:
        body_quat_w = asset.data.body_link_quat_w[:, asset_cfg.body_ids, :].squeeze(1)
        gravity_b = quat_apply_inverse(body_quat_w, asset.data.gravity_vec_w)
    else:
        gravity_b = asset.data.projected_gravity_b
    gravity_b = -gravity_b
    q = _mount_quat_tensor(env, mount_quat, gravity_b.dtype)
    return quat_apply(q, gravity_b)


def mounted_body_ang_vel(
    env: ManagerBasedRlEnv,
    mount_quat: tuple[float, float, float, float],
    asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
    """Angular velocity in the frame of a physical IMU mounted on a body."""
    asset: Entity = env.scene[asset_cfg.name]
    if asset_cfg.body_ids:
        body_id = asset_cfg.body_ids[0]
        body_quat_w = asset.data.body_link_quat_w[:, body_id, :]
        ang_vel_w = asset.data.body_link_ang_vel_w[:, body_id, :]
        ang_vel_b = quat_apply_inverse(body_quat_w, ang_vel_w)
    else:
        ang_vel_b = asset.data.root_link_ang_vel_b
    q = _mount_quat_tensor(env, mount_quat, ang_vel_b.dtype)
    return quat_apply(q, ang_vel_b)


def action_target_limits_l2(
    env: ManagerBasedRlEnv,
    action_name: str = "joint_pos",
    overshoot: float = 0.3,
) -> torch.Tensor:
    """Penalize command targets beyond hard joint limits.

    This mirrors the existing Microduck training-side regularizer: discourage
    simulator-only overdrive without clipping deployment actions.
    """
    term = env.action_manager.get_term(action_name)
    target = term.raw_action * term.scale + term.offset
    hard = env.scene["robot"].data.joint_pos_limits[:, term.target_ids]
    lo = hard[..., 0] - overshoot
    hi = hard[..., 1] + overshoot
    over = (target - hi).clip(min=0.0) + (lo - target).clip(min=0.0)
    return torch.sum(over, dim=-1)


class upright:
    """Reward for keeping the base at a target pitch orientation.

    Penalizes deviation from a given pitch angle (in radians) rather than
    always rewarding a perfectly vertical posture.

    Args:
        std: Standard deviation of the Gaussian kernel (controls reward sharpness).
        pitch: Target pitch angle in radians. 0.0 = perfectly upright.
               Positive values mean leaning forward.
        asset_cfg: Scene entity configuration for the robot body to track.
    """

    def __init__(self, cfg: RewardTermCfg, env: ManagerBasedRlEnv):
        pass

    def __call__(
        self,
        env: ManagerBasedRlEnv,
        std: float,
        pitch: float = 0.0,
        asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
    ) -> torch.Tensor:
        asset: Entity = env.scene[asset_cfg.name]

        if asset_cfg.body_ids:
            body_quat_w = asset.data.body_link_quat_w[:, asset_cfg.body_ids, :].squeeze(1)
        else:
            body_quat_w = asset.data.root_link_quat_w

        gravity_w = asset.data.gravity_vec_w
        projected_gravity_b = quat_apply_inverse(body_quat_w, gravity_w)

        # Normalize to unit vector so the error is scale-independent.
        gravity_norm = projected_gravity_b.norm(dim=-1, keepdim=True).clamp(min=1e-6)
        projected_gravity_b_unit = projected_gravity_b / gravity_norm

        # At pitch angle θ, the normalised gravity unit vector in body frame has
        # x = sin(θ), y = 0 (assuming flat ground, no roll, no terrain slope).
        target_gx = math.sin(pitch)
        xy_error = (
            torch.square(projected_gravity_b_unit[:, 0] - target_gx)
            + torch.square(projected_gravity_b_unit[:, 1])
        )
        return torch.exp(-xy_error / std**2)

    def reset(self, env_ids: torch.Tensor) -> None:
        del env_ids  # Unused.


def feet_distance_penalty(
    env: ManagerBasedRlEnv,
    min_dist: float,
    asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
    """Penalize the feet getting too close to each other in the horizontal plane.

    Discourages the robot from stepping on its own feet by adding a smooth,
    anticipatory cost as soon as the horizontal distance between the two foot
    sites drops below ``min_dist``. Above the threshold the cost is zero.

    Returns ``clamp(min_dist - d, min=0)`` per env (use with a negative weight),
    where ``d`` is the horizontal (xy) distance between the two foot sites.

    Args:
        min_dist: Minimum desired horizontal distance between feet, in meters.
        asset_cfg: Scene entity configuration whose ``site_names`` select exactly
            the two foot sites.
    """
    asset: Entity = env.scene[asset_cfg.name]
    foot_pos_xy = asset.data.site_pos_w[:, asset_cfg.site_ids, :2]  # [B, 2, 2]
    dist = torch.norm(foot_pos_xy[:, 0] - foot_pos_xy[:, 1], dim=-1)  # [B]
    return torch.clamp(min_dist - dist, min=0.0)


def no_stepping_penalty(
    env: ManagerBasedRlEnv,
    sensor_name: str,
    command_name: str = "twist",
    command_threshold: float = 0.01,
) -> torch.Tensor:
    """
    Penalizes feet in the air when the commanded speed is below threshold.
    Discourages marching in place when the robot should stand still.
    Returns the count of airborne feet per environment (use with a negative weight).
    """
    command = env.command_manager.get_command(command_name)  # (N, 3)
    cmd_speed = torch.norm(command[:, :2], dim=-1) + torch.abs(command[:, 2])
    below_threshold = cmd_speed < command_threshold

    sensor = env.scene.sensors[sensor_name]
    found = sensor.data.found  # (N, num_feet) or (N, num_feet, num_slots)
    if found.dim() == 3:
        found = found.any(dim=-1)  # (N, num_feet)
    in_air = ~found.bool()

    return in_air.float().sum(dim=-1) * below_threshold.float()


########################## CURRICULUM #############################

class step_based_staged_curriculum:
    """
    Curriculum based on step count stages. Each stage is applied once when
    env.common_step_counter reaches the stage's step threshold.

    Stage definitions example:
    stages = [
        {
            "name": "stage 1",
            "step": 10_000 * 24,
            "apply": lambda env: env.reward_manager.get_term_cfg("term_name").weight = 1.0,
        },
        ...
    ]
    """

    def __init__(self, cfg: CurriculumTermCfg, env: ManagerBasedRlEnv):
        self.current_stage = 0

    def __call__(
        self,
        env: ManagerBasedRlEnv,
        env_ids: torch.Tensor,
        stages: list[dict],
    ) -> dict[str, torch.Tensor]:
        del env_ids
        if (
            self.current_stage < len(stages)
            and env.common_step_counter >= stages[self.current_stage]["step"]
        ):
            stage = stages[self.current_stage]
            print(
                f"Curriculum stage {self.current_stage + 1}: {stage['name']} at step {env.common_step_counter}"
            )
            stage["apply"](env)
            self.current_stage += 1

        return {"stage": self.current_stage}

class reward_based_staged_curriculum:
    """
    Curriculum based on stages ending while a reward component gets its mean 
    episode reward accross all environments above a threshold.

    Stage definitions example:
    stages = [
        {
            "name": "stage 1",
            "reward_term_name": "term_name",
            "threshold": 0.5,
            "apply": lambda env: env.reward_manager.get_term_cfg("term_name").weight = 1.0,
        },
        ...
    ]
    """

    def __init__(self, cfg: CurriculumTermCfg, env: ManagerBasedRlEnv):
        self.rewards = torch.zeros(env.num_envs, device=env.device)
        self.current_stage = 0
        self.stage_first_step = 0
        
    def __call__(
        self,
        env: ManagerBasedRlEnv,
        env_ids: torch.Tensor,
        stages: list[dict],
    ) -> dict[str, torch.Tensor]:
        self.rewards[env_ids] = (
            env.reward_manager._episode_sums[stages[self.current_stage]["reward_term_name"]][env_ids]
            / env.max_episode_length_s
        )
        mean_reward = self.rewards.mean().item()

        if (
            self.current_stage < len(stages)
            and mean_reward >= stages[self.current_stage]["threshold"]
            and env.common_step_counter >= self.stage_first_step + 100 * 24
        ):
            stage = stages[self.current_stage]
            print(
                f"Curriculum stage {self.current_stage + 1}: {stage['name']} at step {env.common_step_counter} (mean episode reward: {mean_reward:.4f})"
            )
            stage["apply"](env)
            self.current_stage += 1
            self.stage_first_step = env.common_step_counter
            self.rewards.zero_()  # Reset rewards to avoid immediately triggering the next stage

        return {"stage": self.current_stage}

class reward_based_curriculum:
    """
    Curriculum based on the mean episode reward of a specific term accross all environments.
    Once the mean reward across envs exceeds a threshold, a new curriculum stage is applied.
    """

    def __init__(self, cfg: CurriculumTermCfg, env: ManagerBasedRlEnv):
        self.rewards = torch.zeros(env.num_envs, device=env.device)
        self.current_stage = 0
        self.stage_first_step = 0
        
    def __call__(
        self,
        env: ManagerBasedRlEnv,
        env_ids: torch.Tensor,
        reward_term_name: str,
        stages: list[dict],
    ) -> dict[str, torch.Tensor]:
        self.rewards[env_ids] = (
            env.reward_manager._episode_sums[reward_term_name][env_ids]
            / env.max_episode_length_s
        )
        mean_reward = self.rewards.mean().item()

        if (
            self.current_stage < len(stages)
            and mean_reward >= stages[self.current_stage]["threshold"]
            and env.common_step_counter >= self.stage_first_step + 100 * 24
        ):
            stage = stages[self.current_stage]
            print(
                f"Curriculum stage {self.current_stage + 1}: {stage['name']} at step {env.common_step_counter} (mean episode reward: {mean_reward:.4f})"
            )
            stage["apply"](env)
            self.current_stage += 1
            self.stage_first_step = env.common_step_counter
        
        return {"stage": self.current_stage}

def set_command_velocity(
        env, 
        lin_vel_x=None, 
        lin_vel_y=None, 
        ang_vel_z=None, 
        rotation_env_ang_vel_z=None,
) -> None:
    """
    Helper function to set the command velocity parameters in the environment.
    """
    cmd = env.command_manager.get_term_cfg("twist")
    if lin_vel_x is not None:
        cmd.ranges.lin_vel_x = lin_vel_x
    if lin_vel_y is not None:
        cmd.ranges.lin_vel_y = lin_vel_y
    if ang_vel_z is not None:
        cmd.ranges.ang_vel_z = ang_vel_z
    if rotation_env_ang_vel_z is not None:
        cmd.rotation_env_ang_vel_range = rotation_env_ang_vel_z

def set_stepping_parameters(
    env,
    air_time_weight: float | None = None,
    no_stepping_penalty_weight: float | None = None,
    rel_standing_envs: float | None = None,
    rel_rotation_envs: float | None = None,
) -> None:
    """
    Helper function to set stepping/standing curriculum parameters.
    """
    if air_time_weight is not None:
        env.reward_manager.get_term_cfg("air_time").weight = air_time_weight
    if no_stepping_penalty_weight is not None:
        env.reward_manager.get_term_cfg("no_stepping").weight = no_stepping_penalty_weight
    if rel_standing_envs is not None:
        env.command_manager.get_term_cfg("twist").rel_standing_envs = rel_standing_envs
    if rel_rotation_envs is not None:
        env.command_manager.get_term_cfg("twist").rel_rotation_envs = rel_rotation_envs

def set_push_parameters(
    env,
    velocity_range: dict[str, tuple[float, float]] | None = None,
    interval_range: tuple[float, float] | None = None,
) -> None:
    """
    Helper function to set push event parameters.
    Returns a dict of the current (post-update) values for wandb logging.
    """
    push_event_cfg = env.event_manager.get_term_cfg("push_robot")
    if velocity_range is not None:
        push_event_cfg.params["velocity_range"] = velocity_range
    if interval_range is not None:
        push_event_cfg.params["interval_range"] = interval_range

def penalize_stepping_while_standing(
    env: ManagerBasedRlEnv,
    air_time_weight: float,
    no_stepping_penalty_weight: float,
) -> torch.Tensor:
    """
    Updating the air_time and no_stepping reward weights to penalize stepping while standing.
    """
    env.reward_manager.get_term_cfg("air_time").weight = air_time_weight
    env.reward_manager.get_term_cfg("no_stepping").weight = no_stepping_penalty_weight

def stepping_curriculum(
    env: ManagerBasedRlEnv,
    env_ids: torch.Tensor,
    air_time_weight: float,
    no_stepping_penalty_weight: float,
    rel_standing_envs: float = 0.0,
    rel_rotation_envs: float = 0.0,
    step: int = 10000 * 24,
) -> dict[str, torch.Tensor]:
    """
    Updating the air_time and no_stepping reward weights to penalize stepping while standing
    after a certain number of iterations.
    """
    del env_ids  # Unused.

    if env.common_step_counter >= step: 
        env.reward_manager.get_term_cfg("air_time").weight = air_time_weight
        env.reward_manager.get_term_cfg("no_stepping").weight = no_stepping_penalty_weight
        env.command_manager.get_term_cfg("twist").rel_standing_envs = rel_standing_envs
        env.command_manager.get_term_cfg("twist").rel_rotation_envs = rel_rotation_envs

    return {
        "air_time_weight": torch.tensor(env.reward_manager.get_term_cfg("air_time").weight),
        "no_stepping_penalty_weight": torch.tensor(env.reward_manager.get_term_cfg("no_stepping").weight),
        "rel_standing_envs": torch.tensor(env.command_manager.get_term_cfg("twist").rel_standing_envs),
        "rel_rotation_envs": torch.tensor(env.command_manager.get_term_cfg("twist").rel_rotation_envs),
    }
