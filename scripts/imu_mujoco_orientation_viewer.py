#!/usr/bin/env python3
"""Drive the Microduck MuJoCo model from the real BNO08x orientation.

The script runs locally, streams IMU data from the Pi over SSH, converts the
raw BNO08x quaternion with the deployment IMU_MOUNT_QUAT, and applies the
resulting body quaternion to the free joint in MuJoCo.
"""

from __future__ import annotations

import argparse
import json
import math
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import mujoco
import mujoco.viewer
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MJCF = (
    REPO_ROOT
    / "mjlab_microduck"
    / "src"
    / "mjlab_microduck"
    / "robot"
    / "microduck"
    / "robot_walk.xml"
)

REMOTE_CODE = r"""
import json
import time

from constants import IMU_I2C_BUS, IMU_MOUNT_QUAT
from imu_reader import ThreadedIMUReader, imu_quat_to_body, quat_apply_inverse

frequency = __FREQUENCY__
reader = ThreadedIMUReader(i2c_bus=IMU_I2C_BUS, frequency_hz=max(10.0, frequency))
reader.start()
try:
    while True:
        snap = reader.get_latest()
        q = tuple(float(x) for x in snap.quat)
        body_q = tuple(float(x) for x in imu_quat_to_body(q))
        projected = quat_apply_inverse(q, [0.0, 0.0, 1.0])
        print(json.dumps({
            "time": time.time(),
            "valid": bool(snap.valid),
            "quat": q,
            "body_quat": body_q,
            "gyro": snap.gyro,
            "acc": snap.acc,
            "projected_gravity": projected,
            "mount_quat": IMU_MOUNT_QUAT,
        }), flush=True)
        time.sleep(1.0 / frequency)
except KeyboardInterrupt:
    pass
finally:
    reader.stop()
"""


def reader_thread(proc: subprocess.Popen[str], out: "queue.Queue[dict[str, Any]]") -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        try:
            out.put(json.loads(line))
        except json.JSONDecodeError:
            print(line.rstrip())


def stderr_thread(proc: subprocess.Popen[str]) -> None:
    assert proc.stderr is not None
    for line in proc.stderr:
        print(f"[remote] {line.rstrip()}", file=sys.stderr)


def qpos_addr(model: mujoco.MjModel, joint_name: str) -> int:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise RuntimeError(f"Joint not found: {joint_name}")
    return int(model.jnt_qposadr[joint_id])


def site_id(model: mujoco.MjModel, site_name: str) -> int:
    sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    if sid < 0:
        raise RuntimeError(f"Site not found: {site_name}")
    return int(sid)


def draw_imu_marker(viewer: mujoco.viewer.Handle, data: mujoco.MjData, imu_site_id: int) -> None:
    scene = viewer.user_scn
    scene.ngeom = 0
    geom = scene.geoms[scene.ngeom]
    mujoco.mjv_initGeom(
        geom,
        mujoco.mjtGeom.mjGEOM_BOX,
        np.array([0.018, 0.012, 0.006], dtype=np.float64),
        data.site_xpos[imu_site_id].copy(),
        data.site_xmat[imu_site_id].copy(),
        np.array([0.0, 0.15, 1.0, 1.0], dtype=np.float32),
    )
    scene.ngeom += 1


def set_joint_if_present(model: mujoco.MjModel, data: mujoco.MjData, name: str, value: float) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if joint_id < 0:
        return
    data.qpos[model.jnt_qposadr[joint_id]] = value


def neutral_pose() -> dict[str, float]:
    return {
        "right_hip_yaw": 0.0,
        "right_hip_roll": 0.0873,
        "right_hip_pitch": 0.4579,
        "right_knee": 0.0049,
        "right_ankle": -0.4530,
        "left_hip_yaw": 0.0,
        "left_hip_roll": -0.0873,
        "left_hip_pitch": -0.4579,
        "left_knee": -0.0049,
        "left_ankle": 0.4530,
        "neck_pitch": 0.3491,
        "head_pitch": 0.3491,
        "head_yaw": 0.0,
        "head_roll": 0.0,
    }


def quat_to_euler_deg(q: list[float] | tuple[float, float, float, float]) -> tuple[float, float, float]:
    w, x, y, z = [float(v) for v in q]
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    sinp = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    pitch = math.asin(sinp)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="microduck", help="SSH host or alias for the Pi")
    parser.add_argument("--remote-dir", default="microduck", help="Remote microduck directory")
    parser.add_argument("--frequency", type=float, default=30.0, help="Streaming frequency in Hz")
    parser.add_argument("--mjcf", type=Path, default=DEFAULT_MJCF, help="Microduck MJCF XML")
    parser.add_argument("--root-z", type=float, default=0.18, help="Viewer root height")
    args = parser.parse_args()

    remote_code = REMOTE_CODE.replace("__FREQUENCY__", repr(float(args.frequency)))
    ssh_cmd = [
        "ssh",
        args.host,
        f"cd {args.remote_dir} && PYTHONPATH=src .venv/bin/python -u - <<'PY'\n{remote_code}\nPY",
    ]
    proc = subprocess.Popen(
        ssh_cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    updates: "queue.Queue[dict[str, Any]]" = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc, updates), daemon=True).start()
    threading.Thread(target=stderr_thread, args=(proc,), daemon=True).start()

    model = mujoco.MjModel.from_xml_path(str(args.mjcf))
    data = mujoco.MjData(model)
    root_addr = qpos_addr(model, "trunk_base_freejoint")
    imu_sid = site_id(model, "imu")

    data.qpos[:] = 0.0
    data.qpos[root_addr + 3] = 1.0
    for name, value in neutral_pose().items():
        set_joint_if_present(model, data, name, value)
    mujoco.mj_forward(model, data)

    latest: dict[str, Any] | None = None
    last_print = 0.0

    print("Microduck IMU MuJoCo viewer")
    print("The duck pose is driven by the real IMU after applying deployment IMU_MOUNT_QUAT.")
    print("Use the IMU in the same mounting direction as on the robot.")
    print("Expected silkscreen: IMU +X points robot-up, IMU +Y points robot-left.")
    print("The blue cube marks the simulated IMU site on the duck body.")

    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            while True:
                try:
                    latest = updates.get_nowait()
                except queue.Empty:
                    break

            if latest is not None:
                body_q = [float(v) for v in latest["body_quat"]]
                data.qpos[root_addr : root_addr + 3] = [0.0, 0.0, args.root_z]
                data.qpos[root_addr + 3 : root_addr + 7] = body_q
                mujoco.mj_forward(model, data)
                draw_imu_marker(viewer, data, imu_sid)

                now = time.monotonic()
                if now - last_print > 1.0:
                    g = latest.get("projected_gravity", [])
                    roll, pitch, yaw = quat_to_euler_deg(body_q)
                    print(
                        "valid={} body_rpy=[{:+.1f}, {:+.1f}, {:+.1f}] "
                        "imu_up=[{:+.3f}, {:+.3f}, {:+.3f}] mount_quat={}".format(
                            latest.get("valid"),
                            roll,
                            pitch,
                            yaw,
                            float(g[0]) if len(g) > 0 else 0.0,
                            float(g[1]) if len(g) > 1 else 0.0,
                            float(g[2]) if len(g) > 2 else 0.0,
                            latest.get("mount_quat"),
                        )
                    )
                    last_print = now

            viewer.sync()
            time.sleep(0.01)

    proc.terminate()


if __name__ == "__main__":
    main()
