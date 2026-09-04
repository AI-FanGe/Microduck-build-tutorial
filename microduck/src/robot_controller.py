# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

from rustypot import Xl330PyController
import glob
import os
import numpy as np

from constants import MOTOR_TO_ID, MOTOR_OFFSET, MOTOR_SIGN, IMU_I2C_BUS, PRESENT_CURRENT_UNIT_A
from imu_reader import ThreadedIMUReader


def resolve_serial_port(serial_port: str) -> str:
    if serial_port != "auto":
        return serial_port
    candidates = (
        sorted(glob.glob("/dev/serial/by-id/usb-ROBOTIS_OpenRB-150_*"))
        + ["/dev/ttyACM0", "/dev/serial0", "/dev/ttyAMA0", "/dev/ttyS0"]
    )
    for path in candidates:
        if os.path.exists(path):
            return path
    return "/dev/ttyAMA0"


class RobotController:
    """Wraps Xl330PyController."""

    def __init__(self, serial_port: str = "auto", baudrate: int = 1_000_000, timeout: float = 0.1) -> None:
        serial_port = resolve_serial_port(serial_port)
        print(f"Using Dynamixel serial port: {serial_port}", flush=True)
        self._controller = Xl330PyController(serial_port=serial_port, baudrate=baudrate, timeout=timeout)
        self._id_to_sign: dict[int, float] = {MOTOR_TO_ID[name]: MOTOR_SIGN[name] for name in MOTOR_TO_ID}
        self._id_to_offset: dict[int, float] = {MOTOR_TO_ID[name]: MOTOR_OFFSET[name] for name in MOTOR_TO_ID}
        self._imu_reader = ThreadedIMUReader(i2c_bus=IMU_I2C_BUS, frequency_hz=50.0)
        self._imu_reader.start()

    def sync_write_torque_enable(self, ids: list[int], values: list[bool]) -> None:
        self._controller.sync_write_torque_enable(ids, values)

    def sync_write_status_return_level(self, ids: list[int], levels: list[int]) -> None:
        self._controller.sync_write_status_return_level(ids, levels)

    def sync_write_goal_position(self, ids: list[int], positions: list[float]) -> None:
        hw_positions = [
            pos * self._id_to_sign[motor_id] + self._id_to_offset[motor_id]
            for motor_id, pos in zip(ids, positions)
        ]
        self._controller.sync_write_goal_position(ids, hw_positions)

    def sync_read_present_position(self, ids: list[int]) -> list[float]:
        raw = self._controller.sync_read_present_position(ids)
        return [
            (r - self._id_to_offset[motor_id]) * self._id_to_sign[motor_id]
            for motor_id, r in zip(ids, raw)
        ]

    def read_present_position(self, motor_id: int) -> float:
        raw = self._controller.read_present_position(motor_id)
        raw_value = raw[0] if isinstance(raw, (list, tuple)) else float(raw)
        return (raw_value - self._id_to_offset[motor_id]) * self._id_to_sign[motor_id]

    def sync_read_present_velocity(self, ids: list[int]) -> list[float]:
        raw = np.array(self._controller.sync_read_present_velocity(ids)) * 0.229 * np.pi / 30
        return [r * self._id_to_sign[motor_id] for motor_id, r in zip(ids, raw)]
    
    def read_present_velocity(self, motor_id: int) -> float:
        raw = self._controller.read_present_velocity(motor_id) * 0.229 * np.pi / 30
        return raw * self._id_to_sign[motor_id]

    def sync_read_present_current(self, ids: list[int]) -> list[float]:
        """Present current per motor, in Amps (signed). Magnitude is what matters for the BMS budget."""
        raw = self._controller.sync_read_present_current(ids)
        return [
            (r[0] if isinstance(r, (list, tuple)) else float(r)) * PRESENT_CURRENT_UNIT_A
            for r in raw
        ]

    def sync_read_present_input_voltage(self, ids: list[int]) -> list[float]:
        raw = self._controller.sync_read_present_input_voltage(ids)
        return [r[0] if isinstance(r, (list, tuple)) else float(r) for r in raw]

    def read_present_input_voltage(self, motor_id: int) -> float:
        raw = self._controller.read_present_input_voltage(motor_id)
        return raw[0] if isinstance(raw, (list, tuple)) else float(raw)

    def sync_read_kp(self, ids: list[int]) -> list[int]:
        return [int(v) for v in self._controller.sync_read_position_p_gain(ids)]

    def sync_write_kp(self, ids: list[int], gains: list[int]) -> None:
        self._controller.sync_write_position_p_gain(ids, gains)

    def read_acc(self) -> tuple[float, float, float]:
        """Return raw accelerometer (ax, ay, az) in g."""
        return self._imu_reader.get_latest().acc

    def read_gyro(self) -> tuple[float, float, float]:
        """Return (gx, gy, gz) in rad/s."""
        return self._imu_reader.get_latest().gyro

    def read_quat(self, dt: float) -> tuple[float, float, float, float]:
        """Return orientation quaternion (w, x, y, z)."""
        _ = dt
        return self._imu_reader.get_latest().quat

    def get_imu_status(self) -> dict[str, float | int | bool]:
        return self._imu_reader.get_status()

    def shutdown(self) -> None:
        self._imu_reader.stop()

    def close(self) -> None:
        self.shutdown()