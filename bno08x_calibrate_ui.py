#!/usr/bin/env python3
"""BNO08x IMU check UI for Microduck training.

Run this on the Ubuntu PC. It SSHs into the Pi Zero and temporarily runs a
minimal BNO080/085/086 I2C streamer there. It does not modify the Pi.

The UI shows the signals used by the walking policy:
  - gyro in rad/s
  - projected_gravity in the robot body frame
  - quaternion age/rate and gyro age/rate

Example:
  python3 bno08x_calibrate_ui.py --host microduck --user pi
  python3 bno08x_calibrate_ui.py --host 192.168.2.42 --user pi --password '...'
"""

from __future__ import annotations

import argparse
import json
import math
import os
import queue
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Any

try:
    import tkinter as tk
    from tkinter import scrolledtext
except ImportError:
    print("Need tkinter: sudo apt install python3-tk", file=sys.stderr)
    sys.exit(1)


DEFAULT_MOUNT_QUAT = "0.5,-0.5,-0.5,0.5"
LOG_PATH = "/tmp/microduck_bno08x_calibrate_ui.log"

REMOTE_TEMPLATE = r"""
import fcntl, glob, json, math, os, struct, sys, time, traceback

FORCED_BUS = __BUS__
FORCED_ADDR = __ADDR__
INTERVAL_US = __INTERVAL_US__
MOUNT_QUAT = tuple(__MOUNT_QUAT__)

I2C_SLAVE = 0x0703
I2C_SLAVE_FORCE = 0x0706
CHAN_EXE = 1
CHAN_CONTROL = 2
CHAN_REPORTS = 3
SET_FEATURE = 0xFD
REPORT_ACCEL = 0x01
REPORT_GYRO = 0x02
REPORT_RV = 0x05
REPORT_GAME_RV = 0x08
QUAT_SCALE = 1.0 / (1 << 14)
GYRO_SCALE = 1.0 / (1 << 9)
ACCEL_SCALE = 1.0 / (1 << 8)


def emit(x):
    print(json.dumps(x), flush=True)


def qn(q):
    w, x, y, z = q
    n = math.sqrt(w*w + x*x + y*y + z*z) or 1.0
    return (w/n, x/n, y/n, z/n)


def qc(q):
    w, x, y, z = q
    return (w, -x, -y, -z)


def qm(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def q_apply_inv(q, v):
    # Same convention as microduck/src/imu_reader.py.
    w, x, y, z = q
    vx, vy, vz = v
    tx = 2.0 * (y*vz - z*vy)
    ty = 2.0 * (z*vx - x*vz)
    tz = 2.0 * (x*vy - y*vx)
    return (
        vx - w*tx + (y*tz - z*ty),
        vy - w*ty + (z*tx - x*tz),
        vz - w*tz + (x*ty - y*tx),
    )


def euler(q):
    w, x, y, z = q
    roll = math.degrees(math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y)))
    pitch = math.degrees(math.asin(max(-1, min(1, 2*(w*y - z*x)))))
    yaw = math.degrees(math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))
    return (roll, pitch, yaw)


class BNO:
    def __init__(self, bus, addr):
        self.fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
        try:
            fcntl.ioctl(self.fd, I2C_SLAVE, addr)
        except OSError:
            fcntl.ioctl(self.fd, I2C_SLAVE_FORCE, addr)
        self.seq = [0] * 6

    def close(self):
        try:
            os.close(self.fd)
        except OSError:
            pass

    def send(self, ch, data):
        data = bytes(data)
        pkt = struct.pack("<HBB", len(data) + 4, ch, self.seq[ch] & 255) + data
        self.seq[ch] = (self.seq[ch] + 1) & 255
        os.write(self.fd, pkt)

    def read(self):
        h = os.read(self.fd, 4)
        if len(h) < 4:
            return None
        raw_len, ch, seq = struct.unpack("<HBB", h)
        total = raw_len & 0x7FFF
        if total <= 4 or total == 0x7FFF or ch > 5:
            return None
        self.seq[ch] = seq
        # Some Linux I2C adapters return the payload when asked for total-4
        # bytes; others behave like the working debug script and need a read of
        # total bytes, including a repeated header. Accept both forms.
        p = os.read(self.fd, total)
        if len(p) == total - 4:
            payload = p
        elif len(p) >= total:
            payload = p[4:]
        elif len(p) >= 4:
            payload = p[4:]
        else:
            return None
        return ch, payload

    def feature(self, report_id):
        p = bytearray(17)
        p[0] = SET_FEATURE
        p[1] = report_id
        struct.pack_into("<I", p, 5, int(INTERVAL_US))
        self.send(CHAN_CONTROL, p)


def parse(payload):
    out = {}
    i = 0
    while i < len(payload):
        rid = payload[i]
        if rid == 0xFB:
            i += 5
        elif rid in (REPORT_GAME_RV, REPORT_RV) and i + 12 <= len(payload):
            iq, jq, kq, rq = struct.unpack_from("<hhhh", payload, i + 4)
            out["quat"] = (rq * QUAT_SCALE, iq * QUAT_SCALE, jq * QUAT_SCALE, kq * QUAT_SCALE)
            i += 12 if rid == REPORT_GAME_RV else 14
        elif rid == REPORT_GYRO and i + 10 <= len(payload):
            gx, gy, gz = struct.unpack_from("<hhh", payload, i + 4)
            out["gyro"] = (gx * GYRO_SCALE, gy * GYRO_SCALE, gz * GYRO_SCALE)
            i += 10
        elif rid == REPORT_ACCEL and i + 10 <= len(payload):
            ax, ay, az = struct.unpack_from("<hhh", payload, i + 4)
            out["accel"] = (ax * ACCEL_SCALE, ay * ACCEL_SCALE, az * ACCEL_SCALE)
            i += 10
        else:
            i += 1
    return out


def ack(bus, addr):
    try:
        fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
    except OSError:
        return False
    try:
        try:
            fcntl.ioctl(fd, I2C_SLAVE, addr)
        except OSError:
            fcntl.ioctl(fd, I2C_SLAVE_FORCE, addr)
        os.read(fd, 4)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


def find_device():
    if FORCED_BUS >= 0 and FORCED_ADDR > 0:
        return FORCED_BUS, FORCED_ADDR
    found = []
    for node in sorted(glob.glob("/dev/i2c-*")):
        try:
            bus = int(node.split("-")[-1])
        except ValueError:
            continue
        for addr in (0x4A, 0x4B):
            if ack(bus, addr):
                found.append((bus, addr))
    emit({"debug": "scan", "found": [{"bus": b, "addr": hex(a)} for b, a in found]})
    if not found:
        raise RuntimeError("BNO08x not found at 0x4A/0x4B on /dev/i2c-*")
    return found[0]


try:
    bus, addr = find_device()
    imu = BNO(bus, addr)
    try:
        imu.send(CHAN_EXE, [1])
        time.sleep(0.8)
        deadline = time.time() + 0.4
        while time.time() < deadline:
            try:
                imu.read()
            except OSError:
                time.sleep(0.01)
        imu.feature(REPORT_GAME_RV)
        imu.feature(REPORT_GYRO)
        imu.feature(REPORT_ACCEL)
        time.sleep(0.2)

        start = time.perf_counter()
        last_emit = start
        last_q = (1.0, 0.0, 0.0, 0.0)
        last_g = (0.0, 0.0, 0.0)
        last_a = (0.0, 0.0, 0.0)
        last_t = {"quat": start, "gyro": start, "accel": start}
        counts = {"quat": 0, "gyro": 0, "accel": 0}
        intervals = {"quat": [], "gyro": [], "accel": []}
        prev = {"quat": None, "gyro": None, "accel": None}
        errors = 0

        while True:
            now = time.perf_counter()
            try:
                pkt = imu.read()
            except OSError as exc:
                errors += 1
                emit({"error": "I2C read failed: %s" % exc})
                time.sleep(0.05)
                continue
            if pkt:
                ch, payload = pkt
                if ch in (CHAN_REPORTS, 4):
                    got = parse(payload)
                    for key in ("quat", "gyro", "accel"):
                        if key in got:
                            if prev[key] is not None:
                                intervals[key].append(now - prev[key])
                                intervals[key] = intervals[key][-500:]
                            prev[key] = now
                            last_t[key] = now
                            counts[key] += 1
                    if "quat" in got:
                        last_q = qn(got["quat"])
                    if "gyro" in got:
                        last_g = got["gyro"]
                    if "accel" in got:
                        last_a = got["accel"]

            now = time.perf_counter()
            if now - last_emit < 0.05:
                continue
            last_emit = now
            body_q = qn(qm(last_q, qc(MOUNT_QUAT)))
            body_gyro = q_apply_inv(MOUNT_QUAT, last_g)
            pg = q_apply_inv(body_q, (0.0, 0.0, -1.0))
            elapsed = max(1e-6, now - start)

            def hz(k):
                return counts[k] / elapsed

            def p95(k):
                vals = sorted(v * 1000 for v in intervals[k])
                return None if not vals else vals[min(len(vals)-1, int(0.95 * (len(vals)-1)))]

            emit({
                "valid": True,
                "bus": bus,
                "addr": hex(addr),
                "interval_us": INTERVAL_US,
                "errors": errors,
                "quat": [round(v, 6) for v in last_q],
                "imu_euler_deg": [round(v, 2) for v in euler(last_q)],
                "body_euler_deg": [round(v, 2) for v in euler(body_q)],
                "gyro": [round(v, 5) for v in last_g],
                "body_gyro": [round(v, 5) for v in body_gyro],
                "accel_mps2": [round(v, 4) for v in last_a],
                "projected_gravity": [round(v, 5) for v in pg],
                "quat_age_ms": round((now - last_t["quat"]) * 1000, 1),
                "gyro_age_ms": round((now - last_t["gyro"]) * 1000, 1),
                "quat_hz": round(hz("quat"), 1),
                "gyro_hz": round(hz("gyro"), 1),
                "accel_hz": round(hz("accel"), 1),
                "quat_interval_p95_ms": None if p95("quat") is None else round(p95("quat"), 1),
                "gyro_interval_p95_ms": None if p95("gyro") is None else round(p95("gyro"), 1),
            })
    finally:
        imu.close()
except Exception:
    emit({"error": traceback.format_exc()})
    sys.exit(1)
"""


def parse_mount_quat(text: str) -> tuple[float, float, float, float]:
    vals = tuple(float(x.strip()) for x in text.split(","))
    if len(vals) != 4:
        raise argparse.ArgumentTypeError("expected w,x,y,z")
    n = math.sqrt(sum(v * v for v in vals))
    if n <= 0:
        raise argparse.ArgumentTypeError("zero quaternion")
    return tuple(v / n for v in vals)  # type: ignore[return-value]


def fmt_vec(v: Any, digits: int = 3) -> str:
    if not isinstance(v, list):
        return "n/a"
    return "[" + ", ".join(f"{float(x):+.{digits}f}" for x in v) + "]"


def summarize_samples(samples: list[dict[str, Any]], title: str) -> str:
    if not samples:
        return f"{title}: no samples."

    def vals(key: str, idx: int | None = None) -> list[float]:
        out = []
        for item in samples:
            v = item.get(key)
            if isinstance(v, list) and idx is not None:
                out.append(float(v[idx]))
            elif isinstance(v, (int, float)) and idx is None:
                out.append(float(v))
        return out

    def mean_std(key: str, idx: int | None = None) -> tuple[float, float]:
        xs = vals(key, idx)
        if not xs:
            return float("nan"), float("nan")
        return statistics.fmean(xs), statistics.pstdev(xs) if len(xs) > 1 else 0.0

    lines = [f"{title} ({len(samples)} UI samples)"]
    gyro_key = "body_gyro" if any("body_gyro" in item for item in samples) else "gyro"
    for name, key in (("body_gyro rad/s", gyro_key), ("projected_gravity", "projected_gravity")):
        parts = []
        for idx, axis in enumerate("xyz"):
            mu, sd = mean_std(key, idx)
            parts.append(f"{axis} mean={mu:+.4f} std={sd:.4f}")
        lines.append(f"{name}: " + "; ".join(parts))
    for key in ("quat_age_ms", "gyro_age_ms", "quat_hz", "gyro_hz", "errors"):
        mu, sd = mean_std(key)
        lines.append(f"{key}: mean={mu:.2f} std={sd:.2f}")

    max_age = max(
        max(vals("quat_age_ms") or [9999.0]),
        max(vals("gyro_age_ms") or [9999.0]),
    )
    if max_age <= 25:
        delay = "0..1 control steps"
    elif max_age <= 65:
        delay = "0..3 control steps"
    else:
        delay = "fix IMU transport first; sample age > 60ms"
    lines.append(f"Suggested training IMU delay: {delay}")
    return "\n".join(lines)


@dataclass
class RollingStats:
    samples: list[dict[str, Any]]

    def window(self, seconds: float = 5.0) -> list[dict[str, Any]]:
        if not self.samples:
            return []
        cutoff = self.samples[-1]["local_t"] - seconds
        return [s for s in self.samples if s["local_t"] >= cutoff]

    def summary(self, seconds: float = 5.0) -> str:
        win = self.window(seconds)
        if not win:
            return "No samples yet."
        text = summarize_samples(win, f"Rolling {seconds:.0f}s stats")
        return text + "\nUpright target: projected_gravity ~= [0, 0, -1], body_gyro ~= [0, 0, 0]."


class Stream:
    def __init__(self, args: argparse.Namespace) -> None:
        self.host = f"{args.user}@{args.host}" if args.user and "@" not in args.host else args.host
        self.password = args.password
        self.bus = -1 if args.bus is None else args.bus
        self.addr = 0 if args.addr is None else args.addr
        self.interval_us = args.interval_us
        self.mount_quat = args.mount_quat
        self.q: queue.Queue[dict[str, Any]] = queue.Queue()
        self.proc: subprocess.Popen[str] | None = None
        self.askpass: str | None = None
        self.stop_flag = threading.Event()

    def start(self) -> None:
        remote = (
            REMOTE_TEMPLATE
            .replace("__BUS__", str(self.bus))
            .replace("__ADDR__", str(self.addr))
            .replace("__INTERVAL_US__", str(self.interval_us))
            .replace("__MOUNT_QUAT__", json.dumps(list(self.mount_quat)))
        )
        env = os.environ.copy()
        opts = []
        if self.password:
            fd, path = tempfile.mkstemp(prefix="bno08x_askpass_", text=True)
            os.close(fd)
            with open(path, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\ncat <<'EOF'\n" + self.password + "\nEOF\n")
            os.chmod(path, 0o700)
            self.askpass = path
            env["DISPLAY"] = env.get("DISPLAY") or ":0"
            env["SSH_ASKPASS"] = path
            env["SSH_ASKPASS_REQUIRE"] = "force"
            opts = ["-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no"]
        cmd = [
            "ssh", "-T",
            "-o", "ConnectTimeout=8",
            "-o", "ServerAliveInterval=5",
            "-o", "StrictHostKeyChecking=accept-new",
            *opts,
            self.host,
            "python3 -u -",
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
        assert self.proc.stdin and self.proc.stdout and self.proc.stderr
        self.proc.stdin.write(remote)
        self.proc.stdin.close()
        threading.Thread(target=self._stdout, daemon=True).start()
        threading.Thread(target=self._stderr, daemon=True).start()

    def close(self) -> None:
        self.stop_flag.set()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        if self.askpass:
            try:
                os.remove(self.askpass)
            except OSError:
                pass

    def _stdout(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            if self.stop_flag.is_set():
                return
            try:
                self.q.put(json.loads(line))
            except json.JSONDecodeError:
                self.q.put({"error": line.strip()})

    def _stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            if self.stop_flag.is_set():
                return
            low = line.lower()
            if "warning:" in low or "permanently added" in low:
                continue
            self.q.put({"error": line.strip()})


class App:
    def __init__(self, root: tk.Tk, stream: Stream) -> None:
        self.root = root
        self.stream = stream
        self.latest: dict[str, Any] = {}
        self.stats = RollingStats([])
        self.records: list[str] = []
        self.capture_name: str | None = None
        self.capture_until = 0.0
        self.capture_samples: list[dict[str, Any]] = []
        root.title("BNO08x IMU training check")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.status = tk.StringVar(value="正在连接 Pi Zero...")
        self.values = tk.StringVar(value="")
        tk.Label(root, textvariable=self.status, anchor="w", justify="left").pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(root, textvariable=self.values, font=("monospace", 11), anchor="w", justify="left").pack(fill="x", padx=8)
        hints = (
            "操作方法：按下面按钮，每次按提示把机器人保持 5 秒。\n"
            "必须先做：直立静止。然后做：前倾、后仰、左倾、右倾。最后可做：水平原地转动。\n"
            "目标：直立时 projected_gravity 接近 [0, 0, -1]，gyro 接近 [0, 0, 0]。"
        )
        tk.Label(root, text=hints, anchor="w", justify="left").pack(fill="x", padx=8, pady=6)
        btns = tk.Frame(root)
        btns.pack(fill="x", padx=8, pady=4)
        tk.Button(btns, text="1 直立静止 5秒", command=lambda: self.start_capture("upright_still")).pack(side="left")
        tk.Button(btns, text="2 前倾 5秒", command=lambda: self.start_capture("pitch_forward")).pack(side="left", padx=3)
        tk.Button(btns, text="3 后仰 5秒", command=lambda: self.start_capture("pitch_backward")).pack(side="left", padx=3)
        tk.Button(btns, text="4 左倾 5秒", command=lambda: self.start_capture("roll_left")).pack(side="left", padx=3)
        tk.Button(btns, text="5 右倾 5秒", command=lambda: self.start_capture("roll_right")).pack(side="left", padx=3)
        tk.Button(btns, text="6 水平转动 5秒", command=lambda: self.start_capture("yaw_rotate")).pack(side="left", padx=3)
        btns2 = tk.Frame(root)
        btns2.pack(fill="x", padx=8, pady=4)
        tk.Button(btns2, text="清空采样", command=self.reset).pack(side="left")
        tk.Button(btns2, text="复制完整报告", command=self.copy).pack(side="left", padx=6)
        tk.Button(btns2, text="退出", command=self.close).pack(side="right")
        self.text = scrolledtext.ScrolledText(root, width=110, height=14, font=("monospace", 10))
        self.text.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.stream.start()
        self.root.after(100, self.poll)

    def reset(self) -> None:
        self.stats.samples.clear()
        self.records.clear()
        self.capture_name = None
        self.capture_samples.clear()

    def copy(self) -> None:
        s = self.full_report()
        self.root.clipboard_clear()
        self.root.clipboard_append(s)
        self.status.set("完整报告已复制，可以发给我或用于设置训练参数")

    def start_capture(self, name: str) -> None:
        self.capture_name = name
        self.capture_until = time.perf_counter() + 5.0
        self.capture_samples = []
        self.status.set(f"正在采样 {name}: 保持这个姿态 5 秒，不要晃动")

    def finish_capture(self) -> None:
        if self.capture_name is None:
            return
        title = f"CAPTURE {self.capture_name}"
        self.records.append(summarize_samples(self.capture_samples, title))
        self.status.set(f"{self.capture_name} 采样完成，继续按下一个按钮")
        self.capture_name = None
        self.capture_samples = []

    def full_report(self) -> str:
        parts = [
            "BNO08x IMU training check report",
            "",
            self.stats.summary(),
        ]
        if self.records:
            parts += ["", "Captured poses:", "", "\n\n".join(self.records)]
        else:
            parts += ["", "No guided captures yet. Press the numbered buttons first."]
        parts += [
            "",
            "Training rule:",
            "- If sample age stays <=25ms, IMU delay can be 0..1.",
            "- If sample age stays <=65ms, keep IMU delay 0..3.",
            "- If projected_gravity upright is not near [0, 0, -1], fix IMU_MOUNT_QUAT before training.",
        ]
        return "\n".join(parts)

    def poll(self) -> None:
        try:
            while True:
                item = self.stream.q.get_nowait()
                if "error" in item:
                    self.status.set("error")
                    self.text.insert("end", "\nERROR:\n" + str(item["error"]) + "\n")
                    self.text.see("end")
                    continue
                if "debug" in item:
                    self.text.insert("end", "DEBUG: " + json.dumps(item, ensure_ascii=False) + "\n")
                    self.text.see("end")
                    continue
                item["local_t"] = time.perf_counter()
                self.latest = item
                self.stats.samples.append(item)
                self.stats.samples = self.stats.samples[-5000:]
                if self.capture_name is not None:
                    self.capture_samples.append(item)
        except queue.Empty:
            pass
        if self.capture_name is not None:
            remaining = self.capture_until - time.perf_counter()
            if remaining <= 0:
                self.finish_capture()
            else:
                self.status.set(f"正在采样 {self.capture_name}: 还剩 {remaining:.1f} 秒")
        self.render()
        self.root.after(100, self.poll)

    def render(self) -> None:
        if not self.latest:
            return
        d = self.latest
        self.status.set(f"bus={d.get('bus')} addr={d.get('addr')} errors={d.get('errors')} interval_us={d.get('interval_us')}")
        self.values.set("\n".join([
            f"quat_hz={d.get('quat_hz')} gyro_hz={d.get('gyro_hz')} accel_hz={d.get('accel_hz')} "
            f"quat_age_ms={d.get('quat_age_ms')} gyro_age_ms={d.get('gyro_age_ms')}",
            f"quat_p95_ms={d.get('quat_interval_p95_ms')} gyro_p95_ms={d.get('gyro_interval_p95_ms')}",
            f"imu_euler_deg  = {fmt_vec(d.get('imu_euler_deg'), 2)}",
            f"body_euler_deg = {fmt_vec(d.get('body_euler_deg'), 2)}",
            f"raw gyro rad/s = {fmt_vec(d.get('gyro'), 4)}",
            f"body gyro      = {fmt_vec(d.get('body_gyro'), 4)}",
            f"proj_gravity   = {fmt_vec(d.get('projected_gravity'), 4)}",
            f"accel m/s^2    = {fmt_vec(d.get('accel_mps2'), 3)}",
        ]))
        self.text.delete("1.0", "end")
        self.text.insert("end", self.full_report())

    def close(self) -> None:
        self.stream.close()
        self.root.destroy()


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default=os.environ.get("HOST", "microduck"))
    p.add_argument("--user", default=os.environ.get("USER_ON_PI"))
    p.add_argument("--password", default=os.environ.get("PASSWORD"))
    p.add_argument("--bus", type=int)
    p.add_argument("--addr", type=lambda s: int(s, 0))
    p.add_argument("--interval-us", type=int, default=20_000)
    p.add_argument("--mount-quat", type=parse_mount_quat, default=parse_mount_quat(DEFAULT_MOUNT_QUAT))
    return p.parse_args()


def main() -> None:
    if shutil.which("ssh") is None:
        raise SystemExit("ssh not found")
    root = tk.Tk()
    App(root, Stream(args()))
    root.mainloop()


if __name__ == "__main__":
    main()
