# kidnix licensing ledger

kidnix ships as a single OS image. Anything inside that image is something we
**redistribute**, so every piece of it needs a licence that permits
redistribution — including the parts nobody thinks of as software: fonts,
recorded voices, clip art, sound effects, and any bundled offline content.

AGENTS.md §5 makes this a standing rule: *"Bundled content/fonts/voices must be
redistributable; record licences."* This file is that record. **Adding anything
to the image means adding a row here in the same commit.**

Statuses used below:

- **yes** — verified redistributable inside an OS image, no extra obligation
  beyond shipping the licence text (which RPM packaging already does under
  `/usr/share/licenses/`).
- **yes, with notice** — redistributable, but we must carry an attribution or
  licence file ourselves because nothing else does.
- **planned** — not in the image yet; the row exists so the decision is made
  before the download, not after.

---

## 1. kidnix itself

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| kidnix source (build scripts, `system_files/`, shell, tests) | 0.1.0 | Apache-2.0 | <https://github.com/mattcree/kidnix> | `/usr/bin/kidnix-*`, `/usr/libexec/kidnix-*`, `/usr/lib/kidnix/`, `/usr/share/kidnix/` | yes — ours |
| kidnix documentation (`docs/`) | 0.1.0 | Apache-2.0 | same | not shipped in the image | yes — ours |

The `LICENSE` file at the repository root is the Apache-2.0 text, and
`org.opencontainers.image.licenses="Apache-2.0"` is set on the image.

## 2. Base image and OS packages

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| Universal Blue `base-main` | `ghcr.io/ublue-os/base-main:44` | Apache-2.0 (ublue's own build scripts); contents are Fedora's | <https://github.com/ublue-os/main> | the whole base layer | yes |
| Fedora 44 packages (~1,600 RPMs) | F44 | per-package; overwhelmingly GPL/LGPL/MIT/BSD/Apache — Fedora's licensing policy forbids non-redistributable content in the main repositories | <https://fedoraproject.org/> | everywhere; each package's text is under `/usr/share/licenses/<pkg>/` | yes |
| `openh264` (Cisco) | 44 | BSD-2-Clause, binaries distributed by Cisco | Fedora's `fedora-cisco-openh264` repo (enabled in `base-main`) | codec plugins | yes — Cisco pays the patent licence for the binaries it distributes |
| RPM Fusion / negativo17 multimedia (via `base-main`) | 44 | mixed; some packages are patent-encumbered in some jurisdictions | ublue's `base-main` build | codec stack | **inherited, not audited by kidnix** — see open question below |
| Mozilla Firefox | as shipped by `base-main` | MPL-2.0 | Fedora build | `/usr/bin/firefox` | yes — but see note |

> **Note on Firefox.** `base-main` ships Firefox; kidnix does not install it and
> does not want it. It is not reachable from the child session (no launcher, no
> network egress for uid 1000), and the parent may legitimately want a browser.
> Recorded here because "there is a web browser in the image" is a fact a parent
> is entitled to know. Removing it is an open question for M2.

## 3. Fonts

Both faces below are packaged by Fedora, so they arrive as ordinary RPMs with
their licence text installed — kidnix vendors no font binaries and carries no
checksummed downloads.

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| SIL Andika | 6.101 (`sil-andika-fonts-6.101-9.fc44`) | OFL-1.1 | <https://software.sil.org/andika/> · Fedora `sil-andika-fonts` | `/usr/share/fonts/sil-andika-fonts/`, licence at `/usr/share/licenses/sil-andika-fonts/` | yes — OFL permits bundling and redistribution; the reserved font name must not be used for a modified version |
| Atkinson Hyperlegible Next | 2.100 (`atkinson-hyperlegible-next-fonts-2.100-3.fc44`) | OFL-1.1 | <https://www.brailleinstitute.org/freefont/> · <https://github.com/googlefonts/atkinson-hyperlegible> | `/usr/share/fonts/atkinson-hyperlegible-next-fonts/` | yes — same OFL terms |
| Atkinson Hyperlegible Mono | 2.100 (`atkinson-hyperlegible-mono-fonts-2.100-3.fc44`) | OFL-1.1 | same | `/usr/share/fonts/atkinson-hyperlegible-mono-fonts/` | yes |
| Adwaita Sans / Adwaita Mono (GNOME 50 default UI faces) | 50.0 | OFL-1.1 | Fedora `adwaita-sans-fonts`, `adwaita-mono-fonts` | `/usr/share/fonts/adwaita-*-fonts/` | yes |
| `default-fonts-*` (Fedora's per-script default set, ~70 subpackages) | 4.3 | OFL-1.1 / GPL+FE / Apache-2.0 per family | Fedora | `/usr/share/fonts/` | yes |
| `sj-stevehand-fonts` (arrives with Tux Paint) | F44 | GPL-2.0-or-later | Fedora | `/usr/share/fonts/sj-fonts/` | yes |

**Why these two families**: Andika is designed by SIL specifically for literacy
and beginning readers (single-storey `a`, tailed `l`, unambiguous `I`/`l`/`1`);
Atkinson Hyperlegible is engineered by the Braille Institute for low-vision
legibility. Non-negotiable #4 ("pre-reader first") is the requirement they
serve. See `build_files/36-fonts.sh`.

**If Fedora ever drops them**, the fallback is a build-time fetch with SHA-256
verification from <https://software.sil.org/andika/download/> and
<https://github.com/googlefonts/atkinson-hyperlegible/releases>, unpacked into
`/usr/share/fonts/kidnix/`. Both are OFL-1.1, so this is permitted; the licence
text must be copied alongside the font files.

## 4. Activities (child-facing applications)

Owned by `build_files/50-activities.sh` and
`docs/spikes/activities-packaging.md`; summarised here so the ledger is
complete.

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| GCompris | 26.x (Fedora `gcompris-qt`) | GPL-3.0-or-later | Fedora | `/usr/bin/gcompris-qt` | yes |
| GCompris voice/word/music assets (`.rcc`) | dated bundles | CC-BY-SA-4.0 / GPL-3.0 (per KDE) | <https://cdn.kde.org/gcompris/> | `/usr/share/gcompris-qt/rcc/data3/` | yes — attribution carried by the bundles |
| Tux Paint + stamps | 0.9.35 | GPL-2.0-or-later; stamps individually licensed (mostly CC / public domain) | Fedora | `/usr/share/tuxpaint/` | yes — Fedora has already filtered non-free stamps |
| SuperTux | 0.6.3 | GPL-3.0-or-later; art CC-BY-SA | Fedora | `/usr/share/supertux2/` | yes |
| KTuberling, Blinken, KLettres, Kolf | KDE 26.04 | GPL-2.0-or-later | Fedora | `/usr/share/` | yes |
| TuxMath | 2.0.3 | GPL-3.0-or-later | Fedora | `/usr/share/tuxmath/` | yes |
| kiwix-tools | 3.8 | GPL-3.0-or-later | Fedora | `/usr/bin/kiwix-serve` | yes |
| TurboWarp (Flatpak, first boot) | — | GPL-3.0 (Scratch derivative, BSD-3-Clause upstream) | Flathub | `/var/lib/flatpak` at first boot | yes — installed on the device, not redistributed by us |

## 5. Parental controls and desktop

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| malcontent / -libs / -control / -tools | 0.14.0 | LGPL-2.1-or-later (libs), GPL-2.0-or-later (tools) | <https://gitlab.freedesktop.org/pwithnall/malcontent> · Fedora | `/usr/bin/malcontent-*`, `/usr/libexec/malcontent-*` | yes |
| GNOME 50 (Shell, Session, Settings, Nautilus, Ptyxis, gnome-kiosk) | 50.x | GPL-2.0-or-later / LGPL | Fedora | throughout | yes |
| `gnome-backgrounds` wallpapers | 50.0 | CC-BY-SA-3.0 / CC-BY-2.0 (per image) | Fedora | `/usr/share/backgrounds/gnome/` | yes — attribution is in the package |

## 6. Planned — decide before downloading

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| Text-to-speech voices (espeak-ng is the current fallback; a neural voice is wanted for pre-readers) | — | **TBD** | Piper voices (MIT/CC0/CC-BY mixed, per voice) · Mimic 3 | `/usr/share/kidnix/voices/` | **planned** — many Piper voices are trained on datasets with non-commercial or attribution terms; each voice must be checked individually |
| Offline reference content (Kiwix ZIM files: Wikipedia for Schools, Wiktionary) | — | CC-BY-SA-3.0/4.0 for Wikimedia content | <https://library.kiwix.org/> | `/usr/share/kidnix/zim/` | **planned** — CC-BY-SA requires carrying attribution and licence; ZIMs embed it, but the image must not strip it |
| First-party activity art and sounds | — | Apache-2.0 or CC-BY-SA-4.0 (decide by ADR) | ours | `/usr/share/kidnix/activities/` | **planned** |
| Icon set for the child shell | — | **TBD** | candidates: Adwaita (already present), Papirus (GPL-3.0) | `/usr/share/icons/` | **planned** |
| Sound effects for the shell (ending ritual, success chimes) | — | **TBD** | candidates: freesound.org (per-clip CC), GNOME sound theme (CC-BY-SA) | `/usr/share/sounds/kidnix/` | **planned** — per-clip licences, so a manifest is required |

---

## Open questions

1. **Codec provenance.** `base-main` enables RPM Fusion / negativo17 and Cisco
   openh264. Fedora proper deliberately does not ship some of these. Shipping
   them is fine for personal use, but if kidnix images are ever published as a
   product, the patent position needs a real answer. Tracked with ADR-0003's
   base-image revisit.
2. **Firefox.** In the image, unused by kidnix, unreachable by the child.
   Remove, or keep for the parent? A decision, not an accident.
3. **Voices are the hard one.** The most useful pre-reader voices are the
   neural ones, and their training-data licences are the least clear part of
   the whole stack. Budget real time for this before M3, and prefer a voice
   whose licence is stated per-voice in a machine-readable manifest.
4. **Automation.** This table is hand-maintained, which means it will drift.
   A `just licenses` recipe that walks `/usr/share/licenses/` in the built
   image and diffs against this file would make drift a build failure. Not
   built yet.
