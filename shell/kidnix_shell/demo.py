"""``--demo``: fake activities and a three-minute session.

The whole ritual -- launch, make something, keep it, ending offer, put away,
goodbye, sleeping -- in about three minutes, with no GCompris, no Tux Paint and
no image. That makes the shell demonstrable on a laptop and exercisable in CI.

The fake activity is a tiny scribble window: click and drag to draw, it
autosaves a PNG into its watch directory every few seconds, and the shell's
Journal picks it up exactly as it would a real one.

This module is also run *as a script* by the launcher (``python demo.py
--play ...``), so everything the play mode needs is imported inside the
functions or at the top without relative imports.
"""

from __future__ import annotations

import argparse
import logging
import math
import random
import signal
import sys
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CANVAS_W = 800
CANVAS_H = 600
AUTOSAVE_MS = 4000

#: (id, name, audio label, colour, category, resumable)
DEMO_ACTIVITIES: tuple[tuple[str, str, str, str, str, bool], ...] = (
    ("scribble", "Scribble", "Scribble. Draw with the mouse.", "#0f8a8a", "make", True),
    ("splodge", "Splodge", "Splodge. Make big blobs of colour.", "#f06292", "make", True),
    ("stamps", "Stamps", "Stamps. Print shapes on the page.", "#f9a825", "make", True),
    (
        "letters",
        "Letters",
        "Letters. Find the letter that makes the sound.",
        "#4527a0",
        "learn",
        False,
    ),
    ("counting", "Counting", "Counting. How many are there?", "#2e7d32", "learn", False),
    ("shapes", "Shapes", "Shapes. Match the shape to its hole.", "#bf360c", "learn", False),
    ("library", "Library", "Library. Look things up.", "#37474f", "learn", False),
    ("bounce", "Bounce", "Bounce. Keep the ball in the air.", "#26c6da", "play", False),
    ("maze", "Maze", "Maze. Find the way out.", "#7b1fa2", "play", False),
    ("memory", "Memory", "Memory. Remember where they are.", "#00838f", "play", False),
    ("music", "Music", "Music. Play a tune.", "#e64a19", "make", True),
    ("photos", "Photos", "Photos. Take a picture.", "#5d4037", "make", True),
    ("sticky", "Sticky", "Sticky. This one is slow to put away.", "#455a64", "play", False),
    ("notyet", "Not ready", "Not ready.", "#6a1b9a", "make", False),
)

#: Not in the parent's allow-list, so Home renders it outline-only (spec S2).
NOT_ALLOWED = {"sticky"}

#: Declares ``content_required`` against a directory the demo leaves empty, so
#: a demo run exercises the predicate that hides the real Library until a
#: parent has put a ZIM on the machine (05 Lib-4). Its tile is simply absent.
NEEDS_CONTENT = {"library"}

#: Banded above the demo profile's ``age_band`` ("4-5"), so a demo run also
#: shows the age filter: no tile, no outline, nothing to ask about (01 #35).
TOO_OLD = {"maze"}

#: Points at a program that does not exist, and asks to be shown anyway --
#: the ``show_when_unavailable`` path, so a demo run exercises the
#: "This one isn't ready yet" tile as well as the not-allowed one.
NOT_INSTALLED = {"notyet"}

#: "Sticky" ignores SIGTERM and its manifest says ``quit = "confirm"``, so a
#: --demo run exercises the whole of spec 7c's put-away conversation -- the
#: ask, the wait with the band stripped back, the one re-ask at the end of the
#: grace, and finally the hard stop's SIGKILL -- rather than only the happy
#: path. It is the demo's stand-in for Tux Paint's tick.
STUBBORN = {"sticky"}

#: The demo session is three minutes and put away is twenty seconds before the
#: end (`SessionPolicy.demo`), so the grace has to be short enough that the
#: re-ask happens on screen and the kill still lands at the hard stop.
STUBBORN_GRACE_SECONDS = 8

#: The demo's stand-in for the GCompris shelf (spec 7d #12), so ``--demo`` shows
#: the second level of Home on a laptop with no GCompris on it. Same data shape
#: as the real one -- ``kind = "shelf"``, a ``children_dir`` beside the
#: manifest, children carrying ``shelf_group*`` -- so the demo exercises the
#: real loader rather than a mock of it.
DEMO_SHELF_ID = "shelfy"
DEMO_SHELF_NAME = "Letters & numbers"
DEMO_SHELF_DIR = "shelfy"

#: ``(id, title, group id, group name)``, in shelf order. Two groups of three,
#: which is the real shelf's shape at a third of the size: enough to show a
#: heading, a page turn and a spoken group name.
DEMO_SHELF_CHILDREN: tuple[tuple[str, str, str, str], ...] = (
    ("shelfy.aa", "Find the A", "letters", "Letters"),
    ("shelfy.bb", "Big and small", "letters", "Letters"),
    ("shelfy.cc", "Name the letter", "letters", "Letters"),
    ("shelfy.dots", "Dice dots", "counting", "Counting"),
    ("shelfy.more", "Which has more?", "counting", "Counting"),
    ("shelfy.order", "Put them in order", "counting", "Counting"),
)


# --- building the demo world (used by the shell) -------------------------


def build_demo_world(root: Path | None = None) -> tuple[Path, list[Any], list[str]]:
    """Write demo manifests under ``root`` and load them with the real loader.

    Returns ``(root, activities, allowed_ids)``. Using the real loader means
    ``--demo`` also smoke-tests manifest parsing on every run.
    """
    from .activities import load_directory, resolve_availability

    base = root or Path(tempfile.mkdtemp(prefix="kidnix-demo-"))
    manifests = base / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)

    script = Path(__file__).resolve()
    for index, (activity_id, name, audio, colour, category, resumable) in enumerate(
        DEMO_ACTIVITIES
    ):
        watch = base / "work" / activity_id
        watch.mkdir(parents=True, exist_ok=True)
        argv = [
            sys.executable,
            str(script),
            "--play",
            "--name",
            name,
            "--colour",
            colour,
            "--out",
            str(watch),
        ]
        if activity_id in STUBBORN:
            argv.append("--stubborn")
        if activity_id in NOT_INSTALLED:
            argv = [str(base / "nothing-here" / activity_id)]
        lines = [
            "schema = 1",
            f'id = "{activity_id}"',
            f'name = "{name}"',
            f'audio_label = "{audio}"',
            f'icon = "kidnix-{category}"',
            'icon_kind = "icon-name"',
            "exec = [" + ", ".join(f'"{a}"' for a in argv) + "]",
            f'category = "{category}"',
            # The demo grid is in the order the list above is written, which is
            # also how the shipped manifests do it (spec section 4, `order`).
            f"order = {(index + 1) * 10}",
            # The demo profile is banded "4-5"; TOO_OLD overrides this below.
            'age_band = "4-6"',
            "network_required = false",
            f'journal_watch = ["{watch}"]',
            'journal_glob = "*.png"',
            f'goal = "A fake activity for demonstrating the shell ({category})."',
        ]
        if activity_id in STUBBORN:
            lines.append('quit = "confirm"')
            lines.append(f"quit_grace = {STUBBORN_GRACE_SECONDS}")
        if activity_id in NEEDS_CONTENT:
            empty = base / "content" / activity_id
            empty.mkdir(parents=True, exist_ok=True)
            lines.append(f'content_required = ["{empty}/*.zim"]')
        if activity_id in TOO_OLD:
            lines[lines.index('age_band = "4-6"')] = 'age_band = "7-10"'
        if activity_id in NOT_INSTALLED:
            lines.append("show_when_unavailable = true")
        if resumable:
            resume = [*argv, "--open", "{file}"]
            lines.append("exec_resume = [" + ", ".join(f'"{a}"' for a in resume) + "]")
        (manifests / f"{activity_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    _write_demo_shelf(base, manifests, script)

    result = load_directory(manifests, home=base)
    for error in result.errors:
        log.error("demo manifest is broken: %s", error)
    activities = resolve_availability(sorted(result.activities, key=lambda a: a.sort_key))
    allowed = [a.id for a in activities if a.id not in NOT_ALLOWED]
    return base, activities, allowed


def _write_demo_shelf(base: Path, manifests: Path, script: Path) -> None:
    """A shelf tile and its children, in the shape the image actually ships.

    The children go in a **subdirectory** for the same reason the real ones do:
    ``load_directory`` globs one directory and does not recurse, so six extra
    tiles cannot leak onto Home. A demo that put them beside the others would
    prove the opposite of what it is for.
    """
    children_dir = manifests / DEMO_SHELF_DIR
    children_dir.mkdir(parents=True, exist_ok=True)
    watch = base / "work" / DEMO_SHELF_ID
    watch.mkdir(parents=True, exist_ok=True)

    def argv(name: str, colour: str) -> list[str]:
        return [
            sys.executable,
            str(script),
            "--play",
            "--name",
            name,
            "--colour",
            colour,
            "--out",
            str(watch),
        ]

    shelf = [
        "schema = 1",
        f'id = "{DEMO_SHELF_ID}"',
        f'name = "{DEMO_SHELF_NAME}"',
        'audio_label = "Letters, counting and shapes. Choose a game."',
        'icon = "kidnix-learn"',
        'icon_kind = "icon-name"',
        'kind = "shelf"',
        f'children_dir = "{DEMO_SHELF_DIR}"',
        # The fallback exec, which a shell that renders shelves never runs. It
        # is the first child rather than anything menu-shaped, exactly as the
        # real gcompris.toml's is (panel-wave-c section 2).
        "exec = [" + ", ".join(f'"{a}"' for a in argv("Find the A", "#4527a0")) + "]",
        'category = "learn"',
        "order = 35",
        'age_band = "4-8"',
        "network_required = false",
        "journal_watch = []",
        'goal = "A pretend shelf, for demonstrating the second level of Home."',
    ]
    (manifests / f"{DEMO_SHELF_ID}.toml").write_text("\n".join(shelf) + "\n", encoding="utf-8")

    for index, (child_id, title, group, group_name) in enumerate(DEMO_SHELF_CHILDREN):
        lines = [
            "schema = 1",
            f'id = "{child_id}"',
            f'name = "{title}"',
            f'audio_label = "{title}. A pretend game."',
            'icon = "kidnix-learn"',
            'icon_kind = "icon-name"',
            f"order = {(index + 1) * 10}",
            "exec = [" + ", ".join(f'"{a}"' for a in argv(title, "#4527a0")) + "]",
            'category = "learn"',
            'age_band = "4-8"',
            "network_required = false",
            f'journal_watch = ["{watch}"]',
            'journal_glob = "*.png"',
            f'goal = "A pretend shelf child ({group_name})."',
            f'shelf_group = "{group}"',
            f'shelf_group_name = "{group_name}"',
            f'shelf_group_audio_label = "{group_name}"',
        ]
        (children_dir / f"{child_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- the fake activity itself (run as a subprocess) ----------------------


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def play(name: str, colour: str, out_dir: Path, open_file: Path | None, stubborn: bool) -> int:
    """A tiny scribble window that keeps saving PNGs where the shell can see."""
    import cairo
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib, Gtk

    if stubborn:
        # Deliberately rude: refuses the polite request to quit, so Put away has
        # to escalate. See the implementation notes.
        signal.signal(signal.SIGTERM, lambda *_a: log.warning("%s ignoring SIGTERM", name))

    out_dir.mkdir(parents=True, exist_ok=True)
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, CANVAS_W, CANVAS_H)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(0.98, 0.97, 0.94)
    ctx.paint()

    if open_file is not None and open_file.is_file():
        try:
            existing = cairo.ImageSurface.create_from_png(str(open_file))
            ctx.set_source_surface(existing, 0, 0)
            ctx.paint()
            log.info("%s resumed %s", name, open_file)
        except Exception as exc:
            log.warning("could not resume %s: %s", open_file, exc)

    red, green, blue = _hex_to_rgb(colour)
    state = {"dirty": open_file is None, "strokes": 0}
    target = out_dir / (open_file.name if open_file else f"{name.lower()}.png")

    def blob(x: float, y: float) -> None:
        ctx.set_source_rgb(
            min(1.0, red + random.uniform(-0.15, 0.15)),
            min(1.0, green + random.uniform(-0.15, 0.15)),
            min(1.0, blue + random.uniform(-0.15, 0.15)),
        )
        ctx.arc(x, y, 18, 0, 2 * math.pi)
        ctx.fill()
        state["dirty"] = True
        state["strokes"] += 1

    # Something is on the canvas from the first frame, so the demo produces a
    # journal entry even if nobody draws.
    for step in range(14):
        blob(120 + step * 44, 300 + math.sin(step / 2) * 110)

    area = Gtk.DrawingArea()
    area.set_hexpand(True)
    area.set_vexpand(True)

    def draw(_a: Gtk.DrawingArea, cr: Any, width: int, height: int) -> None:
        cr.save()
        cr.scale(width / CANVAS_W, height / CANVAS_H)
        cr.set_source_surface(surface, 0, 0)
        cr.paint()
        cr.restore()

    area.set_draw_func(draw)

    def canvas_xy(x: float, y: float) -> tuple[float, float]:
        width = max(1, area.get_width())
        height = max(1, area.get_height())
        return x * CANVAS_W / width, y * CANVAS_H / height

    click = Gtk.GestureClick.new()
    click.set_button(0)

    def on_pressed(_g: Any, _n: int, x: float, y: float) -> None:
        blob(*canvas_xy(x, y))
        area.queue_draw()

    click.connect("pressed", on_pressed)
    area.add_controller(click)

    drag = Gtk.GestureDrag.new()

    def on_drag(gesture: Any, dx: float, dy: float) -> None:
        _, start_x, start_y = gesture.get_start_point()
        blob(*canvas_xy((start_x or 0) + dx, (start_y or 0) + dy))
        area.queue_draw()

    drag.connect("drag-update", on_drag)
    area.add_controller(drag)

    def save() -> None:
        if not state["dirty"]:
            return
        surface.flush()
        surface.write_to_png(str(target))
        state["dirty"] = False
        log.info("%s saved %s", name, target)

    def autosave() -> bool:
        save()
        return True

    application = Gtk.Application(application_id=f"org.kidnix.demo.{name.lower()}")

    def activate(app: Gtk.Application) -> None:
        window = Gtk.ApplicationWindow(application=app, title=name)
        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label=f"{name} (a pretend activity)"))
        done = Gtk.Button(label="I'm done")

        def on_done(_button: Any) -> None:
            save()
            window.close()

        done.connect("clicked", on_done)
        header.pack_end(done)
        window.set_titlebar(header)
        window.set_child(area)
        window.set_default_size(1000, 700)

        def on_close(_w: Any) -> bool:
            save()
            return False

        window.connect("close-request", on_close)
        window.present()
        GLib.timeout_add(AUTOSAVE_MS, autosave)

    application.connect("activate", activate)
    code = application.run([])
    save()
    return int(code)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="kidnix demo activity")
    parser.add_argument("--play", action="store_true", help="run the fake activity")
    parser.add_argument("--name", default="Scribble")
    parser.add_argument("--colour", default="#0f8a8a")
    parser.add_argument("--out", type=Path, default=Path.cwd())
    parser.add_argument("--open", type=Path, default=None, help="resume this file")
    parser.add_argument("--stubborn", action="store_true", help="ignore SIGTERM")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr
    )
    if not args.play:
        parser.error("this module only runs fake activities; use kidnix-shell --demo")
    return play(args.name, args.colour, args.out, args.open, args.stubborn)


if __name__ == "__main__":
    raise SystemExit(main())


# --- a session that already made something (development) -----------------


#: The palette a seeded drawing uses. Five, because SYNTHESIS E1's own example
#: sentence is "you used five colours" and the Goodbye screen now computes that
#: number from the pictures themselves (:mod:`kidnix_shell.feedback`).
SEED_COLOURS = ("#d64545", "#2e7d32", "#1e5aa8", "#f2a53a", "#7b3fa0")


def seed_work(activities: list[Any], drawings: int = 2) -> list[Path]:
    """Write a couple of finished drawings where the Journal will find them.

    Development only, and only for ``--start-on goodbye``: the ending screen's
    whole hierarchy is "the destination, then what was made", and a screenshot
    of it with nothing made shows half the screen. The shapes are deliberately
    a handful of flat colours so the colour count in E1's line is a real
    measurement of a real file rather than a number typed into a demo.
    """
    import cairo

    written: list[Path] = []
    makers = [a for a in activities if a.journal_watch and a.category == "make"]
    for index in range(drawings):
        if not makers:
            break
        activity = makers[index % len(makers)]
        out = Path(activity.journal_watch[0])
        out.mkdir(parents=True, exist_ok=True)
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, CANVAS_W, CANVAS_H)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(0.99, 0.98, 0.96)
        ctx.paint()
        for step, colour in enumerate(SEED_COLOURS):
            red, green, blue = _hex_to_rgb(colour)
            ctx.set_source_rgb(red, green, blue)
            ctx.arc(
                CANVAS_W * (0.2 + 0.15 * step),
                CANVAS_H * (0.35 + 0.18 * ((step + index) % 3)),
                CANVAS_H * 0.12,
                0,
                2 * math.pi,
            )
            ctx.fill()
        target = out / f"seeded-{index}.png"
        surface.write_to_png(str(target))
        written.append(target)
        log.info("demo: seeded %s", target)
    return written
