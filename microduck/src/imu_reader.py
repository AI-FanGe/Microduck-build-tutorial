# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import fcntl
import glob
import os
import struct
import threading
import time
from dataclasses import dataclass

import numpy as np

from constants import IMU_MOUNT_QUAT

I2C_SLAVE = 0x0703
I2C_SLAVE_FORCE = 0x0706

CHAN_EXE = 1
CHAN_CONTROL = 2
CHAN_REPORTS = 3

SET_FEATURE = 0xFD
REPORT_ACCEL = 0x01
REPORT_GYRO = 0x02
REPORT_RV = 0x05
REPORT_GAME_RV = 0x08

QUAT_SCALE = 1.0 / (1 << 14)
GYRO_SCALE = 1.0 / (1 << 9)
ACCEL_SCALE = 1.0 / (1 << 8)


@dataclass(frozen=True)
class IMUSnapshot:
    timestamp_s: float
    quat: tuple[float, float, float, float]
    gyro: tuple[float, float, float]
    acc: tuple[float, float, float]
    valid: bool
    error_count: int


def _normalize_quat(q: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    w, x, y, z = q
    norm = (w * w + x * x + y * y + z * z) ** 0.5 or 1.0
    return (w / norm, x / norm, y / norm, z / norm)


def _quat_conj(q: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    w, x, y, z = q
    return (w, -x, -y, -z)


def _quat_mul(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def imu_quat_to_body(
    q: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Convert a BNO08x quaternion from the IMU mount frame to the robot body frame."""
    return _normalize_quat(_quat_mul(q, IMU_MOUNT_QUAT))


def quat_apply_inverse(quat: list[float] | tuple[float, float, float, float], vec: list[float] | tuple[float, float, float]) -> list[float]:
    """Apply an inverse quaternion rotation to a vector."""
    xyz = np.array(quat[1:], dtype=float)
    v = np.array(vec, dtype=float)
    w = float(quat[0])
    t = 2.0 * np.cross(xyz, v)
    out = v - w * t + np.cross(xyz, t)
    return out.tolist()

class _BNO08x:
    def __init__(self, bus: int, addr: int) -> None:
        self.fd = os.open(f"/dev/i2c-{bus}", os.O_RDWR)
        try:
            fcntl.ioctl(self.fd, I2C_SLAVE, addr)
        except OSError:
            fcntl.ioctl(self.fd, I2C_SLAVE_FORCE, addr)
        self.seq = [0] * 6

    def close(self) -> None:
        try:
            os.close(self.fd)
        except OSError:
            pass

    def send(self, channel: int, data: bytes | bytearray | list[int]) -> None:
        payload = bytes(data)
        packet = struct.pack("<HBB", len(payload) + 4, channel, self.seq[channel] & 0xFF) + payload
        self.seq[channel] = (self.seq[channel] + 1) & 0xFF
        os.write(self.fd, packet)

    def read_packet(self) -> tuple[int, bytes] | None:
        header = os.read(self.fd, 4)
        if len(header) < 4:
            return None
        raw_len, channel, seq = struct.unpack("<HBB", header)
        total = raw_len & 0x7FFF
        if total <= 4 or total == 0x7FFF or channel > 5:
            return None
        self.seq[channel] = seq
        payload = os.read(self.fd, total)
        if len(payload) == total - 4:
            return channel, payload
        if len(payload) >= 4:
            return channel, payload[4:]
        return None

    def enable_feature(self, report_id: int, interval_us: int) -> None:
        payload = bytearray(17)
        payload[0] = SET_FEATURE
        payload[1] = report_id
        struct.pack_into("<I", payload, 5, interval_us)
        self.send(CHAN_CONTROL, payload)


def _parse_reports(payload: bytes) -> dict[str, tuple[float, ...]]:
    out: dict[str, tuple[float, ...]] = {}
    i = 0
    while i < len(payload):
        report_id = payload[i]
        if report_id == 0xFB:
            i += 5
        elif report_id in (REPORT_GAME_RV, REPORT_RV) and i + 12 <= len(payload):
            iq, jq, kq, rq = struct.unpack_from("<hhhh", payload, i + 4)
            out["quat"] = (
                rq * QUAT_SCALE,
                iq * QUAT_SCALE,
                jq * QUAT_SCALE,
                kq * QUAT_SCALE,
            )
            i += 12 if report_id == REPORT_GAME_RV else 14
        elif report_id == REPORT_GYRO and i + 10 <= len(payload):
            gx, gy, gz = struct.unpack_from("<hhh", payload, i + 4)
            out["gyro"] = (gx * GYRO_SCALE, gy * GYRO_SCALE, gz * GYRO_SCALE)
            i += 10
        elif report_id == REPORT_ACCEL and i + 10 <= len(payload):
            ax, ay, az = struct.unpack_from("<hhh", payload, i + 4)
            out["acc"] = (ax * ACCEL_SCALE, ay * ACCEL_SCALE, az * ACCEL_SCALE)
            i += 10
        else:
            i += 1
    return out


def _device_responds(bus: int, addr: int) -> bool:
    try:
        fd = os.open(f"/dev/i2c-{bus}", os.O_RDWR)
    except OSError:
        return False
    try:
        try:
            fcntl.ioctl(fd, I2C_SLAVE, addr)
        except OSError:
            fcntl.ioctl(fd, I2C_SLAVE_FORCE, addr)
        os.read(fd, 4)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


def _find_bno08x(preferred_bus: int) -> tuple[int, int]:
    buses: list[int] = []
    if preferred_bus >= 0:
        buses.append(preferred_bus)
    for node in sorted(glob.glob("/dev/i2c-*")):
        try:
            bus = int(node.rsplit("-", 1)[1])
        except ValueError:
            continue
        if bus not in buses:
            buses.append(bus)

    for bus in buses:
        for addr in (0x4A, 0x4B):
            if _device_responds(bus, addr):
                return bus, addr
    raise RuntimeError("BNO08x not found at 0x4A/0x4B")


class ThreadedIMUReader:
    """Reads a GY-BNO080/BNO08x on a background thread."""

    def __init__(self, i2c_bus: int, frequency_hz: float = 50.0, warn_interval_s: float = 1.0) -> None:
        if frequency_hz <= 0:
            raise ValueError("frequency_hz must be > 0")

        self._bus, self._addr = _find_bno08x(i2c_bus)
        self._imu = _BNO08x(self._bus, self._addr)
        self._period_s = 1.0 / frequency_hz
        self._interval_us = int(round(1_000_000.0 / frequency_hz))
        self._warn_interval_s = warn_interval_s

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, name="imu-reader", daemon=True)

        now = time.perf_counter()
        self._snapshot = IMUSnapshot(
            timestamp_s=now,
            quat=(1.0, 0.0, 0.0, 0.0),
            gyro=(0.0, 0.0, 0.0),
            acc=(0.0, 0.0, 0.0),
            valid=False,
            error_count=0,
        )
        self._error_count = 0
        self._last_warn_s = 0.0

    def start(self) -> None:
        if not self._thread.is_alive():
            self._configure()
            self._thread.start()

    def stop(self, timeout_s: float = 1.0) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout_s)
        self._imu.close()

    def get_latest(self) -> IMUSnapshot:
        with self._lock:
            return self._snapshot

    def get_status(self) -> dict[str, float | int | bool]:
        snap = self.get_latest()
        now = time.perf_counter()
        return {
            "valid": snap.valid,
            "age_s": max(0.0, now - snap.timestamp_s),
            "error_count": snap.error_count,
            "target_frequency_hz": 1.0 / self._period_s,
            "bus": self._bus,
            "addr": self._addr,
        }

    def _configure(self) -> None:
        self._imu.send(CHAN_EXE, [1])
        time.sleep(0.8)
        deadline = time.time() + 0.4
        while time.time() < deadline:
            try:
                self._imu.read_packet()
            except OSError:
                time.sleep(0.01)
        self._imu.enable_feature(REPORT_GAME_RV, self._interval_us)
        self._imu.enable_feature(REPORT_GYRO, self._interval_us)
        self._imu.enable_feature(REPORT_ACCEL, self._interval_us)
        time.sleep(0.2)

    def _run_loop(self) -> None:
        latest_q = (1.0, 0.0, 0.0, 0.0)
        latest_g = (0.0, 0.0, 0.0)
        latest_a = (0.0, 0.0, 0.0)

        while not self._stop_event.is_set():
            now = time.perf_counter()
            try:
                packet = self._imu.read_packet()
                if packet is not None:
                    channel, payload = packet
                    if channel in (CHAN_REPORTS, 4):
                        got = _parse_reports(payload)
                        if "quat" in got:
                            latest_q = _normalize_quat(got["quat"])  # type: ignore[arg-type]
                        if "gyro" in got:
                            latest_g = got["gyro"]  # type: ignore[assignment]
                        if "acc" in got:
                            latest_a = got["acc"]  # type: ignore[assignment]
                        with self._lock:
                            self._snapshot = IMUSnapshot(
                                timestamp_s=now,
                                quat=latest_q,
                                gyro=latest_g,
                                acc=latest_a,
                                valid=True,
                                error_count=self._error_count,
                            )
            except Exception as exc:
                self._error_count += 1
                if (now - self._last_warn_s) >= self._warn_interval_s:
                    print(f"Warning: BNO08x read failed ({self._error_count}): {exc}", end="\r\n", flush=True)
                    self._last_warn_s = now
                with self._lock:
                    prev = self._snapshot
                    self._snapshot = IMUSnapshot(
                        timestamp_s=prev.timestamp_s,
                        quat=prev.quat,
                        gyro=prev.gyro,
                        acc=prev.acc,
                        valid=prev.valid,
                        error_count=self._error_count,
                    )
                time.sleep(0.02)
