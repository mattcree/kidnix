"""Boot the kidnix qcow2 under QEMU and drive it from outside.

Same VM ``just test-boot-qcow2`` boots -- ``-snapshot`` so the developer's disk
image is never touched, UEFI, virtio-vga so there is a framebuffer to
``screendump`` -- plus three things this test needs and that one does not:

* an **absolute pointing device** (``usb-tablet``). q35's default PS/2 mouse is
  relative, and you cannot put a relative pointer on a known pixel.
* a **QMP socket** held open for the whole run, not just for one screenshot.
* **an SSH key for root, injected at boot**, so every assertion can be made
  inside the guest instead of guessed from pixels.

That last one is the only clever part. ``build-qcow2-rootless`` applies no
blueprint, so the disk has no passwords and no authorised keys
(docs/BUILDING.md) -- and mutating the image to add one would defeat the point
of testing the image we ship. Instead the harness passes **systemd system
credentials** over QEMU's SMBIOS type 11 OEM strings::

    -smbios type=11,value=io.systemd.credential.binary:systemd.extra-unit.NAME=<base64>

``systemd-debug-generator`` turns ``systemd.extra-unit.<name>`` and
``systemd.unit-dropin.<unit>`` credentials into real units, so the harness can
land a one-shot service that runs before sshd and gdm. It drops an ephemeral
public key into ``/root/.ssh`` and writes the session policy the scenario needs.
Nothing in the image changes: the key is generated per run into ``output/e2e/``
and the guest filesystem is a throwaway ``-snapshot`` overlay.

Two roads that look easier and are not:

* ``fw_cfg name=opt/io.systemd.credentials/...`` caps the whole name at 55
  characters. The prefix eats 27 of them and ``systemd.extra-unit.x.service``
  needs 37, so the interesting credentials do not fit. SMBIOS has no such cap.
* systemd's own ``ssh.authorized_keys.root`` credential *is* imported (it fits
  in 55 characters, and the serial log confirms PID 1 receives it) but it never
  lands. ``/usr/lib/tmpfiles.d/provision.conf`` writes it through
  ``d- /root`` -- and on a bootc image ``/root`` is a symlink to
  ``var/roothome``, so systemd-tmpfiles will not create the directory and the
  key is silently dropped. See docs/spikes/e2e-scenario.md.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from qmp import QMPClient

MARKER_OK = "KIDNIX_BOOT_OK"
MARKER_FAIL = "KIDNIX_BOOT_FAIL"

PANIC_MARKERS = (
    "Kernel panic",
    "Entering emergency mode",
    "You are in emergency mode",
)

OVMF_CANDIDATES = (
    "/usr/share/OVMF/OVMF_CODE.fd",
    "/usr/share/edk2/ovmf/OVMF_CODE.fd",
    "/usr/share/qemu/ovmf-x86_64-code.bin",
    "/usr/share/OVMF/OVMF_CODE_4M.fd",
)

SESSION_TOML = "/etc/kidnix/session.toml"

MARKER_SETUP = "KIDNIX_E2E_SETUP_OK"

#: Injected as the credential ``systemd.extra-unit.kidnix-e2e.service``.
SETUP_UNIT = """\
[Unit]
Description=kidnix end-to-end test setup (host-injected, ephemeral)
Before=sshd.service gdm.service
ConditionPathExists=/run/credentials/@system/kidnix-e2e-setup

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/bash /run/credentials/@system/kidnix-e2e-setup
StandardOutput=journal+console
StandardError=journal+console
"""

#: Injected as ``systemd.unit-dropin.multi-user.target``. Without this nothing
#: pulls the extra unit into the boot transaction ([Install] is not processed
#: for generated units).
TARGET_DROPIN = """\
[Unit]
Wants=kidnix-e2e.service
"""

#: Injected as the credential ``kidnix-e2e-setup`` and run by the unit above.
SETUP_SCRIPT = """\
set -eu
install -d -m 0700 /root/.ssh
cat >/root/.ssh/authorized_keys <<'KIDNIX_KEY_EOF'
{pubkey}
KIDNIX_KEY_EOF
chmod 0600 /root/.ssh/authorized_keys
install -d -m 0755 /etc/kidnix
cat >/etc/kidnix/session.toml <<'KIDNIX_SESSION_EOF'
{session}
KIDNIX_SESSION_EOF
chmod 0644 /etc/kidnix/session.toml
echo "{marker}" >/dev/console
"""

#: Run one command in the kid's own systemd user manager, without machined.
AS_KID = (
    "runuser -u kid -- env XDG_RUNTIME_DIR=/run/user/$(id -u kid) "
    "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u kid)/bus systemctl --user "
)


class VMError(RuntimeError):
    """Something went wrong booting or talking to the VM."""


def find_ovmf() -> str:
    for candidate in OVMF_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise VMError("no OVMF/UEFI firmware found; install edk2-ovmf")


def kvm_available() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


@dataclass
class GuestVM:
    """A booted kidnix machine, drivable over QMP and ssh."""

    qcow2: Path
    output_dir: Path
    ssh_port: int = 2223
    memory: int = 4096
    cpus: int = 4
    width: int = 1280
    height: int = 800
    boot_timeout: float = 420.0
    session_toml: str = ""

    proc: subprocess.Popen = field(default=None, init=False)
    qmp: QMPClient = field(default=None, init=False)
    serial_log: Path = field(init=False)
    _key: Path = field(init=False)

    # -- lifecycle ---------------------------------------------------------

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.serial_log = self.output_dir / "serial.log"
        self._key = self.output_dir / "id_ed25519"

    def _make_key(self) -> Path:
        """An ephemeral keypair, regenerated on every run."""
        for suffix in ("", ".pub"):
            path = Path(str(self._key) + suffix)
            if path.exists():
                path.unlink()
        subprocess.run(
            [
                "ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "kidnix-e2e",
                "-f",
                str(self._key),
            ],
            check=True,
            capture_output=True,
        )
        return Path(str(self._key) + ".pub")

    def qemu_command(self, qmp_socket: Path) -> list:
        pubkey = self._make_key()
        accel = ["-machine", "q35,accel=kvm", "-cpu", "host"]
        if not kvm_available():
            accel = ["-machine", "q35", "-cpu", "max"]
        return [
            "qemu-system-x86_64",
            *accel,
            "-smp",
            str(self.cpus),
            "-m",
            str(self.memory),
            # Never mutate the disk image the developer built.
            "-snapshot",
            "-bios",
            find_ovmf(),
            "-drive",
            f"file={self.qcow2},if=virtio,format=qcow2",
            "-netdev",
            f"user,id=net0,hostfwd=tcp::{self.ssh_port}-:22",
            "-device",
            "virtio-net-pci,netdev=net0",
            "-device",
            "virtio-rng-pci",
            # A framebuffer screendump can read. No GL: the host's GL display
            # would put the pixels somewhere QEMU cannot dump them.
            "-device",
            f"virtio-vga,xres={self.width},yres={self.height}",
            "-display",
            "none",
            # An ABSOLUTE pointer. Without it the guest has only q35's PS/2
            # mouse and QMP can only nudge a relative pointer around blindly.
            "-device",
            "qemu-xhci,id=xhci",
            "-device",
            "usb-tablet,bus=xhci.0",
            "-serial",
            f"file:{self.serial_log}",
            "-qmp",
            f"unix:{qmp_socket},server=on,wait=off",
            "-no-reboot",
            *self._credential_args(pubkey.read_text().strip()),
        ]

    def _credential_args(self, pubkey: str) -> list:
        """SMBIOS type 11 strings PID 1 imports as system credentials."""
        setup = SETUP_SCRIPT.format(
            pubkey=pubkey, session=self.session_toml.strip(), marker=MARKER_SETUP
        )
        (self.output_dir / "guest-setup.sh").write_text(setup)
        credentials = {
            "systemd.extra-unit.kidnix-e2e.service": SETUP_UNIT,
            "systemd.unit-dropin.multi-user.target": TARGET_DROPIN,
            "kidnix-e2e-setup": setup,
        }
        args = []
        for name, text in credentials.items():
            blob = base64.b64encode(text.encode()).decode()
            args += ["-smbios", f"type=11,value=io.systemd.credential.binary:{name}={blob}"]
        return args

    def start(self) -> GuestVM:
        if self.serial_log.exists():
            self.serial_log.unlink()
        qmp_socket = self.output_dir / "qmp.sock"
        if qmp_socket.exists():
            qmp_socket.unlink()

        command = self.qemu_command(qmp_socket)
        (self.output_dir / "qemu-command.txt").write_text(" ".join(command) + "\n")
        log = (self.output_dir / "qemu.log").open("wb")
        self.proc = subprocess.Popen(
            command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
        )
        self.qmp = QMPClient(qmp_socket).connect()
        self.wait_for_boot()
        return self

    def stop(self) -> None:
        if self.qmp is not None:
            self.qmp.close()
            self.qmp = None
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    # -- boot --------------------------------------------------------------

    def serial_text(self) -> str:
        try:
            return self.serial_log.read_text(errors="replace")
        except OSError:
            return ""

    def wait_for_boot(self) -> None:
        deadline = time.monotonic() + self.boot_timeout
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise VMError(f"qemu exited early with status {self.proc.returncode}")
            text = self.serial_text()
            if MARKER_OK in text:
                return
            if MARKER_FAIL in text:
                line = next(ln for ln in text.splitlines() if MARKER_FAIL in ln)
                raise VMError(f"the guest reported a failed boot: {line.strip()}")
            for panic in PANIC_MARKERS:
                if panic in text:
                    raise VMError(f"the guest died early: {panic}")
            time.sleep(1.0)
        raise VMError(
            f"no {MARKER_OK} on the serial console within {self.boot_timeout:.0f}s\n"
            + "\n".join(self.serial_text().splitlines()[-25:])
        )

    def boot_marker_line(self) -> str:
        for line in self.serial_text().splitlines():
            if MARKER_OK in line:
                return line.strip()
        return ""

    # -- ssh ---------------------------------------------------------------

    def ssh(self, script: str, timeout: float = 90.0, check: bool = True):
        """Run ``script`` in the guest as root. Returns the CompletedProcess."""
        command = [
            "ssh",
            "-p",
            str(self.ssh_port),
            "-i",
            str(self._key),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "LogLevel=ERROR",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "BatchMode=yes",
            "root@127.0.0.1",
            "--",
            "export SYSTEMD_COLORS=0 SYSTEMD_PAGER=cat; " + script,
        ]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if check and proc.returncode != 0:
            raise VMError(
                f"ssh command failed ({proc.returncode}): {script}\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        return proc

    def out(self, script: str, **kwargs) -> str:
        return self.ssh(script, **kwargs).stdout.strip()

    def wait_for_ssh(self, timeout: float = 180.0) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            proc = self.ssh("echo ready", timeout=30, check=False)
            if proc.returncode == 0 and "ready" in proc.stdout:
                return
            last = (proc.stderr or proc.stdout).strip()
            time.sleep(2)
        raise VMError(f"root ssh never came up within {timeout:.0f}s: {last}")

    # -- the shell ---------------------------------------------------------

    def write_session_policy(self, toml: str) -> None:
        """Replace the root-owned session policy. Takes effect on restart."""
        self.ssh(
            "install -d -m 0755 /etc/kidnix && "
            f"cat >{SESSION_TOML} <<'KIDNIX_E2E_EOF'\n{toml}\nKIDNIX_E2E_EOF\n"
            f"chmod 0644 {SESSION_TOML}"
        )

    def restart_shell(self, timeout: float = 60.0) -> str:
        """Restart kidnix-shell.service in the kid's user manager and wait.

        Returns a journal cursor taken *before* the restart, so a caller can
        tell the new shell's log lines from the old shell's identical ones.
        """
        cursor = self.journal_cursor()
        self.ssh(AS_KID + "restart kidnix-shell.service")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.out(AS_KID + "is-active kidnix-shell.service", check=False) == "active":
                # Active is not the same as painted: wait for the line the
                # shell logs once it has measured the monitor and laid out.
                self.wait_for_shell_log("display metrics:", timeout=30, since_cursor=cursor)
                return cursor
            time.sleep(1)
        raise VMError("kidnix-shell.service did not come back after a restart")

    def shell_journal(self, since_cursor: str = "") -> str:
        """Everything ``kidnix-shell.service`` has logged, as the kid user."""
        after = f"--after-cursor '{since_cursor}' " if since_cursor else ""
        return self.out(
            "journalctl -b --no-pager -o cat "
            f"_SYSTEMD_USER_UNIT=kidnix-shell.service {after}2>/dev/null || true"
        )

    def journal_cursor(self) -> str:
        """A cursor for :meth:`shell_journal`, so stale lines cannot match."""
        return self.out(
            "journalctl -b --no-pager -n1 -o export "
            "_SYSTEMD_USER_UNIT=kidnix-shell.service 2>/dev/null "
            "| sed -n 's/^__CURSOR=//p' || true"
        )

    def wait_for_shell_log(self, needle: str, timeout: float = 20.0, since_cursor: str = "") -> str:
        """Poll the shell's journal until ``needle`` appears. Returns the line."""
        deadline = time.monotonic() + timeout
        text = ""
        while True:
            text = self.shell_journal(since_cursor)
            for line in text.splitlines():
                if needle in line:
                    return line
            if time.monotonic() >= deadline:
                break
            time.sleep(1.0)
        tail = "\n".join(text.splitlines()[-25:])
        raise VMError(f"the shell never logged {needle!r} within {timeout:.0f}s\n{tail}")

    # -- pixels ------------------------------------------------------------

    def screenshot(self, name: str) -> Path:
        assert self.qmp is not None
        return self.qmp.screendump(self.output_dir / name)

    # -- input -------------------------------------------------------------

    def click(self, x: int, y: int) -> None:
        self.qmp.click(x, y, self.width, self.height)

    def move(self, x: int, y: int) -> None:
        self.qmp.move_to(x, y, self.width, self.height)

    def drag(self, points: list, step_delay: float = 0.05) -> None:
        self.qmp.drag(points, self.width, self.height, step_delay)

    def key(self, *qcodes: str) -> None:
        self.qmp.key(*qcodes)


def require_tools() -> None:
    for tool in ("qemu-system-x86_64", "ssh", "ssh-keygen"):
        if shutil.which(tool) is None:
            raise VMError(f"{tool} is not on PATH")
    find_ovmf()


# --------------------------------------------------------------------------- #
# `just vm-qmp`: hold a VM open so a human can drive it with `just vm-qmp-*`.
# --------------------------------------------------------------------------- #


def main(argv: list | None = None) -> int:
    import argparse
    import datetime

    parser = argparse.ArgumentParser(description="Boot the kidnix qcow2 with a QMP socket.")
    parser.add_argument("--qcow2", default="output/qcow2/disk.qcow2")
    parser.add_argument("--output-dir", default="output/e2e")
    parser.add_argument("--ssh-port", type=int, default=2223)
    parser.add_argument("--memory", type=int, default=4096)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument(
        "--session-minutes", type=float, default=25.0, help="override the session length"
    )
    args = parser.parse_args(argv)

    far = (datetime.datetime.now() + datetime.timedelta(hours=6)).replace(second=0, microsecond=0)
    policy = (
        f"length_minutes = {args.session_minutes}\n"
        "daily_budget_minutes = 600\n"
        "ending_offer_minutes = 6\n"
        "put_away_minutes = 2\n"
        f'bedtime_start = "{far:%H:%M}"\n'
        f'bedtime_end = "{(far + datetime.timedelta(minutes=1)):%H:%M}"\n'
    )
    vm = GuestVM(
        qcow2=Path(args.qcow2),
        output_dir=Path(args.output_dir),
        ssh_port=args.ssh_port,
        memory=args.memory,
        cpus=args.cpus,
        session_toml=policy,
    )
    print(f"==> booting {args.qcow2} (snapshot mode)")
    vm.start()
    print(f"==> {vm.boot_marker_line()}")
    vm.wait_for_ssh()
    print(
        "==> the VM is up. From another terminal:\n"
        "      just vm-qmp-shot            # -> output/e2e/qmp-shot.png\n"
        "      just vm-qmp-click 640 400\n"
        "      just vm-qmp-key esc\n"
        f"      ssh -p {vm.ssh_port} -i {vm._key} root@127.0.0.1\n"
        "    Ctrl-C here destroys it."
    )
    try:
        while vm.proc is not None and vm.proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n==> shutting down")
    finally:
        vm.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
