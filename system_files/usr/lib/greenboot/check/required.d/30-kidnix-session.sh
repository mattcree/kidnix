#!/usr/bin/bash
# greenboot REQUIRED check: the pieces the kiosk session is made of are present
# and enabled.
#
# Deliberately STRUCTURAL, not behavioural. "Is gdm enabled, does the session
# binary exist, is the lockdown policy installed" are facts that are true or
# false the instant the deployment lands; they cannot be flaky. Whether the
# session actually *came up* is checked in wanted.d, where a slow machine
# cannot trigger a rollback loop.
set -uo pipefail

fail=0

require_exec() {
    if [[ ! -x "$1" ]]; then
        echo "kidnix: $1 is missing or not executable" >&2
        fail=1
    fi
}

require_file() {
    if [[ ! -f "$1" ]]; then
        echo "kidnix: $1 is missing" >&2
        fail=1
    fi
}

require_exec /usr/bin/kidnix-shell
require_exec /usr/bin/gnome-kiosk
require_exec /usr/libexec/kidnix-app-supervisor
require_file /usr/share/wayland-sessions/kidnix-shell.desktop

# The lockdown policy itself.
require_file /usr/share/polkit-1/rules.d/40-kidnix-kid.rules
require_file /usr/share/kidnix/dconf/kid.compiled
require_file /etc/dconf/profile/kid
require_file /usr/lib/systemd/logind.conf.d/10-kidnix-kiosk.conf

if ! systemctl is-enabled gdm.service >/dev/null 2>&1; then
    echo "kidnix: gdm.service is not enabled" >&2
    fail=1
fi

if ! systemctl is-enabled kidnix-egress.service >/dev/null 2>&1; then
    echo "kidnix: kidnix-egress.service is not enabled" >&2
    fail=1
fi

# An unattended reboot in the middle of an activity is exactly the surprise
# kidnix promises not to spring on a child.
if [[ "$(systemctl is-enabled bootc-fetch-apply-updates.timer 2>/dev/null)" != "masked" ]]; then
    echo "kidnix: bootc-fetch-apply-updates.timer is not masked" >&2
    fail=1
fi

exit "${fail}"
