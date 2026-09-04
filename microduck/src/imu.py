# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

"""Standalone IMU reader — prints roll, pitch, yaw and gyroscope data at 2 Hz.

Usage:
    uv run src/imu.py
    make imu
"""

import math
import time

from constants import IMU_I2C_BUS
from imu_reader import ThreadedIMUReader, imu_quat_to_body, quat_apply_inverse

reader = ThreadedIMUReader(i2c_bus=IMU_I2C_BUS, frequency_hz=200.0)
reader.start()

print("IMU (BNO08x) — Ctrl-C to stop.")

try:
    while True:
        sample = reader.get_latest()
        gx, gy, gz = sample.gyro
        ax, ay, az = sample.acc
        w, x, y, z = sample.quat
        bw, bx, by, bz = imu_quat_to_body((w, x, y, z))
        px, py, pz = quat_apply_inverse((bw, bx, by, bz), (0.0, 0.0, -1.0))

        roll = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))
        yaw = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))

        b_roll = math.degrees(math.atan2(2 * (bw * bx + by * bz), 1 - 2 * (bx * bx + by * by)))
        b_pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (bw * by - bz * bx)))))
        b_yaw = math.degrees(math.atan2(2 * (bw * bz + bx * by), 1 - 2 * (by * by + bz * bz)))

        age_ms = max(0.0, (time.perf_counter() - sample.timestamp_s) * 1000.0)
        print("--------------------------------------------")
        print(f"Gyro: gx={gx:+.3f}  gy={gy:+.3f}  gz={gz:+.3f} rad/s")
        print(f"Acc:  ax={ax:+.3f}  ay={ay:+.3f}  az={az:+.3f} g")
        print(f"IMU:  roll={roll:+.1f}°  pitch={pitch:+.1f}°  yaw={yaw:+.1f}°")
        print(f"Body: roll={b_roll:+.1f}°  pitch={b_pitch:+.1f}°  yaw={b_yaw:+.1f}°")
        print(f"Projected Gravity: px={px:+.3f}  py={py:+.3f}  pz={pz:+.3f}")
        print(f"Status: valid={sample.valid}  age={age_ms:.1f} ms  errors={sample.error_count}")

        # Slow print loop; the internal reader still runs at 200 Hz.
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    reader.stop()