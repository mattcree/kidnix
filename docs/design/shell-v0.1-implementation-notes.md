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
