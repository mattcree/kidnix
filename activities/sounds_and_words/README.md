# Sounds & Words

The kidnix literacy activity. This directory is **week 1** of the six-week v1
plan in `docs/plan/SUITE.md` §3 and `docs/research/10-early-reading-writing-sota.md`
§7.1: the corpus, the ceiling, the acceptance test and the schedule skeleton.

Data and pure logic. No GTK, no audio, no window. The UI arrives in weeks 2–4
on top of the `kidnix_activity` SDK (`shell/kidnix_activity`).

The design lives in `docs/design/sounds-and-words.md`. Read that first.

## What is here

```
data/
  graphemes.toml     114 GPCs + 15 never-taught pseudo-GPCs, in teaching order
  words.toml         846 words from the L&S banks, each with its GPC split
  tricky_words.toml  56 tricky words, gated by GPC order or by phase
  sentences.toml     119 captions/questions/sentences + 5 short texts
  lexicon.toml       200 segmentations for words outside the banks
  parent_text.toml   every word a parent reads
  sources.toml       provenance, page numbers, licence, and what we changed
  schemes/           the L&S ordering, plus stubs for the schemes we don't ship
sounds_and_words/
  corpus.py          loading and indexing
  ceiling.py         the hard gate
  schemes.py         "which programme does his school use?" -> a ceiling
  schedule.py        Leitner boxes, the two-day mastery rule, compose_session
tests/               the Appendix 7 acceptance test and everything else
tools/               the transcription and the generator that writes data/
```

`data/*.toml` is generated: `tools/lsdata.py` is the page-by-page
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
uv sync
uv run pytest          # 236 tests, including the Appendix 7 acceptance test
uv run ruff check
```

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

## Licence

Code: Apache-2.0, like the rest of kidnix.

Corpus: **Contains public sector information licensed under the Open Government
Licence v3.0.** © Crown copyright 2007 (Letters and Sounds) and © Crown
copyright (the Reading Framework). See `LICENSES.md` — it carries the exact
attribution the OGL requires, and it is not optional.

Letters and Sounds is **not** on the DfE's validated list of systematic
synthetic phonics programmes. kidnix uses it as a default ordering and an openly
licensed word corpus, and must never describe it as a validated programme.
