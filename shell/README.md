# kidnix shell

The full-screen surface a child sees. GTK4 + libadwaita via PyGObject
(ADR-0004), specified in [`docs/design/shell-v0.1.md`](../docs/design/shell-v0.1.md).

It is a launcher, a Journal and a session manager — not a host for activity
code. Activities are separate processes started with a clean environment; the
shell watches what they write and keeps it.

This directory also holds **`kidnix_activity`**, the activity SDK that
first-party activities are built from — same uv project, same wheel, same copy
into the image, because an SDK that lagged the shell it borrows `Metrics`,
`Journal` and `SpeechManager` from would break every activity on the machine.
Its contract is [`docs/design/activity-sdk.md`](../docs/design/activity-sdk.md).

## Quick start

```bash
cd shell
just setup          # venv (--system-site-packages) + dev tools
just demo           # fake activities, three-minute session, whole ritual
just test           # headless test suite
just lint           # ruff check + ruff format --check + mypy
```

`just --list` is the documentation of what you can do.

## Why the venv sees the system packages

PyGObject, GTK4, libadwaita, GdkPixbuf and `speechd` come from the **system**,
not from PyPI:

- they are already in the bootc image, so depending on them from PyPI would
  duplicate them and drag a GObject-introspection build toolchain into the
  image for no gain;
- `pygobject` from PyPI has to compile against the same GTK anyway.

So `just setup` runs `uv venv --system-site-packages`, and `pyproject.toml`
declares **no runtime dependencies at all**. The dev group is `pytest`, `ruff`
and `mypy` and nothing else.

If `just setup` reports GTK or PyGObject missing, on Fedora:

```bash
sudo dnf install python3-gobject gtk4 libadwaita python3-speechd
```

`python3-speechd` is optional. Without it the shell falls back to the `spd-say`
CLI, and without that it degrades silently and logs once (spec §3).

## Command line

```
kidnix-shell [--demo] [--config PATH] [--session-config PATH]
             [--activities DIR] [--windowed] [--screen WxH[@DPI]]
             [--run-seconds N] [--screenshot PATH]
             [--start-on {choosing,next-after,home,goodbye}]
             [--speech {auto,speechd,spd-say,null}] [-v]
kidnix-shell --validate-manifests [DIR]
kidnix-shell --generate-earcons [DIR]
```

- `--demo` — fourteen fake activities (a scribble window that autosaves PNGs)
  and a three-minute session: ending offer at T−60 s, put away at T−20 s. The
  whole world lives in a temp directory; your real journal is never touched.
  Each of the five ways a tile can fail is represented: one activity is outside
  the allow-list (outline-only tile), one points at a program that does not
  exist and asks to be shown anyway (`show_when_unavailable`, the "This one
  isn't ready yet" tile), one declares `content_required` against an empty
  directory (no tile at all — the Library case), one is banded above the demo
  profile's `age_band` (no tile, nothing to ask for), and one deliberately
  ignores `SIGTERM` so put-away has to escalate.
- `--validate-manifests` — exits non-zero on any schema error, for CI.
- `--windowed` — do not go fullscreen; use this on a normal desktop.
- `--screen WxH[@DPI]` — pretend the monitor is that size and density, e.g.
  `--screen 1280x800@102`. This is how you see, on a 27" desktop, exactly what
  a small panel gets. `KIDNIX_SCREEN` and `KIDNIX_FORCE_DPI` do the same from
  the environment.
- `--run-seconds N` — quit after N seconds, for smoke tests.
- `--screenshot PATH` — write a PNG of the shell as the child sees it, before
  quitting. GNOME 45+ lets no external tool photograph the kiosk, so the shell
  renders its own widget trees and **composites the two windows** — the band at
  the top, the content below it (`just demo-small --run-seconds 7 --start-on
  home --screenshot x.png`). If the band cannot be rendered the content window
  is written on its own and the log says so.
- `--start-on {next-after,home,goodbye}` — development only: drive the shell
  forward immediately so a `--screenshot` run photographs the surface you asked
  for rather than the "Who's here?" chooser it would otherwise still be on.
  `goodbye` also picks a next-after, so the ending shows the child's own
  choice. The child always starts on S1.
- `--generate-earcons [DIR]` — write the five generated earcons and exit; run
  at image build time so `/usr` has them and the child's cache does not need to.

Logging goes to stderr, which is the systemd journal in the real session.
There is no telemetry and no network access.

## Layout

```
kidnix_shell/
  cli.py          argument parsing, the two non-GUI modes
  app.py          ShellApplication / BandWindow / ShellWindow -- the only
                  thing that touches the state machine, session and launcher
  context.py      what screens are handed (ShellContext, ShellHost)
  band.py         the persistent 96 px band and the sun
  widgets.py      ChildButton and friends: where the input rules live
  screens/        S1 who's here, S1b what's next after, S2 home,
                  S4 my things, S5/S6 ending, S7 goodbye, S8 sleeping,
                  S9 grown-up sheet
  access.py       captions, calm mode, volume/mute, the focus ring's order
                  (pure; no GTK)
  keyboard.py     one key controller across both toplevels, one focus ring
  theme.css       the reserved highlight colour, flat-with-depth, tints
  data/icons/     representational fallback icons (SVG)
  data/sounds/    the five earcons (generated, never committed)

  # pure logic, no GTK, fully unit-tested headless:
  theme.py        the runtime half of the theme: profile tint, type scale
  labels.py       the no-cut label rule: wrap, shrink, floor at 18 pt
  kiosk.py        gnome-kiosk's window-config.ini: the two phases that keep
                  the band above an activity (no GTK; fully unit-tested)
  metrics.py      mm <-> px, DPI-aware sizing, and the fit-to-screen clamp
  activities.py   manifest loading, validation, order and availability (s4)
  ritual.py       the ending ritual as one pure decision (spec S5-S7)
  journal.py      the Journal storage contract (spec section 5)
  session.py      session timing and policy (spec section 6)
  state.py        the navigation graph (spec section 2)
  sun.py          the sun's geometry: it shrinks and sinks, it never travels
  next_after.py   S1b's picture options and their parent config
  speech.py       read-aloud queue, the 450 ms settle-gated dwell, backends
  launcher.py     activity subprocess lifecycle
  settings.py     XDG paths, parent config, PIN hashing, profiles
  suggestions.py  the Goodbye screen's offline continuation lines
  util.py         pagination
  sound.py        earcon synthesis and GStreamer playback
  demo.py         --demo world, and the fake activity itself
```

```
kidnix_activity/          the activity SDK (docs/design/activity-sdk.md)
  app.py          ActivityApplication / ActivityWindow -- one window, sized
                  to the rectangle below the band
  widgets.py      BigButton, PictureTile, Prompt, GrownUpTurn
  keyboard.py     the focus ring. Escape is the SHELL's and is never taken
  activity.css    what an activity adds to theme.css (loaded second)
  examples/hello_draw/   the worked example, not installed on the image

  # pure logic, no GTK, fully unit-tested headless:
  env.py          the launch environment (KIDNIX_ACTIVITY_ID, KIDNIX_PROFILE_ID)
  lifecycle.py    SIGTERM -> on_finish() -> exit. There is no quit dialogue
  captions.py     the caption datagram to $XDG_RUNTIME_DIR/kidnix/captions.sock
  metrics.py      ContentArea: mm sizing for the area an activity is given
  journal.py      save_entry(): write into the child's Journal directly
  manifest.py     validation + the template a new manifest starts from
  scaffold.py     what `kidnix-activity new` writes
  speech.py       one voice: speech-dispatcher plus the caption hook
  cli.py          `kidnix-activity new|validate`
```

```bash
just validate-activity                       # the example's manifest
just new-activity "Clock and time" ../activities
just hello-draw                              # runs on a Broadway display
```

Everything a child touches is a `ChildButton`, which is where the input rules
from SYNTHESIS §2A live in one place: fires on **press**, every mouse button
does the same thing, 150 ms debounce so eight clicks a second is one action,
and `speak_text` doubles as the accessible name (and as the test hook).

## Testing

```bash
just test            # everything the current host can run
just test-headless   # what CI runs: no display, pure logic only
```

GTK widget tests skip themselves when there is no `WAYLAND_DISPLAY` or
`DISPLAY`. The logic tests never need one.

## Fitting the screen

Child-facing sizes are specified in **millimetres** (SYNTHESIS §3), but a
millimetre is only affordable if it fits. `metrics.py` computes the mm-based
ideal, then shrinks every size by one `fit` factor until the band, the Home
grid and the pager provably fit inside the monitor's geometry — and
`app.py` measures the built widget tree and shrinks again if GTK disagrees.
On 1920×1080 and up nothing shrinks (`fit = 1.0`). On the 1280×800 panel of
the first real boot it settles around 0.81, which is a 34 mm tile instead of a
40 mm one — small, and *visible*, which the clipped one was not. The tile is
also allowed to be taller than it is wide: two reserved label lines are more
than the spec's 40 px label strip, and `home_size()` budgets for them, which is
what keeps twelve tiles on that panel instead of eight.

The band is clamped to 80–128 px (spec §7a) and its buttons are sized to live
inside that clamp. On a genuinely small panel Home drops to 4×2 tiles rather
than shrinking twelve of them past 128 px.

Since v0.1.5 there are **two budgets, not one**, because there are two windows:
the band window gets `W × band_window_height` — the row of controls *and* the
caption strip under it — and the content window gets what is left,
`Metrics.content_height`. gnome-kiosk gives each of
them exactly that and nothing more, so a content tree measured against the full
monitor height would have fitted the old single window and been clipped in the
new one.

## The band over activities

The band is its own toplevel (`kidnix-band`), and the surfaces under it are a
second one (`kidnix-content`), on **one** `GtkApplication` — two processes
sharing an application id do not get two windows. gnome-kiosk pins the band to
the top strip, keeps it above everything with `set-above`, and locks every other
window (the content window and every activity) into the area below it. The
evidence, the four undocumented compositor rules it turns on and the reason the
configuration has to be written in two phases are in
[`docs/spikes/band-over-activity.md`](../docs/spikes/band-over-activity.md) and
in `kidnix_shell/kiosk.py`'s docstring.

What it changes for a child: Back, Undo, My Things, the Ear, the sun and the
grown-up gate are all reachable **during** an activity, and the ending offer is
no longer a fullscreen window over their drawing.

Back and My Things **ask** the activity to finish — SIGTERM, and then the shell
waits. It does not insist, and that is deliberate: Tux Paint answers SIGTERM
with its own picture-coded "Do you really want to quit?" and only saves when the
child taps the tick, so a Back that killed after the autosave grace would
destroy the drawing every time (measured; see §19.2 of the implementation
notes). Put away at T−2 is the one thing that insists — the hard stop is the
hard stop.

The band's placement is *confirmed*, not assumed: the shell writes phase A once,
presents the band, and polls until the window's own allocation is the strip
before it writes phase B and shows anything else. If the compositor will not
place it after three fresh toplevels, the shell falls back to one fullscreen
window — v0.1.4's layout — rather than leaving a child looking at a screen with
no way out of it.

`--windowed` does not write `window-config.ini` at all: that is a developer on
their own desktop, where `$XDG_CONFIG_HOME` is theirs and there is no
gnome-kiosk to talk to. Both windows still exist, so the code path under test is
the real one; the window manager simply places them itself.

## Labels are never cut

SYNTHESIS B4 asks for icon + label + audio on every affordance, with the label
at **>= 18 pt**. v0.1.1 asked Pango to ellipsise instead, and on the 1280x800
panel Home said `Letters & n...`, `Number ga...`, `Copy the li...` and
`Jump and r...` -- four of the ten activities the image ships. A pre-reader
matching a shape to a word cannot match half a word, and cannot widen the tile.

`labels.py` is the rule, in order:

1. **Wrap, never cut.** `ellipsize` is `NONE` on everything a child looks at.
2. **Two lines is the budget.** The tile reserves two label lines in its own
   height (`Metrics.tile_label_height`), so a page of long names and a page of
   short ones lay out identically and the grid never jumps.
3. **Shrink before spilling**, in 1 pt steps, breaking between words -- a
   single long word shrinks to the floor before it is ever broken between
   characters ("Goodnig-ht" is a cut label wearing a hyphen).
4. **18 pt is the floor**, absolutely — not scaled by `fit`, because a floor
   that moves is not a floor. Every child-facing size in `theme.css` goes
   through the same floor (`Metrics.child_points`).
5. **A third line is the last resort**, and the one case where a tile grows.

Two other rules fall out of it. A page of tiles is set at **one** size -- the
size the longest name on that page can carry -- because a grid where "Draw" is
24 pt and "Letters & numbers" is 18 pt reads as a mistake, not a hierarchy; and
a page whose labels all fit on one line gives the second line's room back to
the **icon** rather than leaving an empty line under every tile.

`audio_label` is untouched by all of this: what the child *hears* is always the
manifest's whole sentence, however the visible name had to wrap.

The measuring is pluggable. On a display, Pango measures; headless, a
deliberately pessimistic pure-Python model of the shipped face does, which is
what lets `just test-headless` prove the ten shipped names fit at 1280x800 at
96 / 102 / 118 dpi and at 1366x768 with no display at all
(`tests/test_labels.py`). `tests/test_gtk_smoke.py` then checks
`Gtk.Label.get_layout().is_ellipsized()` on every real Home tile.

## Configuration

| File | Owner | What |
|---|---|---|
| `/etc/kidnix/parent.toml`, then `/usr/share/kidnix/parent.toml` | **root** | PIN hash (**absent on a fresh image** — see below), default session length, activity allow-list (empty = all), child profiles (`age_band`, `skip_next_choice`), `hover_dwell_ms`, `[home]` (progressive disclosure), `[[next_after]]` (S1b's options) |
| `/etc/kidnix/session.toml`, then `/usr/share/kidnix/session.toml` | **root** | session length, daily budget, ending offer / put away offsets, bedtime window |
| `/etc/kidnix/research.toml` | **root** | the switch every instrument is behind (hover-speech log, PIN attempts, burst-click). Ships **false**; missing, unreadable or malformed also means false |
| `<state>/kidnix/profiles/<id>/usage.toml` | child | seconds used today, **per child** (budget day rolls at 04:00) |
| `<state>/kidnix/profiles/<id>/progress.toml` | child | sessions completed, ever — the clock progressive disclosure runs on. Not a streak: nothing shows it to the child |
| `<data>/kidnix/profiles/<id>/journal/` | child | the Journal: `YYYY/MM/DD/<entry>/entry.json` + versions + `thumb.png` + `note.ogg` |
| `<cache>/kidnix/sounds/` | child | generated earcons, when `/usr` is read-only |

**The parent config is never read from the child's home.** `~/.config` belongs
to the five-year-old, and a child-writable PIN is not a PIN. If no root-owned
copy exists the shell prints a loud banner to stderr and runs on the built-in
defaults (every activity allowed). `--config PATH` is the one exception and
exists for development.

**The image ships no PIN at all** (spec §7d #11). `ParentConfig.must_set_pin` is
therefore true on a fresh machine, and the grown-up sheet **opens on "Choose a
grown-up PIN"** — typed twice — with nothing else reachable until it is done.
There is no pad to type the old documented 1234 into first. The PIN is stored as
a PBKDF2-SHA256 hash; to make one permanent from a terminal or the parent
account:

```sh
sudo kidnix-set-pin          # or: sudo kidnix-shell --set-pin
```

From the *child's* session that helper is refused by polkit
(`40-kidnix-kid.rules` denies `kid` every `org.kidnix.*` action, which is what
stops a child authorising `kidnix-wipe`), so the sheet keeps the chosen PIN for
that session and says so. Changing any other setting from the sheet holds for
the current boot in the same way.

**Per profile.** Everything a child owns — Journal, daily budget, progressive
disclosure counter — lives under `profiles/<id>/`. A machine built before
2026-08-23 has the old single-profile layout, which is *moved* into the first
profile once, idempotently, on the next start (`settings.migrate_profile_data`).

**Shelves.** A manifest with `kind = "shelf"` and `children_dir = "<name>"`
opens one more screen of tiles instead of launching: the children are ordinary
manifests in that subdirectory (so they can never appear on Home), grouped by
`shelf_group` / `shelf_group_name`, one group to a page. See
`docs/spikes/panel-wave-c.md` §2.

**"Tell me about it".** A 20 s voice note on "Let's keep that" and on Journal
cards in "Show a grown-up" mode, written as `note.ogg` inside the entry's own
directory. One press starts, a second (or twenty seconds) stops, it plays back
once, and on a machine with no microphone the button is not drawn at all.

## Accessible without a pointer

Since v0.1.8 (`keyboard.py`, `access.py`; implementation notes §22, spec §7d #7).
Everything below is what an automated test drives, not what it hopes for.

- **One key controller across both toplevels.** Tab cannot cross a Wayland
  toplevel boundary and the band is a toplevel of its own, so the shell keeps
  the focus ring itself, paints the indicator itself (`.kid-focus`) and
  dispatches activation itself. Tab / Shift-Tab / arrows walk **one** ring —
  the band first, because it is the half that never changes — Enter or Space
  activates, and **Escape is Back**. Every screen puts focus on its own first
  control when the child arrives, which is also free read-aloud.
- **The grown-up gate really is a hold.** Enter or Space for three seconds, the
  same three the pointer hold is, *or* five presses inside three seconds,
  because a switch is a button and cannot say "and keep it down".
- **Captions.** A strip under the band mirrors every spoken line for four
  seconds. It is driven from inside `SpeechManager.speak`, *before* the "is
  speech enabled?" check, so there is no code path that says something without
  showing it — and a test walks the package's AST to keep it that way. On by
  default (`[access] captions`).
- **`[access] calm`.** One switch: reduced motion, only the "kept it" sound,
  a slightly slower voice. `gtk-enable-animations` is honoured too.
- **`[access] sound_volume` / `mute`.** The control the image's unbypassable
  70% hardware ceiling is not. Muting is safe because captions are on.
