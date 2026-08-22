# Spike: how the first-wave activities ship

**Status:** implemented and green. Written 2026-08-22 against Fedora 44 /
`ghcr.io/ublue-os/base-main:44`. Every size and package version below was
measured in that image, not remembered.

`localhost/kidnix:activities` builds, `bootc container lint` passes (13 checks),
`tests/image/test_image.sh` is 48/48 and `tests/image/test_activities.sh` is
70/70. Nothing here has been seen in a running graphical session — see §8.

**Answers:** `docs/research/07-linux-stack.md` §4 item 3 (Flatpaks in an
immutable image — flagged as *"the highest-risk unknown in the whole build"*),
item 8 (GCompris offline voices), item 12 (disk budget), item 13 (Kiwix).

---

## 1. Decision: RPM-first

**Fedora 44 packages nine of the ten first-wave activities.** The Flatpak
question that the research called the highest-risk unknown turns out not to be
on the critical path at all: it applies to exactly one app (TurboWarp), and that
app is for the top of the age band, not for a five-year-old.

Verified with `dnf5 repoquery` inside `base-main:44`:

| Activity | Fedora 44 RPM | Flathub equivalent |
|---|---|---|
| GCompris | `gcompris-qt` **26.1** | `org.kde.gcompris` 26.1 |
| Tux Paint | `tuxpaint` **0.9.35** (+ `tuxpaint-stamps` 2020.05.29) | 0.9.35 |
| KTuberling | `ktuberling` **26.04.3** | 26.08.0 |
| Blinken | `blinken` **26.04.3** | 26.08.0 |
| KLettres | `klettres` **26.04.3** | 26.04.3 |
| Kolf | `kolf` **26.04.3** | 26.08.0 |
| SuperTux | `supertux` **0.6.3** | 0.7.0 |
| TuxMath | `tuxmath` **2.0.3** | 2.0.3 |
| Kiwix | `kiwix-tools` **3.8.1** (`kiwix-serve`) | `org.kiwix.desktop` (stale, EOL runtime) |
| TurboWarp | **not packaged** | `org.turbowarp.TurboWarp` 1.16.0 |

**Not in Fedora 44 at all:** `tuxtype` (checked — absent; only `tuxmath` is
packaged from the Tux4Kids set), `gcompris-qt-voices` (checked — no such
subpackage; §3 below is the consequence).

Why RPM wins for a child's appliance, in priority order:

1. **It lands in `/usr`.** That is the half of the filesystem bootc versions,
   ships atomically and can roll back. A Flatpak lands in `/var/lib/flatpak`,
   which bootc treats as machine-local and throws away at install time —
   `bootc container lint` fails the build if you try to ship content there.
   So a Flatpak activity is *not* covered by the "cannot be broken" guarantee
   in AGENTS.md §3.8; an RPM one is.
2. **No first-boot network.** The child session has no egress by design. An RPM
   activity works on a machine that has never been online. A Flatpak one needs
   one successful online boot before the tile does anything.
3. **One update mechanism.** `bootc upgrade` moves everything at once, and
   `bootc rollback` moves it all back. Flatpaks drift independently and roll
   back separately, which is a second failure mode on a machine nobody
   administers.
4. **Signed by Fedora**, on Fedora's security response, with no separate
   supply-chain surface to reason about.

The costs, honestly: Fedora's SuperTux (0.6.3) is a release behind Flathub's
0.7.0, and the KDE apps are on 26.04 rather than 26.08. Neither matters to a
five-year-old. Sandboxing is the real loss — a Flatpak activity is confined and
an RPM one is not — and that is why the lockdown work (nftables egress rules
keyed on `kid`'s uid, dconf locks, polkit) carries more weight in this design
than it otherwise would.

### What is deliberately not shipped

| Activity | Why not |
|---|---|
| Stellarium | 823 MiB, OARS 13+ |
| SuperTuxKart | ~791 MB, OARS 13+ |
| Luanti / Minetest | OARS 13+ |
| Marble | 729 MiB, and offline it is a low-res globe (needs network for tiles) |
| KAnagram, KHangMan, KGeography | 7+ and reading-first; wrong end of the band |
| KTurtle | 7+, typing-first. Cheap (+6 MiB) — a good second-wave pick |
| `kiwix-desktop` | 438 MiB of Qt5 for a UI a child should not see |
| `edu.mit.Scratch`, Kolibri, LMMS, ScratchJr | dead / EOL runtime / no Linux build |

---

## 2. Measurements

Method: `dnf5 -y install --assumeno <pkgs>` in `base-main:44`, reading the
`After this operation, N extra will be used` line — i.e. **installed size**, with
the full transitive dependency closure, not download size.

### Marginal cost is what matters, not standalone cost

The Qt 6 and KF 6 stacks dominate, and they are shared. Standalone numbers are
badly misleading:

| Group | Installed, alone | Marginal, on top of the rest |
|---|---:|---:|
| `gcompris-qt` (drags Qt 6 + qt6-qtwayland, 44 pkgs) | 248 MiB | — |
| `tuxpaint` | 39 MiB | — |
| `tuxpaint-stamps` | +193 MiB | +193 MiB |
| `ktuberling` (drags KF 6, 96 pkgs) | 432 MiB | ~194 MiB after Qt 6 |
| `blinken` | 247 MiB | **+3 MiB** after KF 6 |
| `kolf` | 344 MiB | **+3 MiB** after KF 6 |
| `klettres` | 297 MiB | **+48 MiB** after KF 6 |
| `kturtle` (not shipped) | 336 MiB | **+6 MiB** after KF 6 |
| `supertux` | 240 MiB | +240 MiB (self-contained) |
| `tuxmath`, weak deps on | 158 MiB | +158 MiB |
| `tuxmath`, `--exclude=fluid-soundfont-gm` | 16 MiB | **+16 MiB** |
| `kiwix-tools` | 7 MiB | +7 MiB |
| `espeak-ng` + `speech-dispatcher-espeak-ng` | 0 | **already in base-main** |
| `marble` (not shipped) | 729 MiB | — |
| `stellarium` (not shipped) | 823 MiB | — |

The lesson for the roadmap: **once GCompris and one KDE app are in, further KDE
activities are nearly free.** Blinken and Kolf cost 3 MiB each. That inverts the
"tiered images" plan in research §4 item 12 — the tier boundary is not "how many
KDE apps", it is "Qt 6 + KF 6 at all", which GCompris alone already forces.

### The one weak-dependency exclusion

`tuxmath` *Recommends* `fluid-soundfont-gm`: **142 MiB** of General MIDI
soundfont, nine times the size of the game, purely so its background music can
play. `00-packages.sh` deliberately leaves weak deps on across this image;
this is the single measured exception, taken as a size decision. If a child
notices the silence, add the soundfont back — do not drop the game.

### Image total

Measured with `podman image inspect --format '{{ .Size }}'` (uncompressed sum of
layers):

| | Size |
|---|---:|
| `ghcr.io/ublue-os/base-main:44` | 5.8 GiB |
| `localhost/kidnix:latest` (before activities) | 6.4 GiB |
| `localhost/kidnix:activities` | **7.6 GiB** |
| **activity payload** | **+1.2 GiB** |

Which breaks down, from `rpm -q --qf '%{SIZE}'` in the built image:

```
tuxpaint-stamps  193M      klettres          49M      tuxmath      15M
supertux         239M      tuxpaint          39M      kolf        3.3M
ktuberling        95M      gcompris-qt       34M      blinken     3.0M
gcompris assets   93M      kiwix-tools      171K
```

...plus the shared Qt 6 + KF 6 runtime, which is most of the remainder and is
what makes further KDE activities nearly free.

> **Warning for CI, per research §4 item 12:** the payload is ~1 GiB of
> activities on a 6.8 GB base. A GitHub-hosted standard runner has to hold the
> base image, the build cache and the output layer at once. If CI starts failing
> on disk, the tier split is the lever — and per the marginal-cost table above,
> a `kidnix-core` that drops Qt/KF 6 entirely (no GCompris, no KDE apps) is the
> only split that actually saves anything meaningful.

---

## 3. GCompris voices, words and music offline

**The problem.** `gcompris-qt` 26.1 ships **no audio at all** — `rpm -ql` gives
you a binary, a desktop file and translation `.qm` files, nothing else. Voices,
word images and background music are fetched from `https://cdn.kde.org/gcompris`
at runtime. There is **no `gcompris-qt-voices` subpackage** in Fedora 44
(checked). A child session with no egress therefore gets a silent GCompris,
which for a pre-reader means an unusable GCompris.

**The mechanism**, read out of upstream `master` on 2026-08-22
(`invent.kde.org/education/gcompris`) and cross-checked against `strings` on
Fedora's binary:

`src/core/DownloadManager.cpp`, `getSystemResourcePaths()` returns, in order:

```
QCoreApplication::applicationDirPath() + "/" + GCOMPRIS_DATA_FOLDER + "/rcc/"
ApplicationSettings::cachePath()
QStandardPaths::writableLocation(CacheLocation)
QStandardPaths::writableLocation(GenericDataLocation) + "/gcompris-qt"
QStandardPaths::standardLocations(AppDataLocation)          // /usr/share/KDE/gcompris-qt
```

`GCOMPRIS_DATA_FOLDER` is `"../@_data_dest_dir@"` (`src/core/config.h.in`), and
`_data_dest_dir` is `${CMAKE_INSTALL_DATADIR}/${GCOMPRIS_EXECUTABLE_NAME}` =
`share/gcompris-qt` (`CMakeLists.txt:230`). `applicationDirPath()` is `/usr/bin`.
So the first and best search root is:

```
/usr/share/gcompris-qt/rcc/
```

Corroborated independently: the Fedora RPM already installs translations to
`/usr/share/gcompris-qt/translations`, which is the sibling directory the same
CMake variable produces.

Under that root the app looks for `data3/<subdir>/<file>.rcc` — but only after
`initializeAssets()` has parsed the sibling **`Contents`** index. That function
populates the app's entire resource map from four files and nothing else:

```
data3/Contents
data3/voices-ogg/Contents
data3/backgroundMusic/Contents
data3/words/Contents
```

`parseContents()` wants `md5sum(1)` format (`<md5>  <filename>`) and rejects the
whole file if any line does not split into exactly two fields. **The index files
are load-bearing: an `.rcc` with no `Contents` entry is invisible.**

`COMPRESSED_AUDIO` defaults to `ogg` on Linux (`CMakeLists.txt:305`), which is
why the directory is `voices-ogg` and the key is `backgroundMusic-ogg`.

**What we ship** (`build_files/50-activities.sh`), fetched at build time,
md5-verified against upstream's own digests, into
`/usr/share/gcompris-qt/rcc/data3/`:

| File | Size | md5 (pinned) |
|---|---:|---|
| `voices-ogg/voices-en_GB-2026-07-28-15-07-14.rcc` | 13.7 MB | `efde411f…` |
| `voices-ogg/voices-en_US-2026-07-28-15-07-14.rcc` | 13.7 MB | `3c3f72d4…` |
| `words/words-webp-2022-04-10-21-14-15.rcc` | 43.1 MB | `d8bd7a3f…` |
| `backgroundMusic/backgroundMusic-ogg-2024-03-19-11-10-30.rcc` | 16.6 MB | `121469ac…` |
| **total** | **~87 MB** | |

en_GB is primary (UK household). en_US is the fallback: when the system locale
is `C`, `ApplicationInfo::getVoicesLocale()` returns `en_US`, and `en_GB`/`en_US`
are two of only five locales GCompris keeps country-specific voices for.

We write **our own** `Contents` files listing only the bundles actually present,
rather than shipping upstream's index of ~50 locales — otherwise GCompris is told
about voices whose `.rcc` is not on disk and registers empty paths.

We do **not** ship `data3/Contents` (the top-level index), because it names only
the ~500 MB `full-{aac,mp3,ogg}.rcc` bundles, which we are not shipping.

Filenames and digests are **pinned**, not resolved from the live index, so a CDN
rotation becomes an explicit reviewed bump rather than a silent content change
under a child's OS — the same reasoning as pinning `BASE_TAG=44`.

**Belt and braces:** even with automatic downloads left on, `DownloadManager`'s
`outError` path registers any local `.rcc` it can find when the `Contents`
download fails — so an offline machine falls back to the baked-in bundles.
`/usr/share/kidnix/activities/gcompris-qt.conf.default` additionally sets
`enableAutomaticDownloads=false` and `locale=en_GB.UTF-8`; GCompris' config is
per-user (`~/.config/gcompris/gcompris-qt.conf`, `src/core/main.cpp:78`), so
something has to copy it into the kid's home — see open questions.

### Licence

GCompris **code** is AGPL-3.0-only (Fedora's `%license` field). The bundled
**assets** — voice recordings, word images, background music — are the GCompris
project's own, released under CC-BY-SA-4.0 / GPL-3.0-or-later. Redistributable
in an image; recorded here per AGENTS.md §5.

### Verification status

- **Verified:** the search paths, the `data3/<subdir>/{Contents,*.rcc}` layout,
  the `Contents` format, the md5 algorithm (`DownloadManager.h:122`,
  `QCryptographicHash::Md5`), the locale-key derivation, and that the files are
  on disk in the built image with matching digests (`test_activities.sh`).
- **NOT verified:** that GCompris *actually speaks* from them. That needs a
  running session.

**The exact check to run**, once a VM boots into the kiosk:

```sh
# as the kid user, in the graphical session
QT_LOGGING_RULES='*.debug=true' gcompris-qt 2>&1 | grep -iE 'Contents:|voices|register'
```

Expect `Contents:  en_GB  ->  voices-en_GB-….rcc` and a successful
`registerResourceAbsolute` for the `/usr/share/gcompris-qt/rcc/...` path, with no
`does not exist, cannot parse Contents` line. Then open any activity that speaks
and confirm audio. If the paths turn out to be wrong, the cheap fallback is a
symlink from `/usr/share/KDE/gcompris-qt/data3` (search path #5) to the real
directory — no re-download needed.

---

## 4. Flatpak: options, and what was prototyped

Needed for exactly one app today — **TurboWarp**, the offline Scratch 3 fork.
There is no supported Linux ScratchJr, `edu.mit.Scratch` is abandoned on an EOL
runtime, and Fedora packages neither.

### (a) First-boot `flatpak install` from Flathub — **prototyped, shipping**

`kidnix-flatpaks-firstboot.service` + `.timer` +
`/usr/libexec/kidnix-flatpak-firstboot`, reading app IDs from
`/usr/share/kidnix/flatpaks.txt`.

- Needs the network **once**, on the parent's setup pass.
- Offline is the normal state for this machine, so the helper returns
  `75` (`EX_TEMPFAIL`) rather than failing; the unit declares
  `SuccessExitStatus=0 75` and the timer retries every 30 min.
- A stamp at `/var/lib/kidnix/flatpaks-firstboot.done` plus
  `ConditionPathExists=!` makes the unit a no-op once complete.
- Adds the `flathub` remote if absent (base-main ships `flatpak`, not the remote).

**Pros:** ~30 lines, no image-size cost, no new build step, standard Flatpak.
**Cons:** the tile does nothing until an online boot happens, so the shell has to
check at runtime; and the machine has to be online at all, once, which is exactly
the property we removed everywhere else.

### (b) Sideload repo baked into `/usr/share/kidnix/flatpak-repo` — **not implemented**

`flatpak create-usb` / an OSTree repo in the image, then
`flatpak install --sideload-repo=…` at first boot with no network.

**Pros:** genuinely offline; the activity is present on a machine that has never
been online; the repo lives in `/usr` so it is versioned and rollback-covered.
**Cons:** +382 MB in the image for one app *plus* the runtime
(`org.freedesktop.Platform` is another ~1 GB uncompressed), which roughly
doubles the image for one 6+ activity; and it needs a new build step
(`flatpak create-usb` inside the build, which needs a populated installation to
copy from — awkward in a container build). **Revisit when there are 3+ Flatpak
activities, or if "works on a machine that was never online" becomes a hard
requirement.**

### (c) A Flatpak installation under `/usr`, via `installations.d` — **not implemented, unverified**

`/etc/flatpak/installations.d/kidnix.conf` pointing `Path=` at a read-only
directory in `/usr`, populated at build time.

**Pros:** the tidiest fit with bootc semantics — activities in `/usr`, versioned,
rollback-covered, zero first-boot work.
**Cons:** entirely unverified. Flatpak expects its installation directory to be
writable (repo locks, `.changed` stamps, per-installation overrides), and it is
not established that a read-only installation is a supported configuration. It
would also put the `--unshare=network` override in a read-only place, which
conflicts with the lockdown design that copies a global override into
`/var/lib/flatpak/overrides/`. **This is the remaining spike**, and it is only
worth doing if (b) proves too fat.

### Network policy

The child session must not reach the internet through a Flatpak. The global
`flatpak override --system --unshare=network` is **owned by the lockdown work**
(`system_files/usr/share/kidnix/flatpak/overrides-global`, copied into
`/var/lib/flatpak/overrides/global` on first boot by tmpfiles). This spike only
*notes* the dependency: `kidnix-flatpak-firstboot` logs a warning if that file is
absent after an install, so a regression shows up in the journal rather than as a
child quietly online.

---

## 5. Activity manifest schema

`/usr/share/kidnix/activities/<id>.toml`, one per activity. TOML because
`tomllib` is in the Python standard library (`python3` 3.14.7 is already in
base-main), so validation costs nothing at build time or in tests.

| Key | Type | Meaning |
|---|---|---|
| `schema` | int | Format version. Currently `1`. |
| `id` | str | Stable identifier; **must** equal the filename stem. |
| `name` | str | Display name. |
| `audio_label` | str | What the shell speaks when the tile is focused. Written for a pre-reader: what it is, then what you do with it. |
| `icon` | str | Icon name or path. |
| `icon_kind` | str | `icon-name` or `path`. |
| `exec` | list[str] | argv. Not a shell string — no quoting bugs, no shell. |
| `category` | str | `make` / `learn` / `play`. Drives the shell's grouping; "making over consuming" is a non-negotiable, so the split is structural. |
| `age_min`, `age_max` | int | Band this is right for. |
| `oars_rating` | str | OARS 1.1 string, or `none`. |
| `network_required` | bool | **Must be false.** The child session has no egress; a true here is a build failure. |
| `content_required` | bool | Optional. True when the activity needs data a parent must add (Kiwix ZIMs) — the shell hides the tile until then. |
| `source` | str | `rpm` or `flatpak`. Only `rpm` activities are guaranteed present in the image. |
| `package` | str | RPM name or Flatpak app ID. |
| `licence` | str | Recorded per AGENTS.md §5. |
| `journal_watch` | list[str] | Directories the Journal watches for things the child made. |
| `wayland_native` | bool | False means XWayland (or unknown). |
| `notes` | str | Prose for humans, including what is unverified. |

Validated twice: at build time (`50-activities.sh`, fails the build) and in
`tests/image/test_activities.sh`. Both check that every `rpm`-sourced manifest's
`exec[0]` is actually on `PATH` — the failure mode this prevents is a tile that
does nothing, which to a pre-reader is indistinguishable from a broken computer.

Ten manifests: `tuxpaint`, `gcompris`, `ktuberling`, `blinken`, `klettres`,
`kolf`, `supertux`, `tuxmath`, `kiwix`, `turbowarp`.

---

## 6. Tux Paint configuration

Written to `/etc/tuxpaint/tuxpaint.conf` — the system-wide path confirmed in
`tuxpaint(1)` and in the shipped default. Syntax is `key=value`, one option per
line, each matching a `--long-option`.

**It is written by `50-activities.sh`, not dropped in `system_files/`**, because
the `tuxpaint` RPM owns that path as a `%config` file (`rpm -qc tuxpaint`) and
the dnf transaction would clobber an overlay copy that was staged before it.

| Setting | Why |
|---|---|
| `fullscreen=native` | The shell owns the screen. `native` uses the panel's own resolution instead of making the compositor rescale a guessed mode. |
| `sound=yes` | For a pre-reader, sound is not decoration — it is half the feedback. |
| `stamps=yes` | Stamps are most of what makes Tux Paint fun at four. (Costs 193 MiB.) |
| `saveovernew=yes` | The default is to *ask* "save over the old file?". A five-year-old cannot answer that. Always write a new file, so nothing a child made can be destroyed by saving again. |
| `autosave=yes` | Never ask "do you want to save?" on the way out. Quitting saves. |
| `nolockfile=yes` | Tux Paint refuses to start twice within 30 seconds. In a kiosk where the shell may relaunch after a crash, that is a mysteriously dead button. |
| `quit=yes` (default, explicit) | `noquit` was considered and rejected: the shell must be able to close an activity, and a child needs an exit that is not "ask a grown-up to reboot". |

**Considered and left out, as questions rather than answers:**

- `uppercase=yes` — shows all text in capitals, which some argue suits 4-5 year
  olds who learn capitals first. But UK Reception teaches lowercase first
  (phonics), and Tux Paint's Text tool is not the point of the activity.
  **Question for the human, to test with the actual child.**
- `nobuttondistinction` — exists (listed in the shipped conf's FIXME block) but
  is undocumented in `tuxpaint(1)`. Not shipped without knowing what it does.
- `--savedir` — left at the default `~/.tuxpaint/saved/` so the Journal has a
  stable, documented path to watch. Revisit if the Journal wants its own root.
- `nosave` — explicitly *not* set. "Making over consuming" requires that what a
  child makes persists.

---

## 7. Kiwix (research §4 item 13)

Research flagged that `org.kiwix.desktop` on Flathub is 20 months stale on an EOL
KDE runtime while upstream is alive. Resolved by taking neither: Fedora 44 *does*
package `kiwix-desktop` 2.5.1 (current), but it costs **438 MiB** of Qt 5 for a
desktop UI a child should never see.

**We ship `kiwix-tools` 3.8.1 (7 MiB), which is `kiwix-serve`,** and let the
kidnix shell be the viewer. The manifest's `exec` starts the server on
`127.0.0.1:8172` against `/var/lib/kidnix/library/library.xml`.

**The viewer is TBD and is the real open question**: something must render
`http://127.0.0.1:8172/` without being a web browser (non-negotiable: no web
browser). WebKitGTK inside the shell is the obvious candidate and fits the
GTK4/PyGObject shell pick in research §3.

**Content is not shipped.** The practical kid bundle is
`wikipedia_en-simple_all_mini` (450 MB) + `vikidia_en_all_nopic` (8 MB). Baking
458 MB of encyclopedia into every image is not defensible before someone has
watched a five-year-old actually use it. `content_required = true` in the
manifest tells the shell to hide the tile until a parent adds a ZIM.

---

## 8. Open questions for the thinker

1. **Does GCompris speak?** The one thing this spike could not verify without a
   VM. Exact check in §3. *Blocking for the anchor app.*
2. **Who seeds `~/.config/gcompris/gcompris-qt.conf`?** GCompris' settings are
   per-user and cannot be shipped read-only in `/usr`. The default is parked at
   `/usr/share/kidnix/activities/gcompris-qt.conf.default`; the shell's
   first-run path or a tmpfiles `C` line has to copy it. Overlaps with the
   `/var` first-boot ordering risk (research §4 item 11).
3. **GCompris background music defaults to on.** 16.6 MB shipped and
   `enableBackgroundMusic` defaults true. Autoplaying music in a bounded session
   is at least adjacent to the "no autoplay" principle. Taste call.
4. **`uppercase=yes` for Tux Paint?** See §6. Needs the actual child.
5. **SuperTux has lives and game-over.** The only activity in the set with a
   real failure state, against a design constitution that is wary of surprise
   endings. Worth watching a five-year-old hit it before deciding it stays.
6. **TuxMath's Wayland story is the weakest.** SDL 1.2 via `sdl12-compat`;
   research §2.5 flags the Flathub build as X11-only. `wayland_native = false`
   in the manifest is a guess, not an observation.
7. **Wayland-native is inferred throughout**, not observed. Qt apps get
   `qt6-qtwayland` (asserted at build time), and SDL prefers Wayland on Fedora
   44 — but nothing here has been seen rendering in a real kiosk session.
8. **Second wave is nearly free.** KTurtle +6 MiB, GNOME Nibbles +4 MiB,
   Minuet, KAnagram, KHangMan all ~3-10 MiB marginal now that Qt 6 + KF 6 are
   paid for. The expensive additions are content, not code: SuperTuxKart,
   Stellarium, Marble, ZIM files.
9. **Tiering (research §4 item 12) needs rethinking.** The marginal-cost data
   says a `kidnix-core` / `kidnix-full` split only saves real space if `core`
   drops Qt 6 + KF 6 entirely — which means dropping GCompris, the anchor app.
   That is probably not a tier anyone wants.
10. **Option (c)** — a read-only Flatpak installation under `/usr` — remains
    unverified. Only worth spiking if the sideload-repo route (b) is needed and
    proves too fat.
