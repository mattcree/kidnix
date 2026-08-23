"""``--screenshot``: photograph Find it and Blend it, then quit.

Run under GTK's Broadway backend, never on a developer's desktop -- the SDK
says so (``docs/design/activity-sdk.md`` 10) and the reason is that an activity
that opens a window on the machine you are working on is an activity somebody
will eventually ship a screenshot of with their own wallpaper behind it::

    gtk4-broadwayd :8 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:8 \\
        kidnix-sounds-and-words --screenshot docs/design/screenshots --seed 3

Capturing takes the same two routes the shell's own ``--screenshot`` does, and
for the same measured reason: ``Gtk.WidgetPaintable`` hands back the widget's
*last painted* content and returns nothing at all when the widget is waiting
for a redraw -- which is the normal state of a window nobody is compositing,
i.e. every automated screenshot run. So when the paintable comes back empty the
tree is walked directly, which always has an answer.
"""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402

from .pictures import PICTURE_WORDS  # noqa: E402
from .reading import texts_for  # noqa: E402
from .schedule import ItemKind  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["capture", "run_screenshots"]

#: Long enough for Broadway to have laid the window out at least once. A
#: capture before the first allocation comes back empty and writes nothing --
#: measured, and the reason this is two seconds rather than a few hundred
#: milliseconds.
FIRST_FRAME_MS = 2000
#: Between building a screen and photographing it. A tree that was built in
#: this callback has not been laid out yet, so the shot has to wait a frame.
SETTLE_MS = 1200


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


def _blend_word(activity) -> str | None:
    """A word for the Blend it shot: one with a picture, if the plan has one."""
    words = [item.payload for item in activity.plan.items if item.kind is ItemKind.BLEND_IT]
    for word in words:
        if word in PICTURE_WORDS:
            return word
    return words[0] if words else None


def run_screenshots(app: ActivityApplication, activity, out_dir: Path) -> int:
    """Build each screen in turn, photograph it, and exit. Returns a process code.

    A chain rather than a loop, because each shot has to wait a frame for the
    tree it just built to be laid out, and a frame is a timeout rather than a
    line of code.
    """
    from .activity import build_blend_it, build_find_it
    from .reader import build_read_it, build_shelf

    state: dict[str, object] = {"ok": True}

    def build_find(window: ActivityWindow) -> None:
        item = next((i for i in activity.plan.items if i.kind is ItemKind.FIND_IT), None)
        if item is None:
            log.warning("no Find it item in today's plan; saw-find-it.png not written")
            state["ok"] = False
            return
        gpc = activity.corpus.gpc_by_id.get(item.gpc_id or "")
        if gpc is not None:
            activity.screen = build_find_it(window, activity, gpc)

    def build_blend(window: ActivityWindow) -> None:
        word = _blend_word(activity)
        if word is None:
            log.warning("no blend word in today's plan; saw-blend-it.png not written")
            state["ok"] = False
            return
        activity.screen = build_blend_it(window, activity, word)

    def build_shelf_screen(window: ActivityWindow) -> None:
        books = activity.shelf_for()
        if not books:
            log.warning("no book inside this ceiling; saw-read-shelf.png not written")
            state["ok"] = False
            return
        activity.screen = build_shelf(window, activity, books, lambda book: None)

    def build_book(window: ActivityWindow) -> None:
        books = texts_for(activity.corpus, activity.ceiling)
        if not books:
            log.warning("no book inside this ceiling; saw-read-it.png not written")
            state["ok"] = False
            return
        # The last one the ceiling admits: the most interesting sentence, and
        # the one whose drawing is doing the most work.
        activity.screen = build_read_it(window, activity, books[-1], narration=activity.narration)

    #: What to build, and what to call the photograph of it. The Blend it shot
    #: is of the *sounds* stage, before the tiles have been pushed together,
    #: because the dots and the bars are the point of that picture.
    STEPS = [
        (build_find, "saw-find-it.png"),
        (build_blend, "saw-blend-it.png"),
        (build_shelf_screen, "saw-read-shelf.png"),
        (build_book, "saw-read-it.png"),
    ]

    def step(index: int, window: ActivityWindow) -> bool:
        if index >= len(STEPS):
            app.quit()
            return GLib.SOURCE_REMOVE
        builder, name = STEPS[index]
        builder(window)
        # One frame between building the tree and photographing it: a widget
        # that has never been laid out has nothing to paint.
        GLib.timeout_add(SETTLE_MS, shoot, index, name, window)
        return GLib.SOURCE_REMOVE

    def shoot(index: int, name: str, window: ActivityWindow) -> bool:
        state["ok"] = capture(window, out_dir / name) and state["ok"]
        GLib.timeout_add(1, step, index + 1, window)
        return GLib.SOURCE_REMOVE

    def build(window: ActivityWindow) -> None:
        activity.window = window
        activity._load_css()
        build_find(window)
        GLib.timeout_add(FIRST_FRAME_MS, shoot, 0, "saw-find-it.png", window)

    app.set_build(build)
    # Nothing is saved on a screenshot run: it is not a session, no child sat
    # through it, and a card in My Things saying "read today: cat" would be a
    # lie about a person.
    app.set_on_finish(lambda: log.info("screenshot run: nothing saved, by design"))
    code = app.run(["kidnix-sounds-and-words"])
    return code if code else (0 if state["ok"] else 1)
