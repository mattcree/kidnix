# kidnix licensing ledger

kidnix ships as a single OS image. Anything inside that image is something we
**redistribute**, so every piece of it needs a licence that permits
redistribution — including the parts nobody thinks of as software: fonts,
recorded voices, clip art, sound effects, and any bundled offline content.

AGENTS.md §5 makes this a standing rule: *"Bundled content/fonts/voices must be
redistributable; record licences."* This file is that record. **Adding anything
to the image means adding a row here in the same commit.**

**The machine-readable half of this file is
`system_files/usr/share/kidnix/THIRD-PARTY.tsv`**, shipped in the image at
`/usr/share/kidnix/THIRD-PARTY.tsv`. It carries one row (path, licence, source,
origin) for every file the image ships that did **not** arrive inside an RPM.
`tests/image/test_licenses.sh` fails the build when a vendored file has no row,
a row has no file, a row is missing from this ledger, or any licence anywhere in
the image is non-commercial or proprietary. Adding an asset therefore means
three edits in one commit: the download, the TSV row, and the row here.

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
| kidnix wallpaper (`default.svg` source, `default.png` render) | 0.1.0 | Apache-2.0 | same | `/usr/share/backgrounds/kidnix/` | yes — ours, drawn for kidnix; replaces the removed `gnome-backgrounds` |
| Activity-shell icons and generated earcons | 0.1.0 | Apache-2.0 | same | `…/site-packages/kidnix_shell/data/` | yes — ours; the earcons are synthesised at build time from `sound.py`, so no audio is vendored |

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
| GCompris voice/word/music assets (`.rcc`) | dated bundles, pinned by MD5 in `build_files/50-activities.sh` | CC-BY-SA-4.0 / GPL-3.0 (per KDE) | <https://cdn.kde.org/gcompris/data3/> | `/usr/share/gcompris-qt/rcc/data3/voices-ogg/`, `/usr/share/gcompris-qt/rcc/data3/words/`, `/usr/share/gcompris-qt/rcc/data3/backgroundMusic/` | yes — attribution carried by the bundles |
| Tux Paint + stamps | 0.9.35 | GPL-2.0-or-later; stamps individually licensed (mostly CC / public domain) | Fedora | `/usr/share/tuxpaint/` | yes — Fedora has already filtered non-free stamps |
| SuperTux | 0.6.3 | GPL-3.0-or-later; art CC-BY-SA | Fedora | `/usr/share/supertux2/` | yes |
| KTuberling, Blinken, KLettres, Kolf | KDE 26.04 | GPL-2.0-or-later | Fedora | `/usr/share/` | yes |
| TuxMath | 2.0.3 | GPL-3.0-or-later | Fedora | `/usr/share/tuxmath/` | yes |
| kiwix-tools | 3.8 | GPL-3.0-or-later | Fedora | `/usr/bin/kiwix-serve` | yes |
| **Sounds & Words** — kidnix's own activity (code, drawings, `icon.svg`) | 0.1.0 | Apache-2.0 | ours, <https://github.com/mattcree/kidnix> | `/usr/lib/python3.14/site-packages/sounds_and_words/`, `/usr/bin/kidnix-sounds-and-words`, `/usr/share/kidnix/icons/sounds-and-words.svg` | yes — ours |
| Letters and Sounds (2007) corpus — the graphemes, words, tricky words and sentences Sounds & Words reads | DFES-00281-2007, © Crown copyright 2007 | Open Government Licence v3.0 | <https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/> | `/usr/lib/python3.14/site-packages/sounds_and_words/data/` (`graphemes`, `words`, `tricky_words`, `sentences`, `lexicon`) | **yes, with notice** — every generated file carries the OGL attribution line, and `…/sounds_and_words/LICENSES.md` ships beside it |
| GCompris en_GB **letter-name** clips, unpacked from the `.rcc` at build time by `build_files/lib/rcc.py` | same bundle as the row above | CC-BY-SA-4.0 | <https://cdn.kde.org/gcompris/data3/voices-ogg/> | `/usr/share/kidnix/phonemes/en_GB/letter-names/` | **yes, with notice** — unmodified, and the attribution the bundle used to carry is written out beside them in `ATTRIBUTION` |
| Phoneme provenance ledger (generated) | 0.1.0 | Apache-2.0 | ours | `/usr/share/kidnix/phonemes/en_GB/phonemes.toml` | yes — ours |
| TurboWarp (Flatpak, first boot) | — | GPL-3.0 (Scratch derivative, BSD-3-Clause upstream) | Flathub | `/var/lib/flatpak` at first boot | yes — installed on the device, not redistributed by us |

> **A note on the phoneme audio, because it is the kind of thing a ledger hides.**
> Sounds & Words needs recordings of letter *sounds* — /s/, /a/, /t/. The only
> English speech kidnix already redistributes is GCompris' `voices-en_GB`, and
> its `alphabet/` set turned out to be the letters' **names** — the alphabet
> song, not phonics (`docs/spikes/first-party-install.md` has the measurements).
> Those 26 clips are therefore shipped as `letter-names/`, licensed and
> attributed as above, and **no code plays them**. There are no phoneme
> recordings in the image, none are synthesised, and
> `/usr/share/kidnix/phonemes/en_GB/phonemes.toml` says so for every one of the
> 114 grapheme–phoneme correspondences in the corpus. Recording them — about
> twenty clips, one adult, one morning — makes them kidnix's own CC-BY-SA-4.0
> asset and gets its own row here on the day it happens.

## 5. Parental controls and desktop

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| malcontent / -libs / -control / -tools | 0.14.0 | LGPL-2.1-or-later (libs), GPL-2.0-or-later (tools) | <https://gitlab.freedesktop.org/pwithnall/malcontent> · Fedora | `/usr/bin/malcontent-*`, `/usr/libexec/malcontent-*` | yes |
| GNOME 50 (Shell, Session, Settings, Nautilus, Ptyxis, gnome-kiosk) | 50.x | GPL-2.0-or-later / LGPL | Fedora | throughout | yes |
| `gnome-backgrounds` wallpapers | 50.0 | CC-BY-SA-3.0 / CC-BY-2.0 (per image) | Fedora | `/usr/share/backgrounds/gnome/` | yes — attribution is in the package |

## 6. Read-aloud (text-to-speech)

Owned by `build_files/65-tts.sh` and `docs/spikes/tts.md`. This is the one part
of the image where kidnix **vendors prebuilt binaries and model weights from
outside Fedora**, so it gets the most detail. Every artefact below is pinned by
SHA-256 in the build script and re-checked by `tests/image/test_tts.sh`; a CDN
rotation fails the build rather than shipping an unreviewed voice to a child.

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| `speech-dispatcher`, `speech-dispatcher-espeak-ng`, `python3-speechd` | 0.12.1-6.fc44 | GPL-2.0-or-later / LGPL-2.1-or-later | Fedora | `/usr/bin/spd-say`, `/usr/lib64/speech-dispatcher-modules/` | yes |
| espeak-ng (the guaranteed fallback voice, and Piper's phonemiser) | 1.52.0-3.fc44 | GPL-3.0-or-later | Fedora | `/usr/lib64/libespeak-ng.so.1`, `/usr/share/espeak-ng-data/` | yes — Fedora carries the source |
| **piper** (CLI) | `rhasspy/piper` 2023.11.14-2 (archived Oct 2025) | **MIT** | <https://github.com/rhasspy/piper/releases/tag/2023.11.14-2> · tarball sha256 `a50cb45f355b7af1f6d758c1b360717877ba0a398cc8cbe6d2a7a3a26e225992` (x86_64), `fea0fd2d87c54dbc7078d0f878289f404bd4d6eea6e7444a77835d1537ab88eb` (aarch64) | `/usr/lib/kidnix/piper/piper` | yes, with notice — licence text at `/usr/share/licenses/kidnix-piper/LICENSE.piper.md` |
| **libpiper_phonemize.so.1.2.0** | bundled in the same tarball | **MIT** | <https://github.com/rhasspy/piper-phonemize> | `/usr/lib/kidnix/piper/` | yes, with notice |
| **libonnxruntime.so.1.14.1** | 1.14.1, bundled in the same tarball | **MIT** | <https://github.com/microsoft/onnxruntime/tree/v1.14.1> | `/usr/lib/kidnix/piper/` | yes, with notice |
| **Voice: `en_GB-alba-medium`** — **the default voice** | piper-voices, retrieved 2026-08-23 | **CC-BY-4.0** — stated by the voice's own `MODEL_CARD`, which points at the Alba speech corpus | <https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/alba/medium> · corpus <https://datashare.ed.ac.uk/handle/10283/3270> (<https://doi.org/10.7488/ds/2506>) | `/usr/share/kidnix/voices/en_GB-alba-medium.onnx` (63,201,294 B, sha256 `401369c4a81d09fdd86c32c5c864440811dbdcc66466cde2d64f7133a66ad03b`); config sha256 `aa965a2f02ecced632c2694e1fc72bbff6d65f265fab567ca945918c73dd89f4`; card sha256 `fa166b1779404c470b0b6b4ba0238bc4a35bf89d2cd130c6788f697188b737d6` | **yes, with notice** — attribution carried at `/usr/share/licenses/kidnix-voices/ATTRIBUTION` |
| **Voice: `en_GB-cori-high`** | piper-voices, retrieved 2026-08-22 | **public domain** (training data: LibriVox, ~24 h) — stated by the voice's own `MODEL_CARD` | <https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/cori/high> · trained by <https://brycebeattie.com/files/tts/> | `/usr/share/kidnix/voices/en_GB-cori-high.onnx` (114,219,352 B, sha256 `470b4dd634c98f8a4850d7626ffc3dfc90774628eeef6605a6dd8f88f30a5903`); config sha256 `9e7fb5b5671612c22f3c81cbe46c1ae87b031a4632bcb509e499dad6f1e2adec` | yes — public domain, no attribution obligation |
| **Voice: `en_GB-cori-medium`** | same | **public domain**, same dataset and card | <https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/cori/medium> | `/usr/share/kidnix/voices/en_GB-cori-medium.onnx` (63,531,379 B, sha256 `1899f98e5fb8310154f3c2973f4b8a929ba7245e722b3d3a85680b833d95f10d`); config sha256 `e262c16d7f192f69d4edd6b4ef8a5915379e67495fcc402f1ab15eeb33da3d36` | yes |

**Which voices, and why the default moved.** *docs/research/07 §2.4* lists
eleven en_GB Piper voices. Their `MODEL_CARD` licences were re-read on
2026-08-22: `alba`, `aru` and `vctk` are CC-BY-4.0 (attribution to carry);
`northern_english_male` and `southern_english_female` are CC-BY-SA-4.0;
`jenny_dioco` requires attribution; **`semaine` is CC-BY-NC-SA-4.0 —
non-commercial, and therefore disqualified outright by AGENTS.md §5**; `alan`'s
card says only "See URL", which is not a licence. `cori` is the only en_GB
voice whose card states **public domain**, and the only one available at the
`high` tier.

That is why `cori` was the original default — and it was chosen *entirely* on
that basis, at a point where nobody in the loop had heard a single one of the
candidates (`docs/spikes/tts.md` §8.7 says so plainly: "no one has listened,
and that is still the only test that matters"). On **2026-08-23 someone
listened**, and cori was judged bad. So the default is now `alba`, and kidnix
takes on the one obligation it was previously avoiding.

**This is a deliberate trade, not a drift.** AGENTS.md §5 asks for content that
is *redistributable and recorded* — it does not ask for content that costs
nothing. CC-BY-4.0 is redistributable inside a commercial product; the price is
a credit, which is cheap, and the benefit is a voice a child will actually
listen to, which is the entire point of the subsystem. What remains refused is
unchanged: non-commercial (`semaine`) and unresolved (`alan`, `jenny_dioco`).

**The attribution is carried at
`/usr/share/licenses/kidnix-voices/ATTRIBUTION`**, written by
`build_files/65-tts.sh`. It names the depositors, the work, the DOI, the
licence URI, and the fact that the work was modified — CC-BY-4.0 §3(a)(1)(A–D)
item by item — plus the moral-rights sentence the corpus attaches on its own
account:

> Valentini-Botinhao, Cassia; Yamagishi, Junichi. (2019). Alba speech corpus,
> [dataset]. University of Edinburgh. <https://doi.org/10.7488/ds/2506>.
> Licensed under CC BY 4.0, <https://creativecommons.org/licenses/by/4.0/>.
> Modified: kidnix redistributes a neural model finetuned from those
> recordings, not the recordings themselves.

`tests/image/test_tts.sh` asserts each of those clauses separately, because the
file that discharges the obligation is a text file nothing else depends on, and
a tidy-up could delete it without breaking anything that makes a sound.

**All three models ship**; `/etc/kidnix/tts.env` picks which one loads, with no
rebuild and no network. `cori` stays precisely so that "the voice is wrong" is
a one-line fix for a parent rather than a rebuild — the same escape hatch that
was just used to get here.

**Two things we deliberately do *not* redistribute.**

1. Upstream's piper tarball bundles a prebuilt `libespeak-ng.so.1.52.0.1` and
   19 MB of `espeak-ng-data`. espeak-ng is **GPL-3.0-or-later**, and shipping
   someone else's prebuilt GPL binary means owing its corresponding source.
   `build_files/65-tts.sh` deletes both and links against Fedora's espeak-ng
   instead — verified byte-identical output (`--noise_scale 0 --noise_w 0`
   produces the same WAV either way), so this costs nothing and removes the
   obligation. Fedora carries espeak-ng's source; we carry none.
2. `libtashkeel_model.ort` (10 MB, Arabic diacritisation) is dropped as unused
   weight.

**A caveat worth writing down.** Piper's own README says its voice models are
"intended for personal use and text-to-speech research only". That sentence is
about the *project's* model collection as a whole, and it is not a licence — the
per-voice `MODEL_CARD` is, and cori's says public domain. For a personally-built
image this is settled. If kidnix images are ever published as a product, get a
real answer on that sentence before shipping, the same way open question #1
below treats codecs.

## 7. Planned — decide before downloading

| Item | Version | Licence | Source | Where in the image | Redistribution OK? |
|---|---|---|---|---|---|
| Offline reference content (Kiwix ZIM files: Wikipedia for Schools, Wiktionary) | — | CC-BY-SA-3.0/4.0 for Wikimedia content | <https://library.kiwix.org/> | `/usr/share/kidnix/zim/` | **planned** — CC-BY-SA requires carrying attribution and licence; ZIMs embed it, but the image must not strip it |
| First-party activity **sounds** (phoneme recordings for Sounds & Words) | — | CC-BY-SA-4.0 (decided: matches GCompris', so a clip can be swapped either way) | ours, to be recorded | `/usr/share/kidnix/phonemes/en_GB/` | **planned** — nothing recorded yet; §4 has what stands in for it |
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
3. ~~**Voices are the hard one.**~~ **Resolved for en_GB** — see §6. The
   default voice is CC-BY-4.0 with its attribution carried in the image and
   asserted by a test; a public-domain alternative ships alongside it and is
   one line away. Every model is pinned by SHA-256. Still open for other
   languages: the Welsh TTS that *docs/research/06 §7.5 #31* asks for has no
   public-domain Piper voice, so it is espeak-ng only for now.
4. ~~**Automation.**~~ **Partly resolved.** `just licenses` cross-checks
   `/usr/share/kidnix/THIRD-PARTY.tsv` against the image's filesystem and
   against this file, and screens every RPM `%{LICENSE}` against a
   non-commercial/proprietary denylist (one reviewed exception: Fedora's
   `LicenseRef-Callaway-Redistributable-no-modification-permitted` firmware
   tag). It runs in `just ci` and in `.github/workflows/build.yml`. What is
   still hand-maintained is the *prose* in this file — the TSV knows a path and
   an SPDX id, not why `cori` was chosen over `semaine`. Walking
   `/usr/share/licenses/` to catch an RPM whose licence text is missing
   entirely remains unbuilt.
