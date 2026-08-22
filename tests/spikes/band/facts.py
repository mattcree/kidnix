#!/usr/bin/python3
"""Facts the band spike needs that pixels cannot answer. THROWAWAY.

Two questions:

* **(b)/(c)** Is Tux Paint a native Wayland client or an XWayland one? Its
  wm_class comes back as ``TuxPaint.TuxPaint``, which looks like an X11
  ``res_name.res_class`` pair -- and if it *is* X11 then ``_NET_WM_STRUT`` is
  on the table for it, which changes what option (b) is worth.
* **(e)** Does a gnome-settings-daemon custom keybinding actually fire inside a
  gnome-kiosk session, with no gnome-shell to own the shortcut? If it does, the
  interim "global escape" is a dconf entry and nothing else.

Usage: python3 tests/spikes/band/facts.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
for path in (str(REPO / "tests" / "e2e"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import vm as vm_module  # noqa: E402
from run_spike import SESSION_TOML, start_tuxpaint  # noqa: E402
from vm import AS_KID, GuestVM, require_tools  # noqa: E402

vm_module.SETUP_SCRIPT = vm_module.SETUP_SCRIPT  # keep the stock setup


AS_KID_GSETTINGS = (
    "uid=$(id -u kid); runuser -u kid -- env "
    "XDG_RUNTIME_DIR=/run/user/$uid "
    "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus "
    "DCONF_PROFILE=kid HOME=/var/home/kid "
)

CUSTOM = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/kidnix0/"


def main() -> int:
    require_tools()
    vm = GuestVM(
        qcow2=REPO / "output" / "qcow2" / "disk.qcow2",
        output_dir=REPO / "output" / "e2e",
        ssh_port=2232,
        memory=4096,
        cpus=4,
        session_toml=SESSION_TOML,
    )
    vm.start()
    try:
        vm.wait_for_ssh()
        print("==> up")

        # ---- (b)/(c): is Tux Paint X11 or Wayland? -----------------------
        start_tuxpaint(vm)
        time.sleep(15)
        pid = vm.out("pgrep -u kid -x tuxpaint | head -1", check=False)
        print(f"\n--- Tux Paint (pid {pid}) ---")
        if pid:
            env = vm.out(
                f"tr '\\0' '\\n' </proc/{pid}/environ "
                "| grep -E '^(DISPLAY|WAYLAND_DISPLAY|SDL_VIDEODRIVER|XDG_SESSION_TYPE)=' || true",
                check=False,
            )
            print("env:\n  " + "\n  ".join(env.splitlines()))
            socks = vm.out(
                f"ls -l /proc/{pid}/fd 2>/dev/null | grep -o 'socket:\\[[0-9]*\\]' | wc -l",
                check=False,
            )
            print(f"open sockets: {socks}")
            x11 = vm.out(
                f"grep -c . /proc/{pid}/maps 2>/dev/null; "
                f"tr '\\0' '\\n' </proc/{pid}/maps 2>/dev/null | grep -c libX11 || true",
                check=False,
            )
            print(f"libX11 mapped (0 = wayland-native): {x11.splitlines()[-1] if x11 else '?'}")
        print("Xwayland running: " + (vm.out("pgrep -a Xwayland || echo NO", check=False)))

        # ---- (e): does a custom keybinding fire in a kiosk session? -------
        print("\n--- (e) gsd custom keybinding ---")
        print(
            "MediaKeys unit: "
            + vm.out(AS_KID + "is-active org.gnome.SettingsDaemon.MediaKeys.service", check=False)
        )
        vm.ssh(
            AS_KID_GSETTINGS + "gsettings set org.gnome.settings-daemon.plugins.media-keys "
            f"custom-keybindings \"['{CUSTOM}']\"",
            check=False,
        )
        for key, value in (
            ("name", "'kidnix escape'"),
            ("command", "'/usr/bin/touch /tmp/kidnix-escape-fired'"),
            ("binding", "'<Super><Shift>Escape'"),
        ):
            vm.ssh(
                AS_KID_GSETTINGS + "gsettings set "
                "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:"
                f"{CUSTOM} {key} {value}",
                check=False,
            )
        print(
            "configured: "
            + vm.out(
                AS_KID_GSETTINGS
                + "gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings",
                check=False,
            )
        )
        vm.ssh("rm -f /tmp/kidnix-escape-fired", check=False)
        time.sleep(3)
        vm.key("meta_l", "shift", "esc")
        time.sleep(4)
        fired = vm.out("test -e /tmp/kidnix-escape-fired && echo FIRED || echo no", check=False)
        print(f"custom keybinding <Super><Shift>Escape fired: {fired}")

        # Retry with a plainer chord, in case the modifier combination or the
        # Escape key was the problem rather than the mechanism.
        for binding, qcodes in (
            ("'<Control><Alt>k'", ("ctrl", "alt", "k")),
            ("'<Super>k'", ("meta_l", "k")),
        ):
            vm.ssh(
                AS_KID_GSETTINGS + "gsettings set org.gnome.settings-daemon.plugins.media-keys."
                f"custom-keybinding:{CUSTOM} binding {binding}",
                check=False,
            )
            vm.ssh("rm -f /tmp/kidnix-escape-fired", check=False)
            time.sleep(3)
            vm.key(*qcodes)
            time.sleep(4)
            fired = vm.out("test -e /tmp/kidnix-escape-fired && echo FIRED || echo no", check=False)
            print(f"custom keybinding {binding} fired: {fired}")

        print(
            "\ngsd-media-keys journal:\n  "
            + "\n  ".join(
                vm.out(
                    "journalctl -b --no-pager -o cat "
                    "_SYSTEMD_USER_UNIT=org.gnome.SettingsDaemon.MediaKeys.service | tail -15",
                    check=False,
                ).splitlines()
            )
        )

        # A plain WM keybinding for comparison: is anything grabbing at all?
        print(
            "wm keybindings in the kid db: "
            + vm.out(
                AS_KID_GSETTINGS + "gsettings list-recursively org.gnome.desktop.wm.keybindings "
                '| grep -vE "\\[\\]$" | head -12',
                check=False,
            )
        )
    finally:
        vm.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
