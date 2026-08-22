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

## 8. Known gaps to spike after v0.1
- **Band over activities.** Research wants the band visible during an
  activity. Under gnome-kiosk (mutter) the shell cannot stay on top. Options:
  gnome-kiosk `window-config.ini` to give activities a fixed region below a
  96 px shell strip; or the shell becomes a tiny compositor later. Spike.
- Ask-a-grown-up, multi-child, printing, sending, calm mode.
