#!/usr/bin/python3
"""Band-over-activity spike driver. THROWAWAY -- not part of the test suite.

Boots the existing ``output/qcow2/disk.qcow2`` (snapshot mode, the developer's
disk is never written) and runs a series of window-configuration experiments
against the real gnome-kiosk 50.1 in the real image, screenshotting each one.

Everything it needs lives at runtime: ``window-config.ini`` is read from
``$XDG_CONFIG_HOME/gnome-kiosk/window-config.ini``, which is in the kid's home
and therefore writable over ssh. No image rebuild is required to change it.

Usage:  python3 tests/spikes/band/run_spike.py [--only NAME ...]
Output: output/spikes/band/*.png + a transcript on stdout.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
E2E = REPO / "tests" / "e2e"
for path in (str(E2E), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import vm as vm_module  # noqa: E402
from pixels import mean_colour, read_ppm  # noqa: E402
from vm import AS_KID, GuestVM, require_tools  # noqa: E402

# gnome-kiosk resolves window-config.ini exactly once, when the compositor
# starts, and only arms its GFileMonitor if the *user* config existed at that
# moment (kiosk-window-config.c: setup_file_monitoring returns early when
# user_config_file_path is NULL). So the file has to be on disk before GDM
# starts the session -- which is precisely what the harness's boot-time
# credential unit (Before=sshd.service gdm.service) is for. Once it exists,
# rewriting it in place is picked up live, which is what makes the experiments
# below cheap.
vm_module.SETUP_SCRIPT = vm_module.SETUP_SCRIPT.replace(
    'echo "{marker}" >/dev/console',
    """install -d -o kid -g kid -m 0755 /var/home/kid/.config /var/home/kid/.config/gnome-kiosk
printf '# seeded before gdm by the band spike\\n' >/var/home/kid/.config/gnome-kiosk/window-config.ini
chown kid:kid /var/home/kid/.config/gnome-kiosk/window-config.ini
install -d -m 0755 /run/systemd/user/org.gnome.Kiosk@wayland.service.d
printf '[Service]\\nEnvironment=G_MESSAGES_DEBUG=all\\n' \\
  >/run/systemd/user/org.gnome.Kiosk@wayland.service.d/debug.conf
echo "{marker}" >/dev/console""",
)

OUT = REPO / "output" / "spikes" / "band"
W, H = 1280, 800
BAND_H = 96
BAND_APP_ID = "org.kidnix.BandProto"
#: The band's fill, so a screenshot can be asked "is the top strip the band?"
BAND_RGB = (0x0F, 0x8A, 0x8A)

SESSION_TOML = (
    "length_minutes = 600\n"
    "daily_budget_minutes = 600\n"
    "ending_offer_minutes = 1\n"
    "put_away_minutes = 1\n"
    'bedtime_start = "03:00"\n'
    'bedtime_end = "03:01"\n'
)

# --------------------------------------------------------------------------- #
# The configurations under test.
# --------------------------------------------------------------------------- #

#: (b) the mechanism the docs advertise for panels. Predicted to FAIL against a
#: fullscreen activity: mutter's meta_window_get_default_layer drops a
#: META_WINDOW_DOCK to META_LAYER_BOTTOM when `monitor->in_fullscreen`.
CONFIG_DOCK = f"""
[band]
match-class={BAND_APP_ID}
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-window-type=dock
"""

#: (a) the mechanism that should work: `set-above` reaches
#: meta_window_make_above(), and wm_state_above is tested *before* the dock
#: branch and without any in_fullscreen check.
CONFIG_ABOVE = f"""
[band]
match-class={BAND_APP_ID}
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-above=true
"""

#: (a) full: band above + every other window constrained to the area below it.
#: Section order matters -- gnome-kiosk evaluates every section and the LAST
#: match wins, so [all] must come first.
CONFIG_FULL = f"""
[all]
set-fullscreen=false
set-x=0
set-y={BAND_H}
set-width={W}
set-height={H - BAND_H}
set-above=false
lock-on-area=0,{BAND_H} {W}x{H - BAND_H}

[band]
match-class={BAND_APP_ID}
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-above=true
"""

#: (a) the shape that should actually work. `lock-on-area` in [all] matches the
#: band too and there is no negation syntax -- but every "set" key is resolved
#: by scanning all sections and keeping the LAST match, so [band] can override
#: the catch-all's lock-on-area with its own strip instead of trying to unset
#: it. This is the whole trick.
CONFIG_BOTH_LOCKED = f"""
[all]
set-fullscreen=false
set-x=0
set-y={BAND_H}
set-width={W}
set-height={H - BAND_H}
set-above=false
lock-on-area=0,{BAND_H} {W}x{H - BAND_H}

[band]
match-class={BAND_APP_ID}
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-above=true
lock-on-area=0,0 {W}x{BAND_H}
"""

#: Does `match-class=tuxpaint` actually match? mutter sets a Wayland window's
#: wm_class from xdg_toplevel.set_app_id; SDL3 derives that from the app name.
#: If this constrains Tux Paint, the class is literally "tuxpaint".
CONFIG_MATCH_TUXPAINT = f"""
[activity]
match-class=tuxpaint
set-fullscreen=false
set-x=0
set-y={BAND_H}
set-width={W}
set-height={H - BAND_H}
set-above=false
lock-on-area=0,{BAND_H} {W}x{H - BAND_H}

[band]
match-class={BAND_APP_ID}
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-above=true
"""

#: (a) THE ANSWER. No catch-all: [all]'s lock-on-area cannot be overridden by a
#: later section (03/05 proved that -- the band was dragged down to y=96), and
#: there is no negation syntax, so activities are matched explicitly instead.
#: Tux Paint's wm_class is `TuxPaint.TuxPaint`, not `tuxpaint`; the compositor's
#: own debug log is the only place that tells you so.
CONFIG_FINAL = f"""
[activity-tuxpaint]
match-class=TuxPaint.TuxPaint
set-fullscreen=false
set-x=0
set-y={BAND_H}
set-width={W}
set-height={H - BAND_H}
set-above=false
lock-on-area=0,{BAND_H} {W}x{H - BAND_H}

[band]
match-class={BAND_APP_ID}
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-above=true
"""

#: (a) same, but with the REAL shell as the band instead of the stand-in.
CONFIG_REAL_SHELL = f"""
[all]
set-fullscreen=false
set-x=0
set-y={BAND_H}
set-width={W}
set-height={H - BAND_H}
set-above=false
lock-on-area=0,{BAND_H} {W}x{H - BAND_H}

[band]
match-class=org.kidnix.Shell
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
set-above=true
"""

#: (a) THE WORKING SHAPE. Geometry and fullscreen are only honoured while the
#: window is still "initial", i.e. during its first configure -- and at that
#: moment a Wayland toplevel has no app_id yet, so `match-class` cannot match
#: (07 proved it: the keys are read on a later pass and do nothing). Only a
#: catch-all section matches early enough to place a window.
#:
#: So the shell drives it in time instead of by name: while the band is the
#: only window the catch-all describes the *band's* strip; before launching an
#: activity the shell rewrites the file so the catch-all describes the area
#: *below* the band. gnome-kiosk re-reads on every write (its GFileMonitor),
#: and a window's initial config is consumed once, so the band keeps what it
#: was given.
CONFIG_PHASE_BAND = f"""
[all]
set-fullscreen=false
set-x=0
set-y=0
set-width={W}
set-height={BAND_H}
lock-on-area=0,0 {W}x{BAND_H}

[band]
match-class={BAND_APP_ID}
set-above=true
"""

CONFIG_PHASE_ACTIVITY = f"""
[all]
set-fullscreen=false
set-x=0
set-y={BAND_H}
set-width={W}
set-height={H - BAND_H}
set-above=false
lock-on-area=0,{BAND_H} {W}x{H - BAND_H}

[band]
match-class={BAND_APP_ID}
set-above=true
"""

CONFIG_NONE = ""

KID_CONFIG = "/var/home/kid/.config/gnome-kiosk/window-config.ini"


# --------------------------------------------------------------------------- #
# Guest helpers
# --------------------------------------------------------------------------- #


def as_kid_run(vm: GuestVM, command: str, check: bool = True) -> str:
    """Run a command in the kid's session with a working Wayland environment."""
    script = (
        "uid=$(id -u kid); "
        "runuser -u kid -- env "
        "XDG_RUNTIME_DIR=/run/user/$uid "
        "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus "
        "WAYLAND_DISPLAY=$(runuser -u kid -- env XDG_RUNTIME_DIR=/run/user/$uid "
        "systemctl --user show-environment | sed -n 's/^WAYLAND_DISPLAY=//p') "
        "XDG_CURRENT_DESKTOP=GNOME-Kiosk XDG_SESSION_TYPE=wayland "
        "DCONF_PROFILE=kid HOME=/var/home/kid "
        f"{command}"
    )
    return vm.ssh(script, check=check, timeout=120).stdout


def write_config(vm: GuestVM, text: str) -> None:
    """Rewrite the kid's window-config.ini *in place*.

    In place matters. gnome-kiosk resolves the config path once, at compositor
    start-up (kiosk_window_config_load), and
    kiosk_window_config_setup_file_monitoring returns early unless the *user*
    config file existed at that moment. So a file created after gnome-kiosk is
    running is never seen, however many times it is written -- but a file that
    existed at start-up is re-read on every G_FILE_MONITOR_EVENT_CHANGED.
    seed_config() + a reboot establishes the file; this then edits it.
    """
    body = text if text.strip() else "# deliberately empty\n"
    vm.ssh(
        "install -d -o kid -g kid -m 0755 /var/home/kid/.config/gnome-kiosk && "
        f"cat >{KID_CONFIG} <<'KIDNIX_WC_EOF'\n{body}\nKIDNIX_WC_EOF\n"
        f"chown kid:kid {KID_CONFIG}; sync"
    )
    # Give the compositor's GFileMonitor time to fire and reload.
    time.sleep(3)


def restart_session(vm: GuestVM, timeout: float = 180.0) -> None:
    """Restart GDM, and with it the kid's whole session (gnome-kiosk included).

    The VM runs with ``-no-reboot``, so `systemctl reboot` would take QEMU down
    with it. Restarting GDM is enough: it re-runs the autologin, which starts a
    fresh gnome-kiosk, which is the only moment window-config.ini is resolved.
    """
    vm.ssh("systemctl restart gdm", check=False, timeout=120)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(5)
        state = vm.ssh(
            AS_KID + "is-active kidnix-shell.service 2>/dev/null || true", check=False
        ).stdout.strip()
        if state == "active":
            time.sleep(8)  # painted, not merely active
            return
    raise RuntimeError("the kid session did not come back after restarting gdm")


def seed_config(vm: GuestVM) -> None:
    """Make the user config exist, then restart the session so it is found."""
    print("==> seeding window-config.ini and restarting the session")
    vm.ssh(
        "install -d -o kid -g kid -m 0755 /var/home/kid/.config/gnome-kiosk && "
        f"printf '# seeded by the band spike\\n' >{KID_CONFIG} && "
        f"chown kid:kid {KID_CONFIG}"
    )
    restart_session(vm)
    found = vm.ssh(
        "journalctl -b --no-pager -o cat | grep -c 'window-config.ini' || true", check=False
    ).stdout.strip()
    print(f"==> session back (window-config.ini journal mentions: {found})")


def start_band(vm: GuestVM) -> None:
    as_kid_run(
        vm,
        "setsid /usr/bin/python3 /var/home/kid/guest_band.py "
        f"{BAND_APP_ID} {BAND_H} '#0f8a8a' 'BAND  <  undo  star  sun  ear  cog' "
        ">/tmp/band.log 2>&1 &",
    )


def start_tuxpaint(vm: GuestVM) -> None:
    as_kid_run(vm, "setsid /usr/bin/tuxpaint >/tmp/tuxpaint.log 2>&1 &")


def kill_all(vm: GuestVM) -> None:
    # SIGKILL, by full command line, and *verified* -- a Tux Paint left over
    # from the previous experiment sits on top of the next one's band and
    # silently invalidates it (which is what the first run of this script did).
    for _ in range(10):
        vm.ssh(
            "pkill -9 -u kid -f guest_band.py; pkill -9 -u kid -f tuxpaint; true",
            check=False,
        )
        time.sleep(1.5)
        left = vm.ssh(
            "pgrep -u kid -a -f 'guest_band.py|tuxpaint' | grep -v defunct || true",
            check=False,
        ).stdout.strip()
        if not left:
            return
    raise RuntimeError(f"could not clear the previous experiment: {left}")


def shot(vm: GuestVM, name: str) -> Path:
    png = vm.screenshot(f"{name}.png")
    ppm = vm.screenshot(f"{name}.ppm")
    OUT.mkdir(parents=True, exist_ok=True)
    for src in (png, ppm):
        (OUT / src.name).write_bytes(src.read_bytes())
    return OUT / ppm.name


def describe(ppm: Path) -> str:
    """What is at the top of the screen, and what is below it?"""
    image = read_ppm(ppm)
    strip = mean_colour(image, (0, 0, W, BAND_H))
    below = mean_colour(image, (0, BAND_H + 20, W, H))
    close = all(abs(a - b) < 24 for a, b in zip(strip, BAND_RGB))
    return (
        f"top {BAND_H}px mean rgb={strip} "
        f"{'== BAND' if close else '!= band'} | below mean rgb={below}"
    )


# --------------------------------------------------------------------------- #
# Experiments
# --------------------------------------------------------------------------- #


def experiment(vm: GuestVM, name: str, config: str, real_shell: bool = False) -> None:
    print(f"\n=== {name} " + "=" * (60 - len(name)))
    kill_all(vm)
    write_config(vm, config)

    if real_shell:
        vm.ssh(AS_KID + "restart kidnix-shell.service")
        time.sleep(12)
    else:
        vm.ssh(AS_KID + "stop kidnix-shell.service", check=False)
        time.sleep(3)
        start_band(vm)
        time.sleep(6)

    ppm = shot(vm, f"{name}-1-band-only")
    print(f"  band alone      : {describe(ppm)}")

    start_tuxpaint(vm)
    time.sleep(18)
    ppm = shot(vm, f"{name}-2-activity")
    print(f"  activity running: {describe(ppm)}")

    # Does focus/interaction make gnome-kiosk re-fullscreen and cover the band?
    vm.click(W // 2, H // 2)
    time.sleep(3)
    ppm = shot(vm, f"{name}-3-after-click")
    print(f"  after a click   : {describe(ppm)}")

    windows = as_kid_run(
        vm,
        "sh -c 'ps -o pid=,args= -u kid | grep -E \"tuxpaint|guest_band\" | grep -v grep'",
        check=False,
    )
    print("  processes       : " + " / ".join(w.strip()[:70] for w in windows.splitlines()))
    print(
        "  tuxpaint log    : " + (as_kid_run(vm, "tail -5 /tmp/tuxpaint.log", check=False) or "-")
    )

    # What did the compositor actually decide, and about which window? The
    # `meta_window_get_description()` in every g_debug carries the wm_class,
    # which is the only reliable way to learn what `match-class` must say.
    kiosk = vm.ssh(
        "journalctl -b --no-pager -o cat _SYSTEMD_USER_UNIT=org.gnome.Kiosk@wayland.service "
        "| grep -E 'KioskWindowConfig' | tail -400 || true",
        check=False,
    ).stdout
    log = OUT / f"{name}-kiosk.log"
    log.write_text(kiosk)
    keep = [
        ln
        for ln in kiosk.splitlines()
        if any(
            k in ln
            for k in ("Using '", "Setting", "Fixed window", "Made window", "Locking", "Should make")
        )
    ]
    for line in keep[-24:]:
        print("    | " + line.strip()[:150])


KIOSK_DIR = REPO / "system_files" / "usr" / "share" / "kidnix" / "kiosk"


def render(template: str) -> str:
    """The production template, with the numbers the shell would substitute."""
    text = (KIOSK_DIR / template).read_text()
    for token, value in (
        ("@WIDTH@", W),
        ("@HEIGHT@", H),
        ("@BAND_HEIGHT@", BAND_H),
        ("@CONTENT_HEIGHT@", H - BAND_H),
    ):
        text = text.replace(token, str(value))
    return text


def start_window(vm: GuestVM, height: int, colour: str, label: str, title: str) -> None:
    """One shell-shaped window. Both share the app id; only the title differs."""
    as_kid_run(
        vm,
        "setsid /usr/bin/python3 /var/home/kid/guest_band.py "
        f"org.kidnix.Shell {height} '{colour}' '{label}' '{title}' "
        f">/tmp/{title.replace(' ', '-')}.log 2>&1 &",
    )


def experiment_production(vm: GuestVM, name: str = "09-production") -> None:
    """The exact shape system_files/usr/share/kidnix/kiosk/ ships, end to end."""
    print(f"\n=== {name} " + "=" * (60 - len(name)))
    kill_all(vm)
    vm.ssh(AS_KID + "stop kidnix-shell.service", check=False)
    vm.ssh("pkill -9 -u kid -f guest_band.py; true", check=False)
    time.sleep(3)

    write_config(vm, render("window-config.band.ini"))
    start_window(vm, BAND_H, "#0f8a8a", "BAND  <  undo  star  sun  ear  cog", "kidnix band")
    time.sleep(7)
    print(f"  band only       : {describe(shot(vm, f'{name}-1-band'))}")

    write_config(vm, render("window-config.activity.ini"))
    # Same process, second toplevel -- exactly how the shell will do it.
    vm.ssh("runuser -u kid -- touch /tmp/kidnix-make-content", check=False)
    time.sleep(7)
    print(f"  + content window: {describe(shot(vm, f'{name}-2-home'))}")

    start_tuxpaint(vm)
    time.sleep(18)
    print(f"  + activity      : {describe(shot(vm, f'{name}-3-activity'))}")

    vm.click(W // 2, H // 2 + 100)
    time.sleep(3)
    print(f"  after a click   : {describe(shot(vm, f'{name}-4-after-click'))}")

    vm.ssh("pkill -9 -u kid -f tuxpaint; true", check=False)
    time.sleep(5)
    print(f"  activity gone   : {describe(shot(vm, f'{name}-5-back-home'))}")


def experiment_rewrite(vm: GuestVM, name: str = "08-rewrite") -> None:
    """The two-phase config: band placed under one config, activity under the next."""
    print(f"\n=== {name} " + "=" * (60 - len(name)))
    kill_all(vm)
    vm.ssh(AS_KID + "stop kidnix-shell.service", check=False)
    time.sleep(3)

    write_config(vm, CONFIG_PHASE_BAND)
    start_band(vm)
    time.sleep(6)
    ppm = shot(vm, f"{name}-1-band-only")
    print(f"  band alone      : {describe(ppm)}")

    # The shell would do exactly this on its way into IN_ACTIVITY.
    write_config(vm, CONFIG_PHASE_ACTIVITY)
    ppm = shot(vm, f"{name}-2-after-reconfig")
    print(f"  after reconfig  : {describe(ppm)}   <- did the band stay put?")

    start_tuxpaint(vm)
    time.sleep(18)
    ppm = shot(vm, f"{name}-3-activity")
    print(f"  activity running: {describe(ppm)}")

    vm.click(W // 2, H // 2 + 100)
    time.sleep(3)
    ppm = shot(vm, f"{name}-4-after-click")
    print(f"  after a click   : {describe(ppm)}")

    # And back out again, the way "All done" would.
    vm.ssh("pkill -9 -u kid -f tuxpaint; true", check=False)
    time.sleep(4)
    write_config(vm, CONFIG_PHASE_BAND)
    ppm = shot(vm, f"{name}-5-back-home")
    print(f"  activity gone   : {describe(ppm)}")

    kiosk = vm.ssh(
        "journalctl -b --no-pager -o cat _SYSTEMD_USER_UNIT=org.gnome.Kiosk@wayland.service "
        "| grep -E 'KioskWindowConfig' | tail -400 || true",
        check=False,
    ).stdout
    (OUT / f"{name}-kiosk.log").write_text(kiosk)
    keep = [
        ln
        for ln in kiosk.splitlines()
        if any(
            k in ln
            for k in ("Using '", "Setting", "Fixed window", "Made window", "Locking", "constraint")
        )
    ]
    for line in keep[-22:]:
        print("    | " + line.strip()[:150])


EXPERIMENTS = {
    "00-baseline": (CONFIG_NONE, False),
    "01-dock": (CONFIG_DOCK, False),
    "02-above": (CONFIG_ABOVE, False),
    "03-above-plus-lock": (CONFIG_FULL, False),
    "05-both-locked": (CONFIG_BOTH_LOCKED, False),
    "06-match-tuxpaint": (CONFIG_MATCH_TUXPAINT, False),
    "07-final": (CONFIG_FINAL, False),
    "08-rewrite": (None, False),
    "09-production": (None, False),
    "04-real-shell": (CONFIG_REAL_SHELL, True),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    require_tools()
    OUT.mkdir(parents=True, exist_ok=True)
    vm = GuestVM(
        qcow2=REPO / "output" / "qcow2" / "disk.qcow2",
        output_dir=REPO / "output" / "e2e",
        ssh_port=2231,
        memory=4096,
        cpus=4,
        session_toml=SESSION_TOML,
    )
    print("==> booting (snapshot mode)")
    vm.start()
    try:
        vm.wait_for_ssh()
        print("==> up:", vm.boot_marker_line())

        subprocess.run(
            [
                "scp",
                "-P",
                str(vm.ssh_port),
                "-i",
                str(vm._key),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "LogLevel=ERROR",
                str(HERE / "guest_band.py"),
                "root@127.0.0.1:/var/home/kid/guest_band.py",
            ],
            check=True,
        )
        vm.ssh("chown kid:kid /var/home/kid/guest_band.py")
        print(
            "==> gnome-kiosk:", vm.out("rpm -q gnome-kiosk mutter gtk4 tuxpaint").replace("\n", " ")
        )

        seeded = vm.out(f"cat {KID_CONFIG} 2>/dev/null || echo MISSING", check=False)
        print(f"==> seeded at boot: {seeded!r}")

        names = args.only or list(EXPERIMENTS)
        for name in names:
            try:
                if name == "08-rewrite":
                    experiment_rewrite(vm)
                    continue
                if name == "09-production":
                    experiment_production(vm)
                    continue
                config, real_shell = EXPERIMENTS[name]
                experiment(vm, name, config, real_shell)
            except Exception as error:
                print(f"  !! {name} blew up: {error}")
    finally:
        vm.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
