# Copyright 2026 Marc Duclusaud

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:

#     http://www.apache.org/licenses/LICENSE-2.0

"""Export a trained .pt checkpoint to ONNX.

Usage:
    # Latest checkpoint of the latest run:
    uv run python src/mjlab_microduck/scripts/export_onnx.py

    # Specific checkpoint file:
    uv run python src/mjlab_microduck/scripts/export_onnx.py --checkpoint logs/rsl_rl/mjlab_microduck_velocity/2026-06-25_21-24-43/model_5000.pt
"""

import argparse
from dataclasses import asdict
from pathlib import Path

from mjlab.rl import RslRlVecEnvWrapper
from mjlab.rl.exporter_utils import attach_metadata_to_onnx, get_base_metadata
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab.utils.os import get_checkpoint_path

TASK = "Mjlab-Velocity-Microduck"
LOG_ROOT = Path("logs/rsl_rl/mjlab_microduck_velocity")
OUTPUT_FILENAME = "policy.onnx"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", type=Path, default=None, help="Path to a specific .pt file (default: latest)")
    p.add_argument("--device", type=str, default="cpu", help="Device for model loading (default: cpu)")
    return p.parse_args()


def main():
    args = parse_args()

    if args.checkpoint is not None:
        checkpoint_path = args.checkpoint
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    else:
        checkpoint_path = get_checkpoint_path(LOG_ROOT)

    print(f"[INFO] Checkpoint: {checkpoint_path}")

    env_cfg = load_env_cfg(TASK, play=True)
    agent_cfg = load_rl_cfg(TASK)

    env = ManagerBasedRlEnv(cfg=env_cfg, device=args.device)
    env = RslRlVecEnvWrapper(env)

    runner_cls = load_runner_cls(TASK)
    runner = runner_cls(env, asdict(agent_cfg), device=args.device)
    runner.load(str(checkpoint_path), load_cfg={"actor": True}, strict=True, map_location=args.device)

    output_dir = Path.cwd()
    runner.export_policy_to_onnx(str(output_dir), OUTPUT_FILENAME)

    onnx_path = output_dir / OUTPUT_FILENAME
    metadata = get_base_metadata(env.unwrapped, run_path=str(checkpoint_path.parent.name))
    attach_metadata_to_onnx(str(onnx_path), metadata)

    print(f"[INFO] Exported: {onnx_path}")

    env.close()


if __name__ == "__main__":
    main()
