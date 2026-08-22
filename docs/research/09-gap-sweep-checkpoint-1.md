# 09 — Gap sweep, checkpoint 1

> Targeted literature sweep against the nine open questions carried by
> `SYNTHESIS.md` §6, `01-cci-foundations.md` §5 (esp. #2, #30), `02` §5.7/§5.9,
> and `08` §4.6–4.7 / §6. Written 2026-08-22.
>
> **Method and its limits.** WebSearch was unavailable for this pass. Discovery
> ran through Europe PMC, ERIC, Crossref, DBLP and Semantic Scholar's REST APIs
> with primary-source retrieval by DOI and direct PDF fetch. OpenAlex was
> rate-limited out for the day; the ACM Digital Library returns 403 to
> non-browser fetches, so ACM abstracts came via Semantic Scholar's DOI endpoint
> and, where a paper mattered enough, from author-hosted PDFs. Google Scholar is
> blocked. The practical consequence: **coverage of open-access and
> indexed-abstract literature is good; coverage of paywalled ACM full texts is
> shallow except where noted.** Where I say "nothing found", I mean nothing found
> through those routes, and I say how hard I looked.
>
> Evidence tags used throughout: `RCT` randomised trial · `SCED` single-case
> experimental design · `FIELD-EXP` in-the-wild experiment with randomised
> condition order · `QUASI` · `OBS` observational/correlational · `QUAL`
> qualitative · `META` review/meta-analysis · `EXPERT` practitioner consensus or
> vendor guidance · `REG` regulatory/normative · `GAP` searched and found empty.
>
> **The single most valuable thing recovered in this pass** is the full text of
> Hiniker, Heung, Hong & Kientz, *Coco's Videos* (CHI 2018) — a three-week,
> 24-family in-home experiment on exactly the design problem kidnix's ending
> ritual solves. It is cited across Q1, Q4, Q6 and Q8 below and it changes three
> specifications.

---

## 1. Continuously visible depleting timers for 4–7s

### What's known

**Nobody has run the study.** No trial anywhere compares a continuously visible,
non-numeric depleting timer inside a child's software against no visible timer,
with end-of-session distress as the outcome. Europe PMC returns exactly two
records for `TITLE:"visual timer" OR TITLE:"time timer"` (one is about newborn
resuscitation); ERIC returns one for `description:"visual timer"`. The gap flagged
in `01` §5.2–5.3 and `02` §5.7 survives this sweep intact.

**What does exist, on the timer side, is two small SCEDs.** Grey, Healy, Leader &
Hayes (2009, *Research in Developmental Disabilities*) used a Time Timer as a
predictive stimulus with **one** child with developmental disabilities, in a
changing-criterion design, and successfully extended appropriate waiting from 1 s
to 10 min `SCED`. Note what the outcome was: *waiting for* a reinforcer, not
*ending* an activity. Hall Pistorio, Brady & Morris (2019, *Early Child
Development and Care*) taught self-regulation to four children aged 2–4 with a
literacy-based behavioural intervention — an electronic story *featuring* a visual
timer — with large effect sizes and generalisation `SCED`; the timer is
confounded with the story and the adult instruction, and cannot be isolated.

**What exists on the warning side is much stronger, and it is convergent and
negative.** Four independent behaviour-analytic experiments, all with
preschool-aged children, all find that the antecedent cue *on its own* does
nothing:

- Cote, Thompson & McKerchar (2005, *JABA* 38:235) compared a **2-minute verbal
  warning** with toy access during transitions in toddlers. "Both antecedent
  interventions were ineffective when implemented alone"; compliance improved only
  when combined with extinction `SCED`.
- Wilder, Chen, Atwell, Pritchard & Weinstein (2006, *JABA* 39:103), two
  preschoolers: "**advance notice of an upcoming transition was ineffective**";
  DRO + extinction reduced tantrums `SCED`.
- Wilder, Nicholson & Allison (2010, *JABA* 43:751), three children aged 4–5:
  advance notice "was ineffective for all 3 participants" `SCED`.
- Waters, Lerman & Hovanetz (2009, *JABA* 42:309) ran the component analysis on
  the *visual* version: "**visual schedules alone were ineffective**"; problem
  behaviour fell with extinction + DRO regardless of whether the schedule was
  present `SCED`.

This is important because it is a different finding from Hiniker et al. (2016).
Hiniker found parental warnings *correlated with worse* transitions (a
correlational result with an obvious confound). The JABA line finds warnings are
**inert**, not harmful. Both converge on the same design conclusion: *the
announcement is not the active ingredient.*

**What predicts a bad transition is the destination, not the signal.** Castillo,
Clark, Schaller, Donaldson, DeLeon & Kahng (2018, *JABA* 51:99) ran a descriptive
assessment across four children and found problem behaviour was more probable
"during a transition to an activity with a **lower density of reinforcement**"
`OBS/SCED`. The ending hurts because what comes next is thinner, not because the
child was told it was coming.

**The one place visual supports do earn an evidence-based-practice label** is
Knight, Sartini & Spriggs (2015, *JADD* 45:157) — 31 studies, 16 of acceptable
quality: visual activity schedules qualify as EBP for ASD **"especially when used
in combination with systematic instructional procedures"** `META`. The support is
for a *taught routine that includes a visual*, not for a visual as a standalone
signal.

**Can a 5-year-old read the metaphor?** Two developmental findings bear directly
on the sun-crossing-the-sky design. Tillman, Tulagan, Fukuda & Barner (2018,
*Developmental Science*) found that 4-year-olds can arrange temporal items in a
line with minimal priming, but **"unlike kindergarteners and adults, most
preschoolers did not represent" time as a directional spatial line** `QUASI`.
Maheshwari & Barner (2026, *Child Development*, n=121) found 3-year-olds
comprehend "yesterday"/"tomorrow" for **autobiographical** events but even some
4-year-olds fail on hypothetical timelines `QUASI`. And Chen-style work on long
durations (2013, *J. Genetic Psychology*, n=121 preschool–grade 2) found children
**overestimate** durations they find interesting, the opposite of the adult
pattern `QUASI`. So: a horizontal left-to-right position is a weak carrier at 5;
a *quantity that visibly shrinks* is a strong one; and the child's felt duration
runs long when they are absorbed, which is precisely when the ending lands.

### Recommendation for kidnix

**Keep the sun. Change what carries the information, and stop asking it to do the
warning's job.**

- **Encode depletion as shrinking filled area / falling height, not horizontal
  travel.** The mental timeline is not reliably available at 5. Time Timer's
  actual claim is about a diminishing *quantity of red*. Make the sun visibly
  *lower and smaller*; treat left-to-right drift as decoration, not signal.
- **Do not budget effort on making the timer more salient.** Four experiments say
  the antecedent cue is inert alone. Spend that effort on S6/S7 instead (Q6).
- **Design the destination up, not the signal.** Castillo et al. says the drop in
  reinforcement density is the aversive event. The Goodbye screen must be the
  highest-reward moment of the session, and the offline continuation must be
  concrete and pre-committed (see Q6).
- **Keep the spoken two-beat ritual at natural boundaries** (T−6, T−2). That form
  *is* empirically supported — see Coco's Videos in Q6 — but it is supported as a
  *ritual*, not as a warning. Say the same words every day.
- Verdict on D3 as written: **broadly right, with one amendment** — the sun is a
  glanceable ambient state, not the mechanism. Say so in the spec so nobody
  tunes the sun expecting it to buy calm.

**Genuinely unknown → test with the child.** Whether the sun's presence reduces
or manufactures clock-watching. Protocol in §11.

---

## 2. Read-aloud on hover vs on click for pointer-using pre-readers

### What's known

**This is the emptiest of the nine.** `GAP`. DBLP's entire "children read-aloud"
result set (14 papers) is about *assessing children reading aloud* — ASR,
disfluency detection, oral-reading-fluency corpora. Not one paper evaluates
text-to-speech as a labelling layer for pre-readers. Europe PMC and Crossref add
nothing. `02` §5.9's verdict stands: read-aloud UI has no wellbeing or usability
evidence base, and the case for it is **autonomy and access**, argued from
children's-rights design principles, not outcomes.

**The nearest transferable quantitative evidence is the gaze dwell-time
literature**, which is about a *different* problem (dwell as the sole selector)
but bounds the parameter:

- Paulus & Remijn (2021, *Displays*), two experiments, 12 then 30 adults: dwell
  times from **250 ms to ~1000 ms were rated potentially useful**; across
  200/400/800/1000/1200 ms, total selection time rose with dwell but **success
  rate rose and corrections fell** `QUASI`. The trade is speed against false
  triggers, and it is monotone.
- Isomoto, Yamanaka & Shizuki (2023, *PACM HCI*) derive dwell thresholds from
  Model-Human-Processor cognitive stages rather than tuning empirically
  `QUASI` — useful framing, adult participants.

The asymmetry matters for kidnix: in gaze interaction a false dwell **performs an
action**; in hover-to-speak a false dwell **plays an unwanted sentence**. The cost
of a false positive is an order of magnitude lower, which argues for a *shorter*
threshold than gaze work would suggest — but a 5-year-old's pointer sweeps across
half a grid on the way to a target, and 12 tiles' worth of interrupted, cancelled
half-utterances is exactly the "chatter" failure mode that would make a parent
turn speech off.

**Precedent for the Ear/repeat control** is strong and entirely non-empirical
`EXPERT`: Sugar's rollover labels, PBS Kids' and Nick Jr's replay-instructions
buttons, ScratchJr's `?` help mode, CBeebies' character-led re-prompting. `08`
§4.2 already argues the case correctly — one persistent replay control beats
per-element replay affordances. No study tests it. Sesame's rule that children do
not attend to audio instructions alone, so every utterance needs a paired visual,
is the constraint that actually binds `EXPERT`.

### Recommendation for kidnix

**Keep hover-to-speak, but raise the threshold and add a motion gate.**

- **Dwell 450 ms, not 300 ms** (shell-v0.1 §3 currently says 300 ms). 300 ms sits
  at the bottom of the range adults rate usable and gives no headroom for a
  child's overshoot-and-correct trajectory.
- **Add a settle condition**: only start the dwell timer once pointer velocity
  drops below a threshold. A sweep across a tile should never start the clock.
  This is cheaper and more effective than tuning the delay upwards further.
- **Cancel on leave, and never queue.** Already specified ("new utterance cancels
  the previous"); make cancel-on-exit-before-speech explicit too.
- **Speak on keyboard focus with no delay.** This is what every screen reader
  does, it is the accessibility-correct default, and focus is deliberate in a way
  hover is not.
- **Never make hover the only route.** Every tile keeps its ≥18 pt label; the Ear
  is the deliberate on-demand route; hover is the *ambient* layer. If a family
  disables hover speech, nothing becomes unreachable.
- **Suppress hover speech during the ending ritual's scripted lines.** The one
  place the shell must be allowed to finish a sentence is S5–S7.
- Record in the spec that 450 ms is **extrapolated from adult gaze research**, and
  is the first parameter to tune in child testing.

---

## 3. Tiles per page / choice-set size for 5–6 year olds

### What's known

**Choice overload in young children is unstudied.** `GAP` — six Europe PMC hits
for `"choice overload" AND children`, none about children choosing; ERIC has one,
irrelevant. The classic choice-overload literature (Iyengar & Lepper; Scheibehenne's
null meta-analysis) is adult and contested even there.

**The best direct experiment on number of options in digital learning media** is
Schneider et al. (2021, *Human Behavior and Emerging Technologies*): Experiment 1,
N=208, M age 14.66, six between-subjects groups at 0/2/3/4/5/6 options; Experiment
2, N=180, M age 18.71, at 2/4/6 `RCT`. Result: a clear inverted U, with **four
options highest on both retention and transfer**, and the authors' guideline
"a minimum of three to five choice options." The mechanism is the interesting
part: the 2→4 gain was mediated by **decisional autonomy**, and the 4→6 loss by
**affective autonomy — emotional stress — not cognitive load**. Wrong age band for
us, right direction, and the mechanism (affective, not capacity) travels
downwards more plausibly than a capacity story would.

**The developmental constraint that actually applies is smaller than the folk
number.** Pailian, Libertus, Feigenson & Halberda (2016, *Attention, Perception &
Psychophysics*) found visual working memory capacity **increases across ages 3–8
and approaches adult-like levels between 6 and 8**, controlling for gains in
attention and executive control `QUASI`. Elliott & Cowan-line work (2019, *Dev.
Sci.*, n=30 adults / 29 seven-year-olds / 28 four-year-olds) found **filtering
efficiency** uniquely predicts WM capacity and continues developing past 7, while
capacity itself may asymptote around 7 `QUASI`. At 5–6, expect roughly 2–3 objects
held, and poor filtering of irrelevant items.

**The reframe this forces.** `SYNTHESIS` B2's "≤5 primary choices per screen" is
derived from working-memory capacity. But a Home screen of persistent, labelled,
spatially stable, audio-narrated tiles is a **recognition task with the memory
externalised**: nothing is held in mind. WM limits bind on *held* option sets — a
spoken menu, a sequence to remember, a modal list that replaces the screen. They
do not bind on a visible grid. What actually limits grid size for a 5-year-old is
(a) geometry — 40–60 mm tiles with ≥12 mm gaps on a 13" panel; (b) **visual
search**, which is serial and slow in children and is exactly what poor filtering
efficiency degrades; and (c) the affective cost of *deciding*, which Schneider puts
at its minimum around four.

Nobody has run a usability study on icon-grid size with 5-year-olds — not rows vs
free layout, not 8 vs 12 vs 16, not paging vs scrolling `GAP`. DBLP returns zero
for "kiosk children". The commercial precedent is unhelpful in a specific way:
Amazon Kids and Google Kids Space present effectively unbounded grids, which is
the "store dressed as a home" failure `08` §7 #16 already names.

### Recommendation for kidnix

**Separate the ceiling from the default, and stop citing working memory for the
grid.**

- **Hard ceiling stays at 12 tiles on one page** — justified by geometry and
  visual-search cost, not by WM. Write the justification correctly in
  `SYNTHESIS` B2, because the current wording invites someone to argue the Home
  screen down to five and lose the "everything you can do is visible at once"
  property that makes a flat shell work.
- **Default first-run set: 5–6 tiles**, growing by progressive disclosure. This is
  where the "≤5" instinct belongs, and it lands on Schneider's optimum. B2 already
  says "progressive disclosure (first session simpler than tenth)" — make the
  numbers explicit: 5 at first boot, +1 per few sessions, capped at 12.
- **Fixed grid, fixed positions, never reorder.** A 3×4 grid at the cap. Position
  learning is the field's documented success and it is also what protects a child
  with poor filtering. The *thumbnail* on a tile may update; the tile never moves.
- **Paging, not scrolling** — already correct (A4).
- **No free layout.** No evidence either way, but a movable grid destroys the one
  property (spatial stability) that the evidence does support.
- Reframe the "choice" burden away from the grid: the place to apply "3–5 options"
  is every *modal moment* — the Ending offer (2 buttons: correct), the Ask flow
  (3–4 pre-composed messages: correct), the colour chooser (3×3 = 9: consider
  cutting to 6).

---

## 4. Do 5–6 year olds understand a chronological Journal, thumbnails-as-identity, and "resume"?

### What's known

**Temporal category words: yes, earlier than expected — for their own life.**
Maheshwari & Barner (2026, *Child Development*, n=121, 3–4-year-olds) found
3-year-olds comprehend "yesterday" and "tomorrow" **when applied to
autobiographical events**, while even some 4-year-olds fail when the same words
are applied to hypothetical timelines `QUASI`. Grant-line work (2018, *JECP*)
found 3–5s more accurate on past than future references `QUASI`. A cross-linguistic
study of English and German 3–7s (N=304) found deictic *status* (past vs future) is
acquired long before precise *location* `QUASI`. So "Today / Yesterday / Before"
attached to the child's own making is developmentally within reach at 5–6.
Anything more precise ("three days ago", a date) is not.

**Temporal ordering: no, and later than you would guess.** Pathman, Doydum & Bauer
(2013, *JECP*) had 8–10-year-olds and adults photograph events daily for four
weeks; on a 12-photo ordering task, **"performance was relatively low"** for both
groups, and children were worse than adults even on simple which-came-first
judgements `QUASI`. A 2024 follow-up with ERP (7–11s vs adults, museum photos)
found the same developmental gap `QUASI`. And Tillman et al. 2018 (above) puts the
directional mental timeline at kindergarten, not preschool. **Conclusion: coarse
recency bins are fine; ordering *within* a bin must never be a task the child is
asked to perform or reason about.**

**Thumbnails-as-identity: the best evidence is indirect and strong.** In *Coco's
Videos* (Hiniker et al., CHI 2018; 24 families, children aged 3–5, M 3.6, three
weeks, 597 playlists), the **History tab — recently-watched videos as thumbnails
in reverse chronological order — was the default tab and supplied 53% of all
1,149 videos children put in playlists** `FIELD-EXP`. That is the strongest
existing evidence that a preschooler will fluently navigate a reverse-chronological
thumbnail store of their own recent activity. It is about consumption, not
creation, but the interaction is identical to a Journal card.

**Portfolio evaluations with young children are thin and contain a warning.**
Knauf & Lepold (2021, *EECERJ*) analysed analogue and digital portfolios in early
childhood education: **"the differences between both portfolio variants are very
small"**, and educators simply translate analogue habits into the digital form —
with the "children's voice" claim largely unrealised `QUAL`. Nothing found on
Seesaw or ClassDojo portfolios evaluated *with* children as users `GAP`. The
lesson: a portfolio becomes an adult's artefact unless the child's own actions
produce it. kidnix's auto-keep is the mitigation and should be argued as such.

**The closest live prior art is three months old.** Dylan (IDC 2026), *PhotoThings:
Designing child-friendly ways into personal photo archives* — autobiographical
Research-through-Design with the author's five-year-old daughter, building
physical–digital artefacts over a child-owned archive `QUAL, n=1`. Sensitising
concepts: **increasing ownership, playfulness and performativity, self-direction,
comprehensible structures, and narrative anchors**. CC-BY. This is the nearest
thing in the literature to My Things and it should be read in full before the
Journal UI is finalised.

**"Resume" semantics: still unevidenced** `GAP`. The indirect signal is again
Coco's: children ended a playlist early **31% of the time**, "often to adjust and
restart the active list of videos", and 53% of selections were re-watches from
History — i.e. returning to a previously-touched item is natural. Whether a
5-year-old forms the model "tapping this picture puts me back inside the thing that
made it" is untested.

### Recommendation for kidnix

- **Keep Today / Yesterday / Before.** It is developmentally supportable at 5–6
  *because* the events are the child's own. Do not subdivide "Before" — an
  undifferentiated bag is the correct representation of a 5-year-old's remote past.
- **Never ask the child to order anything.** No timeline graphic, no
  "which did you make first", no drag-to-reorder. Within a bin: reverse
  chronological, silently.
- **Put the recency strip on Home, not only in My Things.** Coco's History tab was
  the default surface and carried the majority of selections. shell-v0.1 already
  puts a last-entry thumbnail on the tile; go one step further and consider a
  single "the last thing you made" card on Home as the default door into the
  Journal.
- **Adopt PhotoThings' "narrative anchors"**: the caption / voice note is the
  retrieval handle a 5-year-old actually has. `05`'s "caption field + tell-me-about-it
  recorder on every drawing" already buys this — surface the caption *on the card*,
  spoken on focus.
- **Argue auto-keep as the answer to Knauf's warning** in the parent-facing copy:
  this portfolio is made by the child's doing, not by an adult's curation.
- Resume stays as designed, and goes on the test list.

---

## 5. Auditory icons and earcons for young children

### What's known

**Two papers. That is the entire literature.** `GAP`

- Jacko (1996, *Interacting with Computers* 8:1), *The Identifiability of Auditory
  Icons for Use in Educational Software for Children* — abstract elided by the
  publisher, not retrievable through open routes.
- Jacko et al. (1997, *Perceptual and Motor Skills* 84:1223): 24 children aged
  **6–9** mapped 40 auditory icons to 40 visual icons among 66 distractors.
  **Older children mapped significantly better**, and the authors attribute this to
  "more extensive exposure to everyday sounds" `QUASI, n=24`.

That single result carries the whole recommendation, and its direction is
unfavourable to kidnix's current plan: **auditory icons are learned from
world experience, and a 5-year-old has less of it than a 9-year-old.** Nothing
exists on children's recognition of *earcons* (abstract musical motifs), on
preferred durations or loudness, on startle, or on annoyance `GAP`. Hourcade's
verdict that "very little research exists" on non-speech audio for children (`01`
§5.4) is, if anything, generous.

Note the taxonomy problem in the current spec: shell-v0.1 §7a ships "four short
generated tones (keep, tap, back, sleep) at −14 LUFS". Generated tones are
**earcons** — the category with *zero* evidence — not auditory icons, the category
with weak evidence and a known age gradient.

The music-under-speech question is already settled elsewhere in the corpus and this
sweep found nothing to disturb it: the coherence principle (`02` E2), EYSTAG's
slow-content rules, and Takacs, Swart & Bus (2015) on multimedia extras all point
one way. No background music under narration, ever.

### Recommendation for kidnix

- **Prefer representational auditory icons over abstract tones wherever a
  real-world referent exists.** "Keep" should sound like paper sliding into a
  tray or a drawer shutting softly, not like a chime. "Back" should sound like a
  soft step. Reserve pure tones only for states with no physical referent (sleep).
  This is the one thing the age gradient in Jacko et al. actually tells you to do:
  lean on sounds a 5-year-old has heard in the world.
- **Keep them short (≤400 ms) and quiet (−14 LUFS, as built), and never overlap
  speech.** Queue behind the utterance; do not duck the voice. There is no
  evidence on loudness for children, so the precautionary setting is the right one.
- **Every earcon keeps a redundant visual** (already the rule). Treat the sound as
  confirmation, never as the sole carrier of a state change.
- **Keep child-facing mute** as one of the three permitted child preferences
  (`08` §7 #17).
- **Write the honesty note into the spec**: kidnix's soundscape is extrapolation
  from adult auditory-display research plus one 1997 study of 6–9s. Do not defend
  it as evidence-based; defend it as conservative.

---

## 6. The ending ritual itself

### What's known

This question turned out to have the most new evidence, almost all of it from one
paper.

**Hiniker, Heung, Hong & Kientz, *Coco's Videos* (CHI 2018)** `FIELD-EXP`. Method:
24 families, target child aged 3–5 (M 3.6, SD 0.92), Android tablet in the home for
three weeks, randomised complete block design, each family experiencing all three
conditions for a week each in counterbalanced order. The app made the child (a)
choose a session length with a parent, (b) **choose the offline activity that would
follow, from nine picture options**, then (c) build a playlist bounded by that time
budget. Nine "next activity" categories were derived empirically by clustering **381
diary entries** of what children actually did after screen use: *read a book, play
outside, eat, sleep, see friends, play with toys, bath time, leave the house,
something else*. At the start of the final item Coco says "We're almost done! Get
ready to say goodbye when this video ends"; one minute before the end, "One minute
left, then it's time to say goodbye." At the end, a full-screen transition scene
shows the child's own pre-chosen next activity and Coco says "Now it's time to
[activity]. Are you ready to [activity]?" Conditions differed only in that final
screen: **neutral** (a home button), **controlled** (no home button, locked out,
auto-reset after 3 min), **post-play** (home button plus auto-playing related
videos, the Netflix pattern). 411 playlists analysed; 292 three-minute audio
recordings of the transition coded (Cohen's κ = .783).

Findings, all of which bear on kidnix:

1. **The spoken closing ritual became an anticipated, internalised routine.**
   Children replied *aloud* to Coco ("Mm-hmm, I'm hungry!", "I'm ready to play
   outside", "No! Nope nope nope nope, no"). One child anticipated it — "Is she
   gonna say, 'Time to say goodbye'?" Another **resisted putting the tablet away
   before the line played**: "I want to see what she says." A third pre-empted the
   words. Children announced the transition to their families ("Everybody! It's
   time for bed!") and, watching with a father, explained "*we* have one minute
   left", applying the rule to both of them. This is the best empirical support
   anywhere for kidnix's Goodbye ritual, and it is qualitative but vivid and
   replicated across many families.
2. **Post-play / up-next is unambiguously harmful.** Post-play sessions had
   significantly more spill-over time than neutral (mean difference in logs .189,
   95% CI [.002, .377], p = .047) and than controlled (.322, 95% CI [.119, .525],
   p < .001). It significantly reduced children speaking directly to the character
   (16% vs 40%; χ²(2) = 16.75, p < .001) and significantly reduced autonomous
   transitions (χ²(2) = 14.655, p = .001). **71% of parents preferred it off; 0%
   preferred it on.**
3. **A hard lock-out is no better than a plain home button.** Neutral vs
   controlled did not differ significantly on spill-over (.1328, 95% CI
   [−.066, .331]), on speaking to the character, or on autonomous transitions.
   The lock-out "did not appear to reduce children's autonomy, although it also
   did not reduce viewing time or increase the need for parents to intervene."
4. **Child-initiated endings are normal.** Children ended a playlist early **31%
   of the time**. (Hiniker 2016 found 25% of transitions were child-initiated.)
5. **Parents split on rigidity, and several wanted enforcement *lower in the
   stack*.** Over half appreciated the lock-out; **35% found it too restrictive**
   ("if we both agreed that she could watch more, it would have been nice to allow
   it") — a pre-defined contract does not match how families actually negotiate.
   Meanwhile parents who wanted *stricter* limits observed that an app-level lock is
   useless: "he would exit the app and open YouTube directly"; "I would rather use
   the timer on my iPad which shuts the tablet off"; an app-level control is
   "trying to solve a problem it can't solve… not a useful feature without a global
   lock."
6. **The failure mode is literal rigidity.** Some children took the machine's
   statements as inviolable rules: one child, having picked the wrong follow-up
   activity, "had to go back and do the entire experience over again from the
   beginning… now could not go to bed because Coco had not said 'Now it's time for
   bed'". Another told his mother "Coco will make you do it."

**Putting-away rituals in preschool.** Izumi-Taylor (2024, *Childhood Education*)
describes Japanese clean-up practice `QUAL/descriptive`: teachers use **music and
encouragement** to make clean-up appealing; clean-up is framed as **an extension of
play**, not its termination; and — the detail worth stealing — **toys and activities
are saved for the next day "so children may enjoy them again."** A Greek study
(EECERJ 2016, n=30 five-year-olds) found children of exactly our age hold coherent,
uniform judgements about clean-up duties `QUAL`, i.e. the concept is available at 5.

**Exit friction as a named harm.** Kuo, Zhao & Scott (IDC 2026), *The Evil Bird and
the Right to Disconnect* `QUAL`, interviews with North American parent–child dyads
about a mainstream gamified learning app. Introduces **goal drift** (engagement
shifts from mastery to metric maintenance) and **gamified obligation** (guilt or
disappointment on exiting), shows that **exit friction stabilises engagement even
as educational meaning wanes**, and argues for an "**easy way out**" as
learning-supportive design. This is the first paper in the literature to name
kidnix's D5/D6 stance as a principle.

**Bridging / offline continuation beyond Coco's**: nothing found `GAP`.

### Recommendation for kidnix — three concrete spec changes

- **Move the offline continuation to the *start* of the session.** shell-v0.1 §S7
  currently generates the suggestion at the end from a list keyed by the last
  activity. The empirically supported form is: the child **chooses** it before they
  begin, from a small set of picture options, and the Goodbye screen simply shows
  it back and asks "Are you ready to [thing]?" This is the single highest-value
  change in this document, it costs one screen, and it converts the ending from a
  removal into the fulfilment of the child's own plan. Keep the end-generated line
  as the fallback when the child skipped or declined the choice. **Derive the option
  set the way Coco's did** — from what children in the household actually do next
  (parent-configurable, 6–9 picture options, "something else" included).
- **Fix the ritual script and never vary it.** The value observed in Coco's was
  ritual *predictability* — children pre-empted the line. Two beats: at the start of
  the last natural unit, "We're nearly done. Get ready to say goodbye"; one minute
  before, "One minute left, then it's time to say goodbye." kidnix's T−6 offer and
  T−2 put-away are the same shape; freeze the wording.
- **Build in revisability, to avoid the rigidity failure.** No line may be phrased
  as an obligation on the child or on the family. The Goodbye must accept "not yet"
  once, routed into Ask, with no shame and no bribe. The character must never say
  anything that reads as "the machine will make you."
- **Reframe the justification for Sleeping.** Neutral and controlled endings were
  indistinguishable for the *child*. So justify the Sleeping screen as **enforcement
  for the parent** (need #2), not as a kindness to the child — and make it warm,
  non-punitive and non-scolding, which shell-v0.1 §S8 already does. Do not claim it
  smooths the transition; the evidence says it does not, and it does not hurt either.
- **Take the parents' complaint seriously and note that kidnix already answers it.**
  35% of parents found a pre-defined contract too rigid → that is exactly what
  D7's +5/+15/+30 grants and the Ask flow are for; make grants reachable from the
  Ending offer, not only from the gate. And the parents who said an app-level lock
  "can't solve the problem" without "a global lock" are describing kidnix's entire
  architectural thesis. This is a quotable, primary-source validation of I1 —
  use it in the README.
- **Steal the Japanese framing for S6.** "Let's keep that **for tomorrow**" beats
  "Let's keep that." Put-away as saving-for-next-time, not as ending.
- **Adopt "the easy way out" as an explicit named principle** in `SYNTHESIS` D6,
  crediting Kuo et al. 2026 — it gives the anti-dark-pattern stance a citation in
  the current literature rather than only a moral argument.

---

## 7. Mouse / trackpad vs touch for 4–7s on a 13" convertible

### What's known

**Nothing new. `GAP`, checked hard.** Crossref, Europe PMC and DBLP return no
2020–2026 comparison of pointing devices for 4–7-year-olds on laptops. The field's
evidence remains the material already in `06`: Hourcade's throughput figures (4 yr
1.95, 5 yr 3.24, adult 7.8 bits/s), Donker & Reitsma's "it is best to point for
young children" (1998, *Computers in Human Behavior* — pointing beats dragging),
and the unresolved drag-vs-click-move-click dispute in `01` §5.1.

**The one adult finding worth extrapolating** is Sesto-line work on age and indirect
pointing: *How Age Affects Pointing With Mouse and Touchpad* (2010, *IJHCI* 26:7),
comparing young, adult and elderly users `QUASI`. Touchpad is consistently slower
and more error-prone than mouse, and the penalty **grows as motor control
degrades**. Extrapolating downwards in age rather than upwards: a five-year-old on a
trackpad is the worst pointing case in the household. There is **no** child-specific
evidence on palm rejection, accidental taps, two-finger scroll, or on tent-mode
ergonomics `GAP`.

### Recommendation for kidnix

**Optimise for mouse and touch; treat the trackpad as the degraded path, and
harden it in software.**

- **Disable tap-to-click for the kid session.** Accidental taps from a resting palm
  or a wandering finger are the trackpad's dominant failure mode with small hands,
  and A3's "input registers on press" makes every accidental tap an action.
  Require a physical click.
- **Disable two-finger scroll, edge scroll and all gestures at libinput level.**
  A2 already bans multi-touch as a design rule; enforce it in the session's input
  configuration so it is not merely a convention shell code has to honour.
- **Maximum palm rejection; disable-while-typing on.**
- **Keep 48 px cursor, flat acceleration, 700 ms double-click, 16 px drag
  threshold** (A7, unchanged).
- **Recommend tent mode as touch-first in the docs.** In tent mode the T480's
  keyboard and trackpad are inaccessible, so the machine becomes a pure touch
  device — which, for this age, is the *best* input. Recommend it as the default
  posture for 4–6, and test it first.
- This remains SYNTHESIS §6 #5 — a genuine unknown, resolvable only by testing on
  the actual hardware with the actual child. Protocol in §11.

---

## 8. Parent gate designs

### What's known

**Still no study measures bypass rates by gate type** — the `08` §4.5 gap survives
`GAP`. But this sweep found a large new experiment that bears on the underlying
behaviour.

**Johnson, Howard, Mallawaarachchi, Phillips, White, Kervin & Tobin (2026),
*An Experimental Study of Persuasive Design's Effects on Children's In-App Choices
and Play*** `RCT, preprint (Research Square, not yet peer-reviewed)`. Purpose-built
app; **554 children, M age 4.34**, randomly assigned to one of five conditions from
no persuasive design to all features combined (character pressure, locked options,
pop-up advertisements). Findings:

- Children were significantly more likely to follow a **character's**
  recommendation.
- Children **avoided locked options at greater-than-chance levels** — locks do
  deter.
- **"Still a majority attempted to access at least one locked item and bypass
  parental controls."**
- When combined, the deterring effect of locked content **outweighed** character
  persuasion.
- Advertising effects were mixed: nearly half attempted to purchase a
  limited-time character.

The design conclusion for kidnix is precise: **at four, a lock is salient and mostly
respected, but attempting it is the norm rather than the exception.** Design so that
attempting costs nothing and reveals nothing.

**Normative guidance** `REG`:

- **Apple App Review Guideline 1.3** (Kids Category): apps "must not include links
  out of the app, purchasing opportunities, or other distractions to kids unless
  reserved for a designated area behind a parental gate."
- **Apple's Kids Apps page** defines a parental gate as "adult-level tasks that must
  be completed in order to continue"; gives **maths** and **answering a question**
  as illustrative examples; prescribes **no specific mechanism**; and adds, directly
  relevant to kidnix: *"If your app is intended for pre-literate children, consider
  using a voiceover prompt to help kids know that they need to involve their
  parent."*
- **Google Play Families policy** requires a **neutral age screen** for
  mixed-audience apps and "adult action" — "a mechanism to verify that the user is
  not a child" (PIN, password, birthdate, email, photo ID, credit card) — without
  encouraging age falsification; bans interest-based advertising and remarketing to
  children.
- **COPPA's "verifiable parental consent"** is a different and much stronger
  category (credit card, signed form, video call) and is not triggered by a local,
  zero-egress device with no personal information collection. **The ICO Children's
  Code prescribes no gate design**; its relevant standards are default-high privacy,
  data minimisation and best interests. Neither regime tells kidnix how to build the
  gate; both make the *architecture* (no egress, no accounts) the compliance story.

**HCI on parental controls more broadly** `QUAL/QUASI`: Dumaru, Atashpanjeh &
Al-Ameen (CSCW 2024) prototyped controls around open communication, instilling
self-regulation and granularity against a Google baseline (21 interviews + 156
online participants); parents valued **nudges and conversation-starters over
restriction**. Ghosh et al. (CHI 2018) found children experience restriction-only
controls as surveillance. Both support G3's "Ask a grown-up replaces every silent
denial."

### Recommendation for kidnix

**Keep the layered gate as specified (G2), with five refinements — and never build
a maths gate.**

- **No arithmetic gate.** Apple's own examples are illustrative, not normative, and
  a maths gate is defeated by the exact curriculum kidnix's activities practise.
  Any gate whose difficulty is a school objective decays as the child succeeds.
- **3-second hold + shuffled-layout PIN stays.** The hold defeats accidental entry
  (the 90% case); the PIN is the only component whose difficulty does not decay.
- **The hold target must be visually inert and never announced** — no animation, no
  glow, not spoken by the character, no read-aloud on hover. Apple's "must not be
  enticing" and Sesame's rule agree. **Do not** follow Apple's pre-literate voiceover
  advice: voicing the gate advertises it. The child-facing route to a blocked thing
  is the outline-only tile and the Ask flow, not the gate.
- **Failure is silent and free.** After three wrong PINs, return to Home with no
  sound, no message, no lockout, no counter shown. Never punish a child for trying;
  Johnson et al. say most of them will.
- **Log gate attempts locally for the parent.** Same signal as an Ask request:
  "your child tried the grown-up button four times this week" is useful, private,
  and consistent with G1's no-surveillance stance because it is about *the child's
  requests*, not their behaviour. Show nothing to the child.
- **Say plainly in the docs that the PIN is not the security boundary.** The gate
  defeats a five-year-old's curiosity for a year or two. What holds is the
  architecture: a separate GDM session, immutable root, policy below the session,
  no egress. That is also precisely what the Coco's parents were asking for (Q6,
  finding 5).

---

## 9. Recent work (2024–2026) we had missed

I enumerated the complete IDC 2024 (129), IDC 2025 (146) and IDC 2026 (165)
programmes via DBLP and screened all 440 titles, plus targeted CHI/CSCW searches.

**Headline negative result: there is still no paper on a kids' operating system,
launcher, kiosk shell or child-centred OS in IDC 2024–2026.** DBLP returns zero for
"kiosk children". The field-is-empty claim in `SYNTHESIS` §0 holds as of IDC 2026.

The fifteen most relevant recent papers:

| # | Paper | Venue | Why it matters to kidnix |
|---|---|---|---|
| 1 | Kuo, Zhao & Scott, *The Evil Bird and the Right to Disconnect* — [10.1145/3773077.3806127](https://doi.org/10.1145/3773077.3806127) | IDC 2026 | Names **exit dark patterns**, *goal drift*, *gamified obligation*; argues for an "easy way out". Cite in D6. |
| 2 | Dylan, *PhotoThings* — [10.1145/3773077.3811934](https://doi.org/10.1145/3773077.3811934) | IDC 2026 | Nearest prior art to My Things; child-owned archive, **narrative anchors**, ownership, self-direction. Read in full. |
| 3 | Arif, Wani, Chowdhury, Maqsood & Chiasson, *Understanding Deception* — [10.1145/3773077.3806137](https://doi.org/10.1145/3773077.3806137) | IDC 2026 | 18 children 11–13: they **recognise** manipulative intent yet still engage, and blame themselves. Supports the "don't ship it at all" position. |
| 4 | Johnson et al., *Persuasive Design's Effects on Children's In-App Choices* — [10.21203/rs.3.rs-10395354/v1](https://doi.org/10.21203/rs.3.rs-10395354/v1) | preprint 2026 | **n=554, M 4.34, randomised.** Locks deter but most children try to bypass; character pressure works. Q8's core evidence. |
| 5 | Baxter, *Transitioning from Technology Use to Non-Technology Activities in Young Children* — [10.1145/3713043.3731608](https://doi.org/10.1145/3713043.3731608) | IDC 2025 | Ongoing PhD aiming squarely at **guidelines for apps to ease transitions in 2–5s**. Track it; consider contacting the author. |
| 6 | Brulé & Howland, *Design Space of Children Audio Players* — [10.1145/3713043.3731537](https://doi.org/10.1145/3713043.3731537) | IDC 2025 | Design space for Yoto/tonies-class devices. Directly informs need #11 (screen-off story mode). Open access. |
| 7 | *Part of the show: pseudo-interactions in educational screen media for preschoolers* — [10.1145/3773077.3812143](https://doi.org/10.1145/3773077.3812143) | IDC 2026 | Parents' and children's views on fake interactivity — the honesty question for kidnix's character. |
| 8 | *Exploring Design Principles for Engaging and Educational Pseudo-Interactions* — [10.1145/3713043.3731606](https://doi.org/10.1145/3713043.3731606) | IDC 2025 | Companion to #7. |
| 9 | *Frameworks in the Field: Real Life Tensions When Designing AI for Children's Well-being* — [10.1145/3773077.3816193](https://doi.org/10.1145/3773077.3816193) | IDC 2026 | Revisit material for ADR-0009's annual review. |
| 10 | *Designing Ethical and Rights-Respecting Child-Centred AI for Learning* — [10.1145/3773077.3816195](https://doi.org/10.1145/3773077.3816195) | IDC 2026 | Same. |
| 11 | *Grasping Data: Tangible Activities for Young Children's Understanding of Personal Data* — [10.1145/3773077.3813773](https://doi.org/10.1145/3773077.3813773) | IDC 2026 | Age-appropriate framing for explaining kidnix's local-only posture to the child. |
| 12 | *When Institutional Structures Become Child-Facing* (Singapore national learning platform) — [10.1145/3773077.3812146](https://doi.org/10.1145/3773077.3812146) | IDC 2026 | Closest thing to a deployed child-facing system shell in the recent programme. |
| 13 | *Enchanted Forest: gamified self-regulation in noisy and overstimulating settings* — [10.1145/3713043.3731554](https://doi.org/10.1145/3713043.3731554) | IDC 2025 | Input to "calm mode" (H6). |
| 14 | Dumaru, Atashpanjeh & Al-Ameen, *Re-orienting Parental Control for Children* — [10.1145/3637359](https://doi.org/10.1145/3637359) | CSCW 2024 | Parents prefer communication + self-regulation + granularity over restriction. Supports G1/G3. Open access. |
| 15 | *Reimagining Parental Control for Children with ASD* — [10.1145/3613904.3642696](https://doi.org/10.1145/3613904.3642696) | CHI 2024 | Same theme, accessibility angle; relevant to calm mode + Ask flow. |

Also noted but lower priority: *Beyond Screens: Tangible User Interfaces and Emotion
Regulation for Preschool Children* (IDC 2025, [10.1145/3713043.3728862](https://doi.org/10.1145/3713043.3728862));
*"I Like My Own Watch Independence": low-burden customisation of a probe by children
with ADHD and their parents* (IDC 2025, [10.1145/3713043.3733254](https://doi.org/10.1145/3713043.3733254));
*A Preschooler-Friendly Picture Book Recommender* (IDC 2026,
[10.1145/3773077.3812136](https://doi.org/10.1145/3773077.3812136)).

---

## 10. Changes to SYNTHESIS this implies

Nine concrete edits, in rough order of value.

1. **D4 — move the offline continuation to the start of the session.** The child
   chooses what happens next *before* they begin, from 6–9 parent-configurable
   picture options; the Goodbye shows it back and asks "Are you ready to [thing]?"
   Evidence: Coco's Videos. Also update `shell-v0.1` §S7 and add a screen between
   S1 and S2. *(This is the highest-value change in this document.)*
2. **D3 — restate the sun's job.** It is a glanceable ambient state, not a warning
   and not the mechanism that buys calm. Encode depletion as **shrinking area /
   falling height**, not horizontal travel (the mental timeline is not reliable at
   5). Evidence: four JABA antecedent-cue experiments; Tillman et al. 2018.
3. **D6 — add "the easy way out" as a named principle**, crediting Kuo, Zhao &
   Scott 2026, and add "no exit friction of any kind" to the prohibition list
   alongside autoplay and streaks.
4. **B2 — fix the justification and split ceiling from default.** Ceiling 12 tiles
   (justified by geometry and visual search, not working memory); **first-run
   default 5–6**, growing to 12. Working-memory limits bind on held option sets,
   not on a visible, labelled, spatially stable grid. Evidence: Pailian et al.
   2016; Schneider et al. 2021.
5. **D2/D5 — record the two new supporting facts**: children ended sessions early
   31% of the time in Coco's (supports D5 as first-class, not exceptional); and a
   hard lock-out was **not** better than a neutral home button for the child
   (so justify Sleeping as parent-side enforcement, not child-side kindness).
6. **B4/§3 of shell spec — raise hover dwell from 300 ms to 450 ms and add a
   pointer-velocity settle gate.** Evidence: Paulus & Remijn 2021 (extrapolated).
7. **§7a earcons — prefer representational auditory icons over generated tones**
   where a real-world referent exists; the only child evidence (Jacko 1997) says
   recognition is driven by everyday-sound exposure. Add the honesty note that the
   soundscape is extrapolation.
8. **A7 / input policy — add trackpad hardening** to the kid-session settings:
   tap-to-click off, gestures and two-finger scroll off at libinput level, palm
   rejection maximum, disable-while-typing on. Document tent mode as the
   recommended touch-first posture for 4–6.
9. **G2 — refine the gate**: never an arithmetic gate; silent, free, un-penalised
   failure; log attempts for the parent only; do **not** voice the gate (invert
   Apple's pre-literate advice). Add the primary-source parent quotes from Coco's
   about app-level locks being unable to solve the problem "without a global lock"
   as external validation of I1.

Two things this sweep **did not** change, and that should now be treated as
settled enough to stop re-litigating: the prohibition on autoplay / up-next
(Coco's gives it a clean effect size and a 71%–0% parent preference), and the
no-scrolling / paginate rule.

---

## 11. Still unknown → child-test protocols

Six things the literature cannot answer. Each with the cheapest design that would
answer it. All are within-child, run at home, with the ethics rules from `08` §6
(continuous assent; you may collect behaviour but not opinion from your own child;
recruit two or three other families).

**P1 — Does the visible sun help or hurt? (Q1; SYNTHESIS §6 #1)**
ABAB reversal, one week per phase, sun visible / sun hidden (band slot present but
empty, so spatial stability is preserved). Everything else identical, including the
spoken T−6 and T−2 lines. Primary outcome: **parent-diary upset rating at the
transition, 1–5, Hiniker's scale, one entry per session.** Secondary: sessions
ending at a natural boundary vs forced; number of times the child looks at or taps
the sun (loggable); adult appeals in the final five minutes. Minimum 8 sessions per
phase. Prediction to pre-register: no difference, or a small benefit in phase B.
If clock-watching appears, it will show as sun-taps rising through the session.

**P2 — Does the pre-chosen offline continuation work? (Q6)**
Alternating conditions by day: (a) child chooses next-activity at session start from
6 picture options, shown back at Goodbye; (b) shell generates a suggestion at
Goodbye keyed to the last activity (current behaviour). Outcome: did the child
actually do the named thing within 5 minutes (parent diary, yes/partly/no), plus
the upset rating. Coco's predicts (a) wins. n≈20 sessions.

**P3 — Does the Journal's temporal grouping and "resume" land? (Q4; §6 #2)**
Task-based, retrospective prompting over a screen recording, 20 minutes, no
think-aloud. Three tasks: "find the picture you made yesterday"; "find the one with
the blue house" (thumbnail-as-identity); "make this one different" (resume). Code:
time to first correct card; whether the child treats a card tap as *open* or as
*resume* (watch for surprise when the activity opens with the work in it); adult
appeals. Then the passive metric that matters more: **Journal entries created vs
resumed, logged daily for a month.** A resume rate near zero means the metaphor did
not land regardless of what the child says.

**P4 — Mouse vs trackpad vs touch on the T480. (Q7; §6 #5)**
Counterbalanced within-child, same task each time (open Draw, make three marks in
three named colours, return Home). Measure: time to first meaningful action;
mis-selections per minute; accidental activations (trackpad taps specifically);
observed frustration signals including burst-clicking (C4 already logs this).
Run tent mode as a fourth condition. Two sessions per condition. This is a
half-day study and it settles a decision that affects every tile size in the shell.

**P5 — Hover dwell threshold. (Q2)**
Instrument the shell to log every hover-speech trigger with dwell duration and
whether the pointer then selected that tile. Ship at 450 ms for two weeks, then
350 ms for two weeks. Metric: **proportion of utterances that are followed by a
selection of the same tile** (a proxy for "the speech was wanted") and utterances
per minute. If utterances-per-minute climbs while the follow-through proportion
falls, the threshold is too low. No child task required; this rides along on
ordinary use.

**P6 — Does the ending ritual become an anticipated object? (Q6)**
Purely observational, no instrumentation. Over four weeks, note in the parent diary
any occasion on which the child: pre-empts or quotes the closing line; announces the
ending to someone else; asks for the ritual; or applies the rule to an adult. These
were the strongest signals in Coco's and they are free to collect. If none appear
after four weeks, the script is not memorable enough — shorten and fix it further.

**Deliberately not tested**: the bounded-session premise itself (`01` §5.9 —
no RCT establishes that a software-imposed limit improves wellbeing, and a
household A/B cannot establish it either). Keep saying so.

---

## 12. Full source list

Ordered as cited. Tags: `RCT` · `SCED` · `FIELD-EXP` · `QUASI` · `OBS` · `QUAL` ·
`META` · `EXPERT` · `REG` · `GAP`.

**Transitions, warnings and endings**

1. Cote, Thompson & McKerchar (2005). The effects of antecedent interventions and extinction on toddlers' compliance during transitions. *JABA* 38:235–238. https://doi.org/10.1901/jaba.2005.143-04 — `SCED`
2. Wilder, Chen, Atwell, Pritchard & Weinstein (2006). Brief functional analysis and treatment of tantrums associated with transitions in preschool children. *JABA* 39:103–107. https://doi.org/10.1901/jaba/2006.66-04 — `SCED`
3. Waters, Lerman & Hovanetz (2009). Separate and combined effects of visual schedules and extinction plus differential reinforcement. *JABA* 42:309–313. https://doi.org/10.1901/jaba.2009.42-309 — `SCED`
4. Wilder, Nicholson & Allison (2010). An evaluation of advance notice to increase compliance among preschoolers. *JABA* 43:751–755. https://doi.org/10.1901/jaba.2010.43-751 — `SCED`
5. Castillo, Clark, Schaller, Donaldson, DeLeon & Kahng (2018). Descriptive assessment of problem behavior during transitions. *JABA* 51:99–117. https://doi.org/10.1002/jaba.430 — `OBS`
6. Knight, Sartini & Spriggs (2015). Evaluating visual activity schedules as evidence-based practice for individuals with ASD. *JADD* 45:157–178. https://doi.org/10.1007/s10803-014-2201-z — `META`
7. Grey, Healy, Leader & Hayes (2009). Using a Time Timer to increase appropriate waiting behavior. *Res. Dev. Disabil.* 30:359–366. https://doi.org/10.1016/j.ridd.2008.07.001 — `SCED n=1`
8. Hall Pistorio, Brady & Morris (2019). Using literacy-based behavioural interventions to teach self-regulation skills to young children. *Early Child Dev. Care* 189. https://doi.org/10.1080/03004430.2017.1406483 — `SCED n=4`
9. **Hiniker, Heung, Hong & Kientz (2018). Coco's Videos: An Empirical Investigation of Video-Player Design Features and Children's Media Use. CHI '18.** https://doi.org/10.1145/3173574.3173828 · full text https://faculty.washington.edu/alexisr/CocosVideos.pdf — `FIELD-EXP` *(read in full; the key source of this pass)*
10. Hiniker, Lee, Sobel & Choe (2017). Plan & Play: Supporting Intentional Media Use in Early Childhood. IDC '17. https://doi.org/10.1145/3078072.3079752 — `FIELD-EXP` *(metadata only; abstract elided)*
11. Kuo, Zhao & Scott (2026). The Evil Bird and the Right to Disconnect. IDC '26. https://doi.org/10.1145/3773077.3806127 — `QUAL` (CC-BY)
12. Izumi-Taylor (2024). Play and Responsibility: Clean-Up Time for Japanese Preschoolers. *Childhood Education* 100:4. https://doi.org/10.1080/00094056.2024.2377064 — `QUAL`
13. Young Children's Views Concerning Distribution of Clean-Up Duties (2016). *EECERJ*. https://doi.org/10.1080/1350293X.2016.1213566 — `QUAL n=30`
14. Baxter (2025). Exploring the Effects of Transitioning from Technology Use to Non-Technology Activities in Young Children. IDC '25 DC. https://doi.org/10.1145/3713043.3731608 — `protocol`

**Time, memory and temporal reasoning**

15. Tillman, Tulagan, Fukuda & Barner (2018). The mental timeline is gradually constructed in childhood. *Developmental Science*. https://doi.org/10.1111/desc.12679 — `QUASI`
16. Maheshwari & Barner (2026). Back to reality: Children's early temporal reasoning applies to real but not hypothetical events. *Child Development*. https://doi.org/10.1093/chidev/aacaf019 — `QUASI n=121`
17. Pathman, Doydum & Bauer (2013). Bringing order to life events. *JECP* 115:309–325. https://doi.org/10.1016/j.jecp.2013.01.011 — `QUASI`
18. Pathman et al. (2024). Children's and adults' memory for the order of events in a museum. *Neuropsychologia*. https://doi.org/10.1016/j.neuropsychologia.2024.108835 — `QUASI`
19. Children's understanding of yesterday and tomorrow (2018). *JECP*. https://doi.org/10.1016/j.jecp.2018.01.010 — `QUASI`
20. Today, Tomorrow, and Overmorrow: acquisition of deictic temporal terms in English and German (2025). *Open Mind*. https://doi.org/10.1162/opmi.a.254 — `QUASI N=304`
21. Children's representation of long duration (2013). *J. Genetic Psychology* 174. https://doi.org/10.1080/00221325.2011.652994 — `QUASI`
22. Busby Grant (2010). Linking yesterday and tomorrow: preschoolers' ability to report temporally displaced events. *BJDP*. https://doi.org/10.1348/026151009X479169 — `QUASI n=82`

**Choice, working memory, layout**

23. Schneider et al. (2021). Are there never too many choice options? *Human Behavior and Emerging Technologies* 3. https://doi.org/10.1002/hbe2.295 — `RCT` (CC-BY)
24. Pailian, Libertus, Feigenson & Halberda (2016). Visual working memory capacity increases between ages 3 and 8. *Attention, Perception & Psychophysics* 78. https://doi.org/10.3758/s13414-016-1140-5 — `QUASI`
25. Elliott & Cowan et al. (2019). Selective attention, filtering, and the development of working memory. *Developmental Science* 22. https://doi.org/10.1111/desc.12727 — `QUASI`

**Audio, dwell, input**

26. Jacko (1996). The Identifiability of Auditory Icons for Use in Educational Software for Children. *Interacting with Computers* 8. https://doi.org/10.1016/0953-5438(96)01023-5 — `QUASI` *(abstract closed)*
27. Jacko et al. (1997). Age-related differences in the mapping of auditory icons to visual icons in computer interfaces for children. *Perceptual and Motor Skills* 84:1223. https://doi.org/10.2466/pms.1997.84.3c.1223 — `QUASI n=24`
28. Brulé & Howland (2025). Exploring the Design Space of Children Audio Players. IDC '25. https://doi.org/10.1145/3713043.3731537 · OA https://figshare.com/articles/conference_contribution/28887008 — `QUAL`
29. Paulus & Remijn (2021). Usability of various dwell times for eye-gaze-based object selection. *Displays* 67:101997. https://doi.org/10.1016/j.displa.2021.101997 — `QUASI`
30. Isomoto, Yamanaka & Shizuki (2023). Exploring Dwell-time from Human Cognitive Processes for Dwell Selection. *PACM HCI*. https://doi.org/10.1145/3591128 — `QUASI`
31. Donker & Reitsma (1998). It is best to point for young children: a comparison of children's pointing and dragging. *Computers in Human Behavior* 14:437. https://doi.org/10.1016/S0747-5632(98)00021-1 — `QUASI`
32. How Age Affects Pointing With Mouse and Touchpad (2010). *IJHCI* 26:703. https://doi.org/10.1080/10447318.2010.487198 — `QUASI, adults`

**Gates, controls, persuasive design**

33. Johnson, Howard, Mallawaarachchi, Phillips, White, Kervin & Tobin (2026). An Experimental Study of Persuasive Design's Effects on Children's In-App Choices and Play. Research Square preprint. https://doi.org/10.21203/rs.3.rs-10395354/v1 — `RCT n=554, M age 4.34, not peer-reviewed`
34. Apple. App Review Guidelines §1.3 (Kids Category). https://developer.apple.com/app-store/review/guidelines/ — `REG`
35. Apple. Kids Apps — parental gates. https://developer.apple.com/app-store/kids-apps/ — `REG`
36. Google. Play Families policy. https://support.google.com/googleplay/android-developer/answer/9893335 — `REG`
37. Dumaru, Atashpanjeh & Al-Ameen (2024). "It's hard for him to make choices sometimes and he needs guidance": Re-orienting Parental Control for Children. *PACM HCI* (CSCW). https://doi.org/10.1145/3637359 — `QUAL+QUASI` (CC-BY)
38. Ghosh et al. (2018). Safety vs. Surveillance: What Children Have to Say about Mobile Apps for Parental Control. CHI '18. https://doi.org/10.1145/3173574.3173698 — `QUAL`
39. Reimagining Parental Control for Children with ASD (2024). CHI '24. https://doi.org/10.1145/3613904.3642696 — `QUAL`

**Journals, portfolios, archives**

40. Dylan (2026). PhotoThings: Designing child-friendly ways into personal photo archives. IDC '26. https://doi.org/10.1145/3773077.3811934 — `QUAL n=1` (CC-BY)
41. Knauf & Lepold (2021). The children's voice — how do children participate in analog and digital portfolios? *EECERJ* 29. https://doi.org/10.1080/1350293X.2021.1906291 — `QUAL`

**Recent IDC (see §9 table for the rest)**

42. Arif, Wani, Chowdhury, Maqsood & Chiasson (2026). Understanding Deception. IDC '26. https://doi.org/10.1145/3773077.3806137 — `QUAL n=18` (CC-BY)
43. Part of the show: pseudo-interactions in educational screen media for preschoolers (2026). IDC '26. https://doi.org/10.1145/3773077.3812143 — `QUAL`
44. Exploring Design Principles for Engaging and Educational Pseudo-Interactions (2025). IDC '25. https://doi.org/10.1145/3713043.3731606 — `QUAL`
45. Speer, Haney, Tasota & Hamner (2025). Beyond Screens: Tangible User Interfaces Impact Engagement with Emotion Regulation Activities for Preschool Children. IDC '25. https://doi.org/10.1145/3713043.3728862 — `QUASI`

**Searched and empty** `GAP`

- Continuously visible in-software depleting timers vs no timer, child distress outcome — Europe PMC, ERIC, Crossref, DBLP.
- Hover-triggered read-aloud with children; optimal dwell for audio labelling — DBLP (14 "children read-aloud" records, all ASR/fluency), Crossref, Europe PMC.
- Icon-grid size studies with 4–7s (rows vs free layout, 8/12/16, paging vs scrolling) — DBLP, Crossref.
- Choice overload in children — Europe PMC (6 hits, none on-topic), ERIC (1, irrelevant).
- Earcon recognition, duration, loudness, startle in children — Europe PMC (1 hit, 1997).
- Seesaw / ClassDojo portfolio evaluations with children as users — ERIC.
- 2020–2026 pointing-device comparisons for 4–7s; trackpad palm rejection / accidental taps in children; tent-mode ergonomics for children — Crossref, DBLP, Europe PMC.
- Empirical bypass rates by parental-gate type — Crossref, Europe PMC, DBLP.
- Kids' OS / launcher / kiosk shell papers, IDC 2024–2026 — full programme screen of 440 titles; DBLP "kiosk children" = 0.
