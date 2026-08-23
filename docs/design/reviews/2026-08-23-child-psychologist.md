# Review — child clinical & educational psychologist

> Reviewer: HCPC-registered child clinical & educational psychologist (UK),
> assessing 4–8s for schools and families. Read-only review of shell v0.1.6,
> 2026-08-23. I read the spec, the implementation notes, the words the machine
> says, and the screenshots. I have not seen a child use this.
>
> My frame: I see the children for whom things go wrong — the child with ADHD,
> the anxious child, the demand-avoidant child, the younger sibling. kidnix is
> currently designed for a regulated, willing, only child in a good mood.

## 1. Verdict

**Ship it to one child, in the parent's presence, with the fixes in §3 marked
BLOCKER done first.** This is the most psychologically literate children's
computing product I have read the internals of. My concerns are not that the
principles are wrong; they are that several are **stated in the docs and not
yet true in the code**, and that the session model is calibrated for one child
at the older end of the band.

The biggest conceptual risk is not any one screen. It is that **the ending has
grown from a ritual into a six-minute wind-down**, and the evidence the team
itself cites says the announcement is not the active ingredient.

## 2. Five strengths

1. **The machine owns the ending, and the wording never blames the adult.**
   No line anywhere says "your mum said stop". This is the highest-value
   single decision in the product and it is executed cleanly. It is also the
   thing most likely to reduce real household conflict.
2. **"All done" exists, is one tap, has no confirmation, no "are you sure?",
   no bribe — and is recoverable.** `on_back` + `_goodbye_now` means an
   accidental press costs three seconds, not a session. Child-initiated
   endings are 25–31% of transitions in the literature; almost no product
   treats them as first-class. This one does.
3. **The refusal to fake competence.** Undo speaks "Draw has its own undo
   button" rather than guessing a keystroke; Ask is hidden rather than shown
   disabled; the shell says "Time to stop now" rather than "Let's keep that"
   when it destroyed work. Adults routinely underestimate how quickly a
   five-year-old detects a button that lies.
4. **Reward is the artefact, and the counting is honest.** "You made one thing
   today" counts imported entries, so it cannot claim work that was lost.
   No points, no streak, no return incentive, no notification; the
   `sessions_completed` counter is invisible to the child. A genuinely
   non-manipulative product, which is rare enough to be a finding in itself.
5. **The gate is unvoiced, free and un-penalised on failure.** No lockout, no
   growing delay, no sound, no counter. Most parental gates teach a child that
   curiosity is punished; this one teaches nothing at all, which is correct.

## 3. Concerns, ranked

### BLOCKER 1 — "All done" moves under the child's hand

`screens/home.py:134` returns `[*self._revealed(shown), ALL_DONE]`, and
progressive disclosure adds one activity every two sessions. So the tile that
carries child-initiated ending — the one control whose whole value is that a
child can reach it without deliberation — **shifts one cell along row 2 every
two sessions** until the allow-list is exhausted. This contradicts 09 §3
("fixed grid, fixed positions, never reorder"), §17.4's own promise that a
revealed tile never goes away, and the position-learning evidence the shell is
otherwise built on.

Clinically: a 4–5 year old, and any child with weak visual filtering, locates
by position before picture. A control that migrates stops being available at
the moment of highest affect — precisely when D5 is supposed to work.

**Recommendation.** Reserve "All done" a fixed cell from first run (bottom-right
of the 4×3 at the cap) and grow the activity set *around* it. Cheap; testable
headless.

### BLOCKER 2 — the sun is full and high at Goodbye

`app.py:873`: when the session is not running the band is set to
`set_progress(0.0, False, …)` — fraction 0 is *start of day*. The screenshot
`demo-goodbye-choice.png` shows it: "See you next time", and above it a bright
sun at the top of the sky at full size. The one ambient state the product has
contradicts the ritual at the exact second the child is checking whether it is
really over — and the spoken fallback ("The sun has gone down for today") says
the opposite of the picture. For a pre-reader the picture wins. For an anxious
or rigid child it is evidence that the machine's own rule does not hold, which
is an invitation to argue.

**Recommendation.** After `Session.end`, hold the sun at fraction 1.0 (below the
horizon, outline only) through Goodbye and Sleeping; reset to 0.0 only on entry
to `CHOOSING`. One line, one test.

### MAJOR 3 — the ending is 24% of the session

At the 25-minute default, the ending offer lands at T−6 and put-away at T−2:
**a quarter of the sitting is about the sitting ending.** The evidence the team
cites does not support this shape. Coco's ritual was two beats — at the start
of the last item, and one minute out. The four JABA experiments say an
antecedent cue six minutes ahead is inert; Hiniker says an early adult-voiced
warning is worse than none. Six minutes is also well beyond the felt-time
horizon of a 4–5 year old, and Chen's finding (children *overestimate* absorbing
durations) means those six minutes feel longer than they are.

Predicted failure: the child answers the offer, carries on, forgets entirely,
and experiences put-away at T−2 as the surprise the design exists to prevent.
The offer latch (`offer_shown`) guarantees it is never repeated — correct as
anti-nagging, wrong as memory support.

**Recommendation.** Make `ending_offer_at` proportional (≈15–20% of the granted
length, floor 2 min, ceiling 4) rather than a fixed six minutes, and default to
3–4. Keep put-away at 2. Then run P1 against the shortened version, not the
current one.

### MAJOR 4 — a truncated session opens into its own ending

`Session.start`: `granted = min(wanted, usage.remaining(daily_budget))`, with no
floor. With a 60-minute budget and 25-minute sittings, the third sitting is 10
minutes and the offer arrives four minutes in. A 7-minute grant produces a
session that is offer, then put-away, then goodbye. There is no
"not-enough-time-left" refusal.

Two harms. Session *length* becomes unpredictable, so the child cannot learn
how long "a go on the computer" is — the one thing a depleting timer should
teach. And the sun's rate silently changes between sittings, so a child who has
learned to read it is systematically misled. This lands hardest on the second
and third sittings, when the child is most tired and least regulated.

**Recommendation.** Add `MIN_SESSION_SECONDS`. If less than that remains, refuse
the start warmly and honestly ("The sun has gone down for today") rather than
granting a stub. If you would rather spend the remainder, compress the ritual
proportionally (see MAJOR 3) so the offer never lands in the first third.

### MAJOR 5 — "What's next after?" is a forced choice, and there are eight of them

`screens/next_after.py` has no skip, no "not sure", no "something else". The
only route off is Back, which stops the clock and returns to "Who's here?" —
where saying who you are lands you straight back on the same question. So the
child must comply with an adult-authored planning demand before the computer
will open.

That is not autonomy support. A choice is autonomy-supportive when declining is
one of the options; a compulsory choice among options someone else set is a
compliance task wearing a choice's clothes. In Coco's the choosing sat inside a
session the child had already begun. Here it is the toll gate.

Also: eight options. 09 §3's ruling is that "3–5 options" applies at every modal
moment, and Schneider's inverted-U puts the optimum at four, the 4→6 loss
mediated by **affective** stress rather than cognitive load. Eight is the
largest choice set in the product, at the moment of least investment. For a
demand-avoidant child this is the screen that ends the session before it
starts; for an ADHD child it is a planning task at the point of highest
approach motivation.

**Recommendation.** (a) Default six options, not eight. (b) Add "Not sure yet"
as a real tile that goes to Home and leaves Goodbye on the generated fallback —
it costs nothing and converts a demand into an offer. (c) Default
`skip_next_choice = true` for the 4–5 band until P2 reports. (d) Ship Coco's
ninth option; "something else" is doing autonomy work, not taxonomy work.

### MAJOR 6 — "Ask for more time" hands the ending back to the parent

The button speaks: *"A grown-up can add more time. Go and ask them."* D2 says
the machine ends the session, never the adult. This line does the opposite: it
dispatches the child to find the person who will say no, and the grants
(+5/+15/+30) live behind the PIN gate. Everything D2 buys is spent here.

This is the most likely origin of a power struggle in the product: it converts
an impersonal limit into an interpersonal negotiation at the moment of highest
arousal, with the machine's authority behind the child's request.

**Recommendation.** Until the Ask queue exists, close the loop inside the
machine ("Not this time. The sun's going down.") and **log the request for the
parent** so they can extend tomorrow's shape rather than tonight's session.
09 §6 explicitly asked for grants reachable *from the offer*; that is the right
end state, but a silent request log is the honest interim.

### MAJOR 7 — the band offer overloads two learned positions, with no words

§18.5: inside an activity, "Finish this one" and "One last little thing"
replace Undo and My Things *in their own cells, at their own size*. The note
correctly flags that these are the only unlabelled child-facing controls. It
does not flag the larger harm: **the child who has spent three weeks learning
that the third square is My Things now presses "one last little thing" with
that motor habit**, at the highest-stakes decision in the product. "Nothing
moves" was the right instinct applied to the wrong invariant — the invariant a
child learns is *position means meaning*, not *position means pixel*.

**Recommendation.** Do not reuse learned positions. Put the offer in the band's
empty middle region (either side of the sun), or accept a taller band for
twenty seconds. Get a child's eyes on it before this ships, as §18.9 #5 asks.

### MAJOR 8 — nothing is actually age-banded

B8 wants 4–5 and 6–8 treated as different bands. `Profile.age_band` currently
gates which activities appear and nothing else. A four-year-old and a
seven-year-old get the same six-minute pre-warning, the same eight-option
planning screen, the same 450 ms hover, the same disclosure rate. The shell's
executive demands, ascending: locate a tile (fine at 4); hold "I chose outside"
across 25 minutes (hard at 4, easy at 7); answer a two-alternative question
about the future six minutes out (beyond most 4s); inhibit a habitual reach
when the band changes meaning (hard at 4, effortful at 7). Three of the four
are pitched at the top of the band.

**Recommendation.** Wire `age_band` to ritual timings, `skip_next_choice`,
`initial_tiles` and `reveal_every_sessions`. The keys exist; only the wiring is
missing.

### MINOR 9 — the PIN is a fixed keypad entered on the child's screen

09 §8 recommended a **shuffled-layout** PIN; `_pin_page` attaches 1–9 in a
fixed 3×4 grid. A six-to-eight year old watching a parent's finger learns a
four-digit motor pattern within a fortnight, and siblings trade it. What a
child *learns* from a gate is separate from what it enforces: a gate that is
trivially observed teaches that adult limits are a puzzle rather than a
decision. Shuffle the digits.

### MINOR 10 — small wording and coverage gaps

- `KEEP_LINE` is "Let's keep that." 09 §6 asked for the Japanese framing:
  **"Let's keep that for tomorrow."** Free, and it reframes put-away as saving
  rather than ending. Do it.
- Goodbye on a zero-make day is "See you next time" plus one button. That is
  the thinnest ending in the product, delivered to the child who had the worst
  session — the exact reinforcement-density drop Castillo names as the aversive
  event. Keep the chosen next-thing large and add one warm specific line.
- The fallback suggestions are eight consecutive "Can you…?" questions. To a
  demand-avoidant child a question is a demand. Offer some declaratives.
- No `prefers-reduced-motion` handling and no calm mode; H6 promises both, and
  every transition is 350–450 ms. Sensory-sensitive children are a named
  population in your own accessibility commitment.
- §20.6 #5 is right and is a clinical issue: during the put-away wait the line
  is spoken once and two buttons silently vanish. A child who missed the audio
  — inattentive, absorbed, or in a noisy kitchen — sees only that things
  disappeared. Give the band a visible put-away state.

### On siblings, specifically

v0.1 is single-profile, but the shape is already set and it is wrong for the
39% of families who share. One Linux account means one `usage.toml`, one
Journal, one bedtime. The consequence is that **the younger child loses the
machine because the older one used it** — and that limit will be attributed to
the sibling, not to the machine, which discards the entire benefit of D2 and
imports a fairness dispute into the household. Budget, usage, disclosure state
and Journal must be per-profile before a second child is added, and the
"Who's here?" screen must not be the only per-child thing.

## 4. Red flags to watch for in the first month

1. **Sun taps rising through the session.** That is manufactured clock-watching
   and it is P1's own kill criterion. Log it and look weekly.
2. **The child asking an adult "how long have I got?" more often, not less.**
   The sun is supposed to remove that question.
3. **"All done" never pressed once in four weeks** — D5 did not land — or
   pressed within 60 seconds of Home, which means it is being hit by accident
   or used to escape something.
4. **"All done" pressed immediately after the T−6 offer.** The ritual has
   become something to get away from rather than an anticipated object.
5. **Any occasion the parent is the one who says "time's up."** That is D2
   failing, and it will show up first around "Ask for more time".
6. **Rigidity in either direction**: the child refusing to leave until the line
   plays, or treating "Ready to go outside?" as an order that must be obeyed
   even when the family's plan changed. Coco's found both.
7. **Distress concentrated on the second or third sitting of the day** —
   suspect the truncated-session problem (MAJOR 4) before you suspect the child.
8. **The child watching the PIN pad**, or asking about the grown-up button.
9. **Confusion between same-shaped icons.** The demo world ships three
   identical pencils and two identical books; shape is your only carrier of
   *what*, and colour is reserved for *whose*.
10. **A drift from making to browsing** — sessions that end with zero Journal
    entries but plenty of time in My Things. That is the consumption failure
    mode 04 warns about, arriving quietly.

## 5. Three questions

1. **When the budget runs out mid-afternoon, whose ending is that?** The
   product has one ritual and two quite different meanings — "this sitting is
   over" and "today is over". A five-year-old will not distinguish them, and
   the second is the one that produces the tantrum. What should the machine say
   the third time in a day, and should that sitting exist at all?
2. **What is the shell's answer when the child says "no"?** Right now there
   isn't one: the offer accepts two yeses and a dispatch, Goodbye accepts only
   Goodnight, and S1b accepts only compliance. 09 §6 asked for the Goodbye to
   accept "not yet" *once*, routed into Ask, without shame or bribe. That is
   the single most important missing behaviour for the anxious and
   demand-avoidant children this will meet.
3. **What does the second child get?** Every model in the code — usage,
   progress, Journal, bedtime, the sun itself — is device-scoped. Decide now
   whether kidnix is a child's computer or a family's computer, because the
   answer changes the session model, not just the profile chooser.
