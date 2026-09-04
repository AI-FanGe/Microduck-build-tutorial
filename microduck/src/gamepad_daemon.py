# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Marc Duclusaud

"""Headless gamepad launcher.

Runs as a background service (opt-in, see systemd/microduck-gamepad.service). While the
robot has no control loop running, it watches the Bluetooth controller and, when START
is held, starts the control loop (the same `src/main.py` that `make run` runs) — no SSH
needed. The control loop is stopped from the gamepad with B (writes the stop flag).
Holding both triggers together powers the Pi off cleanly.

Wi-Fi is cut as soon as the gamepad connects over Bluetooth (to free the 2.4 GHz
antenna) and restored whenever it's not connected — independent of whether a
control-loop session is actually running. Whenever the daemon has to wait for a
gamepad (at startup, or after it disconnects, or after a control-loop crash), it
first makes sure Wi-Fi is enabled, undoing any stale `rfkill` block left over from
an unclean shutdown or crash. This means powering the controller off before booting
the robot keeps Wi-Fi up, giving you an escape hatch to SSH in (e.g. to run
`make gamepad-headless-disable`) even with headless mode enabled.

Coexists with `make run`: main.py refuses to start a second session (PID guard), and
this daemon skips launching if one is already running.
"""

import os
import sys
import time
import select
import signal
import subprocess
from pathlib import Path

from input.gamepad_input import (
    find_gamepad_path,
    XBOX_BUTTONS,
    TRIGGER_AXES,
    TRIGGER_PRESS_THRESHOLD,
    JS_EVENT,
    JS_EVENT_AXIS,
    JS_EVENT_BUTTON,
    JS_EVENT_INIT,
)

REPO = Path(__file__).resolve().parent.parent
PID_FILE = Path("/tmp/microduck_scheduler.pid")

LAUNCH_BUTTON = XBOX_BUTTONS["START"]
LAUNCH_HOLD_SECONDS = 2.0
SHUTDOWN_AXES = (TRIGGER_AXES["LT"], TRIGGER_AXES["RT"])  # held together to power off
SHUTDOWN_HOLD_SECONDS = 2.0
CUT_WIFI = True  # turn Wi-Fi off during a session (better Bluetooth signal)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def session_running() -> bool:
    """True if a control loop (main.py) is already running."""
    if not PID_FILE.exists():
        return False
    try:
        return process_exists(int(PID_FILE.read_text(encoding="ascii").strip()))
    except (ValueError, OSError):
        return False


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, timeout=10)
    except Exception as e:  # noqa: BLE001 - never let Wi-Fi toggling crash the daemon
        print(f"warning: command {' '.join(cmd)} failed: {e}", flush=True)


def wifi(enabled: bool) -> None:
    if CUT_WIFI:
        _run(["sudo", "/usr/sbin/rfkill", "unblock" if enabled else "block", "wifi"])


def wait_for_gamepad() -> str:
    """Block until a joystick device is present, then return its path.

    If none is connected yet, Wi-Fi is (re)enabled first. This is what makes the
    robot reachable over SSH at boot and after a control-loop crash.
    """
    path = find_gamepad_path()
    if path is None:
        wifi(enabled=True)
        while path is None:
            time.sleep(1.0)
            path = find_gamepad_path()
    print(f"Gamepad connected: {path}", flush=True)
    return path


def wait_for_action(path: str) -> str:
    """Watch the gamepad in the armed (idle) state for a held-button gesture.

    Returns "launch" (START held), "shutdown" (both triggers held), or "disconnect"
    if the device goes away (so the caller can wait for it to come back).
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return "disconnect"

    held: dict[int, float] = {}  # button number -> press time (monotonic)
    triggers_pressed = {axis: False for axis in SHUTDOWN_AXES}
    triggers_since: float | None = None  # when both triggers were first held together
    print("Armed — hold START to launch, hold both triggers to power off", flush=True)
    try:
        while True:
            select.select([fd], [], [], 0.1)
            try:
                data = os.read(fd, JS_EVENT.size * 32)
            except BlockingIOError:
                data = b""
            except OSError:
                return "disconnect"

            if data == b"" and not os.path.exists(path):
                return "disconnect"

            for offset in range(0, len(data) - JS_EVENT.size + 1, JS_EVENT.size):
                _, value, ev_type, number = JS_EVENT.unpack_from(data, offset)
                if ev_type & JS_EVENT_INIT:
                    continue
                if ev_type == JS_EVENT_BUTTON:
                    if value == 1:
                        held[number] = time.monotonic()
                    else:
                        held.pop(number, None)
                elif ev_type == JS_EVENT_AXIS and number in triggers_pressed:
                    triggers_pressed[number] = value >= TRIGGER_PRESS_THRESHOLD

            now = time.monotonic()
            if LAUNCH_BUTTON in held and now - held[LAUNCH_BUTTON] >= LAUNCH_HOLD_SECONDS:
                return "launch"

            if all(triggers_pressed.values()):
                if triggers_since is None:
                    triggers_since = now
                elif now - triggers_since >= SHUTDOWN_HOLD_SECONDS:
                    return "shutdown"
            else:
                triggers_since = None
    finally:
        os.close(fd)


def power_off() -> None:
    print("Shutdown requested from gamepad", flush=True)
    wifi(enabled=True)  # leave Wi-Fi unblocked for the next boot
    _run(["sudo", "/usr/sbin/shutdown", "-h", "now"])


def run_session() -> None:
    """Start the control loop and block until it exits (B button or crash)."""
    print("Launching control loop", flush=True)
    env = {**os.environ, "PYTHONPATH": "src"}
    proc = subprocess.Popen([sys.executable, "src/main.py"], cwd=str(REPO), env=env)
    proc.wait()
    print(f"Control loop exited (code {proc.returncode})", flush=True)


def main() -> None:
    # Restore Wi-Fi on service stop even if we are mid-session.
    signal.signal(signal.SIGTERM, lambda *_: (wifi(enabled=True), sys.exit(0)))

    print("microduck gamepad daemon started", flush=True)
    while True:
        path = wait_for_gamepad()
        wifi(enabled=False)  # gamepad connected over Bluetooth: free the 2.4 GHz band
        action = wait_for_action(path)

        if action == "disconnect":
            print("Gamepad disconnected while armed", flush=True)
            wifi(enabled=True)
            continue
        if action == "shutdown":
            power_off()
            return
        # action == "launch"
        if session_running():
            print("A control loop is already running — ignoring launch", flush=True)
            continue
        run_session()


if __name__ == "__main__":
    main()