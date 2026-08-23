# Sounds & Words

The kidnix literacy activity. This directory is **weeks 1–4** of the six-week
v1 plan in `docs/plan/SUITE.md` §3 and
`docs/research/10-early-reading-writing-sota.md` §7.1: the corpus, the ceiling,
the acceptance test, the schedule, and three modules of the loop —
**Find it** (B), **Blend it** (C) and **Read it** (E), on the `kidnix_activity`
SDK (`shell/kidnix_activity`). Hear it (A) is week 6 if there is time.

**Importing this package imports no GTK.** The half that carries the guarantee
— which grapheme comes next, what the ceiling is, whether a word is decodable —
is provable headless; the window is in `sounds_and_words/activity.py` and is
imported only by the entry point.

The design lives in `docs/design/sounds-and-words.md`. Read that first — §12 is
what Find it and Blend it do and why, and §16 is Read it.

## What is here

```
data/
  graphemes.toml     114 GPCs + 15 never-taught pseudo-GPCs, in teaching order
  words.toml         846 words from the L&S banks, each with its GPC split
  tricky_words.toml  56 tricky words, gated by GPC order or by phase
  sentences.toml     119 captions/questions/sentences + 5 short texts
  lexicon.toml       200 segmentations for words outside the banks
  read_texts.toml    the 12 authored decodable texts (ours, not L&S)
  parent_text.toml   every word a parent reads
  sources.toml       provenance, page numbers, licence, and what we changed
  schemes/           the L&S ordering, plus stubs for the schemes we don't ship
sounds_and_words/
  corpus.py          loading and indexing
  ceiling.py         the hard gate
  schemes.py         "which programme does his school use?" -> a ceiling
  schedule.py        Leitner boxes, the two-day mastery rule, compose_session
  settings.py        the parent's ceiling (/etc), this child's history (state)
  loop.py            the session: order, <= 12 items, <= 12 minutes, 2 tries
  distractors.py     which three wrong tiles, and why those three
  keys.py            what a key press meant, digraphs included
  blend.py           dots, bars, and the three stages of a word
  phonemes.py        what to *say* for a sound, and where it comes from
  pictures.py        fifteen concrete nouns, drawn here
  reading.py         the 12 books: the shelf, pagination, highlight timing
  summary.py         the two cards the child takes away
  activity.py        the window. Wiring only.
  reader.py          the Read it screens: the shelf and the book
  screenshots.py     --screenshot, under Broadway, never on a desktop
  pictures/*.svg     bag bed bus cat cup dog fox hat jam map net pin pot sun tap
  scenes/*.svg       sandpit truck hill pond farmyard shed box shop fish rain train
  icons/*.svg        push, say, next, back, listen
manifest.toml        the shell's input contract (not installed yet -- see below)
tests/               the Appendix 7 acceptance test and everything else
tools/               the transcription and the generator that writes data/
```

`read_texts.toml`, `parent_text.toml`, `sources.toml` and `schemes/` are
hand-written; everything else in `data/` is generated: `tools/lsdata.py` is the page-by-page
transcription of the L&S tables, `tools/lexicon_data.py` the hand-written
grapheme splits, and `uv run python tools/gen.py` writes the TOML. A test
re-runs the generator and insists the checked-in files match byte for byte.

## The one thing this module is for

> A Reception child whose parent has said *"they've done up to `ck`"* can find a
> grapheme, blend six words and read one four-sentence book, and **never sees a
> grapheme past `ck`**.

`ceiling.py` is the part that makes the last clause true. Everything else is
downstream of it.

## Running it

```sh
just setup             # a venv with --system-site-packages, for gi
just test              # 849 tests, including the Appendix 7 acceptance test
just lint
just validate          # the manifest, through the shell's own parser
```

Never on your own desktop. The window only ever opens on a Broadway display:

```sh
just run               # the activity, on gtk4-broadwayd :108
just test-gtk          # the 79 GTK tests, likewise
just screenshots       # regenerates docs/design/screenshots/saw-*.png
```

`kidnix_activity` and `kidnix_shell` come from the image on a real machine and
from `../../shell` in a checkout — the Justfile puts that on `PYTHONPATH` and
`tests/conftest.py` does the same for the tests. Neither is a dependency in
`pyproject.toml` and neither should become one.

**Not installed yet.** There is no tile: `manifest.toml` is deliberately not in
`system_files/usr/share/kidnix/activities/`, because a tile that opens a
half-built activity is worse than no tile. The install plan is
`docs/design/sounds-and-words.md` §13.

```python
from sounds_and_words import load_corpus, ceiling_for_grapheme, check_text, compose_session
from sounds_and_words.schedule import History

corpus  = load_corpus()
ceiling = ceiling_for_grapheme(corpus, "ck")      # what the parent told us

check_text(corpus, "a tin can", ceiling).allowed        # True
check_text(corpus, "a cat in a hat", ceiling).report()  # rejected: 'hat' needs h ...
check_text(corpus, "the night bus", ceiling).report()   # rejected: 'the' is a tricky word ...

compose_session(corpus, ceiling, History(), day=0)
```

## Rules this module is held to

From `docs/research/10-early-reading-writing-sota.md` §4.6, enforced by tests
where a test can enforce them:

- Never show an untaught GPC in a decodable context. Under-permit rather than
  over-permit; the school decides the next sound.
- No score, level, star, streak, badge or percentile, to child or parent.
- No claim to teach reading. No reading ages. No prediction of the screening
  check.
- No handwriting, letter formation or lead-in strokes — and say so to parents.
- No speech recognition judging a child's reading, ever.
- No adaptivity beyond a Leitner box and a `WHERE` clause.
- **No hotspots, tap-to-animate, mini-games or tap-a-word dictionary in Read
  it.** The clearest negative finding in the literature, and the way it is kept
  is that the sentence is one label with no per-word control under it.

## Licence

Code: Apache-2.0, like the rest of kidnix.

Corpus: **Contains public sector information licensed under the Open Government
Licence v3.0.** © Crown copyright 2007 (Letters and Sounds) and © Crown
copyright (the Reading Framework). See `LICENSES.md` — it carries the exact
attribution the OGL requires, and it is not optional.

Letters and Sounds is **not** on the DfE's validated list of systematic
synthetic phonics programmes. kidnix uses it as a default ordering and an openly
licensed word corpus, and must never describe it as a validated programme.
