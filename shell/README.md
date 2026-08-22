# kidnix shell

The full-screen surface a child sees. GTK4 + libadwaita via PyGObject
(ADR-0004), specified in [`docs/design/shell-v0.1.md`](../docs/design/shell-v0.1.md).

It is a launcher, a Journal and a session manager — not a host for activity
code. Activities are separate processes started with a clean environment; the
shell watches what they write and keeps it.

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
             [--activities DIR] [--windowed] [--run-seconds N]
             [--speech {auto,speechd,spd-say,null}] [-v]
kidnix-shell --validate-manifests [DIR]
```

- `--demo` — thirteen fake activities (a scribble window that autosaves PNGs)
  and a three-minute session: ending offer at T−60 s, put away at T−20 s. The
  whole world lives in a temp directory; your real journal is never touched.
  One demo activity is outside the allow-list (outline-only tile) and one
  deliberately ignores `SIGTERM` so put-away has to escalate.
- `--validate-manifests` — exits non-zero on any schema error, for CI.
- `--windowed` — do not go fullscreen; use this on a normal desktop.
- `--run-seconds N` — quit after N seconds, for smoke tests.

Logging goes to stderr, which is the systemd journal in the real session.
There is no telemetry and no network access.

## Layout

```
kidnix_shell/
  cli.py          argument parsing, the two non-GUI modes
  app.py          ShellApplication / ShellWindow -- the only thing that
                  touches the state machine, session and launcher
  context.py      what screens are handed (ShellContext, ShellHost)
  band.py         the persistent 96 px band and the sun
  widgets.py      ChildButton and friends: where the input rules live
  screens/        S1 who's here, S2 home, S4 my things, S5/S6 ending,
                  S7 goodbye, S8 sleeping, S9 grown-up sheet
  theme.css       the reserved highlight colour, flat-with-depth, tints
  data/icons/     representational fallback icons (SVG)
  data/sounds/    the earcon set -- specified, not yet composed

  # pure logic, no GTK, fully unit-tested headless:
  metrics.py      mm <-> px, DPI-aware sizing
  activities.py   manifest loading and validation (spec section 4)
  journal.py      the Journal storage contract (spec section 5)
  session.py      session timing and policy (spec section 6)
  state.py        the navigation graph (spec section 2)
  speech.py       read-aloud queue, dwell, backends (spec section 3)
  launcher.py     activity subprocess lifecycle
  settings.py     XDG paths, parent config, PIN hashing, profiles
  suggestions.py  the Goodbye screen's offline continuation lines
  util.py         pagination
  sound.py        earcon call sites
  demo.py         --demo world, and the fake activity itself
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

## Configuration

| File | Owner | What |
|---|---|---|
| `/etc/kidnix/session.toml` | root | session length, daily budget, ending offer / put away offsets, bedtime window |
| `<config>/kidnix/parent.toml` | parent | PIN hash, default session length, activity allow-list, child profiles |
| `<state>/kidnix/usage.toml` | child | seconds used today |
| `<data>/kidnix/journal/` | child | the Journal: `YYYY/MM/DD/<entry>/entry.json` + versions + `thumb.png` |

The dev default PIN is **1234**, stored as a PBKDF2-SHA256 hash. Change it from
the grown-up sheet.
