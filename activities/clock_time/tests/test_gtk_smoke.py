"""The window, under Broadway, on a machine that has one.

**Never on the developer's desktop.** The SDK says so
(``docs/design/activity-sdk.md`` section 10) and this module enforces it: it
starts its own ``gtk4-broadwayd`` on a private display, points GDK at it before
GTK is initialised, and skips the whole file if the daemon is not there or will
not come up. An activity that opened a window on the machine you are working on
is an activity somebody will eventually ship a screenshot of with their own
wallpaper behind it.

Headless tests are the floor and these are the ceiling: everything worth
proving is in the pure modules and is asserted without a display. What is here
is the wiring -- that the tree builds, that the rim targets exist and are
named, that they land where the drawing puts the marks, and that the two
screens can be built and rebuilt without taking the ring with them.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from datetime import datetime

import pytest

from conftest import HAVE_SDK

pytestmark = pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")

#: A display number nothing else is likely to be on. Broadway listens on
#: 8080 + N, which is why the port is what gets probed below.
DISPLAY = 117
PORT = 8080 + DISPLAY


def _listening() -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex(("127.0.0.1", PORT)) == 0


@pytest.fixture(scope="session")
def broadway():
    """One daemon for the whole run, torn down after it."""
    binary = shutil.which("gtk4-broadwayd")
    if binary is None:
        pytest.skip("gtk4-broadwayd is not installed")
    process = subprocess.Popen(
        [binary, f":{DISPLAY}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(50):
        if _listening():
            break
        time.sleep(0.1)
    else:  # pragma: no cover - a machine where broadwayd will not start
        process.terminate()
        pytest.skip("gtk4-broadwayd did not come up")
    os.environ["GDK_BACKEND"] = "broadway"
    os.environ["BROADWAY_DISPLAY"] = f":{DISPLAY}"
    yield f":{DISPLAY}"
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
def gtk(broadway):
    """GTK, initialised against that display, or a skip."""
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    if not Gtk.init_check():  # pragma: no cover - a display that will not open
        pytest.skip("GTK would not initialise against Broadway")
    return Gtk


@pytest.fixture
def area(gtk):
    from kidnix_activity.metrics import ContentArea

    return ContentArea.detect()


# --- the face ---------------------------------------------------------------


def test_the_face_builds_with_a_target_for_every_taught_position(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import Mode, grid_for

    for mode in Mode:
        face = ClockFace(area, mode, on_move=lambda _clock: None)
        assert [minute for minute, _button in face.targets] == list(grid_for(mode))


def test_year_one_has_two_targets_and_year_two_has_twelve(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import Mode

    assert len(ClockFace(area, Mode.Y1, on_move=lambda _c: None).targets) == 2
    assert len(ClockFace(area, Mode.Y2, on_move=lambda _c: None).targets) == 12


def test_every_target_is_named_by_its_position_and_says_so(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import Mode

    face = ClockFace(area, Mode.Y2, on_move=lambda _c: None)
    names = {button.speak_text for _minute, button in face.targets}
    assert "o'clock" in names
    assert "half past" in names
    assert "quarter past" in names
    assert "quarter to" in names
    assert not any(any(character.isdigit() for character in name) for name in names)


def test_every_target_is_at_least_the_twenty_millimetre_floor(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import Mode

    face = ClockFace(area, Mode.Y2, on_move=lambda _c: None)
    for _minute, button in face.targets:
        width, height = button.get_size_request()
        assert width >= area.min_target
        assert height >= area.min_target


def test_resizing_puts_each_target_somewhere_of_its_own(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import Mode

    face = ClockFace(area, Mode.Y2, on_move=lambda _c: None)
    face._on_resize(face.dial, 600, 600)
    positions = set()
    for _minute, button in face.targets:
        # Read back through the transform rather than `get_child_position`,
        # whose PyGObject binding hands back (0, 0) for every child however it
        # was placed. Measured on GTK 4 / PyGObject 3.5x under Broadway; the
        # transform is the same number and it is the one that is true.
        dx, dy = face.marks.get_child_transform(button).to_translate()
        positions.add((round(dx), round(dy)))
    assert len(positions) == 12


def test_the_targets_sit_on_a_circle_around_the_middle_of_the_face(gtk, area):
    """They are over the marks the drawing puts there, so a child aiming at
    the numeral hits the target and vice versa."""
    import math

    from clock_time.activity import RIM_FRACTION, ClockFace
    from clock_time.words import Mode

    face = ClockFace(area, Mode.Y2, on_move=lambda _c: None)
    face._on_resize(face.dial, 600, 600)
    size = area.min_target
    expected = 600 / 2.0 * 0.92 * RIM_FRACTION
    for _minute, button in face.targets:
        dx, dy = face.marks.get_child_transform(button).to_translate()
        centre = (dx + size / 2.0 - 300.0, dy + size / 2.0 - 300.0)
        assert math.hypot(*centre) == pytest.approx(expected, abs=1.0)


def test_pressing_a_target_moves_the_hands_and_reports_it(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import ClockTime, Mode

    moved: list[ClockTime] = []
    face = ClockFace(area, Mode.Y1, on_move=moved.append)
    half_past = next(button for minute, button in face.targets if minute == 30)
    half_past.fire()
    assert moved == [ClockTime.of(3, 30)]


def test_pressing_the_target_the_hands_are_already_on_reports_nothing(gtk, area):
    from clock_time.activity import ClockFace
    from clock_time.words import Mode

    moved = []
    face = ClockFace(area, Mode.Y1, on_move=moved.append)
    o_clock = next(button for minute, button in face.targets if minute == 0)
    o_clock.fire()
    assert moved == []


# --- the disc ---------------------------------------------------------------


def test_the_disc_builds_and_remembers_its_phase(gtk, area):
    from clock_time.activity import Disc
    from clock_time.minute import Phase

    disc = Disc(area)
    disc.set_state(Phase.SHOWING, 0.5)
    assert disc.phase is Phase.SHOWING
    assert disc.fraction == 0.5
    disc.set_state(Phase.RESULT, 9.0)
    assert disc.fraction == 1.0


# --- both screens, in a real application ------------------------------------


@pytest.fixture
def running(gtk, tmp_path):
    """One activity, built into a real window, with the loop pumped once."""
    from gi.repository import GLib
    from kidnix_activity.app import ActivityApplication

    from clock_time import ACTIVITY_ID, TITLE
    from clock_time.activity import ClockActivity

    app = ActivityApplication(ACTIVITY_ID, TITLE, env={})
    activity = ClockActivity(
        app,
        clock=lambda: datetime(2026, 8, 23, 15, 32),
        scratch=tmp_path,
    )
    app.set_build(activity.build)
    app.set_on_finish(lambda: None)
    GLib.idle_add(app.quit)
    app.run(["kidnix-clock-time"])
    return activity


def test_the_clock_screen_builds(running):
    assert running.face is not None
    assert running.prompt is not None
    assert len(running.tiles) == 8


def test_the_sky_behind_the_clock_follows_the_time_of_day(running):
    """The second, redundant channel for "when" (SYNTHESIS B6): the prompt says
    it, the highlight shows it and the sky is doing it. There is no separate
    scene card, because a fourth copy is clutter rather than emphasis."""
    from clock_time.routine import Sky
    from clock_time.words import ClockTime

    running.set_time(ClockTime.of(9, 0))
    assert running.face.sky is running.sky
    morning = running.face.sky
    running.set_time(ClockTime.of(7, 30))
    assert running.face.sky is running.sky
    assert {morning, running.face.sky} <= set(Sky)


def test_the_prompt_carries_the_whole_sentence(running):
    """"Half past three. Home is at half past three." One line, spoken and
    written, and no digit in it."""
    from clock_time.words import ClockTime

    running.set_time(ClockTime.of(3, 30))
    assert running.time.words() in running.prompt.text
    assert running.item.sentence in running.prompt.text
    assert not any(character.isdigit() for character in running.prompt.text)


def test_the_face_takes_sixty_percent_of_the_height_or_all_that_is_left(running):
    """The brief gives the face 60%. On a panel too short for that plus a
    prompt and a routine strip it yields rather than overflowing, because what
    falls off the bottom of an over-tall window is the routine strip -- the
    half of this activity that is not a clock."""
    from clock_time.activity import FACE_HEIGHT_FRACTION

    area = running.window.area
    _width, height = running.face.get_size_request()
    assert height > 0
    if not area.known:
        return
    wanted = int(area.height * FACE_HEIGHT_FRACTION)
    assert height <= wanted
    assert height >= area.min_target * 3


@pytest.mark.parametrize("screen", ["clock", "minute"])
def test_neither_screen_is_taller_than_the_rectangle_below_the_band(running, screen):
    """The bug this replaces: the first version of the clock screen wanted
    1074 x 890 px in a 1024 x 618 rectangle, and under gnome-kiosk what falls
    off the bottom is the routine strip -- the half of this activity that is
    not a clock. GTK will not go under a widget's *minimum*, so the minimum of
    the whole tree is what has to fit, in both directions."""
    from gi.repository import Gtk

    area = running.window.area
    if not area.known:
        return
    if screen == "minute":
        running.build_minute(running.window)
    wide, _natural, _mb, _nb = running.window.content.measure(
        Gtk.Orientation.HORIZONTAL, -1
    )
    assert wide <= area.width
    minimum, _natural, _mb, _nb = running.window.content.measure(
        Gtk.Orientation.VERTICAL, area.width
    )
    assert minimum <= area.height


def test_the_face_is_the_biggest_thing_on_the_screen(running):
    _width, face = running.face.get_size_request()
    assert face > running.window.area.big_button
    for tile in running.tiles.values():
        assert face > tile.get_size_request()[1]


def test_the_grown_ups_card_is_one_press_away_on_the_minute_screen(running):
    """SUITE section 3's co-use moment. It is not on the clock screen because
    four rows do not fit below the band; it names both screens instead."""
    from kidnix_activity.widgets import GrownUpTurn

    from clock_time.activity import GROWNUP_BODY

    def cards(widget):
        found = []
        child = widget.get_first_child()
        while child is not None:
            if isinstance(child, GrownUpTurn):
                found.append(child)
            child = child.get_next_sibling()
        return found

    assert cards(running.window.content) == []
    running.build_minute(running.window)
    assert len(cards(running.window.content)) == 1
    assert "clock" in GROWNUP_BODY
    assert "minute" in GROWNUP_BODY


def test_the_current_moment_is_the_only_one_highlighted(running):
    running.set_time(running.time)
    current = [key for key, tile in running.tiles.items() if tile.has_css_class("current")]
    assert current == [running.item.id]


def test_moving_the_hands_moves_the_highlight(running):
    """Half past three in the afternoon is home time. The hands and the
    highlight are one fact, so moving one moves the other."""
    from clock_time.words import ClockTime, Mode

    running.set_time(ClockTime.of(12, 0).snapped(Mode.Y1))
    assert running.item.id == "lunch"
    assert running.tiles["lunch"].has_css_class("current")
    assert not running.tiles["tea"].has_css_class("current")


def test_seven_o_clock_at_half_past_three_in_the_afternoon_is_bedtime(running):
    """The room resolves the dial: at half past three, seven o'clock is four
    hours ahead and eight hours behind, so it means the evening one."""
    from clock_time.words import ClockTime

    running.set_time(ClockTime.of(7, 30))
    assert running.item.id == "bed"


def test_now_puts_the_hands_on_the_real_time(running):
    from clock_time.words import ClockTime

    running.jump_to_now()
    assert running.time == ClockTime.of(3, 32)


def test_the_arrow_keys_step_the_hands(running):
    from clock_time.keys import Action
    from clock_time.words import ClockTime

    running.set_time(ClockTime.of(3, 0))
    running.do_action(Action.MINUTE_FORWARD)
    assert running.time == ClockTime.of(3, 30)
    running.do_action(Action.MINUTE_BACK)
    assert running.time == ClockTime.of(3, 0)


def test_the_minute_screen_builds_and_can_go_back(running):
    from clock_time.keys import Screen

    running.build_minute(running.window)
    assert running.screen is Screen.MINUTE
    assert running.disc is not None
    assert running.face is None
    running.build_clock(running.window)
    assert running.screen is Screen.CLOCK
    assert running.face is not None
    assert running.disc is None


def _big_buttons(widget):
    """Every :class:`BigButton` under ``widget``, in tree order.

    A ``Prompt``'s replay control and the routine tiles are deliberately not
    among them: they are a ``ChildButton`` and a ``PictureTile``, and both
    already carry a picture.
    """
    from kidnix_activity.widgets import BigButton

    def walk(node):
        yield node
        child = node.get_first_child()
        while child is not None:
            yield from walk(child)
            child = child.get_next_sibling()

    return [node for node in walk(widget) if isinstance(node, BigButton)]


def test_every_control_on_the_minute_screen_has_a_picture_a_word_and_a_sentence(running):
    """**The regression.** On 2026-08-23 this screen carried six controls and
    five of them were a word and nothing else -- on the screen of an activity
    written for a child who cannot read one (the CCI audit's ruling 4).
    SYNTHESIS B3 asks every control for all three channels."""
    running.build_minute(running.window)
    buttons = _big_buttons(running.window.content)
    assert len(buttons) == 6
    for button in buttons:
        assert button.icon_image is not None
        assert button.label is not None
        assert button.label.get_label().strip()
        assert button.speak_text.strip()
        assert not any(character.isdigit() for character in button.speak_text)


def test_the_start_button_becomes_the_stop_button_in_all_three_channels(running):
    """One control, two meanings. Until the pictures existed only the *ear*
    knew: the word still said "Start" while the sentence said "Stop"."""
    from clock_time.icons import icon_for
    from clock_time.minute import Phase

    running.build_minute(running.window)
    assert running.go.label.get_label() == "Start"
    assert "Start" in running.go.speak_text

    running.start_or_stop()
    assert running.phase is Phase.GUESSING
    assert running.go.label.get_label() == "Stop"
    assert running.go.speak_text.startswith("Stop")

    running.start_or_stop()
    assert running.phase is Phase.RESULT
    assert running.go.label.get_label() == "Start"
    assert "Start" in running.go.speak_text
    assert icon_for("start") and icon_for("stop")


@pytest.mark.parametrize("leave", ["watch", "choose"])
def test_every_way_out_of_a_guess_puts_the_button_back(running, leave):
    """A child who starts a guess and then asks to watch one instead, or
    picks a different interval, must not be left holding a button that says
    Stop when there is nothing running."""
    from clock_time.minute import Length

    running.build_minute(running.window)
    running.start_or_stop()
    assert running.go.label.get_label() == "Stop"
    if leave == "watch":
        running.watch()
    else:
        running.choose(Length.TWO_MINUTES)
    running._stop_ticking()
    assert running.go.label.get_label() == "Start"
    assert "Start" in running.go.speak_text


def test_each_interval_carries_its_own_drawing(running):
    """Three discs, one bigger than the last, and never a digit -- the
    picture is the only thing on the screen that says how long "Two" is."""
    from clock_time.icons import length_icon
    from clock_time.minute import LENGTHS

    running.build_minute(running.window)
    assert len({length_icon(length) for length in LENGTHS}) == len(LENGTHS)
    labels = {button.label.get_label() for button in _big_buttons(running.window.content)}
    assert {length.label for length in LENGTHS} <= labels


def test_starting_and_stopping_gives_a_verdict_without_a_number(running):
    from clock_time.minute import Length, Phase

    running.build_minute(running.window)
    running.choose(Length.HALF_MINUTE)
    running.start_or_stop()
    assert running.phase is Phase.GUESSING
    running.start_or_stop()
    assert running.phase is Phase.RESULT
    assert not any(character.isdigit() for character in running.prompt.text)


def test_the_ring_holds_every_control_on_both_screens(running):
    from kidnix_activity.keyboard import focusables

    on_clock = focusables(running.window.content)
    assert len(on_clock) >= 8
    running.build_minute(running.window)
    on_minute = focusables(running.window.content)
    assert len(on_minute) >= 6
    assert not set(on_clock) & set(on_minute)


def test_finishing_without_playing_keeps_nothing(running, tmp_path):
    """A card in My Things saying "half past three" for a session in which
    nobody touched anything is a claim about a person that is not true."""
    running.played = False
    running.finish()
    assert not list(tmp_path.glob("*.png"))


def test_finishing_after_playing_keeps_the_clock_they_made(gtk, tmp_path):
    """The end-to-end the SDK asks every activity for: launch, make one thing,
    find it in My Things."""
    import json

    from gi.repository import GLib
    from kidnix_activity.app import ActivityApplication

    from clock_time import ACTIVITY_ID, TITLE
    from clock_time.activity import ClockActivity
    from clock_time.words import ClockTime

    home = tmp_path / "home"
    env = {
        "HOME": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "KIDNIX_ACTIVITY_ID": ACTIVITY_ID,
        "KIDNIX_PROFILE_ID": "sam",
    }
    app = ActivityApplication(ACTIVITY_ID, TITLE, env=env)
    activity = ClockActivity(
        app, clock=lambda: datetime(2026, 8, 23, 15, 32), scratch=tmp_path / "scratch"
    )
    app.set_build(activity.build)
    GLib.idle_add(app.quit)
    app.run(["kidnix-clock-time"])

    activity.set_time(ClockTime.of(3, 30))
    activity.finish()

    entries = sorted(
        (home / ".local" / "share" / "kidnix" / "profiles" / "sam" / "journal").glob(
            "*/*/*/*/entry.json"
        )
    )
    assert len(entries) == 1
    written = json.loads(entries[0].read_text())
    # A short caption becomes the entry's title, which is what My Things reads
    # aloud -- and it is words, never digits (01 #19).
    assert written["title"] == "Half past three"
    assert written["activity_id"] == ACTIVITY_ID
    assert not any(character.isdigit() for character in written["title"])
    assert (entries[0].parent / "caption.txt").read_text().strip() == "Half past three"
    # The activity's own `meta` is nested under "meta": entry.json is written
    # by the shell's own dataclass and would drop any key we added to it
    # (docs/design/activity-sdk.md section 8).
    document = json.loads((entries[0].parent / "meta.json").read_text())
    assert document["kind"] == "picture"
    assert document["meta"]["time"] == "half past three"
    assert document["meta"]["routine"] == "home"
    assert document["meta"]["mode"] == "y1"
    assert (entries[0].parent / "v001.png").is_file()
    # And the routine's own drawing goes in beside it, so the card in My Things
    # is a record of *what happens when* and not only of a dial.
    assert (entries[0].parent / "v002.svg").is_file()


# --- the routine strip's words, measured by the engine that draws them -------


def _tile_label(tile):
    """The Gtk.Label inside a routine tile, and what is actually set on it."""
    from gi.repository import Gtk

    def walk(widget):
        yield widget
        child = widget.get_first_child()
        while child is not None:
            yield from walk(child)
            child = child.get_next_sibling()

    return next(w for w in walk(tile) if isinstance(w, Gtk.Label))


def test_no_routine_name_is_ever_cut(running):
    """**The regression.** ``docs/design/screenshots/clock-play.png`` on
    2026-08-23 said "Brea-kfast" and "Scho-ol": the tiles were sized from the
    count and the names were asked to fit whatever that left, so Pango broke
    the words between characters and drew a hyphen where it did.

    A pre-reader learning to match a shape to a word cannot match half a word,
    and cannot widen the tile. So: whatever the strip does to fit -- smaller
    tiles, smaller type, a wider tile for a longer word -- the lines it sets
    must join back to the name, with the same words in the same order and no
    hyphen that the grown-up did not type."""
    for item_id, tile in running.tiles.items():
        item = running.routine.by_id(item_id)
        label = _tile_label(tile)
        lines = label.get_label().split("\n")
        assert " ".join(line.strip() for line in lines).split() == item.name.split()
        assert "-" not in label.get_label() or "-" in item.name


def test_every_routine_line_fits_the_box_it_was_measured_for(running):
    """Not cut *and* not spilling. Each line, laid out at the size the strip
    settled on, is no wider than the label box the tile reserved -- which is
    the other half of "wrap, never cut": a label that overflows its tile is
    clipped by the tile, which is a cut word wearing a different hat."""
    from gi.repository import Gtk

    for tile in running.tiles.values():
        label = _tile_label(tile)
        box = label.get_size_request()[0]
        if box <= 0:  # an unknown panel constrains nothing
            continue
        assert label.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= box


def test_the_strip_asks_for_no_more_room_than_the_row_has(running):
    """The plan is made with Pango and the widgets are built from it, so the
    two must agree: the strip's *minimum* width -- which is what GTK will not
    go below, and what pushed v0.1.0's window past the panel -- fits inside the
    content box's margins."""
    from gi.repository import Gtk

    area = running.window.area
    if not area.known:
        return
    strip = next(
        w
        for w in _children(running.window.content)
        if w.has_css_class("routine-strip")
    )
    minimum = strip.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
    assert minimum <= area.width - area.margin * 2


def _children(widget):
    child = widget.get_first_child()
    while child is not None:
        yield child
        child = child.get_next_sibling()


def test_a_long_name_gets_a_wider_tile_and_the_others_keep_the_floor(running):
    """The shape of the fix, on the real screen: the tile that carries the
    longest word is wider than the tile that says "Tea", and every tile is
    still at least the 20 mm ADR-0011 asks for."""
    area = running.window.area
    widths = {i: t.get_size_request()[0] for i, t in running.tiles.items()}
    assert widths["breakfast"] > widths["tea"]
    for tile_id, width in widths.items():
        assert area.mm_of(width) >= 20.0 - 1e-9, tile_id


def test_every_routine_label_is_at_least_eighteen_point(running):
    """SYNTHESIS B4's floor, read back off the attribute the label was set
    with -- the strip may shrink type to fit, and this is where it stops."""
    from gi.repository import Pango

    area = running.window.area
    sizes = set()
    for tile in running.tiles.values():
        attributes = _tile_label(tile).get_attributes()
        assert attributes is not None
        found = [
            attribute.as_size().size / Pango.SCALE
            for attribute in attributes.get_attributes()
            if attribute.klass.type == Pango.AttrType.SIZE
        ]
        assert found, "the label carries no size attribute at all"
        assert min(found) >= area.points(18.0) - 0.05
        sizes.add(round(found[-1], 1))
    # One size for the whole row: eight names, one typographic voice.
    assert len(sizes) == 1
