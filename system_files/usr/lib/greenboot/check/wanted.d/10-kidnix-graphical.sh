#!/usr/bin/bash
# greenboot WANTED check: the graphical session actually reached the child.
#
# WANTED, not REQUIRED, and that is a considered decision. This is the thing we
# most want to know, but it is also the thing most likely to be slow rather
# than broken -- a cold first boot on a cheap laptop, a display that takes its
# time, an activity's first-run setup. A required check that fails on a slow
# boot rolls the machine back to an older image and does it again, which is a
# far worse failure than one red line in the journal.
#
# The boot test (tests/boot/boot_test.py) and kidnix-boot-report.service are
# where "did the kiosk really come up" is asserted properly, with a timeout
# that suits a test rather than a bootloader.
set -uo pipefail

fail=0

if ! systemctl is-active gdm.service >/dev/null 2>&1; then
    echo "kidnix: gdm.service is not active" >&2
    fail=1
fi

if [[ "$(systemctl get-default 2>/dev/null)" != "graphical.target" ]]; then
    echo "kidnix: default target is not graphical.target" >&2
    fail=1
fi

# A wayland session for the child. Absent this early in boot is common and
# harmless; that is the whole reason this file is in wanted.d.
# Captured, not piped into `grep -q` -- see the note in 20-kidnix-egress.sh.
sessions="$(loginctl list-sessions --no-legend 2>/dev/null || true)"
session_users="$(awk '{print $3}' <<<"${sessions}")"
if ! grep -qx kid <<<"${session_users}"; then
    echo "kidnix: no login session for user 'kid' yet" >&2
    fail=1
fi

# The Flatpak global override should have been seeded by tmpfiles.
if [[ -e /var/lib/flatpak/overrides/global ]]; then
    if ! grep -q 'shared=!network' /var/lib/flatpak/overrides/global 2>/dev/null; then
        echo "kidnix: flatpak global override exists but does not unshare network" >&2
        fail=1
    fi
else
    echo "kidnix: /var/lib/flatpak/overrides/global has not been seeded" >&2
    fail=1
fi

exit "${fail}"
