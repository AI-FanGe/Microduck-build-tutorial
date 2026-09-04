# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import os
import sys
import select
import termios
import tty
import threading
from pathlib import Path

from input.input_source import InputSource, UserInput

VELOCITY_STEP = 0.1
VELOCITY_MAX = 1.0

_ESCAPE = "\x1b"
_ARROW_UP = "\x1b[A"
_ARROW_DOWN = "\x1b[B"
_ARROW_RIGHT = "\x1b[C"
_ARROW_LEFT = "\x1b[D"


class KeyboardInputSource(InputSource):
    """Read keyboard input from a raw terminal in a background daemon thread.

    Args:
        move_keys: mapping from key character to move name, e.g. {"h": "head", "w": "walk"}.
        stop_flag_path: path to the stop flag file polled by the scheduler.
    """

    def __init__(
        self,
        move_keys: dict[str, str],
        stop_flag_path: str = "/tmp/microduck_scheduler.stop",
    ) -> None:
        self._move_keys = move_keys
        self._stop_flag_path = Path(stop_flag_path)
        self._state = UserInput()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._old_settings: list | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self._print_help()

    def stop(self) -> None:
        self._running = False
        self._restore_terminal()

    def read(self) -> UserInput:
        with self._lock:
            return UserInput(
                active_moves=set(self._state.active_moves),
                velocity=dict(self._state.velocity),
                show_imu=self._state.show_imu,
            )

    # ------------------------------------------------------------------
    # Internal

    def _read_loop(self) -> None:
        fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while self._running:
                # Use select with a timeout so the loop can notice _running=False.
                if not select.select([sys.stdin], [], [], 0.1)[0]:
                    continue
                key = self._read_key(fd)
                if key:
                    self._handle_key(key)
        finally:
            self._restore_terminal()

    def _read_key(self, fd: int) -> str:
        ch = os.read(fd, 1).decode("utf-8", errors="replace")
        if ch == _ESCAPE:
            # Try to read the CSI sequence that follows (e.g., "[A" for arrow up).
            if select.select([sys.stdin], [], [], 0.05)[0]:
                rest = os.read(fd, 2).decode("utf-8", errors="replace")
                return ch + rest
        return ch

    def _handle_key(self, key: str) -> None:
        if key in self._move_keys:
            move_name = self._move_keys[key]
            with self._lock:
                if move_name in self._state.active_moves:
                    self._state.active_moves.discard(move_name)
                    print(f"Move '{move_name}' disabled", end="\r\n", flush=True)
                else:
                    self._state.active_moves.add(move_name)
                    print(f"Move '{move_name}' enabled", end="\r\n", flush=True)
        elif key == "x":
            with self._lock:
                self._state.velocity = {"vx": 0.0, "vy": 0.0, "vtheta": 0.0}
            print("Velocity reset to zero", end="\r\n", flush=True)
        elif key in ("q", "\x03"):  # q or Ctrl+C
            self._stop_flag_path.write_text("stop\n", encoding="ascii")
            print("Stop requested", end="\r\n", flush=True)
        elif key == "i":
            with self._lock:
                self._state.show_imu = not self._state.show_imu
            status = "enabled" if self._state.show_imu else "disabled"
            print(f"IMU display {status}", end="\r\n", flush=True)
        elif key == _ARROW_UP:
            self._adjust_velocity("vx", +VELOCITY_STEP)
        elif key == _ARROW_DOWN:
            self._adjust_velocity("vx", -VELOCITY_STEP)
        elif key == _ARROW_RIGHT:
            self._adjust_velocity("vtheta", -VELOCITY_STEP)
        elif key == _ARROW_LEFT:
            self._adjust_velocity("vtheta", +VELOCITY_STEP)

    def _adjust_velocity(self, axis: str, delta: float) -> None:
        with self._lock:
            v = self._state.velocity
            v[axis] = max(-VELOCITY_MAX, min(VELOCITY_MAX, v[axis] + delta))
        print(f"{axis}={self._state.velocity[axis]:.1f}", end="\r\n", flush=True)

    def _restore_terminal(self) -> None:
        if self._old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)
            except Exception:
                pass
            self._old_settings = None

    def _print_help(self) -> None:
        lines = [
            "Keyboard controls:",
            *(f"  [{key}]      toggle move '{name}'" for key, name in self._move_keys.items()),
            "  [i]      toggle IMU/gyro display",
            "  [arrows] vx (up/down), vtheta (left/right)",
            "  [x]      reset velocity to zero",
            "  [q]      stop scheduler",
        ]
        for line in lines:
            print(line, end="\r\n", flush=True)