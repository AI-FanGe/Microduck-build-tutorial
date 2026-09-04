#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Record BNO08x IMU samples for checking the mount orientation.

Run on the Pi through:
    make imu-check

The output is copied back to logs/imu_orientation_check/latest.json by the
Makefile target.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from constants import IMU_I2C_BUS, IMU_MOUNT_QUAT
from imu_reader import ThreadedIMUReader, imu_quat_to_body, quat_apply_inverse


POSES = (
    (
        "level",
        "Put the robot upright and level in its neutral body pose.",
    ),
    (
        "front_down",
        "Tilt the robot so the front/beak side points downward, then hold still.",
    ),
    (
        "front_up",
        "Tilt the robot so the front/beak side points upward, then hold still.",
    ),
    (
        "left_down",
        "Tilt the robot so its left side points downward, then hold still.",
    ),
    (
        "right_down",
        "Tilt the robot so its right side points downward, then hold still.",
    ),
    (
        "yaw_left_level",
        "Keep the robot level and rotate the front/beak to the left, then hold still.",
    ),
    (
        "yaw_right_level",
        "Keep the robot level and rotate the front/beak to the right, then hold still.",
    ),
)


def quat_to_euler_deg(q: tuple[float, float, float, float]) -> tuple[float, float, float]:
    w, x, y, z = q
    roll = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))
    yaw = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
    return roll, pitch, yaw


def mean(values: list[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def stdev(values: list[float]) -> float:
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        ("quat_raw", 4),
        ("quat_body", 4),
        ("gyro", 3),
        ("acc", 3),
        ("projected_gravity", 3),
        ("euler_raw_deg", 3),
        ("euler_body_deg", 3),
    )
    summary: dict[str, Any] = {"sample_count": len(samples)}
    for key, size in keys:
        summary[key] = {
            "mean": [mean([sample[key][i] for sample in samples]) for i in range(size)],
            "std": [stdev([sample[key][i] for sample in samples]) for i in range(size)],
        }
    summary["age_ms"] = {
        "mean": mean([sample["age_ms"] for sample in samples]),
        "max": max((sample["age_ms"] for sample in samples), default=0.0),
    }
    summary["valid_ratio"] = (
        mean([1.0 if sample["valid"] else 0.0 for sample in samples]) if samples else 0.0
    )
    summary["error_count_delta"] = (
        samples[-1]["error_count"] - samples[0]["error_count"] if len(samples) > 1 else 0
    )
    return summary


def collect_pose(
    reader: ThreadedIMUReader,
    duration_s: float,
    frequency_hz: float,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    period_s = 1.0 / frequency_hz
    deadline_s = time.perf_counter() + duration_s
    while time.perf_counter() < deadline_s:
        now_s = time.perf_counter()
        snap = reader.get_latest()
        quat_raw = tuple(float(v) for v in snap.quat)
        quat_body = imu_quat_to_body(quat_raw)
        projected_gravity = quat_apply_inverse(quat_body, (0.0, 0.0, -1.0))
        samples.append(
            {
                "t_s": now_s,
                "sensor_t_s": snap.timestamp_s,
                "age_ms": max(0.0, (now_s - snap.timestamp_s) * 1000.0),
                "valid": bool(snap.valid),
                "error_count": int(snap.error_count),
                "quat_raw": list(quat_raw),
                "quat_body": list(quat_body),
                "gyro": [float(v) for v in snap.gyro],
                "acc": [float(v) for v in snap.acc],
                "projected_gravity": [float(v) for v in projected_gravity],
                "euler_raw_deg": list(quat_to_euler_deg(quat_raw)),
                "euler_body_deg": list(quat_to_euler_deg(quat_body)),
            }
        )
        time.sleep(period_s)
    return samples


def wait_for_valid(reader: ThreadedIMUReader, timeout_s: float) -> None:
    deadline_s = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline_s:
        snap = reader.get_latest()
        if snap.valid:
            return
        time.sleep(0.05)
    status = reader.get_status()
    raise RuntimeError(f"IMU did not produce a valid sample within {timeout_s}s: {status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=3.0, help="Seconds to record per pose.")
    parser.add_argument("--frequency", type=float, default=50.0, help="Sampling frequency in Hz.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to logs/imu_orientation_check/<timestamp>.json.",
    )
    parser.add_argument(
        "--skip-yaw",
        action="store_true",
        help="Only record level/front/back/left/right tilt poses.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    poses = POSES[:5] if args.skip_yaw else POSES
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or Path("logs/imu_orientation_check") / f"{timestamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    reader = ThreadedIMUReader(i2c_bus=IMU_I2C_BUS, frequency_hz=args.frequency)
    reader.start()
    try:
        wait_for_valid(reader, timeout_s=8.0)
        print("IMU ready.")
        print(f"Mount quat used by deployment: {IMU_MOUNT_QUAT}")
        print(f"Recording {len(poses)} poses, {args.duration:.1f}s each.")
        print("Hold the robot still during each recording window.")

        records = []
        for index, (name, prompt) in enumerate(poses, start=1):
            print()
            print(f"[{index}/{len(poses)}] {name}")
            print(prompt)
            input("Press Enter when stable...")
            print("Recording...")
            samples = collect_pose(reader, args.duration, args.frequency)
            summary = summarize(samples)
            records.append({"name": name, "prompt": prompt, "summary": summary, "samples": samples})
            pg = summary["projected_gravity"]["mean"]
            euler = summary["euler_body_deg"]["mean"]
            print(
                "Done. body_euler_deg="
                f"roll={euler[0]:+.1f} pitch={euler[1]:+.1f} yaw={euler[2]:+.1f}; "
                f"projected_gravity=({pg[0]:+.3f}, {pg[1]:+.3f}, {pg[2]:+.3f})"
            )

        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "duration_s": args.duration,
            "frequency_hz": args.frequency,
            "imu_i2c_bus": IMU_I2C_BUS,
            "imu_mount_quat": IMU_MOUNT_QUAT,
            "reader_status": reader.get_status(),
            "poses": records,
        }
        output.write_text(json.dumps(payload, indent=2))
        latest = output.parent / "latest.json"
        latest.write_text(json.dumps(payload, indent=2))
        print()
        print(f"Saved: {output}")
        print(f"Saved latest copy: {latest}")
    finally:
        reader.stop()


if __name__ == "__main__":
    main()
