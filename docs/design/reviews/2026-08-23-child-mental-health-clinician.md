# Review — child & adolescent mental-health clinician

> UK CAMHS clinician (child psychotherapy / play therapy; anxiety, attachment,
> dysregulation, early compulsive technology use). Read-only pass over the
> review packet, the shipped strings in `shell/kidnix_shell/`, four
> screenshots, and the panel forum. 2026-08-23.

## 1. Verdict

**Sound, unusually honest, and not yet safe to put in front of a child without
about a day's work on the last ninety seconds of the session.**

I have never read a children's-software spec that cites Deci, Radesky and four
JABA reversal designs, says where its own evidence is thin, and writes the
honesty note into the shipped source (`sound.py`: "the first person to hear it
with a five-year-old knows they are the experiment"). The constitution is right
— no streaks, no autoplay, no pleading character, no gen-AI, the artefact as
the reward, the machine owning the ending, no exit friction, a parent who
shapes the sandbox rather than watching the child in it. Those decisions
determine whether a product is good for a five-year-old, and they are all made
right.

My concerns are almost entirely about **the emotional register of the last two
minutes** and **what the machine does to a child who is not coping** — where
children's software actually causes harm, and the least finished part of this
build. No blocker below is expensive.

## 2. Five strengths

1. **The ending never destroys work** (§7c, §20): SIGTERM, the activity's own
   save step, a re-ask at the grace, then a kill *named as a loss* ("Time to
   stop now.", no keep earcon, nothing claimed in the Goodbye count). A tantrum
   about lost work is a tantrum you caused; you engineered that away with care.
2. **"All done" has zero friction, in a table, with a test guarding the table**
   (`BACK_DELAY_SECONDS` has one row). 25–31% of endings are child-initiated;
   you treat that as normal and make adding friction a public argument.
3. **"What's next after?" at the start** — the best clinical decision here: the
   ending becomes delivery of the child's own plan rather than a removal.
4. **The refusal to fabricate.** No digits, no countdown, no points, "Nothing
   to undo" rather than a greyed button, `Ask` hidden rather than disabled
   because "a control that never does anything teaches that buttons lie".
5. **Honesty about the evidence** — no time threshold is evidenced; Sleeping is
   parent-side enforcement and does nothing for the child; the earcons are a
   guess.

## 3. Concerns, ranked

### BLOCKER 1 — "Goodnight", a moon and a yawn, at four in the afternoon

`goodbye.py`'s **Goodnight** leads to `sleeping.py`'s moon + "kidnix is
sleeping"; `sound.py`'s `SLEEP` earcon is explicitly *a yawn*. Default bedtime
is 19:00–07:00, so the ordinary after-school session ends in night vocabulary
hours before night.

Two harms. (a) *It is not true*, and this codebase holds itself to "the words
have to be true" everywhere else (§20.3). Coco's documents the failure mode — a
child who "could not go to bed because Coco had not said it"; you run it in
reverse and invite "is it bedtime?" at 4 pm. (b) *You are spending your sleep
cues on the wrong event.* A moon, "goodnight" and a yawn are sleep-onset cues;
conditioning them to the moment the nice thing stops is backwards for
bedtime-resistant and bedtime-anxious children, most of my caseload.

**Fix:** two vocabularies, one switch (`policy.is_bedtime(now)`). Daytime
ending: "All done for today", a sun below the horizon, a state named *Resting*,
no yawn. Reserve moon/Goodnight/yawn for the real lockout. Forum #31 adds that
because Sleeping does not auto-wake while budget remains (ADR-0010 #8), the
child cannot tell whether the machine returns after tea, tomorrow or never — so
*Resting* must also say **when**, in child terms.

### BLOCKER 2 — what the machine does to a dysregulated child

`sleeping.py` binds *every* press anywhere on the surface to
`speech.speak(SLEEPING_LINE)`; `Speech.speak` has no rate limit and cancels the
previous utterance mid-word. A crying child hammering the screen — the exact
population this state exists for — gets "kidnix is sleep— kidnix is sleep—
kidnix is sleeping. Ask a grown-up." indefinitely, chopped, synthetic.

That is aversive, and it is a *demand* issued to a child whose executive
function has gone offline. Repeated demands during dysregulation escalate; it is
why we teach parents to stop talking. Everything else in the shell is admirably
non-escalating; this one surface undoes it.

**Fix:** speak once, then an 8–10 s floor; silent after three presses, warm and
dim. Drop the demand: "The computer's having a rest." Finding an adult is not a
five-year-old's task. Audit for any other unbounded repetition.

### BLOCKER 3 — a session can open inside its own ending

Found by forum #14/#15; I escalate it because clinically it is worse than
either of my own. With `granted = min(wanted, budget_remaining)` and no floor, a
late two-minute sitting begins in `Phase.PUT_AWAY`: the child taps her face,
**commits to a plan out loud on "What's next after?"**, reaches Home, and is
immediately told "Let's keep that" over nothing, then "See you next time" with
no thumbnails. A promise collected and broken inside ninety seconds, by the
object the child has been taught owns the ending. Five-year-olds attribute that
to themselves, and it teaches that the machine's rituals are unreliable.
Relatedly, fixed 6/2-minute windows make 40% of a 15-minute test session "the
sun is going down".

**Fix:** floor the grant and refuse **at Who's here**, before "What's next
after?" — never collect a plan for a session that cannot happen. Make the
windows proportional (~15–20% of granted, floor 2 / ceiling 4 min), and the
refusal warm and non-explanatory.

### MAJOR 4 — the ending offer is a choice that changes nothing

`dismiss_offer()`: both buttons latch the same flag; in-activity the transition
is an explicit no-op; put-away lands at T−2 either way. Three buttons, one
outcome. Autonomy support only works when the choice is real — Deci's
informational/controlling distinction, which this project already cites. A
pseudo-choice repeated daily teaches that the machine's questions are
decorative, and that credit is spent on every later question, including "What's
next after?", which you need believed. **Fix:** make one answer consequential
("Finish this one" suppresses new launches and lets the activity's exit trigger
put-away early), or demote it to a statement with one acknowledgement.

### MAJOR 5 — the ending does not round to a natural boundary

Spec §6: "the hard stop is the hard stop." But natural stopping points are the
*highest-leverage intervention in your own corpus* (02 §3 #2, §6 #4) — what
Hiniker actually found, as distinct from the ritual, which is Coco's. You built
the ritual beautifully and not the boundary. **Fix:** a bounded, silent
elasticity (≤90 s once per session, banked against the budget, never announced
— announcing makes it negotiable). If out of scope, say so in SYNTHESIS, so the
child test is not read as a test of it.

### MAJOR 6 — the worst day gets the coldest screen, and two banned return promises

`suggestions.py` states the rule: "never a promise about the device, never *see
you next time* (D6)". `goodbye.py`:160 sets the headline to **"See you next
time"**; `app._refuse` says **"That's all the time for today. See you
tomorrow."** Both fire on the child's flattest day — and
`show_button.set_visible(bool(made))` means the same condition **hides "Show a
grown-up"**. `demo-goodbye-choice.png` is that screen: a return promise over a
void, co-use withdrawn. **Fix:** delete both strings; a warm, non-evaluative
headline about *doing* rather than producing; never hide "Show a grown-up" —
point it at earlier days.

### MAJOR 7 — the one co-use moment is on a two-minute timer

`SHOWING_SECONDS = 120`; `_showing_done` fires unconditionally. Co-viewing is
the strongest protective moderator in your whole literature (02 §2.6, §3
#11–12) and this is the only place you build it; two minutes is about how long
it takes an adult to arrive from a kitchen. **Fix:** no timer, or 10 minutes
resetting on interaction, ended by an adult-pressed "Finished looking"; if no
adult comes, don't snatch it back. Relatedly, E1's descriptive competence
feedback ("you used five colours") — the one channel Deci says *raises*
intrinsic motivation — is in SYNTHESIS and nowhere in the code.

### MAJOR 8 — the parent gate as a relational event, and laundered anger

`finish_now()` is the *same path* for the child's "All done" and the gate's
"End session now", so a session ended in frustration reaches the child as the
machine's decision. For a scheduled ending, machine-attribution is right and
well-evidenced. For a *consequential* one it is not: the child loses the
relational information and, more importantly, the repair. What makes a rupture
safe at this age is that it is named and mended; an unnamed one attributed to a
neutral object teaches that good things stop arbitrarily. **Fix:** keep the
shared ritual, but document the rule in the panel — *"End session now" is for a
changed situation, not a consequence; if you are stopping because of behaviour,
say so yourself.* The grant flow (+5/+15/+30, reached by the child going to ask)
is the genuinely good relational event here, and "A grown-up can add more time.
Go and ask them." is the right sentence. Protect it.

### MINOR 9 — the sun contradicts its own sentence

S5 shows a large, bright, full sun above "The sun is going down". Worse (forum
#7): at Goodbye `set_progress(0.0)` reads as *start of day*, so a full high sun
sits under "See you next time". At Goodbye the child is appraising — is this
real, is it negotiable, is it my fault — and a full high sun is an affordance
for protest. **Fix:** hold at 1.0 through Goodbye and Sleeping; fix the S5
icon; soften `NOT_RUNNING` ("The sun has gone down for today."), a finality
statement available on tap to a child who checks things repeatedly. For P1 add
one measure: **sun taps in the first third** — clock-watching that starts early
is the anxiety signature.

### MINOR 10 — no character, and the ritual's evidence came from a character

Coco's effects were relational: children answered her aloud and told their
families. kidnix keeps the script and removes the speaker. Do **not** reverse
that — Radesky's parasocial-pressure category makes a character genuinely
dangerous — but note that P6 tests a *de-characterised* version of a
characterised finding, so a null result may mean "no character", not "bad
script". Meanwhile a proto-character accretes by accident: "I haven't said
anything yet", "kidnix is sleeping", a moon that sleeps, a yawn. Choose.

### MINOR 11 — band offer, bedtime wind-down, no honest exit from S1b

(a) In an activity the offer replaces **Undo and My Things** with two icon-only
glyphs whose words live only in `speak_text`, and speech "degrades silently" —
use free slots, and fall back to S5 with no voice. (b) Nothing warms or dims as
bedtime approaches (02 §3 #17): shorten a session that would overrun, and warm
the palette through the preceding hour. (c) "What's next after?" has no
"something else" and no exit but Back — rigidity is Coco's named failure mode;
add a ninth tile.

### Signs of compulsive use — keep them off the screen, put them on paper

G1 is right that there must be no dashboard. The signals that matter at 4–8 are
behavioural and belong in the parent's diary: asking for the machine as the
*first* thing on waking or on getting home; negotiating for time as the opening
move of an interaction; ending-distress that does not settle in ~10 minutes and
is unlike other transitions; loss of interest in the continuation the child
chose; the machine becoming the most reliable regulator when upset; rising
sleep-onset latency or night waking. None is diagnostic. Two or more persisting
three weeks means shorter sessions earlier in the day — not abrupt removal,
which reliably makes things worse.

### Could anything be used punitively?

Three levers: "End session now" (above); the daily budget, cut mid-day so the
child meets a refusal the machine explains on the parent's behalf; and
`allowed_activity_ids` / age bands, where a removed tile simply *vanishes*
(§16.3) — kind when developmental, punitive when a consequence,
indistinguishable to the child. None needs code; all three need a paragraph
saying limits shape the sandbox, and consequences belong in a relationship,
said out loud, by a person.

### Ethics of testing on one's own child

Better than most institutional protocols I have seen. Four additions. (1) **The
rater is not neutral** — every upset rating is made by the person who built the
thing; have the second adult rate, or rate from audio afterwards, and
pre-register all six predictions. (2) **Run P1 last, ready to abandon it** — an
ABAB reversal costs eight weeks of an inconsistent ritual in the one domain
(predictability) the product exists to provide; stop at the first sign the
child has noticed. (3) **Assent must survive the parent's investment** — a
standing rule that the child may end any session with no discussion and no
visible disappointment, and the parent logs every occasion they felt the pull
to persuade. That log is the real ethics record. (4) **This child cannot consent
to being the origin of a public artefact** — keep the log, drawings and quotes
out of anything published unless she is old enough to say no.

## 4. "Do no harm" checklist before the first child session

1. Retire Goodnight/moon/yawn from the ordinary ending; make *Resting* say when
   the machine comes back. (B1)
2. Rate-limit the Sleeping line, strip the demand, go silent after three
   presses. (B2)
3. Floor the grant and refuse at Who's here — never collect a plan for a session
   that cannot happen. (B3)
4. Delete "See you next time" / "See you tomorrow"; warm the made-nothing
   headline; never hide "Show a grown-up". (M6)
5. Make "Show a grown-up" adult-ended, not 120 s. (M7)
6. Hear all five earcons on real speakers at the capped volume before the child
   does — `sound.py` says nobody ever has. Do the yawn and the rustle startle?
7. Unplug speech-dispatcher and walk the ritual. If the band offer becomes two
   unlabelled glyphs, force S5 for test #1.
8. Rehearse the hard-stop loss path without the child, and decide what the adult
   says when a drawing is lost. It will happen.
9. Agree stopping rules in writing: stop at first clear distress; if
   ending-distress does not settle in 10 minutes, the next session is shorter
   and earlier and P1–P6 pause.
10. The parent does not touch "End session now" during test #1. And write the
    sentence the child can hold: "I made this computer and I want to see if it's
    any good. You can stop whenever."

## 5. Three questions

1. **Who is the ending for?** 09 says plainly that a hard lock-out does nothing
   for the child and exists for the parent. Will you say that in the parent
   documentation — and if not, why is the ending harder than the evidence
   supports?
2. **What is this machine's relationship to this child meant to be?** Today it
   is a room with nobody in it that nonetheless says "I", sleeps and yawns.
   Deliberate stance, or unexamined middle? P6 cannot be interpreted until that
   is answered.
3. **What would make you stop?** Name in advance the child *outcome* — not bug
   — that would cause kidnix to be shortened, delayed or shelved. Without one,
   the child test is a demonstration rather than an experiment.
