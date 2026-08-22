# ADR-0006: Activities ship as Fedora RPMs first; Flatpak is the escape hatch

- Status: accepted
- Date: 2026-08-22

## Context

Research (*07 §4.3*) flagged "Flatpaks in an immutable image" as the
highest-risk unknown: bootc ships `/var` once, so `/var/lib/flatpak` content
is machine-local and needs first-boot network or a sideload repo. The
activity-packaging spike (`docs/spikes/activities-packaging.md`) found that
Fedora 44 packages nine of the ten first-wave activities (gcompris-qt 26.1,
tuxpaint + stamps, ktuberling, blinken, klettres, kolf, supertux, tuxmath,
kiwix-tools) and that marginal costs are small once Qt 6/KF 6 are present
(blinken/kolf ≈ 3 MiB each). Activities total +1.2 GiB on the image.

## Decision

- First-wave activities are installed as RPMs at image build time into
  `/usr`; they are covered by `bootc upgrade`/rollback and need no network.
- GCompris voices (en_GB, en_US), words and music are pre-seeded under
  `/usr/share/gcompris-qt/rcc/data3/` with md5-pinned `Contents` indexes so
  the no-egress child session has a speaking GCompris.
- Flatpak (Flathub) is used only where no RPM exists (TurboWarp as offline
  Scratch for the top of the age band), installed by a first-boot unit/timer
  that is harmless offline, with `--unshare=network` enforced globally.
- Excluded for now: marble (729 MiB, needs network), stellarium (823 MiB,
  OARS 13+), kiwix-desktop (438 MiB Qt 5), fluid-soundfont-gm (142 MiB for
  MIDI). The activity *shell* decides what a child sees — installing a
  package is not the same as exposing it (manifests + parent allow-list).

## Consequences

- Sandboxing of activities comes from the session (UID egress block, polkit,
  dconf locks), not from Flatpak. Acceptable: these are trusted FOSS apps run
  by a no-network user; revisit if we ever ship third-party binaries.
- A `kidnix-core` image only saves real space if it drops Qt 6 + KF 6 (i.e.
  drops GCompris); tiering is therefore deferred.
- Open: whether GCompris actually speaks from the seeded path (VM check), the
  per-user `gcompris-qt.conf` seeding, `uppercase=yes` for Tux Paint.
