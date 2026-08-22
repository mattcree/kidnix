# Spike: turning GCompris' 198 activities into a shelf of 18

**Status:** implemented and green. `tests/image/test_gcompris.sh` is **46/46**
against `localhost/kidnix:gcompris`, `tests/image/test_activities.sh` still
**70/70** (the settings-file symlink in §2.1 did not disturb it), and
`just lint-shell` / `lint-containerfile` / `lint-yaml` / `lint-just` are clean.

Two caveats on the wider suite, both from work in flight beside this one. The
image was built from `HEAD` plus only this task's files, because another
worker's in-progress `build_files/40-lockdown.sh` edit fails the build outright
("nsswitch still routes hosts through nss-resolve"). Against that image
`just tag=gcompris test-image` is 8/10 scripts — `test_egress.sh` and
`test_licenses.sh` fail because they assert the build changes that were excluded
— and `just tag=gcompris test-boot` has one failure, the same egress worker's
"kid's DNS no longer escapes via systemd-resolved". Everything the boot test says
about the session coming up passes, which is what this spike needed from it: the
new tmpfiles fragment does not break boot.

What is **not** verified is that a child can play any of these. Nothing in this
loop has a display, so every claim below about what appears *on screen* is
inferred from the config GCompris reads back, not from a screenshot. See §7.

Everything here was measured against the actual image — `gcompris-qt 26.1-1.fc44`
under `podman run` with `QT_QPA_PLATFORM=offscreen` — and against upstream
source at `invent.kde.org/education/gcompris`. Where the existing code in
`build_files/50-activities.sh` was wrong, §2.1 says so.

The brief is `docs/research/05-learning-science.md` §3:

> Treat it as a **curated shelf, not a whole product**. Hand-pick 12–20
> activities mapped to EYFS/KS1 objectives; hide the rest behind a parent
> control. Group by what the child is *doing*, not by subject. Localise to en-GB
> and check every letter activity against a UK phonics progression before
> exposing it. Market it as "the ones we picked", never "100 activities!".

---

## 1. What was decided

| | |
|---|---|
| Shelf size | **18 of 198**, in 6 groups of 3 |
| Grouping | Point and click · Letters and sounds · Counting · Numbers in order, and adding · Look, listen and remember · Shapes, time and patterns |
| Difficulty | 1–2 stars only, on GCompris' own 1–6 rating (≈ ages 2–6) |
| Enforcement | the shell launches each one by name with `--launch`; the child never sees the menu |
| Backstops | `filterLevelMax=2`, `kiosk=true`, `homeButtonVisible=false`, `sectionVisible=false`, `[Favorite]` = the same 18 |
| Locale | `en_GB.UTF-8` — a real translation, not a stub ("Colours", "analogue clock") |
| Sound | voices **on**, background music **off** and volume zeroed |
| Network | `enableAutomaticDownloads=false`; assets baked in at build time by `50-activities.sh` |
| Delivery | image-owned files in `/usr/share/kidnix/gcompris/`, seeded to `~kid/.config/gcompris/` by tmpfiles at boot |
| Image delta | **0 bytes of packages** — ~30 KB of config and documentation |

The shelf itself, with the per-activity EYFS/KS1 mapping and the full list of
what was rejected and why, is
`system_files/usr/share/kidnix/gcompris/CURATION.md`. It is shipped *into the
image* rather than left in `docs/` on purpose: a parent asking "what are these
and why these?" should be able to get the answer off the machine.

---

## 2. How GCompris can and cannot be restricted

This was the whole question, and the answer is narrower than the task assumed.

**There is no per-activity enable/disable key.** `ActivityInfoTree::filterEnabledActivities()`
removes entries whose `ActivityInfo::enabled()` is false, and that is a QML
property compiled into the binary — nothing in `ApplicationSettings` reads or
writes it, and no `[Activities]` group exists anywhere. The groups
`ApplicationSettings.cpp` actually uses are `General`, `Admin`, `Internal`,
`Favorite`, `Levels`, `IgnoredLevels`, `Teacher`, plus one group per activity
name for that activity's own options (`loadActivityConfiguration()` /
`saveActivityConfiguration()`).

So there are exactly three levers, and they are not equal:

| Lever | What it does | Strength |
|---|---|---|
| `--launch <id>` | starts one activity, menu never drawn | **hard** — this is the one doing the work |
| `filterLevelMin` / `filterLevelMax` | 1–6 star *display* filter in the menu | soft; does not stop `--launch` |
| `[Favorite]` group | the menu's first tab filters on it (`filterByTag`, `isFavoriteTag && activity->favorite()`) | soft; only matters if the menu is reached |

kidnix uses all three. The shell gives each curated activity its own tile and
runs `gcompris-qt --launch <id> --hide-home-button`; the other two exist so that
a corrupted per-user config, or a future code path that does open the menu,
still lands somewhere age-appropriate.

**`--launch` fails open, and that is the sharp edge.** Given an id GCompris does
not recognise, it does not error and does not exit — it silently falls through
to the full 198-activity menu. A typo in the curated list is therefore a
lockdown hole that would surface as a child suddenly holding the whole suite.
Both `build_files/55-gcompris.sh` and `tests/image/test_gcompris.sh` check every
id against `gcompris-qt --list-activities`, which is why that assertion exists
twice.

### 2.1 The `[%General]` trap — and a bug this found

GCompris reads its settings with `QSettings::IniFormat` and does
`m_config.beginGroup("General")`. QSettings reserves the literal `[General]`
section for *top-level* keys, so a real group called `General` is escaped to
`%General` on write and looked for as `%General` on read. **A settings file
written with `[General]` parses without error and is then ignored in full.**

Demonstrated in the image rather than asserted:

```
$ printf '[%%General]\nlocale=fr_FR.UTF-8\n' > $XDG_CONFIG_HOME/gcompris/gcompris-qt.conf
$ gcompris-qt --export-activities-as-sql | grep clickgame
INSERT INTO activities VALUES(8, 'clickgame/Clickgame.qml', ..., "Clique sur les poissons", ...

$ printf '[General]\nlocale=fr_FR.UTF-8\n'  > $XDG_CONFIG_HOME/gcompris/gcompris-qt.conf
$ gcompris-qt --export-activities-as-sql | grep clickgame
INSERT INTO activities VALUES(8, 'clickgame/Clickgame.qml', ..., "Click on me", ...
```

**`build_files/50-activities.sh` writes `[General]`.** Its
`/usr/share/kidnix/activities/gcompris-qt.conf.default` — five settings
including `locale=en_GB.UTF-8` and `enableAutomaticDownloads=false` — would have
done nothing at all had it been seeded. It also puts
`enableAutomaticDownloads` under `[Admin]`, where it does not live.
`55-gcompris.sh` replaces that path with a symlink to the curated config, so
there is one file to review and `tests/image/test_activities.sh` keeps
resolving the path it knows. **The dead heredoc in `50-activities.sh` §2 should
be deleted outright — that is the activities owner's call, not this spike's.**

### 2.2 The key names, taken from GCompris rather than from memory

A first run against an empty `XDG_CONFIG_HOME` makes GCompris write its own
defaults, and that dump is the authority for every spelling used:

```
[%General]  audioEffectsVolume backgroundMusicVolume baseFontSize defaultCursor
            enableAudioVoices enableAutomaticDownloads enableBackgroundMusic
            exitConfirmation filterLevelMax filterLevelMin filteredBackgroundMusic
            font fontCapitalization fontLetterSpacing fullscreen homeButtonVisible
            isCurrentFontEmbedded kiosk locale noCursor previousHeight
            previousWidth sectionVisible virtualKeyboard
[Admin]     cachePath downloadServerUrl renderer userDataPath
[Internal]  exeCount lastGCVersionRan
[Teacher]   teacherId teacherPort
```

Three corrections to the assumptions in the brief:

- The key is **`kiosk`**, not `kioskMode`; **`exitConfirmation`**, not
  `exitConfirm`; **`enableAutomaticDownloads`**, not `isAutomaticDownloadsEnabled`
  (that is the Q_PROPERTY name, not the config key).
- **`useExternalWordset` is not a config key at all.** It is
  `return DownloadManager::getInstance()->isDataRegistered("words-webp")` — it
  is true because `50-activities.sh` bakes the words bundle in, and there is
  nothing to set.
- **`showLockedActivities` does not exist** in 26.1.

`fontCapitalization` is `QFont::Capitalization` (0 MixedCase, 1 AllUppercase,
2 AllLowercase). The brief asked for lowercase, and it is **deliberately left at
0**: GCompris renders activity letter data with the same font as its chrome, so
AllLowercase would flatten the letters `click_on_letter` asks the child to find
and break `memory-case-association` entirely — the one activity whose whole job
is the uppercase/lowercase mapping. Lowercase-first is served by *choosing
lowercase activities* instead (`click_on_letter`, never `click_on_letter_up`).

### 2.3 Teacher/server mode: looked at, not used

26.1 has a `[Teacher]` group (`teacherId`, `teacherPort=65524`) and dataset
plumbing (`DATASET_CREATION`, `acceptDataset`, `hasDataset`, `getDataset`) for
the separate GCompris-teachers server. It assigns *datasets* — level content
within an activity — from a networked teacher application. It is not a way to
express "these 18 activities", it needs a second machine and a socket, and the
child session has no egress. Rejected. If it is ever revisited, the useful part
is `loadActivityConfiguration(activity)`, which reads a QSettings group named
after the activity — that is how per-activity options (e.g. which letters
`click_on_letter` draws from) could be pinned locally without a server.

### 2.4 Round-trip behaviour

QSettings regenerates the whole ini on write, so **the comments in the shipped
config survive only in the `/usr` copy**; the seeded per-user file loses them the
first time GCompris writes. What does survive is the values. Three real
`gcompris-qt --launch clockgame` runs against a seeded copy left every key
unchanged and kept the `[Favorite]` group intact — GCompris only rewrites keys
it actually changes.

One exception worth recording, because it cost an hour: **`--export-activities-as-sql`
resets `filterLevelMin`/`filterLevelMax` to 1–6** (deliberately, so that it can
export everything) and writes that back. It is a probe artefact, not normal
behaviour, and it is why both the build stage and the image test run their
probes against a copy in `/tmp` and never against the file in `/usr`.

---

## 3. Where the config lives, and the upgrade trade-off

`src/core/main.cpp`:

```cpp
QSettings config(QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation)
                     + "/gcompris/" + GCOMPRIS_APPLICATION_NAME + ".conf",
                 QSettings::IniFormat);
```

`GenericConfigLocation` is `$XDG_CONFIG_HOME` (default `~/.config`). **There is
no system-wide fallback.** `QSettings::IniFormat` constructed with an explicit
filename does not consult `XDG_CONFIG_DIRS`, and GCompris never calls
`QSettings::setPath()`. Setting `XDG_CONFIG_DIRS` in the session would achieve
nothing. A symlink from the kid's home into `/usr` is also out: GCompris writes
this file, so the symlink would either fail against the read-only root or be
replaced by a plain file the first time the child quits.

So it has to be seeded, and `/usr/lib/tmpfiles.d/kidnix-gcompris.conf` does it
with `C` — copy only if the target does not exist — the same contract
`kidnix.conf` and `kidnix-lockdown.conf` already use for home directories.

**The trade-off, stated plainly: a seeded per-user file does not update on
`bootc upgrade`.** Ship a better shelf next month and an already-installed
machine keeps the old one forever. The three options:

| | Behaviour | Cost |
|---|---|---|
| `C` (**chosen**) | seed once, never touch again | a shelf change never reaches an installed machine |
| `C+` | overwrite on every boot | wipes `[Levels]`, so the child loses every level they have reached, every boot |
| generation-triggered unit | re-seed only when the shelf actually changes | needs a unit; not written |

The third is right and is not implemented here. The groundwork is: the image
carries `/usr/share/kidnix/gcompris/GENERATION` (an integer, also mirrored as
`generation` in `curated.toml` and checked equal by the image test), and tmpfiles
seeds a copy to `~kid/.config/gcompris/.kidnix-generation`. Because that copy is
also `C`, it keeps the *old* number across an upgrade while `/usr` holds the new
one — which is exactly the signal a re-seed unit needs:

```
# sketch, not shipped
if [[ "$(cat ~/.config/gcompris/.kidnix-generation)" != "$(cat /usr/share/.../GENERATION)" ]]; then
    merge [%General] and [Favorite] from /usr over the user's file, keep [Levels]
    cp /usr/share/.../GENERATION ~/.config/gcompris/.kidnix-generation
fi
```

It has to *merge*, not copy, or it reintroduces the `C+` problem. Nothing
consumes the marker yet; this is the open item in §7.

### 3.1 tmpfiles ordering

`kidnix-gcompris.conf` sorts **before** `kidnix.conf` by filename (`-` < `.`),
which would matter if `/var/home/kid` were created by the wrong entry — the `C`
line in `kidnix.conf` copies `/etc/skel` in only when the directory does not
already exist, so a stray `d /var/home/kid/.config` running first would leave a
root-owned home with no skel. It does not happen: systemd-tmpfiles collects
every entry and processes them **by path**, parents before children. Verified
with `systemd-tmpfiles --create --root=` over just those two files —
`/var/home/kid` comes out `kid:kid` with `.bashrc` from skel, and only then are
`.config/` and `.config/gcompris/` created.

---

## 4. The shelf

Full table with EYFS/KS1 mapping, star ratings, voice coverage and the
rejections: `system_files/usr/share/kidnix/gcompris/CURATION.md`. In brief:

| Group | Activities |
|---|---|
| **Point and click** | `erase` · `erase_clic` · `clickgame` |
| **Letters and sounds** | `click_on_letter` · `memory-case-association` · `gletters` |
| **Counting** | `learn_digits` · `learn_quantities` · `smallnumbers` · `enumerate` |
| **Numbers in order, and adding** | `adjacent_numbers` · `learn_additions` |
| **Look, listen and remember** | `colors` · `memory` · `memory-sound` |
| **Shapes, time and patterns** | `baby_tangram` · `clockgame` · `frieze` |

The choices that are arguments rather than lookups:

- **`smallnumbers` for subitising.** The 2021 EYFS reform dropped Shape/Space/Measure
  and *added* "subitise up to 5" — a target `05` §2c notes almost no consumer app
  addresses. `smallnumbers` shows plain dice pips, which is also the right side
  of Kaminski & Sloutsky's perceptual-richness finding: countable cartoons make
  children count the cartoons.
- **`learn_digits` / `learn_quantities` / `learn_additions`** are recent GCompris
  additions built for exactly this band, and they run the Number ELG in both
  directions (digit → quantity and back) before touching addition.
- **`clockgame`** because Matt asked for clocks and because KS1 Y1 Measurement
  asks for "tell the time to the hour and half past the hour". Levels 1–2 are
  whole hours.
- **`gletters` is the keyboard activity**, and it is key *location* only — which
  is what `05` §3 asks for. No home row, no WPM, no posture. `baby_wordprocessor`
  was rejected: a free-text editor with no purpose and no audience, when purpose
  and audience are the EEF's named motivational mechanism.
- **`letter-in-word` was the hardest cut.** It is a good activity. It shows whole
  words off a word list with no phonics-phase control, and `05` §2a is
  unambiguous that showing a child a GPC they may not have been taught actively
  undermines the school's programme.
- **`left_right_click`, `penalty`, `erase_2clic` rejected on a shell rule, not on
  taste.** kidnix makes every mouse button do the same thing and never requires
  a double-click (`01` #4–#5, dconf-locked). Shipping an activity that trains
  the opposite would contradict the OS the child is holding.
- **Drawing, music and block coding are all rejected** because kidnix ships
  something better for each: Tux Paint, a first-party pentatonic music activity,
  and TurboWarp. `frieze` survives as the one on-screen pattern/sequence
  activity because it is 1★ and needs no reading.

### 4.1 The phonics honesty problem

`click_on_letter`'s own stated goal is "Recognize the **name** of lowercase
letters". Reception teaches the *sound* first. This is a real deviation from the
UK progression and the activity is on the shelf anyway — letter-name knowledge
is still one of the better single predictors of later reading, and nothing else
in the suite does the job. **The consequence is copy, not code:** the
parent-facing description must say "letter names", never "phonics", and kidnix
must not claim GCompris teaches reading. Recorded in CURATION.md so it cannot
quietly become a marketing line.

### 4.2 Voice coverage is not complete, and the shell has to cover it

The en_GB bundle (`voices-en_GB-2026-07-28`) has a spoken introduction for
**12 of the 18**. The six without are `memory-case-association`,
`learn_digits`, `learn_quantities`, `learn_additions`, `adjacent_numbers` and
`frieze` — mostly the newer activities, which the voice recordings have not
caught up with. In-*play* audio is unaffected: the letter recordings
(`alphabet/U0061.ogg`…) and number recordings those activities use are all
present, and that is what they actually speak.

Each row in `curated.toml` carries `intro_voice_en_GB`, and both the build stage
and the image test verify the claim against the bundle's own name table (which
is UTF-16BE inside the `.rcc`, hence a decode rather than a grep). For the six
that are false, the shell's own `audio_label` is the only thing a pre-reader
hears before starting — so those labels have to carry the whole instruction, not
just the name. That is a handover to the shell/TTS work, not something this
spike can fix.

---

## 5. What is verified, and by what

`build_files/55-gcompris.sh`, at image build time:

1. the overlay files and the tmpfiles fragment are present
2. `gcompris-qt --list-activities` returns ≥ 150 activities (it returns 198)
3. `curated.toml` parses, is 12–20 activities, no duplicate ids, every declared
   group populated, every required key present
4. **every curated id is in `--list-activities`** — the `--launch`-fails-open guard
5. every difficulty is 1 or 2; every `exec` is `gcompris-qt --launch <own id>`
   and passes `--hide-home-button`
6. `[Favorite]` in the config equals the shelf exactly
7. twelve `[%General]` values are what they should be
8. **the shipped config is seeded into a scratch `XDG_CONFIG_HOME` and GCompris
   is made to prove it read it** — activity titles come back with "analogue
   clock", which can only have come from `locale=en_GB.UTF-8` under a group
   name QSettings resolved
9. the seven settings that survive a real run come back unchanged, and
   `[Favorite]` is not dropped
10. the en_GB bundle carries `alphabet/`, `colors/`, `misc/`, `intro/`,
    `words/`, a recording for every lowercase `a`–`z`, and an introduction for
    exactly the activities that claim one

`tests/image/test_gcompris.sh`, against the built image — **46 assertions**
covering all of the above plus: no literal `[General]` group anywhere; the old
`activities/gcompris-qt.conf.default` resolves to the curated file; nothing on
the shelf needs a right-click, double-click or scroll wheel; no uppercase-first
letter activity and no uncontrolled word list; no drawing activity; pointer
skills, letters, number and time are all represented; the tmpfiles fragment
seeds the right path with `C` and not `C+`; `GENERATION` is an integer and
matches `curated.toml`; systemd-tmpfiles parses every shipped fragment; and
`/var` carries no GCompris content.

The seeding was then exercised end to end inside the built image, because
nothing else proves the tmpfiles fragment actually produces a file GCompris can
read. `systemd-tmpfiles --create --root=` over the image's own fragments:

- writes `~kid/.config/gcompris/gcompris-qt.conf` (6,504 bytes, `kid:kid`, 0600)
  and `.kidnix-generation` (`1`);
- leaves `/var/home/kid` `kid`-owned with `/etc/skel` copied in — the ordering
  question in §3.1, settled on the real image rather than a mock;
- and GCompris, pointed at that seeded home, returns "analogue clock" from
  `--export-activities-as-sql`, which can only have come from
  `locale=en_GB.UTF-8` parsed out of the group QSettings resolved. All 18
  favourites are still in the file afterwards.

Running tmpfiles a second time with a hand-added line in the file leaves that
line alone, which is the `C` contract the upgrade story in §3 depends on.

`just tag=gcompris test-boot` passes everything about the session coming up,
which shows the fragment does not break boot. It does **not** show a logged-in
child got a usable file: the boot test does not log in as `kid` and inspect
`~/.config`, so the paragraph above is a `--root` simulation, not a real login.

---

## 6. What this does not do

- **No parent control over the shelf.** `05` §3 says "hide the rest behind a
  parent control"; today the rest is hidden, full stop. A parent who wants
  `letter-in-word` back has no way to ask. The shelf is a file, so the mechanism
  is obvious (parent panel edits `~kid/.config/kidnix/gcompris-extra.toml`,
  shell unions it) — it just is not built.
- **No per-activity option pinning.** `loadActivityConfiguration()` would let us
  fix, say, which letters `click_on_letter` draws from, or lock `clockgame` to
  whole hours. Not attempted; the key names are per-activity and undocumented,
  and guessing them would ship silent no-ops.
- **The shell is not wired to this.** `curated.toml` is written for the shell to
  read and nothing reads it yet. Until it does, GCompris is still one tile
  running the menu.

---

## 7. Open questions

1. **Should the shelf be per-age-band?** It is one list for 4–6. A 4-year-old
   still learning to click and a 6-year-old doing number bonds get the same 18
   tiles, with the difference absorbed by each activity's own level ladder. Two
   candidate fixes — a parent-set band that swaps the list, or the shell fading
   tiles the child never opens — and no evidence either way. This is a child-test
   question (`docs/plan/CHILD-TEST-PROTOCOL.md`), not a literature one.
2. **Does the upgrade path need the re-seed unit before v0.1 ships?** It matters
   the first time the shelf changes and not before. §3 has the sketch.
3. **Is 18 too many?** `05` §3 says 12–20 and this sits near the top. If the
   shell shows six groups of three, a child scanning for one thing has 18
   choices. Worth watching in a child test; the cheapest cut is the second half
   of Counting.
4. **`click_on_letter` teaches letter names, not phonemes** (§4.1). Should it be
   on the shelf at all? Kept, with the copy constraint recorded. A Reception
   teacher's opinion would settle this faster than any amount of reading.
5. **Nobody has watched a child use any of these.** Every claim about difficulty
   is GCompris' own star rating, which is one project's judgement and has no
   published validation.
