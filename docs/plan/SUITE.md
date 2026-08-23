# The kidnix suite — what a child can do, and in what order we build it

> Thinker's plan, 2026-08-23, after checkpoint 1, the expert panel and
> research 10 (early reading & writing). Matt's steer: a fully fleshed-out
> system of separable apps; reading and writing first and done properly;
> prioritise between wide-and-shallow and narrow-and-deep.

## 0. The decision: narrow-and-deep on literacy, thin-and-solid everywhere else

Why: the literature says apps move *constrained* skills (phonics, key-finding,
number bonds) and almost nothing else; the best-evidenced reading-software
feature is narrated decodable text; and the one clear moderator of digital
phonics outcomes is **adult interaction** (GraphoGame meta-analysis: g = −0.02
overall, **0.48** with high adult interaction; EEF's own trial −1 month with
teachers calling it "highly engaging"). So the deep vertical is a **co-use
tool**, not a solo game, and everything else on the machine should be simple,
honest and stable rather than many half-built toys.

## 1. The suite (v1 → v3)

| Tile (child sees) | What it is | Build or curate | Depth | Status |
|---|---|---|---|---|
| **Draw** | Tux Paint, tuned (fewer tools, bigger buttons, en_GB) | curate | thin | shipped |
| **Sounds & Words** | the literacy suite (research 10): Hear it → Find it → Blend it → Read it (v1); Spell it, Write it, My name (v2) — one predictable 8–12 min loop, parent sets the school's scheme + last grapheme as a hard ceiling | **build** | **deep** | weeks 1–3 built (corpus, ceiling, Find it, Blend it); image install + phoneme clips in progress; Read it next |
| **Letters & numbers** | GCompris, as a one-level shelf of 18 curated activities | curate | thin | wired (wave C) |
| **Potato faces** | KTuberling | curate | thin | shipped |
| **Copy the lights** | Blinken | curate | thin | shipped |
| **Clock & time** | play-with-the-clock toy + routine strip + "how long is a minute" (Matt's idea; Y1/Y2 time) | build | medium | in progress (SDK) |
| **Numbers** | subitising & bonds to 5/10 built to the ELG (05 §3) | build | medium | P1 |
| **Photos** | webcam → Journal, caption/voice | build | thin | P1 |
| **Letters to family** | picture + caption + voice to a parent-approved recipient; the reply comes back into the Journal | build | medium | P1 (the strongest activity in 05) |
| **Listen** | read-to-me: narrated decodable/picture books (shares Read it's engine), family-recorded stories; screen dim | build | medium | P1 |
| **Music** | pentatonic xylophone/loops, save to Journal | build | thin | P2 |
| **Make a game** | TurboWarp (offline Scratch) for 7+ | curate | thin | P2 |
| **Jump and run / Mini golf** | SuperTux (7+), Kolf | curate | thin | shipped |
| **Library** | kiwix-serve + no-navigation viewer | curate | thin | P2 |

Cross-cutting, built once and used by all: **voice note** ("tell me about
it", 20 s) on Let's keep that and Journal cards; **captions** for every spoken
line; **print** from the Journal; **calm mode**.

## 2. Activities are separable apps: the contract

Each first-party activity is its own package (later its own repo) that the
shell launches like any other program. The shell owns: launch, the band, the
session, the Journal import, read-aloud of *its* chrome. The activity owns
its window and its content. Contract (`docs/design/activity-sdk.md` to write):

- **Manifest** (TOML, already exists): id, name, audio_label, icon, exec,
  exec_resume, category, age band, goal (honest line), `quit`/`quit_grace`,
  `undo_key`, `journal_watch`/`journal_glob`, `content_required`, `kind`
  (activity | shelf), `network_required` (always false for us).
- **SDK (Python, `kidnix_activity`)**: a full-screen GTK4 window factory
  with the kidnix theme tokens, mm-based metrics, read-aloud helper
  (speech-dispatcher + the caption hook), earcons, a Journal writer
  (`save_entry(kind, files, caption, voice)`), a "grown-up turn" prompt
  widget, calm-mode and age-band accessors, and the input rules (press-only,
  no right-click/double-click, big targets) baked into the base widgets.
- **Tests**: each activity ships headless tests and one e2e step (launch →
  make → Journal entry) the shell's e2e can include.
- **Packaging**: RPM later; for now a Python package installed into the image
  like the shell; third-party activities stay upstream RPMs.

## 3. Sounds & Words — the v1 plan (4–6 weeks of one implementer)

From research 10 §7.1: week 1 corpus + ceiling (Letters and Sounds 2007 OGL
sets, word/caption banks, tricky words → TOML; Reading Framework Appendix 7
as a unit-test fixture; parent sets scheme + last grapheme); week 2 **Find
it** (screen + keyboard, lowercase, GCompris a–z voices + ~20 recorded digraph
clips); week 3 **Blend it** (sound buttons dot/bar, push-together slider);
week 4 **Read it** (~12 authored decodable texts Phases 2–3, Piper narration,
optional word highlighting, zero hotspots); week 5 Leitner schedule + the
three-pane parent view (no scores/ages/percentiles; an honesty paragraph);
week 6 **Hear it**, accessibility, image tests, the "what this is not" page.
Design rules: letter *names and sounds* (Piasta 2010), never auto-correct,
handwriting stays on paper and the product says so, the school decides the
next GPC, the child says words aloud to a person (no ASR grading, ever),
every loop has a **grown-up turn** because the evidence says the adult is
the active ingredient. Evaluation: within-child multiple baseline across GPC
sets; falsifiers stated in advance (research 10 §7.2).

## 4. Order of work (after the panel's fix waves land)

1. Panel fix waves A–E + rebuild + e2e (this week).
2. Activity SDK skeleton extracted from the shell's widgets/metrics/speech. **(done: kidnix_activity v0 + caption listener)**
3. **Sounds & Words v1** (weeks 1–6), with the voice note and captions
   landing in the shell in parallel.
4. Clock & time; Numbers; Letters to family; Listen (P1, in that order —
   Clock first because it's small and Matt asked; Letters to family early
   because purpose + audience is the literacy engine).
5. Parent panel v0 (PIN on first boot, profiles, time, allow-list, "keep the
   grid", volume, export) — in parallel with 3 because it unlocks every
   parent in the panel.
6. Child test #1 after waves A–E and the icon probe; P-protocols after.

## 5. What we are saying no to (still)

A browser, video, accounts, a store, a reward economy, AI in the child
session, claiming to teach reading, grading oral reading, replacing
handwriting, a dashboard of the child.
