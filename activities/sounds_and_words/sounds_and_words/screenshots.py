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
    """Build both screens, photograph each, and exit. Returns a process code."""
    from .activity import build_blend_it, build_find_it

    state: dict[str, object] = {"ok": True}

    def shoot_blend(window: ActivityWindow) -> bool:
        # The bars and dots are the point of the picture, so the shot is of the
        # sounds stage, before the tiles have been pushed together.
        state["ok"] = capture(window, out_dir / "saw-blend-it.png") and state["ok"]
        app.quit()
        return GLib.SOURCE_REMOVE

    def build_blend(window: ActivityWindow) -> bool:
        word = _blend_word(activity)
        if word is None:
            log.warning("no blend word in today's plan; saw-blend-it.png not written")
            state["ok"] = False
            app.quit()
            return GLib.SOURCE_REMOVE
        activity.screen = build_blend_it(window, activity, word)
        # One frame between building the tree and photographing it: a widget
        # that has never been laid out has nothing to paint.
        GLib.timeout_add(SETTLE_MS, shoot_blend, window)
        return GLib.SOURCE_REMOVE

    def shoot_find(window: ActivityWindow) -> bool:
        state["ok"] = capture(window, out_dir / "saw-find-it.png") and state["ok"]
        GLib.timeout_add(1, build_blend, window)
        return GLib.SOURCE_REMOVE

    def build(window: ActivityWindow) -> None:
        activity.window = window
        activity._load_css()
        item = next((i for i in activity.plan.items if i.kind is ItemKind.FIND_IT), None)
        if item is not None:
            gpc = activity.corpus.gpc_by_id.get(item.gpc_id or "")
            if gpc is not None:
                activity.screen = build_find_it(window, activity, gpc)
        GLib.timeout_add(FIRST_FRAME_MS, shoot_find, window)

    app.set_build(build)
    # Nothing is saved on a screenshot run: it is not a session, no child sat
    # through it, and a card in My Things saying "read today: cat" would be a
    # lie about a person.
    app.set_on_finish(lambda: log.info("screenshot run: nothing saved, by design"))
    code = app.run(["kidnix-sounds-and-words"])
    return code if code else (0 if state["ok"] else 1)
