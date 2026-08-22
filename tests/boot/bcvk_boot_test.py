#!/usr/bin/env python3
"""Rootless boot test: boot the kidnix *container image* as a VM with bcvk.

This is the fast loop. `bcvk ephemeral` boots the OCI image directly under
QEMU/KVM -- the container's filesystem is exported over virtiofs as the VM's
root, so there is no disk image to build and, crucially, **no sudo anywhere**.
A cold run takes well under a minute against an already-built image.

    just build && just test-boot

What it proves: the machine reaches graphical.target, GDM autologs `kid` in,
that session is a *Wayland* session, `gnome-kiosk` is actually running as
`kid`, kid's `graphical-session.target` is active (so the portals start), the
activity shell is running and comes back when it is killed, and `kid` genuinely
cannot reach the network while root can. That is the whole point of kidnix, and
none of it is visible to `just test-image`.

What it does NOT prove: anything about the bootloader, the composefs root,
partitioning, or first-boot units gated on real hardware -- `bcvk ephemeral`
boots the kernel directly and roots on virtiofs. `just test-boot-qcow2` is the
full-fidelity counterpart; run it before believing an image will install.

Python 3.9+, standard library only, deliberately: this runs unchanged on a CI
runner and on a dev laptop with nothing installed.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# bcvk lands here when installed by `just bcvk-install`; a distro package on
# PATH is preferred if one exists.
LOCAL_BIN = Path.home() / ".local" / "bin"

PROBE_BEGIN = "KIDNIX_PROBE_BEGIN"
PROBE_END = "KIDNIX_PROBE_END"

# systemd is chatty in colour and pipes through a pager even over ssh; both
# corrupt the key=value block we parse. Belt and braces: strip ANSI in Python.
ANSI = re.compile(r"\x1b\[[0-9;:]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

# `systemctl is-system-running` after a healthy boot. 'degraded' is accepted
# on purpose: under bcvk there is no ESP, so bootloader-update.service always
# fails. Individual units we care about are asserted by name instead.
HEALTHY_SYSTEM_STATES = frozenset({"running", "degraded"})

# Units allowed to be failed without failing the test, with the reason why.
# Keep this list short and justified -- it is the place a real regression hides.
EXPECTED_FAILED_UNITS = {
    "bootloader-update.service": "no ESP: bcvk ephemeral boots the kernel directly",
    # Same root cause, one layer up: bcvk roots the VM on virtiofs and never
    # mounts /boot, so greenboot's "am I allowed to mark this boot good"
    # bookkeeping (`Failed to check boot mount state: Failed to read mount
    # info`) cannot run. The health *checks* themselves pass -- the journal
    # shows all three required.d scripts succeeding. A disk boot
    # (`just test-boot-qcow2`) is where greenboot can actually be judged.
    "greenboot-healthcheck.service": "no /boot mount: bcvk ephemeral roots on virtiofs",
    "greenboot-set-rollback-trigger.service": "no /boot mount: bcvk ephemeral roots on virtiofs",
}

# How long the shell gets to come back after we kill it. kidnix-shell.service
# is Restart=always / RestartSec=1, so this is generous by an order of
# magnitude; it is a ceiling, not a target.
SHELL_RESTART_BUDGET_SECONDS = 10

# Runs inside the guest as root. Emits one key=value block we can parse, then
# a human-readable dump for the log. Must not use `sudo` (it decorates output
# with OSC sequences) and must not fail the ssh session on a missing tool.
GUEST_PROBE = r"""
set +e
export SYSTEMD_COLORS=0 SYSTEMD_PAGER=cat SYSTEMD_URLIFY=0 SYSTEMD_LESS=

# Block until the boot transaction settles, bounded by our own caller timeout.
systemctl is-system-running --wait >/dev/null 2>&1

# ...but `--wait` only covers the SYSTEM manager. Everything this probe cares
# about lives in kid's per-user manager, which GDM starts afterwards, so wait
# for the session to settle too. Without this every assertion below races the
# login: plymouth holds the console for the first ~10 s, and gnome-session has
# a great deal more to do than v0.1's `exec gnome-kiosk` did.
uctl() { systemctl --user -M kid@ "$@" 2>/dev/null; }

tries=0
while [ "$tries" -lt 90 ]; do
    [ "$(uctl is-active kidnix-shell.service)" = "active" ] && break
    sleep 1
    tries=$(( tries + 1 ))
done

scan_kid_session() {
    kid_session=""; kid_type=""; kid_active=""
    for s in $(loginctl list-sessions --no-legend --no-pager 2>/dev/null | awk '{print $1}'); do
        name=$(loginctl show-session "$s" -p Name --value 2>/dev/null)
        [ "$name" = "kid" ] || continue
        type=$(loginctl show-session "$s" -p Type --value 2>/dev/null)
        # Prefer a graphical session if the user also has a manager session.
        if [ -z "$kid_session" ] || [ "$type" = "wayland" ]; then
            kid_session="$s"; kid_type="$type"
            kid_active=$(loginctl show-session "$s" -p Active --value 2>/dev/null)
        fi
    done
}

tries=0
while [ "$tries" -lt 60 ]; do
    scan_kid_session
    [ "$kid_type" = "wayland" ] && [ "$kid_active" = "yes" ] && break
    sleep 1
    tries=$(( tries + 1 ))
done

kiosk_pid=$(pgrep -x gnome-kiosk 2>/dev/null | head -1)
kiosk_user=""
[ -n "$kiosk_pid" ] && kiosk_user=$(ps -o user= -p "$kiosk_pid" 2>/dev/null | tr -d ' ')

# --- kid's own systemd user manager -----------------------------------------
# `uctl` (defined above) is how root reaches kid's per-user manager; nothing
# below is visible any other way. graphical-session.target being ACTIVE is the
# whole point of routing the session through gnome-session: the portals carry
# `Requisite=graphical-session.target`, which fails instantly if it is not.
kid_graphical_session=$(uctl is-active graphical-session.target)
kid_session_target=$(uctl is-active gnome-session@kidnix.target)
kid_kiosk_target=$(uctl is-active org.gnome.Kiosk.target)
kid_portal=$(uctl is-active xdg-desktop-portal.service)
kid_portal_gnome=$(uctl is-active xdg-desktop-portal-gnome.service)
kid_shell_unit=$(uctl is-active kidnix-shell.service)

# --- the shell process -------------------------------------------------------
# Ask systemd for the PID rather than pgrep. `pgrep -f kidnix-shell-app` also
# matches THIS SCRIPT -- the probe text is the command line of the shell
# running it -- and killing that instead of the real shell is a silent, total
# failure (the probe dies before it prints anything). Learned the hard way.
shell_main_pid() { uctl show kidnix-shell.service -p MainPID --value; }

shell_pid=$(shell_main_pid)
[ "$shell_pid" = "0" ] && shell_pid=""
shell_user=""
[ -n "$shell_pid" ] && shell_user=$(ps -o user= -p "$shell_pid" 2>/dev/null | tr -d ' ')
# -u kid keeps the root-owned probe out of the match for the same reason.
session_leader=$(pgrep -u kid -f 'gnome-session-service --session=kidnix' 2>/dev/null | head -1)

# DCONF_PROFILE has to reach processes the *user manager* started, not merely
# children of the session wrapper (docs/spikes/lockdown.md section 3, item 2).
kiosk_dconf=""
[ -n "$kiosk_pid" ] && kiosk_dconf=$(tr '\0' '\n' < "/proc/${kiosk_pid}/environ" 2>/dev/null \
    | sed -n 's/^DCONF_PROFILE=//p' | head -1)
shell_dconf=""
[ -n "$shell_pid" ] && shell_dconf=$(tr '\0' '\n' < "/proc/${shell_pid}/environ" 2>/dev/null \
    | sed -n 's/^DCONF_PROFILE=//p' | head -1)

# --- egress (docs/spikes/lockdown.md section 3, item 3) ----------------------
# The single most important boot assertion the lockdown spike asked for: prove
# the nftables rule drops a real packet, not just that it loaded.
nft_table=absent
nft list table inet kidnix_egress >/dev/null 2>&1 && nft_table=loaded
curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_root=$?
runuser -u kid -- curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_kid=$?

# --- crash recovery ----------------------------------------------------------
# kidnix-shell.service is Restart=always/RestartSec=1, which replaced the bash
# supervisor. Kill the shell and time how long the child would stare at an
# empty compositor. Done last, because it perturbs the machine; `failed_units`
# below is therefore measured after it has settled.
shell_restart_pid=""
shell_restart_seconds=""
if [ -n "$shell_pid" ]; then
    kill -9 "$shell_pid" 2>/dev/null
    tries=0
    while [ "$tries" -lt 40 ]; do
        sleep 0.5
        tries=$(( tries + 1 ))
        candidate=$(shell_main_pid)
        if [ -n "$candidate" ] && [ "$candidate" != "0" ] && [ "$candidate" != "$shell_pid" ]; then
            shell_restart_pid="$candidate"
            shell_restart_seconds=$(awk "BEGIN{printf \"%.1f\", ${tries}/2}")
            break
        fi
    done
fi

# The unit passes through `deactivating` on its way back; wait for it to settle
# rather than photographing the restart mid-flight.
kid_shell_unit_after=""
tries=0
while [ "$tries" -lt 20 ]; do
    kid_shell_unit_after=$(uctl is-active kidnix-shell.service)
    [ "$kid_shell_unit_after" = "active" ] && break
    sleep 0.5
    tries=$(( tries + 1 ))
done

echo "KIDNIX_PROBE_BEGIN"
echo "system_running=$(systemctl is-system-running 2>/dev/null)"
echo "default_target=$(systemctl get-default 2>/dev/null)"
echo "gdm_enabled=$(systemctl is-enabled gdm 2>/dev/null)"
echo "gdm_active=$(systemctl is-active gdm 2>/dev/null)"
echo "kid_session=${kid_session}"
echo "kid_session_type=${kid_type}"
echo "kid_session_active=${kid_active}"
echo "kiosk_pid=${kiosk_pid}"
echo "kiosk_user=${kiosk_user}"
echo "kiosk_cmdline=$(tr '\0' ' ' < /proc/${kiosk_pid:-0}/cmdline 2>/dev/null)"
echo "kid_graphical_session=${kid_graphical_session}"
echo "kid_session_target=${kid_session_target}"
echo "kid_kiosk_target=${kid_kiosk_target}"
echo "kid_portal=${kid_portal}"
echo "kid_portal_gnome=${kid_portal_gnome}"
echo "kid_shell_unit=${kid_shell_unit}"
echo "kid_shell_unit_after=${kid_shell_unit_after}"
echo "shell_pid=${shell_pid}"
echo "shell_user=${shell_user}"
echo "session_leader=${session_leader}"
echo "kiosk_dconf=${kiosk_dconf}"
echo "shell_dconf=${shell_dconf}"
echo "shell_restart_pid=${shell_restart_pid}"
echo "shell_restart_seconds=${shell_restart_seconds}"
echo "nft_table=${nft_table}"
echo "egress_root=${egress_root}"
echo "egress_kid=${egress_kid}"
echo "failed_units=$(systemctl list-units --state=failed --no-legend --plain \
    --no-pager 2>/dev/null | awk '{print $1}' | paste -sd, -)"
echo "os_id=$(. /etc/os-release && echo "$ID")"
echo "os_version=$(. /etc/os-release && echo "$VERSION_ID")"
echo "kernel=$(uname -r)"
echo "hypervisor=$(systemd-detect-virt 2>/dev/null)"
echo "boot_time=$(systemd-analyze time 2>/dev/null | head -1)"
echo "graphical_target=$(systemd-analyze critical-chain graphical.target 2>/dev/null \
    | grep -o '@[0-9.]*m\?s' | head -1)"
echo "mem_used_mb=$(free -m | awk '/^Mem:/{print $3}')"
echo "mem_total_mb=$(free -m | awk '/^Mem:/{print $2}')"
echo "KIDNIX_PROBE_END"

echo "--- systemd-analyze blame (top 10) ---"
systemd-analyze blame --no-pager 2>/dev/null | head -10
echo "--- loginctl ---"
loginctl list-sessions --no-pager 2>/dev/null
echo "--- processes owned by kid ---"
ps -u kid -o pid,user,args --no-headers 2>/dev/null | head -30
echo "--- kid session units ---"
uctl list-units --state=failed --no-legend --plain 2>/dev/null
echo "--- the shell's own log ---"
journalctl -b _SYSTEMD_USER_UNIT=kidnix-shell.service --no-pager 2>/dev/null | tail -25
"""


class BootTestError(RuntimeError):
    """A failure to report cleanly rather than as a traceback."""


# --------------------------------------------------------------------------- #
# plumbing
# --------------------------------------------------------------------------- #


def find_bcvk() -> str:
    """bcvk from PATH, else the copy `just bcvk-install` drops in ~/.local/bin."""
    found = shutil.which("bcvk")
    if found:
        return found
    local = LOCAL_BIN / "bcvk"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    raise BootTestError(
        "bcvk not found on PATH or in ~/.local/bin.\nInstall it with: just bcvk-install"
    )


def kvm_available() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


def clean(text: str) -> str:
    return ANSI.sub("", text)


def run(cmd: list[str], timeout: float, check: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if check and proc.returncode != 0:
        raise BootTestError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{clean(proc.stderr).strip()}"
        )
    return proc


def parse_probe(text: str) -> dict[str, str]:
    """Pull the key=value block out of the guest probe's output."""
    body = clean(text)
    if PROBE_BEGIN not in body or PROBE_END not in body:
        raise BootTestError(
            "the guest probe did not produce a result block; the VM likely never "
            "became reachable.\n--- probe output ---\n" + body.strip()[-2000:]
        )
    block = body.split(PROBE_BEGIN, 1)[1].split(PROBE_END, 1)[0]
    values: dict[str, str] = {}
    for line in block.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


# --------------------------------------------------------------------------- #
# the VM
# --------------------------------------------------------------------------- #


class EphemeralVM:
    """A detached `bcvk ephemeral` VM, cleaned up on exit."""

    def __init__(self, bcvk: str, image: str, name: str, args: argparse.Namespace) -> None:
        self.bcvk = bcvk
        self.image = image
        self.name = name
        self.args = args
        self.started = False

    def __enter__(self) -> EphemeralVM:
        cmd = [
            self.bcvk,
            "ephemeral",
            "run",
            "--detach",
            "--rm",
            "--ssh-keygen",
            "--name",
            self.name,
            "--memory",
            self.args.memory,
            "--vcpus",
            str(self.args.cpus),
            "--log-dir",
            f"console={self.args.output_dir}",
            self.image,
        ]
        print(f"==> {' '.join(cmd)}", flush=True)
        run(cmd, timeout=180, check=True)
        self.started = True
        return self

    def __exit__(self, *_exc) -> None:
        if not self.started or self.args.keep:
            if self.args.keep:
                print(
                    f"\n==> VM left running as '{self.name}'.\n"
                    f"    shell in:  bcvk ephemeral ssh {self.name}\n"
                    f"    remove:    podman rm -f {self.name}"
                )
            return
        subprocess.run(
            ["podman", "rm", "-f", self.name],
            capture_output=True,
            check=False,
            timeout=120,
        )

    def ssh(self, script: str, timeout: float) -> subprocess.CompletedProcess:
        return run(
            [self.bcvk, "ephemeral", "ssh", self.name, "--", script],
            timeout=timeout,
        )

    def wait_for_ssh(self, deadline: float) -> float:
        """Poll until sshd answers. Returns seconds waited."""
        start = time.monotonic()
        last = ""
        while time.monotonic() < deadline:
            if not self.is_running():
                raise BootTestError(
                    f"the VM container '{self.name}' exited before ssh came up. "
                    f"See {self.args.output_dir}/console.txt"
                )
            proc = self.ssh("echo ready", timeout=30)
            if proc.returncode == 0 and "ready" in clean(proc.stdout):
                return time.monotonic() - start
            last = clean(proc.stderr).strip().splitlines()[-1:] or [""]
            time.sleep(2)
        raise BootTestError(
            f"the VM never became reachable over ssh within the timeout. "
            f"Last error: {last[0] if last else 'none'}\n"
            f"See {self.args.output_dir}/console.txt"
        )

    def is_running(self) -> bool:
        proc = run(["podman", "container", "exists", self.name], timeout=30)
        return proc.returncode == 0

    def qemu_used_kvm(self) -> bool | None:
        """Read the QEMU command line inside the VM container. None = unknown."""
        proc = run(
            [
                "podman",
                "exec",
                self.name,
                "sh",
                "-c",
                "tr '\\0' '\\n' < /proc/$(pgrep -f qemu-system | head -1)/cmdline",
            ],
            timeout=60,
        )
        if proc.returncode != 0:
            return None
        return "-enable-kvm" in proc.stdout


# --------------------------------------------------------------------------- #
# assertions
# --------------------------------------------------------------------------- #


class Checks:
    def __init__(self) -> None:
        self.results: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        self.results.append((ok, name, detail))
        return ok

    @property
    def failed(self) -> int:
        return sum(1 for ok, _, _ in self.results if not ok)

    @property
    def passed(self) -> int:
        return sum(1 for ok, _, _ in self.results if ok)

    def report(self) -> None:
        for ok, name, detail in self.results:
            mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
            print(f"  {mark}  {name}" + (f" -- {detail}" if detail else ""))


def assert_session(probe: dict[str, str], checks: Checks) -> None:
    """The gnome-session-shaped kid session, and the portals it finally allows.

    v0.1 exec'd gnome-kiosk directly, so `graphical-session.target` never
    activated and every `xdg-desktop-portal*` unit died on its
    `Requisite=graphical-session.target`. Routing the session through
    `gnome-session --session=kidnix` is the fix; these are the assertions that
    say so. See docs/spikes/session-integration.md.
    """
    for key, unit in (
        ("kid_graphical_session", "graphical-session.target"),
        ("kid_session_target", "gnome-session@kidnix.target"),
        ("kid_kiosk_target", "org.gnome.Kiosk.target"),
        ("kid_portal", "xdg-desktop-portal.service"),
        ("kid_portal_gnome", "xdg-desktop-portal-gnome.service"),
    ):
        state = probe.get(key, "")
        checks.check(state == "active", f"kid's {unit} is active (got '{state or 'unknown'}')")

    checks.check(
        bool(probe.get("session_leader")),
        "gnome-session is running the kidnix session",
        "" if probe.get("session_leader") else "no `gnome-session-service --session=kidnix`",
    )

    # The child's dconf profile has to reach processes the *user manager*
    # started, not merely children of /usr/bin/kidnix-shell. This is
    # docs/spikes/lockdown.md section 3 item 2, which could not be proven
    # anywhere but in a booted session.
    for key, who in (("kiosk_dconf", "gnome-kiosk"), ("shell_dconf", "the shell")):
        value = probe.get(key, "")
        checks.check(value == "kid", f"DCONF_PROFILE=kid reached {who} (got '{value or 'unset'}')")


def assert_shell(probe: dict[str, str], checks: Checks) -> None:
    """The activity shell is up, is kid's, and comes back when it is killed."""
    state = probe.get("kid_shell_unit", "")
    checks.check(state == "active", f"kidnix-shell.service is active (got '{state or 'unknown'}')")

    pid = probe.get("shell_pid", "")
    checks.check(bool(pid), "the activity shell is running", "" if pid else "no kidnix-shell-app")
    checks.check(
        probe.get("shell_user") == "kid",
        f"the activity shell runs as kid (got '{probe.get('shell_user') or 'nobody'}')",
    )

    # AGENTS.md non-negotiable 8, "crash-proof shell": SIGKILL the shell and
    # watch systemd put it back. This is what replaced the bash supervisor.
    restarted = probe.get("shell_restart_pid", "")
    seconds = probe.get("shell_restart_seconds", "")
    within = False
    try:
        within = bool(restarted) and float(seconds) <= SHELL_RESTART_BUDGET_SECONDS
    except ValueError:
        within = False
    checks.check(
        within,
        f"the shell comes back within {SHELL_RESTART_BUDGET_SECONDS}s of being killed"
        + (f" (took {seconds}s, pid {pid} -> {restarted})" if restarted else ""),
        "" if restarted else "it never came back",
    )

    after = probe.get("kid_shell_unit_after", "")
    checks.check(
        after == "active",
        f"kidnix-shell.service is active again after the kill (got '{after or 'unknown'}')",
    )


def assert_egress(probe: dict[str, str], checks: Checks) -> None:
    """AGENTS.md non-negotiable 5: the child session has no network egress.

    docs/spikes/lockdown.md section 3 item 3 called this "the single most
    important boot-test assertion to add" -- the image tests can only prove the
    ruleset *loads*, never that it drops a packet.
    """
    checks.check(
        probe.get("nft_table") == "loaded",
        f"nft table inet kidnix_egress is loaded (got '{probe.get('nft_table') or 'unknown'}')",
    )

    root_rc = probe.get("egress_root", "")
    kid_rc = probe.get("egress_kid", "")

    if root_rc != "0":
        # No route out of the VM at all: the differential is meaningless and a
        # "kid cannot reach the network" pass would be worthless. Say so.
        print(
            f"  \033[33mNOTE\033[0m  egress differential skipped -- root's own "
            f"`curl http://1.1.1.1` exited {root_rc or '?'}, so this VM has no "
            f"outbound network to be blocked from."
        )
        return

    checks.check(
        kid_rc not in ("", "0"),
        f"kid cannot reach the network (curl exited {kid_rc or '?'}; root got out fine)",
    )


def assert_probe(probe: dict[str, str], checks: Checks) -> None:
    state = probe.get("system_running", "")
    checks.check(
        state in HEALTHY_SYSTEM_STATES,
        f"system state is running/degraded (got '{state or 'unknown'}')",
    )

    target = probe.get("default_target", "")
    checks.check(
        target == "graphical.target",
        f"default target is graphical.target (got '{target or 'unknown'}')",
    )

    checks.check(
        probe.get("gdm_enabled") == "enabled",
        f"gdm is enabled (got '{probe.get('gdm_enabled', 'unknown')}')",
    )
    checks.check(
        probe.get("gdm_active") == "active",
        f"gdm is active (got '{probe.get('gdm_active', 'unknown')}')",
    )

    session = probe.get("kid_session", "")
    checks.check(bool(session), "user 'kid' has a logind session", "" if session else "none found")
    checks.check(
        probe.get("kid_session_type") == "wayland",
        f"kid's session Type=wayland (got '{probe.get('kid_session_type') or 'none'}')",
    )
    checks.check(
        probe.get("kid_session_active") == "yes",
        f"kid's session is active (got '{probe.get('kid_session_active') or 'none'}')",
    )

    checks.check(bool(probe.get("kiosk_pid")), "gnome-kiosk is running")
    checks.check(
        probe.get("kiosk_user") == "kid",
        f"gnome-kiosk runs as kid (got '{probe.get('kiosk_user') or 'nobody'}')",
    )

    assert_session(probe, checks)
    assert_shell(probe, checks)
    assert_egress(probe, checks)

    failed = [u for u in probe.get("failed_units", "").split(",") if u]
    unexpected = [u for u in failed if u not in EXPECTED_FAILED_UNITS]
    checks.check(
        not unexpected,
        "no unexpected failed units",
        ", ".join(unexpected),
    )
    for unit in failed:
        if unit in EXPECTED_FAILED_UNITS:
            print(f"  \033[33mNOTE\033[0m  {unit} failed -- {EXPECTED_FAILED_UNITS[unit]}")


# --------------------------------------------------------------------------- #
# main flow
# --------------------------------------------------------------------------- #


def capture_journal(vm: EphemeralVM, output_dir: Path) -> Path | None:
    """Save warning-and-worse journal from this boot -- the first thing to read."""
    proc = vm.ssh("export SYSTEMD_COLORS=0; journalctl -b -p warning --no-pager 2>&1", timeout=120)
    if proc.returncode != 0 and not proc.stdout.strip():
        print(f"warning: could not capture the journal: {clean(proc.stderr).strip()}")
        return None
    path = output_dir / "boot-journal.txt"
    path.write_text(clean(proc.stdout))
    return path


def note_no_screenshot() -> None:
    """Say plainly why there is no screenshot, so nobody re-investigates."""
    print(
        "\n  \033[33mSKIP\033[0m  screenshot -- `bcvk ephemeral` runs QEMU with\n"
        "        `-nographic -display none -monitor none`, so there is no QMP\n"
        "        socket and no VNC to screendump. gnome-kiosk does export\n"
        "        org.gnome.Shell.Screenshot, but it answers 'Access denied' even\n"
        "        to a caller running as `kid` inside kid's own session cgroup.\n"
        "        For pixels use:  just test-boot-qcow2   (QMP screendump)\n"
        "                     or:  just vm-graphical      (SPICE + virsh screenshot)"
    )


def run_boot_test(args: argparse.Namespace) -> int:
    bcvk = find_bcvk()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    proc = run(["podman", "image", "exists", args.image], timeout=60)
    if proc.returncode != 0:
        raise BootTestError(f"image not found: {args.image}\nRun: just build")

    if not kvm_available():
        print(
            "warning: /dev/kvm is not usable -- bcvk will fall back to software\n"
            "         emulation, which will not boot a GNOME stack inside the timeout.",
            file=sys.stderr,
        )

    name = args.name or f"kidnix-boot-{os.getpid()}"
    deadline = time.monotonic() + args.timeout
    checks = Checks()
    started = time.monotonic()

    with EphemeralVM(bcvk, args.image, name, args) as vm:
        waited = vm.wait_for_ssh(deadline)
        print(f"==> ssh reachable after {waited:.1f}s")

        used_kvm = vm.qemu_used_kvm()

        remaining = max(30.0, deadline - time.monotonic())
        result = vm.ssh(GUEST_PROBE, timeout=remaining)
        if args.verbose:
            print(clean(result.stdout))

        probe = parse_probe(result.stdout)
        journal = capture_journal(vm, output_dir)

    elapsed = time.monotonic() - started

    print("\n" + "=" * 72)
    print(f"image      : {args.image}")
    print(
        f"os         : {probe.get('os_id', '?')} {probe.get('os_version', '?')} "
        f"kernel {probe.get('kernel', '?')}"
    )
    print(
        f"virt       : {probe.get('hypervisor', '?')}, "
        f"KVM used: {'yes' if used_kvm else 'no' if used_kvm is False else 'unknown'}"
    )
    print(f"boot       : {probe.get('boot_time', '?')}")
    if probe.get("graphical_target"):
        print(f"graphical  : reached at {probe['graphical_target'].lstrip('@')}")
    print(
        f"memory     : {probe.get('mem_used_mb', '?')} MiB used of "
        f"{probe.get('mem_total_mb', '?')} MiB"
    )
    print(f"kiosk      : {probe.get('kiosk_cmdline') or 'not running'}")
    print(f"shell      : pid {probe.get('shell_pid') or '-'} as {probe.get('shell_user') or '-'}")
    print(
        f"kid session: graphical-session={probe.get('kid_graphical_session', '?')} "
        f"portal={probe.get('kid_portal', '?')} shell={probe.get('kid_shell_unit', '?')}"
    )
    print(f"console log: {output_dir / 'console.txt'}")
    if journal:
        print(f"journal    : {journal}")
    print(f"wall clock : {elapsed:.1f}s")
    print("=" * 72)

    assert_probe(probe, checks)
    checks.report()
    note_no_screenshot()

    print()
    if checks.failed == 0:
        print(f"\033[32mPASS\033[0m  {checks.passed} checks, kidnix booted into the kiosk.")
        return 0

    print(
        f"\033[31mFAIL\033[0m  {checks.failed} of {checks.passed + checks.failed} checks failed.",
        file=sys.stderr,
    )
    if journal:
        print(f"\nFirst 30 lines of {journal}:", file=sys.stderr)
        print("\n".join(journal.read_text().splitlines()[:30]), file=sys.stderr)
    return 1


def dry_run(args: argparse.Namespace) -> int:
    """Everything we can validate without booting anything."""
    print("==> dry run (no VM is booted)")
    ok = True

    try:
        print(f"  PASS  bcvk: {find_bcvk()}")
    except BootTestError as exc:
        print(f"  FAIL  {exc}")
        ok = False

    if shutil.which("podman"):
        print("  PASS  podman on PATH")
    else:
        print("  FAIL  podman not found")
        ok = False

    print(f"  {'PASS' if kvm_available() else 'WARN'}  /dev/kvm usable: {kvm_available()}")

    if run(["podman", "image", "exists", args.image], timeout=60).returncode == 0:
        print(f"  PASS  image present: {args.image}")
    else:
        print(f"  WARN  image not built yet: {args.image} (run 'just build')")

    try:
        sample = (
            f"noise\n{PROBE_BEGIN}\nsystem_running=running\nkid_session_type=wayland\n"
            f"{PROBE_END}\ntail"
        )
        parsed = parse_probe(sample)
        assert parsed["system_running"] == "running"
        assert parsed["kid_session_type"] == "wayland"
        print(f"  PASS  probe parser ({len(parsed)} keys from a synthetic block)")
    except (BootTestError, AssertionError, KeyError) as exc:
        print(f"  FAIL  probe parser: {exc}")
        ok = False

    print("\n" + ("dry run OK" if ok else "dry run FAILED"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", default="localhost/kidnix:latest", help="image to boot")
    parser.add_argument("--output-dir", default="output", help="where logs are written")
    parser.add_argument("--timeout", type=int, default=360, help="overall seconds budget")
    parser.add_argument("--memory", default="4G", help="VM RAM (bcvk syntax, e.g. 4G)")
    parser.add_argument("--cpus", type=int, default=4, help="VM vCPUs")
    parser.add_argument("--name", default="", help="container name for the VM")
    parser.add_argument("--keep", action="store_true", help="leave the VM running afterwards")
    parser.add_argument("--verbose", action="store_true", help="print the raw guest probe")
    parser.add_argument("--dry-run", action="store_true", help="validate plumbing, boot nothing")
    args = parser.parse_args()

    try:
        return dry_run(args) if args.dry_run else run_boot_test(args)
    except BootTestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired as exc:
        print(f"error: timed out running {exc.cmd}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
