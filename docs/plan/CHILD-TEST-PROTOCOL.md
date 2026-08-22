# Child test protocol — test #1 (and the template for later ones)

> Drafted 2026-08-22 from 01 #41–45, 08 §6, 02 §5, 03 §2.12 and the
> checkpoint-1 audit. This is a *learning* session with one child (n = 1):
> it tells us about this child and this build, not about children in general.
> Write that at the top of the notes.

## Ethics first (the tester is the parent)

- Written note of intent in `docs/design/testing-log.md` before the session:
  purpose, what is observed, where notes live (local repo only, no video of
  the child committed; screenshots of the *screen* are fine).
- **Continuous assent**: "Do you want to try the computer? You can stop
  whenever you like." Stop at the first clear sign of distress or boredom —
  that is a result, not a failure.
- No incentives beyond the activity itself. No "do it for Daddy".
- A second adult (if available) for any opinion questions, so the child is
  not answering the parent.
- The parent sits *behind*, briefed to stay quiet unless asked (01 #45) —
  except: the ending is the machine's, not the parent's (02 #3).

## Setup

- Device: the VM window full-screen on the laptop, or the convertible once it
  arrives (tent mode first). Mouse + keyboard available; touch if present.
- Config for test #1 (`/etc/kidnix/parent.toml`): one profile (name, colours,
  age band 4–5), **session 15 min** (Ending offer at T−6, Put away at T−2 as
  shipped), `allowed_activity_ids` = Draw, Potato faces, Letters & numbers,
  Copy the lights, All done (5 tiles) — the subset is the checkpoint-1 A/B
  candidate; later sessions try the full grid.
- Voice: Piper cori-high (default). Audio at the capped level.
- Everything else default. No parent panel.

## Session plan (20–30 min total)

1. 0–2 min: the child sees "Who's here?" and is told only: "This is your
   computer. Touch what you like." No instructions.
2. 2–15 min: free play. Observer codes (see below). Do not rescue early; count
   to ten before helping; note what prompted help.
3. Ending offer arrives from the machine (T−6). Observe the transition with
   no adult input. Put away. Goodbye. Note the affect at each step.
4. After Sleeping: 5 minutes looking at My Things together (the co-use
   surface): "Tell me about this one." Then the Again-Again question.
5. Stop. Tidy notes within the hour.

## What to record (observation-led, 01 #42)

Per minute or per event, in `docs/design/testing-log.md`:
- Time to first successful action; time to first *creation*.
- Target misses / burst-clicks (≥ 3 clicks in 1 s) and where.
- Which tile first, which most; whether the child hovers and listens, or
  clicks immediately; whether the Ear is ever used.
- Adult appeals ("what does this do?"), and whether the spoken label answered
  it.
- Right-clicks, double-clicks, drags attempted; keyboard touched?
- Tux Paint: tools used; the quit dialog — understood? accidental quits?
- The sun: looked at? pointed at? tapped? any words about time.
- Transition: upset 1–5 (Hiniker's scale), what the child said/did at Ending
  offer / Put away / Goodbye; child-initiated ending?
- Journal: recognises own work? taps a card? understands "resume"?
- Any moment the child looked lost (no visible way back) or scared (sound,
  sudden change).
- Voice: understood? imitated? asked to repeat?

## Preference measures (01 #43)

- **Again-Again** (would you do this again? yes/maybe/no) per activity, asked
  daily across sessions rather than once.
- **This-or-That** only when comparing two versions (e.g. sun vs no sun) —
  and only after several sessions, by the second adult.
- Smileyometer: not as a primary measure.

## Hypotheses this test can speak to (from checkpoint 1)

The gap sweep (`docs/research/09 §11`) defines six costed within-child
protocols — **P1** sun visible vs hidden (ABAB, 8 sessions/phase, upset 1–5),
**P2** pre-chosen offline continuation vs generated suggestion, **P3** Journal
temporal grouping and resume (three tasks + resume-rate over a month), **P4**
mouse vs trackpad vs touch vs tent mode on the real hardware (half a day),
**P5** hover dwell 450 vs 350 ms (instrumented, no task), **P6** the ending
ritual as an anticipated object (diary, four weeks). Test #1 is the baseline
session before any of them; it should collect every measure P1–P6 need.

- H1: the child notices and understands the sun (or not).
- H2: 5 tiles vs 12: time-to-first-launch and errors (later sessions A/B).
- H3: hover-speak at 300 ms: chatter vs help (count utterances/min).
- H4: machine-owned ending: upset ≤ 2 on a 5-point scale.
- H5: the Journal's temporal grouping is understood (can find "the one from
  yesterday" on day 2).

## After the session

- Write the log; list the top 3 things that surprised us; file issues.
- Re-run the checkpoint audit items whose status the session changed.
- Decide the next session's single variable to change.
