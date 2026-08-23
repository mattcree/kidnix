#!/usr/bin/bash
# This machine is British. Assert it, in every place it has to be true.
#
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_locale.sh
#
# docs/design/reviews/2026-08-23-early-years-teacher.md opens with this as a
# BLOCKER, and the evidence was our own screenshot: Tux Paint's status bar
# reading "Pick a COLOR and a brush shape to draw with." Her closing sentence
# is what this file exists to enforce -- "add an image test asserting no
# child-facing binary starts in C/en_US."
#
# WHAT THIS CAN AND CANNOT PROVE. There is no session in a container, so it
# cannot watch a program start and read its LANG. What it can prove is every
# link in the chain that produces that LANG: the locale data exists, the file
# systemd reads names it, nothing else in the image contradicts it, and each
# child-facing program that keeps its own language setting is set to the
# British one. The last link -- a running session -- is tests/boot/ and the
# e2e screenshots.
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

assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

assert_no_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report no "$3" "unexpected match for /$1/ in $2"
    else
        _report ok "$3"
    fi
}

# assert_eq <description> <want> <got>
assert_eq() {
    if [[ "$2" == "$3" ]]; then
        _report ok "$1 ($3)"
    else
        _report no "$1" "want '$2', got '$3'"
    fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local description="$1"; shift
    local output
    if output="$("$@" 2>&1)"; then
        _report ok "${description}${output:+ (${output})}"
    else
        _report no "${description}" "${output}"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

readonly WANT=en_GB.UTF-8

# -----------------------------------------------------------------------------

section "the locale data is on the machine"
if locale -a 2>/dev/null | grep -qx 'en_GB.utf8'; then
    _report ok "en_GB.utf8 is in the locale archive"
else
    _report no "en_GB.utf8 is in the locale archive" "locale -a does not list it"
fi
assert_cmd "LC_ALL=${WANT} is a usable locale" env LC_ALL="${WANT}" locale

section "what systemd reads at boot"
# systemd PID 1 parses /etc/locale.conf and puts LANG into the default
# environment of every unit, which is how it reaches gdm, the child's
# `systemd --user`, gnome-session and every activity. No profile.d step.
assert_file /etc/locale.conf
assert_grep "^LANG=${WANT}$" /etc/locale.conf "locale.conf sets LANG=${WANT}"
assert_no_grep '^LC_ALL=' /etc/locale.conf \
    "locale.conf does NOT set LC_ALL (it would override every category permanently)"
assert_eq "exactly one LANG= line in locale.conf" "1" "$(grep -c '^LANG=' /etc/locale.conf)"

section "nothing else in the image contradicts it"
# The failure this catches is a second, later definition winning: an
# /etc/environment, a profile.d fragment or a unit Environment= line that
# re-exports LANG as C or en_US would beat locale.conf for everything it
# reaches, and would be invisible in a diff.
conflicts=""
for candidate in /etc/environment /etc/profile.d/*.sh /etc/locale.conf.d/*; do
    [[ -f "${candidate}" ]] || continue
    # Fedora's own /etc/profile.d/lang.sh is excluded and checked separately
    # below: it does mention C.UTF-8 and en_US, but only as a fallback when the
    # named locale is unavailable and only for CJK on a text console. Its main
    # job is to read /etc/locale.conf, which is what we want.
    [[ "${candidate}" == /etc/profile.d/lang.sh ]] && continue
    if grep -Eq '^[^#]*\b(LANG|LC_ALL)=(C|POSIX|en_US)' "${candidate}" 2>/dev/null; then
        conflicts="${conflicts} ${candidate}"
    fi
done
unit_conflicts="$(grep -rlE '^Environment=.*\b(LANG|LC_ALL)=(C|POSIX|en_US)' \
    /usr/lib/systemd/system /usr/lib/systemd/user 2>/dev/null || true)"
if [[ -z "${conflicts}${unit_conflicts}" ]]; then
    _report ok "no file in the image re-exports LANG as C/POSIX/en_US"
else
    _report no "no file in the image re-exports LANG as C/POSIX/en_US" \
        "${conflicts} ${unit_conflicts}"
fi
# Fedora's lang.sh, checked for what it actually does rather than skipped.
# It only resets to C.UTF-8 when `locale` emits a warning -- i.e. when the
# configured locale is NOT INSTALLED -- which is the failure the first section
# of this file rules out. Note that the child's session never reaches it at
# all: GDM starts a systemd user manager, not a login shell.
if [[ -f /etc/profile.d/lang.sh ]]; then
    assert_grep '/etc/locale.conf' /etc/profile.d/lang.sh \
        "Fedora's lang.sh reads /etc/locale.conf rather than inventing a locale"
    assert_cmd "a login shell ends up in ${WANT}" \
        bash -lc "[[ \"\${LANG}\" == '${WANT}' ]]"
fi

# And the session wrapper the child's login actually execs must not clear the
# environment it was handed.
assert_no_grep '\benv -i\b' /usr/bin/kidnix-shell \
    "the kid session wrapper does not start from an empty environment"

section "the locale behaves like en_GB, not just like 'some locale'"
# Three different locale categories, so all three passing means the whole
# locale loaded rather than one table. These are the differences a UK parent
# would notice on a school form.
uk_date="$(LC_ALL="${WANT}" date -u -d '2026-02-03' +%x 2>/dev/null)"
us_date="$(LC_ALL=en_US.UTF-8 date -u -d '2026-02-03' +%x 2>/dev/null)"
if [[ "${uk_date}" == 03/02* && "${uk_date}" != "${us_date}" ]]; then
    _report ok "dates are day-first (${uk_date}, vs en_US ${us_date})"
else
    _report no "dates are day-first" "en_GB '${uk_date}' vs en_US '${us_date}'"
fi
assert_eq "paper size is A4 (297 mm tall)" "297" \
    "$(LC_ALL="${WANT}" locale -k LC_PAPER 2>/dev/null | sed -n 's/^height=//p')"
assert_eq "measurement system is metric" "1" \
    "$(LC_ALL="${WANT}" locale -k LC_MEASUREMENT 2>/dev/null | sed -n 's/^measurement=//p')"

section "keyboard: the characters printed on the keys"
# gb and us differ on @ and \" and there is no £ on us at all. A five-year-old
# copying a letter out of a book has no way to discover a layout is wrong.
assert_file /etc/vconsole.conf
assert_grep '^KEYMAP=uk$' /etc/vconsole.conf "console keymap is uk"
assert_file /etc/X11/xorg.conf.d/00-keyboard.conf
assert_grep '^[[:space:]]*Option[[:space:]]+"XkbLayout"[[:space:]]+"gb"$' \
    /etc/X11/xorg.conf.d/00-keyboard.conf \
    "the system X11/Wayland layout is gb (what systemd-localed owns and mutter asks for)"
if [[ -f /usr/share/X11/xkb/rules/evdev.lst ]]; then
    assert_grep '^[[:space:]]+gb[[:space:]]' /usr/share/X11/xkb/rules/evdev.lst \
        "xkeyboard-config actually has a 'gb' layout"
fi

section "keyboard: the child's own session"
# GNOME's per-session input sources override the system layout the moment a
# session starts, so setting only the system half would leave the child on the
# compiled-in `us`.
export HOME="${HOME:-/root}"
mkdir -p "${HOME}" 2>/dev/null || true
kid_sources="$(DCONF_PROFILE=kid gsettings get org.gnome.desktop.input-sources sources 2>/dev/null || echo '<error>')"
assert_eq "the kid profile's keyboard layout" "[('xkb', 'gb')]" "${kid_sources}"
kid_locked="$(DCONF_PROFILE=kid gsettings writable org.gnome.desktop.input-sources sources 2>/dev/null || echo '<error>')"
assert_eq "the layout is locked against the child changing it" "false" "${kid_locked}"
# One source and no xkb options means no layout switcher and no dead keys:
# GNOME only shows the input-source indicator (and binds Super+Space) when
# there is more than one source.
assert_eq "no xkb options (no dead keys, no swapped modifiers)" "@as []" \
    "$(DCONF_PROFILE=kid gsettings get org.gnome.desktop.input-sources xkb-options 2>/dev/null || echo '<error>')"
# ...and the default profile must be untouched, or this leaked out of the kid
# session into the parent's desktop.
default_sources="$(gsettings get org.gnome.desktop.input-sources sources 2>/dev/null || echo '<error>')"
if [[ "${default_sources}" != "[('xkb', 'gb')]" ]]; then
    _report ok "the kid layout does not leak into the default dconf profile"
else
    _report no "the kid layout does not leak into the default dconf profile" \
        "the default profile also reads ${default_sources}"
fi

section "the programs that keep their own language setting"
# Three child-facing programs do NOT take their UI language from LANG; each has
# a setting of its own, and each is a separate way to end up in American
# English on a British child's machine.

# Tux Paint: its own language table, keyed by NAME not by POSIX locale.
assert_file /etc/tuxpaint/tuxpaint.conf
assert_grep '^lang=british-english$' /etc/tuxpaint/tuxpaint.conf \
    "Tux Paint is set to British English (the 'COLOR' screenshot in the review)"
if command -v tuxpaint >/dev/null 2>&1; then
    assert_cmd "tuxpaint --lang help actually offers 'british-english'" \
        bash -c "tuxpaint --lang help 2>&1 | grep -qw 'british-english'"
fi

# GCompris: locale under the [%General] group QSettings really reads.
assert_grep '^locale=en_GB\.UTF-8$' /usr/share/kidnix/gcompris/gcompris-qt.conf \
    "GCompris is set to en_GB.UTF-8"

# KLettres: /usr/share/config.kcfg/klettres.kcfg defaults Language to "en",
# which is the AMERICAN recording set, while /usr/share/klettres/en_GB/ exists
# in the same RPM and nothing selects it unless we do.
assert_file /etc/xdg/klettresrc
# shellcheck disable=SC2016  # [$i] is KConfig's immutability marker, not a shell variable
assert_grep '^Language\[\$i\]=en_GB$' /etc/xdg/klettresrc \
    "KLettres is pinned to the en_GB recordings (and pinned immutably)"
assert_cmd "the en_GB KLettres recordings are actually installed" \
    test -f /usr/share/klettres/en_GB/sounds.xml
assert_cmd "en_GB KLettres has 26 alphabet clips" \
    bash -c "[[ \$(find /usr/share/klettres/en_GB/alpha -name '*.ogg' | wc -l) -eq 26 ]]"

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
