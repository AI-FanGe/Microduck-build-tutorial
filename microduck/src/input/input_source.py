# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from constants import VX_MAX, VX_MAX_BACKWARD, VY_MAX, VTHETA_MAX_STATIONARY, VTHETA_MAX_MOVING


@dataclass
class UserInput:
    """Human or agent control state for one scheduler iteration."""

    active_moves: set[str] = field(default_factory=set)
    velocity: dict[str, float] = field(default_factory=lambda: {"vx": 0.0, "vy": 0.0, "vtheta": 0.0})
    show_imu: bool = False


def scale_velocity(velocity: dict[str, float]) -> dict[str, float]:
    """Map a normalized velocity command in [-1, 1] per axis to physical limits.

    Applied centrally (in the scheduler) so the limits are identical for every input
    source — keyboard, gamepad, or agent. Forward and backward have different caps, and
    rotation gets a wider range when turning in place (vx = vy = 0) than while translating.
    """
    vx = max(-1.0, min(1.0, velocity.get("vx", 0.0)))
    vy = max(-1.0, min(1.0, velocity.get("vy", 0.0)))
    vtheta = max(-1.0, min(1.0, velocity.get("vtheta", 0.0)))

    moving = abs(vx) > 1e-6 or abs(vy) > 1e-6
    vtheta_max = VTHETA_MAX_MOVING if moving else VTHETA_MAX_STATIONARY
    vx_max = VX_MAX if vx >= 0.0 else VX_MAX_BACKWARD

    return {"vx": vx * vx_max, "vy": vy * VY_MAX, "vtheta": vtheta * vtheta_max}


class InputSource(ABC):
    """Abstract interface for human or agent input. Swap keyboard for gamepad without touching the rest."""

    def start(self) -> None:
        """Start the input source (e.g., launch a background thread)."""

    def stop(self) -> None:
        """Stop the input source and release resources."""

    @abstractmethod
    def read(self) -> UserInput:
        """Return the current input state. Must be non-blocking."""