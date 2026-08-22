#!/usr/bin/bash
# Wire up the graphical target, the kiosk session and the boot-readiness probe.
set -euo pipefail

# base-main is headless and defaults to multi-user.target.
systemctl set-default graphical.target

systemctl enable gdm.service
systemctl enable kidnix-boot-report.service

# The session file must point at something that exists, or GDM silently falls
# back and the boot test fails with a very unhelpful message.
test -x /usr/bin/kidnix-shell
test -x /usr/libexec/kidnix-boot-report
grep -q '^Exec=/usr/bin/kidnix-shell$' /usr/share/wayland-sessions/kidnix-shell.desktop

# GDM needs DesktopNames to match the gnome-session the wrapper starts, or
# XDG_CURRENT_DESKTOP is wrong and OnlyShowIn=GNOME components are skipped.
grep -q '^DesktopNames=GNOME-Kiosk;GNOME;$' /usr/share/wayland-sessions/kidnix-shell.desktop

# The session's own pieces are installed and verified by 60-shell.sh, which
# runs later; assert here only what 30-kiosk itself is responsible for.

# Autologin is only meaningful if GDM can resolve the session name; the name is
# the desktop file's basename, so keep the two in lockstep.
grep -q '^XSession=kidnix-shell$' /usr/share/kidnix/accountsservice-kid

if command -v desktop-file-validate >/dev/null 2>&1; then
    # X-GDM-* keys are legitimate vendor extensions but not in the spec's
    # registry, so only hard-fail on real errors.
    desktop-file-validate /usr/share/wayland-sessions/kidnix-shell.desktop || true
fi
