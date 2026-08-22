# The GCompris shelf: 18 of 198

GCompris ships 198 activities for ages 2–10. kidnix shows a child eighteen of
them, grouped by what the child *does*, and never shows the menu. This file is
the reasoning; `curated.toml` beside it is the machine-readable list the shell
reads, and `gcompris-qt.conf` is the settings file seeded into the kid account.

Everything here was checked against the actual image (`gcompris-qt 26.1-1.fc44`),
not against memory. The method is in `docs/spikes/gcompris-curation.md`.

> "Treat it as a curated shelf, not a whole product. Hand-pick 12–20 activities
> mapped to EYFS/KS1 objectives; hide the rest behind a parent control. Group by
> what the child is *doing*, not by subject. Localise to en-GB and check every
> letter activity against a UK phonics progression before exposing it. Market it
> as 'the ones we picked', never '100 activities!'."
> — `docs/research/05-learning-science.md` §3

## The shelf

Difficulty is GCompris' own 1–6 star rating. Every activity on the shelf is 1★
or 2★, which is roughly the 2–6 age band. "Voice" is whether the 2026-07-28
en_GB bundle contains a spoken introduction for that activity; where it does
not, the shell's own `audio_label` is the only thing a pre-reader hears before
starting, so those rows matter for the TTS work.

### 1. Point and click

The skills every other activity silently assumes. Ordered as a progression:
move, then click, then click something moving.

| Activity | ★ | Voice | What the child does | EYFS / KS1 |
|---|---|---|---|---|
| `erase` | 1 | ✓ | Wipes squares off a hidden photo by moving the pointer over them | EYFS Physical Development, fine motor: pointer control with no target to hit |
| `erase_clic` | 1 | ✓ | Same picture, but each square needs a click | EYFS PD, fine motor: the first deliberate click on a stationary target |
| `clickgame` | 1 | ✓ | Clicks fish swimming across a tank before they leave | EYFS PD, fine motor: clicking a *moving* target — the hardest pointer skill a five-year-old needs (`01-cci-foundations.md` §3) |

### 2. Letters and sounds

**Read the phonics caveat below before adding anything to this group.**

| Activity | ★ | Voice | What the child does | EYFS / KS1 |
|---|---|---|---|---|
| `click_on_letter` | 2 | ✓ | Hears a letter, clicks it among lowercase letters | EYFS Literacy, Word Reading ELG — but letter **names**, not phonemes |
| `memory-case-association` | 2 | ✗ | Turns cards to pair `A` with `a` | EYFS Literacy, Word Reading ELG: case correspondence. Answers the keycaps-are-uppercase-but-phonics-is-lowercase problem named in `05` §2b |
| `gletters` | 2 | ✓ | Types the letter falling down the screen | KS1 Computing, "use technology purposefully". Key **location** only |

### 3. Counting

The EYFS Number ELG is unusually concrete — "deep understanding of numbers to
10, including the composition of each number; subitise up to 5; automatically
recall number bonds up to 5" — and these four hit it almost line by line.
`learn_digits`, `learn_quantities` and `learn_additions` are recent GCompris
additions built specifically for this band.

| Activity | ★ | Voice | What the child does | EYFS / KS1 |
|---|---|---|---|---|
| `learn_digits` | 1 | ✗ | Given a digit, builds that many objects | Number ELG: composition of each number, digit → quantity |
| `learn_quantities` | 1 | ✗ | Given a quantity, produces it | Number ELG, the same objective run backwards |
| `smallnumbers` | 2 | ✓ | Says how many dots are on a falling die | Number ELG: **subitise up to 5** — the 2021 addition almost no consumer app addresses. Plain pips, not cartoon cupcakes (`05` §2c, Kaminski & Sloutsky) |
| `enumerate` | 2 | ✓ | Arranges scattered objects, then counts them | Number ELG: one-to-one correspondence; the child has to *organise* before counting |

### 4. Numbers in order, and adding

| Activity | ★ | Voice | What the child does | EYFS / KS1 |
|---|---|---|---|---|
| `adjacent_numbers` | 1 | ✗ | Fills in a number's missing neighbours | EYFS Numerical Patterns / KS1 Y1 counting forwards and backwards. Linear number ordering is the cheapest well-evidenced early-maths mechanic there is (Siegler & Ramani, `05` §2c) |
| `learn_additions` | 2 | ✗ | Adds two small quantities by combining them | Number ELG: number bonds to 5 and some to 10, by combining visible quantities rather than symbol drill |

### 5. Look, listen and remember

No reading anywhere in this group. `colors` in particular is carried entirely by
the en_GB voice bundle — a child who cannot read a single word can play it.

| Activity | ★ | Voice | What the child does | EYFS / KS1 |
|---|---|---|---|---|
| `colors` | 1 | ✓ | Hears a colour name, clicks that duck | EYFS Communication & Language, listening and attention; colour vocabulary |
| `memory` | 1 | ✓ | Turns picture cards over to find pairs | EYFS Characteristics of Effective Learning: sustained attention, visual working memory. No losing |
| `memory-sound` | 2 | ✓ | Turns cards over to find matching *sounds* | EYFS C&L, auditory discrimination — the precursor to the phonemic awareness the WWC rates Strong Evidence (`05` §2a) |

### 6. Shapes, time and patterns

| Activity | ★ | Voice | What the child does | EYFS / KS1 |
|---|---|---|---|---|
| `baby_tangram` | 1 | ✓ | Drags and rotates shapes into an outline | EYFS Mathematics, shape and space. Dropped from the ELGs in 2021 but retained in the EEF's early maths guidance |
| `clockgame` | 2 | ✓ | Sets the hands on an analogue clock | KS1 Y1 Measurement: "tell the time to the hour and half past the hour and draw the hands on a clock face". Levels 1–2 are whole hours |
| `frieze` | 1 | ✗ | Copies, then completes, a repeating pattern | EYFS Numerical Patterns and KS1 Computing. A repeating sequence is the first algorithm; GCompris' own stated goal for it is "learn algorithms" |

## The phonics caveat, in full

`docs/research/05-learning-science.md` §2a is blunt about this:

> kidnix must not invent its own phonics progression, and must never show a
> child a grapheme–phoneme correspondence they may not have been taught.

GCompris was not built to England's systematic synthetic phonics programmes, and
three specific mismatches survive into the shelf:

1. **`click_on_letter` teaches letter *names*, not phonemes.** GCompris' own goal
   string is "Recognize the name of lowercase letters". Reception teaches the
   *sound* first — /a/ before "ay". This is a genuine deviation and it is on the
   shelf anyway, because letter-name knowledge is still one of the best single
   predictors of later reading and because nothing else in the suite does the
   job. The parent-facing copy must say "letter names", not "phonics".
2. **`gletters` is key location, not phonics.** That is exactly what `05` §3
   asks a keyboard activity to be, so it is fine — but it must never be
   described as teaching reading, and there is no WPM, no streak and no posture
   correction anywhere in it.
3. **Anything that shows whole words is out.** See the rejections below.

Where an activity has both a lowercase and an uppercase variant, kidnix ships
the lowercase one only. `fontCapitalization` is deliberately left at MixedCase
rather than forced to AllLowercase: GCompris renders activity letter data with
the same font as its chrome, so forcing lowercase would break
`memory-case-association`, the one activity whose entire job is the case
mapping.

## What was rejected, and why

Rejections matter more than selections here — 180 activities did not make it,
and these are the ones a future reviewer will be tempted to add back.

| Rejected | ★ | Why not |
|---|---|---|
| `letter-in-word` | 2 | Shows whole words from a word list with no phonics-phase control. `05` §2a: showing a child a GPC they have not been taught actively undermines the school's programme. The single hardest cut on this list |
| `click_on_letter_up` | 2 | Uppercase-first contradicts UK phonics. The lowercase variant is shipped instead |
| `alphabet-sequence`, `ordering_alphabets` | 2 | Alphabetical order is not a Reception objective, and both require decoding first |
| `baby_wordprocessor` | 2 | A free-text editor with no purpose and no audience. `05` §3 and the EEF are explicit that purpose + audience is the motivational mechanism for writing; kidnix's own story-maker and letters-to-family do this properly |
| `left_right_click` | 1 | Teaches right-click. The kidnix shell makes every mouse button do the same thing and locks it in dconf (`01` #4, Hourcade: most 4-year-olds mix left and right clicks). Shipping an activity that trains the opposite would be incoherent |
| `penalty`, `erase_2clic` | 1–2 | Require a double-click. `01` #5: never require a double-click; the shell's dconf sets a 700 ms threshold and nothing in kidnix asks for one |
| `mining` | 1 | Requires a mouse wheel or pinch-zoom, which the target hardware may not have and the shell never uses |
| `simplepaint`, `sketch`, `drawing_wheels`, `clickanddraw`, `drawletters`, `drawnumbers` | 1 | Drawing is Tux Paint's job, and Tux Paint is far better at it (`05` §3 "Draw / paint": big canvas, ≤ 8 tools, caption + voice recorder). `drawletters` is also letter *formation*, which `05` §2a says belongs to a pencil, not a screen |
| `smallnumbers2`, `reversecount` | 2 | Redundant with `smallnumbers`; `reversecount` additionally needs domino reading |
| `target`, `share`, `magic-hat-plus`, `magic-hat-minus` | 2 | Need reading numbers to 15, or division. Year 2 and up |
| `numbers-odd-even`, `comparator`, `money`, `scalesboard` | 2 | Year 2+. `money` also ships a non-GBP coin set by default |
| `vertical_addition`, `vertical_subtraction` | 1 | Column method is Year 3 in England, and teaching it at 5 conflicts with the mastery sequence |
| `melody`, `play_piano`, `play_rhythm`, `piano_composition` | 1–2 | `play_piano` and `piano_composition` require musical notation, which `05` §3 "Music" rules out outright ("**No notation.**"). Music is a first-party activity in kidnix with a pentatonic set so nothing sounds wrong; GCompris' versions would contradict it |
| `maze`, `football`, `hexagon`, `photo_hunter`, `balancebox` | 1–2 | Pure play with no curriculum hook. kidnix already ships SuperTux for play, and shelf space is the scarce resource |
| `tic_tac_toe`, `align4`, `bargame`, `checkers`, `chess` | 1+ | Two-player strategy. Fine games; not what a child alone at a bounded session needs, and the 2-player variants need a second person the design does not assume |
| `path_encoding`, `path_decoding`, `algorithm`, `traffic`, `railroad`, `hanoi` | 1–2 | Computational thinking is TurboWarp's job in kidnix, and `05` §2d finds tangible/unplugged approaches beat on-screen ones (g = 1.03 unplugged, 0.72 physicality vs 0.44 visualisation). `frieze` is kept as the one on-screen pattern activity because it is 1★ and pre-verbal |
| `babymatch`, `geography`, `geo-country`, `chronos`, `family`, `explore_farm_animals` | 1–2 | Content knowledge that assumes cultural references, reading, or both. `babymatch` is 1★ and tempting, but its own prerequisite string is literally "Cultural references" — the pairings it asks for are not a UK five-year-old's |
| `braille_alphabets`, `braille_fun`, `louis-braille` | — | Not applicable, and the activity is a reading-heavy biography |
| everything 3★ and above (98 activities) | 3–6 | Above the band. The config's `filterLevelMax=2` is the backstop |

## Open question: should the shelf be per-age-band?

The current shelf is one list for 4–6. A 4-year-old who cannot click reliably
and a 6-year-old doing number bonds to 10 get the same eighteen tiles, and the
difference is absorbed inside each activity's own level ladder. Two things could
change that — a parent-set band that swaps the list, or the shell hiding tiles
the child has never opened — and neither is decided. See
`docs/spikes/gcompris-curation.md` §6.
