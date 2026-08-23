"""``--screenshot``: photograph "Who for?" and "Make it", then quit.

Run under GTK's Broadway backend, **never** on a developer's desktop -- the SDK
says so (``docs/design/activity-sdk.md`` section 10) and AGENTS.md says it
twice::

    gtk4-broadwayd :14 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:14 \\
        kidnix-letters --screenshot docs/design/screenshots

Two shots, because they are the two halves of the activity a picture can
actually show: the row of faces (purpose and audience -- the whole point) and
the picture step (what a five-year-old's letter is made of). "Post it" and the
shelf are one line of text and one thumbnail respectively, which a screenshot
does not explain better than a sentence does.

Capturing takes the same two routes the shell's own ``--screenshot`` does, and
for the same measured reason: ``Gtk.WidgetPaintable`` hands back the widget's
*last painted* content and returns nothing at all when the widget is waiting for
a redraw -- which is the normal state of a window nobody is compositing, i.e.
every automated screenshot run. So when the paintable comes back empty the tree
is walked directly, which always has an answer.

**Nothing is saved on a screenshot run.** No child sat through it, and a letter
in the outbox addressed to somebody's real grandfather because a build ran would
be the worst bug in this package.
"""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402

from . import draw  # noqa: E402
from .journal_read import recent_pictures  # noqa: E402
from .recipients import Recipient  # noqa: E402
from .scribble import Scribble  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["DEMO_FAMILY", "capture", "run_screenshots"]

#: Long enough for Broadway to have laid the window out at least once.
FIRST_FRAME_MS = 900
#: Between the two shots.
BETWEEN_MS = 1400

#: Who the screenshot is addressed to when the machine taking it has no
#: ``[[family]]`` list -- a build container, or a developer's checkout. Invented
#: names, no photos, so the shot shows the drawn placeholder, which is what most
#: households will actually see on day one.
DEMO_FAMILY = (
    Recipient(id="grandad", name="Grandad", relation="Grandpa"),
    Recipient(id="nanna", name="Nanna", relation="Grandma"),
    Recipient(id="auntie-jo", name="Auntie Jo", relation="Aunt"),
)


#: Two drawings to stand in for the child's own, when the profile taking the
#: screenshot has an empty Journal (a build container, a fresh checkout). The
#: picture step is *about* sending something you already made, so a shot of it
#: with nothing to choose between would be a picture of the wrong screen.
DEMO_STROKES = (
    (("teal", ((0.15, 0.7), (0.3, 0.3), (0.45, 0.7), (0.15, 0.7))),
     ("pink", ((0.55, 0.72), (0.62, 0.35), (0.72, 0.55), (0.82, 0.3), (0.88, 0.72))),
     ("black", ((0.1, 0.85), (0.9, 0.85)))),
    (("pink", ((0.2, 0.5), (0.35, 0.25), (0.5, 0.5), (0.35, 0.75), (0.2, 0.5))),
     ("teal", ((0.6, 0.6), (0.75, 0.28), (0.9, 0.6))),
     ("black", ((0.12, 0.88), (0.88, 0.88)))),
)
DEMO_TITLES = ("My dinosaur", "The park")


def seed_demo_journal(root: Path) -> Path:
    """Write two drawings into a scratch Journal, in the shell's own layout.

    **Development only, and never the child's own Journal.** ``root`` is a
    directory the caller made for this run; nothing here writes to
    ``$XDG_DATA_HOME`` and nothing here is reachable from ``main()`` except
    through ``--screenshot``.
    """
    import json

    for index, (strokes, title) in enumerate(zip(DEMO_STROKES, DEMO_TITLES, strict=True)):
        scribble = Scribble()
        for key, points in strokes:
            scribble.choose(key)
            scribble.start(*points[0])
            for point in points[1:]:
                scribble.extend(*point)
            scribble.end()
        entry_id = f"demo{index}"
        directory = root / "2026" / "08" / "20" / entry_id
        picture = draw.render_scribble(directory / "v001.png", scribble, 320, 240)
        draw.render_scribble(directory / "thumb.png", scribble, 256, 192)
        (directory / "entry.json").write_text(
            json.dumps(
                {
                    "id": entry_id,
                    "activity_id": "hello-draw",
                    "created": f"2026-08-2{index}T10:00:00",
                    "updated": f"2026-08-2{index}T10:00:00",
                    "title": title,
                    "source_path": "",
                    "mime": "image/png",
                    "versions": [
                        {
                            "filename": "v001.png",
                            "imported": "2026-08-20",
                            "size": picture.stat().st_size,
                            "sha256": "",
                        }
                    ],
                }
            )
        )
    return root


def capture(window: Gtk.Widget, path: Path) -> bool:
    """Write ``window`` to ``path`` as a PNG. Never raises."""
    try:
        width = window.get_width() or 1280
        height = window.get_height() or 720
        native = window.get_native()
        renderer = native.get_renderer() if native is not None else None
        if renderer is None:
            log.warning("no renderer yet; %s not written", path)
            return False

        paintable = Gtk.WidgetPaintable.new(window)
        snapshot = Gtk.Snapshot()
        paintable.snapshot(snapshot, width, height)
        node = snapshot.to_node()
        if node is None:
            direct = Gtk.Snapshot()
            window.do_snapshot(window, direct)
            node = direct.to_node()
        if node is None:
            log.warning("nothing to capture yet; %s not written", path)
            return False

        texture = renderer.render_texture(node, None)
        path.parent.mkdir(parents=True, exist_ok=True)
        texture.save_to_png(str(path))
        log.info("wrote %s (%dx%d)", path, width, height)
        return True
    except Exception as exc:  # pragma: no cover - a display that will not draw
        log.warning("could not capture %s: %s", path, exc)
        return False


def run_screenshots(app: ActivityApplication, activity, out_dir: Path) -> int:
    """Build both screens, photograph each, and exit. Returns a process code.

    **This does not call ``Gio.Application.run()``**, and the reason is worth
    writing down because it looks like a shortcut and is not.

    ``run()`` registers the application on the session bus before it activates
    anything. On the machine this ships to that is instant. On a build
    container, a sandboxed test runner or a terminal outside the developer's own
    session there is no reachable bus, and ``g_application_register`` spends the
    D-Bus default timeout -- **25 seconds, measured** -- failing, and then
    ``run()`` returns *without having activated at all*. The result was a
    screenshot recipe that took half a minute and wrote nothing.

    ``do_activate()`` is the half a screenshot needs: the CSS, the window, the
    speech bridge, the signal handler and the activity's ``build``. It is the
    same code path the shell takes on the machine, minus the bus. The main loop
    is then ours, because the shots are timed.
    """
    state: dict[str, object] = {"ok": True}
    if not activity.people:
        activity.people = list(DEMO_FAMILY)
    if not recent_pictures(activity.journal_root):
        activity.journal_root = seed_demo_journal(activity.scratch / "demo-journal")

    if not Gtk.init_check():  # pragma: no cover - no display at all
        log.error(
            "GTK would not initialise. Screenshots run under Broadway, never on "
            "a desktop: gtk4-broadwayd :14 & GDK_BACKEND=broadway "
            "BROADWAY_DISPLAY=:14 kidnix-letters --screenshot <dir>"
        )
        return 1

    loop = GLib.MainLoop()

    def shoot_make(window: ActivityWindow) -> bool:
        state["ok"] = capture(window, out_dir / "letters-make.png") and state["ok"]
        loop.quit()
        return GLib.SOURCE_REMOVE

    def shoot_who(window: ActivityWindow) -> bool:
        state["ok"] = capture(window, out_dir / "letters-who-for.png") and state["ok"]
        # Straight to the picture step, so the second shot is the half of the
        # activity a picture can explain: what a five-year-old's letter is
        # made of.
        activity.choose_recipient(activity.people[0])
        GLib.timeout_add(BETWEEN_MS, shoot_make, window)
        return GLib.SOURCE_REMOVE

    # Nothing is kept and nothing is posted on a screenshot run: no child sat
    # through it, and a letter in the outbox addressed to somebody's real
    # grandfather because a build ran would be the worst bug in this package.
    app.set_on_finish(lambda: log.info("screenshot run: nothing kept, nothing posted"))
    app.set_build(activity.build)
    app.do_activate()
    window = app.window
    if window is None:  # pragma: no cover - a compositor that gave us nothing
        log.error("no window was built; nothing to photograph")
        return 1
    GLib.timeout_add(FIRST_FRAME_MS, shoot_who, window)
    loop.run()
    return 0 if state["ok"] else 1
