#!/usr/bin/env python3
"""Headless boot test for a kidnix qcow2.

Boots the disk image under QEMU/KVM with -snapshot (the qcow2 is never
modified), watches the serial console for the readiness marker emitted by
kidnix-boot-report.service, grabs a framebuffer screenshot over QMP, and exits
non-zero if the kiosk did not come up.

    just test-boot                 # after `just build-qcow2`
    just test-boot-dry             # no disk image needed; validates plumbing

Python 3.9+, standard library only -- deliberately: this runs on CI runners and
inside minimal containers where installing anything is friction we do not need.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

# Emitted by /usr/libexec/kidnix-boot-report on the serial console.
MARKER_OK = "KIDNIX_BOOT_OK"
MARKER_FAIL = "KIDNIX_BOOT_FAIL"

# Anything matching this means the boot died early and waiting is pointless.
PANIC_PATTERNS = (
    re.compile(rb"Kernel panic"),
    re.compile(rb"Entering emergency mode"),
    re.compile(rb"You are in emergency mode"),
    re.compile(rb"Failed to start Switch Root"),
)

OVMF_CANDIDATES = (
    "/usr/share/OVMF/OVMF_CODE.fd",
    "/usr/share/edk2/ovmf/OVMF_CODE.fd",
    "/usr/share/qemu/ovmf-x86_64-code.bin",
    "/usr/share/OVMF/OVMF_CODE_4M.fd",
)


class BootTestError(RuntimeError):
    """A failure that should be reported cleanly rather than as a traceback."""


# --------------------------------------------------------------------------- #
# QMP
# --------------------------------------------------------------------------- #


class QMPClient:
    """Minimal QEMU Machine Protocol client (connect, negotiate, execute)."""

    def __init__(self, path: str, timeout: float = 30.0) -> None:
        self.path = path
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._buf = b""

    def connect(self) -> None:
        deadline = time.monotonic() + self.timeout
        last: Exception | None = None
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect(self.path)
                self._sock = sock
                break
            except OSError as exc:  # socket not created by QEMU yet
                last = exc
                time.sleep(0.2)
        else:
            raise BootTestError(f"could not connect to QMP socket {self.path}: {last}")

        self._read_json()  # greeting
        self.execute("qmp_capabilities")

    def _read_json(self) -> dict:
        assert self._sock is not None
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise BootTestError("QMP connection closed unexpectedly")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def execute(self, command: str, **arguments) -> dict:
        assert self._sock is not None
        payload = {"execute": command}
        if arguments:
            payload["arguments"] = arguments
        self._sock.sendall(json.dumps(payload).encode() + b"\n")
        while True:
            message = self._read_json()
            if "return" in message:
                return message["return"]
            if "error" in message:
                raise BootTestError(f"QMP {command} failed: {message['error']}")
            # else: an asynchronous event; keep reading.

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def find_ovmf() -> str:
    for candidate in OVMF_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise BootTestError(
        "no OVMF/UEFI firmware found; install edk2-ovmf. Looked in:\n  "
        + "\n  ".join(OVMF_CANDIDATES)
    )


def kvm_available() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


def convert_screenshot(ppm: Path) -> Path | None:
    """Best-effort PPM -> PNG. The PPM is kept either way."""
    png = ppm.with_suffix(".png")
    for cmd in (
        ["magick", str(ppm), str(png)],
        ["convert", str(ppm), str(png)],
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ppm), str(png)],
    ):
        if shutil.which(cmd[0]) is None:
            continue
        if subprocess.run(cmd, capture_output=True, check=False).returncode == 0:
            return png
    return None


# --------------------------------------------------------------------------- #
# the test
# --------------------------------------------------------------------------- #


def build_qemu_command(args: argparse.Namespace, qmp_socket: str) -> list[str]:
    # Flag/value pairs stay on one line; one-arg-per-line is unreadable here.
    # fmt: off
    return [
        "qemu-system-x86_64",
        "-machine", "q35,accel=kvm" if kvm_available() else "q35",
        *(["-cpu", "host"] if kvm_available() else ["-cpu", "max"]),
        "-smp", str(args.cpus),
        "-m", str(args.memory),
        # Never mutate the disk image the developer built.
        "-snapshot",
        "-bios", find_ovmf(),
        "-drive", f"file={args.qcow2},if=virtio,format=qcow2",
        "-netdev", f"user,id=net0,hostfwd=tcp::{args.ssh_port}-:22",
        "-device", "virtio-net-pci,netdev=net0",
        "-device", "virtio-rng-pci",
        # A real (virtual) GPU so the compositor has something to drive and the
        # screenshot shows the kiosk rather than a blank text console.
        "-device", "virtio-vga",
        "-display", "none",
        "-serial", "stdio",
        "-qmp", f"unix:{qmp_socket},server=on,wait=off",
        "-no-reboot",
    ]
    # fmt: on


def run_boot_test(args: argparse.Namespace) -> int:
    qcow2 = Path(args.qcow2)
    if not qcow2.is_file():
        raise BootTestError(f"disk image not found: {qcow2}\nRun: just build-qcow2")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    serial_log = output_dir / "boot-serial.log"
    screenshot_ppm = output_dir / "boot.ppm"

    if not kvm_available():
        print(
            "warning: /dev/kvm unavailable -- falling back to TCG emulation, "
            "which is roughly 10x slower and will likely exceed the timeout.",
            file=sys.stderr,
        )

    with tempfile.TemporaryDirectory(prefix="kidnix-boot-") as tmpdir:
        qmp_socket = os.path.join(tmpdir, "qmp.sock")
        command = build_qemu_command(args, qmp_socket)
        print(f"==> {' '.join(command)}\n", flush=True)

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            bufsize=0,
        )

        verdict: dict = {"result": None, "line": ""}
        deadline = time.monotonic() + args.timeout

        def pump_serial() -> None:
            """Tee the serial console to stdout and the log; detect the marker."""
            assert proc.stdout is not None
            with serial_log.open("wb") as log:
                for raw in iter(proc.stdout.readline, b""):
                    log.write(raw)
                    log.flush()
                    if args.verbose:
                        sys.stdout.buffer.write(raw)
                        sys.stdout.buffer.flush()
                    if verdict["result"] is not None:
                        continue
                    text = raw.decode("utf-8", "replace").rstrip()
                    if MARKER_OK in text:
                        verdict.update(result="ok", line=text)
                    elif MARKER_FAIL in text:
                        verdict.update(result="fail", line=text)
                    elif any(p.search(raw) for p in PANIC_PATTERNS):
                        verdict.update(result="panic", line=text)

        pump = threading.Thread(target=pump_serial, daemon=True)
        pump.start()

        qmp = QMPClient(qmp_socket)
        try:
            qmp.connect()

            while verdict["result"] is None and time.monotonic() < deadline:
                if proc.poll() is not None:
                    verdict.update(
                        result="died",
                        line=f"qemu exited early with status {proc.returncode}",
                    )
                    break
                time.sleep(1)

            if verdict["result"] is None:
                verdict.update(
                    result="timeout",
                    line=f"no marker within {args.timeout}s",
                )

            # Screenshot regardless of outcome -- a failure screenshot is the
            # single most useful artifact when a boot goes wrong.
            if proc.poll() is None:
                if verdict["result"] == "ok" and args.settle:
                    time.sleep(args.settle)
                try:
                    qmp.execute("screendump", filename=str(screenshot_ppm))
                    # screendump returns before the file is fully written.
                    for _ in range(50):
                        if screenshot_ppm.exists() and screenshot_ppm.stat().st_size:
                            break
                        time.sleep(0.1)
                except BootTestError as exc:
                    print(f"warning: screenshot failed: {exc}", file=sys.stderr)
        finally:
            qmp.close()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
            pump.join(timeout=10)

    # ----------------------------------------------------------------------- #

    png = convert_screenshot(screenshot_ppm) if screenshot_ppm.exists() else None

    print("\n" + "=" * 72)
    print(f"serial log : {serial_log}")
    if screenshot_ppm.exists():
        print(f"screenshot : {png or screenshot_ppm}")
    print("=" * 72)

    if verdict["result"] == "ok":
        print(f"PASS  {verdict['line']}")
        return 0

    print(f"FAIL  ({verdict['result']}) {verdict['line']}", file=sys.stderr)
    print("\n--- last 40 lines of serial console ---", file=sys.stderr)
    try:
        tail = serial_log.read_text(errors="replace").splitlines()[-40:]
        print("\n".join(tail), file=sys.stderr)
    except OSError:
        pass
    return 1


def dry_run(args: argparse.Namespace) -> int:
    """Validate everything we can without a disk image."""
    print("==> dry run (no VM is booted)")
    ok = True

    if shutil.which("qemu-system-x86_64"):
        print("  PASS  qemu-system-x86_64 on PATH")
    else:
        print("  FAIL  qemu-system-x86_64 not found")
        ok = False

    try:
        print(f"  PASS  UEFI firmware: {find_ovmf()}")
    except BootTestError as exc:
        print(f"  FAIL  {exc}")
        ok = False

    print(f"  {'PASS' if kvm_available() else 'WARN'}  /dev/kvm usable: {kvm_available()}")

    # Exercise command construction so a typo here fails the dry run.
    try:
        args.qcow2 = args.qcow2 or "/nonexistent/disk.qcow2"
        command = build_qemu_command(args, "/tmp/kidnix-dry.sock")
        assert "-snapshot" in command, "-snapshot missing: would mutate the disk image"
        assert any(a.startswith("unix:") for a in command), "QMP socket missing"
        print(f"  PASS  qemu command builds ({len(command)} args, -snapshot present)")
    except (BootTestError, AssertionError) as exc:
        print(f"  FAIL  qemu command: {exc}")
        ok = False

    print(f"  PASS  markers: {MARKER_OK} / {MARKER_FAIL}")
    print("\n" + ("dry run OK" if ok else "dry run FAILED"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qcow2", default="output/qcow2/disk.qcow2", help="disk image to boot")
    parser.add_argument("--output-dir", default="output", help="where to write log + screenshot")
    parser.add_argument("--timeout", type=int, default=300, help="seconds to wait for the marker")
    parser.add_argument(
        "--settle", type=float, default=5.0, help="seconds to wait before screenshot"
    )
    parser.add_argument("--memory", type=int, default=4096, help="VM RAM in MiB")
    parser.add_argument("--cpus", type=int, default=4, help="VM vCPUs")
    parser.add_argument("--ssh-port", type=int, default=2222, help="host port forwarded to :22")
    parser.add_argument("--verbose", action="store_true", help="tee the serial console to stdout")
    parser.add_argument("--dry-run", action="store_true", help="validate plumbing, boot nothing")
    args = parser.parse_args()

    try:
        return dry_run(args) if args.dry_run else run_boot_test(args)
    except BootTestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
