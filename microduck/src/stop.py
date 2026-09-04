# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

import os
import signal
import time
from pathlib import Path

STOP_FLAG_FILE = Path("/tmp/microduck_scheduler.stop")
PID_FILE = Path("/tmp/microduck_scheduler.pid")

def process_exists(pid: int) -> bool:
	try:
		os.kill(pid, 0)
		return True
	except ProcessLookupError:
		return False
	except PermissionError:
		return True


def main() -> None:
	STOP_FLAG_FILE.write_text("stop\n", encoding="ascii")

	if not PID_FILE.exists():
		print("No scheduler PID file found. Stop flag has been set.")
		return

	pid = int(PID_FILE.read_text(encoding="ascii").strip())
	if not process_exists(pid):
		print(f"Scheduler process {pid} is not running.")
		if PID_FILE.exists():
			PID_FILE.unlink()
		return

	print(f"Sending SIGINT to scheduler process {pid}")
	os.kill(pid, signal.SIGINT)

	timeout_s = 3.0
	start = time.perf_counter()
	while process_exists(pid) and (time.perf_counter() - start) < timeout_s:
		time.sleep(0.1)

	if process_exists(pid):
		print(f"Scheduler {pid} did not stop after SIGINT, sending SIGTERM")
		os.kill(pid, signal.SIGTERM)

	print("Stop request sent.")


if __name__ == "__main__":
	main()