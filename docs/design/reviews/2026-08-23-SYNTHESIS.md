# Expert panel review — chair's synthesis (2026-08-23)

Nine independent reviewers (CCI researcher; developmental psychologist; child
clinical/educational psychologist; child mental-health clinician; UK
early-years teacher/SENCO; children's-media UX designer; accessibility
specialist; child-safety/privacy expert; a four-parent panel) read the same
packet — constitution, research synthesis, spec, implementation notes,
checkpoint-1 audit, the shell source, manifests, and the real screenshots —
and wrote separate reviews under `docs/design/reviews/`. They also posted to a
shared forum (`2026-08-23-forum.jsonl`, 61 posts) so they could see each
other's findings. This is the chair's synthesis; the individual files are the
evidence and are more specific than this.

## 1. The verdicts, in their words

- **CCI researcher** — "the most carefully-reasoned child-facing shell I have
  read the source of — and not yet child–computer interaction research: an
  unusually good design rationale with zero children in it."
- **Developmental psychologist** — "the most developmentally literate
  children's system software I have read … what is wrong is arithmetic and
  hierarchy, not philosophy."
- **Child psychologist** — "ship it to one child, in the parent's presence,
  with the two blockers fixed first."
- **Mental-health clinician** — (forum) the ordinary 4 pm session ends in
  night vocabulary; the Sleeping screen makes demands of a dysregulated child.
- **Early-years teacher** — "conditional pass; the shape is better than
  anything I've used in a classroom and isn't on the market."
- **UX designer** — "structurally right, visually unfinished; two screens are
  broken on the panel we ship for; don't run the child test in this state —
  it would measure the missing icons rather than the design."
- **Accessibility specialist** — "conditional fail for a disabled child's
  first session; strong pass on the things most children's products get
  wrong."
- **Safety/privacy** — "conditionally excellent … ship it for Matt's own
  household; not yet for a second family."
- **Parents** — the machine-owned ending is "the thing I'd pay for"; the
  shipped PIN, one child per machine, a grid that changes, and no way out for
  the drawings are what stop them saying yes.

## 2. Where they converged (independent findings on the same defect)

| Finding | Who | Severity |
|---|---|---|
| **Session arithmetic**: ending windows are absolute (T−6/T−2) not proportional; `Session.start()` has no floor, so a late sitting can begin inside its own ending ("Let's keep that" over nothing, then goodbye) | dev-psych #14, child-psych #15, MH #46, Priya #59 | blocker |
| **"Finish this one" is a promise the clock doesn't keep** — both offer answers do the same thing | dev-psych #20, CCI #29 | blocker |
| **Activity icons are vendor logos**, drawn small; fallback collapses tiles to one pencil | CCI #19, teacher #35, a11y #37, UX #50 | blocker |
| **"All done" migrates** across the grid as tiles reveal; band offer *replaces* Undo/My Things at T−6 | child-psych #5, teacher #27, CCI #41, Dan #57, UX #55, teacher #61 | blocker |
| **Goodbye inverts the hierarchy**: the chosen destination is the smallest thing; the sun is full and high at Goodbye; no descriptive feedback; "Show a grown-up" hidden when nothing was made | dev-psych #24, child-psych #7, CCI #30, MH #28/#52 | blocker/major |
| **Night vocabulary at 4 pm** (moon, Goodnight, yawn earcon, "See you tomorrow") | MH #17, child-psych #31, teacher #34, dev-psych #47 | blocker |
| **Tux Paint's quit dialog is the save step**: ~20 px tick, a live "carry on" cross, another program inside the ritual | teacher #6, Dan #9, CCI #42 | blocker |
| **Shipped PIN 1234** suppresses its own warning; no way for a parent to change it | Mags #13, safety #44 | blocker |
| **Profiles are cosmetic** — one journal, one budget, one disclosure counter per machine | Priya #4, safety #18 | blocker (for a second child) |
| **No data exit** for parent or child (no export/delete); no retention cap | safety #10, Tom #16 | blocker (second family) |
| **Not keyboard/switch-operable** across two toplevels; gate keyboard route is a no-op; no captions for spoken-only lines; no calm mode; contrast failures on the band; Sleeping paints cream | a11y #8/#21/#22/#38/#39 | blocker (SEND) |
| **Locale is en_US** ("color"); GCompris tile still opens 198 activities; "Letter sounds" is an unverified phonics claim | teacher #3/#12 | blocker |
| **Research instrumentation on by default** (hover log, PIN attempts) in a persistent journal | safety #32 | major |
| **Update channel claims signing it doesn't verify** | safety #25, Tom #58 | blocker before any update button |
| **Nothing records the child's voice** — "tell me about it" on Let's keep that | teacher #11, (05 §3) | major, cheapest big win |
| **18 mm floor is a unit-conversion artefact**; Hourcade's 64 px was ~20–24 mm | CCI #53 | major |
| **Child-test method**: ABAB with the builder as rater can't answer P1; burst-click detector doesn't exist | CCI #54 | major |

## 3. Where they disagreed (recorded, not papered over)

- **Progressive disclosure**: the gap sweep (09 Q3) endorsed 5–6 growing to
  12; the teacher and Dan want it **off by default** ("a stable grid is
  worth more to every 4–6 year old than novelty"). *Chair ruling:* off by
  default, opt-in; All done pinned regardless.
- **The sun**: researchers say the antecedent cue is inert and Goodbye is the
  active ingredient; the sun is still worth keeping as *state* (and P1 tests
  it) — but effort shifts to Goodbye. *Ruling:* keep, one metaphor, held
  down through the ending; Goodbye gets the design weight.
- **Offer length**: child-psych wants 15–20% of the session; dev-psych warns
  shrinking it leaves one beat. *Ruling:* proportional with caps (2–4 min),
  two beats kept.
- **"Ask for more time"**: child-psych sees it handing the ending back to the
  parent. *Ruling:* keep, but it neither names the parent nor promises; the
  gate refuses sub-floor grants in words.
- **Tux Paint tick**: teacher/Dan want the cross gone; the implementer showed
  `noquit` loses work. *Ruling:* enlarge (buttonsize) now; the real fix is
  a shell-owned save for activities that can't save on signal (Journal already
  captures autosaves) — tracked.
- **Character/mascot**: UX asks for a decision; research (08 §3.7) is
  equivocal. *Ruling:* no character for v0.1; revisit after child test #1.

## 4. Decisions taken by the chair (recorded in spec §7d / ADR-0011 to follow)

1. Session floor 5 min; proportional windows with caps; refusal at Who's here
   before What's-next-after; sub-floor grants refused in the gate in words.
2. The offer is consequential: "Finish this one" defers put-away to T−1;
   "One last little thing" returns Home; words made true.
3. Goodbye led by the destination; descriptive feedback; "Show a grown-up"
   always; no return promises in daytime; sun held down through the ending;
   one sun metaphor.
4. Day vs bedtime vocabularies; Resting says *when* in child terms; Sleeping
   /Resting speech rate-limited and silent after repeated taps; screen dim.
5. All done pinned; disclosure off by default; band offer buttons ADD.
6. What's-next-after gains "Not sure yet".
7. Depictive icons for all tiles; thumbnail as corner badge.
8. Locale en_GB; GCompris tile → a one-level shelf of the 18; KLettres named
   truthfully; TuxMath/SuperTux out of the 4–6 band.
9. PIN: the starter PIN is detected and the gate forces setting one;
   parent.toml ships without a usable default as soon as the set-PIN flow
   exists.
10. Per-profile journal/budget/progress; parent export + wipe; journald
    retention cap; research logging off by default; signature policy on the
    device before any update button.
11. Accessibility: one key controller across both toplevels + focus on screen
    enter + real key-hold gate; caption strip driven off the speech hook;
    `calm = true`; earcon fades ≥ 150 ms; volume/mute control; contrast fixes.
12. Voice recorder (20 s) on "Let's keep that" and on Journal cards.
13. Target floor: 20 mm (Hourcade's physical figure), 24 mm preferred — ADR.
14. Child-test method: randomised alternating treatments, blind second coder
    from a screen+room recording, burst-click detector built first.

## 5. What the panel did NOT ask for (deliberately not doing)

A web browser, video, accounts, a reward economy, a chatbot, an AI reading
tutor, a character (for now), a parent surveillance dashboard.

## 6. Execution

Waves (disjoint file ownership): **A** shell session/ending/words/sun/All-done
/Not-sure (running); **C** image: locale, GCompris shelf data, KLettres,
TuxMath/SuperTux bands, Tux Paint buttonsize, signature policy, journald cap,
export/wipe helpers, PARENTS.md (running); **D** ten depictive icons
(running); **B** accessibility (keys, captions, calm, contrast, sound) and
**E** voice recorder + Undo routing + per-profile paths + PIN flow + shelf
rendering (after A lands). Then rebuild → e2e → checkpoint-2 mini-audit against
this list → child test #1.

## 7. Questions the panel asked Matt (for when you're back)

- Whose journal is it as the child ages (when does the child get delete)?
- Is hover-speech logging research or product? (Ruled: research, off by default.)
- Character or not? (Ruled: not yet.)
- How much delight is the product allowed? (UX: "every individually-correct
  restraint sums to a screen a five-year-old has no reason to look forward
  to.") — I'd like your view.
