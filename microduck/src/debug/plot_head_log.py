# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import json
import matplotlib.pyplot as plt

if __name__ == "__main__":
    with open("logs/rotate_head_log.json", "r") as f:
        log = json.load(f)

    # with open("logs/rotate_head_log_rsl2.json", "r") as f:
    #     log = json.load(f)

    obs_head_angle = log["obs_head_angle"]
    obs_head_velocity = log["obs_head_velocity"]
    target_head_angle = log["target_head_angle"]
    target_head_velocity = log["target_head_velocity"]

    time = [0.02 * i for i in range(len(obs_head_angle))]

    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(time, obs_head_angle, label="Observed Head Angle")
    plt.plot(time, target_head_angle, label="Target Head Angle", linestyle="--")
    plt.xlabel("Time (s)")
    plt.ylabel("Head Angle (rad)")
    plt.title("Head Angle vs Time")
    plt.legend()
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.plot(time, obs_head_velocity, label="Observed Head Velocity")
    plt.plot(time, target_head_velocity, label="Target Head Velocity", linestyle="--")
    plt.xlabel("Time (s)")
    plt.ylabel("Head Velocity (rad/s)")
    plt.title("Head Velocity vs Time")
    plt.legend()
    plt.grid()

    plt.tight_layout()
    plt.show()