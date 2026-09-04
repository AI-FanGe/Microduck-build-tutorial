#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Microduck MuJoCo + Pi Zero motor direction checker.

Run from the local computer, not from the Pi Zero:

    PYTHONPATH=src uv run --group sim src/debug/mujoco_motor_direction_check.py --host microduck

The script opens a local MuJoCo viewer and a Tk slider window. Moving one slider
sends the same joint target to MuJoCo and to the robot over SSH. The `mouth`
servo has no MJCF joint, so its slider is sent to the real robot only.
"""

from __future__ import annotations

import argparse
import json
import math
import selectors
import shlex
import subprocess
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer

from constants import KP_DEFAULT, MOTOR_OFFSET, MOTOR_SIGN, MOTOR_TO_ID, NEUTRAL_POSE

try:
    import tkinter as tk
except ImportError as exc:  # pragma: no cover - depends on local desktop setup
    raise SystemExit("tkinter is required for the slider UI.") from exc


MICRODUCK_REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = MICRODUCK_REPO_ROOT.parent
DEFAULT_MJCF = (
    WORKSPACE_ROOT
    / "mjlab_microduck/src/mjlab_microduck/robot/microduck/scene.xml"
)
FALLBACK_MJCF = MICRODUCK_REPO_ROOT / "src/model/mjcf/scene.xml"
DEFAULT_ROOT_Z = 0.12
DEFAULT_SERIAL_PORT = "auto"
STARTUP_RAMP_SECONDS = 2.0

HOME_POSE: dict[str, float] = dict(NEUTRAL_POSE)
MOTOR_ONLY_RANGE_DEG: dict[str, tuple[float, float]] = {}


REMOTE_CODE_TEMPLATE = r"""
import json
import glob
import os
import sys
import time

from rustypot import Xl330PyController

MOTOR_SERIAL_PORT = __MOTOR_SERIAL_PORT__
MOTOR_TO_ID = __MOTOR_TO_ID__
MOTOR_SIGN = __MOTOR_SIGN__
MOTOR_OFFSET = __MOTOR_OFFSET__
HOME_POSE = __HOME_POSE__
KP_DEFAULT = __KP_DEFAULT__
STARTUP_RAMP_SECONDS = __STARTUP_RAMP_SECONDS__


def resolve_serial_port(serial_port):
    if serial_port != "auto":
        return serial_port
    candidates = (
        sorted(glob.glob("/dev/serial/by-id/usb-ROBOTIS_OpenRB-150_*"))
        + ["/dev/ttyACM0", "/dev/serial0", "/dev/ttyAMA0", "/dev/ttyS0"]
    )
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError("No Dynamixel serial port found. Pass --serial-port explicitly.")


MOTOR_SERIAL_PORT = resolve_serial_port(MOTOR_SERIAL_PORT)
print("REMOTE_SERIAL_PORT {}".format(MOTOR_SERIAL_PORT), flush=True)
controller = Xl330PyController(serial_port=MOTOR_SERIAL_PORT, baudrate=1_000_000, timeout=0.1)
all_ids = list(MOTOR_TO_ID.values())
id_to_name = {motor_id: name for name, motor_id in MOTOR_TO_ID.items()}
id_to_sign = {motor_id: float(MOTOR_SIGN.get(name, 1.0)) for name, motor_id in MOTOR_TO_ID.items()}
id_to_offset = {motor_id: float(MOTOR_OFFSET.get(name, 0.0)) for name, motor_id in MOTOR_TO_ID.items()}


def write_named_targets(targets):
    ids = []
    positions = []
    for name, target in targets.items():
        if name not in MOTOR_TO_ID:
            continue
        motor_id = MOTOR_TO_ID[name]
        ids.append(motor_id)
        positions.append(float(target) * id_to_sign[motor_id] + id_to_offset[motor_id])
    if ids:
        controller.sync_write_goal_position(ids, positions)


def read_named_positions():
    raw_positions = controller.sync_read_present_position(all_ids)
    if len(raw_positions) != len(all_ids):
        raise RuntimeError(
            "Expected {} motor positions, got {}".format(len(all_ids), len(raw_positions))
        )
    return {
        id_to_name[motor_id]: (float(position) - id_to_offset[motor_id]) * id_to_sign[motor_id]
        for motor_id, position in zip(all_ids, raw_positions)
    }


def ramp_named_targets(start_targets, end_targets, duration_s):
    steps = max(1, int(duration_s * 50.0))
    delay = duration_s / steps
    for step in range(steps + 1):
        alpha = step / steps
        targets = {
            name: start + (float(end_targets.get(name, 0.0)) - start) * alpha
            for name, start in start_targets.items()
        }
        write_named_targets(targets)
        time.sleep(delay)


torque_enabled = False
last_targets = None

try:
    controller.sync_write_status_return_level(all_ids, [1] * len(all_ids))
    controller.sync_write_position_p_gain(all_ids, [KP_DEFAULT] * len(all_ids))
    current_targets = read_named_positions()
    write_named_targets(current_targets)
    controller.sync_write_torque_enable(all_ids, [True] * len(all_ids))
    torque_enabled = True
    last_targets = dict(current_targets)
    ramp_named_targets(current_targets, HOME_POSE, STARTUP_RAMP_SECONDS)
    last_targets = dict(HOME_POSE)
    print("REMOTE_READY", flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        if message.get("type") == "targets":
            last_targets = dict(message["targets"])
            write_named_targets(last_targets)
        elif message.get("type") == "stop":
            break
finally:
    try:
        if torque_enabled:
            if last_targets is not None:
                ramp_named_targets(last_targets, HOME_POSE, STARTUP_RAMP_SECONDS)
            else:
                write_named_targets(HOME_POSE)
                time.sleep(0.2)
    finally:
        if torque_enabled:
            controller.sync_write_torque_enable(all_ids, [False] * len(all_ids))
    print("REMOTE_STOPPED", flush=True)
"""


def build_remote_code(serial_port: str) -> str:
    return (
        REMOTE_CODE_TEMPLATE
        .replace("__MOTOR_SERIAL_PORT__", repr(serial_port))
        .replace("__MOTOR_TO_ID__", repr(dict(MOTOR_TO_ID)))
        .replace("__MOTOR_SIGN__", repr(dict(MOTOR_SIGN)))
        .replace("__MOTOR_OFFSET__", repr(dict(MOTOR_OFFSET)))
        .replace("__HOME_POSE__", repr(dict(HOME_POSE)))
        .replace("__KP_DEFAULT__", repr(int(KP_DEFAULT)))
        .replace("__STARTUP_RAMP_SECONDS__", repr(float(STARTUP_RAMP_SECONDS)))
    )


class PiMotorBridge:
    """Line-delimited JSON bridge to a Python process running on the Pi."""

    def __init__(self, host: str, serial_port: str, ready_timeout_s: float) -> None:
        code_arg = shlex.quote(build_remote_code(serial_port))
        remote_shell = (
            'if [ -x "$HOME/microduck/.venv/bin/python" ]; then '
            f'cd "$HOME/microduck" && PYTHONPATH=src exec .venv/bin/python -u -c {code_arg} 2>&1; '
            "elif command -v python3 >/dev/null 2>&1; then "
            f"exec python3 -u -c {code_arg} 2>&1; "
            "elif command -v python >/dev/null 2>&1; then "
            f"exec python -u -c {code_arg} 2>&1; "
            "else "
            "echo 'No Python interpreter found on Pi' >&2; exit 127; "
            "fi"
        )
        self._proc = subprocess.Popen(
            ["ssh", host, f"bash -lc {shlex.quote(remote_shell)}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._wait_until_ready(ready_timeout_s)

    def _wait_until_ready(self, timeout_s: float) -> None:
        assert self._proc.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(self._proc.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout_s
        output: list[str] = []

        try:
            while time.monotonic() < deadline:
                if self._proc.poll() is not None:
                    remainder = self._proc.stdout.read() or ""
                    raise RuntimeError(
                        "Pi bridge exited before it was ready:\n"
                        + "".join(output)
                        + remainder
                    )
                events = selector.select(timeout=max(0.0, deadline - time.monotonic()))
                if not events:
                    break
                line = self._proc.stdout.readline()
                if not line:
                    continue
                output.append(line)
                print(f"[pi] {line}", end="")
                if line.strip() == "REMOTE_READY":
                    return
        finally:
            selector.close()

        self.close()
        raise TimeoutError(
            "Timed out waiting for the Pi bridge. Check SSH, servo power, and the serial port."
        )

    def send_targets(self, targets: dict[str, float]) -> None:
        if self._proc.poll() is not None:
            raise RuntimeError(f"Pi bridge exited with code {self._proc.returncode}.")
        assert self._proc.stdin is not None
        self._proc.stdin.write(json.dumps({"type": "targets", "targets": targets}) + "\n")
        self._proc.stdin.flush()

    def close(self) -> None:
        if self._proc.poll() is None and self._proc.stdin is not None:
            try:
                self._proc.stdin.write(json.dumps({"type": "stop"}) + "\n")
                self._proc.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            self._proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            self._proc.terminate()


class DirectionCheckApp:
    def __init__(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        viewer,
        motor_names: list[str],
        angle_limit_deg: float | None,
        bridge: PiMotorBridge | None,
    ) -> None:
        self._model = model
        self._data = data
        self._viewer = viewer
        self._bridge = bridge
        self._deltas = {name: 0.0 for name in motor_names}
        self._targets = dict(HOME_POSE)
        self._joint_qpos: dict[str, int] = {}
        self._sliders: dict[str, tk.Scale] = {}
        self._dirty = True
        self._closed = False

        for name in motor_names:
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
            if joint_id >= 0:
                self._joint_qpos[name] = int(model.jnt_qposadr[joint_id])

        self._root = tk.Tk()
        self._root.title("Microduck motor direction check")
        self._root.protocol("WM_DELETE_WINDOW", self.close)

        tk.Label(
            self._root,
            text=(
                "Move one slider at a time. Values are deltas from the HOME pose.\n"
                "Compare the real robot with MuJoCo. Opposite direction => flip the sign.\n"
                "The mouth servo has no MJCF joint, so it is robot-only."
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=4, padx=8, pady=(8, 4), sticky="w")

        for row, name in enumerate(motor_names, start=1):
            low_deg, high_deg = self._slider_range_deg(name, angle_limit_deg)
            sim_note = "" if name in self._joint_qpos else "  robot-only"
            offset_note = ""
            if abs(MOTOR_OFFSET[name]) > 1e-9:
                offset_note = f"  hw offset {math.degrees(MOTOR_OFFSET[name]):+.0f}deg"
            tk.Label(
                self._root,
                text=(
                    f"ID {MOTOR_TO_ID[name]:02d}  {name}{sim_note}{offset_note}  "
                    f"delta [{low_deg:+.1f}, {high_deg:+.1f}]"
                ),
            ).grid(row=row, column=0, padx=8, sticky="w")
            value = tk.StringVar(value=self._format_value(name, 0.0))
            slider = tk.Scale(
                self._root,
                from_=low_deg,
                to=high_deg,
                resolution=0.5,
                orient=tk.HORIZONTAL,
                length=280,
                showvalue=False,
                command=lambda raw, n=name, v=value: self._set_delta_deg(n, raw, v),
            )
            slider.grid(row=row, column=1, padx=4, sticky="ew")
            tk.Label(self._root, textvariable=value, width=20).grid(row=row, column=2, padx=4)
            tk.Button(
                self._root,
                text="home",
                command=lambda n=name: self._home_one(n),
            ).grid(row=row, column=3, padx=4)
            self._sliders[name] = slider
            slider.set(0.0)

        control_row = len(self._targets) + 1
        tk.Button(self._root, text="home all", command=self._home_all).grid(
            row=control_row, column=0, padx=8, pady=8, sticky="ew"
        )
        tk.Button(self._root, text="quit", command=self.close).grid(
            row=control_row, column=3, padx=8, pady=8, sticky="ew"
        )

        self._apply_targets()
        self._root.after(20, self._tick)

    def _slider_range_deg(self, name: str, angle_limit_deg: float | None) -> tuple[float, float]:
        home = HOME_POSE[name]
        if name in MOTOR_ONLY_RANGE_DEG:
            low, high = (math.radians(value) for value in MOTOR_ONLY_RANGE_DEG[name])
        else:
            joint_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
            if joint_id < 0:
                limit = math.radians(angle_limit_deg if angle_limit_deg is not None else 20.0)
                low, high = home - limit, home + limit
            elif self._model.jnt_limited[joint_id]:
                low, high = (float(value) for value in self._model.jnt_range[joint_id])
            else:
                limit = math.radians(angle_limit_deg if angle_limit_deg is not None else 180.0)
                low, high = home - limit, home + limit

        low_delta = low - home
        high_delta = high - home
        if angle_limit_deg is not None:
            limit = math.radians(angle_limit_deg)
            low_delta = max(low_delta, -limit)
            high_delta = min(high_delta, limit)
        return math.degrees(low_delta), math.degrees(high_delta)

    def _format_value(self, name: str, delta_rad: float) -> str:
        target = HOME_POSE[name] + delta_rad
        return f"d {math.degrees(delta_rad):+5.1f} | tgt {math.degrees(target):+6.1f}"

    def _set_delta_deg(self, name: str, raw_value: str, value: tk.StringVar) -> None:
        delta = math.radians(float(raw_value))
        value.set(self._format_value(name, delta))
        self._deltas[name] = delta
        self._targets[name] = HOME_POSE[name] + delta
        self._dirty = True

    def _home_one(self, name: str) -> None:
        self._sliders[name].set(0.0)

    def _home_all(self) -> None:
        for slider in self._sliders.values():
            slider.set(0.0)
        self._dirty = True

    def _apply_targets(self, send_to_bridge: bool = True) -> None:
        if self._data.qpos.size >= 7:
            self._data.qpos[0:7] = [0.0, 0.0, DEFAULT_ROOT_Z, 1.0, 0.0, 0.0, 0.0]
        for name, angle in self._targets.items():
            qpos = self._joint_qpos.get(name)
            if qpos is not None:
                self._data.qpos[qpos] = angle
        mujoco.mj_forward(self._model, self._data)
        self._viewer.sync()
        if send_to_bridge and self._bridge is not None:
            self._bridge.send_targets(self._targets)

    def _tick(self) -> None:
        if self._closed:
            return
        if not self._viewer.is_running():
            self.close()
            return
        if self._dirty:
            self._dirty = False
            try:
                self._apply_targets()
            except Exception as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                self.close()
                return
        self._root.after(20, self._tick)

    def run(self) -> None:
        self._root.mainloop()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._targets = dict(HOME_POSE)
            self._apply_targets(send_to_bridge=False)
        except Exception as exc:
            print(f"Warning: failed to reset MuJoCo targets: {exc}", file=sys.stderr)
        if self._bridge is not None:
            self._bridge.close()
        try:
            self._viewer.close()
        finally:
            self._root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="microduck", help="SSH host for the Pi Zero.")
    parser.add_argument("--serial-port", default=DEFAULT_SERIAL_PORT, help="Dynamixel serial port on the Pi.")
    parser.add_argument(
        "--mjcf",
        type=Path,
        default=DEFAULT_MJCF if DEFAULT_MJCF.exists() else FALLBACK_MJCF,
        help="Path to the MuJoCo scene.xml.",
    )
    parser.add_argument(
        "--limit-deg",
        type=float,
        default=20.0,
        help="Symmetric slider limit around HOME before joint-range clipping.",
    )
    parser.add_argument(
        "--full-range",
        action="store_true",
        help="Use the full MJCF or motor-only range instead of the safety-limited slider range.",
    )
    parser.add_argument(
        "--no-robot",
        action="store_true",
        help="Open MuJoCo sliders without connecting to the Pi.",
    )
    parser.add_argument(
        "--ready-timeout",
        type=float,
        default=20.0,
        help="Seconds to wait for the remote Pi process to enable torque and reach HOME.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.mjcf.exists():
        raise SystemExit(f"MJCF not found: {args.mjcf}")

    model = mujoco.MjModel.from_xml_path(str(args.mjcf))
    data = mujoco.MjData(model)
    motor_names = [name for name, _motor_id in sorted(MOTOR_TO_ID.items(), key=lambda item: item[1])]
    sim_names = []
    motor_only_names = []

    for name in motor_names:
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint_id >= 0:
            sim_names.append(name)
        else:
            motor_only_names.append(name)

    if data.qpos.size >= 7:
        data.qpos[0:7] = [0.0, 0.0, DEFAULT_ROOT_Z, 1.0, 0.0, 0.0, 0.0]
    for name, angle in HOME_POSE.items():
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint_id >= 0:
            data.qpos[model.jnt_qposadr[joint_id]] = angle
    mujoco.mj_forward(model, data)

    print("Opening MuJoCo viewer...")
    print(f"Loaded MJCF: {args.mjcf.resolve()}")
    print("Slider motors:")
    for name in motor_names:
        note = "" if name in sim_names else " (robot-only, no MJCF joint)"
        offset = MOTOR_OFFSET[name]
        offset_note = "" if abs(offset) < 1e-9 else f" hw_offset={math.degrees(offset):+.0f}deg"
        print(f"  ID {MOTOR_TO_ID[name]:02d}: {name}{note}{offset_note}")
    if motor_only_names:
        print("Motor-only entries:", ", ".join(motor_only_names))

    viewer = mujoco.viewer.launch_passive(model, data)

    bridge = None
    if not args.no_robot:
        print(f"Connecting to Pi over SSH: {args.host}")
        print("If prompted, enter the Pi password in this terminal.")
        bridge = PiMotorBridge(args.host, args.serial_port, args.ready_timeout)

    app = DirectionCheckApp(
        model=model,
        data=data,
        viewer=viewer,
        motor_names=motor_names,
        angle_limit_deg=None if args.full_range else args.limit_deg,
        bridge=bridge,
    )
    app.run()


if __name__ == "__main__":
    main()
