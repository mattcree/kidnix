# Review — developmental psychology (self-regulation, transitions, family routines)

> Reviewer: developmental psychologist, early-childhood self-regulation and
> screen-media transitions. Read: AGENTS.md §3; SYNTHESIS §2 D/E/G, §4b; 02
> §3–§5; 09 Q1/Q6/Q8/§10–11; shell-v0.1 §2 S5–S8, §7a–7c; impl. notes §16–20;
> CHILD-TEST-PROTOCOL; ADR-0010; the five screenshots; and the shell's spoken
> strings. Read-only review. 2026-08-23.

## 1. Verdict

This is the most developmentally literate piece of children's system software I
have read, and I say that having read the commercial competition. The team has
correctly identified that the ending is the product: it moved the offline
continuation to the *start* of the session, made the machine rather than the
parent own the stop, refused every reinforcement schedule, removed exit
friction as a testable fact, and — the thing I least expected — rewrote
put-away so that "Let's keep that" is only said when it is true. The
evidence-to-implementation chain is traceable in a way I have not seen outside
a trial protocol. What is not yet right is arithmetic and hierarchy, not
philosophy. Two things would make me hold the first child session: the ending
windows are absolute rather than proportional, so a short or budget-truncated
session can begin inside its own ending — including at the exact 15-minute
length the child-test protocol specifies; and the ending offer makes a promise
("Finish this one") that the clock does not keep. Both are cheap fixes. Beyond
those, the Goodbye screen buries the element the evidence calls the active
ingredient — the destination — under the element it calls inert. Fix the
arithmetic, fix the hierarchy, then test with the child.

## 2. Five strengths

1. **The destination is designed, not just the signal.** S1b "What's next
   after?" is a faithful implementation of the only field experiment on this
   exact problem, and `next_after.py` gets the subtle part right: tile label
   and spoken phrase are different strings, and *nothing* is phrased as an
   obligation on the child or the family. The docstring names Coco's rigidity
   failure mode and designs against it.
2. **"The words have to be true."** `ctx.work_lost` → "Time to stop now.", no
   keep earcon, no flight animation, and `made_on_today()` counting the Journal
   rather than the sitting so the shell cannot claim work it destroyed. A child
   told their thing was kept who then finds it gone learns that the machine
   lies about what matters to them. Few products would spend a release on this.
3. **No digits; comparisons instead of quantities.** `time_left_words` ("About
   as long as one story") is the right developmental move — 5-year-olds have no
   interval sense but own the units of their own routines — and `when_words`
   extends the same vocabulary to the Journal ("from this morning").
4. **Reward discipline is structural, not aspirational.** `sessions_completed`
   is deliberately invisible to the child, kept out of `usage.toml`, never
   reset. Favourites evict quietly at 8. No counter, no streak, no "come back
   tomorrow" in the child-facing strings. Deci/Ryan honoured in data structures.
5. **The gate is unvoiced and failure is free.** Inverting Apple's pre-literate
   advice is right, and "no lockout, no growing delay, no attempt counter, no
   sound" is the correct reading of Johnson et al. 2026 — most four-year-olds
   will try, and a machine that is cross with a child for being curious teaches
   something worse than it prevents.

## 3. Concerns, ranked

### C1 — BLOCKER. The ending windows are absolute; a session can start inside its own ending.

**Evidence.** `Session.phase()` compares `remaining` against
`policy.ending_offer_at` (360 s) and `put_away_at` (120 s), both fixed.
`Session.start()` sets `granted = min(wanted, usage.remaining(budget))` and
`may_start()` refuses only when remaining is `<= 0` — there is no floor.
Consequences:

- At the 15-minute session the child-test protocol specifies, the offer fires
  at 9 minutes: **40% of the sitting is spent in "the sun is going down"**, with
  a warm-tinted sun for the last six. At the documented minimum of 10 minutes
  it is 60%.
- With the default 60-minute budget and 25-minute sessions, a third sitting is
  granted 10 minutes; a fourth after a short session can be granted 2 minutes,
  which starts in `Phase.PUT_AWAY`. The child taps their face, answers "What's
  next after?", reaches Home — and is immediately told "Let's keep that" over
  nothing, then "See you next time" with no thumbnails.

Not a corner case: it is the ordinary end of a normal day, and it is the
un-signalled collapse in reinforcement density Castillo et al. (2018) identify
as the aversive event. A ritual occupying most of the session is not a ritual.

**Recommendation.** (a) Floor the grant: if the remaining budget is below
`MIN_SESSION_MINUTES`, refuse at Who's here with the unavailability line rather
than starting. (b) Make the windows proportional with caps —
`offer_at = min(360, 0.25 × granted)`, `put_away_at = min(120, 0.1 × granted)`.
(c) Add an invariant test: `offer_at < granted / 2` for every reachable policy.

### C2 — BLOCKER (words). "Finish this one" is a promise the clock does not keep.

**Evidence.** `dismiss_offer()` touches nothing but the latch and speech; both
answers are identical to the session. Spec §6 states the position openly ("the
hard stop is the hard stop"), but 02 §3 #2 — the strongest transition finding
in the corpus — says the timer *should* round to the activity boundary, and the
deviation is not in ADR-0010. A child who chooses "Finish this one" at T−6 and
is still drawing at T−2 has their program asked to quit anyway. The choice has
no consequence, which contradicts E3, and the second option, "One last little
thing", answers with "One last little thing, then." — permission for something
the shell may cut in four minutes.

**Recommendation.** Pick one and record it. Either make the offer real — a
bounded elastic tail (say up to 3 minutes from the same daily budget, logged) —
or change the words to describe what happens ("The sun is going down. Time for
the last thing."). Do not ship the shell's most prominent choice as theatre;
Coco's showed children take these statements literally, and the inverse lesson
— that the machine's questions mean nothing — is the one that generalises.

### C3 — MAJOR. Goodbye inverts the evidence's own hierarchy.

**Evidence.** In `goodbye.py` the headline is `screen-title`, the ritual
buttons are 60 × 28 mm, thumbnails 35 mm — and the child's chosen destination
is a 24 mm icon beside a `quiet-line` label, appended last; on the e2e contact
sheet it sits on the bottom edge, and the implementer flagged that it wraps.
The utterance is `speech.speak(f"{headline}. {line}")`, so the sentence the gap
sweep rates highest arrives as the tail of a sentence about counting.

**Recommendation.** Invert it: the chosen picture large and central, "Ready
to…?" at `big-line`, Goodnight below it. Speak it as a separate utterance,
last, after a beat. This costs layout, not evidence, and it is the single
cheapest way to act on Castillo's finding.

### C4 — MAJOR. The in-activity offer asks a five-year-old to choose between two unlabelled pictures.

**Evidence.** §18.5 and `shell-v0.1.5-band-offer.png`: Undo and My Things are
replaced in place by `kidnix-finish` (a setting sun) and `kidnix-one-more` (an
abstract square-plus-small-square). The notes concede this is "the one place in
the shell where a child-facing control has no visible label". The two icons are
not discriminable without the audio, and the audio plays once, over a child who
was drawing.

**Recommendation.** Do not offer a choice you cannot label. Either present the
offer on the content surface (as everywhere else), or reduce the in-activity
form to one spoken statement plus one labelled action. A guess made under time
pressure is not agency.

### C5 — MAJOR. "Show a grown-up" is a two-minute timer on the co-use surface, and it revokes itself.

**Evidence.** `SHOWING_SECONDS = 120`, then `SHOWING_DONE` returns the child to
Goodbye. 02 §12 names the post-session journal review as the highest-leverage
co-use moment for a busy family; the child cannot *summon* the adult (Ask is
hidden in v0.1); two minutes is often less than the time an adult takes to
arrive, and a child mid-narration is interrupted by the machine — the exact
experience the ritual exists to prevent.

**Recommendation.** No wall clock. End SHOWING on Goodnight, or after ~60 s of
no interaction, never mid-look.

### C6 — MAJOR (small words, real principle). Two lines invite the child back.

**Evidence.** `app._refuse()`: "That's all the time for today. **See you
tomorrow.**" And `goodbye.py`'s headline when nothing was made: "**See you next
time**". `suggestions.py`'s own docstring forbids exactly this. Worse, the
budget refusal lands *after* the child has chosen their profile and committed,
so it reads as a rejection rather than as unavailability.

**Recommendation.** "That's all the computer for today." Headline: "Goodbye",
or lead with the chosen next thing. And surface budget exhaustion at Who's here
as unavailability (dimmed tile, spoken once), before the child invests.

### C7 — MINOR/MAJOR. "All done" is one of six equal first-run tiles, spoken as a question, acting immediately.

**Evidence.** `home.py`: `speak_text = "All done for today?"` on a control that
fires the ending with no confirmation; progressive disclosure puts it in the
first-run six, same size, same grid, a pretty lilac moon. D5 is right that early
ending must be unconfirmed — but a *question* on an immediate control is a
mismatch, and recovery (Back on Put away after the 3 s lock) needs a child who
knows Back and acts inside a window. **Recommendation:** keep
no-confirmation; make the utterance a statement of consequence ("All done. That
finishes today's turn."); consider a gap or its own row so it is not one of six
equals. Count accidental presses in test #1 — directly measurable.

### C8 — MINOR. The instrumentation is small, local, and still a behavioural record of a child.

`hover-speech: id=… dwell_ms=… selected=…` per hover, plus gate attempts, plus
`sessions_completed`. Individually defensible; together a log of what a child
looked at and hesitated over. G1 says no engagement metrics, and what gets
measured gets optimised. **Recommendation:** put the hover log behind an
`instrumentation = true` key, off by default, on only for a protocol; state a
retention period; never surface it in the parent panel.

### C9 — MINOR. The gate ships with a published PIN and no way to change it.

`DEFAULT_PIN = "1234"` with a fixed public salt; the parent panel is a stub and
the sheet has no set-PIN action. The docs are admirably honest ("treat 'still
1234' as unconfigured"), and the architecture, not the PIN, is the wall. But
behind that sheet sit "End session now" and "+30", and a child who watches a
parent type 1234 four times is inside it. **Recommendation:** force a PIN at
first boot, or refuse the grants while the default is in force.

### C10 — MINOR. Tux Paint's quit dialogue is still the child's save step.

ADR-0010 #5 is a reasonable ruling and §7c's 30 s grace with one re-ask is good
engineering. But "Let's keep that. Press the tick." resolves onto two lines of
English a pre-reader cannot read, in a shell whose fourth non-negotiable is
that nothing essential is text-only. The child who does not press it hears
"Time to stop now." and loses the drawing. Highest-value activity-side fix
after v0.1.

### On the bounded-session premise itself

I endorse it, and the team's honesty is exemplary — 09 §11 lists it as
"deliberately not tested"; 02 §5.10 records that interventions to reduce screen
time mostly don't work. Put that in the README, not only the research docs: the
defensible claim is better *quality* and better *endings*, not less time and no
developmental outcome. One residual risk: D3 says the machine owns the ending,
but the parent sets the length, presses "End session now" and grants +5. If the
child works out that the sun is the parent wearing a costume, the mechanism's
benefit evaporates. That is a family-script problem, not a code one — see Q3.

## 4. First child sessions: what to watch, and what would stop me

**Observe, at each of five beats** (first notice of the sun / offer / put away /
Goodbye / Sleeping): Hiniker upset 1–5; what the child *does with their hands*;
and — the strongest signal in Coco's, and free — **whether the child answers the
machine out loud**, pre-empts the line, quotes it to someone else, or applies it
to an adult. Also: when and how often the sun is looked at or tapped (rising
taps through the session = clock-watching, the P1 failure signal); whether the
two band-offer icons are distinguished or guessed; latency from Goodnight to
actually doing the chosen next thing; whether the child disputes or accepts the
count ("you made one thing"); accidental "All done" presses; what happens when
"Show a grown-up" is pressed and no adult comes; body language at Sleeping — a
dark screen with no way back can read as punishment; and any shame language at
all ("I didn't make anything", "I was too slow", "I did it wrong").

**I would say stop** if any of these appear:

1. Upset ≥ 4 at the same beat in two consecutive sessions.
2. Any utterance implying the machine is cross, disappointed, or judging —
   or that the child was *bad*.
3. Work destroyed where the child sees it. One instance; stop and fix.
4. The child pleads with, apologises to, or negotiates with the shell —
   parasocial attachment forming around the endings.
5. Coco's rigidity failure: the child cannot end, or cannot go to bed, because
   the machine has not said the words; or tells a parent "kidnix says you have to".
6. Agency reversal: the child asks permission before pressing "All done".
7. Sleep or bedtime worsens on days the machine is used.
8. The child stops making things and starts managing the session — rushing,
   checking the sun, choosing by what finishes in time.

Points 4, 5 and 6 are the ones I would treat as design-fatal rather than
tuneable. And per the protocol's own ethics note: the child stopping early or
finding it boring is a result, not a failure.

## 5. Three questions to the team

1. **What is the floor on a session, and what should happen when the day's
   budget leaves less than one?** Today the answer is "start anyway", and the
   child can meet a sitting that begins in its own put-away. What do you want a
   two-minute remainder to do?
2. **Is "Finish this one" allowed to move the clock?** If yes, how much and out
   of whose budget; if no, will you change the words — and who owns that call,
   the spec or the shell?
3. **In the family's account of events, who ends the session?** The design says
   the machine. The parent sets the length, can end it, and can grant +5. When
   the child asks "can I have more?", what is the parent supposed to say — and
   should the parent panel ship that sentence, the way it will ship the PIN
   prompt? If the honest answer is "ask a grown-up", then D3's protection is
   thinner than the docs claim, and the Ask flow becomes the most important
   unbuilt feature in the product rather than the fourth.
