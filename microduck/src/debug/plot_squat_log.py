# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import json
import matplotlib.pyplot as plt

if __name__ == "__main__":
    with open("logs/squat_log.json", "r") as f:
        log = json.load(f)

    obs_projected_gravity_x = log["obs_projected_gravity_x"]
    obs_projected_gravity_y = log["obs_projected_gravity_y"]
    obs_projected_gravity_z = log["obs_projected_gravity_z"]
    obs_gyro_roll = log["obs_gyro_roll"]
    obs_gyro_pitch = log["obs_gyro_pitch"]
    obs_gyro_yaw = log["obs_gyro_yaw"]
    target_com_z = log["target_com_z"]

    time = [0.02 * i for i in range(len(obs_projected_gravity_x))]
    plt.figure(figsize=(12, 8))
    ax1 = plt.subplot(3, 1, 1)
    plt.plot(time, obs_projected_gravity_x, label="Projected Gravity X")
    plt.plot(time, obs_projected_gravity_y, label="Projected Gravity Y")
    plt.plot(time, obs_projected_gravity_z, label="Projected Gravity Z")
    plt.xlabel("Time (s)")
    plt.ylabel("Projected Gravity (m/s^2)")
    plt.title("Projected Gravity vs Time")
    plt.legend()
    plt.grid() 

    plt.subplot(3, 1, 2).sharex(ax1)
    plt.plot(time, obs_gyro_roll, label="Gyro Roll")
    plt.plot(time, obs_gyro_pitch, label="Gyro Pitch")
    plt.plot(time, obs_gyro_yaw, label="Gyro Yaw")
    plt.xlabel("Time (s)")
    plt.ylabel("Gyro (rad/s)")
    plt.title("Gyro vs Time")
    plt.legend()
    plt.grid()

    plt.subplot(3, 1, 3).sharex(ax1)
    plt.plot(time, target_com_z, label="Target COM Z")
    plt.xlabel("Time (s)")
    plt.ylabel("Target COM Z (m)")
    plt.title("Target COM Z vs Time")
    plt.legend()
    plt.grid()

    plt.tight_layout()
    plt.show()