# kidnix window configuration for gnome-kiosk

Templates for `window-config.ini`, the one file that decides where gnome-kiosk
puts a window and whether it is fullscreen. Evidence and measurements:
`docs/spikes/band-over-activity.md`.

These are **prototypes**, not yet wired into the image. They exist so the shell
change and the session change can be written against a shape that has already
been proven on the real compositor.

## Why there are two of them

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
| shell start, before the band window is created | `window-config.band.ini` | the band strip, `0,0 W×H_band` |
| once the band window is mapped, and from then on | `window-config.activity.ini` | everything below the band, `0,H_band W×(H−H_band)` |

The shell writes the second file and never needs to touch it again: the content
window and every activity launched afterwards are all placed below the band.

## The `@TOKENS@`

Both files are templates. The shell substitutes real numbers from the monitor it
measured (`metrics.py` already computes the band height, clamped 80–128 px):

- `@WIDTH@`, `@HEIGHT@` — the monitor's pixel size
- `@BAND_HEIGHT@` — the band's height
- `@CONTENT_HEIGHT@` — `@HEIGHT@ − @BAND_HEIGHT@`

Rendered output goes to `$XDG_CONFIG_HOME/gnome-kiosk/window-config.ini`
(`/var/home/kid/.config/gnome-kiosk/window-config.ini`).

## The seeding requirement

`window-config.seed.ini` must be copied into place **before gnome-kiosk starts**.
gnome-kiosk resolves the config path once, at compositor start-up, and arms its
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

## The `[band]` section

`set-above` is *not* subject to the initial-configure rule — it is applied on
every pass, including the late one after `app_id` and title are known. So
matching the band by title works, and it is what keeps the band above a
fullscreen-sized activity. `set-above=false` never *lowers* an already-raised
window (gnome-kiosk only ever calls `meta_window_make_above()`, never
`unmake_above`), so the catch-all's `set-above=false` cannot undo it.

Match on **title**, not class: both shell windows share the app id
`org.kidnix.Shell`, and only the band may be above.
