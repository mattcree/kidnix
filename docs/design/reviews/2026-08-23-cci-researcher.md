# Expert review — child–computer interaction

> Senior CCI researcher (IDC tradition; co-design and evaluation with 4–7s).
> Read against AGENTS.md §3, SYNTHESIS, the spec + §7a/7b/7c, impl-notes
> §16–20, the audit, gap sweep 09, 01 §3, CHILD-TEST-PROTOCOL, the screenshots
> and the source; shell also run here at `--demo --screen 1280x800@102`.

## 1. Verdict

This is the most carefully-reasoned child-facing shell I have read the source
of, and it is not yet child–computer interaction *research* — it is an
unusually good design rationale with zero children in it. The reading in
`09-gap-sweep` §1 and §3 beats most IDC related-work sections I referee: it
separates known from extrapolated, it correctly identifies that the
working-memory justification for "≤5 choices" was mis-derived for a visible
labelled grid, and it correctly concludes that the antecedent cue is not the
active ingredient in a transition. The build then does the opposite of what
that implies, and that gap — an evidence base saying *the destination matters*
against a product whose best-engineered object is *the signal* — is the theme
of this review. Second theme: the shell is excellent and the *system* is not.
The child's choices are made from tiles wearing vendor logos, launching
upstream programs whose tool density, target sizes and modal dialogues you do
not control and have mostly not measured. Fix the icons, make the ending's
choices real, build the Goodbye, and correct the evaluation plan before it
burns the one child you have.

## 2. Five genuine strengths

1. **The honesty is structural.** `grownup.py:30` tells the parent "No number
   here is evidence-based; 25 is the precaution." `gcompris.toml`'s `goal` says
   the shelf is uncurated. `speech.py` states that no child evidence for hover
   read-aloud exists anywhere, which is why every hover utterance is
   instrumented. Nothing else in this market does this, and it is why an
   outsider can audit you at all.
2. **`09-gap-sweep` §3 corrects the constitution against your own interest.**
   Recognising that WM limits bind on *held* option sets, not on a persistent
   labelled grid, then splitting *ceiling* (12, from geometry and visual search)
   from *first-run default* (5–6, from Schneider's inverted-U), is a better
   reading than 01 #12's, and the one I would defend at a PC meeting.
3. **The ending's truthfulness.** Impl-notes §20.3: when the hard stop destroys
   work, S6 says "Time to stop now." instead of "Let's keep that", the keep
   earcon is silent, and Goodbye counts only what was imported. A shell that
   refuses to claim a save it did not make is the most ethically interesting
   thing in the repository.
4. **Physical sizing that finally holds.** `metrics.py` separates floors from
   preferences and lets the *grid* give way (4×3 → 4×2 → 3×2) before the tile
   does. Measured here at 1280×800@102: tiles 42.3 mm, gaps 12.2 mm, band
   buttons 20.4 mm, label floor 18 pt. Almost nobody builds a real
   physical-layout system; you did.
5. **The icons you drew yourselves.** The next-after tiles (apple, bath, pan,
   blocks, tree) are textbook depictive icons for a pre-reader — concrete,
   single-referent, high-contrast line art. Proof you know exactly what a
   5-year-old's icon should look like.

## 3. Ranked concerns

### C1 — BLOCKER: the activity tiles are vendor logos, not depictive icons

**Evidence.** Every shipped manifest sets `icon_kind = "icon-name"`:
`tuxpaint` → a penguin, `klettres` → a flag, `gcompris` → a brand swirl,
`blinken` → a colour wheel. See `e2e-contact-sheet.png` panel 3. The audit
marks "08 3.7a Representational icons — **MET**" (audit:232) but measures the
shell's own 17 chrome SVGs, not the tiles the child chooses from. Worse (forum
#37): `widgets.icon_image()` falls back to `category_icon(category)` when the
theme lacks a name, collapsing every "make" tile to one identical pencil and
every "learn" tile to one book — visible in `demo-home-1280.png`. 01 #14 is
explicit: depictive, not conventional. For a pre-reader the label is decoration
and the audio is transient, so the icon is the *only persistent* channel; a
penguin does not mean "draw", and three identical pencils teach the child that
the picture carries no information.

**Recommendation.** Draw ten depictive activity icons in your next-after style,
showing the **output or the action** rather than the tool (a finished scribble
for Draw; a face for Potato faces), set `icon_kind = "path"`, and make
`--validate-manifests` fail when two visible tiles resolve to the same image.
A day's work, and the highest-leverage child-facing change you have.

### C2 — MAJOR: the effort went into the signal you concluded was inert

**Evidence.** `09 §1` states the finding (four JABA component analyses: the
antecedent cue alone is ineffective; Castillo 2018: the aversive event is the
drop in reinforcement density at the *destination*) and writes the design
implication itself — "the Goodbye screen must be the highest-reward moment of
the session". What shipped is an elaborate Cairo sun with shrink-and-sink
geometry, tap-to-speak, phase earcons, warm colouring and a whole A/B protocol
— versus a Goodbye of one headline, up to three 35 mm thumbnails and two
buttons (`demo-goodbye-choice.png`; forum #24 has the layout numbers). E1's
specific descriptive feedback ("you used five colours") exists in SYNTHESIS and
nowhere in the code.

**One caution on the reading, since you asked.** All four JABA studies are
children referred for problem behaviour or with developmental disabilities, and
"ineffective" there means "did not reduce problem behaviour below baseline in a
component analysis" — which does not license SYNTHESIS D3's compressed claim
that advance notice is "inert" for a typically-developing child's *felt*
experience of a transition. Keep the conclusion; note the population.

**Recommendation.** Give S7 the weight the sun got — the day's making shown
large and named, the pre-chosen destination as the biggest thing on screen and
spoken last as its own utterance, "Show a grown-up" as the primary action. Do
it *before* P1, or P1 measures the half you concluded does not matter.

### C3 — MAJOR: the T−6 ending offer is a choice with no consequence

**Evidence.** `app.py:1359–1380`: both answers do the same thing to the
machine; inside an activity the transition is explicitly a no-op; put-away
lands at T−2 either way. `session.answer_offer()` only latches that the
question was asked. Spec §6 says the ending "rounds to a natural boundary" — it
does not. SYNTHESIS E3 requires choices to be contingent and consequential;
01 #38 forbids nudges. A 5-year-old who picks "one last little thing" and is
stopped at the same second as if they had not is being taught the choice was
theatre — and children this age detect exactly that, because they test it.

**Recommendation.** Either let "finish this one" actually hold put-away to the
next natural boundary (capped, budget unaffected, while the activity is still
receiving input), or delete the second button and make S5 a plain spoken
acknowledgement. Do not ship a fake choice.

### C4 — MAJOR: Undo is inert exactly where undo matters

**Evidence.** `app.py:1509–1528` — in `IN_ACTIVITY` the band's Undo just speaks
"Draw has its own undo button." Tux Paint's undo is ~12 mm inside a 16-tool
column (audit 01 #1 measured 48 px), unlabelled for a pre-reader. 01 #22 asks
for universal undo in a fixed position *because* under-7s cannot mentally
reverse actions. The docstring's reasoning is honest, but you removed Ask from
the band arguing "an always-disabled control teaches the child that buttons
lie" (§7a) — which applies with more force to the control the child needs most
while drawing. **Recommendation:** add `undo_key` to the manifest (Tux Paint
and KTuberling are both documented Ctrl+Z) and synthesise it; where no key
exists, hide Undo as `set_finishing_mode` already does.

### C5 — MAJOR: the 18 mm floor is a unit-conversion artefact

**Evidence.** `06:23` records Hourcade et al. (2004) as 1024×768 on a period
17-inch CRT; `06:37` converts "64 px ≈ 17 mm at ~96 dpi"; 06 #13 makes that an
18 mm floor. But 1024 px across a 17-inch CRT is ~75–80 dpi, so the study's
64 px target was ~20–22 mm — and 01 #1 reports its physical figure as
**23.7 mm**. Checkpoint-1 item 15 ruled "keep 18 / prefer 24" without noticing
that the smaller number assumes the study's display had modern density —
precisely the error 01 §4 names (*do not size targets in pixels*). It matters
downstream: everyone else's target arguments (the tick, the gate, band buttons
at 20.4 mm) are being judged against a floor a third too low.

**Recommendation.** Set `MIN_TARGET_MM = 24.0`, or write an ADR saying "we chose
18 because 24 does not fit a 1280×800 panel" — an honest reason, unlike the
current derivation.

### C6 — MAJOR: the evaluation plan cannot answer its own question

**Evidence.** `09 §11` P1 / CHILD-TEST-PROTOCOL: the primary outcome is a 1–5
upset rating made by the parent who built the system, in an ABAB with 8-session
phases — two months in which phase is confounded with novelty, maturation and
household season. Expectancy effects on an affect rating by an invested rater
are not a caveat, they are the result. Second: P4 asserts burst-clicking "C4
already logs this". It does not — `grep` finds two comments (`widgets.py:44`,
`state.py:115`) and no detector; the audit marks C4 **MISSING**. The plan rests
on an instrument that does not exist, and burst-clicking is the field's best
behavioural proxy for frustration.

**Recommendation.** (a) Randomised alternating-treatments, condition by coin at
session start, so time is balanced. (b) A second adult codes affect from a
recording framed below the band — trivially blindable. (c) Build the
burst-click detector before test #1 (~20 lines). (d) Treat n=1 with your own
child as hypothesis-generation; recruit three other families before any claim
reaches the README.

### C7 — MINOR: the band swaps meaning under the hand at the worst moment

`band.py:403` `set_offer_mode` replaces Undo and My Things with two ending
buttons *in their slots* for 20 s (`app.py:119`). "Nothing moves" is good
reasoning; the consequence is that position-learned affordances briefly mean
something else, and the replacement icons (a sunset; two shapes) are not
depictive of the sentences they carry. Same principle as forum #5 (All done
migrating), which I agree with. **Fix:** put the offer buttons in slots the
child has never learned (between the sun and the Ear); leave Undo alone.

### C8 — MINOR: "See you next time"

`goodbye.py:160` sets the headline to exactly the sentence `suggestions.py:8`
forbids ("never *see you next time* — D6, the system has no interest in whether
the child returns"), on the branch where the child made nothing. Forum #28 has
the fuller version (the same condition hides "Show a grown-up"); I agree.
**Fix:** a warm, non-evaluative line about doing, not producing.

### C9 — MINOR: the Journal's day headings are words

`journal.py:45–47` — "Today / Yesterday / Before" with no picture cue, which
01 #33 and 08 §4.3 both ask for and the audit logged as P1. It is the surface
P3 exists to test. **Fix:** a sun / moon / stack-of-days glyph per heading
before P3 runs, or P3 measures the wrong thing.

### C10 — MINOR: the percentages are conformance, not usability

"≈45% MET" reads like an outcome. No child has used this; every MET row is a
claim about code against your own reading. Keep the number out of anything
public.

## 4. What I would test with a 5-year-old first, and how

**Before switching anything on — the icon-naming probe (10 min, paper).** Print
the Home tiles with labels masked. A second adult asks "point to the one where
you draw a picture", then per tile "what do you think this one does?" Code hit
rate and spontaneous naming. Settles C1 for the cost of a sheet of paper, and
without spending a session. Same for the band and offer icons.

**Session 1 — baseline free play (25 min), recorded, coded afterwards.**
CHILD-TEST-PROTOCOL's plan, with amendments. Record screen + room audio + a
wide shot of the hands (no face) and code from the recording, not live — you
cannot facilitate and code at once, and live coding is where observer bias
enters. Active intervention (01 #44) only after a count of ten. Codes: time to
first launch; time to first *mark on a canvas*; target misses and burst-clicks;
every adult appeal and what preceded it; each Back/Undo press and what the
child expected; unprompted Ear use; right-clicks, double-clicks and drags
attempted. No think-aloud — 5-year-olds do not do it, and asking changes what
they do. The ending happens in the same session: the machine ends it, the
parent stays silent behind, upset coded 1–5 from the recording by the second
adult, and note whether the child answers the offer and what they think it
bought them (C3).

**Day 2 — the Journal (10 min).** P3's three tasks, plus one: hand the child a
printed thumbnail of yesterday's drawing and ask them to find it on screen —
that separates thumbnail-as-identity from temporal grouping, which P3 confounds.
Then the metric that matters more: entries created vs resumed, daily, for a
month.

**Preference measures.** Again-Again daily, asked by the second adult; the
Giggle Gauge (validated 4–7, named in 01 #43 and dropped from the protocol);
This-or-That only for the sun A/B, after several sessions. Never the
Smileyometer alone.

## 5. Three questions

1. **What is the ending *for*?** If its job is a smooth transition, C3's offer
   is theatre and should bite or go. If its job is to teach a routine, Knight
   (2015) — your own source — says visuals earn EBP status *only* alongside
   systematic instruction. Who teaches the ritual, and does the parent get a
   script?
2. **Who owns the tile's picture?** Accepting upstream apps meant accepting
   their icons, tool density and modal dialogues. Keep wrapping them, fork
   icons and config, or write first-party activities? That decides whether C1
   is a day's work or a permanent tax.
3. **What result would make you abandon the sun?** P1's pre-registered
   prediction is "no difference". If that is what comes back, does the
   most-engineered object in the shell stay because it is pretty? Pre-register
   the decision rule, not only the prediction.

## 6. What is genuinely novel here — honestly

The child-facing interaction vocabulary is **not** new. A flat spatially-stable
icon grid, read-aloud on everything, an auto-keep Journal with
resume-not-open, a non-numeric depleting timer, no autoplay, a machine-owned
ending: Sugar, Time Timer practice, Nintendo's soft stops and *Coco's Videos*
between them describe all of it. Do not claim otherwise. Three things *are*
new and worth writing up.

- **Enforcement below the child's session in an immutable OS image.** Your
  screen of 440 IDC 2024–26 titles matches my own reading of the venue: nobody
  has built a kids' OS. A real systems contribution to CCI.
- **A persistent child-owned band over unmodified third-party applications**
  (two toplevels + gnome-kiosk `window-config` phases, impl-notes §18–19).
  Every other kids' launcher hands over the screen and loses its chrome. §18.2's
  four compositor rules plus the §19 correction are a publishable systems note,
  and the thing I would write up first.
- **The quit contract** (`quit = signal | confirm`, grace, and refusing to
  claim a save that did not happen) — an honest ending protocol for programs
  you do not control is a small idea nobody has named.

The one cheap study that would be a genuine empirical contribution is the one
your own audit identified (§4 item 11): a 20-child replication of Hourcade's
16/32/64 px pointing task on modern hardware with modern children. Half a day,
and it settles both your 18-vs-24 argument (C5) and a 20-year-old number the
whole field still cites.
