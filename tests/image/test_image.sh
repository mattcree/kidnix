#!/usr/bin/bash
# Static assertions about the built image. Runs INSIDE the container via
# `podman run` (rootless, no VM, ~2 seconds) -- this is the fast feedback loop
# that catches 90% of packaging mistakes before anyone builds a disk image.
#
#   just test-image
#
# It cannot verify anything that only happens at boot (users actually being
# created, the session actually starting). That is tests/boot/boot_test.py.
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

# assert_file <path> -- exists and is a regular file
assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

# assert_exec <path> -- exists and is executable
assert_exec() {
    if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi
}

# assert_rpm <name>
assert_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report ok "package $1 ($(rpm -q --qf '%{VERSION}-%{RELEASE}' "$1"))"
    else
        _report no "package $1" "not installed"
    fi
}

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_absent <path>
assert_absent() {
    if [[ ! -e "$1" ]]; then _report ok "absent $1"; else _report no "absent $1" "should not exist"; fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# -----------------------------------------------------------------------------

section "packages"
for pkg in gdm gnome-kiosk gnome-kiosk-a11y malcontent malcontent-control \
           speech-dispatcher gnome-text-editor flatpak systemd bootc; do
    assert_rpm "${pkg}"
done

section "branding"
assert_file /usr/lib/os-release
assert_grep '^ID=kidnix$'        /usr/lib/os-release "os-release ID=kidnix"
assert_grep '^ID_LIKE="fedora"$' /usr/lib/os-release "os-release ID_LIKE=fedora (keeps dnf/flatpak tooling working)"
assert_grep '^NAME="kidnix"$'    /usr/lib/os-release "os-release NAME"
assert_grep '^PRETTY_NAME="kidnix' /usr/lib/os-release "os-release PRETTY_NAME"
assert_grep '^VARIANT_ID=kidnix$' /usr/lib/os-release "os-release VARIANT_ID"
assert_grep '^VERSION_ID=44$'    /usr/lib/os-release "still Fedora 44 underneath"
assert_file /usr/share/kidnix/VERSION
assert_file /usr/share/kidnix/image-info.json
if command -v python3 >/dev/null 2>&1 \
   && python3 -c 'import json,sys; json.load(open("/usr/share/kidnix/image-info.json"))' 2>/dev/null; then
    _report ok "image-info.json is valid JSON"
else
    _report no "image-info.json is valid JSON"
fi

section "kiosk session"
assert_exec /usr/bin/kidnix-shell
assert_exec /usr/bin/gnome-kiosk
assert_file /usr/share/wayland-sessions/kidnix-shell.desktop
assert_grep '^Exec=/usr/bin/kidnix-shell$' \
    /usr/share/wayland-sessions/kidnix-shell.desktop "session Exec points at kidnix-shell"
assert_grep '^X-GDM-CanRunHeadless=true$' \
    /usr/share/wayland-sessions/kidnix-shell.desktop "session can run headless (needed by test-boot)"
# The placeholder payload must exist or the session dies instantly at boot.
assert_exec /usr/bin/gnome-text-editor

section "accounts (declarative -- created at first boot)"
assert_file /usr/lib/sysusers.d/kidnix.conf
assert_file /usr/lib/tmpfiles.d/kidnix.conf
assert_grep '^u[[:space:]]+kid[[:space:]]'    /usr/lib/sysusers.d/kidnix.conf "sysusers declares kid"
assert_grep '^u[[:space:]]+parent[[:space:]]' /usr/lib/sysusers.d/kidnix.conf "sysusers declares parent"
assert_grep '^m[[:space:]]+parent[[:space:]]+wheel' /usr/lib/sysusers.d/kidnix.conf "parent is in wheel"
assert_grep '/var/home/kid' /usr/lib/tmpfiles.d/kidnix.conf "tmpfiles creates kid's home under /var/home"
# kid must NOT be an admin.
if grep -Eq '^m[[:space:]]+kid[[:space:]]+(wheel|sudo|root)' /usr/lib/sysusers.d/kidnix.conf; then
    _report no "kid is not in an admin group" "kid has privileged group membership"
else
    _report ok "kid is not in an admin group"
fi
if systemd-sysusers --cat-config >/dev/null 2>&1; then
    _report ok "sysusers config parses"
else
    _report no "sysusers config parses"
fi
if systemd-tmpfiles --cat-config >/dev/null 2>&1; then
    _report ok "tmpfiles config parses"
else
    _report no "tmpfiles config parses"
fi

section "autologin"
assert_file /etc/gdm/custom.conf
assert_grep '^AutomaticLoginEnable=True$' /etc/gdm/custom.conf "GDM autologin enabled"
assert_grep '^AutomaticLogin=kid$'        /etc/gdm/custom.conf "GDM autologs in as kid"
assert_file /usr/share/kidnix/accountsservice-kid
assert_grep '^XSession=kidnix-shell$' \
    /usr/share/kidnix/accountsservice-kid "kid's default session is the kiosk"

section "systemd wiring"
assert_file /usr/lib/systemd/system/kidnix-boot-report.service
assert_exec /usr/libexec/kidnix-boot-report
if [[ "$(readlink -f /etc/systemd/system/default.target)" == */graphical.target ]]; then
    _report ok "default target is graphical.target"
else
    _report no "default target is graphical.target" \
        "got $(readlink -f /etc/systemd/system/default.target 2>/dev/null || echo unset)"
fi
for unit in gdm.service kidnix-boot-report.service; do
    if [[ -L "/etc/systemd/system/graphical.target.wants/${unit}" \
       || -L "/etc/systemd/system/multi-user.target.wants/${unit}" \
       || -L "/etc/systemd/system/display-manager.service" ]]; then
        _report ok "unit enabled: ${unit}"
    else
        _report no "unit enabled: ${unit}" "no enablement symlink found"
    fi
done

section "bootc hygiene"
# build_files must not survive into the shipped image.
assert_absent /tmp/build_files
# /var must be empty-ish: it is machine-local and discarded at install time.
if [[ -z "$(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -print -quit 2>/dev/null)" ]]; then
    _report ok "/var carries no image content"
else
    _report no "/var carries no image content" \
        "found: $(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -printf '%f ' 2>/dev/null)"
fi
assert_file /usr/lib/sysimage/rpm/rpmdb.sqlite

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
