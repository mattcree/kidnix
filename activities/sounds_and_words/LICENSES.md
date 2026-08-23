# Sounds & Words — licensing ledger

This activity redistributes UK government content. The Open Government Licence
permits that and asks for one thing in return: an attribution statement, in the
form it specifies. This file is that statement, and the same wording appears at
the top of every generated TOML file under `data/`.

The repository-wide ledger is `docs/LICENSES.md`; this file is the detail for
this activity and must be summarised there when the activity ships in the image.

---

## The attribution, in the form the OGL requires

> Contains public sector information licensed under the Open Government Licence
> v3.0.
> <https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/>

Applies to everything derived from the two Crown-copyright documents below.

---

## 1. Letters and Sounds (2007)

| | |
|---|---|
| **Title** | Letters and Sounds: Principles and Practice of High Quality Phonics |
| **Reference** | DFES-00281-2007 |
| **Publisher** | Department for Education and Skills / Primary National Strategy |
| **Year** | 2007 |
| **Copyright** | © Crown copyright 2007 |
| **Licence** | **Open Government Licence v3.0** |
| **Licence text** | <https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/> |
| **PDF** | <https://assets.publishing.service.gov.uk/media/5a7aa7b6e5274a34770e630c/Letters_and_Sounds_-_DFES-00281-2007.pdf> |
| **Landing page** | <https://www.gov.uk/government/publications/letters-and-sounds> |
| **Retrieved** | 2026-08-23 |
| **Verified** | yes — gov.uk states OGL v3 for this publication |
| **Redistribution OK?** | **yes, with notice** — the attribution above must travel with the data |

**What we took.** The grapheme–phoneme progression and set order (pp. 50, 76–77);
the word banks (pp. 69–70, 100–103, 126–127, 151–154); the caption, question and
sentence banks (pp. 71, 100–101, 103, 128); the tricky-word lists (pp. 50, 76–77,
114, 132–133); the phase assessment criteria (pp. 197–198); and the footnotes
that make several of those words decodable at all (p. 69, p. 70).

**What we must not say.** Letters and Sounds is **not** on the DfE's validated
list of systematic synthetic phonics programmes. kidnix uses it as a *default
ordering and a licensed word corpus*. Describing it as a validated programme, or
implying kidnix is one, is out of bounds — see `docs/research/10-early-reading-writing-sota.md` §4.2.

**Residual risk, recorded rather than ignored.** L&S credits its word and
high-frequency-word tables (p. 195) to:

> Masterson, J., Stuart, M., Dixon, M. and Lovejoy, S. (2003) *Children's Printed
> Word Database*: Economic and Social Research Council funded project, R00023406.

The tables as published sit inside an OGL document and are redistributed on that
basis. A cautious reading treats the *derived frequency ranking* as third-party;
kidnix ships no frequency data and needs none, because L&S's lists are already
matched to the progression. The credit is carried in `data/sources.toml`.

---

## 2. The Reading Framework (2023)

| | |
|---|---|
| **Title** | The reading framework: teaching the foundations of literacy |
| **Publisher** | Department for Education |
| **Year** | 2023 (this revision, May 2024 asset) |
| **Copyright** | © Crown copyright |
| **Licence** | **Open Government Licence v3.0** |
| **PDF** | <https://assets.publishing.service.gov.uk/media/664f600c05e5fe28788fc437/The_reading_framework_.pdf> |
| **Landing page** | <https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy> |
| **Retrieved** | 2026-08-23 |
| **Verified** | yes |
| **Redistribution OK?** | **yes, with notice** |

**What we took.** Appendix 7, *Decodable texts for pupils beginning to learn to
read* (printed pp. 144–145): the stated GPC set, the three exception words, the
four exemplar books and footnote 158. Transcribed verbatim into
`tests/fixtures/reading_framework_appendix7.toml` and used as this activity's
acceptance test.

---

## 3. National Curriculum English Appendix 1 (Spelling)

| | |
|---|---|
| **Publisher** | Department for Education, 2013 |
| **Licence** | **Open Government Licence v3.0** |
| **PDF** | <https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/239784/English_Appendix_1_-_Spelling.pdf> |
| **Status** | **planned** — cited in `data/sources.toml`, not yet transcribed |

The statutory Year 1 common exception word list is the authoritative superset for
tricky words. The L&S list currently shipped is a subset of it. Adding it needs
no new licence decision.

---

## 4. kidnix's own additions

Everything kidnix added to the Crown-copyright material is marked
`added_by = "kidnix"` in the data and explained in `data/sources.toml`:

- eight doubled-consonant GPCs (`bb dd gg mm nn pp rr tt`) that L&S uses in its
  own word banks without ever introducing;
- one GPC, `or_er` (`or` standing for /ɜː/, as in *word*, *worm*, *work*),
  without which the Reading Framework's own acceptance test cannot distinguish
  *worn* from *worms*;
- fifteen never-taught pseudo-GPCs used only to explain *why* a word is not
  decodable;
- the segmentations in `data/lexicon.toml` for words that appear in L&S captions
  and sentences but in none of its word bank columns.

These are kidnix's, under Apache-2.0, and are separable from the OGL material.

---

## 5. Not yet here, and what it will need

| Asset | Planned licence | Note |
|---|---|---|
| a–z phoneme audio | CC-BY-SA-4.0 (GCompris `voices-en_GB`, already in the image) | covers every single-letter grapheme |
| ~20 digraph/trigraph recordings | ours, CC-BY-SA-4.0 | **must be recorded**; never synthesise a phoneme — TTS adds a schwa, which is the classic phonics error |
| narration for sentences and books | Piper `en_GB-cori-high`, public domain | already pinned in `docs/LICENSES.md`; fine for sentences, **not** for isolated phonemes |
| picture prompts | Mulberry Symbols, CC BY-SA 4.0 | UK-made AAC set |
| ~12 authored decodable texts | ours, Apache-2.0 | built from the OGL word banks; no CC-licensed UK-progression decodable set exists |
| Andika 7.000 | SIL OFL 1.1 | use the SIL release, **not** the Google Fonts subset |

Each of these needs a row here and in `docs/LICENSES.md` **in the same commit as
the download**, per AGENTS.md §5.
