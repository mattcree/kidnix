#!/usr/bin/env python3
"""Prove that a bad update rolls itself back (AGENTS.md non-negotiable #8).

This is the test behind the single largest untested claim in kidnix -- "it
cannot be broken". Everything else about greenboot is asserted *structurally*
(the checks exist, the GRUB snippet is installed); this boots a real machine,
switches it onto an image whose required health check fails on purpose, and
watches until the machine puts itself back on the deployment that worked.

    just build-selftest-broken     # the deliberately unhealthy image
    just test-rollback             # ~4 min, slow, nightly

What it does
------------
1. Copies-on-write ``output/qcow2/disk.qcow2`` into ``output/rollback/disk.qcow2``
   (a qcow2 overlay: instant, and the developer's disk image is never written).
   This test CANNOT use ``-snapshot`` like the other boot tests: the whole
   subject is state that has to survive a reboot -- the staged deployment and
   GRUB's ``boot_counter`` in ``/boot/grub2/grubenv``.
2. Boots it under QEMU with a QMP socket, the serial console teed to
   ``output/rollback/serial.log``, and an ephemeral SSH key injected through
   SMBIOS system credentials (the same trick as tests/e2e/vm.py -- nothing in
   the image is modified to make it testable).
3. Over ssh: ``bootc switch`` onto the broken image served by the local
   registry on the host (10.0.2.2:5000 through QEMU user networking), reboot.
4. Watches the serial console across every subsequent boot. An injected probe
   unit prints one line per boot saying which deployment booted and what GRUB's
   boot_counter/boot_success are, and greenboot's own verdict is forced onto
   the console with a drop-in.
5. Asserts the machine ends up back on the ORIGINAL deployment, green, with the
   child's shell running.

Python 3.9+, standard library only, same as the other boot harnesses.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The sys.path shim above must run before this import.
from boot_test import (
    MARKER_FAIL,
    MARKER_OK,
    BootTestError,
    QMPClient,
    convert_screenshot,
    find_ovmf,
    firmware_args,
    kvm_available,
)

# The greenboot check that only ever exists in a --build-arg
# KIDNIX_SELFTEST_BREAK_HEALTH=1 build. Its presence in the booted deployment
# is how the guest tells us which of the two images it is running -- far more
# robust than parsing `bootc status` JSON, whose schema is bootc's to change.
BROKEN_CHECK = "/usr/lib/greenboot/check/required.d/99-kidnix-selftest-broken.sh"

MARKER_SETUP = "KIDNIX_ROLLBACK_SETUP_OK"
MARKER_PROBE = "KIDNIX_ROLLBACK_PROBE"

PROBE_RE = re.compile(
    MARKER_PROBE
    + r" boot_id=(?P<boot_id>\S+) deployment=(?P<deployment>\S+) grubenv=\{(?P<env>[^}]*)\}"
)

PANIC_MARKERS = (
    "Kernel panic",
    "Entering emergency mode",
    "You are in emergency mode",
)

# Injected at boot as a system credential; runs before sshd so every boot --
# original deployment or broken one -- is reachable.
SETUP_UNIT = """\
[Unit]
Description=kidnix rollback test setup (host-injected, ephemeral)
Before=sshd.service gdm.service greenboot-healthcheck.service
ConditionPathExists=/run/credentials/@system/kidnix-rollback-setup

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/bash /run/credentials/@system/kidnix-rollback-setup
StandardOutput=journal+console
StandardError=journal+console
"""

# One line per boot, early, on the serial console: which deployment came up and
# what GRUB left in the boot counter. Ordered before greenboot so the counter is
# the value the *bootloader* wrote, not the value greenboot rewrote.
PROBE_UNIT = """\
[Unit]
Description=kidnix rollback probe (host-injected, ephemeral)
After=local-fs.target
Before=greenboot-healthcheck.service
RequiresMountsFor=/boot
ConditionPathExists=/run/credentials/@system/kidnix-rollback-probe

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/bash /run/credentials/@system/kidnix-rollback-probe
StandardOutput=journal+console
StandardError=journal+console
"""

# [Install] is not processed for generated units, so something has to pull them
# into the boot transaction.
TARGET_DROPIN = """\
[Unit]
Wants=kidnix-rollback-setup.service kidnix-rollback-probe.service
"""

# greenboot's verdict normally only reaches the journal, and a machine that is
# rebooting itself every 60s is a bad place to read journals from. Put it on the
# serial console instead, where it is captured for free.
GREENBOOT_DROPIN = """\
[Service]
StandardOutput=journal+console
StandardError=journal+console
"""

SETUP_SCRIPT = """\
set -eu
install -d -m 0700 /root/.ssh
cat >/root/.ssh/authorized_keys <<'KIDNIX_KEY_EOF'
{pubkey}
KIDNIX_KEY_EOF
chmod 0600 /root/.ssh/authorized_keys

# The local registry is plain HTTP on the host. This is TEST-TIME ONLY config,
# written into the running machine's /etc -- the image ships no insecure
# registry and must not. (The image's signature policy needs no help: the
# default `docker: ""` scope inherited from the base is insecureAcceptAnything,
# and only ghcr.io/mattcree/kidnix demands a signature.)
install -d -m 0755 /etc/containers/registries.conf.d
cat >/etc/containers/registries.conf.d/99-kidnix-rollback-test.conf <<'KIDNIX_REG_EOF'
[[registry]]
location = "{registry}"
insecure = true
KIDNIX_REG_EOF
{fix}
echo "{marker}" >/dev/console
"""

#: The proposed fix from docs/spikes/rollback.md, injected into the guest by
#: --with-proposed-fix so the spike can prove it works before anyone ships it.
#: DELETE this and the flag once the real script is in system_files/.
#:
#: greenboot-rs 0.16.3 DOES roll back on its own (`bootc rollback`, once
#: boot_counter hits 0) -- but it never decrements the counter, because that is
#: GRUB's job in bootupd's 08_greenboot.cfg, and GRUB cannot write grubenv when
#: /boot is btrfs. So the counter sticks and the machine reboot-loops forever.
#: Decrementing it from Linux, where writing btrfs is not a problem, is all that
#: is missing.
FIX_SCRIPT = r"""
install -d -m 0755 /etc/greenboot/red.d
cat >/etc/greenboot/red.d/10-kidnix-boot-counter.sh <<'KIDNIX_FIX_EOF'
#!/usr/bin/bash
# Decrement greenboot's boot_counter from userspace.
#
# GRUB cannot write /boot/grub2/grubenv when /boot is btrfs, so the
# `decrement boot_counter` in bootupd's 08_greenboot.cfg never happens and
# greenboot's own rollback -- which fires when the counter reaches 0 -- is
# never reached. Without this the machine reboot-loops on a bad update forever.
set -uo pipefail
GRUBENV=/boot/grub2/grubenv
counter="$(grub2-editenv "${GRUBENV}" list 2>/dev/null | sed -n 's/^boot_counter=//p')"
[[ "${counter}" =~ ^-?[0-9]+$ ]] || exit 0
(( counter <= 0 )) && exit 0
remounted=0
if findmnt -no OPTIONS /boot | tr ',' '\n' | grep -qx ro; then
    mount -o remount,rw /boot && remounted=1
fi
grub2-editenv "${GRUBENV}" set "boot_counter=$(( counter - 1 ))"
rc=$?
(( remounted )) && mount -o remount,ro /boot
echo "kidnix: boot_counter ${counter} -> $(( counter - 1 )) (GRUB cannot write a btrfs /boot)"
exit "${rc}"
KIDNIX_FIX_EOF
chmod 0755 /etc/greenboot/red.d/10-kidnix-boot-counter.sh
echo "KIDNIX_ROLLBACK_FIX_INSTALLED" >/dev/console
"""

PROBE_SCRIPT = """\
set -u
boot_id="$(tr -d - </proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)"
if [ -e "{broken_check}" ]; then
    deployment=BROKEN
else
    deployment=ORIGINAL
fi
env="$(grub2-editenv /boot/grub2/grubenv list 2>/dev/null | tr '\\n' ' ' || true)"
printf '{marker} boot_id=%s deployment=%s grubenv={{%s}}\\n' \
    "$boot_id" "$deployment" "$env" >/dev/console
"""

#: Run one command in the kid's own systemd user manager. `systemctl --user -M
#: kid@` needs systemd-container (machined), which this image does not ship;
#: runuser with the runtime dir set by hand is the equivalent.
AS_KID = (
    "runuser -u kid -- env XDG_RUNTIME_DIR=/run/user/$(id -u kid) "
    "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u kid)/bus systemctl --user "
)


# --------------------------------------------------------------------------- #
# results
# --------------------------------------------------------------------------- #


@dataclass
class Results:
    """Ordered PASS/FAIL record, printed as the test's verdict."""

    checks: list = field(default_factory=list)

    def record(self, ok: bool, name: str, detail: str = "") -> bool:
        self.checks.append((bool(ok), name, detail))
        mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
        print(f"  {mark}  {name}{(' -- ' + detail) if detail else ''}", flush=True)
        return bool(ok)

    @property
    def failed(self) -> int:
        return sum(1 for ok, _, _ in self.checks if not ok)

    def summary(self) -> str:
        total = len(self.checks)
        return f"{total - self.failed}/{total} checks passed"


@dataclass
class Probe:
    boot_id: str
    deployment: str
    grubenv: dict

    @property
    def broken(self) -> bool:
        return self.deployment == "BROKEN"


def parse_probes(text: str) -> list:
    """One entry per boot, in order.

    Deduplicated by ``boot_id`` (the kernel's, so it is genuinely one per boot):
    the probe writes to ``/dev/console`` *and* the unit forwards its output to
    the console, so the same line can land on the serial log twice, and not
    always adjacently.
    """
    probes: list = []
    seen: set = set()
    for match in PROBE_RE.finditer(text):
        boot_id = match.group("boot_id")
        if boot_id in seen:
            continue
        seen.add(boot_id)
        env = {}
        for item in match.group("env").split():
            if "=" in item:
                key, _, value = item.partition("=")
                env[key] = value
        probes.append(Probe(boot_id, match.group("deployment"), env))
    return probes


# --------------------------------------------------------------------------- #
# the machine
# --------------------------------------------------------------------------- #


@dataclass
class RollbackVM:
    """A kidnix machine that is allowed to reboot itself, repeatedly."""

    qcow2: Path
    output_dir: Path
    registry: str
    ssh_port: int = 2224
    memory: int = 4096
    cpus: int = 4
    with_fix: bool = False

    proc: subprocess.Popen = field(default=None, init=False)
    qmp: QMPClient = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.serial_log = self.output_dir / "serial.log"
        self._key = self.output_dir / "id_ed25519"

    # -- credentials -------------------------------------------------------

    def _make_key(self) -> str:
        for suffix in ("", ".pub"):
            path = Path(str(self._key) + suffix)
            if path.exists():
                path.unlink()
        keygen = ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "kidnix-rollback"]
        subprocess.run([*keygen, "-f", str(self._key)], check=True, capture_output=True)
        return Path(str(self._key) + ".pub").read_text().strip()

    def _credential_args(self) -> list:
        setup = SETUP_SCRIPT.format(
            pubkey=self._make_key(),
            registry=self.registry,
            marker=MARKER_SETUP,
            fix=FIX_SCRIPT if self.with_fix else "",
        )
        probe = PROBE_SCRIPT.format(broken_check=BROKEN_CHECK, marker=MARKER_PROBE)
        (self.output_dir / "guest-setup.sh").write_text(setup)
        (self.output_dir / "guest-probe.sh").write_text(probe)
        credentials = {
            "systemd.extra-unit.kidnix-rollback-setup.service": SETUP_UNIT,
            "systemd.extra-unit.kidnix-rollback-probe.service": PROBE_UNIT,
            "systemd.unit-dropin.multi-user.target": TARGET_DROPIN,
            "systemd.unit-dropin.greenboot-healthcheck.service": GREENBOOT_DROPIN,
            "kidnix-rollback-setup": setup,
            "kidnix-rollback-probe": probe,
        }
        args = []
        for name, text in credentials.items():
            blob = base64.b64encode(text.encode()).decode()
            args += ["-smbios", f"type=11,value=io.systemd.credential.binary:{name}={blob}"]
        return args

    # -- lifecycle ---------------------------------------------------------

    def qemu_command(self, qmp_socket: Path) -> list:
        accel = ["-machine", "q35,accel=kvm", "-cpu", "host"]
        if not kvm_available():
            accel = ["-machine", "q35", "-cpu", "max"]
        # fmt: off
        return [
            "qemu-system-x86_64",
            *accel,
            "-smp", str(self.cpus),
            "-m", str(self.memory),
            # NO -snapshot and NO -no-reboot. Both would defeat this test: the
            # staged deployment and boot_counter must survive, and the guest
            # must be able to reboot itself as many times as greenboot wants.
            *firmware_args(os.path.dirname(os.path.abspath(self.qcow2))),
            "-drive", f"file={self.qcow2},if=virtio,format=qcow2",
            "-netdev", f"user,id=net0,hostfwd=tcp::{self.ssh_port}-:22",
            "-device", "virtio-net-pci,netdev=net0",
            "-device", "virtio-rng-pci",
            "-device", "virtio-vga",
            "-display", "none",
            "-serial", "stdio",
            "-qmp", f"unix:{qmp_socket},server=on,wait=off",
            *self._credential_args(),
        ]
        # fmt: on

    def start(self, verbose: bool = False) -> RollbackVM:
        if self.serial_log.exists():
            self.serial_log.unlink()
        qmp_socket = self.output_dir / "qmp.sock"
        if qmp_socket.exists():
            qmp_socket.unlink()

        command = self.qemu_command(qmp_socket)
        (self.output_dir / "qemu-command.txt").write_text(" ".join(command) + "\n")
        self.proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            bufsize=0,
        )
        self._pump = threading.Thread(target=self._pump_serial, args=(verbose,), daemon=True)
        self._pump.start()
        self.qmp = QMPClient(str(qmp_socket))
        self.qmp.connect()
        return self

    def _pump_serial(self, verbose: bool) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        with self.serial_log.open("wb") as log:
            for raw in iter(self.proc.stdout.readline, b""):
                log.write(raw)
                log.flush()
                if verbose or MARKER_PROBE in raw.decode("utf-8", "replace"):
                    sys.stdout.buffer.write(b"    | " + raw)
                    sys.stdout.buffer.flush()

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

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    # -- the serial console ------------------------------------------------

    def serial_text(self) -> str:
        try:
            return self.serial_log.read_text(errors="replace")
        except OSError:
            return ""

    def probes(self) -> list:
        return parse_probes(self.serial_text())

    def wait_for_boot(self, timeout: float, offset: int = 0) -> str:
        """Wait for the boot that starts at ``offset`` in the serial log.

        ``offset`` matters: this machine boots many times and the log is one
        continuous stream, so a plain search would match the *first* boot's
        marker every time.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.alive():
                raise BootTestError(f"qemu exited with status {self.proc.returncode}")
            text = self.serial_text()[offset:]
            if MARKER_OK in text:
                for line in text.splitlines():
                    if MARKER_OK in line:
                        return line.strip()
                return MARKER_OK
            if MARKER_FAIL in text:
                line = next(ln for ln in text.splitlines() if MARKER_FAIL in ln)
                raise BootTestError(f"the guest reported a failed boot: {line.strip()}")
            for panic in PANIC_MARKERS:
                if panic in text:
                    raise BootTestError(f"the guest died early: {panic}")
            # The reporter shares ttyS0 with agetty's login prompt, so the
            # marker can arrive shredded by escape sequences. Once a prompt is
            # up, ask the journal instead (tests/e2e/vm.py hit the same thing).
            if "login:" in text:
                journal = self.ssh(
                    "journalctl -b -t kidnix-boot-report --no-pager -o cat 2>/dev/null | tail -5",
                    timeout=30,
                    check=False,
                )
                if MARKER_OK in (journal.stdout or ""):
                    return (journal.stdout or "").strip().splitlines()[-1]
            time.sleep(2)
        raise BootTestError(f"no {MARKER_OK} within {timeout:.0f}s")

    def screenshot(self, name: str) -> Path | None:
        if self.qmp is None or not self.alive():
            return None
        ppm = self.output_dir / name
        try:
            self.qmp.execute("screendump", filename=str(ppm))
        except BootTestError:
            return None
        for _ in range(50):
            if ppm.exists() and ppm.stat().st_size:
                break
            time.sleep(0.1)
        return convert_screenshot(ppm) or ppm

    # -- ssh ---------------------------------------------------------------

    def ssh(self, script: str, timeout: float = 120.0, check: bool = True):
        # fmt: off
        command = [
            "ssh",
            "-p", str(self.ssh_port),
            "-i", str(self._key),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "IdentitiesOnly=yes",
            "-o", "LogLevel=ERROR",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
            "root@127.0.0.1",
            "--",
            "export SYSTEMD_COLORS=0 SYSTEMD_PAGER=cat; " + script,
        ]
        # fmt: on
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise BootTestError(f"ssh timed out after {timeout:.0f}s: {script}") from exc
        if check and proc.returncode != 0:
            raise BootTestError(
                f"ssh failed ({proc.returncode}): {script}\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        return proc

    def out(self, script: str, **kwargs) -> str:
        return self.ssh(script, **kwargs).stdout.strip()

    def wait_for_ssh(self, timeout: float = 240.0) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            if not self.alive():
                raise BootTestError("qemu exited while waiting for ssh")
            proc = self.ssh("echo ready", timeout=30, check=False)
            if proc.returncode == 0 and "ready" in proc.stdout:
                return
            last = (proc.stderr or proc.stdout).strip()
            time.sleep(3)
        raise BootTestError(f"root ssh never came up within {timeout:.0f}s: {last}")


# --------------------------------------------------------------------------- #
# guest state
# --------------------------------------------------------------------------- #


def booted_image(vm: RollbackVM) -> str:
    """The image reference of the currently booted deployment, best effort."""
    raw = vm.out("bootc status --format=json 2>/dev/null || true", check=False)
    try:
        status = json.loads(raw)
    except (ValueError, TypeError):
        return ""
    booted = (status.get("status") or {}).get("booted") or {}
    image = (booted.get("image") or {}).get("image") or {}
    ref = image.get("image") or ""
    digest = (booted.get("image") or {}).get("imageDigest") or ""
    return f"{ref}@{digest[:19]}" if digest else ref


def guest_state(vm: RollbackVM) -> dict:
    broken = vm.out(f"test -e {BROKEN_CHECK} && echo yes || echo no", check=False) == "yes"
    return {
        "deployment": "BROKEN" if broken else "ORIGINAL",
        "image": booted_image(vm),
        "bootc": vm.out("bootc status 2>&1 | head -40", check=False),
        "grubenv": vm.out(
            "grub2-editenv /boot/grub2/grubenv list 2>&1 | tr '\\n' ' '", check=False
        ),
        "greenboot": vm.out(
            "systemctl is-active greenboot-healthcheck.service 2>&1 | head -1", check=False
        ),
        "motd": vm.out("cat /run/motd.d/*greenboot* 2>/dev/null | head -5", check=False),
    }


# --------------------------------------------------------------------------- #
# the test
# --------------------------------------------------------------------------- #


def prepare_overlay(source: Path, target: Path) -> None:
    """A copy-on-write overlay, so the source qcow2 is never written."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    # fmt: off
    subprocess.run(
        [
            "qemu-img", "create", "-q", "-f", "qcow2",
            "-F", "qcow2", "-b", str(source.resolve()), str(target),
        ],
        check=True,
    )
    # fmt: on


def run(args: argparse.Namespace) -> int:
    source = Path(args.qcow2)
    if not source.is_file():
        raise BootTestError(f"disk image not found: {source}\nRun: just build-qcow2-rootless")

    output_dir = Path(args.output_dir)
    work_disk = output_dir / "disk.qcow2"
    results = Results()
    started = time.monotonic()
    deadline = started + args.timeout

    print(f"==> overlay {work_disk} on {source} (the source is never written)")
    prepare_overlay(source, work_disk)

    vm = RollbackVM(
        qcow2=work_disk,
        output_dir=output_dir,
        registry=args.registry,
        ssh_port=args.ssh_port,
        memory=args.memory,
        cpus=args.cpus,
        with_fix=args.with_proposed_fix,
    )

    timeline: list = []

    def note(text: str) -> None:
        stamp = time.monotonic() - started
        timeline.append(f"[{stamp / 60:5.1f}m] {text}")
        print(f"\n==> [{stamp / 60:5.1f}m] {text}", flush=True)

    try:
        note("booting the ORIGINAL deployment")
        vm.start(verbose=args.verbose)
        marker = vm.wait_for_boot(args.boot_timeout)
        print(f"    {marker}")
        vm.wait_for_ssh()

        before = guest_state(vm)
        results.record(
            before["deployment"] == "ORIGINAL",
            "the machine starts on a healthy deployment",
            before["image"] or before["deployment"],
        )
        results.record(
            MARKER_SETUP in vm.serial_text(),
            "the test's own setup unit ran (ssh key + insecure registry)",
        )

        # ---- switch onto the broken image --------------------------------
        note(f"bootc switch --> {args.image}")
        switch = vm.ssh(
            f"bootc switch --transport registry {args.image} 2>&1", timeout=900, check=False
        )
        sig_fallback = False
        if switch.returncode != 0:
            print(switch.stdout[-2000:])
            note("plain switch failed; retrying with --enforce-container-sigpolicy=false")
            sig_fallback = True
            switch = vm.ssh(
                "bootc switch --transport registry --enforce-container-sigpolicy=false "
                f"{args.image} 2>&1",
                timeout=900,
                check=False,
            )
        (output_dir / "bootc-switch.log").write_text(switch.stdout + switch.stderr)
        if not results.record(
            switch.returncode == 0,
            "bootc switch staged the broken image",
            ("needed --enforce-container-sigpolicy=false" if sig_fallback else "default policy")
            if switch.returncode == 0
            else switch.stdout.strip()[-300:],
        ):
            raise BootTestError("could not stage the broken image; nothing to roll back")

        staged = vm.out("bootc status 2>&1 | head -40", check=False)
        (output_dir / "bootc-status-staged.txt").write_text(staged)

        note("rebooting onto the broken deployment")
        vm.ssh("systemctl reboot", timeout=30, check=False)

        # ---- watch it fail its way home ----------------------------------
        seen_broken = False
        rolled_back = False
        boots: list = []
        broken_run: list = []
        looping = False
        last_count = 0
        rollback_offset = 0
        while time.monotonic() < deadline:
            if not vm.alive():
                note("qemu exited -- the guest powered off instead of rebooting")
                break
            probes = vm.probes()
            if len(probes) > last_count:
                for probe in probes[last_count:]:
                    counter = probe.grubenv.get("boot_counter", "-")
                    success = probe.grubenv.get("boot_success", "-")
                    note(
                        f"boot #{len(boots) + 1}: {probe.deployment} "
                        f"(boot_counter={counter} boot_success={success})"
                    )
                    boots.append(probe)
                    if probe.broken:
                        seen_broken = True
                        broken_run.append(probe.grubenv.get("boot_counter"))
                    elif seen_broken:
                        rolled_back = True
                        # Where this boot starts in the log, so the wait below
                        # cannot match the very first boot's marker.
                        rollback_offset = len(vm.serial_text())
                last_count = len(probes)
            if rolled_back:
                break
            # A machine that reboots every few seconds and never moves the
            # counter is not "still working on it", it is bricked. Say so now
            # rather than at the end of the budget.
            if len(broken_run) >= args.loop_limit and len(set(broken_run)) <= 1:
                looping = True
                note(
                    f"REBOOT LOOP: {len(broken_run)} boots of the broken deployment, "
                    f"boot_counter stuck at {broken_run[-1]}"
                )
                break
            time.sleep(3)

        results.record(seen_broken, "the broken deployment actually booted")

        broken_boots = sum(1 for p in boots if p.broken)
        counters = [p.grubenv.get("boot_counter") for p in boots if p.broken]
        results.record(
            any(c is not None for c in counters),
            "GRUB's boot_counter is armed on the broken deployment",
            f"seen: {counters}",
        )
        decreasing = [int(c) for c in counters if c is not None and c.lstrip("-").isdigit()]
        results.record(
            len(decreasing) >= 2 and all(b <= a for a, b in zip(decreasing, decreasing[1:])),
            "boot_counter decrements on every failed boot",
            f"{decreasing}",
        )
        results.record(
            rolled_back,
            "the machine rolled ITSELF back to the original deployment",
            f"after {broken_boots} boot(s) of the broken image",
        )

        if not rolled_back:
            note("NO ROLLBACK -- collecting evidence from wherever we are")
            try:
                vm.wait_for_ssh(timeout=120)
                stuck = guest_state(vm)
                (output_dir / "stuck-state.txt").write_text(json.dumps(stuck, indent=2))
                print(json.dumps(stuck, indent=2))
            except BootTestError as exc:
                print(f"    (no ssh: {exc})")
            raise BootTestError(
                (
                    f"REBOOT LOOP: {broken_boots} boots of the broken deployment with "
                    f"boot_counter stuck at {broken_run[-1] if broken_run else '?'}"
                )
                if looping
                else (
                    f"no rollback within {args.timeout / 60:.0f} min "
                    f"({broken_boots} boots of the broken deployment)"
                )
            )

        # ---- and back on its feet ----------------------------------------
        note("waiting for the rolled-back deployment to come all the way up")
        marker = vm.wait_for_boot(args.boot_timeout, offset=rollback_offset)
        print(f"    {marker}")
        vm.wait_for_ssh()
        after = guest_state(vm)
        (output_dir / "final-state.txt").write_text(json.dumps(after, indent=2))

        results.record(
            after["deployment"] == "ORIGINAL",
            "the booted deployment is the original one, not the broken one",
            after["image"],
        )
        results.record(
            bool(before["image"]) and after["image"] == before["image"],
            "bootc agrees it is the image we started from",
            f"{before['image']} -> {after['image']}",
        )
        results.record(
            after["greenboot"] == "active",
            "greenboot is green again on the rolled-back deployment",
            after["greenboot"],
        )
        shell = vm.out(AS_KID + "is-active kidnix-shell.service", check=False)
        results.record(shell == "active", "the child's shell is running again", shell)

        shot = vm.screenshot("rollback.ppm")
        if shot:
            print(f"    screenshot: {shot}")

    except BootTestError as exc:
        results.record(False, "the test ran to completion", str(exc).splitlines()[0])
    finally:
        with contextlib.suppress(Exception):  # best effort; we are already leaving
            vm.screenshot("rollback-final.ppm")
        vm.stop()
        (output_dir / "timeline.txt").write_text("\n".join(timeline) + "\n")

    elapsed = (time.monotonic() - started) / 60
    print("\n" + "=" * 72)
    for line in timeline:
        print(line)
    print("=" * 72)
    print(f"serial log : {vm.serial_log}")
    print(f"artifacts  : {output_dir}")
    print(f"elapsed    : {elapsed:.1f} min")
    print(f"{results.summary()}")
    if results.failed:
        print(
            "\033[31mFAIL\033[0m  a bad update did NOT roll itself back"
            " -- see docs/spikes/rollback.md",
            file=sys.stderr,
        )
        print("\n--- last 60 lines of serial console ---", file=sys.stderr)
        print("\n".join(vm.serial_text().splitlines()[-60:]), file=sys.stderr)
        return 1
    print("\033[32mPASS\033[0m  a bad update rolled itself back unattended")
    return 0


def dry_run(args: argparse.Namespace) -> int:
    """Everything that can be checked without booting anything."""
    print("==> dry run (no VM is booted)")
    ok = True
    for tool in ("qemu-system-x86_64", "qemu-img", "ssh", "ssh-keygen"):
        found = shutil.which(tool) is not None
        ok &= found
        print(f"  {'PASS' if found else 'FAIL'}  {tool} on PATH")
    try:
        print(f"  PASS  UEFI firmware: {find_ovmf()}")
    except BootTestError as exc:
        print(f"  FAIL  {exc}")
        ok = False
    print(f"  {'PASS' if kvm_available() else 'WARN'}  /dev/kvm usable: {kvm_available()}")

    vm = RollbackVM(
        qcow2=Path(args.qcow2 or "/nonexistent"),
        output_dir=Path(args.output_dir),
        registry=args.registry,
        ssh_port=args.ssh_port,
    )
    command = vm.qemu_command(Path(args.output_dir) / "qmp.sock")
    for forbidden, why in (
        ("-snapshot", "the staged deployment must survive a reboot"),
        ("-no-reboot", "the guest must be able to reboot itself"),
    ):
        absent = forbidden not in command
        ok &= absent
        print(f"  {'PASS' if absent else 'FAIL'}  {forbidden} is absent ({why})")
    creds = sum(1 for a in command if a.startswith("type=11,"))
    print(f"  {'PASS' if creds == 6 else 'FAIL'}  {creds} SMBIOS credentials injected")
    ok &= creds == 6

    sample = "\n".join(
        [
            f"{MARKER_PROBE} boot_id=abc deployment=BROKEN grubenv={{boot_counter=2 boot_success=0 }}",
            "some other console noise",
            # the same boot, echoed a second time by the unit's console forwarding
            f"{MARKER_PROBE} boot_id=abc deployment=BROKEN grubenv={{boot_counter=2 boot_success=0 }}",
            f"{MARKER_PROBE} boot_id=def deployment=ORIGINAL grubenv={{}}",
        ]
    )
    probes = parse_probes(sample)
    parsed = (
        len(probes) == 2
        and probes[0].broken
        and probes[0].grubenv["boot_counter"] == "2"
        and not probes[1].broken
    )
    ok &= parsed
    print(f"  {'PASS' if parsed else 'FAIL'}  the probe parser round-trips and dedupes by boot_id")

    for path in (Path(args.output_dir) / "id_ed25519", Path(args.output_dir) / "id_ed25519.pub"):
        if path.exists():
            path.unlink()
    print("\n" + ("dry run OK" if ok else "dry run FAILED"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qcow2", default="output/qcow2/disk.qcow2", help="the known-good disk")
    parser.add_argument("--output-dir", default="output/rollback")
    parser.add_argument(
        "--image",
        default="10.0.2.2:5000/kidnix:selftest-broken",
        help="the deliberately unhealthy image, as the GUEST sees it",
    )
    parser.add_argument(
        "--registry",
        default="10.0.2.2:5000",
        help="registry host:port to mark insecure inside the guest",
    )
    parser.add_argument("--timeout", type=float, default=1800.0, help="overall budget, seconds")
    parser.add_argument("--boot-timeout", type=float, default=420.0, help="per-boot budget")
    parser.add_argument("--memory", type=int, default=4096)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--ssh-port", type=int, default=2224)
    parser.add_argument(
        "--loop-limit",
        type=int,
        default=6,
        help="give up after this many boots of the broken image with an unchanged counter",
    )
    parser.add_argument(
        "--with-proposed-fix",
        action="store_true",
        help="inject the boot_counter fix from docs/spikes/rollback.md into the guest "
        "(temporary: proves the fix before it is shipped in system_files/)",
    )
    parser.add_argument("--verbose", action="store_true", help="tee the whole serial console")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.environ.get("PYTHONDONTWRITEBYTECODE"):
        sys.dont_write_bytecode = True

    try:
        return dry_run(args) if args.dry_run else run(args)
    except BootTestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
