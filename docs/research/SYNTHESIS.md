# kidnix — research synthesis → product requirements

> Thinker's synthesis of `docs/research/01–08` (≈60k words, ~450 sources),
> written 2026-08-22. Where this document and a research doc disagree, the
> research doc is the evidence and this document is the judgement call; say
> so in an ADR if you change one. Section references like *07 §2.3* point into
> the research docs.

## 0. The thesis in one page

**Parents are not unaware; they are unserved.** 93% of UK parents know
parental controls exist, ~35% use the built-in ones, and 75% of US parents of
0–8s use no screen-time tool at all (*04*). Ages 6–7 are the peak window where
parents act (built-in control use jumped 36%→50% in a year). The problem is
friction and trust, not education.

**Every general-purpose OS leaks, and the leak list is public** (WebViews,
accessibility menus, recovery mode, clock changes, "parental control bypass"
CVEs). The most-praised system in the market — Nintendo's — wins on
*architecture*: enforcement below the user session, reporting over
restriction, soft stops with grants (*04*). An immutable OS whose policy
engine sits below the child's session, with no general web renderer and no
reachable escape hatch, is the single most defensible technical claim kidnix
can make — and **nobody has built it**: GNOME 50 (March 2026) shipped child
screen-time limits, bedtime schedules and a web-filter backend; no kids
edition exists anywhere in the atomic/immutable ecosystem (*04 §5*).

**The field has moved from "how long?" to "what, with whom, instead of what,
and designed how?"** (AAP 2026 "5 Cs", UK EYSTAG March 2026; *02*). Nobody can
evidence a time threshold; the defensible precaution is ~30-minute sessions
within ~1 h/day at this age. The best-evidenced design interventions are:
natural stopping points, **the machine (not the parent) ending the session**
(Hiniker 2016, p=.006), no autoplay, no manipulative design (present in 80% of
apps preschoolers use), rewards = the artefact, not points (*02*).

**The child–computer-interaction evidence is unusually concrete** (*01, 06,
08*): 4-year-olds hit 16 px targets 43% of the time and 64 px (≈18–24 mm) 90%;
no double-click, right-click, long-press, scroll or chording; flat one-level
navigation on a spatially stable grid; ≤5 primary choices per screen; icon +
label + audio on everything; universal undo; no confirmation dialogues; no
speech *input* (child ASR WER 9–35%); representational icons not glyphs;
Andika/Atkinson Hyperlegible type (dyslexia fonts don't work — 2026
meta-analysis). Sugar's Journal (auto-keep, resume-not-open, temporal order)
is "the one great uncopied idea" in kids' shells; Sugar failed on navigation,
not philosophy (*08*).

**Regulation points the same way** (*03*): ICO Children's Code (now
statutory), GDPR-K, DSA minors guidelines, COPPA 2025 — high privacy by
default, data minimisation, no nudges, no profiling, best interests of the
child. A local-only, no-account, no-egress OS with exportable data is in the
easiest legal posture there is. The real legal trap is *licensing* of bundled
voices/content, not privacy. California AB 1043 (Jan 2027) obliges OS vendors
to emit an age-bracket signal — worth adopting voluntarily. **No conversational
LLM for this age group**: EYSTAG, FTC 6(b) orders, Common Sense "Unacceptable"
(*06 §e, 02, 03*).

**Technically it is buildable now** (*07*): Fedora 44 / GNOME 50, gnome-kiosk
50 as compositor, GTK4+libadwaita (PyGObject) shell, RPM-first activities
(GCompris 26.1, Tux Paint, KTuberling, kiwix-tools are in Fedora),
speech-dispatcher + espeak-ng baseline with Piper `en_GB-cori-high` as the
quality voice, nftables `meta skuid` egress block, greenboot-rs rollback, bcvk
for unprivileged VM testing, QMP screendump + ydotool for UI tests.

So: **build a thin layer — shell, session model, Journal, parent app — over
upstream GNOME primitives, on an immutable base, and ship it while the field
is empty.** Don't fork the desktop; don't build a theme-plus-package-list;
don't build surveillance; don't promise educational outcomes — promise a good
experience of computing.

## 1. What modern families need (ranked, with evidence)

| # | Need | Evidence | kidnix answer |
|---|---|---|---|
| 1 | **Set it up once and trust it** — controls that don't need weekly admin (75% use none; 33% feel judged) | 04 §4 | Allow-list of ≤12 activities, session/schedule shape set once; no dashboard to tend |
| 2 | **Enforcement that actually holds** — no bypass via browser/settings/recovery | 04 §5, 03 | Immutable root; policy below session; no web renderer; nft egress block by UID |
| 3 | **Endings without tantrums** | 02 §2.7, 01 #27–32, 08 §4.7 | Machine-owned, predictable, ritualised ending at a natural boundary; no adult-voiced "2 minutes!" |
| 4 | **Creative, not passive** (65% of 3–7s already draw on devices; parents name creativity as top benefit) | 04 §7, 02 §19 | Default state is *making*; Journal shows what was made |
| 5 | **No ads, no purchases, no data collection** (73%/72% worry) | 04, 03 | Zero telemetry, no store, no accounts; exportable data |
| 6 | **Multiple children, one device** (39% of UK primary families share) | 04 §5.6 | Instant profile switching, colour = whose |
| 7 | **Works offline / no server dependency** | 04 don't #9 | Everything local; Flatpak/updates are parent-driven |
| 8 | **Co-use that fits real life** — invited, never required | 02 #11–12 | "Grown-up turn" moments, journal as the 5-minute co-use surface, letters-to-family |
| 9 | **An adult mode the adult can use** (Sugar's fatal wound) | 04 don't #16, 08 §2.1 | Stock GNOME session for the parent on the same login screen |
| 10 | **Longevity and open formats** ("still works in ten years") | 04 takeaway 8 | Open source, bootc, PNG/OGG/TXT in the Journal, export |
| 11 | **Screen-off story mode** (Yoto/tonies market; 3–7s most likely to listen to audiobooks) | 04 §5.7 | Later: "Listen" activity with screen dimmed, family-recorded stories |
| 12 | **Teaches real computing** — real keyboard/pointer, graduates up not sideways | user goal; 04 §5.10 (Flip-to-Hack) | Real programs, real input; later: "flip to see how it works" |

## 2. Design principles (consolidated — the constitution, with sources)

These are the requirements every shell/activity PR is reviewed against. Each
cites its evidence; AGENTS.md §3 is the short form.

### A. Input & targets (01 #1–10, 06 §3, 08 §3.1)
- A1. Minimum interactive target **18 mm** (≈64 px @ 96 dpi; 44 CSS px absolute floor); primary tiles **40–60 mm**; ≥ 8–12 mm gaps. Specify in mm, compute from DPI.
- A2. All mouse buttons do the same thing on primary controls; **no right-click menus, no double-click, no long-press-as-sole-route, no chording, no modifiers, no multi-touch**.
- A3. Input registers on **press**; every control is idempotent under burst-clicking (8 clicks/s); debounce don't queue.
- A4. **No free scrolling in the shell**; paginate with big page dots/arrows.
- A5. Drags short, with pick-up/drop state cues and a click-move-click fallback.
- A6. Keyboard never required to reach/leave any shell surface.
- A7. OS pointer settings for the kid session: double-click 700 ms, drag-threshold 16 px, flat accel, cursor-size 48, no natural-scroll surprises (06 §3); **trackpad hardening**: tap-to-click off, gestures and two-finger scroll off at the libinput/mutter level, palm rejection max, disable-while-typing on; tent mode is the recommended touch-first posture for 4–6 (*09 Q7/Q8*).

### B. Navigation, layout, text (01 #11–21, 08 §3–5)
- B1. **Flat, one level deep, spatially stable**; no menus, no hamburgers, no folders, no search box.
- B2. Home grid **ceiling 12 tiles** on one page (justified by geometry and visual search, not working memory — WM limits bind on *held* option sets, not a visible, labelled, spatially stable grid; Pailian 2016, Schneider 2021 inverted-U with ~4 optimal mediated by *affective* load); **first-run default 5–6 tiles**, growing toward 12 as the child uses the system (progressive disclosure). Dialogs/choice screens: ≤ 5 choices. (Revised at checkpoint 1; *09 Q3*.)
- B3. Fixed **band** at the top (Back · Undo · My Things · sun/timer · Ear · Ask · Grown-up) on every surface; never hides.
- B4. **Icon + label + audio, always** — representational icons (a paintbrush, not a glyph), label ≥ 18 pt, tap/hover reads aloud; "Ear" repeats the last utterance. Hover dwell **450 ms with a pointer-velocity settle gate** (no child evidence exists for hover read-aloud; Paulus & Remijn 2021 extrapolated; instrumented for P5). Earcons: prefer representational auditory icons where a referent exists (Jacko 1997 — recognition driven by everyday-sound exposure); the soundscape is extrapolation and says so.
- B5. Instructions audio-first, ≤ 2 sentences, ≤ 12 words, imperative; **demonstrate with a looping animation** rather than describe; every spoken thing paired with a visual highlight.
- B6. Type: **Andika** (child-facing) / **Atkinson Hyperlegible**; no dyslexia fonts. Colour never the sole carrier of meaning (≈8% of boys colour-blind, mostly undiagnosed). **Colour = whose (child identity), shape = what.**
- B7. Visual quiet: one focal region, ≤ 2 animated elements, no ambient loops, no music under speech (EYSTAG slow-content rules applied to the chrome).
- B8. Age-band finely (4–5 vs 6–8); children reject content pitched one band younger.

### C. Recoverability (01 #22–26, 08 §4.8)
- C1. **Universal undo** in a fixed band position; **continuous autosave** to the Journal; no save dialogues.
- C2. **No modal text confirmations**; destructive actions are spatial and recoverable (a bin that keeps things ≥ 30 days); effectively **no delete** for the child.
- C3. No adult-style error messages: return to a known-good state with a friendly line; log detail for the parent only.
- C4. Burst-click on a non-target = usability alarm → proactive help (highlight target, replay instruction).

### D. Sessions & endings (02 #1–10, 17–18; 01 #27–32; 08 §4.6–4.7)
- D1. Default session **20–30 min** (parent-configurable 10–45); soft ceiling ~1 h/day; bedtime lockout; schedule windows that match household boundaries. State honestly that no number is evidenced.
- D2. **The machine ends the session**, never the parent; consistent character/ritual; never "your mum said stop."
- D3. Ending is **predictable and in-experience**: a glanceable ambient state, **not** a digital countdown, **not** a modal "2 minutes left". The sun is *state*, not a warning and not the mechanism that buys calm (four JABA single-case experiments: advance notice/visual schedules are inert on their own; Castillo 2018: the aversive event is the drop in reinforcement density at the destination). Encode depletion as **shrinking area / falling height**, not left-to-right travel (the directional mental timeline isn't reliable before ~6; Tillman 2018). (*09 Q1*.)
- D4. Session end **rounds to a natural boundary**: T−6 min *Ending offer* ("finish this one / one last little thing / ask for more time"), T−2 min *Put away* (work animates into Journal), *Goodbye* (what you made today; show a grown-up; **the offline continuation the child chose at session start** — Coco's Videos (Hiniker et al. CHI 2018, 24 families, 3–5 yr, randomised order): a pre-chosen next activity made endings work; the shell shows it back: "Ready to [thing]?"). A *What's next after?* picture choice (6–9 parent-configurable options) sits between Who's here and Home. (*09 Q6*.)
- D5. **Child-initiated ending is first-class** ("I'm finished" runs the same dignified ritual; never "are you sure?", never a bribe to stay).
- D6. **No autoplay, no up-next, no notifications, no streaks, no daily rewards, no parasocial pleading, no fabricated time pressure, and no exit friction of any kind** ("the easy way out", Kuo, Zhao & Scott 2026). Coco's: post-play/autoplay is unambiguously harmful (p<.001; 71% of parents against, 0% for); children ended early 31% of the time (D5 is normal, not exceptional); a hard lock-out was **no better** for the child than a plain home button — Sleeping is parent-side enforcement, not child-side kindness. The system has no interest in whether the child comes back.
- D7. Grants: parent-side +5/+15/+30 (Nintendo pattern) via the Ask flow; soft stop, not hard cut.

### E. Reward, motivation, content (02 #8–9, 14–16, 19; 05)
- E1. **Reward = the artefact** in the Journal + specific descriptive feedback ("you used five colours"). No points, coins, stars, badges, levels, scores, leaderboards.
- E2. Coherence principle: no celebratory bells/whistles unless they serve the activity's goal; default none.
- E3. Interaction is contingent and consequential (choices with consequences, not stimulus–response taps).
- E4. Every activity has a one-line honest goal visible to the parent, including "this one is just for fun".
- E5. Educational/creative types are the default; passive video is a minority mode, off by default.

### F. Journal (08 §4.3, 01 #33, 04 §5.9)
- F1. Auto-keep everything; **resume-not-open**; temporal grouping (Today / Yesterday / Before); thumbnail-dominant cards ≥ 20 mm; activity icon + colour in the corner; spoken day headings.
- F2. A small, bounded **favourites shelf** the child curates; temporal falloff; no search.
- F3. Card actions: Show a grown-up / Print / Send to family / Put away. Versions kept.
- F4. A boring conventional file view for the adult (Sugar's most repeated complaint) — open formats (PNG/OGG/TXT/JSON), exportable.

### G. Parent side (04, 02 #20, 03 checklist)
- G1. Controls set the **shape** of the sandbox (children, time, activities, requests, their things, family recipients, calm mode) and get out of the way; **no engagement metrics, no surveillance**.
- G2. Parent gate = 3-second hold on a plain corner tile + PIN; adult typography; **never an arithmetic gate; silent, free, un-penalised failure; attempts logged for the parent only; the gate is not voiced** (RCT n=554, mean age 4.3: locks deter above chance but a majority still try to bypass — so the gate is a speed bump, the lockdown below the session is the wall; *09 Q8*).
- G3. **Ask a grown-up** replaces every silent denial: three picture-button taps (+ optional voice note), non-blocking, answered asynchronously (incl. by the parent's recorded voice); outline-only tiles for not-allowed activities open the Ask flow.
- G4. Parent can **see, export and delete everything**; nothing leaves the device; the parent's own stock GNOME session is on the same login screen.
- G5. Parent drives updates (`bootc upgrade` from the panel); never a surprise reboot mid-activity; auto-rollback on failed health checks.

### H. Privacy, safety, legal (03 §3 checklist — 41 items; highlights)
- H1. **No network egress from the child session by default** (nftables by UID + Flatpak `--unshare=network` + NM polkit deny). Any future online feature is an explicit allow-list at the network layer, never a browser with a filter.
- H2. Zero telemetry, no accounts, no profiling, no nudges; best interests of the child recorded as the primary design consideration.
- H3. **No conversational/generative AI** in the child-facing system (on-device or cloud). Deterministic TTS read-aloud is fine. Revisit annually against EYSTAG/FTC.
- H4. Emit a coarse age-bracket signal (AB 1043 pattern) for any activity that asks.
- H5. Licensing ledger for every bundled font/voice/content item (`docs/LICENSES.md`); Piper `en_GB-cori` (public domain) is the only clean high-tier en_GB voice; avoid CPML/NC models.
- H6. Accessibility: WCAG 2.2 AA colour/contrast, reduced-motion honoured, one **calm mode** (autism-friendly = distraction-reduced), switch/dwell later.

### I. Engineering (07 §3, AGENTS.md §5)
- I1. Enforcement lives **below the session** in the image: immutable root, policy in `/usr`, first-boot idempotent units for `/var` state.
- I2. Thin layer over upstream: consume GNOME 50 parental-control primitives (malcontent 0.14 as policy record; kidnix enforces), don't fork the desktop.
- I3. Every feature proven by an image test, a boot test, or a shell test in CI.

## 3. The numbers (quick reference)

| Quantity | Value | Source |
|---|---|---|
| Min target | 18 mm / 64 px (44 CSS px floor) | 06, 01 |
| Primary tile | 40–60 mm; 160×160 px tiles + 40 px label in the proposed IA | 01, 08 |
| Gap between targets | ≥ 8 mm (12 mm preferred) | 08, 01 |
| Band height | 96 px, top of screen | 08 §5.2 |
| Max choices/screen | 5 (4–6 yr); ≤ 12 home tiles total, one page | 01 |
| Label size | ≥ 18 pt | 01 |
| Feedback latency | ≤ 100 ms; progress indicator > 1 s | 01 |
| Double-click interval / drag threshold / cursor | 700 ms / 16 px / 48 px | 06 |
| Session default / range / daily ceiling | 25 min / 10–45 / ~60 min | 02 |
| Ending offer / put away | T−6 min / T−2 min | 08 |
| Bin retention | ≥ 30 days | 01 |
| Pointing throughput | 4 yr 1.95, 5 yr 3.24, adult 7.8 bits/s | 06 |
| Child ASR WER | 9–16% (fine-tuned, 8–11 yr) to ~35% (kindergarten) | 06, 01 |
| Parents using no tools (US, 0–8) | 75% | 04 |
| Preschool apps with manipulative design | 80% | 02 |
| Reference device | refurbished ThinkPad T480, £150–320; floor 4 GB/64 GB, rec 8 GB/128 GB | 06 |
| Activity disk budget | ~3.4 GB for the full wave; plan core vs full images | 07 §4.12 |

## 4. Learning science → activity design (from 05)

Headline: **match the school, don't compete with it.** UK statutory documents
(EYFS ELGs, KS1 programmes of study, validated SSP phonics schemes, DfE
screen-use guidance now referenced by the EYFS framework) are specific enough
to design against. kidnix's job is practice, application and pleasure — not
first teaching. Apps move *constrained* skills (phonics, key location, number
bonds; Kim et al. 2021 g ≈ 0.31, shrinking under standardised outcomes), not
unconstrained ones (comprehension, composition) — so never claim "teaches
reading", cognitive transfer from music (ḡ ≈ 0) or coding.

Per-activity rules (05 §3):
- **Draw/paint**: big canvas, ≤ 8 tools visible, finger/mouse first; **caption
  field + "tell me about it" voice recorder on every drawing** (cheapest
  literacy win); stamps one level down; no grading.
- **GCompris**: a **curated shelf of 12–20 activities** mapped to EYFS/KS1,
  grouped by what the child *does*; en-GB; check letter activities against a UK
  phonics progression before exposing; never "100 activities!".
- **Keyboard game**: *find the key that makes this sound* — lowercase
  graphemes, phoneme or letter-name mode, any finger, no posture scolding, no
  WPM, no streaks; tell parents it does not replace handwriting. No home-row
  touch typing at 5–7 (no RCT below 8; d = 0.27).
- **Story-maker**: picture first, words second; three caption routes (type /
  record voice / grown-up scribes); never silently correct spelling; "say your
  sentence out loud first"; **finish by publishing to somebody**.
- **Music**: no notation; pentatonic/Orff set so nothing sounds wrong; 4/8-beat
  loops; 3–5 layers; instant sound; save to Journal; claim joy, not IQ.
- **Block coding**: pictorial blocks, 3–8 blocks is a program; sandbox over
  level ladder; celebrate the debugging loop, never a red error; paint editor
  inside; **printable unplugged companions** (physicality g = 0.72 vs 0.44;
  unplugged g = 1.03).
- **Photos**: one enormous shutter, instant Polaroid-style result into the
  Journal, caption/narrate; prompt cards; no face detection/auto-tagging.
- **Letters to family**: **the strongest activity in the list** (purpose +
  audience is the EEF's named mechanism). Real named recipient with photo;
  picture + caption + voice; **the reply must come back into the Journal**;
  invented spelling untouched.
- **Offline library**: two shelves — *Books I can read* (decodable, phonics
  phase set once by parent) and *Books to me* (rich language, narrated with
  congruent illustration and optional word highlighting). **Zero hotspots,
  mini-games or tap-a-word dictionaries** (Takacs, Swart & Bus 2015 — the
  clearest negative finding); no "books read" counter.
- **Add** (evidence-supported, missing from the original list): *read-to-me /
  I-read-to-you recording loop*; *subitising & number bonds to 5/10 built to
  the ELG*; *printable unplugged companions*; *dialogic prompt layer over the
  library*; *oral storytelling recorder with picture prompts* (developmentally
  ahead of a typing-based story tool at 5).
- General: **guidance/scaffolding helps most for the youngest** (d ≈ 0.5–0.7)
  — scaffold heavily, fade deliberately, don't design for struggle; no
  over-engineered adaptivity; no background music under narration; never
  position kidnix as a way to occupy or calm a child (DfE guidance forbids).

## 4b. Checkpoint 1 (2026-08-22)

Adherence audit: `docs/design/cci-compliance-audit-2026-08-22.md`. Gap sweep:
`docs/research/09-gap-sweep-checkpoint-1.md` (its §10 edits are applied above;
its §11 child-test protocols P1–P6 are adopted in `docs/plan/CHILD-TEST-PROTOCOL.md`).
Settled enough to stop re-litigating: no autoplay/up-next; no scrolling/paginate.
Still genuinely unknown (test with children): visible sun help/hurt; hover dwell;
Journal comprehension/resume; pointer device on the real hardware; ending ritual
as an anticipated object. No IDC/CHI/IJCCI paper 2024–26 describes a kids' OS,
launcher or kiosk shell — the field is still empty.

## 5. Decisions taken (ADRs) and pending

Taken: ADR-0001 bootc image; ADR-0002 agent roles; ADR-0003 stay on
`ublue-os/base-main:44` for v0.1 with revisit triggers.

Pending (to be written after the current spikes report):
- ADR-0004 **Shell technology**: GTK4 + libadwaita via PyGObject (07's pick:
  native portals, `python3-speechd`, AT-SPI tree, smallest delta), runner-up
  WebKitGTK web shell (Playwright testing, richer motion). Leaning GTK4/Python.
- ADR-0005 **Parent experience**: stock GNOME session for `parent` on the same
  GDM screen (04 "don't build an interface the adult cannot use"; Endless "95%
  GNOME OS") + a kidnix parent-panel GTK app; consume GNOME 50's parental
  controls rather than rebuild them.
- ADR-0006 **Activities packaging**: RPM-first from Fedora repos, Flatpak via
  first-boot for the rest, GCompris voices pre-seeded at build time.
- ADR-0007 **Dev loop**: bcvk ephemeral VMs for PR-time boot tests; full qcow2
  nightly; image-builder (bib successor) for ISO.
- ADR-0008 **TTS**: speech-dispatcher + espeak-ng guaranteed; Piper
  `en_GB-cori-high` behind a flag via resident server.
- ADR-0009 **No generative AI in the child session** (explicit, with revisit triggers).

## 6. Open questions to test with a real child (not answerable from literature)

1. Does a continuously visible sun/timer reduce or increase end-of-session distress vs. no visible timer? (Hiniker's warning finding was about *adult verbal* warnings.) A/B with the family.
2. Does a 5–6 year old understand the Journal's temporal grouping and "resume" semantics? (No published usability evidence for the journal model.)
3. Is the "Ask a grown-up" flow used, ignored, or abused?
4. Is GTK4's animation vocabulary rich enough for the spatial transitions BBC GEL recommends, or do we need the web-shell runner-up?
5. Mouse vs trackpad vs touchscreen on the actual hardware with the actual child — which do we optimise the first tiles for?
6. Uppercase vs lowercase labels/keys for a Reception/Year-1 child (UK phonics teaches lowercase first).

## 7. Top risks

- **Enforcement claims vs reality** (04 don't #19): VT switching, keybinding escape, audio cap, greenboot rollback all need VM/hardware verification before we tell any parent "it holds".
- **Scope creep into a desktop**: resist every "just add a browser"/"just add YouTube Kids". The value is the shell + session + Journal + parent app.
- **Licensing** of voices/content (03).
- **Base image lifecycle** (ADR-0003 triggers).
- **Our own motivated reasoning** about what a 5-year-old will do ("do not assume the child will create" — 04 don't #17). Design guardrails for consumption first, make creation the easy adjacent step, test early.
