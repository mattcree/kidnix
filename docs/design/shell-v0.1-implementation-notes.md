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

---

## 16. v0.1.3 — the audit fixes (shell side, 2026-08-22)

> Implementer's second report. Everything here answers a row in
> `docs/design/cci-compliance-audit-2026-08-22.md` — §3.2 "by accident" and §5
> "top ten" — and nothing here changes a decision §3.1 says was deliberate.
> The sections above are unchanged; this one is additive.

### 16.1 The floors are floors again (audit §5 #1; 01 #1, #2, #14; 06 #13, #21; A1, B4)

The audit's sentence is the whole fix: *"a floor that moves is not a floor."*
`Metrics` now separates two kinds of number.

* **Floors — `fit` never touches them.** `MIN_TARGET_MM` (18 mm),
  `GAP_FLOOR_MM` (8 mm, new) and `TILE_LABEL_MIN_PT` (18 pt). They are computed
  from the panel's real density by `Metrics.mm_floor()` and that is the end of
  it. `Metrics.label_floor_pt` is now the constant, not `points(18)`.
* **Preferences — `fit` shrinks them.** The 160 design-px tile, the 40 mm
  primary tile, the 12 mm preferred gap, the 96 px band, the icon's share of a
  tile, the margins.

When the ideal will not fit, the cost is paid in this order, which is the order
the audit asked for:

1. **Chrome.** A new `chrome_fit` factor narrows the gaps toward 8 mm, the
   band's spare height and the pager, and nothing else. A child loses nothing
   when 12 mm of dead space becomes 9 mm. `CHROME_STEPS` is the ladder.
2. **The grid.** `Metrics.for_screen` still walks `GRIDS` (4×3 → 4×2 → 3×2) but
   the acceptance test is now `MIN_GRID_TILE_MM` (= 40 mm) instead of
   `MIN_GRID_TILE_PX` (= 128 px, which is 34 mm at 96 dpi and 27 mm at 118).
   Whatever does not fit on the page paginates, which Home already did.
3. **The tile**, and never past 18 mm.

`ShellWindow._check_measured_fit` spends in the same order (`Metrics.shrunk_by`
reduces `chrome_fit` before `fit`), and `MAX_FIT_ATTEMPTS` went 3 → 5 because
each step is now smaller. All of them still happen before the window is shown.

Two consequential knock-ons:

* **`theme.py` floors type at 18 pt.** `Metrics.child_points()` is
  `max(points(base), 18)`, and both `points_for()` (what a widget fits a label
  into) and `font_css()` (what the display provider emits) go through it. The
  grown-up sheet's own type is not in `BASE_POINTS` and is deliberately not
  floored: an adult reads 12 pt happily and 08 §4.5 wants the sheet to feel
  adult.
* **`avatar_size` and `card_size` are chrome-scaled** above their own mm floors
  (30 mm and 20 mm). Who's here? is the *tallest* surface in the stack on a
  small dense panel — taller than Home — so it was the thing actually binding
  the measured fit at 1280×800 @118, and a 40 mm face is still a face.

**The result, per panel** (arithmetic; `Metrics.describe()` prints all of it,
and `tests/test_metrics.py` asserts every floor on every row):

| Panel | fit / chrome | grid | tile | gap | min target | band button | label floor |
|---|---|---|---|---|---|---|---|
| 1280×800 @96 | 1.00 / 1.00 | 4×2 | 42.3 mm | 12.2 mm | 18.3 mm | 20.1 mm | 18 pt |
| 1280×800 @102 | 1.00 / 1.00 | 4×2 | 42.3 mm | 12.2 mm | 18.2 mm | 20.4 mm | 18 pt |
| 1280×800 @118 | 1.00 / 0.82 | 4×2 | 42.4 mm | 9.9 mm | 18.1 mm | 18.1 mm | 18 pt |
| 1366×768 @96 | 1.00 / 1.00 | 4×2 | 42.3 mm | 12.2 mm | 18.3 mm | 20.1 mm | 18 pt |
| 1920×1080 @96 | 1.00 / 1.00 | 4×3 | 42.3 mm | 12.2 mm | 18.3 mm | 20.1 mm | 18 pt |
| 3840×2160 @2× | 1.00 / 1.00 | 4×2 | 42.3 mm | 12.1 mm | 18.0 mm | 19.5 mm | 18 pt |
| 2560×1440 @118 | 1.00 / 1.00 | 4×3 | 42.4 mm | 12.1 mm | 18.1 mm | 21.1 mm | 18 pt |
| 2560×1440 @2× | 1.00 / 0.70 | 4×2 | 42.5 mm | 8.5 mm | 18.2 mm | 18.2 mm | 18 pt |
| 1024×600 @96 | 0.88 / 0.35 | 4×2 | 37.3 mm | 8.2 mm | 18.3 mm | 18.3 mm | 18 pt |

Compare v0.1.2 on the panel we test on: 1280×800 @102 was `fit = 0.83`, a
35.1 mm tile, a 14.9 mm minimum target and a 14.9 pt label floor. **Every
number on the 1280×800 rows is now inside its guideline**; the price is eight
tiles a page rather than twelve, which is a step *toward* 01 #12 rather than
away from it.

**Residuals, stated rather than hidden.**

* **1024×600** (a netbook we do not ship for) cannot hold a 40 mm tile: it
  settles at 37.3 mm. Every floor holds; the preference does not.
  `test_a_netbook_is_the_one_panel_that_costs_a_millimetre` pins it.
* **The band clamp.** Spec §7a's 80–128 px and the 18 mm button are now
  satisfied *together*: `band_height`'s lower bound moves up to
  `min_target + BAND_CHROME_PX` (the CSS padding + border the buttons have to
  live inside), still capped at 128. A panel denser than ≈152 **logical** dpi
  would need more than 128 px for an 18 mm button and would get a button under
  the floor. No panel in `HARDWARE.md` is close — the worst case we ship for
  needs 104 px, at 118 dpi. A 4K panel at scale 2 reports 141 logical dpi and
  needs 120 px, which fits. Recorded here so that when it does bite, it bites a
  documented number rather than a surprise.
* **Twelve versus eight tiles** is now a *panel* decision rather than a product
  one, which is not quite what SYNTHESIS B2 says. The thinker may want to make
  it a product decision (01 #12's five) via `allowed_activity_ids`; §16.4 ships
  the mechanism for that.

### 16.2 `content_required` is a predicate (audit §3.2, §5 #4; 05 Lib-4)

`content_required` was a bool that nothing read, so `kiwix-serve` being on
`PATH` was enough to draw a Library tile that opened an empty library. It is
now **a list of path globs**:

```toml
content_required = ["/var/lib/kidnix/library/*.zim"]
```

Every glob must match at least one file. `Availability.has_content()` answers
it (cached per boot, `globber` injectable so no test touches the disk),
`resolve_availability()` stamps `Activity.has_content`, and
`Activity.usable` = `available and has_content` is what `on_home` and Home's
`_denial()` now ask. The two failures are the same failure to a child, so they
share the "This one isn't ready yet. Ask a grown-up." line — deliberately *not*
"ask a grown-up for this one", because nobody can hand a child a library with
no books in it.

A bare `content_required = true` is now a **manifest error** with a message
naming the fix, rather than a field that silently does nothing.
`--validate-manifests` gates it in CI.

**The path is a choice and here is the reasoning.** `/var/lib/kidnix/library/`
is where a parent drops ZIMs. It is outside the child's `$HOME` (so the child
cannot delete the library), it is on the writable `/var` that bootc upgrades
leave alone, and it is already the directory `kiwix.toml`'s `exec` points
`kiwix-serve` at. Nothing else has to be configured: drop
`wikipedia_en-simple_all_mini.zim` in there and the tile appears at the next
session. **Somebody still has to create that directory in the image** — that is
a `build_files/` change and is not in this pass.

### 16.3 Age bands are honoured (audit §3.2; 01 #35, SYNTHESIS B8)

`age_min` / `age_max` were parsed and never used, so `tuxmath.toml`'s own
comment ("the shell should not show this to a four-year-old") was untrue.

* `Profile.age_range` parses the profile's `age_band` (`"4-5"`, `"6-8"`, or a
  bare `"5"`) via `activities.parse_age_band`.
* `activities.in_age_band(activity, band)` is the predicate: **overlap, not
  containment**, so a Library banded 5–12 is right for a five-year-old and an
  activity with no bounds at all is right for everybody.
* A manifest may also write the shorthand `age_band = "6-8"`; explicit
  `age_min`/`age_max` win over it.
* `HomeScreen.cells()` applies it, and it **removes the tile** rather than
  outlining it. That distinction is the point: a four-year-old is not shown a
  dashed box and told to go and ask about typed arithmetic. There is nothing
  there.
* A profile with an empty or unparsable `age_band` filters nothing. We do not
  guess a child's age from silence.

Against the shipped set, the shipped `"4-5"` profile now hides **two** tiles:
`tuxmath` (6–10) and `turbowarp` (6–12, whose own `goal` says "realistically a
six-plus activity"). A `"6-8"` profile hides none.

### 16.4 `allowed_activity_ids`: empty means *all* (audit §5 #2, G3)

The key already existed and already worked; two things changed.

1. **`is_allowed` treats an empty list as "everything".** It used to mean
   "nothing", which is a Home screen with only "All done" on it and no UI to
   get out of — not a state anyone wants to reach by unticking the last box in
   a parent panel. `None` (absent) and `[]` now behave identically.
2. **`system_files/*/kidnix/parent.toml` ships `allowed_activity_ids = []`
   explicitly**, with the reasoning in a comment, so a parent editing the file
   can see the key and its spelling. Both copies stay byte-identical (there is
   now a test asserting that from the shell suite as well as from
   `test_hardening.sh`).

Tiles not on a non-empty list still render outline-only and still speak
"Ask a grown-up for this one" (G3) — that path is unchanged, and §16.5 is what
makes the outline visible.

**For the thinker:** the audit's §5 #2 asks for a five-tile Home at the child
test. The mechanism is here; choosing the five is a product decision and this
pass deliberately did not make it. Ship it as, e.g.:

```toml
allowed_activity_ids = ["tuxpaint", "ktuberling", "gcompris", "blinken"]
```

(four, plus "All done" — 01 #12's five choices) and note that the age band is
already removing `tuxmath` and `turbowarp` for a 4–5 profile.

**This required two one-line edits outside `shell/`:** `build_files/70-hardening.sh`
and `tests/image/test_hardening.sh` both asserted
`config.allowed_activity_ids is None`, which the shipped `[]` breaks. Both now
assert `not config.allowed_activity_ids` and `config.is_allowed("tuxpaint")`,
which is the property they were reaching for.

### 16.5 Contrast, computed (audit §3.2, §5 #8; 06 #25, 03 #31)

`@kid-edge` was `rgba(0, 0, 0, 0.18)`, which composites to `#cecbc4` on
`@kid-paper`: **1.5:1**. On a `.not-allowed` tile — which has no fill at all —
that border is the entire G3 affordance. It was also the only boundary an
*ordinary* tile had, since a tile's fill is the same paper as the page behind
it.

Edges are stated as solid hex now, because a ratio you cannot compute is a
ratio nobody computed:

| Token | Value | vs `@kid-paper` | vs white (hover) |
|---|---|---|---|
| `@kid-edge` | `#7e838c` | 3.57:1 | 3.81:1 |
| `@kid-edge-strong` | `#5a5f6a` | 5.99:1 | 6.40:1 |

`.not-allowed` and `.all-done` take the strong one. `tests/test_theme_css.py`
parses `theme.css` and recomputes every one of these from the literals, so the
next person to pick a colour by eye gets a red test rather than a shipped
1.5:1.

Also checked and passing: band-button ink on paper **16.6:1** (AAA, and well
over 08 §3.4's preferred 4.5:1 for text and 3:1 for icons); the band button's
own boundary against **all four** profile primaries (3.91 / 4.80 / 9.58 /
5.24:1, since `@kid-primary` is replaced at runtime); the sleeping screen
(12.7:1); the PIN error line (6.1:1).

**One thing the audit did not flag and this pass changed anyway.**
`@kid-highlight` (`#ffd23f`) is 12.3:1 against `@kid-ink` and **1.35:1** against
`@kid-paper` — legible as *colour*, not as an *edge*, which is a WCAG 1.4.11
problem for a focus ring on a pale tile. Rather than spend the one reserved
highlight colour (08 §3.4b) on a darker yellow, `.speaking` and `:focus-visible`
now also take the control's border to full ink while they are up, so the
indicator has a 16.6:1 boundary on both sides of the yellow. One colour, one
meaning, with an edge. **This is a taste call and the human should look at it.**

### 16.6 The font the image actually installs (audit §3.2; 06 #20)

`theme.css` asked for `"Atkinson Hyperlegible"`; `build_files/36-fonts.sh`
installs `atkinson-hyperlegible-next-fonts`, whose family is
**"Atkinson Hyperlegible Next"**. The names did not match, so the grown-up
sheet silently rendered in Cantarell and the only way to notice was to diff two
files. Now:

* `.grownup` — `"Atkinson Hyperlegible Next", "Atkinson Hyperlegible", "Cantarell", sans-serif`
* `window.kidnix` / `.surface` — `"Andika", "Andika New Basic", "Cantarell", sans-serif`
* `.pin-pad` / `.pin-display` — `"Atkinson Hyperlegible Mono", monospace` (the
  image installs that cut too, and it was going unused)
* `widgets.CHILD_FACE` — kept in step, because measuring in a face we do not
  draw in is how a label that "fits" gets clipped on the real machine.

`test_the_shipped_font_packages_still_match_the_stylesheet` reads
`36-fonts.sh`'s own `check_family` lines and asserts each name appears in
`theme.css`, so the two cannot drift again.

### 16.7 No spoken digits (audit §3.2; 01 #19, 03 #32)

`friendly_title()` produced `"Draw 14:32"` and the Journal card read it aloud —
a 24-hour clock spoken to a pre-reader, in a shell that bans digits everywhere
they can be *seen*. Three pure functions in `journal.py`, all tested:

* `part_of_day(when)` → `morning` / `afternoon` / `evening` / `night`
  (boundaries 05:00, 12:00, 17:00, 21:00 — coarse on purpose).
* `when_words(created, now)` → `"this morning"`, `"yesterday afternoon"`,
  `"last night"`, `"tonight"`, or `"before"`. The three buckets are the same
  Today / Yesterday / Before the Journal's own day headings use, so what the
  child hears and what they are looking at are the same vocabulary. A clock
  that has slipped backwards still says "this", never anything about the
  future.
* `spoken_title(title, created, now)` → `"Draw, from this morning"`.

`friendly_title()` no longer puts a time in the stored title at all (and now
rejects a stem containing four or more consecutive digits, which is what a Tux
Paint timestamp filename looks like). `Entry.spoken(now)` composes the phrase at
the moment a child asks; the Journal card's `speak_text` and S7's showing mode
both use it. **The ISO timestamps in `entry.json` are untouched** — exact times
are the parent's business (F4), and the parent has a file browser.

`test_no_spoken_journal_string_contains_a_digit` walks every hour of three days
and asserts the obvious thing.

### 16.8 The session-phase earcon (audit §3.2; 08 §3.6b)

08 lists six earcons; v0.1.2 shipped four and blamed both absences on the
missing Ask flow. Only one of them was Ask's. The fifth is now here:

```
PHASE: A5 (120 ms, level 0.62) -> E5 (250 ms, level 0.55)
```

A gentle step down a fourth, at the lowest level of the five, 370 ms total. It
has to be tellable with the eyes shut from `BACK` (falls further, starts lower)
and from `SLEEP` (an octave down, twice as long), and
`test_the_phase_motif_is_tellable_from_the_others` asserts exactly those
relationships.

`ShellWindow._announce_phase` plays it **once, on the step into
`Phase.ENDING_OFFER`** — the only phase transition with no sound of its own
(Put away already has the keep motif; Goodnight has the sleep motif, and two
earcons inside `MIN_GAP_SECONDS` is one earcon and a swallowed one). It is the
audio half of the sun: a child whose eyes are on their drawing is told the
light has changed before the screen tells them.

Still unheard on real speakers (impl. notes §14.3 remains open).

### 16.9 The sun answers when you ask it (audit §5 #7; 08 §4.6)

`Sun` was a `Gtk.DrawingArea` with `AccessibleRole.IMG` and no gesture. It is
now the child of a `ChildButton` (`Band.sun_button`, CSS class `sun`) drawn
with no button chrome at all — a bordered box around the sun would read as a
control the child is meant to press *for* something. The drawing itself dropped
to `AccessibleRole.PRESENTATION`; the button carries the name.

What it says is `session.time_left_words(fraction_left)`, a pure function with
five sentences and no digits anywhere:

| Remaining | Sentence |
|---|---|
| > 2⁄3 | "Lots of time left." |
| 1⁄3 – 2⁄3 | "About as long as one story." |
| 0.1 – 1⁄3 | "A little bit of time left." |
| ≤ 0.1 | "Nearly time to put things away." |
| not running | "The sun has gone down for today." |

Every one is a **comparison**, never a quantity: a four-year-old has no idea
what "twelve minutes" is and every idea what "one story" is, and a number would
put a digit into the one part of the product that has never had one. (A
twenty-five minute session's middle band is roughly 8–17 minutes, which is a
bedtime story.) The function is total — any float, including one from a clock
that jumped, lands on a sentence.

`Band.set_progress(fraction, warm, words)` keeps `speak_text` current on every
tick, and `speak_text` is both the accessible name and what a tap or a hover
reads aloud, so that is all the wiring the gesture needs. `ShellWindow.on_sun`
exists so the gesture has a named owner and so the timer study (audit §4 item 1)
has one place to count from.

### 16.10 Odds and ends

* **`--start-on {choosing,home}`** (development only). A `--screenshot` run
  would otherwise photograph the "Who's here?" chooser, because six seconds is
  not long enough for anybody to press anything. It chooses the first profile
  after the first frame and zeroes the stack transition — a window nobody is
  compositing gets no frame-clock ticks, so a 400 ms slide never advances and
  the old surface stays up.
* **`ShellWindow.capture()` has a second route.** `Gtk.WidgetPaintable` hands
  back the widget's *last painted* content and returns nothing at all when the
  widget is waiting for a redraw — the normal state of an uncomposited window,
  i.e. every automated screenshot. It now falls back to walking the tree
  itself, which always has an answer. This is why `boot-home.png`-style
  captures were occasionally empty.
* **`--demo` covers all five failure modes now**: outside the allow-list
  (outline), not installed + `show_when_unavailable` (outline, different
  sentence), `content_required` unmatched (no tile — the Library case), above
  the profile's age band (no tile — `maze`, banded 7–10), and `SIGTERM`-ignoring
  (`sticky`).
* **`Metrics.describe()`** now prints the millimetres, not just the pixels:
  tile, gap, min target, band button and the label floor. A future clipped or
  shrunken screenshot has every number that matters next to it in the journal.

### 16.11 Screenshots and tests

`docs/design/screenshots/demo-home-1280.png` (1280×800 @102) and
`demo-home-1366.png` (1366×768 @96) are fresh captures of the new Home: a 4×2
grid of 42 mm tiles at 24 pt, page dots and a 21 mm forward arrow, visible tile
borders, and the Library and Maze tiles correctly absent.

```
just lint            ruff check + ruff format --check + mypy   clean
just test-headless   540 tests, no display
just test            617 tests with a display (77 of them GTK)
```

Up from 370 / 437. Where the 180 new ones went:

| File | before | after | what was added |
|---|---|---|---|
| `test_metrics.py` | 55 | 118 | every floor on every panel we ship for |
| `test_activities.py` | 45 | 75 | `content_required`, age bands |
| `test_journal.py` | 24 | 47 | no spoken digits, at every hour of three days |
| `test_session.py` | 29 | 47 | the sun's words |
| `test_settings.py` | 28 | 38 | empty-means-all, the profile's band |
| `test_theme_css.py` | — | 21 | WCAG arithmetic, the two font families |
| `test_gtk_smoke.py` | 67 | 77 | Home's three filters, the tappable sun |
| `test_demo.py` | 9 | 12 | the two new demo failure modes |
| `test_sound.py` | 20 | 22 | the fifth earcon |

### 16.12 Still open after this pass

1. **Who picks the five tiles.** §16.4 ships `allowed_activity_ids` and the
   empty-means-all semantics; the child-test subset is the thinker's call.
2. **`/var/lib/kidnix/library/` does not exist in the image.** The predicate
   correctly hides the Library either way, but a parent has nowhere obvious to
   put a ZIM until a `build_files/` change creates it (0755 root, or 0775 with
   a group the parent is in).
3. **Eight tiles a page is a panel decision, not a product one.** If 01 #12's
   five is the answer, it should be a product rule, not a consequence of the
   monitor.
4. **The focus ring's ink border is a taste call** (§16.5) and wants a look on
   a real screen before the child test.
5. **The phase earcon has never been heard on speakers**, like the other four.
6. **A 24 mm target floor** (01 #1) instead of 18 (06 #13, A1) is still
   unadjudicated — audit §4 item 11. Raising `MIN_TARGET_MM` to 24 is now a
   one-line change with tests that will tell you exactly what it costs; at a
   guess it takes 1280×800 to a 3×2 grid.

## 17. v0.1.4 — the checkpoint-1 rulings (shell side, 2026-08-22)

> Implementer's third report. Everything here answers a ruling in
> `docs/design/shell-v0.1.md` §7b, which is `docs/research/SYNTHESIS.md` §4b
> and `09-gap-sweep-checkpoint-1.md` §10's nine edits. §§1–16 are unchanged;
> this section is additive.

### 17.1 S1b "What's next after?" (09 §10 #1, §6; SYNTHESIS D4; spec 7b)

The highest-value change in the gap sweep, and the one with the best evidence
behind it: in *Coco's Videos* (Hiniker, Heung, Hong & Kientz, CHI 2018 — 24
families, three weeks, randomised condition order) the child chose the offline
activity **before** they began, from nine picture options, and the ending
showed it back. Castillo et al. (2018) says why that works: what makes a
transition hurt is the destination thinning out, not the announcement.

**A new state, a new screen, four new config keys.**

* `state.State.NEXT_CHOICE` sits between `CHOOSING` and `HOME`.
  `CHOOSE_PROFILE` now lands on it; `CHOOSE_NEXT_AFTER` goes on to Home;
  `SKIP_NEXT_CHOICE` is the profile-level bypass, a separate event rather than
  a conditional edge so the graph says out loud that the screen can be skipped.
  `BACK` returns to "Who's here?" **and stops the clock** (`app.on_back`), since
  the session started when the child said who they were.
* The **hard stop reaches** a child still sitting on S1b (`PUT_AWAY_DUE`,
  `IM_FINISHED` are both valid there, and `ritual.PUT_AWAY_FROM` includes it),
  but the **ending offer never does** — `ritual.INTERRUPTIBLE` deliberately
  leaves `NEXT_CHOICE` out. An ending offer on top of the opening question
  would be absurd. Nothing launches from S1b either.
* `next_after.py` is pure: `NextAfter(id, label, audio_label, icon,
  phrase_override)` plus `parse_next_after()`. It quacks like an `Activity`
  (`name`, `icon_kind`, `category`, `speak_text`) so S1b reuses `ActivityTile`
  at Home's metrics unchanged — one target size, one label size, one gesture.
* `parent.toml` gains `[[next_after]]` (both TOML array spellings parse, since
  a parent should not have to know which one we meant) and each profile gains
  `skip_next_choice`. A malformed option costs one tile and a log line; an
  empty or entirely unusable list falls back to the shipped eight, because an
  empty S1b is a screen a child cannot get off. More than nine is truncated;
  fewer than six is allowed with an INFO line, because a household may honestly
  have four answers.
* The choice lives on `ShellContext.next_after` — **this sitting's state, not
  the config's**. It is cleared when a new session starts, so Goodbye can never
  show a picture nobody chose today. It is deliberately *not* on `Session`,
  because `Session.end()` runs before `GOODBYE_DUE` fires and would wipe it.
* S7 shows the picture beside "Ready to go outside?" and speaks it.
  `suggestions.offline_suggestion()` is now the **fallback** — used when the
  child skipped S1b, when the profile turns it off, or when a grown-up started
  the session from the gate.

**Two things about the wording.** First, the tile label and the sentence are
different strings. "Ready to a book?" is what a single string gets you, so
`NextAfter.phrase` composes the sentence and the label stays short. Second,
labels are short because they have to be: S1b uses Home's two-line label box at
the 18 pt floor, and a third line makes the tile taller than the grid budgeted
for (`test_no_default_label_is_longer_than_a_tile_can_hold` pins it at ≤ 12
characters and ≤ 8 per word). The *audio* label carries the longer wording, so
what the child hears is never the abbreviation of what they see.

| id | tile | spoken | at Goodbye |
|---|---|---|---|
| `outside` | Outside | Going outside | Ready to go outside? |
| `book` | A book | Reading a book | Ready to read a book? |
| `build` | Building | Building with blocks | Ready to build something? |
| `draw` | Drawing | Drawing on paper | Ready to draw on paper? |
| `snack` | A snack | Having a snack | Ready to have a snack? |
| `bath` | Bath time | Bath time | Ready to have a bath? |
| `cook` | Help cook | Helping cook | Ready to help cook? |
| `someone` | With someone | Playing with someone | Ready to play with someone? |

Eight new SVGs in `data/icons/kidnix-next-*.svg`, in the existing style (64×64,
flat fills, 3.5 px ink outlines, the four profile colours). The bath is a tub
**with a duck in it** and the pan has a spoon and a long handle, because the
first drafts of those two were the same teal oval.

**Coco's ninth option, "something else", is not shipped** — the thinker's list
named eight — but `parent.toml` carries a commented-out block for it so adding
it is one paste. Nothing else in the shipped set is a promise: no line anywhere
obliges the child or the family, which is Coco's own failure mode ("Coco will
make you do it").

### 17.2 The sun shrinks and sinks (09 §10 #2, §1; SYNTHESIS D3)

`sun.py` is new and pure; `band.Sun` only paints it. `sun_geometry(fraction,
width, height)` returns `centre_x` (**always `width / 2`**), `centre_y`,
`radius`, `horizon_y`, and where the sun *started*.

* Radius falls from 30% to 13% of the widget's height, monotonically.
* The centre falls from `top_pad + max_radius` to exactly the horizon (80% of
  the height), where a cairo clip cuts it — so the last minute of a session is
  a small half-disc sitting on a line, not a disc sliding over one.
* A faint outline is left where the sun began, at its starting size. That is
  what makes the shrinking legible as a *loss of quantity* rather than as a
  picture that happens to be small today.
* Warm colour in the last six minutes is unchanged (`Session.is_warm`), and it
  is still a `ChildButton` speaking `time_left_words` (§16.9).

The reason is Tillman, Tulagan, Fukuda & Barner (2018): most preschoolers do
not represent time as a directional spatial line, so left-to-right travel was a
weak carrier. `tests/test_sun.py` pins the whole mapping headless — x constant
across every fraction and every width, radius strictly decreasing, centre
strictly increasing, out-of-range floats clamped rather than thrown.

**And the sun is state, not a warning.** Four JABA single-case experiments say
an antecedent cue is inert on its own. The docstring says so, so nobody tunes
these numbers expecting them to buy a calm ending.

### 17.3 Hover: 450 ms with a settle gate, instrumented (09 §10 #6, §2; B4)

`speech.HOVER_DWELL_MS` is 450, up from 300, and the dwell clock only runs
while the pointer is **slower than 40 px/s measured over the last 150 ms**.
Any sample above the threshold restarts the whole dwell, so a child sweeping
across half a grid on the way to a target says nothing, and a hand that comes
to rest says one thing. `ChildButton` now connects `motion` as well as `enter`
and `leave`; `SpeechManager` takes an injectable `clock`, so
`tests/test_speech.py` drives a fake pointer at a fake speed.

Keyboard focus is unchanged and ungated — focus is deliberate in a way hover is
not, and no delay is what every screen reader does.

**Protocol P5's instrumentation.** Every hover utterance emits exactly one INFO
line:

```
hover-speech: id=tuxpaint dwell_ms=450 selected=True
```

The line is *held back* for three seconds so `selected` is a real boolean
rather than a placeholder somebody would have to join up later: if the same
control is activated inside the window it is emitted at once as `True`,
otherwise the timer emits it as `False`. `id` is the activity's manifest id
(`ActivityTile` passes it; other controls fall back to the stem of their widget
key). It never carries utterance text, so nothing a child made can reach a log.

`hover_dwell_ms` is a `parent.toml` key (default 450, clamped 150–3000). It is
in `parent.toml` and not `session.toml` on purpose — it sits with the
allow-list and the profiles, not with "how long is a sitting"; `session.toml`
now carries a comment saying where it went.

### 17.4 Progressive disclosure (09 §10 #4; SYNTHESIS B2)

`settings.HomeConfig` (`[home]` in `parent.toml`): `initial_tiles = 6`,
`reveal_every_sessions = 2`, `show_everything = false`.
`HomeConfig.tiles_visible(total, sessions_completed)` is the whole rule, and
`HomeScreen._revealed()` applies it to the cells left after the age band and
availability filters.

* The budget **counts** "All done" (it takes a tile's room) but "All done" is
  never the tile that gets cut. A first run is five activities plus it.
* The order is the manifests' `order`, so the tiles a child meets first are the
  ones the parent put first — not chance.
* A tile once revealed never goes away: the count only rises and the ceiling is
  whatever the allow-list already left.
* The counter is `KidState.sessions_completed` in
  `$XDG_STATE_HOME/kidnix/progress.toml`, incremented in
  `ShellWindow._on_state_change` on the step into `GOODBYE` (and not on the
  return from "Show a grown-up"). **Not** in `usage.toml`, which resets at
  04:00. It is not a streak: nothing shows it to the child, nothing resets it,
  and a corrupt or unwritable file costs a couple of tiles rather than a
  session.

09 §3's justification is the part worth keeping: this is *not* a working-memory
limit. Limits bind on held option sets, not on a visible, labelled, spatially
stable grid (Pailian 2016; Schneider 2021). The reason to start at six is that
a child meeting a computer should meet five things, learn them, and be handed a
sixth once those five are theirs.

### 17.5 Earcons became auditory icons (09 §10 #7; spec 7b)

`sound.py` grew a small synthesis engine — `Layer` (tone / glide / noise, with
attack, exponential decay, one-pole low- and high-pass, and held-random
"shimmer" amplitude modulation) and `Earcon` (layers, relative level, a
`referent` string, a fixed noise seed). `mix()` sums the layers onto one
timeline and **normalises** the peak to `PEAK × level`, which is what lets a
noise burst and a sine sit at a designed loudness relative to each other
instead of at an arithmetic accident.

| earcon | shape | referent | ms |
|---|---|---|---|
| `keep` | five staggered bursts of high, crackly, fast-decaying noise | paper being gathered up | 250 |
| `back` | two soft knocks: a click over a low resonance that stops quickly | knuckles on a door | 210 |
| `sleep` | a 90 ms-attack glide falling 430 → 175 Hz, an octave above it, a breath under it | a yawn | 360 |
| `tap` | an 8 ms transient on a short 1.5 kHz resonance | a fingertip on a surface | 70 |
| `phase` | two sine tones, a falling fourth, quietest of the five | **none** | 370 |

Every one is now **≤ 400 ms**, including `sleep`, which was 740 and had a
carve-out in the old test. Synthesis is deterministic (a fixed seed per
earcon), so the same source always makes the same WAV and nothing binary enters
git.

**The honesty note is in the module docstring, not only here**, because that is
where the next person to touch it will be: nothing in this soundscape has been
tested with a child or with any listener; the mapping from "shrinking noise
burst" to "paper" is our extrapolation from one 1997 study (Jacko, n=24) of a
different interface; the levels are aimed at −14 LUFS by construction rather
than measured with a meter; and **no kidnix earcon has ever been heard on real
speakers by anyone** (§14.3, §16.12 item 5, still open). The `referent` field
is data rather than a comment so the note cannot drift away from the sound.

### 17.6 The gate is not voiced (09 §10 #9; SYNTHESIS G2)

* `band.HoldButton` no longer takes a `SpeechUI` at all: no hover, no focus,
  no activation utterance, and it is not registered with the speech manager so
  there is no key to ring either. It keeps `Gtk.AccessibleProperty.LABEL` —
  unvoiced *by us* is not invisible to an assistive technology.
* The "Who's here?" grown-up tile is a `ChildButton` built without a
  `speech_ui`, which is the same thing for the same reason.
* The PIN pad was already plain `Gtk.Button`s and stays that way.
* **Failure is free.** No lockout, no growing delay, no attempt counter, no
  sound. A five-year-old poking at a keypad is expected behaviour, and
  punishing it teaches them the machine is cross with them. The adult still
  gets "That PIN is not right." in writing, on an adult surface.
* **Attempts are logged for the parent, never the digits:**
  `grown-up gate: PIN attempt rejected at 2026-08-22T18:04:11`. Accepted
  attempts log too, so the line is a record of the gate rather than a record of
  failure. `test_a_wrong_pin_is_free_silent_and_logged_without_the_digits`
  asserts the digits are absent and that the pad still works afterwards.

This inverts Apple's pre-literate advice deliberately: reading "Grown-up. Hold
this for three seconds" aloud to a pre-reader is teaching them how to open it.

### 17.7 No exit friction, as a testable fact (09 §10 #3; SYNTHESIS D6)

Kuo, Zhao & Scott (IDC 2026) name the harm. kidnix's answer is now data rather
than an `if`: `ritual.BACK_DELAY_SECONDS` is a `dict[State, float]` with
**exactly one row** (`PUT_AWAY: 3.0`, spec 7a's accidental-tap guard) and
`ritual.all_done_delay_seconds()` returns 0.0 for every state that exists.
`app.on_back` asks the table. `tests/test_ritual.py` asserts the table has one
row, that every other state is 0.0, and that "All done" reaches Put away in one
event from Home, an activity, My Things **and** S1b — because an extra tap is
friction too.

The audit found nothing else: `finish_now`, `on_back`, the All-done tile and
the grown-up sheet's "End now" all act on the same tick they are called.

### 17.8 Screenshots, tests, and what did not change

`docs/design/screenshots/`:

* `demo-next-choice.png` — S1b at 1280×800 @102: eight Home-sized tiles, one
  page, the title, the band above.
* `demo-home-firstrun.png` — a first-run Home: **six** tiles (five activities
  by `order` plus "All done"), where the same demo world would otherwise show
  nine.
* `demo-goodbye-choice.png` — Goodbye with the child's own picture and "Ready
  to go outside?".

```
just lint            ruff check + ruff format --check + mypy   clean
just test-headless   654 tests, no display          (was 540)
just test            757 tests with a display        (was 617)
just validate-manifests   10 valid, 0 invalid — unchanged
```

| File | before | after | what was added |
|---|---|---|---|
| `test_sun.py` | — | 11 | the geometry mapping; x constant; clamping |
| `test_next_after.py` | — | 26 | the option set, both TOML spellings, the fallbacks |
| `test_sound.py` | 22 | 50 | the four referents' shapes, ≤ 400 ms, normalisation, determinism |
| `test_speech.py` | 30 | 42 | the settle gate with a fake pointer; P5's log line |
| `test_settings.py` | 38 | 60 | `hover_dwell_ms`, `[home]`, `KidState`, `skip_next_choice` |
| `test_gtk_smoke.py` | 77 | 103 | S1b, Goodbye's choice, disclosure, the unvoiced gate |
| `test_ritual.py` | 26 | 34 | the one-row delay table |
| `test_state.py` | 22 | 34 | S1b's edges, the offer that never lands there |

**Manifests gained nothing**, so `--validate-manifests` is untouched: S1b's
options are `parent.toml`'s business, not an activity's.

**Outside `shell/`:** both copies of `parent.toml` (still byte-identical) gained
`hover_dwell_ms`, `[home]`, `[[next_after]]` and the profile's
`skip_next_choice`, all commented with the evidence and the units;
`session.toml` gained a pointer saying those keys are not there; and
`system_files/usr/lib/tmpfiles.d/kidnix-library.conf` is new — it creates
`/var/lib/kidnix/library`, which closes §16.12 item 2 (the Library's
`content_required` had nowhere for a parent to put a ZIM).

### 17.9 Still open after this pass

1. **Everything in §17.5's honesty note.** The soundscape is a designed guess
   and has still never been heard on speakers.
2. **450 ms and 40 px/s are extrapolated from adult gaze research.** P5 now has
   its instrument; it needs a child and four weeks.
3. **Goodbye's line wraps to two lines** beside the picture on a 1280×800
   panel. It fits and it is legible; whether the picture should be above the
   line instead is a look-at-it-on-the-real-screen call.
4. **`initial_tiles = 6` counts "All done"**, so a first run is five
   *activities*. That matches 01 #12's five choices, but it is a reading of
   09 §3 rather than something it says, and the thinker may want six activities
   plus All done.
5. **S1b costs a tap at the start of every session.** Coco's evidence is about
   choosing *at all*, not about choosing daily; a child who picks "Outside"
   every day for a month may find it friction rather than a plan. Watch for it
   in P2 — `skip_next_choice` is the escape hatch if so.
6. **The demo's three-minute session now has one more screen in it.** Nothing
   broke, but a `--demo` run reaches Home a few seconds later than it did.

---

## 18. v0.1.5 — the band stays visible during activities (2026-08-22)

> Implementer's fourth report. It builds the thing
> `docs/spikes/band-over-activity.md` proved was possible, and it closes the
> single largest hole in the build: the CCI audit's B3 (fixed band on every
> surface), C1 (undo in a fixed position), D3 (the sun glanceable throughout),
> 01 #15, #22, #30, 08 §3.2e and §4.6, plus 02 #4 (the ending offer was a
> fullscreen modal over the child's drawing) and 01 #20 (an autosave during an
> activity was invisible). ADR-0010 #5 retires with it. Additive: nothing in
> §§1–17 changed except where this section says so.

### 18.1 Two toplevels, one process

The shell was one fullscreen window that drew the band and the current surface
together, and `IN_ACTIVITY` simply left it behind the activity. It is now two
`Adw.ApplicationWindow`s on **one** `GtkApplication`:

| Role | Class | Title | Contents |
|---|---|---|---|
| band | `app.BandWindow` | `kidnix-band` | `Band` — Back, Undo, My Things, sun, Ear, Grown-up |
| content | `app.ShellWindow` | `kidnix-content` | the `Gtk.Stack` of screens S1–S8 |

One `GtkApplication` is a requirement, not a tidiness choice: two *processes*
sharing an application id do not get two windows — the second one's `activate`
is delivered to the first, which presents the window it already has. The spike
hit that and had to be rewritten around it.

`ShellWindow` is still the only thing that touches the state machine, the
session and the launcher; `BandWindow` has no logic at all. `_build_content()`
now fills both windows, and `self.band` is still where it was, so every screen,
every action and `ShellHost` are unchanged.

**Titles are the whole identity.** Both windows carry `org.kidnix.Shell`, so
`match-class` cannot tell them apart — and `match-class` could not place them
anyway (rule R3 below). `kiosk.BAND_TITLE` / `kiosk.CONTENT_TITLE` are the one
definition, and `tests/test_kiosk.py` asserts they contain no
`g_pattern_match_simple` metacharacters.

### 18.2 The compositor: `kidnix_shell/kiosk.py`

A new module, no GTK, fully unit-tested headless (`tests/test_kiosk.py`, 26
cases). It holds the three `window-config.ini` files as string constants and
writes the rendered ones. The four rules the spike measured, and what each one
made us do:

* **R1 — the config is resolved once, at compositor start, and gnome-kiosk arms
  its file monitor only if the user's file already existed.** So the file must
  exist *before* gnome-kiosk. `/usr/bin/kidnix-shell` — which runs before
  `gnome-session` — installs the seed, **unconditionally, on every login**. The
  unconditional part is load-bearing: the file the previous session left behind
  is phase B, and a band window created against phase B would be placed below
  itself.
* **R2 — geometry applies only during a window's first configure.** So the
  catch-all is sequenced in time: phase A (the catch-all *is* the band strip)
  before the band window is created, phase B (the catch-all is everything below
  it) once the band is mapped. Exactly one transition, at start-up — not one per
  activity launch.
* **R3 — at that first configure a window may have no identity, and whether it
  does is toolkit-dependent.** Only a catch-all is guaranteed to match early
  enough to place any window, so **nothing here ever matches an activity by
  name**. (Tux Paint is SDL2 and has no `app_id` yet at its first configure;
  its `wm_class` is `TuxPaint.TuxPaint`, and knowing that buys us nothing.)
* **R4 — `set-above` is exempt from R2 and is one-way.** So the band can be
  raised by *title*, on every pass, and phase B's `set-above=false` cannot lower
  it.

**The seed carries no geometry, and that is a change from the spike's
prototype.** The prototype seeded a 1280×96 catch-all "whose numbers barely
matter". They matter in one case: a session whose shell fails to start would
squeeze every window into a strip sized for somebody else's panel. The wrapper
runs before there is a compositor, so it cannot measure a monitor, and
gnome-kiosk's geometry keys are absolute pixels — `CONFIG.md` (read in the
image) types `set-x`/`set-y`/`set-width`/`set-height` as integers and
`lock-on-area` as the literal `"x,y WxH"`; there is **no percentage form**, and
the only monitor-relative form (`set-on-monitor` + `lock-on-monitor-area`) needs
a monitor *name* the wrapper cannot know either. So the seed contains one
section — `match-title=kidnix-band` / `set-above=true` — and exists purely so
that gnome-kiosk resolves the path and arms the monitor. A shell that never
starts then behaves exactly as v0.1.4 did.

Sequencing, as implemented:

1. `ShellWindow.__init__` measures the monitor and writes **phase A**;
2. it creates `BandWindow` and connects its `map` signal;
3. `present_all()` presents the **band alone**;
4. `_on_band_mapped` logs the band's real size, writes **phase B**, and waits
   `CONTENT_SETTLE_MS`;
5. `_present_content` presents the content window and logs the geometry it got.

`CONTENT_SETTLE_MS` is **1200 ms**, not the spike's 3 s sleep. GLib file
monitors rate-limit at 800 ms by default, so anything under a second is a race.
It is paid once, at login, behind an already-visible band. The spike's open
question 3 asked for the shell to say what the content window actually got;
`_log_content_geometry` does, so a regression is a grep rather than a
screenshot somebody has to notice.

Writing the same bytes twice is skipped (`WindowConfig` compares before it
writes): gnome-kiosk reloads on every change event, and a reload that changes
nothing can only cost us a race.

`--windowed` writes nothing at all. That is a developer on their own desktop,
where `$XDG_CONFIG_HOME` is *theirs* and there is no gnome-kiosk. Both windows
still exist, so the code path under test is the real one.

**The shipped templates and the module cannot drift**:
`system_files/usr/share/kidnix/kiosk/*.ini` are byte-identical to the constants
and `tests/test_kiosk.py` asserts it (skipping when the shell is running from an
installed copy with no repo around it).

### 18.3 Two fit budgets, not one

`Metrics.content_height` is new: `screen_height − band_height`, or 0 for an
unknown screen. `_check_measured_fit` now measures **both** trees and shrinks if
either overflows *its own* window — the band against `W × band_height`, the
content against `W × content_height`. gnome-kiosk gives each of them exactly
that and nothing more (`lock-on-area`), so a content tree measured against the
full monitor height would have fitted the old single window and been clipped in
the new one: the v0.1.0 clipping bug wearing a new hat.

On the 1280×800 @102 panel this costs one extra shrink step (chrome 1.00 →
0.96 → 0.98 of that) and settles at a 97 px band, a 42.3 mm tile and every floor
intact.

`--screenshot` now composites both windows — the band's tree at `0,0`, the
content tree at `0,band_height` — into one image the size of the panel, which is
what the compositor puts in front of the child. If the band cannot be rendered
the content window is written on its own and the log says so.
`screenshots/shell-v0.1.5-home.png` is
`just demo-small --start-on home --run-seconds 7 --screenshot …`; it is 1280×795
rather than 1280×800 only because the *development* window is sized to what the
layout needs, not to the strip gnome-kiosk would hand it.

### 18.4 What the band does during an activity

| Control | Before | Now |
|---|---|---|
| Back | unreachable | **ends the activity**: SIGTERM, 5 s autosave grace, SIGKILL; `activity_exited` navigates when it has actually gone |
| Undo | unreachable | speaks "*Draw* has its own undo button" |
| My Things | unreachable | ends the activity, *then* opens the Journal |
| Ear, sun, Grown-up | unreachable | unchanged, and now reachable |

Back and My Things deliberately do **not** navigate first: a shell surface
raised under a program that is still on screen is a screen the child cannot see,
pressed from a band they can. Both sweep the Journal before asking the activity
to quit, so a child quick enough to reach My Things finds their drawing already
there. The stop path is spec S6's, unchanged and shared with Put away.

**Undo speaks rather than routing.** The ruling was "speak", and the reasoning
is worth recording: routing Undo into a running program means synthesising a key
press per activity — Tux Paint's undo is Ctrl+Z, GCompris's is not — and a shell
that guessed would teach a child that the button is unreliable. Honest and
audible beats clever and intermittent; it is the same rule as "Nothing to undo".

### 18.5 The ending offer is not a modal any more (audit 02 #4)

`_present_ending_offer` has two shapes and neither of them covers a drawing:

* **on a shell surface** — the offer is the `ENDING_OFFER` screen in the content
  window, which is where the child already is. (The old code raised a *second*
  fullscreen `Gtk.Window` over everything; that window is gone.)
* **inside an activity** — the band changes. The sun is already low and warm;
  Undo and My Things are replaced, in place and at the same size, by
  "Finish this one" and "One last little thing", spoken once, for
  `BAND_OFFER_SECONDS` (20 s).

Two things about the swap are deliberate and both are trade-offs worth naming.

1. **Nothing moves.** The two offer buttons are the same size as the two they
   replace and sit in the same places, so the band does not change width, the
   sun does not shift and Back and the Ear stay put. A band that re-flowed under
   a five-year-old's hand at the one moment they are being asked to stop would
   be the worst possible time for it.
2. **They are pictures, not words.** A band button is one square ~20 mm on a
   side; "One last little thing" cannot be set inside that at the 18 pt floor
   without cutting it or making the band taller than spec §7a's clamp. The words
   are the `speak_text` — which is also the accessible name — and the shell
   speaks the whole question once when the offer appears. **This is the one
   place in the shell where a child-facing control has no visible label**, and
   it cuts pre-reader-first the other way round on purpose: the audio carries
   the sentence. Two new icons, `kidnix-finish` (the setting sun, the same
   picture the offer screen shows) and `kidnix-one-more` (one more small thing
   beside what is there). **For the thinker: this wants a child's eyes on it.**
   `screenshots/shell-v0.1.5-band-offer.png` is the band in offer mode (the
   content window behind it is Home rather than a drawing, because a demo has
   no Tux Paint to be inside — in the real case the child sees their own
   picture there, untouched).

`ritual.next_action` gained `offer_shown`, because the band route does not
change the state and `IN_ACTIVITY` is in `INTERRUPTIBLE` — without it the shell
would re-present the offer on every 500 ms tick, which is exactly the bug the
offer latch exists to prevent. A band offer nobody answers within 20 s is
latched as answered: ignoring a question is a legitimate answer, and the
alternative is asking it four hundred times over four minutes. Put away at T−2
still arrives and still ends the activity, unchanged.

### 18.6 Sleeping

The band is still hidden on the Sleeping screen — nothing in it is for a machine
that has said goodnight — but its **window stays mapped**. Unmapping it would
cost the band its placement: a re-mapped window gets a fresh first configure, and
by then the file says phase B, which would put the band below itself. The strip
it leaves behind is painted `#171b2c` (`window.kidnix.sleeping` in `theme.css`),
the same colour as the Sleeping screen, so the two windows read as one surface.

### 18.7 Tux Paint: `--noquit`, and where it should really live

`system_files/usr/share/kidnix/activities/tuxpaint.toml` now launches
`tuxpaint --noquit`, which hides Tux Paint's own Quit tool and disables its
`[Escape]` binding. **ADR-0010 #5 retires**: that dialogue ("Do you really want
to quit?", two lines of text a pre-reader cannot read, ~1400 px wide) existed
only because the child had no other way out of the activity. Now Back in the
band is the way out, `autosave=yes` means the drawing is already saved when
SIGTERM arrives, and the Journal keeps it.

**The trade-off, stated:** Tux Paint then has *no* in-app exit. If the band ever
failed to appear, a child would be stuck in it. That is the design — one exit,
always in the same place, in the shell's chrome rather than in each activity —
and it is why `tests/e2e/test_scenario.py` now asserts the band is on screen
*during* the activity before it uses Back. An adult still has Alt+F4 and
Shift+Ctrl+Escape (`tuxpaint(1)`).

**For the thinker — this belongs somewhere else.** The right home is
`noquit=yes` in `/etc/tuxpaint/tuxpaint.conf`, which `build_files/50-activities.sh`
writes with a heredoc (it cannot live in `system_files/`: the tuxpaint RPM owns
that path as a `%config` file and the dnf transaction would clobber an overlay
copy — the script says so at line 157). That script and `tests/image/test_activities.sh`
are both outside this change's ownership, so the flag is on the command line
instead. Two one-line edits move it:

```diff
-# Quit stays available: the shell has to be able to close an activity, and a
-# child needs a way out that is not "ask a grown-up to reboot".
-quit=yes
+# The band's Back is the way out of an activity (v0.1.5), so Tux Paint's own
+# Quit tool and its unreadable "do you really want to quit?" modal go away.
+noquit=yes
```

```diff
-assert_grep '^quit=yes$'  /etc/tuxpaint/tuxpaint.conf "tuxpaint quit stays available"
+assert_grep '^noquit=yes$' /etc/tuxpaint/tuxpaint.conf "the band's Back is the only way out"
```

…and then `--noquit` can come off the manifest's `exec`.

### 18.8 Tests

**Headless** (`just test-headless`, no display):

* `tests/test_kiosk.py` — 26 cases: the geometry arithmetic on five panels, the
  token check, the five refusals, both phases' contents, path resolution,
  idempotence, directory creation, the seed's emptiness, and byte-equality with
  the three shipped `.ini` files.
* `tests/test_ritual.py` — a `BandShell` that models the v0.1.5 route: the offer
  is presented once, the child never leaves `IN_ACTIVITY`, an unanswered offer
  is not asked again, put away still arrives, and `offer_shown` suppresses
  `PRESENT_OFFER` and *nothing else* (checked across every phase × state).

**GTK smoke** (skipped without a display): two toplevels with the two titles and
one application; the band is no longer inside the content tree; each window
measures inside its own share of the panel; `--windowed` writes no config while
a kiosk shell writes phase A before the band exists; the offer never covers the
drawing and the offer buttons are the same size as the two they replace; Back
and My Things end a real child process and then navigate; Undo names the
activity; the band window goes dark rather than away on Sleeping.

`just lint` (ruff + ruff format + mypy strict) and `just test-headless` are
green — 685 passed, 1 skipped, no display. So is the full suite with a display:
798 passed.

**e2e** (`tests/e2e/`, run by the thinker): `pixels.band_height_from()` reads the
band's height out of the shell's own `display metrics:` line rather than
hard-coding 96 (the fit backstop settles it at 97 on this panel), and every Tux
Paint region is now a fraction of the area *below* the band. Step 4 asserts the
band is still there mid-activity and that the rows under it are Tux Paint's
paper, then quits with the band's Back instead of the Quit tool. Step 6 runs the
whole ritual from *inside* an activity on a 2½-minute session, asserts the offer
arrives in the band exactly once and that the pixels below the band did not
change, and checks that Goodbye speaks the child's own "Ready to …". Step 2 was
also brought up to date with wave 4's "What's next after?" screen.

### 18.9 Still open after this pass

1. **None of the compositor half is verified in the shipped image.** Everything
   about `window-config.ini` is measured — but it was measured by the spike's
   throwaway harness, on hand-written files, not by this code in this session.
   The e2e run is the proof; until it is green, treat §18.2 as a design.
2. **`CONTENT_SETTLE_MS = 1200` is reasoned, not measured.** If gnome-kiosk's
   monitor turns out to be slower, the content window's first configure would
   land under phase A and the shell would be a second band. The symptom is
   loud (`content window at 1280x97`), which is why the log line exists.
3. **A monitor hotplug mid-session leaves the band where it was.** Rule R2 means
   a window's geometry cannot be changed after its first configure. The shell
   rewrites phase B so every *subsequent* activity is right, and says so in the
   log. Fixing it properly means destroying and recreating the band window,
   which is a re-map with the wrong file in place; the ordering would have to be
   re-derived. Not urgent — the target hardware is one panel.
4. **Multi-monitor is untested**, as the spike said. `set-on-monitor` +
   `lock-on-monitor-area` are the equivalents.
5. **The band's offer buttons have no visible words** (§18.5). It is the one
   deliberate exception to icon + label + audio and it needs a child.
6. **`--noquit` is on a command line rather than in `tuxpaint.conf`** (§18.7).
7. **Nothing yet puts the keep animation in the band.** Audit 01 #20 asked for
   an autosave during an activity to be *visible*; the earcon is now audible
   because the child is not behind a fullscreen window, but `_on_new_work` still
   only plays a sound. The band is the place for it and the hook is there.
8. **A shell restart mid-activity** (spike open question 4) is exercised by the
   e2e's `restart_shell()` only between sessions, not with an activity running.
   The reasoning says it is safe — the activity's initial config was consumed
   long ago and the new band gets phase A — but it is reasoning.
