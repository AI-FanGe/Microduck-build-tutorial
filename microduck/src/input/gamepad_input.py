# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import os
import glob
import struct
import select
import threading
from pathlib import Path

from input.input_source import InputSource, UserInput

# Stick fraction below which the axis is treated as centered (drift rejection).
DEADZONE = 0.12

# Sign per velocity axis, so the mapping can be flipped without touching the logic.
# Convention: stick up -> +vx (forward), stick left -> +vy (left), right stick left -> +vtheta (CCW).
VX_SIGN = -1.0      # left stick Y: the joystick API reports up as negative
VY_SIGN = -1.0      # left stick X: reports right as positive
VTHETA_SIGN = -1.0  # right stick X: reports right as positive

# Linux joystick API (Documentation/input/joydev/joystick-api.rst).
# Each event is: __u32 time (ms), __s16 value, __u8 type, __u8 number.
# Public so gamepad_daemon can reuse the same parser.
JS_EVENT = struct.Struct("=IhBB")
JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80  # ORed into the type for synthetic startup events (ignored)
_AXIS_FULL_SCALE = 32767.0

# Standard xpad axis numbers.
_AXIS_LX = 0   # left stick X
_AXIS_LY = 1   # left stick Y
_AXIS_RX = 2   # right stick X (horizontal)

# Button numbers. A, B and START are verified on an Xbox controller over Bluetooth
# (HID layout); the others follow the common layout and may differ on your pad — check
# with `jstest /dev/input/js0` if needed.
XBOX_BUTTONS = {
    "A": 0, "B": 1, "X": 3, "Y": 4,
    "LB": 6, "RB": 7,
    "BACK": 10, "START": 11, "GUIDE": 12,
    "L3": 13, "R3": 14,
}

# Trigger axes and the value above which they are considered pressed. 
TRIGGER_AXES = {"LT": 4, "RT": 5}
TRIGGER_PRESS_THRESHOLD = 0


def find_gamepad_path() -> str | None:
    """Return the first joystick device path (/dev/input/js*), or None."""
    paths = sorted(glob.glob("/dev/input/js*"))
    return paths[0] if paths else None


class GamepadInputSource(InputSource):
    """Read an Xbox (or compatible) gamepad via the Linux joystick API in a daemon thread.

    Left stick drives (vx, vy), right stick drives vtheta. Buttons toggle moves.
    Designed as a drop-in replacement for KeyboardInputSource. Zero dependencies:
    reads raw 8-byte events from /dev/input/js* with struct.

    Args:
        button_moves: mapping from Xbox button name to move name, e.g. {"A": "walk"}.
        stop_button: button name that requests scheduler shutdown (writes the stop flag).
        imu_button: button name that toggles the IMU display, or None to disable.
        device_path: explicit /dev/input/jsX path, or None to auto-detect.
        stop_flag_path: path to the stop flag file polled by the scheduler.
    """

    def __init__(
        self,
        button_moves: dict[str, str] | None = None,
        stop_button: str = "B",
        imu_button: str | None = "BACK",
        device_path: str | None = None,
        stop_flag_path: str = "/tmp/microduck_scheduler.stop",
    ) -> None:
        self._button_moves = button_moves if button_moves is not None else {"A": "walk"}
        self._stop_flag_path = Path(stop_flag_path)
        self._device_path = device_path

        # Resolve button names to joystick button numbers once, up front.
        self._move_numbers = {self._number(name): move for name, move in self._button_moves.items()}
        self._stop_number = self._number(stop_button)
        self._imu_number = self._number(imu_button) if imu_button else None
        self._name_by_number = {v: k for k, v in XBOX_BUTTONS.items()}

        self._state = UserInput()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._fd: int | None = None

    @staticmethod
    def _number(name: str) -> int:
        try:
            return XBOX_BUTTONS[name.upper()]
        except KeyError as exc:
            raise ValueError(
                f"Unknown gamepad button name: {name!r}. Known: {sorted(XBOX_BUTTONS)}"
            ) from exc

    def start(self) -> None:
        path = self._device_path or find_gamepad_path()
        if path is None:
            raise RuntimeError(
                "No gamepad found. Pair the controller (bluetoothctl) and check /dev/input/js*."
            )
        self._fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        print(f"Gamepad detected: {path}", end="\r\n", flush=True)
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self._print_help()

    def stop(self) -> None:
        self._running = False
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

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
        fd = self._fd
        assert fd is not None
        while self._running:
            # select with a timeout so the loop can notice _running=False and exit cleanly.
            if not select.select([fd], [], [], 0.1)[0]:
                continue
            try:
                data = os.read(fd, JS_EVENT.size * 32)
            except BlockingIOError:
                continue
            except OSError:
                self._on_disconnect()
                break
            if not data:
                self._on_disconnect()
                break
            for offset in range(0, len(data) - JS_EVENT.size + 1, JS_EVENT.size):
                _, value, ev_type, number = JS_EVENT.unpack_from(data, offset)
                if ev_type & JS_EVENT_INIT:
                    continue  # ignore synthetic startup snapshots
                if ev_type == JS_EVENT_AXIS:
                    self._handle_axis(number, value)
                elif ev_type == JS_EVENT_BUTTON and value == 1:
                    self._handle_button(number)

    def _on_disconnect(self) -> None:
        # Stop commanding motion on the last (now stale) stick values, otherwise the
        # robot would keep moving on the velocity it had when the controller dropped.
        with self._lock:
            self._state.velocity = {"vx": 0.0, "vy": 0.0, "vtheta": 0.0}
        print("Gamepad disconnected (velocity zeroed)", end="\r\n", flush=True)

    def _normalize(self, value: int) -> float:
        norm = max(-1.0, min(1.0, value / _AXIS_FULL_SCALE))
        return 0.0 if abs(norm) < DEADZONE else norm

    def _handle_axis(self, number: int, value: int) -> None:
        if number == _AXIS_LY:
            self._set_velocity("vx", VX_SIGN * self._normalize(value))
        elif number == _AXIS_LX:
            self._set_velocity("vy", VY_SIGN * self._normalize(value))
        elif number == _AXIS_RX:
            self._set_velocity("vtheta", VTHETA_SIGN * self._normalize(value))

    def _set_velocity(self, axis: str, norm: float) -> None:
        # Emit a normalized command in [-1, 1]; scale_velocity() applies the physical limits.
        with self._lock:
            self._state.velocity[axis] = max(-1.0, min(1.0, norm))

    def _handle_button(self, number: int) -> None:
        if number in self._move_numbers:
            move_name = self._move_numbers[number]
            with self._lock:
                if move_name in self._state.active_moves:
                    self._state.active_moves.discard(move_name)
                    print(f"Move '{move_name}' disabled", end="\r\n", flush=True)
                else:
                    self._state.active_moves.add(move_name)
                    print(f"Move '{move_name}' enabled", end="\r\n", flush=True)
        elif number == self._stop_number:
            self._stop_flag_path.write_text("stop\n", encoding="ascii")
            print("Stop requested", end="\r\n", flush=True)
        elif self._imu_number is not None and number == self._imu_number:
            with self._lock:
                self._state.show_imu = not self._state.show_imu
            status = "enabled" if self._state.show_imu else "disabled"
            print(f"IMU display {status}", end="\r\n", flush=True)

    def _print_help(self) -> None:
        def btn(number: int) -> str:
            return self._name_by_number.get(number, str(number))

        lines = [
            "Gamepad controls:",
            "  left stick   vx (up/down), vy (left/right)",
            "  right stick  vtheta",
            *(f"  [{btn(number)}]  toggle move '{move}'" for number, move in self._move_numbers.items()),
        ]
        if self._imu_number is not None:
            lines.append(f"  [{btn(self._imu_number)}]  toggle IMU/gyro display")
        lines.append(f"  [{btn(self._stop_number)}]  stop scheduler")
        for line in lines:
            print(line, end="\r\n", flush=True)