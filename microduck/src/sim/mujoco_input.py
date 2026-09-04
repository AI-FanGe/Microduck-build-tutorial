# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import mujoco

from input.input_source import InputSource, UserInput

if TYPE_CHECKING:
    from mujoco import MjvOption

# GLFW key codes (no glfw import needed — values are stable)
_GLFW_KEY_UP = 265
_GLFW_KEY_DOWN = 264
_GLFW_KEY_RIGHT = 262
_GLFW_KEY_LEFT = 263

VELOCITY_STEP = 0.1
VELOCITY_MAX = 1.0


class MuJoCoInputSource(InputSource):
    """Keyboard input captured through the MuJoCo viewer GLFW callback.

    Key events are received in the viewer window instead of the terminal,
    so control works regardless of which window has OS focus.

    Pass ``key_callback`` to ``mujoco.viewer.launch_passive``.
    """

    def __init__(
        self,
        move_keys: dict[str, str],
        stop_flag_path: str = "/tmp/microduck_scheduler.stop",
    ) -> None:
        # Convert single-char keys to GLFW keycodes (letters = uppercase ASCII)
        self._keycode_to_move: dict[int, str] = {ord(k.upper()): v for k, v in move_keys.items()}
        self._move_keys_display = move_keys
        self._stop_flag_path = Path(stop_flag_path)
        self._state = UserInput()
        self._lock = threading.Lock()
        self._reset_requested = threading.Event()
        self._viewer_opt: "MjvOption | None" = None
        self._show_torque = False

    def set_viewer_opt(self, opt: "MjvOption") -> None:
        """Bind the viewer MjvOption so [i] can toggle the IMU site frame."""
        self._viewer_opt = opt

    @property
    def show_torque(self) -> bool:
        with self._lock:
            return self._show_torque

    def consume_reset(self) -> bool:
        """Return True (and clear the flag) if a reset was requested since last call."""
        return self._reset_requested.is_set() and not self._reset_requested.clear() or False

    def start(self) -> None:
        print("MuJoCo viewer keyboard controls:")
        for char, name in self._move_keys_display.items():
            print(f"  [{char}]      toggle move '{name}'")
        print("  [i]       toggle IMU frame + terminal display")
        print("  [t]       toggle torque sum display")
        print("  [arrows]  vx (up/down), vtheta (left/right)")
        print("  [x]       reset velocity")
        print("  [r]       reset robot to initial pose")
        print("  [q]       quit")

    def stop(self) -> None:
        pass

    def read(self) -> UserInput:
        with self._lock:
            return UserInput(
                active_moves=set(self._state.active_moves),
                velocity=dict(self._state.velocity),
                show_imu=self._state.show_imu,
            )

    def key_callback(self, keycode: int) -> None:
        if keycode in self._keycode_to_move:
            move_name = self._keycode_to_move[keycode]
            with self._lock:
                if move_name in self._state.active_moves:
                    self._state.active_moves.discard(move_name)
                    print(f"Move '{move_name}' disabled")
                else:
                    self._state.active_moves.add(move_name)
                    print(f"Move '{move_name}' enabled")

        elif keycode == ord("X"):
            with self._lock:
                self._state.velocity = {"vx": 0.0, "vy": 0.0, "vtheta": 0.0}
            print("Velocity reset to zero")

        elif keycode == ord("R"):
            self._reset_requested.set()
            print("Robot reset to initial pose")

        elif keycode == ord("I"):
            with self._lock:
                self._state.show_imu = not self._state.show_imu
                show = self._state.show_imu
            if self._viewer_opt is not None:
                self._viewer_opt.frame = (
                    mujoco.mjtFrame.mjFRAME_SITE if show else mujoco.mjtFrame.mjFRAME_NONE
                )
            status = "enabled" if show else "disabled"
            print(f"IMU display {status}")

        elif keycode == ord("T"):
            with self._lock:
                self._show_torque = not self._show_torque
                show = self._show_torque
            status = "enabled" if show else "disabled"
            print(f"Torque sum display {status}")

        elif keycode == ord("Q"):
            self._stop_flag_path.write_text("stop\n", encoding="ascii")
            print("Stop requested")

        elif keycode == _GLFW_KEY_UP:
            self._adjust_velocity("vx", +VELOCITY_STEP)
        elif keycode == _GLFW_KEY_DOWN:
            self._adjust_velocity("vx", -VELOCITY_STEP)
        elif keycode == _GLFW_KEY_RIGHT:
            self._adjust_velocity("vtheta", +VELOCITY_STEP)
        elif keycode == _GLFW_KEY_LEFT:
            self._adjust_velocity("vtheta", -VELOCITY_STEP)

    def _adjust_velocity(self, axis: str, delta: float) -> None:
        with self._lock:
            v = self._state.velocity
            v[axis] = max(-VELOCITY_MAX, min(VELOCITY_MAX, v.get(axis, 0.0) + delta))
        print(f"{axis}={self._state.velocity[axis]:.1f}")