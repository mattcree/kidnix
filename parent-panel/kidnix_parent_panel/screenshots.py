"""``--screenshot``: photograph every tab, then quit.

Run under GTK's **Broadway** backend, never on a developer's desktop
(AGENTS.md §5)::

    gtk4-broadwayd :10 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:10 \\
        kidnix-parent-panel --screenshot docs/design/screenshots

The capture takes the same two routes the shell's own ``--screenshot`` does,
for the same measured reason: ``Gtk.WidgetPaintable`` hands back the widget's
*last painted* content and returns nothing at all while the widget is waiting
for a redraw -- which is the normal state of a window nobody is compositing,
i.e. every automated screenshot run. So when the paintable comes back empty the
tree is snapshot directly, which always has an answer.

The panel is photographed against a **made-up household**, not the machine's
own config: two children with different colours and shapes, a weekday window
and a weekend one, someone in the family list. A screenshot of a fresh install
is one child called "Me" and shows nothing the tabs are for.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import (  # noqa: E402
    catalogue,
    config_io,
    system,
)
from . import model as M  # noqa: E402

log = logging.getLogger(__name__)

#: Long enough for Broadway to have laid the window out at least once.
FIRST_FRAME_MS = 1500
#: Between tabs. A ViewStack switch is a crossfade; capturing mid-fade gives a
#: ghost of the previous tab.
BETWEEN_MS = 1200

SHOTS = ("children", "time", "activities", "sound", "things", "family", "updates")


def demo_state(activities: Path):
    """A household worth photographing, and a runner that forks nothing."""
    from .ui.state import PanelState

    panel = M.PanelModel()
    rosie = panel.add_child("Rosie", age_band="4-5")
    sam = panel.add_child("Sam", age_band="6-8")
    panel.update_child(sam.id, allowed_activity_ids=("tuxpaint", "gcompris", "blinken", "kolf"))
    panel.time = replace(
        panel.time,
        length_minutes=25,
        daily_budget_minutes=60,
        windows=(
            M.ScheduleWindow(days=M.WEEKDAYS, start="15:30", end="18:00", label="After school"),
            M.ScheduleWindow(days=M.WEEKEND, start="09:30", end="18:00", label="Weekends"),
        ),
    )
    panel.add_recipient("Granny", relation="Rosie's grandmother")
    _ = rosie

    def runner(argv, stdin=None, timeout=0):
        return system.Completed(1, "", "not run in a screenshot")

    return PanelState(
        panel=panel,
        activities=catalogue.load(activities),
        runner=runner,
        etc=config_io.ETC,
        usr=config_io.USR,
        synchronous=True,
    )


def capture(window: Gtk.Widget, path: Path) -> bool:
    """Write ``window`` to ``path`` as a PNG. Never raises."""
    try:
        width = window.get_width() or 1000
        height = window.get_height() or 760
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
    except Exception as exc:
        log.warning("could not capture %s: %s", path, exc)
        return False


def run_screenshots(out: Path, etc: Path, usr: Path, activities: Path) -> int:
    """Open the window, walk the tabs, photograph each, quit."""
    from .ui.app import ParentPanelApplication

    _ = (etc, usr)
    state = demo_state(activities)
    app = ParentPanelApplication(state)
    written: list[Path] = []

    def on_activate(_app: Adw.Application) -> None:
        window = app.window
        assert window is not None
        queue = list(SHOTS)

        def shoot() -> bool:
            if not queue:
                app.quit()
                return GLib.SOURCE_REMOVE
            name = queue.pop(0)
            window.stack.set_visible_child_name(name)
            path = out / f"parent-panel-{name}.png"

            def later() -> bool:
                if capture(window, path):
                    written.append(path)
                GLib.timeout_add(50, shoot)
                return GLib.SOURCE_REMOVE

            GLib.timeout_add(BETWEEN_MS, later)
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(FIRST_FRAME_MS, shoot)

    # connect_after: "activate" is RUN_LAST, so a plain connect() runs BEFORE
    # Adw.Application's own default handler -- i.e. before the window exists.
    app.connect_after("activate", on_activate)
    app.run([])
    for path in written:
        print(f"==> {path}")
    return 0 if written else 1


__all__ = ["BETWEEN_MS", "FIRST_FRAME_MS", "SHOTS", "capture", "demo_state", "run_screenshots"]
