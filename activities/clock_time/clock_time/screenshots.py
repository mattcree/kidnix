"""``--screenshot``: photograph both screens, then quit.

Run under GTK's Broadway backend, **never** on a developer's desktop -- the SDK
says so (``docs/design/activity-sdk.md`` section 10) and the reason is that an
activity that opens a window on the machine you are working on is an activity
somebody will eventually ship a screenshot of with their own wallpaper behind
it::

    gtk4-broadwayd :11 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:11 \\
        kidnix-clock-time --screenshot docs/design/screenshots

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

from .minute import Phase  # noqa: E402
from .words import ClockTime  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["capture", "run_screenshots"]

#: Long enough for Broadway to have laid the window out at least once.
FIRST_FRAME_MS = 900
#: Between the two shots.
BETWEEN_MS = 1400

#: The time the "play" shot is taken at. Half past three, because it is the
#: phrase the brief names, it is legal in both Year 1 and Year 2, and it lands
#: on "home time" in the default routine -- so the picture shows the link the
#: activity is for rather than a clock floating on its own.
SHOT_TIME = ClockTime.of(3, 30)


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
    """Build both screens, photograph each, and exit. Returns a process code."""
    state: dict[str, object] = {"ok": True}

    def shoot_minute(window: ActivityWindow) -> bool:
        # Part-way through "watch a minute", so the shot shows the disc down
        # and the ghost of where it started -- which is the whole point of the
        # picture. Set directly rather than by waiting thirty seconds for it.
        activity.phase = Phase.SHOWING
        if activity.disc is not None:
            activity.disc.set_state(Phase.SHOWING, 0.55)
        state["ok"] = capture(window, out_dir / "clock-minute.png") and state["ok"]
        app.quit()
        return GLib.SOURCE_REMOVE

    def shoot_play(window: ActivityWindow) -> bool:
        state["ok"] = capture(window, out_dir / "clock-play.png") and state["ok"]
        activity.build_minute(window)
        GLib.timeout_add(BETWEEN_MS, shoot_minute, window)
        return GLib.SOURCE_REMOVE

    def build(window: ActivityWindow) -> None:
        activity.build(window)
        activity.set_time(SHOT_TIME, speak=False, played=False)
        GLib.timeout_add(FIRST_FRAME_MS, shoot_play, window)

    app.set_build(build)
    # Nothing is saved on a screenshot run: it is not a session, no child sat
    # through it, and a card in My Things saying "half past three" would be a
    # lie about a person.
    app.set_on_finish(lambda: log.info("screenshot run: nothing saved, by design"))
    code = app.run(["kidnix-clock-time"])
    return code if code else (0 if state["ok"] else 1)
