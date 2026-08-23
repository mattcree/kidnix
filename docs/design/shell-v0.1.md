# kidnix shell v0.1 — specification

> Thinker's spec, 2026-08-22. Derived from `docs/research/08-shell-ux-patterns.md`
> §5 (IA + wireframes), `SYNTHESIS.md` §2 (principles A–I) and ADR-0004
> (GTK4 + libadwaita, Python). Numbers come from SYNTHESIS §3. Anything not
> specified here: follow SYNTHESIS §2; if still unclear, pick the simpler
> option and note it in the implementation report.

## 1. Scope of v0.1

A single-profile, English (en-GB), mouse/trackpad-first, keyboard-optional
shell that can:

1. show **Home** with up to 12 activity tiles loaded from activity manifests;
2. **launch** an activity as a child process full-screen (under gnome-kiosk
   the newest window is on top; the shell regains the screen when the
   activity exits), track it, and clean it up;
3. keep **My Things (Journal)**: watch each activity's output directories,
   import new/changed files as entries with thumbnails, group by Today /
   Yesterday / Before, open an entry by re-launching its activity on that
   file ("resume"), star favourites;
4. run a **session**: a visible sun/timer band element that depletes
   continuously; at T−6 min an *Ending offer*; at T−2 min *Put away*; then
   *Goodbye* (shows what was made today, "Show a grown-up", "Goodnight"), then
   lock to a **Sleeping** screen until the next allowed session or a parent
   unlock;
5. **read aloud** every focused/hovered control via speech-dispatcher, with
   an **Ear** button that repeats the last utterance;
6. a **Grown-up** gate (3-second hold on a plain corner tile → PIN pad) that
   opens a minimal parent sheet: start/stop session, set session length, end
   session now, open the parent panel (stub), log out to GDM;
7. **Who's here?** profile chooser — v0.1 has one profile but the data model
   supports N (name, colour pair, avatar, age band);
8. be **testable**: every screen reachable via a documented state machine;
   widgets carry accessible names; a `--demo` mode runs with fake activities
   and a 3-minute session so CI can exercise the ending ritual; headless
   unit tests.

Out of scope for v0.1 (tracked in `docs/plan/PRIORITIES.md`): Ask-a-grown-up
queue, multi-child switching UX, parent panel proper, printing, sending,
band-over-activity (see §8), calm mode, on-screen keyboard.

## 2. Surfaces and state machine

States: `CHOOSING` → `HOME` ⇄ `IN_ACTIVITY`, `HOME` ⇄ `JOURNAL`,
`{HOME, IN_ACTIVITY, JOURNAL}` → `ENDING_OFFER` → `PUT_AWAY` → `GOODBYE` →
`SLEEPING` → `CHOOSING`. Plus `GROWNUP` (modal sheet, from any state).
Every transition is an animated spatial move (AdwNavigationView /
AdwCarousel / custom). There is no state without a visible way back to HOME
except SLEEPING (which needs the session to be allowed again or the gate).

### The band (top, 96 px, never hides, tinted in the child's colours)
`[Back] [Undo] [My Things] ······ [sun] ······ [Ear] [Ask] [Grown-up]`
- Back/Undo ≥ 80 px targets, ≥ 32 px apart. Back on HOME does nothing
  visible but speaks "You're home". Undo in v0.1 routes to the current
  shell action (e.g. un-star) — activities own their own undo.
- Ask is present but disabled-looking in v0.1 (outline), speaks "Asking a
  grown-up is coming soon". Grown-up is small, desaturated, far right, hold
  3 s.
- Sun: starts left, travels right and sinks as the session depletes; colour
  warms in the last 6 minutes. No digits anywhere.

### S1 Who's here? — avatar tiles ≥ 30 mm, child's colours, name spoken on
focus; plain Grown-up tile bottom-right.

### S2 Home — grid of tiles 160×160 px + 40 px label (scale by DPI so tiles
are ≥ 40 mm), ≥ 12 mm gaps, max 12 on one page, page dots if more.
Representational icon (from the manifest), label in Andika ≥ 18 pt, spoken on
focus/hover ("Draw"). Recently used tiles show a small thumbnail of the last
Journal entry from that activity. Not-allowed activities render outline-only
and speak "Ask a grown-up for this one" (no Ask flow yet).

### S3 Activity — the activity's full-screen window. The shell window
remains behind it. The shell: launches the process with a clean env (XDG dirs
under the kid home), records start time, watches the journal dirs, and on
exit returns to HOME with a soft "keep" earcon if new entries appeared.

### S4 My Things — favourites shelf (starred, bounded to 8, horizontal), then
Today / Yesterday / Before sections of cards ≥ 20 mm (thumbnail-dominant,
activity icon + star in the corner). Tap = resume. No delete. Day headings
spoken. No scrolling in v0.1: paginate with big arrows (8–12 cards per page).

### S5 Ending offer (T−6) — sun low; character line "The sun is going down";
two big buttons "Finish this one" / "One last little thing"; small
"Ask for more time" (in v0.1: speaks that a grown-up can add time from the
gate). If in an activity, the shell raises this as its own window — under
gnome-kiosk the newest window is on top; after the child chooses, the shell
lowers itself by hiding the offer window so the activity is back on top.

### S6 Put away (T−2) — no buttons; the current work animates into the
Journal with the keep earcon; the activity is asked to quit (SIGTERM after
autosave grace of 5 s, then SIGKILL), line "Let's keep that."

### S7 Goodbye — "You made N things today" + up to 3 thumbnails; buttons
"Show a grown-up" (opens Journal in read-only showing mode for 2 minutes, then
returns here) and "Goodnight" (→ SLEEPING). One concrete offline suggestion
line drawn from a small list keyed by the last activity ("You drew — can you
find something the same colour in the room?").

### S8 Sleeping — dim, warm, quiet screen with a sleeping sun/moon; tap
speaks "kidnix is sleeping. Ask a grown-up." Grown-up gate available.

### S9 Grown-up sheet (v0.1 minimal) — adult typography; PIN pad (default PIN
1234 for dev, stored hashed in parent-owned config); actions: Start session
(N min), End session now, Add 5/15/30 min, Set default session length, Open
parent panel (stub: opens a libadwaita about-window), Log out (→ GDM).

## 3. Read-aloud
- `speechd` (python3-speechd) client; en-GB voice; rate slightly slower than
  default; queue policy: new utterance cancels the previous (no backlog).
- Every focusable widget has `speak_text` (defaults to its accessible name);
  speak on keyboard focus and on pointer hover after 300 ms dwell (no
  repeat while the pointer stays), and on activation. The Ear repeats the
  last utterance.
- Paired visual highlight: the spoken widget gets a highlight ring while
  speaking.
- If speech-dispatcher is unavailable, degrade silently and log once.

## 4. Activity manifests (input contract)
TOML files in `/usr/share/kidnix/activities/*.toml` (and
`$XDG_DATA_HOME/kidnix/activities/` for dev). Fields: `id`, `name`,
`audio_label`, `icon` (icon name or path), `exec` (argv), `category`
(make/learn/play), `age_min`, `oars_rating`, `network_required`,
`journal_watch` (list of dirs, `~` expanded), `journal_glob` (e.g.
`*.png`), `goal` (one honest line for parents), `wayland_native`, `notes`.
The shell must tolerate missing optional fields and skip invalid files with a
log line. (The activities implementer is writing these; coordinate by
accepting this schema; add a `--validate-manifests` CLI that exits non-zero
on schema errors so CI can run it.)

## 5. Journal (storage contract)
- Root: `$XDG_DATA_HOME/kidnix/journal/` (kid home). Entries are directories
  `YYYY/MM/DD/<entry-id>/` with `entry.json` (id, activity_id, created,
  updated, title, source_path, mime, starred, versions[]) + `thumb.png` +
  optional `note.ogg` / `caption.txt`.
- Import: inotify (Gio.FileMonitor) on `journal_watch` dirs; on create/modify
  (debounced 2 s) copy the file into the entry dir as a new version;
  generate a thumbnail (PIL/GdkPixbuf) for images; for non-images use the
  activity icon.
- Resume: re-launch the activity with the source file as the argument when
  the manifest says it supports it (`exec_resume`), else plain launch.
- Open formats only; nothing proprietary; a plain directory tree the parent
  can browse.

## 6. Session (policy contract)
- Config: `/etc/kidnix/session.toml` (defaults: length 25 min, daily budget
  60 min, ending_offer_at 6 min, put_away_at 2 min, bedtime 19:00–07:00) and
  a kid-owned state file with today's usage.
- Timer runs in the shell process; a watchdog systemd user timer is a later
  backstop (lockdown spike).
- Ending rounds to a natural boundary *only* in the sense of the offer at
  T−6; the hard stop is the hard stop.

## 7. Engineering
- `shell/` is a uv project: `kidnix_shell` package, `pyproject.toml`,
  ruff, mypy (strict-ish), pytest; `just shell-*` recipes are added by the
  implementer in a new `shell/Justfile` (the root Justfile gains a one-line
  include/delegation later by the thinker).
- Headless tests: pure-Python modules (journal, session, manifests, state
  machine, speech queue) fully unit-tested without a display; GTK widget
  tests under `GDK_BACKEND=broadway` or `xvfb` where feasible, skipped if not.
- `kidnix-shell --demo` (fake activities that are tiny GTK windows writing a
  PNG to a temp journal_watch dir; 3-minute session) for CI/VM runs.
- Accessibility names on everything (this is also the test hook).
- Logging to the journal (systemd) via stderr; no telemetry; no network.
- Fonts: Andika (child-facing), Atkinson Hyperlegible (parent sheet) — ship in
  `system_files` later; the shell must fall back cleanly to Cantarell.

## 7a. Rulings on implementation questions (2026-08-22, after the first build)

- **Activity refuses SIGTERM:** SIGTERM → 5 s grace → SIGKILL, as built. The
  Journal importer has already captured autosaved files; losing unsaved
  in-memory state is acceptable and logged.
- **Resume:** manifests gain an optional `exec_resume` (argv with `{file}`);
  where an app cannot open a file from argv (Tux Paint uses its own saved
  gallery), plain launch is the correct behaviour and the card speaks "Open
  Draw to find it". Not a bug.
- **DPI:** keep physical-size scaling for tiles/targets; the band scales with
  the same factor, clamped to 80–128 px.
- **Sleeping ends** at the start of the next allowed schedule window (or a
  new day if no windows) or on a Grown-up unlock. Daily budget resets at
  04:00 local.
- **"I'm finished" (D5):** add a **Home tile** (last position, moon/bed icon,
  label "All done", spoken "All done for today?") that runs the same ending
  ritual from S6 onward — not a band slot. One tap, no confirmation; Back on
  the Put-away screen is disabled for 3 s then returns Home (accidental taps
  recover).
- **Inert controls:** Undo stays visible everywhere for spatial stability and
  speaks "Nothing to undo" when empty. **Ask is hidden** until the flow exists
  (an always-disabled control teaches the child that buttons lie).
- **Earcons:** ship four short generated tones (keep, tap, back, sleep) at
  −14 LUFS; no music.

## 8. Known gaps to spike after v0.1
- **Band over activities.** Research wants the band visible during an
  activity. Under gnome-kiosk (mutter) the shell cannot stay on top. Options:
  gnome-kiosk `window-config.ini` to give activities a fixed region below a
  96 px shell strip; or the shell becomes a tiny compositor later. Spike.
- Ask-a-grown-up, multi-child, printing, sending, calm mode.

## 7b. Rulings from checkpoint 1 (2026-08-22; see SYNTHESIS §4b, 09 §10)

- **S1b "What's next after?"** — a new screen between Who's here and Home:
  6–9 picture options (parent-configurable; defaults: go outside, a book,
  building, drawing on paper, snack, bath, help cook, play with someone) —
  the child picks one; Goodbye shows it back: "Ready to [thing]?" Replaces
  the generated suggestion line (keep it only as a fallback when nothing was
  chosen). Coco's Videos (CHI 2018).
- **The sun depletes by shrinking/sinking, not by travelling.** Redraw: a
  sun whose *height above the horizon and size* fall with remaining time;
  horizontal position fixed at centre. Tapping it speaks a child-terms
  estimate (no digits). The sun is state, not a warning.
- **Hover dwell 450 ms + settle gate** (speak only once pointer velocity has
  dropped below a threshold for the dwell); instrument every hover-speech
  (dwell ms, followed-by-selection?) in the local log for protocol P5.
- **Progressive disclosure**: first-run Home shows the first 5–6 tiles by
  `order`; one more tile appears after each N sessions (N = 2) up to the
  allow-list; parent can set "show everything" in parent.toml.
- **Earcons**: prefer representational auditory icons where a referent
  exists (paper rustle for "keep", soft door for "back", yawn/owl for
  "sleep"); generated tones only where no referent; licence any samples.
- **Gate**: not voiced; silent failure; attempts logged for the parent.
- **Exit friction**: none — "All done" and Back are never delayed except the
  3 s accidental-tap guard on Put away.

## 7c. Rulings after wave 5 (2026-08-22)

- **Put away must never destroy work.** At T−2 the shell does not cover the
  activity: it asks it to finish (SIGTERM; Tux Paint answers with its own
  tick/cross), the band speaks "Let's keep that — press the tick", and the
  content "Let's keep that" screen appears only when the activity has exited.
  Manifests gain `quit = "signal" | "confirm"` and `quit_grace` (Tux Paint:
  `confirm`, 30 s). SIGKILL only at the hard stop, after the grace, and it is
  logged as a loss. Spec §S6 is superseded accordingly.
- **Back in an activity asks and waits** (no SIGKILL); after the grace the
  band speaks "Draw is asking if you're done".
- ADR-0010 #5 stands: Tux Paint's tick/cross dialog is the activity's save
  step; `quit=yes` stays.

## 7d. Rulings from the expert panel (2026-08-23; see reviews/2026-08-23-SYNTHESIS.md)

1. Session floor 5 min (parent ≥ 3); refusal at Who's here *before* What's
   next after, in daytime words; sub-floor grants refused in the gate with the
   minimum named. Windows proportional with caps: offer = clamp(20%, 2–4 min),
   put-away = clamp(10%, 1–2 min); two beats always.
2. The offer is consequential: "Finish this one" defers put-away to T−1;
   "One last little thing" returns Home, put-away at the normal time; "Ask
   for more time" dismisses and names nobody. Offer buttons ADD to the band
   (Undo/My Things keep their cells) with a scale-in and the highlight ring.
3. Goodbye is led by the chosen destination (≥ 40 mm picture + headline,
   spoken last); one line of descriptive feedback from the Journal; "Show a
   grown-up" always visible; no return promises in daytime; the sun is held
   down from Ending offer through Sleeping/Resting; one sun metaphor only.
4. Two vocabularies on `is_bedtime`: daytime **Resting** (no moon/yawn; says
   *when* in child terms: "after tea" / "tomorrow") vs bedtime Sleeping.
   Resting/Sleeping speech ≤ once per 8 s, never cut mid-word, silent after
   three taps in 30 s; the whole content window is dim.
5. All done pinned to a fixed cell; progressive disclosure OFF by default.
   What's next after has "Not sure yet"; Back returns to Who's here.
6. Tiles use depictive icons of the output/action; the recent-work thumbnail
   is a corner badge, never the tile's picture.
7. Accessibility: one key controller across both toplevels, focus on every
   screen, real key-hold on the gate; a caption strip mirrors every spoken
   line; `calm = true` (reduced motion, softer/fewer sounds); earcon fades
   ≥ 150 ms; volume/mute control; focus ring and sun contrast ≥ 3:1 on the
   band; Sleeping/Resting paints the content window.
8. Target floor **20 mm** (Hourcade's physical figure), 24 mm preferred;
   supersedes checkpoint-1 item 15 (ADR-0011).
9. Voice: a 20 s "tell me about it" recorder on Let's keep that and on
   Journal cards (OGG `note.ogg` in the entry).
10. Research logging (hover-speech, PIN attempts, burst-click) behind
    `/etc/kidnix/research.toml enabled=false`; journald retention capped.
11. Per-profile journal/budget/progress; parent export and wipe; starter PIN
    detected and the gate forces a new one.
12. GCompris is a one-level **shelf** tile of the 18 curated children.
