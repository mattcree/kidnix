# Pre-rendered speech: Kokoro's voice, none of Kokoro's cost

**Status:** implemented and measured. `build_files/66-prerender-speech.sh`,
`tools/prerender/`, `shell/kidnix_shell/prerendered.py`, a five-line hook in
`shell/kidnix_shell/speech.py`, `tests/image/test_prerender.sh`,
`shell/tests/test_prerendered.py`, `shell/tests/test_prerender_vocabulary.py`,
and four new assertions in `tests/boot/bcvk_boot_test.py`.

This is `docs/spikes/tts-kokoro.md` §7.1 built. **Read that document first** —
this one assumes its numbers, its licence table and its verdict, and only
records what changed on the way from a sketch to a shipped stage.

The one-line summary: **the shell's 351 fixed strings are rendered once at
image build time with Kokoro `bf_emma` and ship as 4.3 MB of Ogg/Opus. The
image gains no onnxruntime, no numpy and no 325 MB graph, the runtime cost is a
`playbin` on a 14 kB file, and every string that is *not* in the catalogue goes
to Piper exactly as it does today.**

---

## 1. What it costs, measured

All of these are from the real build of `localhost/kidnix:prerender` unless a
row says otherwise.

| | |
|---|---|
| Clips **in the built image** | **351** |
| Speech in them | **871 s** (14 min 31 s), mean 2.48 s per clip |
| On disk | **4.67 MB** — 4.63 MB of Ogg + 39 kB index (`du -sh`: 5.3 M) |
| Image delta | **+4.7 MB**, against §5.4's ~12 MB budget for WAV |
| Runtime memory | **0** — no model, no server, no onnxruntime |
| **Render time, in the real build** (32-core host, 4 workers × 8 threads) | **94 s** |
| Render time, **4 pinned cores**, 4 workers × 1 thread, 314 clips | **175 s** |
| Render time, 4 pinned cores, 2 workers × 2 threads, 314 clips | 188 s |
| Peak RSS while rendering | **1.44 GB** (4 workers, arena off) |
| Build-time download | 325.5 MB model + 0.5 MB voice + 2.3 kB vocab + 39.9 MB wheels |
| Whole image | 7.8 GB |

**175 s on four pinned cores is the number that matters**, because a CI runner
is not a 32-core desktop. The constraint was ≤ 5 min and that is **58 % of
it**; scaled for the 351 clips the image actually holds it is ~196 s, still
**65 %**. The pool is sized from `nproc`, which respects a container's CPU
quota, so a 2-core runner spawns two workers rather than four.

Both threading shapes were measured because the answer is not obvious —
onnxruntime's intra-op scaling on a graph this small is poor, and one process
per core beats two processes of two threads by 7 %. `--jobs`/`--threads` are
flags and `KIDNIX_PRERENDER_JOBS` overrides the default.

### Why Ogg/Opus and not WAV

24 kHz 16-bit mono is 48 kB per second of speech, so 871 s of it is **42 MB of
WAV** — over the 20 MB ceiling twice over. Opus at 48 kbps is 4.63 MB, a **9×**
saving, and needs no new package at either end: GStreamer's `opusenc` is
already in the image because `oggdemux ! opusdec` is what `playbin` uses to
play the clips back, and `playbin` is already there for the five earcons.

48 kbps mono is well past transparent for 24 kHz speech. It was chosen over a
tighter 24 kbps because the budget is 20 MB and we are spending under a
quarter of it; there was no reason to trade audible headroom for 2 MB nobody
needs.

---

## 2. What is in the catalogue, and how it is decided

The list is **derived, never maintained**. `docs/spikes/tts-kokoro.md` §7.1
asked for that explicitly and §8 item 6 named the risk it guards against ("148
speech call sites exist in `shell/`; how many pass a literal versus a formatted
string was not counted"). It is now counted, three ways, by
`tools/prerender/vocabulary.py`:

| Source | Strings (checkout) | What it is |
|---|---|---|
| **catalogue** | 249 | Every `_()` / `N_()` / `NP_()` / `ngettext()` literal in every first-party Python package, found by an `ast` walk over the source |
| **manifests** | 41 | `name`, `audio_label`, `shelf_group_name`, `shelf_group_audio_label` out of `/usr/share/kidnix/activities/*.toml` and GCompris' `curated.toml` |
| **numbers** | 21 | `0`–`20` as digits |
| **resting** | 14 | `"… Back {day}."` × the shell's own seven `WEEKDAY_WORDS`, both templates |
| **next_after** | 8 | `"Ready to {phrase}?"` × the shell's own eight destinations |
| | **333** | after de-duplication, in the checkout |

The **built image** yields **351**, not 333, because it holds every activity
manifest that is actually installed — the checkout numbers above are what the
repository alone can see.

### Which packages get walked, and how they are discovered

Not a list. `60-shell.sh` and `64-first-party-activities.sh` both write a
`.dist-info` with `INSTALLER = kidnix-image-build` and a `top_level.txt`, so
every first-party Python package announces itself and **a new first-party
activity is picked up with no edit to the build stage**. That is load-bearing:
an activity whose labels are missing from the catalogue is one tile that
changes voice, and nobody would notice.

`kidnix_parent_panel` is the one deliberate exclusion. It is a libadwaita app
in the *parent's* GNOME session (ADR-0005); it never speaks to the child, its
accessibility story is Orca's, and rendering its strings would spend image size
on audio nothing plays.

### The `.pot` is read from a checkout, and is not the source of truth

The brief pointed at `shell/po/kidnix.pot` as "the msgid catalogue = the closed
vocabulary". It is **not** used by the build stage, for two reasons, and the
second is the interesting one:

1. It is not installed into the image. `60-shell.sh` compiles `po/*.po` into
   `/usr/share/locale/*/LC_MESSAGES/kidnix.mo` and then deletes `/tmp/shell`;
   there is no `.pot` left to read by the time stage 66 runs.
2. **It was measurably a stale subset.** Twelve `N_`-marked literals in
   `resting.py` — including the entire `WEEKDAY_WORDS` table — are in the
   source and not in the `.pot`. A snapshot goes stale on the first commit
   nobody thinks about; an AST walk cannot.

Checked in both directions on 2026-08-23: the AST walk over `kidnix_shell` +
`kidnix_activity` alone was missing 18 strings the `.pot` had, and **every one
of them belonged to the `sounds_and_words` activity** — a separate installed
package. That is what turned "walk the shell" into "walk every first-party
package", and once that was done the walk became a strict superset of the
`.pot` with nothing left over. `--pot` survives as a flag for anyone running
`tools/prerender` from a checkout; the union is free and can only help.

### The `{placeholder}` rule, and its two deliberate exceptions

**Anything with a `{` in it is skipped and left to Piper.** 32 strings are, and
every one is listed in the build log with its reason. That is the constraint as
written, and it is right in general: a template's fillings are open, and a clip
for a sentence nobody can utter is dead weight.

Two templates are expanded anyway, because their fillings are **closed sets
defined in the shell's own module-level constants** and both are sentences a
child hears constantly:

* `next_after.READY_LINE` over `DEFAULT_NEXT_AFTER` — "Ready to go outside?"
* `resting.RESTING_ON_DAY` / `OUT_OF_HOURS_ON_DAY` over `WEEKDAY_WORDS`

Both are expanded by **importing the module and reading the tuple**, not by a
copy of the values, so a renamed weekday or a new destination cannot leave a
stale clip behind. The `unsure` option is excluded by its own `skips` property:
its `ready_line` is the ungrammatical "Ready to not sure?", a sentence Goodbye
never asks.

### Numbers

The number *words* (`nothing`, `one` … `twenty`, `lots of`) are `N_`-marked in
`words.py` and arrive free with the catalogue. The 21 **digits** are added
separately because `feedback.count_phrase` falls through to `str(count)` above
its "lots of" ceiling, and a number is the thing a five-year-old's ear is least
forgiving about. 21 clips cost ~65 kB.

---

## 3. English only, and why that is the right answer

**Only `en_GB` is rendered.** Kokoro v1.0 has no Welsh and no Polish voice at
all — its 54 voices are American, British, and a handful of others, none of
them `cy` or `pl`. Rendering a Welsh msgstr with a British English voice would
mispronounce exactly the letters ADR-0012 and `docs/design/i18n.md` §3 exist to
get right, which is worse than the current behaviour rather than better.

So the catalogue is per-language on disk (`/usr/share/kidnix/speech/<lang>/`),
`PrerenderedVoice` keys its lookup on the **current** speech language, and a
Welsh or Polish profile finds no index and behaves precisely as it does today.
`tests/image/test_prerender.sh` asserts that no `cy/` or `pl/` directory
appears.

---

## 4. The three things that make a clip *not* play

Every one of these is a fallback to the behaviour that existed before this
stage, so the failure mode of the whole subsystem is **inaudible rather than
silent**. That is the property that makes it safe, and it is also exactly why
it needed a boot-test counter (§6).

1. **The text is not an exact match.** No case folding, no punctuation
   stripping, no normalisation. "You drew two pictures today." is a composite
   and goes to Piper. This is the one place a session changes timbre.
2. **The language has no catalogue** (§3).
3. **The rate is not the one the clips were rendered at.** This one is new
   thinking, and it is the most important design decision in the module.

### The rate gate

`[access] speech_rate` is a whole number −100…100 that a **parent sets for
their child**, and calm mode is a *floor* on it (`CALM_SPEECH_RATE = -35`,
applied as `min()` so it can only ever slow the voice further). A recording has
one tempo and cannot follow either.

The index therefore records the `speechd_rate` it was rendered for (`-20`, the
shipped default, which `kidnix-piper.conf` turns into piper's `length_scale
1.100` and Kokoro's `speed = 1/1.10 = 0.9091` — so a clip and a synthesised
sentence are paced identically and a mid-session fallback is a change of timbre
and *not* of tempo). `PrerenderedVoice.set_rate` switches the **whole
catalogue off** the moment the live rate differs.

A parent who slowed the voice down for their child gets the slower voice, not
the prettier one. The accessibility setting wins. GStreamer could have played
the clip at a rate with `scaletempo`, and that was rejected: pitch-preserving
time-stretch on a 0.75 s label is an artefact generator, and "the good voice,
slightly wrong" is a worse answer than "the ordinary voice, exactly right".

---

## 5. Licensing: cleaner than the Piper path, not dirtier

`docs/spikes/tts-kokoro.md` §4 established this and it survived contact with
the build. Recorded in `docs/LICENSES.md` §6a, in
`/usr/share/kidnix/speech/ATTRIBUTION`, and asserted in
`tests/image/test_prerender.sh` §5.

* **Kokoro-82M weights and all 54 voices: Apache-2.0**, no attribution owed.
  Better than the Piper table, where the *default* voice owes CC-BY-4.0.
* **Two credits are owed** for the v1.0 training set and are carried: Koniwa
  (`tnc`) CC BY 3.0 and SIWIS CC BY 4.0.
* **The provenance caveat is recorded, not silenced.** The model card says
  v1.0's training data includes "synthetic audio generated by closed TTS models
  from large providers". That does not touch the Apache-2.0 grant, and the
  contract question is a claim against hexgrad rather than against us — but a
  project that writes down where every asset came from writes this down too.
* **No GPL binary is redistributed and none is linked.** `kokoro-onnx` is not
  installed, so neither is `phonemizer` (GPL-3.0-or-later) or `espeakng-loader`
  (no licence metadata, ships a prebuilt `libespeak-ng.so`). Phonemes come from
  **Fedora's own** `espeak-ng(1)` as a subprocess — the arm's-length call
  ADR-0008's fallback voice already makes. §4.2 of the Kokoro spike verified
  the two phonemisations agree on eleven real shell strings, 11/11.

### Two manifest rows, not 351

The clips are **build output**: kidnix generated them from its own UI strings,
the way `kidnix_shell/sound.py` generates the five earcons. What is
third-party is the *model*, and that is one fact about the tree rather than 351
identical ones. So `THIRD-PARTY.tsv` records the `ATTRIBUTION` that covers the
directory and the `index.json` — the same shape as the GCompris letter-name
clips' own `ATTRIBUTION` — and `/usr/share/kidnix/speech` is deliberately
**not** added to `test_licenses.sh`'s `VENDORED_TREES`. That is a judgement
call and it is written here so it can be argued with;
`tests/image/test_prerender.sh` §5 is what keeps the obligations honest
instead.

---

## 6. How it is proved, given that every failure is inaudible

This is the same trap `docs/spikes/tts.md` §8 fell into for a day — the image
shipped with speech-dispatcher's rate multiplied by 0.01 and the only symptom
was that a five-year-old was read to at adult pace. A catalogue that does
nothing is *quiet about it*: every miss falls through to Piper and the child is
still read to.

So success is made observable on purpose:

* `kidnix_shell/prerendered.py` logs **`played clip: <sha1>.ogg`** at INFO, one
  line per clip. It carries the file name and never the text — the journal
  already gets `speaking: …` from `speech.py`.
* `tests/boot/bcvk_boot_test.py` greps `kidnix-shell.service`'s journal for it
  and asserts four things: the image ships ≥ 200 clips, at least one played,
  **`"Who's here?"` played from its own named file** (it is S1's `intro`, said
  at the top of every session before anybody touches anything), and
  `onnxruntime` is *not* importable in the runtime image.
* `tests/image/test_prerender.sh` checks the other half of the bargain: the
  index matches the disk both ways, every filename really is `sha1(text)`, no
  clip is a template, `python3 -c "import onnxruntime"` fails, no `.onnx` over
  200 MB survived, `python3-pip` is still absent, and the shipped
  `kidnix_shell.prerendered` can load the shipped catalogue.

**What none of it proves** is that a clip reaches a speaker. There is no audio
device in a container, and the boot VM is deliberately run without one — so
`played clip` proves the lookup hit and playback was *started*, not that a
human would have heard it. That gap is the same one `assert_read_aloud` has
lived with since the TTS spike (`spd-say` returns 0 whether Piper or espeak-ng
spoke), and it is closed only by a person listening to
`output/tts-samples/prerender-bf_emma/`.

---

## 7. Build mechanics worth knowing

* **Wheels by `curl`, not `pip`.** A wheel is a zip. `pip install` would need
  `python3-pip` in the image — the thing `65-tts.sh`'s header explicitly does
  not want in a child's OS — plus a `dnf remove` that can cascade, and it would
  give us no checksum to pin. Two `curl`s and a `zipfile.extractall` give both.
  onnxruntime 1.29.0 and numpy 2.5.2 cp314 wheels are sha256-pinned per
  architecture.
* **Everything lives in one `mktemp -d`** under `/var/tmp` with an `EXIT` trap.
  The model, both wheels and every intermediate WAV go with it, inside the same
  `RUN` layer, so nothing can survive to be committed. The stage then *checks*:
  it fails the build if `onnxruntime` or `numpy` is importable afterwards.
* **The HF Apache-2.0 artefacts, not the GitHub release assets.** The Kokoro
  spike verified `onnx-community`'s per-voice `.bin` is byte-for-byte the same
  array as the corresponding entry in `kokoro-onnx`'s `voices-v1.0.bin`, so
  preferring the copy with an explicit licence costs nothing. That export
  carries no `kokoro_config` metadata, so the 114-entry vocabulary comes
  separately from `hexgrad/Kokoro-82M/config.json` (sha256 pinned here for the
  first time: `5abb01e2…9b43c17f`).
* **`KIDNIX_PRERENDER_VOICE`** switches voice with no patch. `bf_emma` and
  `bm_george` are sha256-pinned; any other voice is fetched and **loudly
  reported as unpinned**, because that is a developer trying something, not
  something a shipped build may do silently.
* **The renderer refuses rather than truncates.** A string past the model's
  510-row style table is recorded as skipped and left to Piper. Any *other*
  failure fails the build: a partial catalogue is a session that changes voice
  at random.

---

## 8. What is NOT verified

1. **How it sounds.** Unchanged from `docs/spikes/tts-kokoro.md` §8 item 1, and
   still the only question that matters. `output/tts-samples/prerender-bf_emma/`
   has three clips chosen to make the decision answerable, including the
   one-word case Kokoro is documented to be worst at.
2. **That a clip is audible.** §6. No audio device in a container or in the
   boot VM.
3. **ARM.** The aarch64 wheels are pinned so a build is reviewable, but Kokoro
   has still never been built or run on ARM.
4. **Long-session behaviour of `ClipPlayer`.** One reused `playbin`, rewound
   per clip. A session is thousands of utterances and nobody has run one.
5. **`speak_then`'s gap is still estimated, not measured.** The index records
   each clip's real duration in `ms`, and `speak_then` still spaces its two
   sentences with `_highlight_ms()`'s 70-ms-per-character guess — because that
   same function drives the highlight ring, and the brief was explicit that the
   ring, the captions and `last_utterance` stay untouched. Using the real
   duration when a clip is available would be a small, contained improvement
   and is deliberately not in this change.
6. **Whether 351 is the right 351.** The enumeration is derived and tested, but
   "does the shell speak a literal this walk cannot see" is answered only by
   the `test_access.py` AST guard that already exists for `speak(` call sites,
   not by anything here.
7. **The grown-up sheet's prose.** Some of the 351 are long adult-facing
   sentences on the grown-up sheet that a child never hears. They cost ~1 MB of
   the 4.67 MB. Trimming them is a possible future saving and was not done,
   because "everything the shell can say" is a rule that needs no maintenance
   and "everything a child hears" is a judgement that does.

---

## 9. Undoing it

One deletion: `build_files/66-prerender-speech.sh`. Nothing else in the image
depends on the catalogue — `prerendered.py` finds no index, `select_prerendered`
returns `None`, the hook in `speech.py` is a `is not None` that is false, and
the shell speaks exactly as it did before. That is the same property that makes
a missing clip safe at runtime, applied to the whole stage.
