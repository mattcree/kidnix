# Review — child clinical & educational psychologist

> HCPC-registered child clinical & educational psychologist (UK), assessing
> 4–8s for schools and families. Read-only review of shell v0.1.6, 2026-08-23:
> spec, implementation notes, the words the machine says, screenshots. I have
> not seen a child use this. My frame is the children for whom things go wrong
> — ADHD, anxious, demand-avoidant, the younger sibling. kidnix is currently
> designed for a regulated, willing, only child in a good mood.

## 1. Verdict

**Ship it to one child, in the parent's presence, with the §3 BLOCKERs fixed
first.** This is the most psychologically literate children's computing product
I have read the internals of. My concerns are not that the principles are wrong;
they are that several are **stated in the docs and not yet true in the code**,
and that the session model is calibrated for one child at the older end of the
band.

The biggest conceptual risk is not any one screen: **the ending has grown from a
ritual into a six-minute wind-down**, and the team's own evidence says the
announcement is not the active ingredient.

## 2. Five strengths

1. **The machine owns the ending, and no line blames the adult.** Nothing says
   "your mum said stop". The highest-value single decision here, cleanly
   executed, and the thing most likely to reduce real household conflict.
2. **"All done" is one tap, with no confirmation, no bribe — and is
   recoverable.** `on_back` + `_goodbye_now` mean an accidental press costs
   three seconds, not a session. Child-initiated endings are 25–31% of
   transitions in the literature; almost no product treats them as first-class.
3. **The refusal to fake competence.** Undo speaks "Draw has its own undo
   button" rather than guessing a keystroke; Ask is hidden rather than shown
   disabled; the shell says "Time to stop now" rather than "Let's keep that"
   when it destroyed work. A five-year-old detects a button that lies faster
   than adults expect.
4. **Reward is the artefact, and the counting is honest.** "You made one thing
   today" counts imported entries, so it cannot claim work that was lost. No
   points, no streak, no return incentive; `sessions_completed` is invisible to
   the child. Genuinely non-manipulative — rare enough to be a finding.
5. **The gate is unvoiced, free and un-penalised on failure.** No lockout, no
   delay, no sound, no counter. Most gates teach a child that curiosity is
   punished; this one teaches nothing at all, which is correct.

## 3. Concerns, ranked

### BLOCKER 1 — "All done" moves under the child's hand

`screens/home.py:134` returns `[*self._revealed(shown), ALL_DONE]`, and
progressive disclosure adds one activity every two sessions. So the tile
carrying child-initiated ending — the one control whose value is that a child
can reach it without deliberation — **shifts one cell along row 2 every
fortnight** until the allow-list runs out. This contradicts 09 §3 ("fixed
positions, never reorder"), §17.4's own promise, and the position-learning
evidence the shell is built on.

Clinically: a 4–5 year old, and any child with weak visual filtering, locates by
position before picture. A control that migrates stops being available at the
moment of highest affect — precisely when D5 must work. (Dan on the parent
panel makes the autism case: the map is redrawn every fortnight.)

**Recommendation.** Reserve "All done" a fixed cell from first run and grow the
activity set *around* it. Cheap; testable headless.

### BLOCKER 2 — the sun is full and high at Goodbye

`app.py:873`: with no session running the band gets `set_progress(0.0, …)` —
fraction 0 is *start of day*. `demo-goodbye-choice.png` shows the result: "See
you next time" under a bright full sun at the top of the sky, while the spoken
fallback says "The sun has gone down for today". For a pre-reader the picture
wins. The one ambient state the product has contradicts the ritual at the second
the child is checking whether it is really over — for an anxious or rigid child,
evidence that the machine's own rule does not hold, and an invitation to argue.

**Recommendation.** After `Session.end`, hold the sun at fraction 1.0 (below the
horizon) through Goodbye and Sleeping; reset only on entry to `CHOOSING`.

### MAJOR 3 — the ending is 24% of the session

At the 25-minute default the offer lands at T−6 and put-away at T−2: **a quarter
of the sitting is about the sitting ending.** The team's own evidence does not
support that shape. Coco's ritual was two beats — the start of the last item,
and one minute out. The four JABA experiments say a cue six minutes ahead is
inert; Hiniker says an early adult-voiced warning is worse than none. Six
minutes is beyond a 4–5 year old's felt-time horizon, and Chen (children
*overestimate* absorbing durations) makes it feel longer still.

Predicted failure: the child answers the offer, carries on, forgets, and meets
put-away as the surprise the design exists to prevent. The `offer_shown` latch
guarantees it is never repeated — right as anti-nagging, wrong as memory support
for the ADHD child.

**Recommendation.** Proportional `ending_offer_at` (≈15–20% of granted, floor 2,
ceiling 4), default 3–4; put-away stays 2. Run P1 against that version.

### MAJOR 4 — a truncated session opens into its own ending

`Session.start` sets `granted = min(wanted, usage.remaining(daily_budget))` with
no floor and no "not-enough-time-left" refusal. Third sitting of a 60-minute
day: 10 minutes, offer four minutes in. (The panel's developmental psychologist
found the sharper case — a 2-minute grant *begins* in `Phase.PUT_AWAY`.)

The clinical harm beyond the reinforcement collapse: session *length* becomes
unlearnable. The sun's rate silently changes between sittings, so a child who
spent three weeks learning to read it is misled on exactly the sittings that
matter — the second and third of the day, when she is tired and least regulated.

**Recommendation.** A `MIN_SESSION` floor; below it, refuse warmly at Who's here
rather than granting a stub. Plus proportional windows (MAJOR 3).

### MAJOR 5 — "What's next after?" is a forced choice, and there are eight of them

`screens/next_after.py` has no skip, no "not sure", no "something else". The only
route off is Back, which stops the clock and returns to "Who's here?" — where
saying who you are lands you back on the same question. The child must comply
with an adult-authored planning demand before the computer will open.

That is not autonomy support. A choice is autonomy-supportive when declining is
one of the options; a compulsory choice among options someone else set is a
compliance task wearing a choice's clothes. In Coco's the choosing sat inside a
session already begun; here it is the toll gate.

Also eight options — the largest choice set in the product, at the moment of
least investment. 09 §3's own ruling is that "3–5" applies at every modal
moment; Schneider's optimum is four, the 4→6 loss mediated by **affective**
stress, not cognitive load. For a demand-avoidant child this is the screen that
ends the session before it starts; for an ADHD child, planning at the point of
peak approach motivation.

**Recommendation.** Six options, not eight. Add "Not sure yet" as a real tile
that goes to Home and leaves Goodbye on the fallback — it costs nothing and
converts a demand into an offer. Default `skip_next_choice = true` for the 4–5
band until P2 reports. Ship Coco's ninth option: "something else" is doing
autonomy work, not taxonomy work.

### MAJOR 6 — "Ask for more time" hands the ending back to the parent

The button speaks: *"A grown-up can add more time. Go and ask them."* D2 says
the machine ends the session, never the adult; this dispatches the child to the
person who will say no, with the grants behind the PIN gate. It is the most
likely origin of a power struggle here — an impersonal limit converted into an
interpersonal negotiation at peak arousal, with the machine's authority behind
the child's request.

**Recommendation.** Until the Ask queue exists, close the loop inside the
machine ("Not this time. The sun's going down.") and **log the request for the
parent**, who can change tomorrow's shape rather than tonight's session.

### MAJOR 7 — the band offer overloads two learned positions, with no words

§18.5: inside an activity, "Finish this one" and "One last little thing" replace
Undo and My Things *in their own cells*. The note flags that these are the only
unlabelled child-facing controls; the larger harm is unflagged. **The child who
spent three weeks learning that the third square is My Things presses "one last
little thing" with that motor habit**, at the highest-stakes decision in the
product. "Nothing moves" was the right instinct on the wrong invariant: a child
learns *position means meaning*, not *position means pixel*.

**Recommendation.** Never reuse a learned position — use the band's empty middle
region, or a taller band for twenty seconds. Child's eyes on it first (§18.9 #5).

### MAJOR 8 — nothing is actually age-banded

B8 wants 4–5 and 6–8 treated differently; `Profile.age_band` gates which
activities appear and nothing else. A four-year-old and a seven-year-old get the
same six-minute pre-warning, eight-option planning screen, 450 ms hover and
disclosure rate. The shell's executive demands, ascending: locate a tile (fine
at 4); hold "I chose outside" across 25 minutes (hard at 4, easy at 7); answer
a two-alternative question about the future six minutes out (beyond most 4s);
inhibit a habitual reach when the band changes meaning (hard at 4, effortful at
7). Three of four are pitched at the top of the band.

**Recommendation.** Wire `age_band` to ritual timings, `skip_next_choice`,
`initial_tiles` and `reveal_every_sessions`. The keys exist; the wiring does not.

### MAJOR 9 — the ordinary 4 pm ending speaks in night vocabulary

Credit to the panel's child-mental-health clinician: Goodbye's button is
"Goodnight", Sleeping shows a moon, the `sleep` earcon is a yawn — while default
bedtime is 19:00–07:00. Beyond their conditioning objection, a second harm:
Sleeping does not auto-wake while budget remains (ADR-0010 #8), so after a 4 pm
"goodnight" the child cannot tell whether the machine returns after tea,
tomorrow, or never. Unreadable availability is what makes a child ask an adult
repeatedly — the thing D2 exists to prevent. Two vocabularies switched on
`is_bedtime`, and the daytime screen must **say when, in child terms**.

### MINOR 10 — the PIN is a fixed keypad entered on the child's screen

09 §8 recommended a **shuffled-layout** PIN; `_pin_page` attaches 1–9 in a fixed
3×4 grid, and it ships as 1234. A six-to-eight year old watching a parent's
finger learns the motor pattern within a fortnight, and siblings trade it. What
a child *learns* from a gate differs from what it enforces: one trivially
observed teaches that adult limits are a puzzle, not a decision.

### MINOR 11 — small wording and coverage gaps

- `KEEP_LINE` is "Let's keep that." 09 §6 asked for the Japanese framing:
  **"Let's keep that for tomorrow."** Free, and it reframes put-away as saving.
- Goodbye on a zero-make day is "See you next time" plus one button — the
  thinnest ending in the product, given to the child who had the worst session.
  Castillo's reinforcement drop, shipped. Keep the chosen next-thing large and
  add one warm specific line.
- The fallback suggestions are eight consecutive "Can you…?" questions. To a
  demand-avoidant child a question is a demand. Offer some declaratives.
- No `prefers-reduced-motion` handling and no calm mode; H6 promises both.
- §20.6 #5 is a clinical issue: during the put-away wait the line is spoken once
  and two buttons silently vanish. A child who missed the audio — inattentive,
  absorbed, in a noisy kitchen — sees only that things went. Give the band a
  visible put-away state.
- A parent grant (+5) can create a sub-minimum sitting; refuse it in the gate,
  in words, with the minimum named.

### On siblings, specifically

The profiles are cosmetic — `journal_root`, `usage_state` and `progress_state`
carry no profile segment. One Journal, one budget, one disclosure counter, so
**the younger child loses the machine because the older one used it** — and the
limit gets attributed to the sibling, not the machine, discarding D2's benefit
and importing a fairness dispute. Fix all three paths before a second child.

### On the honesty of the claims to parents

Better than the field. The README says "nothing here has been tested with a
child yet"; the grown-up sheet says "no number here is evidence-based; 25 is the
precaution"; the sound module records that no earcon has been heard on real
speakers. I have not read a children's product that does this. Two gaps. That
honesty lives in docstrings no parent will read — the *parent panel* needs a
short "what we know and what we're guessing" page. And "a gentle ending" is a
claim about the child's experience that Coco's does not support: a lock-out was
no better for the child than a plain home button. Promise that the machine, not
the parent, holds the limit. Do not promise calm.

## 4. Red flags to watch for in the first month

1. **Sun taps rising through the session** — manufactured clock-watching, P1's
   own kill criterion.
2. **The child asking an adult "how long have I got?" more, not less.**
3. **"All done" never pressed in four weeks** (D5 did not land), or pressed
   within 60 s of Home (mis-hit, or an escape route).
4. **"All done" straight after the T−6 offer** — the ritual has become
   something to get away from.
5. **Any occasion the parent says "time's up."** D2 has failed; look first at
   "Ask for more time".
6. **Rigidity in either direction** — refusing to stop until the line plays, or
   treating "Ready to go outside?" as an order that overrides the family.
7. **Distress concentrated on the second or third sitting** — suspect the
   truncated session (MAJOR 4) before you suspect the child.
8. **The child watching the PIN pad**, or asking about the grown-up button.
9. **Same-shaped icons confused** (the demo ships three identical pencils).
10. **Drift from making to browsing** — sessions ending with no Journal entries
    but time in My Things.

## 5. Three questions

1. **When the budget runs out mid-afternoon, whose ending is that?** One ritual
   carries two very different meanings — "this sitting is over" and "today is
   over". A five-year-old will not distinguish them, and the second is what
   produces the tantrum. What should the machine say the third time in a day,
   and should that sitting exist at all?
2. **What is the shell's answer when the child says "no"?** There isn't one:
   the offer takes two yeses and a dispatch, Goodbye takes only Goodnight, S1b
   takes only compliance. 09 §6 asked for Goodbye to accept "not yet" *once*,
   routed into Ask, without shame or bribe. That is the most important missing
   behaviour for the anxious and demand-avoidant children this will meet.
3. **What does the second child get?** Usage, progress, Journal, bedtime and
   the sun are all device-scoped. Decide now whether kidnix is a child's
   computer or a family's computer: the answer changes the session model, not
   just the profile chooser.
