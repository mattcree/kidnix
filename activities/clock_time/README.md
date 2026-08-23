# Clock — playing with a clock, and finding out how long a minute is

A kidnix first-party activity (`docs/plan/ACTIVITY-IDEAS.md`, Matt, 2026-08-22).
The design note is [`docs/design/clock-time.md`](../../docs/design/clock-time.md);
this file is how to run it.

Two screens:

* **Play with the clock.** A big teaching clock the child moves by pressing the
  rim. The hands snap to the positions their year has been taught — o'clock and
  half past in Year 1, the quarters and the five-minute marks in Year 2 — the
  voice says what they made ("half past three"), and beside it this family's day
  changes with the hands: the sky, the picture, the name of the thing that
  happens then.
* **How long is a minute?** A duration made visible, in the session sun's own
  language: a disc that shrinks and sinks in place. The child presses stop when
  they think the interval has gone and is told, in three words with no number in
  them, how it went.

## Running it

Never on your own desktop — an activity opens a window, and the SDK's rule is
Broadway (`docs/design/activity-sdk.md` §10):

```bash
uv venv --python /usr/bin/python3 --system-site-packages && uv sync --active

gtk4-broadwayd :11 &
GDK_BACKEND=broadway BROADWAY_DISPLAY=:11 uv run --active python -m clock_time
# then open http://localhost:8091/ in a browser
```

Screenshots, for the design note:

```bash
GDK_BACKEND=broadway BROADWAY_DISPLAY=:11 \
    uv run --active python -m clock_time --screenshot ../../docs/design/screenshots
```

## Testing it

```bash
uv run --active pytest        # headless logic + cairo drawing + a GTK smoke test
uv run --active ruff check
kidnix-activity validate manifest.toml
```

The headless tests are the floor and they never skip: the words, the snapping,
the routine lookup, the verdict bands and the whole of the drawing are pure (or
`cairo`, which is also displayless). `tests/test_gtk_smoke.py` starts its own
`gtk4-broadwayd` and skips the file if there is not one on the machine.

## Layout

```
clock_time/
    words.py        what the hands are showing, in words. No GTK, no cairo.
    routine.py      this family's day, and which half of the dial it means
    settings.py     /etc/kidnix/clock_time.toml
    minute.py       the interval, the bands, and the sun's geometry
    keys.py         what a key press means
    pictures.py     where the drawings are
    dial.py         the drawing, in cairo. Displayless, and therefore tested.
    activity.py     the window. Wiring only.
    screenshots.py  --screenshot
    pictures/       eight routine drawings
    icon.svg        the tile on Home
manifest.toml       the shell's input contract
clock_time.toml     the default day, as the image ships it
```

## Configuring it

The grown-up's file is `/etc/kidnix/clock_time.toml` (the image's default is
`clock_time.toml` in this directory, installed to `/usr/share/kidnix/`). It sets
the year band and this family's day; the schema is in the file's own comments
and in `docs/design/clock-time.md` §6. Nothing in the activity infers, advances
or widens the year band — the only way it moves is a grown-up editing that line.
