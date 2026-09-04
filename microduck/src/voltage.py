# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

"""Read and print the bus voltage from one or all motors."""

import sys
from rustypot import Xl330PyController

from constants import MOTOR_TO_ID, ID_TO_MOTOR


def main() -> None:
    controller = Xl330PyController(
        serial_port="/dev/ttyAMA0", baudrate=1_000_000, timeout=0.1
    )

    if len(sys.argv) > 1:
        motor_ids = [int(sys.argv[1])]
    else:
        motor_ids = list(MOTOR_TO_ID.values())

    controller.sync_write_status_return_level(motor_ids, [1] * len(motor_ids))

    for motor_id in motor_ids:
        raw = controller.read_present_input_voltage(motor_id)
        voltage_raw = raw[0] if isinstance(raw, (list, tuple)) else raw
        voltage_v = voltage_raw * 0.1
        name = ID_TO_MOTOR.get(motor_id, str(motor_id))
        print(f"  Motor {motor_id:2d}: {voltage_v:.2f} V ({name})")


if __name__ == "__main__":
    main()