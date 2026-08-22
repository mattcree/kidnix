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

    # Parental controls: app filtering and screen time. malcontent-control is
    # the parent-facing GUI; both are wired into Flatpak/GNOME already.
    malcontent
    malcontent-control

    # Text-to-speech, for pre-readers.
    speech-dispatcher

    # v0.1 placeholder payload for the kiosk session (see /usr/bin/kidnix-shell).
    # Replace with the real kidnix shell once it exists.
    gnome-text-editor
)

dnf5 -y install "${PACKAGES[@]}"

# Assert the things the rest of the image depends on actually landed, so a
# silent upstream rename fails the build here instead of at first boot.
for binary in /usr/bin/gnome-kiosk /usr/sbin/gdm /usr/bin/gnome-text-editor; do
    test -x "${binary}" || { echo "missing expected binary: ${binary}" >&2; exit 1; }
done
