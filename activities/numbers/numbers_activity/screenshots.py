"""``--screenshot``: photograph both halves of the loop, then quit.

Run under GTK's Broadway backend, **never** on a developer's desktop -- the SDK
says so (``docs/design/activity-sdk.md`` section 10) and AGENTS.md says so
again::

    gtk4-broadwayd :12 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:12 \\
        kidnix-numbers --screenshot docs/design/screenshots --seed 5

Capturing takes the same two routes the shell's own ``--screenshot`` does, and
for the same measured reason: ``Gtk.WidgetPaintable`` hands back the widget's
*last painted* content and returns nothing at all when the widget is waiting for
a redraw -- which is the normal state of a window nobody is compositing, i.e.
every automated screenshot run. So when the paintable comes back empty the tree
is walked directly, which always has an answer.

The "how many?" shot is taken **with the dots still up**. The flash is the
mechanic and a photograph of the moment after it is a photograph of an empty
rectangle; the timer that would hide them is cancelled first rather than raced.
"""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402

from .items import HowMany, MakeBond  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["capture", "run_screenshots"]

#: Long enough for Broadway to have laid the window out at least once.
FIRST_FRAME_MS = 900
#: Between the two shots.
BETWEEN_MS = 800


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
    """Build one of each item, photograph it, and exit. Returns a process code."""
    state: dict[str, object] = {"ok": True}

    def _first(kind) -> int:
        for index, item in enumerate(activity.items):
            if isinstance(item, kind):
                return index
        return 0

    def _biggest_how_many() -> int:
        """The most dots this session asks about.

        A screenshot of two dots is a true picture of the activity and a poor
        one: the thing worth photographing is a canonical arrangement with
        enough in it to see why canonical matters.
        """
        best, count = _first(HowMany), -1
        for index, item in enumerate(activity.items):
            if isinstance(item, HowMany) and item.count > count:
                best, count = index, item.count
        return best

    def shoot_bond(window: ActivityWindow) -> bool:
        state["ok"] = capture(window, out_dir / "numbers-make-five.png") and state["ok"]
        app.quit()
        return GLib.SOURCE_REMOVE

    def shoot_how_many(window: ActivityWindow) -> bool:
        # The dots must still be on the card. Cancelling the hide is not
        # cheating -- it is the same picture a child sees for a second and a
        # half, held still for a camera that cannot see a second and a half.
        activity._cancel_timers()
        item = activity.items[_biggest_how_many()]
        if activity.card is not None:
            activity.card.show_arrangement(item.arrangement)
        state["ok"] = capture(window, out_dir / "numbers-how-many.png") and state["ok"]

        activity.index = _first(MakeBond)
        activity.start_item()
        activity._cancel_timers()
        # One counter already in, so the shot shows both kinds: the ones that
        # were there (solid) and the one the child put in (a ring).
        if activity.frame is not None and activity.frame.targets:
            first_box = min(activity.frame.targets)
            activity.frame.placed.add(first_box)
            activity.frame._sync()
        GLib.timeout_add(BETWEEN_MS, shoot_bond, window)
        return GLib.SOURCE_REMOVE

    def build(window: ActivityWindow) -> None:
        activity.build(window)
        activity.index = _biggest_how_many()
        activity.start_item()
        GLib.timeout_add(FIRST_FRAME_MS, shoot_how_many, window)

    app.set_build(build)
    # Nothing is saved on a screenshot run: it is not a session, no child sat
    # through it, and a card in My Things saying what was practised today would
    # be a lie about a person.
    app.set_on_finish(lambda: log.info("screenshot run: nothing saved, by design"))
    code = app.run(["kidnix-numbers"])
    return code if code else (0 if state["ok"] else 1)
