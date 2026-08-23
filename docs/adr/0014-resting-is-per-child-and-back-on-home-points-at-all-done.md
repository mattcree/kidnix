# ADR-0014: Resting is per child, not per machine; Back on Home points at All done

- Status: accepted
- Date: 2026-08-23

## Context

Matt's first hands-on session with the fresh image (2026-08-23): "once you pick
me on the front page, it doesn't seem like you can actually get back out."

That is by design — pressing a face starts the session, and the only exit from
Home is the All done tile, which runs the ending ritual — but the observation
exposed two defects:

1. **Sibling handover is broken.** Spec §7a rules "Sleeping ends at the start
   of the next allowed schedule window (or a new day if no windows) or on a
   Grown-up unlock", and `app._maybe_wake` implements it *for the machine*.
   So when child A presses All done at 16:10, the screen rests until the next
   window or tomorrow, and child B cannot start without a grown-up at the gate.
   P1 #10 ("instant switching, both of us") claims otherwise. The argument for
   the rule — "re-waking thirty seconds later would teach a child that the
   ending is negotiable" — is about the *same* child and says nothing about a
   different one.
2. **Back on Home is a dead end for a pre-reader.** It says "You're home." A
   five-year-old who wants out is given no action. Constitution #4: nothing
   essential is text-only, and an answer that names no action is no answer.

A third candidate — an undo of a wrong face pick from Home within the first
half-minute — was considered and rejected (below).

## Decision

**1. The "sitting is over" rule moves from the machine to the profile.**

- When a child's sitting reaches its end (Goodbye → `GOODNIGHT`, or a hard
  stop), that *profile* is **rested**: `rested_at` is persisted next to the
  day's usage. `Session.may_start` returns a new `StartRefusal.RESTED` for a
  rested profile until exactly the conditions that woke the machine before —
  a new budget day (04:00), the bedtime window that ended it is over, or the
  schedule window has changed. Order of refusals: BEDTIME, OUT_OF_HOURS,
  BUDGET_SPENT, RESTED (the sentence a child can act on wins, and "that's all
  the computer time for today" is truer than "resting" when both hold).
- **Who's here** shows a rested face dimmed (still ≥ 20 mm, still focusable,
  still spoken on hover: the name, then the resting line). Tapping it speaks
  the refusal — "kidnix is resting. Back after tea." in the same words the
  Resting screen uses — rate-limited by the existing `TapSpeechLimiter`, and
  **stays on Who's here**. No state change, no Sleeping.
- The machine-wide **Resting / Goodnight screen is only for "nobody can
  start"**: `_refuse` sends the shell to Sleeping only when *every* profile is
  refused; otherwise the line is spoken and Who's here remains.
- **Sleeping wakes to Who's here as soon as any profile may start**,
  evaluated on the existing tick and immediately on entering Sleeping. After
  A's Goodbye with a sibling who may start, the child sees Who's here with A's
  face resting — not the Resting screen.
- **One child ⇒ identical behaviour to today**: rested until the window/day
  rolls, the same Resting screen, the same words. The existing e2e flows
  (A19/A20/A21) must pass unchanged.
- The grown-up gate's "Start a session" still starts any child, rested or not:
  "anything sooner is the grown-up's decision" stands.

**2. Back on Home names the exit.** In `State.HOME`, Back speaks
"To finish, press All done." and draws the eye to the All done tile for ~2 s —
a soft ring that pulses, or, under reduced motion / calm mode, a static ring.
Nothing else changes: no navigation, no confirmation, the tile stays where it
is (§21.7).

**3. Rejected: a wrong-face undo from Home.** Back on Home must mean one
thing. The undo of "Who's here?" lives on S1b (Back → Who's here, clock
stopped), and a parent who sets `skip_next_choice` has chosen to lose it; the
gate is the other way. Making Back on Home an undo for the first 30 s and a
pointer afterwards would give one button two meanings over time, which is the
kind of hidden rule §7b forbids.

## Consequences

- `session.py`: `rested_at` in the usage state file, `StartRefusal.RESTED`,
  a pure `rested_until`-style predicate reusing `budget_day`, `is_bedtime`,
  `in_window`; `app._maybe_wake` asks "may any profile start?" via a helper
  that loads each profile's usage without swapping the live profile.
- `screens/whos_here.py` renders the rested state; `screens/home.py` gains a
  way to spotlight the All done cell; `app.on_back` uses it.
- New strings go through `N_()`; the pre-render sweep and po-extract pick
  them up; `docs/design/FLOWS.md` A1/A19/A20 and impl. notes updated; spec
  §7a's "Sleeping ends" ruling is amended to read per child.
- Tests: `test_session.py` (RESTED per profile; ordering), `test_state.py`
  (no new dead ends), `test_resting.py`, `test_profiles.py`, a Who's here
  rendering test, an `on_back`-on-Home test, and one new e2e flow: two
  profiles, A presses All done, Who's here returns with A's face resting, A's
  tap speaks the line and stays, B's tap reaches S1b.
- P1 #10's residual list gains nothing; its "instant switching" claim becomes
  true.
