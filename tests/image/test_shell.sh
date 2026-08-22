#!/usr/bin/bash
# Static assertions about the real activity shell and the gnome-session-based
# kid session that runs it. Runs INSIDE the built container:
#
#   just test-image shell
#
# The companion boot assertions (graphical-session.target actually active,
# portals actually running, the shell actually restarting) are in
# tests/boot/bcvk_boot_test.py -- nothing here can see a running session.
#
# Background: docs/spikes/session-integration.md.
set -uo pipefail

pass=0
fail=0

_report() {
    local status="$1" name="$2" detail="${3:-}"
    if [[ "${status}" == ok ]]; then
        printf '  \033[32mPASS\033[0m  %s\n' "${name}"
        pass=$(( pass + 1 ))
    else
        printf '  \033[31mFAIL\033[0m  %s%s\n' "${name}" "${detail:+ -- ${detail}}"
        fail=$(( fail + 1 ))
    fi
}

assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

assert_exec() {
    if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi
}

assert_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report ok "package $1 ($(rpm -q --qf '%{VERSION}-%{RELEASE}' "$1"))"
    else
        _report no "package $1" "not installed"
    fi
}

assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

assert_absent() {
    if [[ ! -e "$1" ]]; then _report ok "absent $1"; else _report no "absent $1" "should not exist"; fi
}

# assert_run <description> <command...> -- the command must exit 0
assert_run() {
    local name="$1"; shift
    local out
    if out="$("$@" 2>&1)"; then
        _report ok "${name}"
    else
        _report no "${name}" "${out##*$'\n'}"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# The image installs into the /usr scheme, not sysconfig's /usr/local default
# (which on an ostree system is a symlink into /var and is not part of the
# image at all).
PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))' 2>/dev/null)"

# -----------------------------------------------------------------------------

section "the shell package"

# cd / so a stray CWD cannot make the import pass against a source tree.
assert_run "kidnix_shell imports" \
    python3 -c 'import kidnix_shell'
if [[ "$(cd / && python3 -c 'import kidnix_shell; print(kidnix_shell.__file__)' 2>/dev/null)" == /usr/lib/* ]]; then
    _report ok "kidnix_shell imports from /usr/lib (not /usr/local, which is /var on ostree)"
else
    _report no "kidnix_shell imports from /usr/lib" \
        "got $(cd / && python3 -c 'import kidnix_shell; print(kidnix_shell.__file__)' 2>&1)"
fi

assert_exec /usr/bin/kidnix-shell-app
assert_run "kidnix-shell-app --version" /usr/bin/kidnix-shell-app --version
assert_run "python3 -m kidnix_shell --version" python3 -m kidnix_shell --version

assert_file "${PURELIB}/kidnix_shell/cli.py"
assert_file "${PURELIB}/kidnix_shell/app.py"
# Loaded by path at runtime, so they have to have travelled with the package.
assert_file "${PURELIB}/kidnix_shell/theme.css"
assert_file "${PURELIB}/kidnix_shell/data/icons/kidnix-make.svg"

# /usr is read-only at runtime: without shipped .pyc the shell re-parses itself
# on every start and can never cache the result.
if compgen -G "${PURELIB}/kidnix_shell/__pycache__/cli.*.pyc" >/dev/null; then
    _report ok "the package is byte-compiled (/usr is read-only at runtime)"
else
    _report no "the package is byte-compiled" "no __pycache__/cli.*.pyc"
fi

# What a wheel install would have left behind, so importlib.metadata works.
if compgen -G "${PURELIB}/kidnix_shell-*.dist-info/METADATA" >/dev/null; then
    _report ok "dist-info metadata present"
else
    _report no "dist-info metadata present" "no kidnix_shell-*.dist-info/METADATA"
fi
assert_run "importlib.metadata knows kidnix-shell" \
    python3 -c 'from importlib.metadata import version; assert version("kidnix-shell")'

section "runtime dependencies (all from RPMs -- shell/pyproject.toml has none)"
for pkg in python3-gobject gtk4 libadwaita python3-speechd speech-dispatcher \
           gnome-session gnome-settings-daemon \
           xdg-desktop-portal xdg-desktop-portal-gnome xdg-desktop-portal-gtk; do
    assert_rpm "${pkg}"
done
assert_run "GTK4 + libadwaita import through PyGObject" python3 -c '
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
'
assert_run "the GTK half of the shell imports" python3 -c 'import kidnix_shell.app'
assert_run "speechd (read-aloud backend) imports" python3 -c 'import speechd'
assert_exec /usr/bin/spd-say

section "the gnome-session session"
# gnome-session --session=kidnix resolves this file; without it
# gnome-session-manager@kidnix.service refuses to start and GDM bounces the
# child back to a greeter.
assert_file /usr/share/gnome-session/sessions/kidnix.session
assert_grep '^Name=kidnix$' /usr/share/gnome-session/sessions/kidnix.session \
    "kidnix.session names the session"

# Where a systemd-managed gnome-session gets its component list.
DROPIN=/usr/lib/systemd/user/gnome-session@kidnix.target.d/session.conf
assert_file "${DROPIN}"
assert_grep '^Requires=org.gnome.Kiosk.target$' "${DROPIN}" \
    "the session requires the kiosk compositor"
assert_grep '^Wants=kidnix-shell.service$' "${DROPIN}" \
    "the session pulls in kidnix-shell.service (Wants=, so a shell crash cannot end the session)"

# The units gnome-kiosk and gnome-session contribute. Both of gnome-kiosk's are
# Requisite=gnome-session-initialized.target, which is exactly why the session
# has to go through gnome-session at all.
for unit in /usr/lib/systemd/user/org.gnome.Kiosk.target \
            /usr/lib/systemd/user/org.gnome.Kiosk@wayland.service \
            /usr/lib/systemd/user/gnome-session@.target \
            /usr/lib/systemd/user/gnome-session-initialized.target \
            /usr/lib/systemd/user/gnome-session.target; do
    assert_file "${unit}"
done
assert_grep '^Requisite=gnome-session-initialized.target$' \
    /usr/lib/systemd/user/org.gnome.Kiosk.target \
    "gnome-kiosk's target still needs gnome-session (the reason for all of this)"
assert_grep '^BindsTo=graphical-session.target$' \
    /usr/lib/systemd/user/gnome-session.target \
    "gnome-session.target is what raises graphical-session.target"
assert_grep '^Requisite=graphical-session.target$' \
    /usr/lib/systemd/user/xdg-desktop-portal.service \
    "xdg-desktop-portal still demands an ACTIVE graphical-session.target"

section "kidnix-shell.service"
UNIT=/usr/lib/systemd/user/kidnix-shell.service
assert_file "${UNIT}"
assert_grep '^ExecStart=/usr/bin/kidnix-shell-app$' "${UNIT}" "the unit starts the real shell"
assert_grep '^Restart=always$'   "${UNIT}" "the shell restarts if it dies"
assert_grep '^RestartSec=1$'     "${UNIT}" "it restarts within a second"
assert_grep '^StartLimitIntervalSec=0$' "${UNIT}" \
    "systemd never gives up on it (a child cannot recover from a black screen)"
assert_grep '^After=gnome-session.target$' "${UNIT}" \
    "it starts after the compositor has exported WAYLAND_DISPLAY"
assert_grep '^BindsTo=gnome-session.target$' "${UNIT}" "it dies with the session"
# speech-dispatcher must be socket-activated into its own cgroup, or an
# autospawned copy joins the shell's, ignores SIGTERM and stalls every restart
# for the full TimeoutStopSec (11.4s measured, vs 1.3s with the socket).
assert_grep '^Wants=speech-dispatcher.socket$' "${UNIT}" \
    "read-aloud is socket-activated, not autospawned into the shell's cgroup"
assert_file /usr/lib/systemd/user/speech-dispatcher.socket
assert_grep 'ListenStream=%t/speech-dispatcher/speechd.sock' \
    /usr/lib/systemd/user/speech-dispatcher.socket \
    "the socket listens where python3-speechd looks"
if command -v systemd-analyze >/dev/null 2>&1; then
    # XDG_RUNTIME_DIR or `--user verify` refuses to start a manager and checks
    # nothing while still exiting 0.
    mkdir -p /tmp/kidnix-verify-runtime
    out="$(XDG_RUNTIME_DIR=/tmp/kidnix-verify-runtime \
        systemd-analyze --user verify --recursive-errors=no "${UNIT}" 2>&1)"
    if grep -q 'kidnix-shell.service' <<<"${out}"; then
        _report no "systemd-analyze accepts kidnix-shell.service" "${out##*$'\n'}"
    else
        _report ok "systemd-analyze accepts kidnix-shell.service"
    fi
fi

section "the GDM entry point"
assert_exec /usr/bin/kidnix-shell
assert_grep '^Exec=/usr/bin/kidnix-shell$' \
    /usr/share/wayland-sessions/kidnix-shell.desktop "GDM execs the wrapper"
assert_grep '^DesktopNames=GNOME-Kiosk;GNOME;$' \
    /usr/share/wayland-sessions/kidnix-shell.desktop "DesktopNames matches gnome-kiosk's own session"
assert_grep '^exec /usr/bin/gnome-session --session=kidnix$' \
    /usr/bin/kidnix-shell "the wrapper hands over to gnome-session --session=kidnix"
assert_grep '^export DCONF_PROFILE=kid$' \
    /usr/bin/kidnix-shell "the wrapper selects the child dconf profile"
assert_grep 'dbus-update-activation-environment --systemd DCONF_PROFILE' \
    /usr/bin/kidnix-shell "DCONF_PROFILE is pushed into systemd --user and D-Bus"

# The v0.1 placeholder is gone from the session path in every direction.
if grep -hv '^[[:space:]]*#' /usr/bin/kidnix-shell "${DROPIN}" "${UNIT}" \
        /usr/share/gnome-session/sessions/kidnix.session \
        /usr/share/wayland-sessions/kidnix-shell.desktop 2>/dev/null \
        | grep -q 'gnome-text-editor'; then
    _report no "no gnome-text-editor placeholder in the session path" "still referenced"
else
    _report ok "no gnome-text-editor placeholder in the session path"
fi
if rpm -q gnome-text-editor >/dev/null 2>&1; then
    _report no "the gnome-text-editor placeholder package is gone" "still installed"
else
    _report ok "the gnome-text-editor placeholder package is gone"
fi
# The bash supervisor is superseded by Restart=always. The file stays for now
# (greenboot's required.d check still names it) but nothing in the session may
# reference it -- see docs/spikes/session-integration.md, "left for removal".
if grep -hv '^[[:space:]]*#' /usr/bin/kidnix-shell "${UNIT}" "${DROPIN}" 2>/dev/null \
        | grep -q 'kidnix-app-supervisor'; then
    _report no "the bash app supervisor is out of the session path" "still referenced"
else
    _report ok "the bash app supervisor is out of the session path"
fi

section "shell configuration and content"
assert_file /etc/kidnix/session.toml
assert_run "session.toml parses and has every key the shell reads" python3 -c '
import tomllib
with open("/etc/kidnix/session.toml", "rb") as fh:
    data = tomllib.load(fh)
required = {"length_minutes", "daily_budget_minutes", "ending_offer_minutes",
            "put_away_minutes", "bedtime_start", "bedtime_end"}
missing = required - set(data)
assert not missing, missing
assert data["length_minutes"] == 25, data["length_minutes"]
'
assert_run "the shell loads /etc/kidnix/session.toml as its policy" python3 -c '
from pathlib import Path
from kidnix_shell.session import load_policy
from kidnix_shell.settings import Paths
policy = load_policy(Path("/etc/kidnix/session.toml"))
assert policy.length == 25 * 60, policy
assert Paths.from_env().session_config == Path("/etc/kidnix/session.toml")
'
assert_run "manifests live where the shell looks for them" python3 -c '
from kidnix_shell.activities import SYSTEM_ACTIVITY_DIR
assert str(SYSTEM_ACTIVITY_DIR) == "/usr/share/kidnix/activities", SYSTEM_ACTIVITY_DIR
assert SYSTEM_ACTIVITY_DIR.is_dir()
'
assert_run "every shipped activity manifest validates" \
    /usr/bin/kidnix-shell-app --validate-manifests /usr/share/kidnix/activities

section "build hygiene"
# The source tree the Containerfile copied in must not survive.
assert_absent /tmp/shell
# ... and no developer venv or cache can have travelled with it.
if compgen -G "${PURELIB}/kidnix_shell/**/.venv" >/dev/null 2>&1; then
    _report no "no developer venv in the installed package"
else
    _report ok "no developer venv in the installed package"
fi

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
