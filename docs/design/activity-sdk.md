# The kidnix activity SDK (`kidnix_activity`) — v0

> Implementer's design note, 2026-08-23. The contract `docs/plan/SUITE.md` §2
> asked for: what a first-party activity is, what the shell does for it, what
> it must do for itself, and what it may never do. Everything here is
> implemented in `shell/kidnix_activity/` and asserted in
> `shell/tests/test_activity_sdk*.py` unless a sentence says otherwise — and
> where something is **not** built yet, §13 says so in as many words. §4.2's
> listener, the one thing this note originally shipped without, landed on
> 2026-08-23 in `shell/kidnix_shell/captions.py` (impl. notes §25).

## 1. Why an SDK at all

SUITE §1 commits to a suite of separable apps: Sounds & Words, Clock & time,
Numbers, Photos, Letters to family, Listen, Music. Each is its own package that
the shell launches like any other program (ADR-0004: the shell is a launcher,
not a host). Without a shared SDK, each of them re-derives — and gets wrong —
the same seven things:

1. **20 mm.** ADR-0011's target floor is a physical measurement, and the
   arithmetic that turns it into pixels on an unknown panel is 1,100 lines of
   `kidnix_shell/metrics.py`. An activity that hard-codes 64 px ships a 13 mm
   button on the panel we test on.
2. **The band is not yours.** gnome-kiosk gives an activity the rectangle
   *below* the band. A layout budgeted against the monitor fits on a
   developer's desktop and is clipped on the machine.
3. **One voice.** en-GB, slightly slow, a new line cancels the old one, and
   calm mode slows it further. A second speech-dispatcher connection with its
   own settings is a second voice.
4. **Nothing essential is audio-only.** Every spoken line is captioned. The
   caption strip belongs to the shell's band window, in another process.
5. **Press, once.** Fires on press, every mouse button, 150 ms debounce, no
   double-click, no right-click, no long-press.
6. **The Journal.** Layout, thumbnails, `entry.json`, the per-profile
   directory, and the fact that starring an entry rewrites it.
7. **How it ends.** SIGTERM, five seconds, save, exit — and never a dialogue.

The SDK is the shell's own code, re-exported with an activity-shaped edge. It
imports `kidnix_shell` rather than copying it, and ships in the same wheel and
the same `cp -a` into the image (`build_files/60-shell.sh`), because an SDK
that lagged the shell it borrows `Metrics`, `Journal` and `SpeechManager` from
would break every activity on the machine the first time one of those changed.

## 2. What an activity is

A **process**. The shell starts it with `exec` from its manifest and a clean
environment, and it owns one window and everything in it. It is not a plug-in,
it does not run in the shell's address space, and it cannot crash the shell.

```
activities/<name>/
    <name>.toml            the manifest (the shell's input contract, spec §4)
    <module>/__init__.py
    <module>/logic.py      what the activity KNOWS -- no GTK, tested headless
    <module>/activity.py   the window -- ActivityApplication, widgets, wiring
    <module>/__main__.py   python -m <module>
    tests/                 headless tests, incl. "the manifest validates"
    pyproject.toml
```

`kidnix-activity new "Clock and time"` writes exactly that, and what it writes
already validates and already passes its own tests.

**The `logic.py` / `activity.py` split is the shape to copy.** The part of an
activity worth proving — which grapheme comes next, what the ceiling is,
whether a word is decodable yet, what the clock's hands are showing — must not
be reachable only through a button. `hello_draw` is split that way at a size
where the split is obviously unnecessary, so that Sounds & Words is split that
way at a size where it is not.

## 3. The lifecycle

### 3.1 Launch

The shell's `Launcher.launch()` builds a deliberately small environment
(`ENV_ALLOWLIST`): the display, the session bus, `XDG_RUNTIME_DIR`, `PATH`, the
locale, XDG directories under the kid home, `no_proxy=*`, and **two variables
of its own**:

| Variable | Meaning |
|---|---|
| `KIDNIX_ACTIVITY_ID` | the manifest `id` this process was launched as |
| `KIDNIX_PROFILE_ID` | **which child is sitting there** |

`KIDNIX_PROFILE_ID` is new (2026-08-23) and is the one shell-side change this
SDK required. Every child's things have lived under
`$XDG_DATA_HOME/kidnix/profiles/<id>/` since the shell stopped sharing one
Journal between siblings (impl. notes §23.3); an activity that wrote to the
pre-profiles `kidnix/journal` would put one child's drawing in a directory the
shell no longer reads. `ShellWindow._use_profile` sets `Launcher.profile_id`
before its own early return, so it is set for the *first* profile too, and the
variable is **omitted rather than set empty** when no profile has been chosen —
an empty string would be a profile called `""`, which is not one.

`kidnix_activity.env.LaunchEnv.from_env()` reads both, hands back the profile's
`Paths`, and **never guesses**: an activity started by hand from a terminal has
`launched_by_shell == False`, and the Journal writer refuses rather than
inventing an id.

### 3.2 Running

`ActivityApplication(activity_id, title)` gives you, before your first line of
layout code runs:

* one `Adw.ApplicationWindow`, sized to `ContentArea` (§5) and **not** asking
  for the whole monitor;
* `kidnix_shell/theme.css` and then `kidnix_activity/activity.css`, in that
  order, so the activity is the same object as the shell rather than a
  lookalike;
* `[access]` read from the root-owned `parent.toml` — the same file the shell
  reads — applied to the voice (calm rate, volume, mute), the earcons (calm
  keeps only `keep`) and the window's `calm` style class;
* one voice with the caption hook wired (§4);
* the five earcons, from the shell's own generated set;
* a keyboard focus ring that does **not** consume Escape (§6);
* the SIGTERM handler (§3.3).

You supply two callbacks and nothing else is required:

```python
app = ActivityApplication("hello-draw", "Hello draw")
app.set_build(build)        # build(window) -> fills window.content
app.set_on_finish(save)     # called once, on SIGTERM
return app.run(argv)
```

### 3.3 Finishing — and why there is never a dialogue

Spec 7c gives a manifest two answers to "please finish". `confirm` exists for
Tux Paint, which turns SIGTERM into its own tick-and-cross question (impl.
notes §19.2), and it costs a 30-second grace and a SIGKILL behind it.

**Every first-party activity is `quit = "signal"`.** We own our own activities,
so we save instead of asking, and then the shell's "Let's keep that" is true
without a five-year-old having to read a question at the exact moment the
session is ending. `kidnix_activity.manifest` makes `quit = "confirm"` a
validation **error**, not a warning.

The handler (`kidnix_activity.lifecycle.FinishHandler`):

1. arms SIGTERM **and SIGINT** — Ctrl-C in a terminal must run the same save,
   or a developer has never tested it;
2. arms them through `GLib.unix_signal_add`, so the callback runs on the main
   loop and may touch widgets;
3. calls `on_finish()` **once**. Put away re-asks at the end of the grace
   (`Launcher.request_stop` counts the asks) and a second save would race the
   first one's half-written file;
4. exits 0.

Two deliberate departures from the one-line version of that:

* **`on_finish()` raising exits 1**, with the traceback in the parent's
  journal. Exit 0 is a claim that the work was saved. The shell treats any exit
  as "it has gone" today; the honest code costs nothing and is there for when
  it does not.
* **The exiter is not `sys.exit`.** Raising `SystemExit` inside a GLib callback
  does not end a GTK application — PyGObject catches it at the callback
  boundary and the main loop carries straight on. Measured: an activity logged
  "saved on the way out" and then had to be killed. So the handler quits the
  main loop, `run()` returns, and the code comes back out through `main()`.

### 3.4 Back, Escape and the session

**All three are the shell's.** Back is a band button, in a fixed position, in
the shell's own window, and it is the only way out of an activity by design
(spec S3; impl. notes §18.4 — Back ends the activity with SIGTERM, a 5 s
autosave grace, then SIGKILL). An activity that handled Escape would have
invented a second way out that is invisible, unlabelled, unspoken and
impossible for a pre-reader to discover.

So `ActivityKeyboard` handles Tab, the arrows, Enter and Space, and **returns
`False` for Escape and Backspace**, which is asserted by a test.

## 4. Captions across a process boundary

### 4.1 The wire (implemented)

The shell listens on a UNIX **datagram** socket at:

```
$XDG_RUNTIME_DIR/kidnix/captions.sock
```

The SDK sends one JSON object per datagram, UTF-8, no framing:

```json
{"speak": "Press the big button.", "source": "hello-draw"}
```

`speak` is the line as it was said, collapsed to one line and capped at 500
characters (the strip is **one** line — `access.CAPTION_LINES`). `source` is
the manifest id. Unknown keys are reserved and a listener must ignore them.

Datagram and not stream, deliberately: nothing to open, nothing to reconnect,
no ordering to keep, and — the property that actually matters — **no way for a
slow or dead listener to block a child's drawing program.** `sendto` to a
missing path fails immediately with `ENOENT`; to a full queue with `EAGAIN`.
Both are swallowed, the child still hears the line, and the log says once that
the caption did not land.

`kidnix_activity.captions` holds **both** halves — `encode()` and `decode()` —
so the listener has a tested parser to call rather than a fresh `json.loads`,
and the two ends cannot drift. `kidnix_shell.captions` imports `decode` from
it: one wire, one parser, and the shell's own module is only the socket, the
gate and the limiter around it.

### 4.2 What the shell does — BUILT (`kidnix_shell/captions.py`)

B2 — *nothing essential is audio-only* — was open for the half of the screen
time a child spends inside an activity, because the strip is in the shell's
band window and the activity is another process. It is closed:
`kidnix_shell.captions` is the listener, `ShellWindow` starts it at start-up
and stops it on the way out, and `shell/tests/test_captions.py` proves it with
real datagrams on a real socket, headless.

What it does, and the one place the original contract was wrong:

1. binds `$XDG_RUNTIME_DIR/kidnix/captions.sock` as `AF_UNIX`/`SOCK_DGRAM` at
   start-up — directory 0700, socket 0600, a **stale socket unlinked first**
   (nothing unlinks it on SIGKILL) and anything at that path that is *not* a
   socket left alone;
2. reads it with a non-blocking `Gio.Socket` source on the main loop, one
   datagram per callback;
3. `captions.decode()`s each one and drops anything that is not a caption with
   a debug line — malformed JSON, a list, a missing or empty `speak`, bytes
   that are not UTF-8;
4. **speaks it through the shell's own `SpeechManager`, which captions it.**
   This is the reversal. The first version of this contract said "display it,
   never speak it", because the activity had already spoken it — but that is
   what *produces* two voices: two speech-dispatcher connections, two sets of
   settings, and a new utterance in one that cannot cancel the one in the
   other. The datagram now carries the whole utterance. The SDK's
   `ActivitySpeech._on_caption` returns whether the datagram was delivered,
   `SpeechManager.speak` treats a truthy `on_caption` as "somebody else is
   saying this", and so **the activity speaks a line if and only if the socket
   was not there** — no shell, a developer's desktop, a headless test, a full
   queue. One voice, one queue, one strip (08 §3.6);
5. **only while `IN_ACTIVITY`.** A datagram that arrives while the child is on
   Home is from something that should not be talking; it is dropped with a
   debug line. The gate is the state machine, so there is one authority on it;
6. rate-limits per `source`: four a second, which is faster than anything can
   be *said*. Above it the datagram is dropped, and the sender costs the
   journal **one** WARNING rather than one per message — a log line per dropped
   datagram would be the denial of service the limit exists to prevent. The
   limiter's own table of sources is bounded, because the id comes off the
   wire;
7. treats the text as **data**: displayed and spoken, never executed, never
   logged as the child's own words. `decode()` has already collapsed it to one
   line and capped it at 500 characters, which is also what stops a newline in
   a datagram forging a line in the journal; the `source` id is sanitised again
   before it reaches a log line.

**No ack.** The SDK sends from an unbound socket, which has no address to reply
to (`receive_bytes_from` hands back `None`), so an ack could not arrive. The
delivery signal that matters is the one the sender already has: `sendto`
failing when nothing is bound.

**What that costs**, stated plainly: a datagram the shell *accepts* and then
drops — over the rate limit, or outside `IN_ACTIVITY` — is a line the child
neither hears nor reads, because the activity has already decided not to say
it. Both drops are for senders behaving in ways no first-party activity does:
the limit is above human speech, and an activity that is on screen is by
definition what `IN_ACTIVITY` means. A shell that has gone away is the safe
case and the common one — the socket is unlinked, `sendto` fails, and the
activity speaks.

## 5. Millimetres, for the area you are actually given

`ContentArea` carries the panel's `Metrics` (for every millimetre, point and
floor) *and* the width and height of the rectangle below the band:

```python
area = window.area
area.min_target     # 20 mm floor, in logical pixels (ADR-0011)
area.big_button     # 40 mm preferred, floored
area.picture_tile   # 30 mm preferred, floored
area.gap            # 12 mm preferred, 8 mm floor
area.points(24.0)   # a child-facing point size, 18 pt floor
area.columns_for(cell=area.picture_tile, count=8)
```

It is a wrapper and not a shrunken `Metrics` for one reason worth stating:
`Metrics.content_height` **already** subtracts the band from `screen_height`,
so a `Metrics` built with `screen_height = content_height` subtracts it twice
and quietly answers the second question differently from the first. The wrapper
cannot make that mistake and a test pins it.

`width == 0 and height == 0` means "unknown screen" — a headless test, a build
container — and constrains nothing, exactly as `Metrics` already treats
`screen_height`.

## 6. The widgets

All four are `kidnix_shell.widgets.ChildButton` underneath, which is where
SYNTHESIS §2A lives and where it stays. An activity **cannot** accidentally
ship a control that double-fires, because there is no code path here that
could.

| Widget | What it is |
|---|---|
| `BigButton(label, icon, speak_text)` | the primary control: 40 mm square by preference, a picture over a fitted label, one sentence in the ear. `speak_text` falls back to the label. |
| `PictureTile(path, speak_text)` | one picture among several to choose between: 30 mm, a *file* rather than an icon name, the whole of it pressable. |
| `Prompt(text)` | the spoken instruction, written down, with a replay that says **this** prompt rather than the last thing said. `set_text()` changes it without interrupting a child. |
| `GrownUpTurn(body)` | the co-use card (§7). |

Labels go through `fit_gtk_label`: wrap word-then-character, step the point size
down to the 18 pt floor, then add a line. Nothing is ever ellipsised.

The focus ring paints itself with `kid-focus` as well as relying on
`:focus-visible`, because focus is per-toplevel and under gnome-kiosk there is
always another toplevel with the compositor's keyboard focus.

## 7. The grown-up's turn

SUITE §3's central finding: the GraphoGame meta-analysis is g = −0.02 overall
and **0.48** with high adult interaction; the EEF's own trial came out at −1
month with teachers calling the software "highly engaging". The adult is the
active ingredient, so every loop has a moment addressed to them.

`GrownUpTurn` is deliberately **the least child-like object on the screen**:
adult typography (Atkinson Hyperlegible Next, 13 pt), adult density, a dimmed
ground, a rule down the leading edge in the profile's secondary colour. A
four-year-old who cannot read a word of it can see that this block is not for
them, which is what stops it being one more thing to press.

Three rules it keeps:

* **It is not a dialogue and not modal.** It never covers the child's work, it
  takes no focus, and if nobody presses `Done` the activity carries on. An
  adult who has walked away must not be able to strand a child.
* **Its button is an adult's**: 9 mm (08 §3.1e), not the child's 20 mm. Being
  unenticing is the point (08 §4.5).
* **Only the title is read aloud.** The child is told whose turn it is — that
  is information they need and cannot read. What the grown-up is being asked to
  do is on the card, for the grown-up.

## 8. Writing to the Journal

```python
entry = app.save_entry(
    "picture",                    # kind: a lowercase slug
    [png_path],                   # files, copied in version order
    caption="A teal square",      # one line; becomes the title if short
    voice=note_ogg,               # optional "tell me about it"
    meta={"colour": "teal"},      # anything JSON-serialisable, back on resume
)
```

It writes the shell's own layout, exactly (spec §5), because My Things reads it
with the shell's own loader and a second spelling would be a second bug:

```
$XDG_DATA_HOME/kidnix/profiles/<profile>/journal/YYYY/MM/DD/<entry-id>/
    entry.json    the shell's Entry dataclass, written by the shell's own code
    v001.png      what the child made (v002… for later saves)
    thumb.png     256 px, images only (GdkPixbuf, the same call the importer makes)
    caption.txt   what they called it, if they said
    note.ogg      the voice note, where kidnix_shell.voice looks for it
    meta.json     ours
```

Four decisions, each of which is a trap somebody would otherwise fall into:

* **`meta` gets its own file.** `entry.json` is written by
  `kidnix_shell.journal.Entry`, whose `to_dict` is `asdict` — any key we added
  would be silently dropped the next time the shell rewrote the entry, which it
  does every time a child stars something. A test stars an SDK entry and
  asserts the meta survives.
* **`source_path` is empty.** The shell uses it to recognise a file it has
  already imported; an SDK entry was never imported, and pointing it at a
  temporary file would make the importer match a path that will not exist
  tomorrow. Resume does not need it — the shell resumes from
  `entry.latest_path`, the copy inside the entry directory.
* **The entry is assembled elsewhere and renamed in.** `Journal.load()` globs
  `*/*/*/*/entry.json`, so a half-written directory sitting in the day's folder
  is an entry the shell can find and fail to parse. Everything is built under
  `<journal>/.incoming/`, two levels deep where that glob cannot reach, and
  moved with one `rename`.
* **`JournalError` is loud.** Everything else in this SDK degrades quietly — a
  dead speech-dispatcher, a missing caption socket, an unknown monitor — because
  the child can carry on without it. Losing the thing they just made is the one
  failure that is not survivable.

An SDK activity therefore needs **no `journal_watch`** in its manifest, and the
validator warns if it has one: the importer would keep the same work twice.

## 9. The manifest

The shell's parser (`kidnix_shell.activities.parse_manifest`) gets the first
word — there is deliberately no second parser, because two parsers is how a
manifest comes to validate in CI and be skipped on the machine. On top of it
`kidnix_activity.manifest` enforces the half a third-party manifest is allowed
to break and ours is not:

| Rule | Why |
|---|---|
| `network_required = false` | SUITE §1. The child session has no egress (SYNTHESIS H1). |
| `quit = "signal"` | §3.3. We save; we never ask. |
| `goal` present | One honest line for a parent. |
| `audio_label` present | Pre-reader first: the tile is heard before it is read. |
| `icon` present | For a child with no English, low vision or CVD it is the only persistent channel (ADR-0011). |
| `kind = "activity"` | A shelf is a screen the shell draws. |

Warnings (true, not fatal): `journal_watch` set, no `age_band`, `exec_resume`
set.

```bash
kidnix-activity validate <file-or-directory>   # non-zero on any error
kidnix-activity new "Clock and time" --dir ../activities
```

## 10. Building, testing and packaging one

```bash
kidnix-activity new "Clock and time" --dir ../activities
cd ../activities/clock-and-time
uv venv --system-site-packages && uv sync --active
uv run --active pytest              # headless; the CI floor
kidnix-activity validate clock-and-time.toml
```

* **Headless tests are the floor.** Put everything worth proving in `logic.py`
  and test it with no display. GTK tests may skip; logic tests may not.
* **Never open a window on the developer's desktop.** Run under GTK's Broadway
  backend: `gtk4-broadwayd :107 &` then
  `GDK_BACKEND=broadway BROADWAY_DISPLAY=:107 python -m <module>`.
  `just hello-draw` (in `shell/`) does exactly that.
* **Dependencies come from the image, not PyPI.** `kidnix_activity`,
  `kidnix_shell`, PyGObject, GTK4, libadwaita, GdkPixbuf and `speechd` are all
  system packages; declare **no** runtime dependencies and create the venv with
  `--system-site-packages`.
* **Packaging**: for now a Python package copied into the image beside the
  shell, exactly as `build_files/60-shell.sh` copies `kidnix_activity`; RPM
  later; third-party activities stay upstream RPMs (SUITE §2).
* **e2e**: each activity ships one step the shell's e2e can include — launch,
  make one thing, find it in My Things.

## 11. What the shell does for you

| | |
|---|---|
| the band | Back, Undo, My Things, the sun, the Ear, the grown-up gate — visible over your window, always |
| your captions, and your voice | every line you speak reaches the strip under the band, and the shell says it (§4.2) |
| Back and Escape | ending your activity, with SIGTERM and a grace |
| the session | the clock, the ending offer, put away, goodbye. **You never end the session and you never ask about time.** |
| My Things | drawing and resuming the cards you write |
| read-aloud of *its* chrome | its own buttons; yours are yours |
| the profile | which child, which Journal, which age band, which colours |
| calm, volume, captions | read once from `parent.toml` and handed to you |

## 12. What you must not do

* **No network.** Not a fetch, not a check for updates, not telemetry, not a
  font from a CDN. `network_required` is always false and the session has no
  egress anyway (SYNTHESIS H1).
* **No quit dialogue, and no "are you sure?".** Save on SIGTERM (§3.3).
* **No reward economy** (SUITE §5): no points, stars, streaks, levels, badges,
  coins, "well done!", or anything that makes stopping cost something. A test
  greps the example for those words.
* **No text-only UI.** Every control is a picture plus a word plus a sentence
  in the ear. A pre-reader must be able to use it with the labels covered.
* **No scores, ages, percentiles or dashboards of the child** (SUITE §5, F4).
* **No AI in the child session** (ADR-0009), and no ASR grading of a child's
  reading, ever (SUITE §3).
* **No digits where a child can see or hear them** (01 #19, 03 #32). "About as
  long as one story", never "twelve minutes".
* **No free scrolling, no double-click, no right-click, no long-press** (A2,
  A4). Use the SDK's widgets and you get this for free.
* **Do not draw a band, a clock, a back button or a way out.** They exist, one
  screen up, in the same place in every activity.

## 13. Still open after this pass

1. **A dropped datagram is a lost line** (§4.2). The wire has no way to say
   "I did not take that" to a sender that has already decided not to speak,
   because a datagram sender has no reply address. Rate-limited and
   out-of-state drops are therefore silent for the child. Giving the SDK a
   bound socket to be acked on would fix it and costs a connection's worth of
   state in every activity; nobody has needed it yet.
2. **The example is not on Home.** `hello-draw.toml` is deliberately not in
   `system_files/usr/share/kidnix/activities/`; `--demo` listing it is a small
   follow-up in `demo.py`, which this pass did not touch.
3. **`ContentArea` trusts the compositor.** It computes the rectangle from the
   monitor and the band's height rather than measuring what it was actually
   given. The shell learned the hard way that those can differ (impl. notes
   §19.1); an activity that overflows should log the difference, and there is
   no measured-fit backstop here yet.
4. **`kind` is free-form.** A slug, validated as a slug, with no vocabulary
   behind it. When the suite is further on, `picture` / `writing` / `sound` /
   `tune` probably wants to be a closed set the Journal can filter on.
5. **Resume is unwired.** `meta.json` is written and nothing reads it back. The
   shell resumes an entry by re-launching with `exec_resume` and the file path;
   an SDK activity that wanted its `meta` back would have to find the entry
   directory from that path. It works, but nobody has done it.
6. **No `--demo` for activities.** An activity has no scratch-journal mode of
   its own; `save_entry(journal_root=...)` is the mechanism and there is no
   flag on top of it.
