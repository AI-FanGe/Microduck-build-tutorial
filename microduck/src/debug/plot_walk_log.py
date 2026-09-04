# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import matplotlib.pyplot as plt
import json

if __name__ == "__main__":
    with open("logs/walk_log.json", "r") as f:
        log = json.load(f)

    motor_positions = log["position"]
    motor_voltages = log["voltage"]

    time = [0.02 * i for i in range(len(motor_positions["head"]))]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    for name in motor_positions.keys():
        ax1.plot(time, motor_positions[name], label=f"Observed {name}")
    ax1.set_ylabel("Motor Position (rad)")
    ax1.set_title("Motor Positions vs Time")
    ax1.legend()
    ax1.grid()

    for name in motor_voltages.keys():
        ax2.plot(time, motor_voltages[name], label=f"Observed {name}")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Motor Voltage (V)")
    ax2.set_title("Motor Voltages vs Time")
    ax2.legend()
    ax2.grid()

    plt.tight_layout()
    plt.show()