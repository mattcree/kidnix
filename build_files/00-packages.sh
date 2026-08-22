#!/usr/bin/bash
# Install the v0.1 package set.
#
# Weak dependencies are left ON deliberately: GNOME's session plumbing
# (portals, pipewire, polkit agents) arrives via Recommends, and a kiosk that
# cannot play a sound or open a file chooser is not shippable. Trimming this is
# a later, measured optimisation -- not a day-one guess.
set -euo pipefail

PACKAGES=(
    # Display manager + the greeter session it needs.
    gdm

    # The kiosk compositor. Chosen over `cage` because it is GNOME-native:
    # same mutter core as the rest of the stack, ships systemd user units, and
    # has a11y and on-screen-keyboard subpackages we will want for young kids.
    gnome-kiosk
    gnome-kiosk-a11y

    # The session manager. It arrives as a weak dependency anyway, but the kid
    # session is now `gnome-session --session=kidnix` (build_files/60-shell.sh,
    # docs/spikes/session-integration.md) so it is load-bearing and must be
    # named: gnome-session is the only thing that raises
    # graphical-session.target, and without that target the portals refuse to
    # start. gnome-settings-daemon supplies the three gsd components the kid
    # session pulls in (a11y, media keys, sound).
    gnome-session
    gnome-session-wayland-session
    gnome-settings-daemon

    # The portals. `Requisite=graphical-session.target` on all three is what
    # docs/BUILDING.md "Known: no portals in the kid session" was about; the
    # gnome-session change above is the fix, and these are the things that then
    # come up. A file chooser inside an activity needs them.
    xdg-desktop-portal
    xdg-desktop-portal-gnome
    xdg-desktop-portal-gtk

    # The shell itself (shell/ in the repo, installed by 60-shell.sh). It is
    # pure Python with no PyPI dependencies at all -- GTK4, libadwaita,
    # PyGObject and speechd come from here, which is why shell/pyproject.toml
    # declares `dependencies = []` and its venv is --system-site-packages.
    python3-gobject
    gtk4
    libadwaita
    python3-speechd

    # Parental controls: app filtering and screen time. malcontent-control is
    # the parent-facing GUI; both are wired into Flatpak/GNOME already.
    malcontent
    malcontent-control

    # Text-to-speech, for pre-readers.
    speech-dispatcher
)

dnf5 -y install "${PACKAGES[@]}"

# Assert the things the rest of the image depends on actually landed, so a
# silent upstream rename fails the build here instead of at first boot.
#
# gnome-text-editor used to be here as the kiosk session's placeholder payload.
# The real shell landed (build_files/60-shell.sh), so it is gone -- do not add
# it back for the child; a five-year-old has no use for a plain-text editor and
# it is one more window manager surface to reason about.
for binary in /usr/bin/gnome-kiosk /usr/sbin/gdm /usr/bin/gnome-session; do
    test -x "${binary}" || { echo "missing expected binary: ${binary}" >&2; exit 1; }
done
