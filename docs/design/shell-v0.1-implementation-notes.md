# kidnix shell v0.1 — implementation notes

> Implementer's report on `shell/`, 2026-08-22. Companion to
> `docs/design/shell-v0.1.md` (the spec). Read the spec first; this records
> what was built, what was deviated from and why, and what the thinker needs to
> decide next.

## 1. Architecture

One process, one window, one band, one stack of surfaces.

```
ShellApplication (Adw.Application)
└── ShellWindow (Adw.ApplicationWindow)  ← the ONLY thing that touches the
    │                                      state machine, session and launcher
    ├── Band            back · undo · my things ·· sun ·· ear · ask · grown-up
    └── Gtk.Stack       S1 choosing · S2 home · S4 journal · S5 ending ·
                        S6 put away · S7 goodbye · S8 sleeping
        (+ GrownupSheet as an Adw.Dialog, S9)
        (+ a transient fullscreen offer window when S5 fires over an activity)
```

The split that matters is **pure logic vs GTK**. Nine modules have no GTK
import at all and carry the whole test suite:

| Module | Owns |
|---|---|
| `metrics` | mm ↔ px, DPI-aware sizing (SYNTHESIS §3 numbers) |
| `activities` | manifest loading/validation (spec §4) |
| `journal` | the storage contract (spec §5), import, versions, favourites, pagination |
| `session` | timing, phases, daily budget, bedtime (spec §6) |
| `state` | the navigation graph (spec §2) |
| `speech` | queue policy, hover dwell, backends (spec §3) |
| `launcher` | subprocess lifecycle, env cleaning, SIGTERM→SIGKILL |
| `settings` | XDG paths, parent config, PIN hashing, profiles |
| `suggestions` | the Goodbye screen's offline continuation lines |

The GTK side (`app`, `band`, `widgets`, `screens/*`) is thin glue. Screens own
layout only; anything that changes state goes through the `ShellHost` protocol
(`context.py`) to `ShellWindow`.

**`ChildButton` is the load-bearing widget.** Every child-facing control is
one, which is why the input rules from SYNTHESIS §2A live in exactly one place:
fires on *press* via a capture-phase `GestureClick` with `set_button(0)` (all
mouse buttons identical, no double-click, no right-click, no long-press, no
scroll, no modifiers), 150 ms debounce so eight clicks a second is one action,
and `speak_text` doubles as the GTK accessible name — one string for the screen
reader, our own read-aloud and the tests.

## 2. What is implemented

Everything in spec §1 items 1–8, plus:

- **The band.** 96 design px (scaled), never hides, tinted from the profile's
  colours via a display-level CSS provider. Sun drawn in Cairo: travels
  left→right along an arc, sinks, warms in the last six minutes, no digits.
  Grown-up gate is a 3 s `HoldButton` with a progress bar; sliding off cancels.
- **S1–S9** as specified. Home pages at 12 tiles with big arrows + dots
  (`Adw.Carousel` with every free-scroll affordance switched off); recently-used
  tiles carry a thumbnail corner; not-allowed tiles are outline-only and say
  "Ask a grown-up for this one". My Things has the favourites shelf (bounded to
  8), Today/Yesterday/Before, star, resume, and repeats the day heading when a
  group spans a page. Put away animates the last thing up-and-left towards My
  Things with `Adw.TimedAnimation`. Goodbye counts in *words* ("two things"),
  shows ≤ 3 thumbnails and one offline suggestion keyed to the last activity.
- **Read-aloud** via `speechd` (verified working on the host), falling back to
  `spd-say`, then to a logging no-op. Speaks on focus, on 300 ms hover dwell
  (once per enter, re-armed on leave), and on activation; new utterance cancels
  the previous; the Ear repeats; the spoken widget wears the reserved yellow
  highlight ring for an estimated utterance duration.
- **Journal** import via `Gio.FileMonitor` (2 s debounce) *plus* a 15 s safety
  sweep, because file monitors are unreliable across the filesystems an activity
  might save to and Tux Paint writes several files per save. Identical bytes are
  a no-op; changed bytes become `v002.png` on the same entry. Thumbnails via
  GdkPixbuf; non-images fall back to the activity icon. Nothing is ever deleted.
- **`--demo`**: 13 fake activities (a real scribble window that autosaves PNGs
  into its watch dir), a 3-minute session with the offer at T−60 s and put away
  at T−20 s, one activity outside the allow-list, and one that deliberately
  ignores `SIGTERM`. The whole demo world lives in a temp directory. The demo
  manifests are written as TOML and read back through the *real* loader, so
  every `--demo` run smoke-tests manifest parsing.
- **`--validate-manifests [DIR]`** — the ten shipped manifests in
  `system_files/usr/share/kidnix/activities/` all validate, and there is a test
  asserting that so the shell and the activities implementer cannot drift apart.

## 3. What is deferred, and why

| Deferred | Why |
|---|---|
| **Earcons** | The six-sound set is specified in `kidnix_shell/data/sounds/README.md` and the call sites (`sound.Earcons`, one-per-250 ms, ducked under speech) are wired. The files are not shipped: a synthesised sine pair is worse than silence for a sound heard 200×/day, and SYNTHESIS H5 wants a real licence provenance entry per file. |
| **Ask-a-grown-up** | Out of scope in the spec. The Ask button exists, is outline-only, and honestly says "Asking a grown-up is coming soon." Not-allowed tiles say the same rather than pretending a queue exists. |
| **Band over activities** | Spec §8's known gap. The shell window sits *behind* the activity; the ending offer is raised as its own fullscreen window (newest-on-top under gnome-kiosk) and closed again, which is what the spec asks for, but Back/Undo/Ear are unreachable while an activity is up. |
| **Child-initiated "I'm finished"** | SYNTHESIS D5 wants it first-class, but the spec's band has no such control and I did not add one to the child's chrome unilaterally. The state machine and `ShellWindow.finish_now()` fully support it; only the grown-up sheet's "End session now" currently calls it. **Decision needed** (§5). |
| **Word-by-word read-aloud highlight** | 08 §3.3 wants the spoken word highlighted. The shell speaks nouns, not sentences, so the whole-widget ring is the right granularity for now; sentence screens (S5, S7) get no word highlight. |
| **Calm mode / `prefers-reduced-motion`** | Out of scope in the spec. Motion is capped at one large animation at a time, so honouring the setting later is a small change. |
| **Fonts** | The CSS requests `"Andika"` and falls back to Cantarell. Andika is not installed on this host, so what I ran was Cantarell. Shipping Andika in `system_files` is the image implementer's call. |

## 4. Deviations from the spec (all deliberate)

1. **`Gtk.Stack` instead of `AdwNavigationView`.** The spec suggested
   NavigationView/Carousel. NavigationView is push/pop, which fits Home→Journal
   but fights the ritual sequence (you cannot "pop" from Goodbye to Home). A
   `Gtk.Stack` with the transition direction chosen per state gives the same
   "see the journey" reading — forward into the ritual slides left, back
   towards Home slides right — with 400 ms slides in the 350–450 ms band 08
   §3.5 asks for. `Adw.Carousel` *is* used, for Home and Journal paging, with
   `interactive`, `allow_mouse_drag`, `allow_scroll_wheel` and
   `allow_long_swipes` all off so it animates but cannot be scrolled (A4).
2. **The favourites shelf bound is enforced by quiet eviction.** Spec says
   "bounded to 8". Starring a ninth silently unstars the least-recently-starred
   rather than refusing. Refusing would need an error a pre-reader cannot read.
   This needed one field the spec's `entry.json` list does not name,
   `starred_at`; it is additive and the loader tolerates its absence.
3. **The parent config is TOML, hand-written.** Spec §5/§6 name `session.toml`;
   for symmetry the mutable parent config is `parent.toml` too. `tomllib` cannot
   write, so `settings.py` has a ~15-line dumper for our flat schema rather than
   a third-party dependency. PIN is PBKDF2-SHA256, 200k rounds, per-config salt.
4. **Manifest schema is the union of the spec's and the shipped files'.**
   The spec names `goal`, `journal_glob`, `exec_resume`; the shipped manifests
   use `schema`, `icon_kind`, `age_max`, `source`, `package`, `licence`,
   `content_required`. All are accepted; unknown fields are logged at debug and
   ignored, so the activities implementer can add fields ahead of the shell.
   Only `id`, `name` and a non-empty `exec` are required.
5. **Sleeping does not auto-wake as soon as budget remains.** "Until the next
   allowed session" would re-wake seconds after Goodnight, since the daily
   budget usually still has time in it. The shell wakes on its own only when the
   day has rolled over or the bedtime window that put it to sleep has ended;
   otherwise the grown-up gate is the way back. See §5 Q4.
6. **No `--config` for the *session* policy under that name.** `--config` is the
   parent config (as asked); the session policy is `--session-config`.

## 5. Questions for the thinker

**Q1. What happens when an activity refuses SIGTERM?**
Currently: put away sends `SIGTERM` to the activity's *process group*, waits the
5 s autosave grace on a GLib timer (the keep animation keeps playing), then
`SIGKILL`s the group. Verified end-to-end with the demo's deliberately stubborn
activity. Two things are unresolved:
- The child sees "Let's keep that" for 5 s and then the activity vanishes
  underneath the shell. Should the shell say something different when it had to
  escalate ("That one was slow to tidy up"), or stay silent?
- We `SIGKILL` a process that may be mid-write. The Journal's write-then-rename
  protects *our* entry.json, but not the activity's own save file. Do we want
  the grace to be longer for known-slow activities (a manifest field
  `autosave_grace`), or is 5 s the contract activities must meet?

**Q2. How should resume pass a file?**
Implemented as spec §5 says: `exec_resume` with an optional `{file}` token,
appended if the token is absent, plain launch if `exec_resume` is missing. But
*none of the ten shipped manifests declares `exec_resume`*, so in practice every
Journal card currently does a plain launch and the child lands in the activity's
own file picker — which is exactly the "no file browser" thing we promised not
to do. Options: (a) the activities implementer adds `exec_resume` per app
(Tux Paint has no open-a-file argument, so this may be impossible for the anchor
activity); (b) the shell copies the entry's latest version *back* over the
activity's working file before launching, so the app opens its own last save;
(c) accept that v0.1 resume is "reopen the activity" and rename the affordance.
I would pick (b) for image-based activities and want a decision.

**Q3. Is the DPI approach right?**
`Gdk.Monitor.get_geometry()` (logical px) × `get_scale_factor()` ÷
`get_width_mm()`, clamped to 60–400 dpi, falling back to 96 dpi when the
compositor reports nonsense (VMs report 0 mm). On this host that reads 118 dpi
and gives a 198 px tile = 43 mm, comfortably over the 40 mm floor. Two open
points: multi-monitor (we take monitor 0 and never re-measure if the window
moves), and whether the *band* should also scale physically — I made it
`max(96 design px, 24 mm)`, which is a judgement call the spec does not cover.

**Q4. When does Sleeping end?**
See deviation 5. The spec says "until the next allowed session or a parent
unlock". If the intended reading is "there is still budget, so let them back
in", say so and I will change it — but then Goodnight is not an ending, and D2's
"the machine ends the session" weakens.

**Q5. Should the child have an "I'm finished" control?**
D5 says child-initiated ending is first-class; the spec's band has no room for
it. Where does it live — a ninth band button, a tile on Home, or the Back button
held down? (Not held down, I'd argue: no child control should need a hold.)

**Q6. Undo.** Spec §2 says Undo "routes to the current shell action (e.g.
un-star)". Implemented as: in My Things it un-stars the most recently starred
thing; everywhere else it says "Nothing to undo here." That is honest but thin —
a fixed band button that usually does nothing may teach a child it is decorative.
Should it be hidden outside My Things instead (08 §3.4: don't show controls that
aren't available)?

**Q7. The `Ask` button.** It is present, outline-only, and speaks
"Asking a grown-up is coming soon." Same objection as Q6: is a permanently
non-functional button in a five-year-old's fixed chrome better or worse than an
absent one for the two months until the Ask queue lands?

## 6. Known issues

- **Screenshots could not be taken.** GNOME 45+ restricts
  `org.gnome.Shell.Screenshot` to the Shell's own UI; the call returns
  `AccessDenied` for any other caller, and `grim` needs wlr-screencopy which
  Mutter does not implement. The shell *was* run for real on the host's Wayland
  session and driven through every state (see §7). VM screendumps via QMP
  (ADR-0004's plan) will be the way to get images.
- **The 2-minute "Show a grown-up" timer keeps running if the child presses
  Goodnight during it.** Harmless — the callback fires into a state where
  `SHOWING_DONE` is invalid and is ignored — but it is a stray timer.
- **`Gtk.Label.set_ellipsize(3)`** in `widgets.py` uses the numeric enum value
  because importing Pango just for one constant felt disproportionate. Tidy
  later.
- **The journal index is in memory only.** `Journal.load()` globs
  `*/*/*/*/entry.json`; at a few thousand entries that is fine, at a hundred
  thousand it is not. A child would need years to get there, but note it.
- **`ShellWindow` is ~450 lines** and is doing host, tick and ritual
  orchestration. If it grows further the ritual should move out.

## 7. How to run and test

```bash
cd shell
just setup              # uv venv --system-site-packages + pytest/ruff/mypy
just demo               # the whole ritual in three minutes, windowed
just smoke              # ten seconds of the demo, then quit (CI)
just test               # 219 tests
just test-headless      # 193 tests + 1 skip, no display needed (the CI floor)
just lint               # ruff check + ruff format --check + mypy (strict-ish)
just validate-manifests # gates the shipped activity manifests
just ci                 # lint + test-headless + validate-manifests
```

The venv is created with `--system-site-packages` because PyGObject, GTK4,
libadwaita, GdkPixbuf and `speechd` come from the system — they are already in
the image, and building PyGObject in a venv needs a whole introspection
toolchain. `pyproject.toml` declares **no runtime dependencies**.

**Verified on this host** (Bluefin/Fedora 44, GTK 4.22.4, libadwaita 1.9.3,
Python 3.14, Wayland): the shell started, detected 118 dpi, connected to
speech-dispatcher, and was driven through
`CHOOSING → HOME → IN_ACTIVITY → ENDING_OFFER → IN_ACTIVITY → PUT_AWAY →
GOODBYE → SLEEPING → GROWNUP → SLEEPING`, launching a real child process,
importing the PNG it wrote through the file monitor, starring it, and killing a
`SIGTERM`-refusing activity after the grace period.

## 8. Handover notes for the image

- Install the tree at `/usr/lib/kidnix/shell/` and point
  `system_files/usr/bin/kidnix-shell`'s `KIDNIX_KIOSK_APP` at a launcher that
  runs `python3 -m kidnix_shell` with that on `PYTHONPATH`. Nothing else in that
  script needs to change.
- Runtime requirements: `python3-gobject`, `gtk4`, `libadwaita`,
  `gdk-pixbuf2`, and `python3-speechd` (optional but wanted).
- `/etc/kidnix/session.toml` is read if present; without it the defaults are
  the SYNTHESIS §3 numbers.
- Andika should land in `system_files` with a licence ledger entry; the shell
  falls back to Cantarell cleanly until it does.

---

# shell v0.1.1 — fitting the screen, owning the config, and the §7a rulings

> Second implementer's report on `shell/`, 2026-08-22. Additive to everything
> above: §1–§8 describe v0.1.0 and are still accurate except where this section
> says otherwise. Driven by the first real boot
> (`docs/design/screenshots/boot-home.png`), the open questions in
> `docs/spikes/session-integration.md` §7, and the §7a rulings in the spec.

## 9. Fit to screen — the clipped band

**The bug.** v0.1.0 sized everything from millimetres and never asked whether
the result fitted. On the VM's 1280×800 / 102 dpi panel the layout wanted about
6% more than the panel had, so the band's buttons were cut off the top of the
screen and the Grown-up tile ran off the bottom-right corner. A control a child
cannot see is worse than one that is 3 mm small.

**The fix, in two layers.**

1. **Arithmetic.** `Metrics` gained `screen_width`/`screen_height` and a single
   `fit` factor that multiplies `mm()` and `design()` — so every size in the
   shell shrinks together. `Metrics.for_screen()` computes the mm-based ideal,
   then shrinks until `required_size()` (band + Home grid + pager + every
   margin, modelled explicitly) fits the monitor. `fit` is exactly 1.0 whenever
   the ideal already fits, which is 1920×1080 and up.
2. **Measurement.** Arithmetic cannot know about CSS padding or font metrics,
   so `ShellWindow._check_measured_fit()` asks GTK how big the built tree
   actually wants to be and, if that exceeds the monitor, shrinks and rebuilds
   (at most three times, before the window is presented). This is what makes
   "never exceeds the monitor" a fact rather than an intention. It logs the
   measured size on every start, so a future clipped screenshot has a number
   next to it.

Rebuilding is a real code path now (`_build_content()`), which also gives us
**monitor changes**: every 8th tick the shell re-reads the monitor and relays
out if the geometry, density or scale changed. Screens hold no state that
outlives them, so throwing them away is safe.

Two supporting changes fell out of it:

- **Band buttons are sized to fit inside the band** (`Metrics.band_target`),
  because the band is clamped to 80–128 px per §7a and an 86 px button inside a
  102 px band plus 20 px of CSS padding is exactly how the tops got cut off.
- **Type scales with the layout.** `theme.css` states point sizes and points do
  not know about `fit`, so `theme.py` re-emits every child-facing size at the
  layout's own scale through the runtime CSS provider.

**What it costs.** On 1280×800 the tile is 35 mm rather than 40 mm (at 118 dpi,
31 mm). That is under SYNTHESIS §3's floor and it is the deliberate trade: the
mm numbers are what we want, the panel is what we have. On a genuinely small
panel Home drops to a 4×2 grid rather than shrinking twelve tiles below 128 px.

Measured, all fitting, from the tests:

| Panel | fit | tile | band | grid |
|---|---|---|---|---|
| 1280×800 @96 | 0.88 | 142 px (38 mm) | 85 px | 4×3 |
| 1280×800 @102 | 0.83 | 141 px (35 mm) | 85 px | 4×3 |
| 1280×800 @118 | 0.72 | 142 px (31 mm) | 85 px | 4×3 |
| 1366×768 @96 | 0.85 | 136 px (36 mm) | 82 px | 4×3 |
| 1920×1080 @96 | 1.00 | 160 px (42 mm) | 96 px | 4×3 |
| 3840×2160 @2× | 0.81 | 191 px (34 mm) | 115 px | 4×3 |
| 2560×1440 @118 | 1.00 | 197 px (42 mm) | 118 px | 4×3 |
| 1024×600 @96 | 0.86 | 138 px (37 mm) | 83 px | 4×2 |

`--screen 1280x800@102` (also `KIDNIX_SCREEN` / `KIDNIX_FORCE_DPI`) makes a
27" desktop render exactly what a small panel gets; `just demo-small` is that
in one word. `docs/design/screenshots/demo-home.png` and `demo-all-done.png`
are 1280×800 @102 captures with nothing clipped.

**Screenshots are possible after all.** §6 above says GNOME 45+ lets no
external tool photograph the kiosk — true, and irrelevant to photographing
*ourselves*: `--screenshot PATH` paints the shell's own widget tree into a
`Gtk.Snapshot` and renders it with the renderer we already have. No portal, no
permission, no QMP.

## 10. The parent config is no longer child-writable

Session-integration spike open question 2, "the one security-shaped gap this
milestone introduces". `Paths.parent_config` used to fall back to
`~/.config/kidnix/parent.toml`, which the child owns — so the PIN, the
allow-list and the profiles were child-writable in principle.

Now: `/etc/kidnix/parent.toml`, then `/usr/share/kidnix/parent.toml`, then
built-in defaults with a **loud stderr banner** naming the dev PIN. There is no
fallback into the child's home at all; `--config PATH` is the single exception
and exists so a developer can point at a file. `session.toml` follows the same
rule. Everything kid-writable (today's usage, the Journal and its favourites,
the generated earcons) stays under `XDG_STATE_HOME` / `XDG_DATA_HOME` /
`XDG_CACHE_HOME`, and nothing in any of it can widen what the child may do.

A config loaded from a system path is marked `read_only`, and `save()` on one
raises rather than pretending. The grown-up sheet therefore changes the default
session length **for this boot only** and says so in the row's subtitle, and
shows a red row when the machine is running on the built-in defaults. Making a
change permanent means writing `/etc/kidnix/parent.toml` as root — the parent
panel's job, from the parent's own account, and now a well-defined one.

**For the image implementer:** nothing is required, but shipping
`/usr/share/kidnix/parent.toml` (a PIN hash and an allow-list) would take the
dev-PIN banner off a real child's machine, and bootc's 3-way merge would keep a
parent's `/etc` edit across upgrades.

## 11. The §7a rulings

- **"All done" tile.** Last position on Home, always (page 2 when there are
  twelve activities), moon icon, calm lavender rather than a treat colour,
  speaks "All done for today?". One tap → `finish_now()` → Put away → Goodbye.
  No confirmation: a pre-reader cannot read one, and asking a child to confirm
  that they have had enough is a bribe to stay.
- **Back on Put away** is dead for 3 s (`PUT_AWAY_BACK_LOCK_SECONDS`) and then
  returns Home, so an accidental tap is recoverable. It is *ignored*, not
  greyed out and not hidden: the band never changes shape under a child. The
  state machine gained `PUT_AWAY --back--> HOME`; if the *clock* put the child
  there, the next tick simply brings the ritual back.
- **Goodbye is now timed for the child-initiated path.** The clock-driven
  ritual reaches Goodbye at `Phase.ENDED`; "All done" has no clock, so
  `finish_now()` schedules it (6 s, covering the SIGTERM grace and the keep
  animation) and the callback checks the state first, so pressing Back does not
  strand a timer that drags the child into Goodbye anyway.
- **Ask is gone from the band** (`band.SHOW_ASK = False`, one line to put it
  back). Undo stays on every surface and says "Nothing to undo."
- **Sleeping** wakes on a new *budget* day or when the bedtime window that put
  it to sleep has ended — otherwise the gate. Unchanged in spirit from
  deviation 5, now expressed against the 04:00 boundary.
- **Daily budget resets at 04:00**, not midnight (`session.budget_day()`).
  `may_start()` rolls the day itself, so a shell that has been sitting on the
  Sleeping screen all night sees the fresh budget without a restart.
- **`exec_resume` with `{file}`** was already implemented in v0.1.0 and is
  unchanged; still no shipped manifest declares it (Q2 above is still open).
- **Earcons: four, generated.** `keep` (E5→B5 rising), `tap` (one A5 tick),
  `back` (D5→G4 falling), `sleep` (E4→A3, low and slow). Sine tones with an
  exponential decay and 6 ms fades, 16-bit mono 44.1 kHz, peak 0.45 — roughly
  −14 LUFS *by construction, not by meter*. Written by
  `python -m kidnix_shell.sound [DIR]` at image build (`just earcons`) or
  generated on first run into `$XDG_CACHE_HOME/kidnix/sounds` because `/usr` is
  read-only; 13 ms for all four, warmed on an idle callback at startup. No
  binary blobs in git and nothing for `docs/LICENSES.md` to track. Playback is
  GStreamer `playbin` built lazily; no GStreamer, no sink or a pipeline error
  logs **once** and the shell runs silent for the rest of the run. Verified
  playing on this host; nobody has confirmed what it sounds like in a room.

  This reverses v0.1.0's "a synthesised sine pair is worse than silence".
  Having built them: for a 90 ms tick heard 200×/day, contour is the whole
  message and a composed sample would not be a better one. If the human
  disagrees after hearing them, `EARCONS` is eight lines to re-point at files.

## 12. Robustness in the kiosk

`SpeechdBackend` now **connects on the first utterance, not at startup**, and
reconnects on its own at most once every 5 s, logging each state change once
rather than per event (a child sweeping a grid of tiles used to be able to fill
the journal). `select_backend()` is a module-import check and opens no socket,
so nothing in startup can block on speech-dispatcher — which, with the unit's
`Wants=speech-dispatcher.socket` from the spike, means a restarting daemon is
now invisible to the child instead of an 11-second black screen. Earcons have
the same discipline: one log line, then silence, never an exception on the main
loop.

## 13. Tests

**282 headless (+1 skip), 320 with a display** (was 193/219). New coverage:
the fit-to-screen arithmetic across eight panels including 1280×800 at three
densities and 3840×2160 @2× (band clamp, band-button-inside-the-band, tile
still touchable, grid choice); the config ownership rules including "a
parent.toml in the child's home is not a parent config"; the four earcons
(rendering, levels, fades, the 250 ms gap, ducking, generation into an
unwritable world); speech lazy-connect and reconnect; the 04:00 budget day; and
— with a display — a real `ShellWindow` measured against four panels and driven
through All done → Put away → Back → Home → All done → Goodbye.

## 14. Still open

1. **The 40 mm floor is now advisory on small panels** (31 mm at 1280×800 @118).
   The alternative is clipping. If the floor is genuinely hard, the answer is
   fewer tiles per page on those panels — say so and it is a two-line change to
   `MIN_GRID_TILE_PX`.
2. **`/usr/share/kidnix/parent.toml` is not shipped** (that is `system_files/`,
   not mine), so a booted image still prints the dev-PIN banner.
3. **Nobody has heard the earcons** on real speakers, and no meter has seen
   them.
4. Q1, Q2 and Q4–Q7 of §5 above are answered by §7a and implemented here;
   **Q3 (DPI)** is answered by §9. Q2 (resume) is still open on the *manifest*
   side.

---

## 15. The two e2e bugs, and the manifest labels (second pass, 2026-08-22)

Fixes for `docs/spikes/e2e-scenario.md` §3.1 and §3.2, plus the kid-facing
naming the spec assumed but the manifests did not have.

### 15.1 The ending offer asked twice (§3.2)

`app._advance_ritual` recomputed the ritual from the clock on **every** 500 ms
tick, so `DISMISS_OFFER` → HOME was immediately followed by
`ENDING_OFFER_DUE` → ENDING_OFFER, for the whole four-minute window. A child
answered the question and the machine asked it again, and "One last little
thing" was indistinguishable from "Finish this one".

The fix is two pieces, both testable without a display:

- **A latch on the session.** `Session._offer_answered`, cleared by `start()`
  and `end()`, set by `answer_offer()`, and **re-armed by `add_minutes()` only
  when the grant pushes the remaining time back past `ending_offer_at`**. A
  grown-up who adds fifteen minutes has created a new ending, and a new ending
  deserves one warning; a grant of one minute inside the offer window has not,
  and re-asking there would be the nagging the latch exists to stop.
- **A pure decision.** New `kidnix_shell/ritual.py`: `next_action(phase, state,
  offer_answered) -> RitualAction`. `_advance_ritual` is now four lines of
  dispatch. The ritual's whole policy — including "never interrupt the grown-up
  sheet" and "Put away happens regardless" — is one function with no clock, no
  GTK and no I/O, and `tests/test_ritual.py` walks a fake shell through whole
  sessions at 4 Hz asserting the offer count.

`ENDING_OFFER → DISMISS_OFFER → _offer_return` already did the right thing for
"stays where they were", so **the state machine did not change**. Home stays
Home, so "one last little thing" is simply Home continuing to work; the test
asserts `LAUNCH_ACTIVITY` is still available afterwards.

One deviation from §7a as written: **"Ask for more time" now dismisses too.**
It speaks the same honest line ("A grown-up can add more time. Go and ask
them.") and then gets out of the way. A child who has gone to find an adult
must not come back to the same question, and leaving the offer up made
"ask" the only choice that did nothing.

### 15.2 A tile that launches nothing (§3.1)

Three layers, because the failure has three:

1. **Not shown.** `Availability` (in `activities.py`) resolves `exec[0]` on
   `PATH` and, for `flatpak run <ref>`, runs `flatpak info <ref>`. One probe per
   *program*, cached for the boot, both injectable so tests never touch `PATH`.
   `resolve_availability()` stamps `Activity.available`; `cli.main` calls it
   once at startup. Unavailable activities stay in the list — the Journal must
   still be able to name the activity an old entry came from — and
   `Activity.on_home` is what Home filters on.
2. **Or shown honestly.** `show_when_unavailable = true` keeps the tile,
   outline-only, speaking *"This one isn't ready yet. Ask a grown-up."* — a
   different sentence from the not-allowed *"Ask a grown-up for this one."*,
   because sending a child to ask for something nobody can give them is not
   G3, it is a runaround. `turbowarp.toml` sets it **false** until the Flatpak
   is really installed by an online boot.
3. **And if it still fails.** `RunningActivity.failed_to_open(code)` is true for
   a non-zero exit inside `FAST_FAIL_SECONDS` (3 s). The shell then speaks
   *"That one didn't open. Let's try something else."* — no error text, no code
   — and logs the stderr tail at WARNING for the parent's journal. stderr is
   captured to an **unnamed temporary file**, not a pipe: nobody reads it while
   the activity runs and a full pipe buffer would block a child's drawing
   program mid-stroke. It is closed after `on_exit`, and by `stop()`.

Note that (1) means the child never *sees* (3) for a missing program; (3) is
the backstop for the launch that fails for a reason a `which` cannot predict
(a missing library, a broken config, a crash on the splash screen).

### 15.3 Tiles are named for what the child does

Every shipped manifest's `name`/`audio_label` is now the **activity**, not the
product (SYNTHESIS B4, 05 §3): Draw, Potato faces, Make a game, Letters &
numbers, Letter sounds, Number game, Copy the lights, Mini golf, Jump and run,
Library. `audio_label` is the spoken form of the same label, which is why it
differs in exactly two places ("Letters and numbers" because `&` does not
speak; "Make a potato face" because the tile has room for two words and the ear
has room for four). Every manifest also gained an honest one-line `goal` for
the parent panel — the place where "a jump-and-run game with a game-over state"
and "not curated yet — some are pitched well above five" belong.

`order` (int, small first; no `order` sorts last, by filename) replaces the old
`(category, name)` sort. Making comes first, then learning, then play, then the
Library: Draw 10 → Library 100, with "All done" always last on its own rule.
`--validate-manifests` now prints the grid in that order with the name and
flags a manifest with no `goal`.

**Consequences for other people's files:**

- `tests/e2e/test_scenario.py` has `DRAW_ROW, DRAW_COLUMN = 1, 2` with a
  comment about `(category, name)`. With `order` — and TurboWarp no longer
  drawn at all — **Draw is row 0, column 0**. The step asserts
  `launched tuxpaint` in the journal, so it fails loudly rather than silently,
  but it needs the two constants changed.
- The same file's open question "assert `speaking: Tux Paint. Draw a picture.`"
  becomes `speaking: Draw`.
- `docs/spikes/activities-packaging.md` documents the manifest schema and does
  not yet mention `order`, `show_when_unavailable` or `goal`. Not edited here
  (not this task's file).

### 15.4 Still open after this pass

1. **The two outline-only tiles look identical.** Not-allowed and not-installed
   render with the same dashed outline and differ only in what they say. If the
   distinction matters visually, it wants a second treatment — a taste call for
   the human, not a code change.
2. **`content_required` is still not implemented.** `kiwix.toml` sets it and
   asks the shell to hide the Library until a ZIM exists; `kiwix-serve` is
   installed, so availability alone leaves the tile up and the child opens an
   empty library. Same shape as `available`; one predicate away.
3. **`flatpak info` is run on the main thread at startup.** Five-second timeout,
   one call for the one Flatpak we ship. If the Flatpak list grows this belongs
   off the startup path.
