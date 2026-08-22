#!/usr/bin/bash
# The parent's desktop: a stock GNOME Shell session on the same GDM greeter.
#
# ADR-0005. The child gets `kidnix-shell`; the adult who owns the machine gets
# ordinary GNOME, because Sugar's fatal wound was that grown-ups could not use
# the computer, and because GNOME 50 already ships the screen-time / parental
# plumbing (malcontent, Settings -> Wellbeing) that kidnix should consume
# rather than reimplement (research 04 sec 5.4, 07 sec 2.2-2.3).
#
# THE SURPRISE, and the reason this stage is 20 lines of dnf5 rather than 200:
# most of GNOME is ALREADY in the image before this script runs. `gdm` hard-
# requires `gnome-shell` (for the greeter) and `gnome-session-wayland-session`,
# and `gnome-shell` hard-requires `gnome-control-center`. So
# /usr/share/wayland-sessions/gnome.desktop, gnome-settings-daemon and
# xdg-desktop-portal-gnome are on disk the moment you install a display
# manager. ADR-0005 estimated +400-700 MB for this stage; the measured delta
# was ~63 MiB (see docs/spikes/parent-desktop.md), 38 MiB of which was
# wallpaper -- and that 38 MiB is now gone too (see the PACKAGES comment).
#
# What we deliberately do NOT install: the `gnome-desktop` comps group. Its
# mandatory list alone drags in gnome-software, gnome-initial-setup and yelp,
# and its default list adds ~50 more (gnome-boxes, gnome-maps, showtime,
# rygel, sane scanner backends...). Every one of those is attack surface a
# parent has to trust on a child's machine, and an app store on a locked-down
# appliance is an anti-feature.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# 0. Baseline, so the delta this stage costs is a number in the build log and
#    not a guess in an ADR. %{SIZE} is the installed (unpacked) size.
# -----------------------------------------------------------------------------

size_before="$(rpm -qa --qf '%{SIZE}\n' | awk '{ s += $1 } END { print s + 0 }')"
count_before="$(rpm -qa | wc -l)"

# -----------------------------------------------------------------------------
# 1. Packages
# -----------------------------------------------------------------------------

PACKAGES=(
    # The session itself. All three are already present via gdm/gnome-shell;
    # naming them explicitly makes the dependency intentional rather than
    # accidental, so a future base-image change that stops pulling them in
    # fails here instead of leaving the parent with no desktop.
    gnome-shell
    gnome-session-wayland-session
    gnome-settings-daemon
    gnome-control-center
    xdg-desktop-portal-gnome

    # A file manager and a terminal: the two things that make the difference
    # between "a desktop" and "a demo". ptyxis is Fedora 44's default terminal
    # (it replaced gnome-terminal); it brings vte291-gtk4 with it.
    nautilus
    ptyxis

    # malcontent-client(1). The parent panel and kidnix's own tooling need a
    # scriptable way to read and write the child's app filter and session
    # limits; without malcontent-tools the only interface is D-Bus by hand.
    malcontent-tools

    # NOT gnome-backgrounds. It used to be installed here, and at 37.8 MiB it
    # was 60% of this entire stage. GNOME's default picture-uri does point into
    # it, so something has to take its place or the parent's first login is a
    # grey rectangle that reads as "broken" -- that something is
    # build_files/70-hardening.sh, which ships one kidnix wallpaper (~110 KiB)
    # and makes it the parent's dconf default. See docs/spikes/hardening.md.
)

dnf5 -y install "${PACKAGES[@]}"

# The things the group would have added, that we are on record as not wanting.
# Something else pulling them in later (a Recommends, a group upgrade) is a
# design regression and should stop the build, not ship quietly.
for unwanted in gnome-software gnome-initial-setup gnome-boxes yelp \
                gnome-user-share gnome-classic-session epiphany; do
    if rpm -q "${unwanted}" >/dev/null 2>&1; then
        die "${unwanted} got pulled into the image; see ADR-0005 (no app store, no setup wizard, no help-browser web engine on a child's machine)"
    fi
done

# ...and the things that ALREADY arrived, before this stage ran, as weak
# dependencies of gnome-shell (which gdm hard-requires). We still do not remove
# them HERE -- 00-packages.sh owns the install_weak_deps policy and its comment
# says leaving Recommends on is a deliberate day-one choice -- but we count
# them, so the number appears in every build log and the decision stays visible
# rather than becoming invisible background radiation.
#
# build_files/70-hardening.sh is where the decision now lands: it runs after
# every install stage and removes gnome-remote-desktop, rygel, gnome-tour and
# gnome-color-manager outright. So this list is the "before" side of that
# measurement, and the extras it names should shrink to nm-connection-editor,
# gnome-bluetooth and bolt by the end of the build. See
# docs/spikes/hardening.md.
recommended_extras=()
for extra in gnome-remote-desktop rygel gnome-tour gnome-color-manager \
             nm-connection-editor gnome-bluetooth bolt; do
    if rpm -q "${extra}" >/dev/null 2>&1; then
        recommended_extras+=("${extra}")
    fi
done
if (( ${#recommended_extras[@]} )); then
    log "NOTE: ${#recommended_extras[@]} GNOME weak-dependency extras are in this image: ${recommended_extras[*]}"
fi

# -----------------------------------------------------------------------------
# 2. Assert the session actually exists
# -----------------------------------------------------------------------------

for binary in /usr/bin/gnome-shell /usr/bin/gnome-session /usr/bin/nautilus \
              /usr/bin/ptyxis /usr/bin/gnome-control-center \
              /usr/bin/malcontent-control /usr/bin/malcontent-client; do
    test -x "${binary}" || die "missing expected binary: ${binary}"
done

readonly GNOME_SESSION=/usr/share/wayland-sessions/gnome.desktop
test -f "${GNOME_SESSION}" || die "${GNOME_SESSION} is missing; the parent would have no session to log into"

# GDM resolves a session by the desktop file's basename, so `gnome` is the
# literal string that must appear in the parent's AccountsService file.
grep -q '^Exec=' "${GNOME_SESSION}" || die "${GNOME_SESSION} has no Exec line"

# We are on Wayland only: no /usr/share/xsessions, no gnome-session-xsession.
# Worth asserting, because an X session appearing in the greeter is a second
# code path nobody tests and a second lockdown surface.
if rpm -q gnome-session-xsession >/dev/null 2>&1; then
    die "gnome-session-xsession is installed; kidnix is Wayland-only"
fi

# -----------------------------------------------------------------------------
# 3. The parent's default session (AccountsService)
# -----------------------------------------------------------------------------
#
# Same mechanism as the kid (see build_files/20-users.sh for why this is a
# tmpfiles seed and not a file baked into the image: /var/lib/AccountsService
# is machine-local, so image content there is first-boot-only at best).
#
# Without this, which session GDM picks for `parent` depends on GDM's fallback
# ordering over /usr/share/wayland-sessions -- where `gnome.desktop` and
# `kidnix-shell.desktop` are the only two entries. A parent silently landing in
# the child's kiosk is a bad first five minutes; be explicit.

readonly AS_PARENT=/usr/share/kidnix/accountsservice-parent
test -f "${AS_PARENT}" || die "${AS_PARENT} is missing from system_files/"
grep -q '^Session=gnome$'  "${AS_PARENT}" || die "${AS_PARENT} does not set Session=gnome"
grep -q '^XSession=gnome$' "${AS_PARENT}" || die "${AS_PARENT} does not set XSession=gnome"

# The session name in that file is the desktop file's basename. Keep them in
# lockstep the same way 30-kiosk.sh does for the kid.
session_name="$(sed -n 's/^Session=//p' "${AS_PARENT}")"
test -f "/usr/share/wayland-sessions/${session_name}.desktop" \
    || die "the parent's Session=${session_name} does not name an installed session"

readonly TMPFILES_PARENT=/usr/lib/tmpfiles.d/kidnix-parent.conf
test -f "${TMPFILES_PARENT}" || die "${TMPFILES_PARENT} is missing from system_files/"
grep -q '/var/lib/AccountsService/users/parent' "${TMPFILES_PARENT}" \
    || die "nothing seeds the parent's AccountsService file on first boot"
systemd-tmpfiles --cat-config >/dev/null || die "tmpfiles config no longer parses"

# Prove the seed works, rather than trusting the syntax. systemd-tmpfiles
# executes items in *path* order across all fragments, so the `d` lines in
# kidnix.conf create and chmod the directories before this `C` line copies into
# them, regardless of which filename sorts first.
log "dry-running the AccountsService seed"
rm -rf /var/lib/AccountsService
systemd-tmpfiles --create "${TMPFILES_PARENT}" >/dev/null 2>&1 || true
grep -q '^Session=gnome$' /var/lib/AccountsService/users/parent \
    || die "the tmpfiles seed did not produce a parent AccountsService file"
# /var is machine-local and 90-cleanup.sh wipes it; leaving this behind would
# bake first-boot state into the image.
rm -rf /var/lib/AccountsService

# -----------------------------------------------------------------------------
# 4. Parent panel placeholder
# -----------------------------------------------------------------------------
#
# The real panel (libadwaita, ADR-0005) does not exist yet. The stub exists so
# the .desktop entry, its icon slot and its place in the parent's app grid are
# real from M1 onwards -- and so a boot test can assert the launcher is there
# before there is anything behind it.

test -f /usr/bin/kidnix-parent-panel \
    || die "/usr/bin/kidnix-parent-panel is missing from system_files/"
# COPY from system_files does not guarantee the mode we want, same as the
# libexec helpers in 40-lockdown.sh.
chmod 0755 /usr/bin/kidnix-parent-panel
bash -n /usr/bin/kidnix-parent-panel || die "the parent panel stub is not valid bash"

readonly PANEL_DESKTOP=/usr/share/applications/kidnix-parent-panel.desktop
test -f "${PANEL_DESKTOP}" || die "${PANEL_DESKTOP} is missing from system_files/"
grep -q '^Exec=/usr/bin/kidnix-parent-panel' "${PANEL_DESKTOP}" \
    || die "${PANEL_DESKTOP} does not exec the stub"

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "${PANEL_DESKTOP}" \
        || die "${PANEL_DESKTOP} is not a valid desktop entry"
fi

# -----------------------------------------------------------------------------
# 5. Report the delta
# -----------------------------------------------------------------------------

size_after="$(rpm -qa --qf '%{SIZE}\n' | awk '{ s += $1 } END { print s + 0 }')"
count_after="$(rpm -qa | wc -l)"

awk -v a="${size_before}" -v b="${size_after}" \
    -v ca="${count_before}" -v cb="${count_after}" \
    'BEGIN { printf "  -- parent desktop delta: %+d packages, %+.1f MiB installed\n", cb - ca, (b - a) / 1048576 }'

log "parent desktop installed"
