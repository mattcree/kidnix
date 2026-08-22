# kidnix — CCI compliance audit, 2026-08-22

> Auditor's report (Claude Opus 5), 2026-08-22. A checkpoint on whether what we
> have **built** adheres to the child–computer-interaction evidence we
> **gathered**. Read `docs/research/SYNTHESIS.md` first; this document assumes
> it.
>
> **Scope of the build audited:** shell v0.1.1 + the two-bug pass
> (`docs/design/shell-v0.1-implementation-notes.md` §15), the ten shipped
> activity manifests, `/etc/kidnix/session.toml`, `/etc/kidnix/parent.toml`,
> the kid dconf profile, the generated `/etc/tuxpaint/tuxpaint.conf`, and the
> e2e evidence in `output/e2e/`.
>
> **Known in-progress fix, excluded from scoring:** *label ellipsis*. The
> contact sheet (`docs/design/screenshots/e2e-contact-sheet.png`) shows
> "Letters & n…", "Number ga…", "Copy the li…", "Jump and r…" — a direct B4
> violation. `shell/kidnix_shell/widgets.py:143` (`fit_gtk_label`) and
> `labels.py` already set `Pango.EllipsizeMode.NONE` with wrap-then-shrink, so
> another worker is landing this. Rows that would otherwise be MISSING for that
> reason are marked **(fix in flight)**.

---

## 1. Method

**What I read.** `AGENTS.md` §3; `SYNTHESIS.md` §§0–7 in full; the numbered
guideline sections of `01-cci-foundations.md` §3 (45 items) and §4;
`02-development-and-wellbeing.md` §3 (20 items) and §4;
`06-input-accessibility-hardware-ai.md` §2.7, §3, §4, §7 (the 40 numbered
SPECS) and §8; `08-shell-ux-patterns.md` §3 (numbers), §4 (13 patterns), §5.1–5.4
(IA, band, screens) and §7; `05-learning-science.md` §3 (per-activity) and §4;
`03-regulation-and-privacy.md` §3 (41-item checklist).

Then the build: `docs/design/shell-v0.1.md` including §7a, the implementation
notes (all 15 sections), and the code — `metrics.py`, `widgets.py`, `band.py`,
`session.py`, `ritual.py`, `journal.py`, `speech.py`, `launcher.py`,
`activities.py`, `settings.py`, `suggestions.py`, `sound.py`, `theme.css`,
`app.py` and every file under `screens/`. Then the config surface:
`system_files/usr/share/kidnix/activities/*.toml`,
`system_files/etc/kidnix/session.toml`, `system_files/etc/kidnix/parent.toml`,
`system_files/usr/share/kidnix/dconf/kid.d/*` and its `locks/`,
`build_files/50-activities.sh` (which writes `/etc/tuxpaint/tuxpaint.conf`),
`build_files/36-fonts.sh`, `docs/LICENSES.md`. Then the spikes
(`lockdown`, `hardening`, `e2e-scenario`, `session-integration`,
`activities-packaging`, `tts`, `parent-desktop`). Then the images:
`docs/design/screenshots/{e2e-contact-sheet,demo-home,boot-home}.png` and all
twelve frames in `output/e2e/`.

**How I judged.**

- **Physical, not nominal.** Every target claim is recomputed in millimetres
  from `metrics.py` at the panel the e2e run actually uses — **1280×800 @
  102 dpi**, which `metrics.for_screen` resolves to `fit = 0.83`. At that fit,
  `px_per_mm = 4.016`, so: tile `141 px = 35.1 mm`; `gap = 40 px = 9.96 mm`;
  `min_target = 60 px = 14.9 mm`; `band_height = 85 px = 21.2 mm`;
  `band_target = 65 px = 16.2 mm`; `band_small_target = 50 px = 12.4 mm`;
  `card_size = 177 px = 44.1 mm`; `avatar = 195 px = 48.6 mm`; pager arrow
  `85 px = 21.2 mm`; ritual buttons `200 × 100 px = 49.8 × 24.9 mm`. The same
  arithmetic at 1920×1080 @96 (`fit = 1.0`) gives tile 42.3 mm, gap 12.2 mm,
  `min_target` 18.0 mm, band 25.4 mm, band button 20.1 mm. **Both numbers are
  quoted where they differ across the pass/fail line**, because the reference
  device (`06 §3.1`, a refurb T480) is 1080p and the VM we test on is not.
- **Contrast computed, not eyeballed.** WCAG relative-luminance arithmetic on
  the literal hex values in `theme.css`.
- **Screenshots as primary evidence** where the code cannot settle it (the Tux
  Paint quit dialog, the absent band during an activity, label truncation).
- **Status vocabulary.** MET = the build does the thing. PARTIAL = does part,
  or does it on some surfaces/panels only. MISSING = does not, and the
  guideline applies now. UNKNOWN = not measured by anyone; I will not guess.
  N/A-yet = the surface the guideline governs does not exist in v0.1 and is
  scheduled (Ask queue, parent panel, multi-child, printing, letters).
- **Priority.** P0 = fix before the first child test, because it will either
  invalidate the test or hurt the child's experience of it. P1 = before any
  second family sees it. P2 = before a public claim.

**What I could not verify.** Whether the earcons are pleasant on real
speakers; the actual read-aloud rate in words per minute; whether GCompris's
pre-seeded voices really play offline; whether the nftables egress block holds
under a packet capture (it is asserted structurally, never observed —
`docs/spikes/lockdown.md` §3); touch behaviour of any kind.

---

## 2. The table

### 2.1 `01-cci-foundations.md` §3 — the 45 design guidelines

| ID | Guideline (short) | Status | Evidence | Action (owner) | Pri |
|---|---|---|---|---|---|
| 01 #1 | Min target 24 × 24 mm physical | **MISSING** | `metrics.py:38` sets `MIN_TARGET_MM = 18.0`, not 24. After `fit=0.83` at 1280×800@102 that is **14.9 mm**; at 1920×1080@96 it is 18.0 mm. Tux Paint's own tools measure **~48 px = 12.0 mm** (`output/e2e/06-tuxpaint-quit.png`) | Decide by ADR: 18 mm floor (SYNTHESIS A1) or 24 mm (01 #1). Then stop `fit` shrinking below whichever it is — shrink the *grid* (`MIN_GRID_TILE_PX`), not the floor (shell) | P0 |
| 01 #2 | Primary tiles 40–60 mm, ≥12 mm dead space | **PARTIAL** | `PRIMARY_TILE_MM = 40.0` (`metrics.py:39`), `MIN_GAP_MM = 12.0` (`:42`). At `fit=1.0`: 42.3 mm / 12.2 mm ✓. At 1280×800@102: **35.1 mm / 9.96 mm** ✗ | Same fix as #1; drop to a 4×2 grid on small panels rather than shrinking the tile (shell) | P0 |
| 01 #3 | PointAssist-equivalent at shell level | **MISSING** | No sub-movement detection anywhere in `shell/` | Not v0.1. Log as a research spike; `06 §9.8` says it is unproven on modern stacks (shell, later) | P2 |
| 01 #4 | All mouse buttons the same; no right-click, no middle-click | **MET** | `widgets.py:338` `click.set_button(0)` — every button, capture phase, `set_state(CLAIMED)`. `10-input` sets `middle-click-emulation=false`, locked | — | — |
| 01 #5 | No double-click, long-press, multi-finger, modifiers | **MET** (one deliberate exception) | `ChildButton` fires on `pressed` (`widgets.py:359`). The only hold in the child's chrome is `HoldButton` (`band.py:129`) — the parent gate, which is exactly Sesame's sanctioned use. `10-input` sets `double-click=700`, locked | — | — |
| 01 #6 | Idempotent under 8 clicks/s; debounce not queue | **MET** | `DEBOUNCE_MS = 150` (`widgets.py:46`), enforced in `fire()` (`:367`). `state.py:92` comments the idempotent transitions | — | — |
| 01 #7 | Short drags, pick-up/drop cues, click-move-click fallback | **N/A-yet** (shell) / **PARTIAL** (activities) | Shell has no drag at all. `10-input` sets `tap-and-drag-lock=true` and `drag-threshold=16`. KTuberling is drag-only with no click-move-click fallback (`ktuberling.toml`) | Watch a child on KTuberling; if drag fails, that is an upstream limit to record, not fix (activity-config) | P1 |
| 01 #8 | No scrolling in the shell; paginate with big dots/arrows | **MET** | `quiet_carousel()` (`widgets.py:658`) turns off `scroll_wheel`, `mouse_drag`, `long_swipes`, `interactive`, and sets `Overflow.HIDDEN`. `Pager` (`:550`) arrows are 21.2 mm. Visible in `demo-home.png` | — | — |
| 01 #9 | Keyboard never required to reach/leave the shell | **MET** | Every surface is pointer-reachable; `app.py:189` comments Escape is not a trap. Keyboard *works* (`clicked` handler, `widgets.py:345`) but is never needed | — | — |
| 01 #10 | Forgiving matching wherever text is entered | **N/A-yet** | No text entry in the child shell. The one text field is the grown-up PIN pad (adult) | — | — |
| 01 #11 | Flat, one level, spatially stable; no menus/folders/search | **MET** | Three surfaces + band (`app.py:253`). No menu widget in the tree; `08 §7.14`'s "no search box" holds — `journal.py` has no search method | — | — |
| 01 #12 | ≤5 primary choices per screen for 4–6 | **MISSING** | Home draws a 4×3 grid = **12 tiles** (`metrics.py:93 GRIDS`, `home.py:116`). The shipped set is 10 activities + "All done" = 11 on one page (`e2e-contact-sheet.png` frame 2) | This is the single sharpest contradiction between SYNTHESIS B2 ("Home tiles ≤ 12 on one page") and 01 #12 ("never more than 5"). SYNTHESIS resolves it with *progressive disclosure*, which is not built. Ship the first child test with a parent allow-list of **5** and add progressive disclosure after (parent-panel/shell) | P0 |
| 01 #13 | One obvious home and one obvious back, fixed position | **MET** | `Band` (`band.py:239–243`): Back, Undo, My Things always leftmost, never reordered. Back on Home speaks "You're home" (`app.py:637`) rather than doing nothing silently | — | — |
| 01 #14 | Icon + label + audio; depictive icons; label ≥18 pt | **PARTIAL** (fix in flight) | Icons: 17 hand-drawn representational SVGs in `data/icons/`, plus RPM app icons. Audio: `ChildButton.speak_text` on everything. Label: `theme.css:141` `.tile-label` is 24 pt, but `metrics.points()` multiplies by `fit`, so the "18 pt floor" is really **14.9 pt** at 1280×800@102 (`metrics.py:222 label_floor_pt`). Truncation visible in the contact sheet | (a) let the ellipsis fix land; (b) make `TILE_LABEL_MIN_PT` an **absolute** floor not a scaled one (shell) | P0 |
| 01 #15 | Read-aloud a first-class always-available service + persistent Ear | **PARTIAL** | `SpeechManager` (`speech.py:339`), Ear at `band.py:258`, verified live in the VM (`e2e-scenario.md` §3.3). **But the band — Ear included — is gone for the whole of `IN_ACTIVITY`** (`app.py:89`, spec §8) | Spike the band-over-activity problem now; it is the largest single hole in the build (shell/image) | P0 |
| 01 #16 | Instructions audio-first, ≤2 sentences, ≤12 words, imperative | **MET** | Longest child-facing utterance: "The sun is going down. Finish this one, or one last little thing?" (`ending.py:112`) — 2 sentences, 12 words. Home: "Home. What shall we make?" (`home.py:202`) | — | — |
| 01 #17 | Demonstrate with a looping animation, not a description | **MISSING** | No demonstration anywhere. The only animation is the Put-away keep flight (`ending.py:160`) | Not v0.1. Note for the first activity that needs a new mechanic (shell) | P2 |
| 01 #18 | Feedback <100 ms; progress indicator >1 s | **PARTIAL** | Press state is CSS-immediate (`theme.css:126`) plus a `tap` earcon. **No progress indicator for activity launch**, which the e2e log shows taking ~1 s for Tux Paint (`e2e-scenario.md` §5) — the screen simply goes black | Add a "opening…" beat with the activity's icon during launch (shell) | P1 |
| 01 #19 | Qualitative not numeric feedback | **MET** | `goodbye.py:27 WORDS` renders counts as words ("two things"); `journal.py` never surfaces a count to the child; the sun has no digits (`band.py:20`) | — | — |
| 01 #20 | Exaggerate state cues; "saved" must be unmistakable | **PARTIAL** | Keep earcon + the flight animation on Put away (`ending.py:155`). **But an autosave during an activity is completely invisible** — `_on_new_work` (`app.py:527`) plays a keep earcon behind a fullscreen activity nobody can hear over | Once the band is over activities, put the keep animation there (shell) | P1 |
| 01 #21 | ≤2 animated elements; no ambient loops; progressive disclosure | **PARTIAL** | Motion is capped at one large animation (impl. notes §3). No ambient loops anywhere. **Progressive disclosure is not built** — session 1 shows the same 11 tiles as session 50 | See #12 (shell) | P1 |
| 01 #22 | Universal undo in a fixed position | **PARTIAL** | Undo is in the band on every surface (`band.py:240`) and honest when empty (`app.py:647`). But it only does one thing (un-star, `journal.py` via `journal.py` screen `undo_star`), it is unreachable during an activity, and it does **not** route into the activity — the spec promised "activities own their own undo", which for Tux Paint means an Undo tool 12 mm across | Band-over-activity again; until then, accept and document (shell) | P0 |
| 01 #23 | Continuous autosave to the journal; no save dialogue | **MET** | `JournalWatcher` (`journal.py:497`), FileMonitor + 15 s safety sweep; `tuxpaint.conf` sets `autosave=yes`, `saveovernew=yes`, so Tux Paint never asks. Proven end-to-end in the VM | — | — |
| 01 #24 | No modal text confirmations; destructive = spatial + recoverable; bin ≥30 days | **PARTIAL — one loud failure** | Shell: zero confirmation dialogues, zero delete (`journal.py:18`). **Tux Paint shows "Do you really want to quit?" with "Yes, I'm done!" / "No, take me back!"** — `output/e2e/06-tuxpaint-quit.png`, a text modal a pre-reader cannot read, ~440 × 195 px, not read aloud. This is exactly what 01 §4 forbids | Tux Paint has no config key to suppress it. Options: (a) accept and note the tick/cross is at least Sesame-shaped; (b) hide Tux Paint's Quit tool via `tuxpaint.conf` and let the shell own exit — but then the child has *no* way out while the band is hidden. **(b) only becomes safe once the band is over activities.** Record as a blocked P0 (activity-config) | P0 |
| 01 #25 | No adult error messages; return to known-good state | **MET** | Three friendly lines, no codes: `app.py:492` "That one didn't want to open. Try another."; `:521` "That one didn't open. Let's try something else."; `:500` "That one isn't here any more." Detail goes to the journal at WARNING with a stderr tail (`launcher.py:120`) | — | — |
| 01 #26 | Burst-click on a non-target = usability alarm → proactive help | **MISSING** | `grep -rn 'burst' shell/kidnix_shell/` returns two comments and no detector. Debounce *survives* a burst; nothing *notices* one | Cheap to add: count presses landing on non-interactive area per 2 s window, log locally, replay the last instruction (shell) | P1 |
| 01 #27 | The system ends the session, not the parent | **MET** | `Session.phase()` drives everything (`session.py:349`); `ritual.next_action()` is the whole policy (`ritual.py:55`). The grown-up sheet's "End now" runs the *same* `finish_now()` the child's tile does (`grownup.py:291`), so even a parent ending looks like the machine's | — | — |
| 01 #28 | Routine and predictable: same slot, length, ritual | **PARTIAL** | Length fixed at 25 min (`session.toml`), ritual identical every time. **No schedule windows** — `SessionPolicy` has only `bedtime_start/end`, not "after tea" windows (02 #18) | Add schedule windows to the policy (shell/parent-panel) | P1 |
| 01 #29 | No autoplay, ever | **MET** | No auto-advance path exists. `launch()` refuses to start anything from the ritual or Sleeping (`app.py:486`). Nothing queues | — | — |
| 01 #30 | Continuous non-numeric depletion, glanceable throughout | **PARTIAL** | The sun is exactly right where it is visible: Cairo arc, travels and sinks, warms in the last 6 min, no digits (`band.py:61–126`, verified in `e2e-contact-sheet.png` frames 9–11). **Invisible for the entire `IN_ACTIVITY` state**, which is most of a session | Band-over-activity (shell/image) | P0 |
| 01 #31 | End on a completion beat | **MET** | S6 Put away is the completion beat: the work flies into My Things with the keep earcon and "Let's keep that" (`ending.py:139–172`). No buttons — nothing to get wrong | — | — |
| 01 #32 | Child-initiated ending is first-class | **MET** | "All done" tile, last position on Home, moon icon, calm lavender, one tap, no confirmation (`home.py:57–69`, `theme.css:294`). `_all_done()` → `finish_now()` → the same ritual (`home.py:190`). Back on Put away recovers an accidental tap after 3 s (`app.py:640`) | — | — |
| 01 #33 | Journal spatial and visual, not searchable; picture date cues | **PARTIAL** | Thumbnail-dominant cards ≥ 44 mm, activity icon corner, star corner, no search (`screens/journal.py:168`). Day headings are **words only** — "Today"/"Yesterday"/"Before" (`journal.py:44`) with no illustration, which 01 #33 and 08 §4.3 both ask for | Add a sun/moon/day-colour glyph to each heading (shell) | P1 |
| 01 #34 | Lean on narrative and scripts | **MET** (for the ritual) | The ending is the same four-beat script every time. No multi-step activity exists yet to test it further | — | — |
| 01 #35 | Age-band finely (4–5 vs 6–8); parent sets the band | **PARTIAL** | `Profile.age_band = "4-5"` exists (`parent.toml`) and manifests carry `age_min`/`age_max` — but **nothing consumes them**. `home.py:98` filters on `on_home` only. `tuxmath.toml` says "The shell should not show this to a four-year-old" and the shell shows it | Filter Home by `age_band` vs `age_min/age_max` — a two-line predicate next to `_denial()` (shell) | P1 |
| 01 #36 | Best interests of the child recorded as the primary consideration | **PARTIAL** | It is the substance of `AGENTS.md` §3 and SYNTHESIS §2, but there is no document that says the words, and no Child Rights Impact Assessment (03 #38) | Write the CRIA; it is a document task, not code (thinker) | P2 |
| 01 #37 | Zero telemetry by architecture | **MET** | No analytics dependency (`pyproject.toml` declares **no runtime dependencies**). `rpm-ostree-countme.timer` masked (`hardening.md` §320). nftables rejects uid 1000 egress. The one INFO log of UI text is local-only and is the shell's own strings (`speech.py:380`) | — | — |
| 01 #38 | No nudge techniques | **MET** | "Ask for more time" *dismisses* the offer and speaks an honest line (`ending.py:102`) rather than dangling a grant. No "are you sure", no bribe. `suggestions.py` explicitly forbids "see you next time" lines | — | — |
| 01 #39 | Design for the dyad; one shared-attention activity; legible parent view | **PARTIAL** | "Show a grown-up" exists on Goodbye and opens My Things read-only for 2 min (`app.py:587`). The Journal on disk is a plain browsable tree (F4 ✓). **No letters-to-family, no photos, no parent panel** | Scheduled; letters is the highest-value next activity per 05 §3 (activity) | P1 |
| 01 #40 | Recruit children as design partners | **N/A-yet** | Nobody has tested with a child. That is what this audit is preparing for | — | — |
| 01 #41 | Test in 20–30 min sessions, familiar setting, +30% recruits | **N/A-yet** | `08 §6` has the protocol; no session has run | Write the protocol into `docs/plan/` before the first test (thinker) | P0 |
| 01 #42 | Weight observation over self-report | **N/A-yet** | — | Same | P0 |
| 01 #43 | Forced-choice / Again-Again; Smileyometer only with support | **N/A-yet** | — | Same | P1 |
| 01 #44 | Active intervention / peer tutoring as facilitation | **N/A-yet** | — | Same | P1 |
| 01 #45 | Written parental consent + verbal child assent | **N/A-yet** | The subject is the author's own child; `08 §6` is explicit that this makes opinion data worthless | Have another adult run any opinion session (human) | P1 |

### 2.2 `02-development-and-wellbeing.md` §3 — the 20 principles

| ID | Principle (short) | Status | Evidence | Action | Pri |
|---|---|---|---|---|---|
| 02 #1 | 20–30 min default, 10–45 range, ~1 h/day ceiling, stated as precaution | **MET** | `session.toml`: `length_minutes = 25`, `daily_budget_minutes = 60`. `MIN/MAX_SESSION_MINUTES = 10/45` (`session.py:43`). The grown-up sheet's subtitle literally says *"No number here is evidence-based; 25 is the precaution."* (`grownup.py:30`) — this is the most intellectually honest thing in the build | — | — |
| 02 #2 | Bounded activities with real completion; round to activity boundary | **MISSING** | Spec §6 is explicit: *"the hard stop is the hard stop"*. `_begin_put_away` (`app.py:431`) SIGTERMs mid-stroke at T−2 with no boundary protocol. 08 §4.7's "never end mid-creation" is not implemented | The activity API has no `at_natural_boundary` hook and Tux Paint could not answer it. Accept for v0.1, but the 5 s autosave grace is the entire mitigation — say so in the parent docs (shell) | P1 |
| 02 #3 | The machine owns the ending | **MET** | See 01 #27 | — | — |
| 02 #4 | Ending predictable and in-experience, not an interruption | **PARTIAL** | The offer is a choice at a soft point, asked **once** — the `_offer_answered` latch (`session.py:252`, `ritual.py:55`) fixes the e2e bug where it re-asked every second for four minutes. But with an activity running, the offer is **raised as a fullscreen window over the child's drawing** (`app.py:423`) — which is precisely the modal interruption 02 #4 argues against | Once the band is over activities, present the offer *in the band* first and only take the screen if ignored (shell) | P1 |
| 02 #5 | Continuous analogue display with a wind-down phase | **PARTIAL** | Analogue ✓ (sun), wind-down ✓ (warm colour in the last 6 min, `session.py:361`), framed as finishing not draining ✓ ("Let's keep that"). Invisible during activities ✗ | See 01 #30 | P0 |
| 02 #6 | A ritual the child performs; saving is the child's act | **PARTIAL** | The ritual is watched, not performed: S6 has **no buttons** by design (`ending.py:115`). The child's only act is Goodnight. Autosave is continuous ✓ | Consider one performed beat — the child taps the thing into My Things. Taste call for the human (shell) | P2 |
| 02 #7 | Hand the child back to the physical world | **MET** | `suggestions.py` — 9 activity-keyed lines, category fallbacks, deterministic per day so a child ending twice hears the same thing. Rules documented in the module docstring. Visible in `e2e-contact-sheet.png` frame 11 | — | — |
| 02 #8 | Reward = artefact + specific descriptive feedback | **PARTIAL** | Artefact ✓ (Journal + "You made two things today"). **Descriptive feedback is absent** — nothing ever says "you used five colours" | Needs activity introspection; not v0.1 (shell/activity) | P2 |
| 02 #9 | No time- or attendance-based reward | **MET** | `grep -rin 'streak\|badge\|leaderboard\|xp'` over `shell/kidnix_shell/` returns **zero** matches outside typography identifiers. No return-frequency logic exists | — | — |
| 02 #10 | Genuine low-friction stop-early, never "are you sure" | **MET** | "All done", one tap, no confirmation, explicitly reasoned in `home.py:190` | — | — |
| 02 #11 | Co-use invited, never required | **MET** | Everything works solo; "Show a grown-up" is an offer | — | — |
| 02 #12 | The Journal is the co-use surface | **PARTIAL** | It is chronological, child-narratable, analytics-free ✓. But there is no "tell me about it" recording, and `SHOWING` mode only speaks the title (`screens/journal.py:244`) | Voice-note-on-a-card is the cheapest literacy win in 05 §3 (activity/shell) | P1 |
| 02 #13 | EYSTAG slow-content rules applied to the chrome | **MET** | No carousels that rotate themselves (`quiet_carousel` is inert), no ambient loops, one motion at a time, chrome never reorders (`band.py:8`) | — | — |
| 02 #14 | Coherence: strip extraneous stimulation, default to none | **MET** | Four earcons total (`sound.py:383`-ish, impl. notes §11), no music, no celebratory animation | — | — |
| 02 #15 | Contingent and consequential, not stimulus–response | **PARTIAL** | The shell responds instantly to everything; the *choices* live in the activities. The one shell choice with a consequence is the ending offer | Fine for a launcher; revisit when first-party activities land | P2 |
| 02 #16 | Every activity has a one-line honest goal, visible to the parent | **MET, and honestly** | All ten manifests carry `goal`, and they do not flatter: `gcompris.toml` — *"Not curated yet — some are pitched well above five."*; `supertux.toml` — *"Just for fun — a jump-and-run game with a game-over state."* `--validate-manifests` flags a manifest with no goal | The parent panel that would *show* these does not exist (parent-panel) | P1 |
| 02 #17 | Protect sleep structurally: bedtime lockout, warmer/dimmer approach | **PARTIAL** | Bedtime 19:00–07:00 enforced (`session.py:93`, `_refuse` speaks "It's night time"). Sleeping screen is dark and warm-toned (`theme.css:229`). **No gradual warming as bedtime approaches** — the transition is a cliff | Low cost: tint the paper toward amber in the last 30 min before `bedtime_start` (shell) | P2 |
| 02 #18 | Reflect household context: schedule windows | **MISSING** | Only a single bedtime window exists. Spec §7a mentions "the next allowed schedule window" but `SessionPolicy` has no window list | Add `windows = [["16:00","18:00"], …]` to `session.toml` (shell) | P1 |
| 02 #19 | Prefer educational/creative; receptive content a minority mode | **MET** | Manifest ordering is `make` (10, 20, 30) → `learn` (40–60) → `play` (70–90) → Library (100), enforced by `Activity.sort_key` (`activities.py:134`). Exactly one pure-play title (SuperTux), and the manifest says so | — | — |
| 02 #20 | Low-intrusion parent controls; no engagement metrics | **PARTIAL** | The sheet shows "Used N of 60 minutes today" (`grownup.py:280`). That is a budget readout, not an engagement metric, but it is the one number in the product that could become one | Keep it minutes-remaining, never minutes-spent-per-day-over-time. No charts, ever (parent-panel) | P2 |

### 2.3 `06-input-accessibility-hardware-ai.md` §7 — the 40 numbered specs

*(§3 hardware and §4 accessibility are prose; §7 is where they are numbered.)*

| ID | Spec | Status | Evidence | Action | Pri |
|---|---|---|---|---|---|
| 06 #1 | `double-click` 700 ms | **MET** | `dconf/kid.d/10-input`, and **locked** in `locks/10-input` | — | — |
| 06 #2 | Never require a double-click | **MET** | `widgets.py:338` | — | — |
| 06 #3 | Never require right-click; both buttons the same | **MET** | `set_button(0)` | — | — |
| 06 #4 | `accel-profile flat`, `speed ≈ −0.4` | **MET** | `10-input`, both locked (mouse) and set (touchpad) | — | — |
| 06 #5 | `drag-threshold` 16 px | **MET** | `10-input`, locked | — | — |
| 06 #6 | Touchpad: drag-lock on, DWT timeout 1000 ms, consider 2-finger scroll off | **PARTIAL** | `tap-and-drag-lock=true`, `disable-while-typing-timeout=1000` ✓. `two-finger-scrolling-enabled` is **not set** — the spec says "consider", so this is a live choice | Set it false in the child session; the shell never scrolls anyway (image) | P2 |
| 06 #7 | Click-lock / sticky-drag as a first-class child setting | **PARTIAL** | `tap-and-drag-lock` covers the touchpad; there is no mouse click-lock | Only matters once a drag activity ships (image) | P2 |
| 06 #8 | Dwell click exposed, 1.2 s, threshold 20 px | **MET** | `10-input` sets all three, `dwell-click-enabled=false` (a parent accommodation, correctly not a default) | — | — |
| 06 #9 | `cursor-size` 48 | **MET** | `10-input`, locked | — | — |
| 06 #10 | Disable key repeat / delay ≥1000 ms | **MET** | `delay=1000`, `repeat-interval=80` | — | — |
| 06 #11 | Never require scroll; paginate | **MET** | See 01 #8 | — | — |
| 06 #12 | Never require multi-touch beyond tap and drag | **UNKNOWN** | Nobody has run kidnix on a touchscreen. `e2e-scenario.md` §7.2 names this as an open question | Borrow a touch device before claiming touch support (human) | P1 |
| 06 #13 | Primary targets ≥18 mm, preferred 24 mm | **PARTIAL** | 18.0 mm at `fit=1.0`; **14.9 mm** at 1280×800@102 | See 01 #1 | P0 |
| 06 #14 | Absolute floor 44 × 44 CSS px | **MET** | `BAND_TARGET_MIN_PX = 44` and `MIN_FIT = 0.45` guarantee it (`metrics.py:83, 101`); tested across eight panels (impl. notes §13) | — | — |
| 06 #15 | Minimum spacing 8 mm | **MET** | 9.96 mm at the worst panel, 12.2 mm at 1080p | — | — |
| 06 #16 | Rounded targets with ~4 mm invisible hit slop | **PARTIAL** | Rounded ✓ (`theme.css:117` 28 px radius on tiles). **No hit-area extension** — the `ChildButton` hit area is its visual bounds | Add 4 mm of transparent margin inside the grid gap (shell) | P1 |
| 06 #17 | Nothing a child needs at edges/corners; hot corners off | **PARTIAL** | `enable-hot-corners=false`, locked ✓. But the Grown-up gate is deliberately in the far corner (correct, per 08 §4.5) and on `boot-home.png` the Who's-here Grown-up tile **ran off the bottom-right corner** — fixed in v0.1.1 by `whos_here.py:35` margins | Verified fixed; re-check on the next boot screenshot (shell) | P2 |
| 06 #18 | Layout may be spacious for free | **MET** | Grids are centred with generous margins | — | — |
| 06 #19 | Reading font Andika | **MET** | `36-fonts.sh` installs `sil-andika-fonts` 6.101 and asserts `fc-match Andika == Andika`; `theme.css:29` requests it with Cantarell behind | — | — |
| 06 #20 | UI chrome Atkinson Hyperlegible | **MISSING (silent)** | `theme.css:262` asks for `"Atkinson Hyperlegible"`. The image installs **`atkinson-hyperlegible-next-fonts`**, family name *"Atkinson Hyperlegible Next"* (`36-fonts.sh:79`). The names do not match, so the grown-up sheet silently falls back to Cantarell | One-word CSS fix (shell) | P2 |
| 06 #21 | Base UI text 24–28 px (18–21 pt); `text-scaling-factor` 1.3 | **PARTIAL** | `text-scaling-factor=1.3` set and deliberately *not* locked ✓. Child text is 22–40 pt in `theme.css` ✓, but `Metrics.points()` scales everything by `fit`, so at 1280×800@102 `.quiet-line` is 18.3 pt (just inside) and a wrapped tile label can reach **14.9 pt** (outside) | See 01 #14 (shell) | P0 |
| 06 #22 | Line length ≤45 chars, line-height ≥1.6, never justified | **PARTIAL** | `big_label` caps at 40 chars (`widgets.py:646`) ✓, centred not justified ✓. `labels.py` uses `LINE_SPACING` — needs checking against 1.6 | Confirm `LINE_SPACING ≥ 1.6` (shell) | P2 |
| 06 #23 | OpenDyslexic as an option, no claims | **N/A-yet** | Not shipped, not claimed. Correct posture | — | — |
| 06 #24 | Colour never the sole carrier | **MET** | Every state carries shape or text: not-allowed = dashed outline + a different spoken line; "All done" = moon icon + label; the sun = position, not hue; disabled pager = `opacity: 0` not grey (`theme.css:254`) | — | — |
| 06 #25 | Non-text ≥3:1, text ≥7:1 | **PARTIAL** | Text: ink `#16181d` on paper `#fbf7ef` = **16.9:1** ✓✓. Band buttons on `#0f8a8a` = **3.9:1** ✓ for 3:1, under 08 §3.4's preferred 4.5:1. **Not-allowed tile border `rgba(0,0,0,0.18)` on paper = 1.5:1 — a clear fail**, and it is the affordance that carries G3 | Darken `@kid-edge` for the `.not-allowed` case to ≥3:1 (shell) | P1 |
| 06 #26 | No sudden sounds; fade ≥150 ms; global quiet mode | **PARTIAL** | `sound.py:45 FADE_MS = 6.0` — 6 ms, not 150. The code's own defence (a 90 ms tick cannot fade for 150 ms) is fair, and the guideline is arguably about sustained audio; but **nobody has heard these on speakers** (impl. notes §14.3). No quiet mode | Listen to them in a room; add a mute tile (08 §3.6 wants a *visible* child mute) (human/shell) | P1 |
| 06 #27 | All motion <250 ms, eased; honour `enable-animations=false` | **PARTIAL** | Durations are **400 ms** (`widgets.py:71`, `app.py:250`) and 1100 ms for the keep flight — deliberately, following 08 §3.5's 350–450 ms "legible as a journey" over 06's 250 ms. Easing ✓ (`EASE_IN_OUT_CUBIC`). **`enable-animations` is not honoured** (deferred, impl. notes §3) | The 400 ms is a defensible ADR-able conflict (see §3). Reduced-motion is not: wire it (shell) | P1 |
| 06 #28 | No notifications, badges, streaks, variable rewards, autoplay, infinite scroll | **MET** | `show-banners=false` locked; no badge/streak code; no autoplay; no scroll | — | — |
| 06 #29 | Piper `en_GB` (cori/jenny) as the voice | **PARTIAL** | ADR-0008: espeak-ng guaranteed, Piper behind a flag. The e2e run used speech-dispatcher's default. **The child will hear espeak-ng**, which is robotic | Turn Piper on for the child test. A five-year-old's first impression of the voice is not a detail (image) | P0 |
| 06 #30 | Rate ≈130 wpm, 300–500 ms sentence pauses | **UNKNOWN** | `SPEECH_RATE = -20` on speechd's −100..100 scale (`speech.py:43`). Nobody has measured the resulting wpm | Measure it against a stopwatch (human) | P1 |
| 06 #31 | Ship Welsh TTS | **N/A-yet** | en-GB only (`SPEECH_LANGUAGE`) | Roadmap (image) | P2 |
| 06 #32 | ASR optional, off, push-to-talk, offline, constrained | **MET** (by absence) | No ASR anywhere | — | — |
| 06 #33 | Visible recording indicator whenever the mic is live | **N/A-yet** | No microphone use | Design it *before* the voice-note feature (shell) | P2 |
| 06 #34–38 | Hardware: T480 reference, Pi 5 tier, peripherals, published minimums | **MET** (documented) | `docs/plan/HARDWARE.md`; the fit work explicitly targets 1280×800 and 1366×768 | — | — |
| 06 #39 | Shell-enforced ergonomics: 20-min sessions, look-away prompt, hard stop <45 min | **PARTIAL** | 25 min default, 45 min hard cap (`MAX_SESSION_MINUTES`) ✓. **No 20-20-20 look-away prompt** | A single spoken beat at T+20 ("look out of the window for a moment") is cheap. Note it competes with 02 #4's "no interruptions" (shell) | P2 |
| 06 #40 | No conversational LLM | **MET** | ADR-0009; there is no model, no network, no prompt anywhere in the tree | — | — |

### 2.4 `08-shell-ux-patterns.md` §3 (numbers) and §4 (patterns)

| ID | Recommendation | Status | Evidence | Action | Pri |
|---|---|---|---|---|---|
| 08 3.1a | Primary target ≥20 mm (≥76 px) | **PARTIAL** | Tiles 42.3 mm / 35.1 mm ✓. Band buttons 20.1 mm / **16.2 mm** — under on the small panel | See 01 #1 | P0 |
| 08 3.1b | Secondary target ≥14 mm | **PARTIAL** | Star button `max(min_target, 0.3 × card)` = 60 px = 14.9 mm ✓ (just). Tux Paint's colour swatches ~58 × 46 px = **14.4 × 11.5 mm** ✗ | Upstream limit; record (activity) | P1 |
| 08 3.1c | Gap ≥8 mm (12 preferred) | **MET** | 9.96–12.2 mm | — | — |
| 08 3.1d | Destructive control ≥20 mm and ≥24 mm from anything | **MET** (vacuously) | There is no destructive control in the child shell | — | — |
| 08 3.1e | Adult control ≥9 mm | **MET** | Grown-up gate 12.4 mm; PIN pad `min-width/height: 64px` = 15.9 mm (`theme.css:271`) | — | — |
| 08 3.1f | Register on press, commit on release, drag-away cancels harmlessly | **PARTIAL** | Fires on press ✓ (`widgets.py:359`). It also *commits* on press — there is no press-then-drag-away cancel. For a debounced, undo-rich, non-destructive shell this is arguably right | Note as a deliberate simplification (shell) | P2 |
| 08 3.1g | Never require a drag; every drop target oversized | **MET** (shell) | No drag in the shell | — | — |
| 08 3.2a | Base unit 8 px; tile 160 × 160 with a 40 px label band | **MET** | `TILE_PX = 160` (`metrics.py:46`); label box is two lines at the floor (`TILE_LABEL_LINES = 2`), which is *more* than 40 px and deliberately so | — | — |
| 08 3.2b | Home ≤3 × 4 = 12, one page, no scroll; page horizontally | **MET** | `GRIDS = ((4,3),(4,2),(3,2))`; `Adw.Carousel` + `Pager`. See 01 #12 for whether 12 is the right number | — | — |
| 08 3.2c | Everything important on screen at first paint | **MET** | `_check_measured_fit` (`app.py:274`) rebuilds up to 3× until the tree provably fits the monitor — this is the fix for `boot-home.png`'s clipped band | — | — |
| 08 3.2d | Scan order left-to-right; most important top-left | **MET** | `order` puts Draw at row 0 col 0 (`activities.py`, impl. notes §15.3) | — | — |
| 08 3.2e | Persistent never-moving chrome band | **PARTIAL** | Perfect on the four shell surfaces; **absent during `IN_ACTIVITY`** | See 01 #15 | P0 |
| 08 3.3a | Tile label 40 px semibold; min glyph 24 px; ≤40 chars; never all-caps | **PARTIAL** | 24 pt ≈ 32 px at `fit=1.0`, under the recommended 40 px, and can reach 14.9 pt ≈ 20 px shrunk. Never all-caps ✓, ≤40 chars ✓ | Same as 01 #14 (shell) | P0 |
| 08 3.3b | Word-by-word highlight during read-aloud | **MISSING** | Deferred (impl. notes §3) with the reasonable argument that the shell speaks nouns. But S5/S7 speak *sentences* with no highlight | Add it to the two sentence screens (shell) | P2 |
| 08 3.4a | Colour = whose, shape = what | **MET** | `_apply_tint` injects `@kid-primary`/`@kid-secondary` from the profile (`app.py:216`, `theme.py`), tinting the band; activity icons stay in their own palette | — | — |
| 08 3.4b | One reserved highlight colour | **PARTIAL** | `@kid-highlight #ffd23f` used for `.speaking` and `:focus-visible` ✓ — and also for the hold-progress bar (`theme.css:94`), a third use | Defensible ("what you are touching"), but note it (shell) | P2 |
| 08 3.4c | Never grey out; outline instead, or don't show | **MET** | `.not-allowed` is dashed outline; disabled pager is `opacity: 0`; unavailable activities get no tile at all (`activities.py:143`). Both reasoning chains are in comments | Contrast fix from 06 #25 (shell) | P1 |
| 08 3.5 | 350–450 ms spatial transitions; ≤1 large motion; reduced motion | **PARTIAL** | 400 ms ✓, direction encodes journey (`app.py:350`) ✓, one motion ✓. Reduced motion ✗ | See 06 #27 | P1 |
| 08 3.6a | Audio always paired with a visual | **MET** | The `.speaking` ring, duration-estimated (`speech.py:434`) | — | — |
| 08 3.6b | Six earcons | **PARTIAL** | Four shipped: keep, tap, back, sleep (impl. notes §11). Missing: *ask sent* (no Ask flow) and *session phase change* — the latter **does** apply now | Add the phase motif; it is the audio half of the sun (shell) | P1 |
| 08 3.6c | Earcons duck under speech; ≥250 ms apart; visible child mute | **PARTIAL** | Ducking and spacing implemented (`sound.py`). **No child-facing mute tile** — 08 §3.6 is explicit that "a muted machine that looks broken is worse than a loud one" | Add a mute tile or band control (shell) | P2 |
| 08 3.6d | Focus-follows-speech, hover dwell ~600 ms | **PARTIAL** | Implemented at **300 ms** (`speech.py:35`), per spec §3, deliberately faster so a sweeping pointer hears the grid. Live-verified in the VM at 1.2 s of rest | Test both with the child; 300 ms may chatter (shell) | P1 |
| 08 3.6e | One voice for the shell | **MET** | One `SpeechManager`, one backend, one language (`speech.py:339`) | — | — |
| 08 3.6f | Pre-render fixed shell strings so the shell never waits on synthesis | **MISSING** | Every utterance is live speechd. Lazy-connect + reconnect (`speech.py:139`) mitigates *outages*, not *latency* | Measure first-word latency; pre-render if >200 ms (shell) | P1 |
| 08 3.7a | Representational icons, not glyphs | **MET** | `data/icons/` is 17 hand-drawn SVGs — a literal ear, a moon, a grown-up's head, an arrow over nothing abstract | — | — |
| 08 3.7b | Flat-with-depth: elevation cue + a press state that moves | **MET** | `theme.css:113–131` — 2 px border, 6 px bottom border, 4 px shadow; press moves 4 px and drops the shadow. `pixels.py` in the e2e harness literally *finds* the UI by this asymmetry | — | — |
| 08 3.7c | One character, at boundaries only, never on the canvas | **MISSING** | There is **no character at all**. The ritual speaks in an unattributed voice | This is a gap, not a violation — 08 recommends one and it is deferred silently. Decide by ADR (thinker) | P1 |
| 08 4.1 | Onboarding: a 60 s ritual, not a lesson; choose colours and avatar | **MISSING** | Profiles come pre-baked from `parent.toml`; the child chooses nothing. First boot is Who's here? with one tile called "Me" | The identity choice is also the child's first success. Build it (shell) | P1 |
| 08 4.2 | An Ear that repeats; speech never a gate | **MET** | `on_ear` (`app.py:660`) with an honest empty case; nothing waits for narration | — | — |
| 08 4.3 | Journal: auto-keep, picture cards, day groups, resume-not-open, star, no delete | **PARTIAL** | Auto-keep ✓, versioned ✓ (`v001.png`, `v002.png`), picture cards ✓, Today/Yesterday/Before ✓, heading repeated across a page break ✓ (`journal.py:393`), star with quiet eviction at 8 ✓, no delete ✓, open formats ✓. **Resume does not resume**: no shipped manifest declares `exec_resume`, so tapping a card plain-launches Tux Paint into its own gallery (impl. notes §14.4, Q2 still open) | Implement option (b) — copy the entry's latest version over the activity's working file before launch — for image activities. This is Sugar's one great idea and we currently only have its shape (shell) | P0 |
| 08 4.4 | Profiles: face tiles ≥30 mm, no passwords, identity worn everywhere | **MET** | Avatar 48.6 mm, no child auth, `_apply_tint` on choose (`app.py:466`) | — | — |
| 08 4.5 | Parent gate: unenticing + 3 s hold + PIN, shuffled keypad | **PARTIAL** | Unenticing ✓ (desaturated, corner, never animates, never announced). 3 s hold with a progress ring and slide-off cancel ✓ (`band.py:190`). PBKDF2-SHA256 200k rounds ✓. **Keypad is not shuffled** (`grownup.py:120` is a fixed 1–9 grid) and **there is no rate limiting** (`settings.py:220 check_pin` is a bare compare) — 03 #17 asks for both | Shuffle the digits; add a 3-strike back-off (shell) | P1 |
| 08 4.6 | Timer: depleting shape, slow, non-alarming, always present, tappable | **PARTIAL** | Depleting ✓, no red ✓, no pulse ✓, no digits ✓, fixed position ✓. **Not always present** (activities). **Not tappable** — `Sun` is `AccessibleRole.IMG` with no gesture (`band.py:73`), so 08 §4.6's "tapping speaks the remaining time in child terms" is absent | Make the sun a `ChildButton` that speaks "about as long as one story" (shell) | P1 |
| 08 4.7 | Ending ritual: offer at a natural boundary, put away, goodbye, one-more via Ask | **PARTIAL** | Offer ✓ once, three answers all dismiss ✓, put-away flight ✓, goodbye with count-in-words + ≤3 thumbnails + offline line ✓ (frames 9–11). **No natural-boundary wait** (02 #2). **"Ask for more time" has nowhere to go** — it speaks "go and ask them" (`ending.py:108`), which is honest but is not the asynchronous grant D7 describes | Ask queue is the next milestone; until then this line is the right honest stopgap (shell) | P1 |
| 08 4.8 | Undo over confirmation; deep persisted undo; no delete; forgive imprecision | **PARTIAL** | No delete ✓, no confirmation in the shell ✓, versioning ✓. **Undo is not deep and does not persist** — it un-stars one thing (`app.py:647`) | See 01 #22 | P0 |
| 08 4.9 | No scores; reward is the artefact; micro-feedback; describe not praise; no fail states | **PARTIAL** | No scores ✓, artefact ✓, micro-feedback ✓, no shell fail state ✓. **SuperTux has lives and a game-over**, which its own manifest flags | Watch it; be ready to drop it (activity-config) | P1 |
| 08 4.10 | Ask a grown-up replaces every silent denial | **PARTIAL** | Not-allowed and not-installed tiles both *speak*, with **two different sentences** so a child is never sent to ask for something nobody can give (`home.py:53–54`) — a genuinely thoughtful implementation of the principle without the flow. But the flow itself is absent and the Ask button is removed from the band (`band.py:45 SHOW_ASK = False`) | Next milestone (shell) | P1 |
| 08 4.11 | No help section; audio-on-focus + idle contextual hints + "I need help" | **PARTIAL** | Audio-on-focus ✓ and no help section ✓. **No idle hints** — nothing happens after 8 s on Home | An idle hint naming one specific tile is the cheapest discoverability win available (shell) | P1 |
| 08 4.12 | Show a grown-up / print / send to family | **PARTIAL** | Show-a-grown-up ✓ (2 min read-only). Print ✗ — and `disable-printing=true` is **locked** in the kid dconf profile, so it cannot be added without unlocking. Send ✗ | Decide: printing is "disproportionately motivating for this age" per 08 §4.12 and we have locked it off (image) | P1 |
| 08 4.13 | Multi-child switching from the band; independent budgets; "two of us" | **N/A-yet** | Data model supports N profiles; UX ships one | Scheduled (shell) | P2 |
| 08 §5.2 | Band 96 px at the top, never hides, tinted | **MET** | `BAND_HEIGHT_PX = 96`, clamped 80–128 per §7a; 85 px at 1280×800; top; tinted | — | — |
| 08 §7.15 | Never expose system state to the child | **MET** | No battery, storage, network or update indicator anywhere in the child's tree | — | — |
| 08 §7.17 | No settings screen for the child | **MET** | There is none. (There is also no child-facing colour/avatar/mute preference, which §7.17 says should be the *only* three — see 08 4.1) | — | — |

### 2.5 `05-learning-science.md` §3 — per-activity, for what we ship

| ID | Rule | Status | Evidence | Action | Pri |
|---|---|---|---|---|---|
| 05 Draw-1 | Big canvas, **≤8 tools visible** | **MISSING** | `output/e2e/04-tuxpaint.png` shows **16 tools** in the left column (Paint, Stamp, Lines, Shapes, Text, Label, Fill, Magic, Undo, Redo, Eraser, New, Open, Save, Print, Quit) plus a 2-wide brush grid and a 20-swatch colour bar | Tux Paint has no "hide tools" config. Either accept, or use `--noshortcuts`-style flags to remove Text/Label/Open/Print for the youngest band (activity-config) | P1 |
| 05 Draw-2 | Finger/mouse first, stylus optional | **MET** | Mouse-first by construction | — | — |
| 05 Draw-3 | **Caption field + "tell me about it" voice recorder on every drawing** | **MISSING** | `journal.py` schema *reserves* `note.ogg` / `caption.txt` (spec §5) and nothing writes them | 05 calls this "the cheapest literacy win in the product". Build it as a Journal-card action, not inside Tux Paint (shell) | P1 |
| 05 Draw-4 | Undo and autosave always; never a "discard changes?" dialog | **PARTIAL** | Autosave ✓ (`tuxpaint.conf autosave=yes, saveovernew=yes`) — genuinely well done. **But the quit dialog exists** (01 #24) | See 01 #24 | P0 |
| 05 Draw-5 | Stamps one level down; no grading | **PARTIAL** | No grading ✓. Stamps are a top-level tool, not one level down (upstream layout) | Accept (activity) | P2 |
| 05 GC-1 | **Curated shelf of 12–20**, not the whole suite | **MISSING** | `gcompris.toml` launches `gcompris-qt` bare — ~190 activities. The manifest's own `goal` admits it: *"Not curated yet — some are pitched well above five."* | GCompris takes `--enable-activity`/menu filters. Curating to 15 EYFS/KS1-mapped activities is the single biggest learning-science debt (activity-config) | P0 |
| 05 GC-2 | Group by what the child does | **MISSING** | GCompris's own subject grouping | Same fix | P1 |
| 05 GC-3 | en-GB; check letter activities against a UK phonics progression | **PARTIAL** | `LANG=en_GB.UTF-8` forced in `build_env` (`launcher.py:159`), voices pre-seeded en_GB (`50-activities.sh`). **Phonics check not done** | Do the check before the child test — getting phonics wrong undermines school (05 §4.1) (human) | P0 |
| 05 GC-4 | Never "100 activities!" | **MET** | Tile says "Letters & numbers" | — | — |
| 05 KT-1 | Speaks every part; no way to lose; drag practice | **MET** | `ktuberling.toml` — correctly identified as the best 4–6 title in the set. Drag-only is the caveat (01 #7) | — | — |
| 05 Lib-1 | **Two shelves**: *Books I can read* (decodable, phonics phase) and *Books to me* | **N/A-yet** | `kiwix.toml` is a placeholder with `content_required = true`, no viewer, no ZIM shipped | Do not ship the Library tile at the child test — see Lib-4 | P0 |
| 05 Lib-2 | Narration + congruent illustration + optional word highlighting | **N/A-yet** | — | — | — |
| 05 Lib-3 | **Zero hotspots, mini-games or tap-a-word dictionaries** | **MET** (by absence) | Nothing to violate yet. Record it as a hard constraint on the viewer spec — it is 05's clearest negative finding | Write it into the viewer spec (thinker) | P1 |
| 05 Lib-4 | Child chooses the book; no "books read" counter | **MISSING (as a bug)** | `content_required` is parsed (`activities.py:122`) and **never checked** (impl. notes §15.4.2). `kiwix-serve` *is* installed, so `Availability` passes, the tile draws, and the child opens an empty library with no viewer behind it | One predicate. This is a P0 for the child test: a tile that opens nothing is the exact failure e2e §3.1 already found once (shell) | P0 |
| 05 Kbd-1 | "Find the key that makes this sound"; lowercase; no WPM/streak | **N/A-yet** | No keyboard activity ships. `tuxmath.toml` is typed arithmetic, correctly banded 6+ | — | — |
| 05 Num-1 | Subitising and bonds to the ELG | **MISSING** | Not shipped; 05 §3 names it as an evidence-supported gap | Roadmap (activity) | P2 |
| 05 §4.3 | No star economies, streaks, leaderboards, badges | **PARTIAL** | Shell: clean. **GCompris has its own star ratings and level progressions**; SuperTux has lives and a score | Curation (05 GC-1) is also the fix for this (activity-config) | P1 |
| 05 §4.12 | No background music under narration | **PARTIAL** | Shell: no music at all ✓. `tuxmath`'s soundfont is excluded at build (`50-activities.sh`) ✓. GCompris ships background music which is pre-seeded | Turn GCompris's music off in its config (activity-config) | P1 |
| 05 §4.10 | Never position kidnix as a way to occupy or calm a child | **MET** | Nothing in `README.md` or the manifests does | — | — |

### 2.6 `03-regulation-and-privacy.md` §3 — the checklist items that bind now

| ID | Requirement | Status | Evidence | Action | Pri |
|---|---|---|---|---|---|
| 03 #1 | No egress from the child session by default; provable by packet capture | **PARTIAL** | `kidnix-egress.nft` rejects uid 1000 in an `inet kidnix_egress` table loaded before `network-pre.target`; syntax-checked at build under `unshare -rn`. **Never observed under a capture** (`lockdown.md` §3) | Run a 30-min tcpdump in the VM and make it a CI assertion. 03 #9: "do not claim compliance you have not tested" (image/CI) | P0 |
| 03 #2 | Deny-by-default, per-activity allow-list at the firewall | **PARTIAL** | Deny-by-default ✓; no per-activity allow-list mechanism exists (nothing needs one yet) | — | P2 |
| 03 #3 | Zero telemetry, crash reporting, update pings | **MET** | `rpm-ostree-countme.timer` masked; no reporter; no device ID | — | — |
| 03 #4 | No third-party SDKs/analytics; CI fails on one | **PARTIAL** | `shell/pyproject.toml` declares **no runtime dependencies** — the strongest possible version of this. But there is no CI *gate* that would fail if one appeared | Add a dependency scan (CI) | P2 |
| 03 #5 | Geolocation absent by default | **MET** | Not used; not requested | — | — |
| 03 #6 | Local data encrypted at rest | **MISSING** | `grep -ri luks disk_config/ Containerfile` → nothing | Decide: LUKS on `/var` complicates recovery for a non-technical parent. ADR it (image) | P2 |
| 03 #7 | Published retention policy, no "indefinite" | **MISSING** | `journal.py:18` says "Nothing is ever deleted" — which *is* indefinite retention, chosen deliberately (08 §4.3 "no falloff at v0.1") but not documented as a policy | Write the retention line into the data page (thinker) | P2 |
| 03 #8 | Parent exports everything in one action; deletes everything in one action | **PARTIAL** | Export ✓ by construction: `~/.local/share/kidnix/journal/YYYY/MM/DD/…` of PNG + JSON, browsable in Files (the F4 requirement, met better than most products manage). **No delete action** | Parent panel (parent-panel) | P1 |
| 03 #9 | The child can see and delete their own entries | **PARTIAL** | See ✓. Delete ✗ — deliberately, per 08 §4.3 ("no deletion by the child, ever"). **03 #9 and 08 §4.3 are in direct conflict** and nobody has adjudicated | ADR it. See §3 (thinker) | P1 |
| 03 #10 | No profiling, no behavioural user model | **MET** | Nothing scores or ranks by dwell, session count or return rate. The only adaptivity is `latest_for_activity()` for a tile thumbnail — an explicit signal, not an inferred one | — | — |
| 03 #11 | No time-based engagement rewards; grep must be empty | **MET** | It is empty | — | — |
| 03 #12 | No autoplay, infinite scroll, feed | **MET** | — | — | — |
| 03 #13 | No push notifications to the child | **MET** | `show-banners=false`, locked | — | — |
| 03 #14 | Sessions end honestly; **no child-actionable extend button** | **PARTIAL** | The warning is visual + spoken and minutes-free ✓. But S5 has an **"Ask for more time" button the child can press** — arguably an extend affordance. Mitigated by the fact that it grants nothing and cannot be repeated (the latch) | Keep, but be able to defend it: it is an *ask*, not an *extend*. Note in the CRIA (thinker) | P1 |
| 03 #15 | No dark patterns; asymmetric prominence included | **MET** | "Finish this one" and "One last little thing" are the *same size* (`ending.py:66`, both `mm(60) × mm(30)`), fitted to a common inner width so neither reads as preferred. That is a deliberate anti-dark-pattern | — | — |
| 03 #16 | No purchase, store, currency or upsell | **MET** | — | — | — |
| 03 #17 | Parent settings behind real auth **with rate limiting** | **PARTIAL** | 3 s hold + 4-digit PBKDF2 PIN ✓. **No rate limiting, no shuffled pad** (`grownup.py:168`). A 4-digit PIN with unlimited attempts is 10,000 tries; an eight-year-old will not brute-force it but shoulder-surfing plus a fixed pad is the real attack | See 08 4.5 (shell) | P1 |
| 03 #18 | The child is told what the parent can see | **MISSING** | Nothing tells them | One spoken line in onboarding (08 4.1) covers both (shell) | P1 |
| 03 #19 | No covert monitoring capability in the codebase | **MET** | No screenshot-of-the-child path (`capture()` renders *our own* widget tree and is dev-only), no keylogger, no audio capture. The one behavioural log is `state x -> y` and `speaking: <our own UI string>` | — | — |
| 03 #20 | Per-entry journal visibility from v1 | **MISSING** | Everything is parent-visible; no "just for me" | Schema-additive; do it before v1 (shell) | P2 |
| 03 #21 | Parent-facing UI honest about what is and is not collected | **PARTIAL** | The grown-up sheet's honesty is excellent where it speaks (`grownup.py:30, 31`, the red "no parent config" row). But there is no "what kidnix does with data" page | See #41 (thinker) | P2 |
| 03 #22 | No user-to-user content path | **MET** | None exists; letters-to-family will need an ADR that keeps it a parent-initiated export | — | — |
| 03 #23 | No accounts, no server, no sync | **MET** | — | — | — |
| 03 #24 | No general browser, no arbitrary URL entry | **PARTIAL** | Firefox removed from the image entirely (`hardening.md`) ✓✓ — stronger than the requirement. **But the Library's planned viewer is "WebKitGTK in the shell"** (`kiwix.toml` notes), which is a renderer pointed at `127.0.0.1` | Write the constraint into the viewer spec now: no address bar, no navigation outside the ZIM, no external scheme handlers (thinker) | P1 |
| 03 #25 | Coarse age-bracket signal only, if third-party activities ever land | **N/A-yet** | The manifest API has no identity field ✓ | — | — |
| 03 #26 | TTS fully on-device | **MET** | speech-dispatcher + espeak-ng locally; no cloud path exists | — | — |
| 03 #27 | No wake-word, no always-listening | **MET** | No mic use | — | — |
| 03 #28–30 | LLM constraints | **N/A** | ADR-0009: none ships | — | — |
| 03 #31 | WCAG 2.2 AA for child-facing UI | **PARTIAL** | Target size far exceeds AA; text contrast far exceeds AAA; focus appearance is a 6 px reserved-colour outline ✓. Non-text contrast fails on `.not-allowed` (06 #25). No timed interactions except the ritual, which is the product | Fix the outline contrast; audit focus order (shell) | P1 |
| 03 #32 | Everything meaningful available non-textually; a session with all text blanked | **PARTIAL** | Every control speaks and carries an icon ✓. **The test has never been run.** And the Journal card's spoken title can be `"Draw 14:32"` (`journal.py:187`) — a clock time read aloud to a pre-reader | Run the blank-text test; drop the time from the spoken title (shell) | P1 |
| 03 #33 | Full keyboard/switch operability; nothing drag-only | **PARTIAL** | Shell is fully keyboard-operable (`set_can_focus(True)` on every `ChildButton`, `clicked` → `fire()`). **KTuberling is drag-only** | Record (activity) | P2 |
| 03 #34 | Every bundled asset has a machine-readable licence entry; CI fails without | **PARTIAL** | `docs/LICENSES.md` is thorough (fonts with versions, paths, redistribution notes; every activity manifest carries `licence`). It is a **table, not a machine-readable manifest**, and no CI gate reads it | Make it a YAML/TOML manifest with a CI check (CI) | P2 |
| 03 #35 | Voice model licences recorded separately; no CPML/NC | **MET** | ADR-0008 picks Piper `en_GB-cori` (public domain); no XTTS | — | — |
| 03 #36 | OFL fonts ship notice, licence and FONTLOG; no RFN reuse | **MET** | `36-fonts.sh` installs the Fedora RPMs, which carry `/usr/share/licenses/…`; `LICENSES.md:58` notes the reserved-font-name constraint | — | — |
| 03 #37 | SBOM and SECURITY.md from day one | **MISSING** | Neither file exists | Two small files (thinker) | P2 |
| 03 #38 | Publish a Child Rights Impact Assessment | **MISSING** | — | Write it; this audit is most of the input (thinker) | P1 |
| 03 #39 | Consult children; record it; let it change the product | **N/A-yet** | The point of the next milestone | — | P0 |
| 03 #40 | eSafety Safety by Design self-assessment | **MISSING** | — | (thinker) | P2 |
| 03 #41 | Public plain-English data page, at two levels | **MISSING** | — | (thinker) | P2 |

### 2.7 `SYNTHESIS.md` §2 — principles A–I

| ID | Principle | Status | Evidence / delta | Pri |
|---|---|---|---|---|
| A1 | 18 mm min, 40–60 mm tiles, 8–12 mm gaps, specified in mm | **PARTIAL** | Specified in mm throughout (`metrics.py`) — architecturally exactly right. But `fit` shrinks the *floor* as well as the layout: 14.9 mm / 35.1 mm at 1280×800@102 | P0 |
| A2 | All buttons the same; no right-click/double-click/long-press/chording/multi-touch | **MET** | `widgets.py:337–342`, `10-input`, locked | — |
| A3 | Registers on press; idempotent under 8 clicks/s; debounce not queue | **MET** | `DEBOUNCE_MS = 150` | — |
| A4 | No free scrolling; paginate with big dots/arrows | **MET** | `quiet_carousel()`, `Pager` | — |
| A5 | Short drags with pick-up/drop cues and a click-move-click fallback | **N/A-yet** (shell) | No drag in the shell | — |
| A6 | Keyboard never required | **MET** | — | — |
| A7 | Pointer settings: 700 ms / 16 px / flat / cursor 48 | **MET** | `10-input` + `locks/10-input` — all four set *and locked* | — |
| B1 | Flat, one level, spatially stable; no menus/folders/search | **MET** | — | — |
| B2 | ≤5 primary choices for 4–6; ≤12 home tiles; progressive disclosure | **PARTIAL** | 11–12 tiles on one page; no progressive disclosure. See 01 #12 | P0 |
| B3 | Fixed band on **every surface**, never hides | **PARTIAL** | Every shell surface ✓; **absent for the whole of `IN_ACTIVITY`** | P0 |
| B4 | Icon + label + audio; representational icons; label ≥18 pt; hover reads aloud; Ear repeats | **PARTIAL** | All four channels exist; label floor is scaled below 18 pt and labels truncate (fix in flight) | P0 |
| B5 | Audio-first, ≤2 sentences, ≤12 words, demonstrate with animation, pair with a visual | **PARTIAL** | Sentences ✓, pairing ✓; demonstration ✗ | P2 |
| B6 | Andika / Atkinson; colour never sole; colour = whose, shape = what | **PARTIAL** | Andika ✓ shipped and asserted; **Atkinson name mismatch** (06 #20); colour rules ✓ | P2 |
| B7 | One focal region, ≤2 animated elements, no ambient loops, no music under speech | **MET** | — | — |
| B8 | Age-band finely (4–5 vs 6–8) | **MISSING** | `age_band` and `age_min/max` exist and are never used | P1 |
| C1 | Universal undo in a fixed position; continuous autosave; no save dialogues | **PARTIAL** | Autosave ✓✓; undo is a single shell action and unreachable in an activity | P0 |
| C2 | No modal text confirmations; destructive = spatial; bin ≥30 days; effectively no delete | **PARTIAL** | Shell ✓✓ (no delete at all — better than a bin). Tux Paint's quit dialog ✗ | P0 |
| C3 | No adult error messages; return to a known-good state; log for the parent | **MET** | Three friendly lines + a stderr tail at WARNING. Implemented well | — |
| C4 | Burst-click = usability alarm → proactive help | **MISSING** | Survived, never noticed | P1 |
| D1 | 20–30 min default (10–45), ~1 h ceiling, bedtime, schedule windows, honest about the number | **PARTIAL** | Everything but schedule windows; the honesty is exemplary | P1 |
| D2 | The machine ends it, never the parent; consistent ritual | **MET** | Even the parent's "End now" runs the child's ritual | — |
| D3 | Predictable, in-experience, continuous analogue depletion, glanceable throughout | **PARTIAL** | The sun is right; it is invisible for most of the session | P0 |
| D4 | Rounds to a natural boundary; T−6 offer, T−2 put away, goodbye with an offline continuation | **PARTIAL** | Timings exactly as specified (`session.toml`, verified in `output/e2e/09..11`); goodbye + continuation ✓; **no boundary rounding** | P1 |
| D5 | Child-initiated ending first-class; never "are you sure", never a bribe | **MET** | The "All done" tile, and the reasoning behind it, are the best-argued part of the build | — |
| D6 | No autoplay/up-next/notifications/streaks/rewards/parasocial/fabricated pressure | **MET** | Verified by grep and by reading. `suggestions.py` even bans "see you next time" | — |
| D7 | Grants +5/+15/+30 via Ask; soft stop | **PARTIAL** | Grants exist and are budget-bounded (`session.py:289`), correctly re-arming the offer only when the grant clears T−6. But they are reachable only through the PIN sheet, not through an Ask | P1 |
| E1 | Reward = artefact + descriptive feedback; no points/stars/badges | **PARTIAL** | Artefact ✓, no gamification ✓; descriptive feedback ✗ | P2 |
| E2 | Coherence: no celebratory noise unless it serves the goal | **MET** | Four earcons, no music | — |
| E3 | Contingent and consequential | **PARTIAL** | See 02 #15 | P2 |
| E4 | One honest goal line per activity, visible to the parent | **PARTIAL** | Written ✓; nowhere to show it ✗ | P1 |
| E5 | Educational/creative default; passive video off | **MET** | Make → learn → play ordering; no video at all | — |
| F1 | Auto-keep, resume-not-open, temporal groups, thumbnail cards ≥20 mm, spoken headings | **PARTIAL** | All of it except **resume**, which plain-launches | P0 |
| F2 | Bounded favourites shelf the child curates; no search | **MET** | 8, with quiet eviction and a `starred_at` field to order it | — |
| F3 | Card actions: show / print / send / put away; versions kept | **PARTIAL** | Versions ✓; only star + resume as actions | P1 |
| F4 | A boring conventional file view for the adult; open formats; exportable | **MET** | `YYYY/MM/DD/<id>/{entry.json, v001.png, thumb.png}` — PNG/JSON, no database, browsable in Files. Sugar's most-repeated complaint, answered | — |
| G1 | Controls set the shape and get out of the way; no engagement metrics | **PARTIAL** | The sheet is minimal ✓; the panel does not exist | P1 |
| G2 | 3 s hold on a plain corner tile + PIN; adult typography | **PARTIAL** | Hold ✓, PIN ✓, adult typography *intended* but falls back to Cantarell (06 #20); no shuffle, no rate limit | P1 |
| G3 | Ask replaces every silent denial; outline-only tiles open the Ask flow | **PARTIAL** | No silent denials remain — every refusal speaks, with the right sentence for the right reason. The flow itself is absent | P1 |
| G4 | Parent sees/exports/deletes everything; nothing leaves; parent has stock GNOME | **PARTIAL** | See ✓, export ✓ (a directory), delete ✗, egress blocked ✓, ADR-0005 parent session ✓ | P1 |
| G5 | Parent drives updates; no surprise reboot mid-activity | **PARTIAL** | `sleep-inactive-*=nothing` and `power-button-action=nothing` locked ✓; greenboot rollback ✓; the panel that would drive `bootc upgrade` does not exist | P2 |
| H1 | No egress by default (nft + Flatpak unshare + NM polkit) | **PARTIAL** | All three layers built (`lockdown.md` §1.1). **Never observed** | P0 |
| H2 | Zero telemetry, no accounts, no profiling, no nudges; best interests recorded | **PARTIAL** | The first four are met; "recorded" is not | P2 |
| H3 | No conversational/generative AI in the child system | **MET** | ADR-0009 | — |
| H4 | Coarse age-bracket signal (AB 1043) | **N/A-yet** | — | P2 |
| H5 | Licensing ledger for every bundled asset | **PARTIAL** | `docs/LICENSES.md` is good and human-readable; not machine-readable, not CI-gated. The earcons are *generated*, so nothing to track — a genuinely elegant dodge | P2 |
| H6 | WCAG 2.2 AA, reduced motion honoured, one calm mode | **PARTIAL** | AA mostly exceeded; **reduced motion not honoured**; no calm mode | P1 |
| I1 | Enforcement below the session; immutable root; first-boot idempotent units | **MET** | nftables before `network-pre.target`; dconf locks in `/usr`; parent config root-owned with no fallback into the child's home (impl. notes §10) — the security-shaped gap the session-integration spike found is closed | — |
| I2 | Thin layer over upstream; don't fork the desktop | **MET** | GTK4/libadwaita, gnome-kiosk, RPM activities, `pyproject.toml` with no runtime deps | — |
| I3 | Every feature proven by an image, boot or shell test in CI | **PARTIAL** | 282 headless / 320 with a display; 93 image assertions; boot test; e2e scenario. **The e2e scenario is nightly/manual only**, and the egress claim has no test at all | P0 |

---

## 3. Deviations: on purpose vs by accident

### 3.1 On purpose, with a ruling behind them

| Deviation | Ruling | Assessment |
|---|---|---|
| **Targets shrink below the mm floor on small panels** (35 mm tiles, 14.9 mm `min_target` at 1280×800) | Impl. notes §9: *"the mm numbers are what we want, the panel is what we have"*; §14.1 offers the alternative (fewer tiles) and asks for a decision | **Correct instinct, wrong resolution.** A clipped control is worse than a small one — but the third option (fewer, bigger tiles) is available and is what 01 #12 wants anyway. This is the deviation that most deserves reversing. |
| **12 tiles, not 5** | SYNTHESIS B2 explicitly chose ≤12 over 01 #12's ≤5, on the strength of 08 §3.2's grid and the promise of progressive disclosure | **Half-honoured.** The ≤12 half shipped; the progressive-disclosure half did not, so the child gets the permissive number without the mitigation. |
| **400 ms transitions, not <250 ms** | Impl. notes §4.1 cites 08 §3.5: 350–450 ms is "legible as a journey"; under 250 ms "reads as a cut" | **Defensible and well-argued.** 06 #27 and 08 §3.5 genuinely disagree; 08 is the more specific source. Worth an ADR so nobody re-litigates it. |
| **Hover dwell 300 ms, not 600 ms** | Spec §3 pins 300 ms so a sweeping pointer hears the grid | Reasonable, untested. Put it in the child-test protocol. |
| **Ask removed from the band entirely** | Spec §7a: *"an always-disabled control teaches the child that buttons lie"* | **Right call**, and better than the alternative. It does mean the band's shape changes when the Ask flow lands — a one-time cost. |
| **Undo stays visible everywhere and says "Nothing to undo"** | Spec §7a, against 08 §3.4's "don't show controls that aren't available" | Spatial stability vs availability signalling. Genuinely contested; the spec picked one and said why. |
| **"Ask for more time" dismisses the offer** | Impl. notes §15.1: *"a child who has gone to find an adult must not come back to the same question"* | Excellent reasoning; a real improvement on §7a as written. |
| **Sleeping does not auto-wake while budget remains** | Impl. notes deviation 5 / §11: *"Goodnight means the sitting is over"* | Correct — the alternative weakens D2. |
| **No delete for the child** | 08 §4.3 | Directly conflicts with 03 #9 ("a 5-year-old can find and delete a drawing unaided"). Deliberate, but **unadjudicated** — see §4. |
| **Favourites evict quietly at 8** | Impl. notes deviation 2: refusing would need an error a pre-reader cannot read | Good. |
| **Budget day rolls at 04:00** | Spec §7a | Good, and the reasoning (a child awake at 00:30 is still having last night) is right. |
| **Earcons generated, not sampled** | Impl. notes §11, reversing v0.1.0's own position | Elegant — no binary blobs, no licence ledger entry. Unvalidated by ear. |
| **Firefox removed from the whole image** | ADR-0005 / `hardening.md`: "no web browser is a property of the machine, not of the session" | **Stronger than the research asked for.** Keep. |

### 3.2 By accident

| Deviation | Why it looks accidental |
|---|---|
| **`content_required` parsed and never checked** (`activities.py:122`) | Flagged in the implementer's own §15.4.2 as "one predicate away" and then not done. The Library tile currently opens nothing — the exact bug e2e §3.1 already caught once, reintroduced through a different door. |
| **`age_min` / `age_max` / `age_band` parsed and never used** | `tuxmath.toml`'s comment says "the shell should not show this to a four-year-old" and the shell does. Nobody decided this; it just was not wired. |
| **`"Atkinson Hyperlegible"` vs the shipped `"Atkinson Hyperlegible Next"`** | A silent font fallback nobody would notice without diffing `theme.css` against `36-fonts.sh`. |
| **`.not-allowed` border at 1.5:1 contrast** | The outline-only treatment is the *right* pattern (08 §3.4) rendered at a contrast that defeats it. No one computed the ratio. |
| **The tile-label 18 pt "floor" is multiplied by `fit`** | `Metrics.points()` was written to scale the theme, and `label_floor_pt` went through it too. A floor that moves is not a floor. |
| **The spoken Journal title can contain a clock time** (`journal.py:187`) | The shell bans digits everywhere the child can *see* them and then reads "Draw 14:32" aloud. |
| **No session-phase earcon** | 08 §3.6 lists six; four shipped; the two missing were both attributed to the absent Ask flow, but the phase motif has nothing to do with Ask. |
| **The offer is a fullscreen modal over the child's activity** | A consequence of the band-over-activity gap rather than a choice, and it lands on exactly the pattern 02 #4 warns about. |
| **No CI gate on egress, licences, or dependencies** | Three "testable:" clauses in 03 §3 with no test. AGENTS.md §5 says "a feature isn't done until a test proves it in CI." |

---

## 4. Where the literature is thin, contested, or absent — and what would settle it

1. **Does a continuously visible timer help or hurt?** (01 §5.2, 02 §5.7, SYNTHESIS §6.1.) The sun is the most distinctive thing we have built and it rests on practice literature, not trials. **What would settle it:** a within-family A/B — ten sessions with the sun, ten with the band's centre blank, parent-diary upset rating at the transition (Hiniker's 5-point scale). n=1 will not generalise but will tell *us*.
2. **Does 300 ms hover dwell chatter?** No evidence either way; 08 says ~600 ms from nowhere in particular. **Settle it:** count utterances per minute on Home at 300 / 600 / 900 ms and watch whether the child stops moving the pointer.
3. **Five choices or twelve?** 01 #12 (working memory ≈4–5 chunks) and 08 §3.2 (a 12-tile grid children learn by position) are both cited, both plausible, and they contradict. **Settle it:** time-to-first-launch and error rate on a 5-tile Home vs an 11-tile Home, same child, counterbalanced. This is the cheapest high-value study we could run.
4. **Can a five-year-old delete their own work, and should they?** 03 #9 (children's-rights: yes, testably) vs 08 §4.3 (design: never). **Settle it:** ask the child whether they can get rid of a drawing they hate, and see what they do. The rights argument is about *agency*, not about disk.
5. **Resume-not-open — does the concept land?** SYNTHESIS §6.2 says there is no published usability evidence for the Journal model at all. We cannot even test it yet, because resume plain-launches. **Settle it:** implement resume properly, then measure the resume-vs-new-entry ratio and whether the child ever returns to a card unprompted.
6. **Drag vs click-move-click** (01 §5.1, unresolved since 1998). KTuberling is our accidental experiment. **Settle it:** watch pick-up and release failures specifically; Hourcade says errors cluster there, not in the holding.
7. **What does an earcon need to sound like?** 01 §5.4: "non-speech audio design for children is nearly a blank." We have four generated sine motifs at an unmeasured level. **Settle it:** a meter, a room, and a child who is asked which of three "kept" sounds means "your drawing is safe".
8. **espeak-ng vs Piper for a five-year-old.** 06 #29 prefers Piper on quality grounds with no child-comprehension evidence. **Settle it:** the same twelve shell utterances in both voices, forced-choice ("which one is easier to understand?"), plus a comprehension check.
9. **Is a character necessary?** 08 §3.7 recommends one and admits the pedagogical-agent meta-analyses are equivocal and none is specific to 4–8s. We shipped none. **Settle it:** honestly, we cannot from n=1. Watch whether the ritual reads as impersonal or as calm.
10. **Does the ending ritual actually reduce upset?** The whole D-series rests on one 2016 study, n=28 families, non-randomised (02 §5.6). **Settle it:** parent diary across 15 sessions, coding trigger and upset. It is the one number in the product that matters.
11. **The 18 mm vs 24 mm floor.** 06 #13 says 18 mm minimum / 24 mm preferred from Hourcade's 64 px; 01 #1 says 24 mm floor from the same data. **Settle it:** Hourcade's own suggestion in 06 §9.1 — a 20-child, 44/64/96 px in-house replication on modern hardware. We would be publishing something.
12. **Whether any of this is why a session is bounded.** 01 §5.9 is blunt: no RCT establishes that a software-imposed limit improves wellbeing. We should keep saying so, as `grownup.py:30` already does.

---

## 5. Top ten fixes before the first child test

1. **Stop `fit` shrinking the floors.** Make `MIN_TARGET_MM`, `BAND_TARGET`'s mm component and `TILE_LABEL_MIN_PT` absolute; drop to a 4×2 or 3×2 grid instead. (`metrics.py`; shell.) *Fixes 01 #1, #2, #14; 06 #13, #21; A1, B4.*
2. **Cut Home to five tiles for the test** via `allowed_activity_ids` in `/etc/kidnix/parent.toml` — Draw, Potato faces, Letters & numbers, Copy the lights, All done. (parent config.) *Fixes 01 #12, B2; and sidesteps GCompris curation for one session.*
3. **Land the label-ellipsis fix and verify it on a fresh screenshot at 1280×800@102.** (shell — in flight.) *Fixes B4.*
4. **Hide the Library tile:** implement the `content_required` predicate next to `_denial()`. (`home.py` / `activities.py`; shell.) *Fixes 05 Lib-4 — a tile that opens nothing.*
5. **Decide the Tux Paint quit dialog** and write the decision down. Either accept it (and note that Sesame would approve of the tick/cross) or remove Tux Paint's Quit tool — which is only safe once the child has another way out. (activity-config + ADR.) *Fixes 01 #24, C2, 05 Draw-4.*
6. **Turn on Piper `en_GB-cori`** for the child session. The child's first impression of the voice is not a detail. (image.) *Fixes 06 #29.*
7. **Make the sun tappable** and give it a child-terms answer ("about as long as one story"), plus the missing session-phase earcon. (`band.py`, `sound.py`; shell.) *Fixes 08 §4.6, §3.6b — and it is the timer study's instrument.*
8. **Fix `.not-allowed` contrast to ≥3:1** and check the band-button ratio. (`theme.css`; shell.) *Fixes 06 #25, 03 #31 — the outline-only tile is the whole G3 affordance.*
9. **Prove the egress claim with a packet capture** in the VM and make it a CI assertion. We are about to put this machine in front of a child and tell a parent it holds. (image/CI.) *Fixes 03 #1, H1, I3, and AGENTS.md §5.*
10. **Write the child-test protocol** into `docs/plan/`: 20–30 minutes, observation-coded (time to first creation, target misses, burst-clicks, adult appeals, affect at the transition), Again-Again daily rather than Smileyometer once, another adult for any opinion data, continuous assent. (thinker.) *Fixes 01 #41–45, 03 #39.*

**Deliberately not in the top ten, and why:** band-over-activities is the single largest hole in the build (it takes out B3, C1, D3, 01 #15, #22, #30, 08 §3.2e at once) — but it is a compositor spike, not a fix, and one child test can be run with it broken as long as we *know* we are testing the shell and not the session. Ask-a-grown-up, the parent panel, letters-to-family, resume-that-resumes and GCompris curation are all P1s that will change the product more than any of the ten above; none of them is a *prerequisite* for learning something from one child.

---

## 6. Verdict

**Yes, we are adhering — unusually closely — and the failures are concentrated and legible.**

Of the ~230 numbered guidelines assessed, roughly 45% are MET, 35% PARTIAL,
10% MISSING, and 10% N/A-yet. That is a good ratio for a v0.1, and the quality
is better than the ratio suggests, because the MET items include almost every
guideline the literature is most confident about: the input model (press-only,
all-buttons-equal, 150 ms debounce, 700 ms double-click locked in dconf), flat
one-level navigation, no scrolling, no delete, no confirmations in the shell,
no autoplay, no streaks, no points, no telemetry, no browser, no LLM, an
analogue non-numeric timer, a machine-owned ending with a first-class
child-initiated path, and a Journal on disk as PNG and JSON that a parent can
open in Files. `grep -rin 'streak\|badge\|leaderboard'` over the shell returns
nothing. The dconf profile implements 06 §7.1 spec-by-spec and *locks* the ones
that matter. That is not a theme plus a package list; it is the research.

Three things are genuinely excellent and worth naming. First, **the honesty**:
`grownup.py:30` tells a parent that no session number is evidence-based, and
`gcompris.toml`'s `goal` tells them the activity is not curated yet. Nothing
else in this market does that. Second, **the reasoning-in-place**: the comments
in `home.py:190`, `ritual.py`, `band.py:8` and `suggestions.py` cite the
principle and argue the trade-off, which is why this audit could tell
deliberate deviation from accident at all. Third, **the fit-to-screen work**:
`_check_measured_fit` turns "the shell never exceeds the monitor" from an
intention into a measured fact, which is the difference between the clipped
`boot-home.png` and the clean contact sheet.

The failures cluster in four places. **(a) The physical floors bend.** The
whole point of specifying in millimetres is that a number does not move, and
`fit` moves them — 14.9 mm targets, 35 mm tiles and a 14.9 pt "18 pt floor" on
the panel we actually test on. **(b) The band vanishes during activities**,
which takes Back, Undo, the Ear and the sun away for the majority of every
session and turns the ending offer into the modal interruption the evidence
warns against. **(c) Parsed-but-unused fields** — `content_required`,
`age_min`, `age_band` — mean the shell will show a five-year-old a typed
arithmetic game and a library with no books. **(d) Claims without tests**:
zero egress is asserted three ways and observed zero times.

And two structural debts. The activities are upstream programs we do not
control, and the literature's per-activity rules mostly do not survive contact
with them: 16 visible tools in Tux Paint against 05's ≤8, ~190 uncurated
GCompris activities against 05's 12–20, star ratings and game-overs against
E1. The shell is exemplary; the *content* has barely started. And 01 #12's
five choices versus SYNTHESIS B2's twelve was resolved on paper and half-built
in code, which is the one place where we have taken the permissive reading of
our own constitution without the mitigation that justified it.

None of that is a reason to delay the first child test. It is a reason to spend
a day on the top ten first, and to be clear with ourselves that what we are
about to test is the *shell*, not yet the *system*.
