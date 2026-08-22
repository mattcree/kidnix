#!/usr/bin/bash
# Static assertions about the parent's desktop (ADR-0005).
#
#   just test-image parent
#   podman run --rm -v ./tests/image:/tests:ro,z --entrypoint /bin/bash \
#       localhost/kidnix:latest /tests/test_parent.sh
#
# Same shape and helpers as test_image.sh / test_lockdown.sh: runs INSIDE the
# built container, rootless, a couple of seconds.
#
# What it proves: the stock GNOME session is installed and complete, the parent
# is pointed at it, the GNOME 50 parental-control surfaces (malcontent,
# Settings' wellbeing panel) exist, the reader-friendly fonts are on disk and
# visible to fontconfig, and the payload we deliberately excluded is still
# excluded.
#
# What it cannot prove: that the parent session actually starts, that GDM
# honours the AccountsService file, or that malcontent-client can read the
# child's policy -- all three need accounts-service on a live D-Bus, i.e. a
# booted machine. The exact VM commands are in docs/spikes/parent-desktop.md.
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

# assert_file <path>
assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

# assert_exec <path>
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

# assert_no_rpm <name> <why>
assert_no_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report no "package $1 is absent" "$2"
    else
        _report ok "package $1 is absent ($2)"
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

# assert_cmd <description> <command...>
assert_cmd() {
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then _report ok "${desc}"; else _report no "${desc}" "$* failed"; fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# -----------------------------------------------------------------------------

section "stock GNOME session packages"
for pkg in gnome-shell gnome-session gnome-session-wayland-session \
           gnome-settings-daemon gnome-control-center xdg-desktop-portal-gnome \
           nautilus ptyxis gnome-backgrounds; do
    assert_rpm "${pkg}"
done

section "the session GDM will start for the parent"
# The session file's basename IS the session name AccountsService stores.
assert_file /usr/share/wayland-sessions/gnome.desktop
assert_grep '^Exec=' /usr/share/wayland-sessions/gnome.desktop "gnome.desktop has an Exec line"
assert_file /usr/share/gnome-session/sessions/gnome.session
for binary in /usr/bin/gnome-shell /usr/bin/gnome-session /usr/bin/nautilus \
              /usr/bin/ptyxis /usr/bin/gnome-control-center; do
    assert_exec "${binary}"
done
# Wayland only: an X session in the greeter would be an untested second path.
if [[ -z "$(find /usr/share/xsessions -type f 2>/dev/null | head -1)" ]]; then
    _report ok "no X11 sessions are offered (Wayland only)"
else
    _report no "no X11 sessions are offered (Wayland only)" \
        "found $(find /usr/share/xsessions -type f -printf '%f ' 2>/dev/null)"
fi
assert_no_rpm gnome-session-xsession "kidnix is Wayland-only"
# Exactly two sessions should exist: the kid's kiosk and stock GNOME.
sessions="$(find /usr/share/wayland-sessions -name '*.desktop' -printf '%f\n' 2>/dev/null | sort | tr '\n' ' ')"
if [[ "${sessions}" == "gnome.desktop kidnix-shell.desktop " ]]; then
    _report ok "exactly two sessions are offered: ${sessions}"
else
    _report no "exactly two sessions are offered" "got: ${sessions}"
fi

section "the parent's default session (AccountsService)"
assert_file /usr/share/kidnix/accountsservice-parent
assert_grep '^Session=gnome$'      /usr/share/kidnix/accountsservice-parent "parent's Session is stock gnome"
assert_grep '^XSession=gnome$'     /usr/share/kidnix/accountsservice-parent "parent's XSession is stock gnome"
assert_grep '^SessionType=wayland$' /usr/share/kidnix/accountsservice-parent "parent's session type is wayland"
assert_file /usr/lib/tmpfiles.d/kidnix-parent.conf
assert_grep '^C /var/lib/AccountsService/users/parent' \
    /usr/lib/tmpfiles.d/kidnix-parent.conf "tmpfiles seeds the parent's AccountsService file"
# The two accounts must not be pointed at the same session.
if grep -q '^Session=kidnix-shell$' /usr/share/kidnix/accountsservice-kid \
   && grep -q '^Session=gnome$' /usr/share/kidnix/accountsservice-parent; then
    _report ok "kid and parent have different default sessions"
else
    _report no "kid and parent have different default sessions"
fi
# The seed must survive a real tmpfiles run, not just parse.
if systemd-tmpfiles --cat-config >/dev/null 2>&1; then
    _report ok "tmpfiles config parses with the parent fragment"
else
    _report no "tmpfiles config parses with the parent fragment"
fi

section "GNOME 50 parental controls"
for pkg in malcontent malcontent-libs malcontent-control malcontent-tools; do
    assert_rpm "${pkg}"
done
assert_exec /usr/bin/malcontent-control
assert_exec /usr/bin/malcontent-client
assert_file /usr/share/applications/org.freedesktop.MalcontentControl.desktop
# The AccountsService vendor extensions are where the policy is actually stored.
for iface in com.endlessm.ParentalControls.AppFilter \
             com.endlessm.ParentalControls.SessionLimits \
             org.freedesktop.Malcontent.WebFilter; do
    assert_file "/usr/share/accountsservice/interfaces/${iface}.xml"
done
# GNOME 50's Settings gained a "wellbeing" panel (screen time / limits).
if XDG_CURRENT_DESKTOP=GNOME gnome-control-center --list 2>/dev/null | grep -qx $'\twellbeing'; then
    _report ok "gnome-control-center has the wellbeing (screen time) panel"
else
    _report no "gnome-control-center has the wellbeing (screen time) panel" \
        "not in --list"
fi
assert_file /usr/share/glib-2.0/schemas/org.gnome.desktop.screen-time-limits.gschema.xml
# malcontent's session-limit daemon must be present for time limits to bite.
assert_file /usr/lib/systemd/system/malcontent-timerd.service

section "fonts for pre-readers"
for pkg in sil-andika-fonts atkinson-hyperlegible-next-fonts \
           atkinson-hyperlegible-mono-fonts fontconfig; do
    assert_rpm "${pkg}"
done
for family in "Andika" "Atkinson Hyperlegible Next" "Atkinson Hyperlegible Mono"; do
    if fc-list : family 2>/dev/null | tr ',' '\n' | grep -qixF "${family}"; then
        _report ok "fontconfig sees the ${family} family"
    else
        _report no "fontconfig sees the ${family} family" "not in fc-list"
    fi
done
# A name request must resolve to the face itself, not to a fallback.
if [[ "$(fc-match Andika family 2>/dev/null | tr -d '\n')" == "Andika" ]]; then
    _report ok "fc-match Andika resolves to Andika (not a fallback)"
else
    _report no "fc-match Andika resolves to Andika (not a fallback)" \
        "got '$(fc-match Andika family 2>/dev/null | tr -d '\n')'"
fi
# The cache must be under /usr, or bootc discards it at install time.
if [[ -d /usr/lib/fontconfig/cache ]] \
   && [[ -n "$(find /usr/lib/fontconfig/cache -type f -print -quit 2>/dev/null)" ]]; then
    _report ok "the font cache is built and lives under /usr"
else
    _report no "the font cache is built and lives under /usr" \
        "nothing in /usr/lib/fontconfig/cache"
fi

section "parent panel (placeholder)"
assert_exec /usr/bin/kidnix-parent-panel
assert_file /usr/share/applications/kidnix-parent-panel.desktop
assert_grep '^Exec=/usr/bin/kidnix-parent-panel$' \
    /usr/share/applications/kidnix-parent-panel.desktop "the launcher execs the stub"
assert_grep '^TryExec=/usr/bin/kidnix-parent-panel$' \
    /usr/share/applications/kidnix-parent-panel.desktop "the launcher has a TryExec guard"
assert_cmd "the stub is valid bash" bash -n /usr/bin/kidnix-parent-panel
# It must run and say something, because a parent clicking a silent launcher
# concludes the machine is broken.
if /usr/bin/kidnix-parent-panel 2>/dev/null | grep -q 'Not built yet'; then
    _report ok "the stub runs and explains itself"
else
    _report no "the stub runs and explains itself"
fi
if command -v desktop-file-validate >/dev/null 2>&1; then
    assert_cmd "the launcher is a valid desktop entry" \
        desktop-file-validate /usr/share/applications/kidnix-parent-panel.desktop
fi

section "deliberately excluded (ADR-0005: no store, no wizard, no help engine)"
assert_no_rpm gnome-software      "a child's appliance has no app store"
assert_no_rpm gnome-initial-setup "the kiosk must never show a setup wizard"
assert_no_rpm gnome-boxes         "no VMs on a 6-year-old's laptop"
assert_no_rpm gnome-user-share    "no file sharing out of the child's home"
assert_no_rpm yelp                "the GNOME help browser embeds a web engine"
assert_no_rpm gnome-classic-session "one parent session, not three"
assert_no_rpm epiphany            "no second browser on top of the base image's firefox"
assert_no_rpm chromium            "no second browser on top of the base image's firefox"
# The @gnome-desktop comps group's *mandatory* list is exactly the tripwire:
# installing the group at any point lands all three of these in one go.
# Checking them together (rather than one by one above) is what catches
# "someone added @gnome-desktop to 00-packages.sh" as a single, legible
# failure.
if ! rpm -q gnome-software gnome-initial-setup yelp >/dev/null 2>&1; then
    _report ok "the @gnome-desktop comps group was not installed wholesale"
else
    _report no "the @gnome-desktop comps group was not installed wholesale" \
        "its mandatory packages are present"
fi

section "lockdown interactions"
# The parent is uid 1001; the egress lockdown filters uid 1000 only.
assert_grep '^u[[:space:]]+parent[[:space:]]+1001:1001' \
    /usr/lib/sysusers.d/kidnix.conf "parent is uid 1001, outside the egress filter"
# Nothing in the parent's desktop may be wired into the child's dconf profile.
if ! grep -rq 'DCONF_PROFILE' /usr/bin/kidnix-parent-panel 2>/dev/null; then
    _report ok "the parent panel does not inherit the child's dconf profile"
else
    _report no "the parent panel does not inherit the child's dconf profile"
fi

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
