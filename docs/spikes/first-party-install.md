# Getting a first-party activity onto the image

> 2026-08-23. What `build_files/64-first-party-activities.sh` does, why it does
> it that way, and the one question this wave was supposed to close and closed
> in the opposite direction to the one everybody expected: **the a–z recordings
> kidnix already ships are the letters' names, not their sounds.**
>
> Companion to `docs/design/sounds-and-words.md` §13 (the plan) and
> `docs/design/activity-sdk.md` §10 (the contract).

---

## 1. What landed

| | |
|---|---|
| the package | `…/site-packages/sounds_and_words/`, `cp -a` + `compileall --invalidation-mode unchecked-hash`, exactly as `60-shell.sh` installs the shell |
| the corpus | `…/site-packages/sounds_and_words/data/` — the wheel's own layout |
| the command | `/usr/bin/kidnix-sounds-and-words` |
| the tile | `/usr/share/kidnix/activities/sounds-and-words.toml`, `order = 15` |
| the icon | `/usr/share/kidnix/icons/sounds-and-words.svg`, `icon_kind = "path"` |
| the ceiling | `/etc/kidnix/sounds_and_words.toml`, shipped **commented out** |
| the audio | `/usr/share/kidnix/phonemes/en_GB/` — a ledger, and no phonemes |
| the reader | `build_files/lib/rcc.py` + `test_rcc.py`, 15 tests |
| the gate | `tests/image/test_first_party.sh` |

The Containerfile gained one line, `COPY activities/ /tmp/activities/`, beside
the `COPY shell/` that has been there since the shell landed.

## 2. Three things that are not obvious

### 2.1 `cp -a`, again, and for the same reason

`60-shell.sh`'s header has the argument in full: `kidnix-sounds-and-words` has
no PyPI dependencies, its build backend is hatchling, and `pip install` would
mean putting `python3-pip` and `python3-hatchling` into a child's operating
system and taking them out again to produce a tree that is byte-for-byte
`cp -a sounds_and_words $purelib/`. The two files of `.dist-info` that anything
actually reads are written by hand.

### 2.2 The corpus is not where the code looks for it

`sounds_and_words.corpus.data_dir()` resolves `__file__/../../data`. In the
source tree that is `activities/sounds_and_words/data/` and it is right. In
**any installed layout** it is wrong, including a wheel's — `pyproject.toml`
force-includes `data` at `sounds_and_words/data`, so a `pip install` of this
package would look for the corpus in `site-packages/data` and not find it.

That is a bug in the package, and it is not this file's to fix. Its docstring
already names the way out — *"`KIDNIX_SOUNDS_AND_WORDS_DATA` overrides, which is
how the image build and the tests point at a different tree"* — so the image
ships the wheel layout and the generated console script exports that variable
with `setdefault`, which leaves a developer's own override winning. Both halves
are asserted at build and again in `tests/image/test_first_party.sh`.

**Follow-up for whoever owns the activity:** make `data_dir()` try
`Path(__file__).parent / "data"` before the source-tree spelling, and the
environment variable stops being load-bearing.

### 2.3 The icon is a path, and the drawing lives with the activity

The shell's `data/icons/` is the shell's. An activity reaching into it to drop
a file would be the wrong ownership, so `icon.svg` lives in the activity's
package and the build copies it to `/usr/share/kidnix/icons/`. The manifest
names that absolute path with `icon_kind = "path"`, which
`kidnix_shell.widgets.icon_image` loads with `Gtk.Image.new_from_file` —
confirmed by reading, and asserted in the image test.

Why not just name the file in site-packages? Because that path has a Python
version in it, and a manifest that said `/usr/lib/python3.14/…` would break on
the Fedora release that ships 3.15.

### 2.4 The tile is second, and Draw is still first

`order = 15`. `tests/e2e/test_scenario.py` opens *"the first cell of the first
row"* and asserts the shell's launcher log says Tux Paint, so anything sorting
below `order = 10` breaks the e2e scenario. Both the build stage and the image
test now assert `[tuxpaint, sounds-and-words]` are the first two, so that fails
here — in two seconds, in a container — rather than twenty minutes into a VM run.

### 2.5 The parent's ceiling file is shipped with every line commented out

`sounds_and_words.settings.load_parent_ceiling()` reads `/etc/kidnix/` first and
`/usr/share/kidnix/` second, and reports `ParentCeiling.source = None` when
nobody has answered. That `None` is not cosmetic: `ParentCeiling.is_default`
is what lets the parent pane say *"nobody has told us yet, so we are starting at
the beginning"* rather than presenting kidnix's guess back to a parent as their
own statement.

So a `/etc` file that **set** the default would make the activity lie about
where the number came from. The shipped file is therefore a template: prose for
a parent, the whole of Phase 2 and Phase 3 written out so they can find their
child's last sheet, and the three lines that matter commented out at the bottom.
`tomllib` reads it as `{}`, the loader logs one line saying it found no
`[ceiling]` table, and the built-in floor stands — which is true, and is what
the log should say.

Design note §13.4 also asked for a copy at `/usr/share/kidnix/sounds_and_words.toml`.
**Not shipped, deliberately**, for the same reason: it would be read as an
answer. The documented default now lives in the `/etc` template's comments,
which was what §13.4 actually wanted it for.

---

## 3. The phoneme clips: the question, and the answer

`docs/design/sounds-and-words.md` §12.6 says every phoneme a child hears today
is a placeholder, and names one thing standing between that and real audio:

> **The a–z clips exist and are not readable.** GCompris' `voices-en_GB` bundle
> is in the image […] but it is a Qt `.rcc` archive, not loose files. Unpacking
> it once, at build time, into the directory above is a `build_files/` job.

Both halves of that turned out to be true and the conclusion did not.

### 3.1 Reading a `.rcc` without Qt

There is no supported extractor. `rcc` is a compiler; Qt 6 has no `--reverse`
and never had one. `QResource` can read a registered bundle, but that means
running a Qt program. `bsdtar` and `7z` do not know the format.

So `build_files/lib/rcc.py` parses it. The format is small and has been stable
since Qt 5.0 — a header, a flat array of fixed-size tree nodes, a UTF-16BE name
table and a data section, big-endian throughout, with per-file zlib or zstd
flags. It is ~180 lines. `test_rcc.py` beside it contains a *writer* for the
same format, so all fifteen tests are round-trips rather than assertions against
a fixture nobody can regenerate; two more run against the real bundle when it is
on the machine, and the build runs the whole suite before trusting the reader
with a 13 MiB download.

The en_GB bundle turned out to be format version 2, 888 files, none compressed
(they are already Ogg Vorbis):

| directory | files |
|---|---|
| `alphabet/` | 47 |
| `colors/` | 11 |
| `geography/` | 129 |
| `intro/` | 114 |
| `misc/` | 23 |
| `words/` | **564** |

### 3.2 `alphabet/` is the alphabet song

The 47 files in `alphabet/` are `U0061.ogg`…`U007A.ogg` (a–z), `U0030`…`U0039`
(the digits) and `10.ogg`…`20.ogg` (ten to twenty). A directory that mixes
letter *sounds* with number *names* would be incoherent; it is the set
`click_on_letter` and `click_on_number` read character names out of.

That is the structural argument. Three acoustic ones, measured on the extracted
clips, because "listen to it" is not a thing a build can do:

**1. The /iː/ cluster.** In English the names of `b c d e g p t v` all end in
the same vowel. Cosine similarity of each clip's *tail* spectrum against the
core of the `e` clip, sorted:

```
  v 0.9967   d 0.9941   e 0.9935   t 0.9935   b 0.9922   g 0.9922
  h 0.9921   p 0.9903   c 0.9866   a 0.9851   k 0.9839   w 0.9783
  …
  z 0.9494   s 0.9479   f 0.9456   x 0.9365   r 0.9108   l 0.8996
```

Eight of the top nine are exactly the eight /iː/-final letters. Nothing about
the *sounds* /b/ /k/ /d/ /g/ /p/ /t/ /v/ would make them cluster like that.

And the tell that settles it: **`z` is not in the group.** An en_GB speaker says
"zed", not "zee". A phoneme set has no reason to know that; a name set does.

**2. `w` is the only clip with more than one syllable in it.** Energy bursts
above 30 % of peak, per clip: every letter has one, `w` has two — and among the
digits, only `seven` does. "Double-you" has three syllables; /w/ has none.

**3. The fricative letters are vowel-dominated.** Spectral centroid and the
ratio of energy above 4 kHz to energy below 1.2 kHz:

| clip | centroid | high/low |
|---|---|---|
| `s` | 2350 Hz | 0.37 |
| `f` | 2101 Hz | 0.28 |
| `z` | 2156 Hz | 0.34 |
| `m` | 1791 Hz | 0.19 |

A pure /s/ or /f/ is noise centred above 4 kHz with a ratio well over 1. These
are "ess", "ef", "zed", "em" — a vowel with a consonant attached.

### 3.3 So they are not installed as phonemes

A child taught to blend who is played "ess ay tee" for `sat` has been told the
opposite of what their teacher told them. That is **worse** than the `"sss"`
placeholder the activity already speaks, not better.

The 26 clips are installed at `/usr/share/kidnix/phonemes/en_GB/letter-names/`,
CC-BY-SA-4.0, with the attribution that used to travel inside the `.rcc` written
out beside them, and a `sha256` per clip in `phonemes.toml`. They are there so
the claim above can be checked by ear on the machine that makes it, and so
whoever records the real clips has the comparison to hand. `phonemes.py` reads
one directory up and never sees them; the image test greps the installed Python
to prove nothing else does either.

### 3.4 And they are not synthesised

The fallback option was Piper — render `"sss"`, `"mmm"`, `"t"` at build time and
call the result a clip. Four reasons not to, in increasing order of importance:

1. **It buys nothing.** The shell already speaks `"sss"` through Piper, live,
   for exactly that string. A build-time render of the same text through the
   same voice is the same audio in a file.
2. **Nothing could play it.** §12.6: *"there is no clip player in the SDK yet,
   so the first real clip will fail as a missing player rather than as a wrong
   sound."* That is still true.
3. **A TTS engine cannot say an isolated consonant, and this one does not.**
   §9 of the design note states the rule flatly — never synthesise a phoneme —
   and the reason is the schwa: an engine is synthesising an *utterance*, and
   English has no utterance /t/, so what comes out is "tuh" or "tee". Measured,
   inside the image, on the image's own Piper and the voice the shell speaks
   with (`en_GB-cori-medium`), feeding it the corpus's own kidnix-safe labels.
   `voiced` is the span above −24 dB of the clip's own peak; `lo/hi` is energy
   below 1.2 kHz over energy above 4 kHz — a vowel is low, a fricative is high:

   | GPC | label | stretchable | total | voiced | lo/hi |
   |---|---|---|---|---|---|
   | `s` | `sss` | yes | 1.15 s | 0.79 s | **0.59** |
   | `sh` | `shh` | yes | 1.22 s | 0.81 s | 1.28 |
   | `a` | `aaa` | yes | 0.94 s | 0.54 s | 8.32 |
   | `m` | `mmm` | yes | 0.87 s | 0.45 s | 14.82 |
   | `f` | `fff` | yes | 1.06 s | 0.57 s | **5.52** |
   | `t` | `t` | no | 0.69 s | **0.36 s** | 2.43 |
   | `d` | `d` | no | 0.79 s | **0.33 s** | 5.92 |
   | `p` | `p` | no | 0.68 s | **0.29 s** | 5.36 |
   | `k` | `k` | no | 0.78 s | **0.45 s** | 4.82 |

   Read it in two halves. The **stretchable** ones are fine and unsurprising:
   `sss` comes back high-frequency-dominated (0.59) — a real sustained /s/ —
   and `mmm` and `aaa` come back low-frequency because a nasal and a vowel *are*
   low-frequency. (`fff` at 5.52 is the one continuant that does not survive:
   /f/ is a weak fricative and the engine has put something voiced in front of
   it.)

   The **plosives** are the finding. A /t/ is a burst of the order of 10–20 ms.
   Piper returns **290–450 ms of above-threshold energy, low-frequency
   dominated** for every one of `t d p k` — which is not a stop, it is a
   syllable, and the only thing a syllable can be here is the consonant plus a
   vowel. That is the schwa the design note refuses, measured rather than
   assumed. Pre-rendering it into a file makes it neither better nor worse than
   the live fallback; it just makes it look like a recording.
4. **It would break the honesty gate.** `phonemes.missing_recordings()` is the
   list §12.6 says has to reach empty before the audio may stop being called a
   placeholder. A synthesised file dropped into `CLIP_DIR` empties it — and the
   activity would then report `Source.RECORDED` for a sound no person ever made.

So: **no clips, and a ledger that says so.**
`/usr/share/kidnix/phonemes/en_GB/phonemes.toml` is generated at build by
resolving every GPC in the shipped corpus through `phonemes.phoneme_for()`
against that same directory, so it cannot claim a recording that is not on the
disk beside it: 114 rows, 0 recorded, 114 `spelled`. The image test checks the
count both ways — no row may name a missing clip, and no `.ogg` may be missing a
row.

### 3.5 What actually ends this

About twenty recordings: one adult, one morning, one microphone, released
CC-BY-SA-4.0 as kidnix's own asset (research 10 §5, open question 8). The
plumbing is now entirely in place for them — the directory, the ledger, the
licence rows and the resolver all exist and are tested; the day the files land,
`missing_recordings()` shrinks on its own and nothing else has to change except
adding a clip player to the SDK.

### 3.6 One thing found on the way that is worth someone's time

The same bundle holds **564 whole-word en_GB recordings**, and **214 of them are
words in the Letters and Sounds corpus** — `cat`, `sat`, `pin`, `dog`, `bed`,
`ship`, `think`, `spring`… Blend it's push-together arrow says the whole word,
and today it says it with TTS. A real adult voice saying `cat` is a strictly
better answer, needs no new recording session, and is already licensed and in
the image.

It is *not* in this wave: a word clip is not a phoneme clip, it belongs to
`blend.py` rather than `phonemes.py`, and the SDK still has no player. But
`build_files/lib/rcc.py` will hand them over in one call whenever someone wants
them.

---

## 4. What the gate checks

`tests/image/test_first_party.sh`, run by `just test-image first_party`, in the
same shape as `test_activities.sh`: the package imports **as the child** from
`/usr/lib`, the pure half imports without dragging in `gi`, the GTK half imports
at all, the corpus loads from where the console script points, `--help` runs,
the manifest passes the SDK's validator (which is stricter than the shell's),
the tile is second and Draw is first, the icon path opens, the `/etc` template
parses to nothing and leaves the built-in floor standing, the gate refuses `hat`
by name at that floor, the ledger and the clips on disk agree in both
directions, the 26 letter-name clips are real Ogg streams matching their
recorded checksums, the CC-BY-SA notice travelled with them, no code reads them,
the licence rows exist, and nothing from `/tmp/activities` survived the build.

## 5. Open

1. `data_dir()` — §2.2. One line in the activity, and the environment variable
   stops being load-bearing.
2. **A clip player in the SDK.** Nothing can play a `.ogg` today.
3. **The recordings.** §3.5.
4. **The 214 word clips.** §3.6.
5. **`icons-brief.md`** does not yet carry the Sounds & words drawing; the SVG
   is in the activity package with the reasoning in a comment.
