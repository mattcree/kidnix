#!/usr/bin/bash
# British English, everywhere, for everyone.
#
# WHY THIS STAGE EXISTS. docs/design/reviews/2026-08-23-early-years-teacher.md
# opens with a BLOCKER, and the evidence is our own screenshot: Tux Paint's
# status bar in docs/design/screenshots/e2e-contact-sheet.png panel 5 reads
# "Pick a COLOR and a brush shape to draw with." Her sentence is the whole
# argument: "A machine whose stated job is helping a UK five-year-old with
# letters and spelling cannot show him American spellings."
#
# Before this stage the image had no /etc/locale.conf, no LANG= anywhere, and
# no keyboard layout: every program fell back to the C locale (which glibc's
# gettext resolves to the untranslated American source strings) and to xkb's
# compiled-in `us` layout, on which the @ and " keys are swapped from a UK
# keycap and there is no £ at all.
#
# FOUR THINGS HAVE TO AGREE, and they are set in four different places
# because four different subsystems own them:
#
#   1. the C library's locale        -> /etc/locale.conf (LANG), read by
#                                       systemd PID 1 and inherited by every
#                                       unit, including gdm and the child's
#                                       `systemd --user`
#   2. the console keymap            -> /etc/vconsole.conf (KEYMAP=uk)
#   3. the X11/Wayland system layout -> /etc/X11/xorg.conf.d/00-keyboard.conf
#                                       (XkbLayout "gb"), which is what
#                                       systemd-localed owns and what mutter
#                                       (gnome-kiosk, the GDM greeter) asks it
#                                       for
#   4. the child session's layout    -> org.gnome.desktop.input-sources in the
#                                       kid dconf profile, because GNOME's
#                                       per-session input sources override (3)
#                                       the moment a session starts
#
# Per-application locale settings that are NOT here, because the application
# owns a file of its own: GCompris (locale=en_GB.UTF-8 in gcompris-qt.conf,
# 55-gcompris.sh), Tux Paint (lang=british-english in tuxpaint.conf,
# 50-activities.sh) and KLettres (/etc/xdg/klettresrc). Each is asserted in
# its own stage; this one asserts the system underneath them all.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

readonly WANT_LOCALE=en_GB.UTF-8

# -----------------------------------------------------------------------------
# 1. the locale data has to exist
# -----------------------------------------------------------------------------
#
# base-main inherits glibc-all-langpacks from the Fedora base, which already
# carries every locale including en_GB -- so on today's base image there is
# nothing to install and `dnf5 install glibc-langpack-en` would add 6 MiB of
# duplicate locale data for nothing (measured: "After this operation, 6 MiB
# extra will be used"). Install it only if en_GB is genuinely absent, so a
# future base image that trims to glibc-minimal-langpack does not silently put
# the whole machine back into American English.
if locale -a 2>/dev/null | grep -qx 'en_GB.utf8'; then
    log "en_GB.utf8 is already in the locale archive (glibc-all-langpacks)"
else
    log "en_GB is missing from this base image; installing glibc-langpack-en"
    dnf5 -y install glibc-langpack-en
fi

locale -a 2>/dev/null | grep -qx 'en_GB.utf8' \
    || die "en_GB.utf8 is not in \`locale -a\` even after installing the langpack"

# `locale -a` normalises the codeset (en_GB.utf8), but LANG must be spelled the
# way setlocale() and every application config expects (en_GB.UTF-8). Prove
# that spelling actually resolves rather than trusting the normalisation.
LC_ALL="${WANT_LOCALE}" locale >/dev/null 2>&1 \
    || die "LC_ALL=${WANT_LOCALE} is not a usable locale"

# -----------------------------------------------------------------------------
# 2. the three system files from the overlay
# -----------------------------------------------------------------------------

readonly LOCALE_CONF=/etc/locale.conf
readonly VCONSOLE_CONF=/etc/vconsole.conf
readonly XKB_CONF=/etc/X11/xorg.conf.d/00-keyboard.conf

for f in "${LOCALE_CONF}" "${VCONSOLE_CONF}" "${XKB_CONF}"; do
    test -f "${f}" || die "${f} is missing from system_files/"
done

grep -qx "LANG=${WANT_LOCALE}" "${LOCALE_CONF}" \
    || die "${LOCALE_CONF} does not set LANG=${WANT_LOCALE}"
# One LANG line and no LC_ALL: LC_ALL in locale.conf would make every category
# unoverridable, including by a parent who wants a different one.
[[ "$(grep -c '^LANG=' "${LOCALE_CONF}")" == 1 ]] \
    || die "${LOCALE_CONF} sets LANG more than once"
! grep -q '^LC_ALL=' "${LOCALE_CONF}" \
    || die "${LOCALE_CONF} sets LC_ALL; that would override every category permanently"

grep -qx 'KEYMAP=uk' "${VCONSOLE_CONF}" || die "${VCONSOLE_CONF} does not set KEYMAP=uk"
# The keymap name has to be one kbd actually ships, or the console silently
# keeps `us` and a rescue shell types the wrong characters for a password.
test -e /usr/lib/kbd/keymaps/xkb/uk.map.gz \
    || find /usr/lib/kbd/keymaps -name 'uk.map*' -print -quit | grep -q . \
    || die "the 'uk' console keymap is not installed"

grep -Eq '^[[:space:]]*Option[[:space:]]+"XkbLayout"[[:space:]]+"gb"$' "${XKB_CONF}" \
    || die "${XKB_CONF} does not set XkbLayout gb"

# xkeyboard-config has to know the layout, or mutter falls back to `us` with
# only a warning in a journal nobody reads.
if [[ -f /usr/share/X11/xkb/rules/evdev.lst ]]; then
    grep -Eq '^[[:space:]]+gb[[:space:]]' /usr/share/X11/xkb/rules/evdev.lst \
        || die "xkeyboard-config has no 'gb' layout"
    log "xkeyboard-config knows the 'gb' layout"
fi

# -----------------------------------------------------------------------------
# 3. prove it, rather than assert the files exist
# -----------------------------------------------------------------------------
#
# A locale that is installed and named in a file is still not evidence that
# anything BEHAVES differently. These three are the differences a UK parent
# would notice on a school form, and they come from three different locale
# categories -- so all three passing means the whole locale, not one table.

# Day first. en_GB's %x is dd/mm/yy (03/02/26), en_US's is mm/dd/yyyy
# (02/03/2026) -- so comparing the two proves the ORDER changed rather than
# just that some locale was loaded. The year width is glibc's business and is
# deliberately not asserted.
date_uk="$(LC_ALL="${WANT_LOCALE}" date -u -d '2026-02-03' +%x)"
date_us="$(LC_ALL=en_US.UTF-8 date -u -d '2026-02-03' +%x)"
[[ "${date_uk}" == 03/02* ]] \
    || die "en_GB dates print as ${date_uk}, expected day-first (03/02...)"
[[ "${date_uk}" != "${date_us}" ]] \
    || die "en_GB and en_US format dates identically (${date_uk}); the locale is not being applied"

paper="$(LC_ALL="${WANT_LOCALE}" locale -k LC_PAPER | sed -n 's/^height=//p')"
[[ "${paper}" == "297" ]] || die "en_GB paper height is ${paper}mm, expected A4's 297"

measurement="$(LC_ALL="${WANT_LOCALE}" locale -k LC_MEASUREMENT | sed -n 's/^measurement=//p')"
[[ "${measurement}" == "1" ]] || die "en_GB measurement is ${measurement}, expected 1 (metric)"

log "locale: ${WANT_LOCALE} (dates ${date_uk}, A4, metric)"
log "keyboard: console 'uk', X11/Wayland 'gb'"
