.PHONY: sync setup run stop shutdown voltage imu imu-check imu-viewer sim viewer direction-check direction-check-sim gamepad-headless-enable gamepad-headless-disable

HOST ?= microduck
ID ?=
UV_HTTP_TIMEOUT ?= 300
SERIAL_PORT ?= auto
IMU_CHECK_DURATION ?= 3.0
IMU_CHECK_FREQUENCY ?= 50.0
IMU_CHECK_ARGS ?=

sync:
	rsync -avz \
		--exclude='.git' \
		--exclude='.venv' \
		--exclude='__pycache__' \
		--exclude='cad' \
		--exclude='docs' \
		--exclude='logs' \
		--exclude='src/debug' \
		--exclude='src/sim' \
		--exclude='src/model/mjcf' \
		./ $(HOST):microduck

setup: sync
	ssh -tt $(HOST) "bash -l -c 'cd microduck && UV_HTTP_TIMEOUT=$(UV_HTTP_TIMEOUT) uv sync --frozen'"

sim:
	PYTHONPATH=src uv run --group sim src/sim/sim_main.py --hz 50

viewer:
	PYTHONPATH=src uv run src/sim/viewer_main.py --hz 25

direction-check:
	PYTHONPATH=src uv run --group sim src/debug/mujoco_motor_direction_check.py --host $(HOST) --serial-port $(SERIAL_PORT)

direction-check-sim:
	PYTHONPATH=src uv run --group sim src/debug/mujoco_motor_direction_check.py --no-robot

run: sync
	ssh -tt $(HOST) "bash -l -c 'cd microduck && PYTHONPATH=src .venv/bin/python src/main.py'"

stop:
	ssh -tt $(HOST) "bash -l -c 'cd microduck && PYTHONPATH=src .venv/bin/python src/stop.py'"

voltage: sync
	ssh $(HOST) "bash -l -c 'cd microduck && PYTHONPATH=src .venv/bin/python src/voltage.py $(ID)'"

imu: sync
	ssh -tt $(HOST) "bash -l -c 'cd microduck && PYTHONPATH=src .venv/bin/python src/imu.py'"

imu-check: sync
	ssh -tt $(HOST) "bash -l -c 'cd microduck && PYTHONPATH=src .venv/bin/python src/imu_orientation_check.py --duration $(IMU_CHECK_DURATION) --frequency $(IMU_CHECK_FREQUENCY) $(IMU_CHECK_ARGS)'"
	mkdir -p logs/imu_orientation_check
	scp $(HOST):microduck/logs/imu_orientation_check/latest.json logs/imu_orientation_check/latest.json

imu-viewer: sync
	cd .. && PYTHONPATH=$(CURDIR)/src mjlab_microduck/.venv/bin/python scripts/imu_mujoco_orientation_viewer.py --host $(HOST) --frequency $(IMU_CHECK_FREQUENCY)

shutdown:
	ssh -tt $(HOST) "sudo shutdown -h now"

# Opt-in headless mode: a service launches the control loop when START is held 2s on
# the gamepad (no SSH needed); B stops it. See docs/usage.md.
gamepad-headless-enable: sync
	ssh -tt $(HOST) "bash -l -c 'cd microduck && sudo bash systemd/install-gamepad-daemon.sh'"

gamepad-headless-disable:
	ssh -tt $(HOST) "bash -l -c 'cd microduck && sudo bash systemd/install-gamepad-daemon.sh --uninstall'"
