# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

"""Local simulation entry point — never deployed to the robot.

Usage:
    uv run --group sim src/sim/sim_main.py --hz 50
    make sim 
"""

import argparse

from scheduler import Scheduler
from sim.mujoco_input import MuJoCoInputSource
from sim.mujoco_controller import MuJoCoController
from moves.rotate_head import RotateHeadMove
from moves.squat import SquatMove
from moves.walk import WalkMove


def main() -> None:
    parser = argparse.ArgumentParser(description="Run microduck scheduler in MuJoCo simulation.")
    parser.add_argument("--hz", type=float, default=50.0, metavar="FREQ", help="Scheduler frequency in Hz (default: 50)")
    parser.add_argument("--delay-act", type=int, default=2, metavar="STEPS", help="Actuation delay in simulator steps (1 step = 0.005 s)")
    parser.add_argument("--delay-pos", type=int, default=0, metavar="TICKS", help="Motor position read delay in scheduler ticks (1 tick = 20 ms at 50 Hz)")
    parser.add_argument("--delay-vel", type=int, default=1, metavar="TICKS", help="Motor velocity read delay in ticks")
    parser.add_argument("--delay-gyro", type=int, default=3, metavar="TICKS", help="Gyro read delay in ticks")
    parser.add_argument("--delay-quat", type=int, default=4, metavar="TICKS", help="Quaternion (projected gravity) read delay in ticks")
    parser.add_argument("--trunk-com-offset", type=float, nargs=3, default=[0.0, 0.0, 0.0], metavar=("X", "Y", "Z"), help="CoM offset on trunk body in meters (body frame)")
    args = parser.parse_args()

    input_source = MuJoCoInputSource(move_keys={"h": "head", "s": "squat", "v": "walk"})
    controller = MuJoCoController(
        mjcf_path="src/model/mjcf/scene.xml",
        key_callback=input_source.key_callback,
        reset_source=input_source,
        delay_act_steps=args.delay_act,
        delay_pos_ticks=args.delay_pos,
        delay_vel_ticks=args.delay_vel,
        delay_gyro_ticks=args.delay_gyro,
        delay_quat_ticks=args.delay_quat,
        trunk_com_offset=tuple(args.trunk_com_offset),
    )
    input_source.set_viewer_opt(controller.viewer_opt)

    scheduler = Scheduler(
        frequency_hz=args.hz,
        controller=controller,
        input_source=input_source,
        moves={
            "head": RotateHeadMove(),
            "squat": SquatMove(),
            "walk": WalkMove(controller=controller),
        },
    )
    scheduler.run()


if __name__ == "__main__":
    main()