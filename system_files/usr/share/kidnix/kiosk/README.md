# kidnix window configuration for gnome-kiosk

Templates for `window-config.ini`, the one file that decides where gnome-kiosk
puts a window and whether it is fullscreen. Evidence and measurements:
`docs/spikes/band-over-activity.md`. The code that renders them is
`shell/kidnix_shell/kiosk.py`, which holds these three files as string constants
— `shell/tests/test_kiosk.py` asserts that the copies here are byte-identical to
them, so the file the session installs and the file the shell writes cannot
drift apart.

**These are shipped.** `/usr/bin/kidnix-shell` installs the seed before
`gnome-session` starts; the shell renders the other two.

## Why there are three of them

gnome-kiosk only honours `set-x` / `set-y` / `set-width` / `set-height` /
`set-fullscreen` / `lock-on-area` while a window is still *initial* — during its
very first configure. At that instant a Wayland toplevel has **no `app_id` yet**,
so `match-class` cannot match it, and a section that matches only later is
ignored for geometry. Measured, with gnome-kiosk's own debug log as evidence, in
the spike (experiment 07).

The consequence: **only a catch-all section can place a window.** There is no
negation syntax, so one static file cannot say "the band goes at the top and
everything else goes below" — the catch-all would drag the band down too
(experiments 03 and 05 did exactly that).

So the placement is sequenced in time instead of by name. gnome-kiosk re-reads
this file whenever it changes, and each window's initial config is consumed
once, so a window keeps whatever it was given:

| When | File in place | What the catch-all describes |
|---|---|---|
| before gnome-kiosk starts | `window-config.seed.ini` | nothing — no geometry at all |
| shell start, before the band window is created | `window-config.band.ini` | the band strip, `0,0 W×H_band` |
| once the band window is mapped, and from then on | `window-config.activity.ini` | everything below the band, `0,H_band W×(H−H_band)` |

The shell writes the third file and never needs to touch it again: the content
window and every activity launched afterwards are all placed below the band.

**The step between the second and the third is a confirmation, not a timer.**
gnome-kiosk reloads this file on its own schedule (measured: about 260 ms after
a write), and a window's geometry is settled for good at its first configure --
which happens *after* GTK has already emitted `map`. So the shell presents the
band and then polls the window's own allocation until it really is the strip;
only then does it write the third file. v0.1.5.0 trusted `map` instead, wrote
the third file into the gap, gnome-kiosk coalesced the whole burst, and the band
was placed by the "everything below the band" rule -- on top of everything, with
the content window invisible underneath it. If three fresh toplevels all fail to
get the strip, the shell stops using this file at all and goes back to
gnome-kiosk's defaults.

## The `@TOKENS@`

The band and activity files are templates. The shell substitutes real numbers
from the monitor it measured (`metrics.py` computes the band height, clamped
80–128 px):

- `@WIDTH@`, `@HEIGHT@` — the monitor's pixel size
- `@BAND_HEIGHT@` — the band's height
- `@CONTENT_HEIGHT@` — `@HEIGHT@ − @BAND_HEIGHT@`

Rendered output goes to `$XDG_CONFIG_HOME/gnome-kiosk/window-config.ini`
(`/var/home/kid/.config/gnome-kiosk/window-config.ini`).

`kiosk.render()` raises rather than emitting a file with a token left in it: an
unreplaced `@WIDTH@` is a value gnome-kiosk's ini parser silently drops, and the
failure would only ever appear as a window in the wrong place.

## The seeding requirement, and why the seed has no numbers in it

`window-config.ini` must exist **before gnome-kiosk starts**. gnome-kiosk
resolves the config path once, at compositor start-up, and arms its
`GFileMonitor` *only if the user file existed at that moment*
(`kiosk-window-config.c`, `setup_file_monitoring()` returns early when
`user_config_file_path` is `NULL`). A file created afterwards is never noticed,
however many times it is rewritten — this cost the spike its first three runs.

`/usr/bin/kidnix-shell` is the right place: it already writes into
`$HOME/.config` before `exec`ing `gnome-session`. One line:

```sh
install -D -m 0644 /usr/share/kidnix/kiosk/window-config.seed.ini \
    "${HOME}/.config/gnome-kiosk/window-config.ini"
```

It runs on **every** login, not just the first, and that is load-bearing: the
file the previous session left behind is the phase-B one, and a band window
created against phase B would be placed below itself.

The seed carries **no geometry**, deliberately. The wrapper runs before the
compositor, so it cannot measure a monitor, and gnome-kiosk's geometry keys are
absolute pixels — `CONFIG.md` types `set-x`/`set-y`/`set-width`/`set-height` as
integers and `lock-on-area` as the literal `"x,y WxH"`; there is no percentage
form, and the only monitor-relative form (`set-on-monitor` +
`lock-on-monitor-area`) needs a monitor *name* the wrapper cannot know either.
A guessed catch-all would be worse than none: if the shell then failed to start,
every activity would be squeezed into a strip on the wrong-sized panel. With no
geometry, a session whose shell never came up behaves exactly as it did before
the band existed.

## The `[band]` section

`set-above` is *not* subject to the initial-configure rule — it is applied on
every pass, including the late one after `app_id` and title are known. So
matching the band by title works, and it is what keeps the band above a
fullscreen-sized activity. `set-above=false` never *lowers* an already-raised
window (gnome-kiosk only ever calls `meta_window_make_above()`, never
`unmake_above`), so the catch-all's `set-above=false` cannot undo it.

Match on **title**, not class: both shell windows share the app id
`org.kidnix.Shell` (one process, one `GtkApplication` — two processes sharing an
application id do not get two windows), and only the band may be above. The
titles are `kidnix-band` and `kidnix-content`, defined once in
`shell/kidnix_shell/kiosk.py`.

## What we deliberately do not use

- **`set-window-type=dock`** is what the documentation advertises for panels and
  it empirically held the band on top (spike experiment 01). Do not use it:
  mutter's `meta_window_get_default_layer()` drops a `META_WINDOW_DOCK` to
  `META_LAYER_BOTTOM` whenever `window->monitor->in_fullscreen`, which would put
  the band *behind* the first activity that really does own the monitor.
  `set-above` takes the `wm_state_above` branch, which has no fullscreen
  condition.
- **`match-tag`** is upstream's own mechanism and would delete the phased
  rewrite entirely, since a tag is known at window creation and so beats the
  initial-configure rule. mutter 50.4 implements `xdg_toplevel_tag_v1`; GTK
  4.22.4 does not expose it (no `xdg_toplevel_tag` symbol in `libgtk-4.so.1`).
  Revisit when GTK gains it.
- **`set-on-monitor` / `lock-on-monitor-area`** are the multi-head equivalents
  of what we use and are untested here. The target hardware is one panel.
