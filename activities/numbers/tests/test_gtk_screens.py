"""The screen, built for real, under Broadway.

These need a display. On a developer's machine that must **not** be the
developer's own desktop (AGENTS.md; ``docs/design/activity-sdk.md`` section
10) -- run them under GTK's Broadway backend::

    gtk4-broadwayd :112 &
    env -u WAYLAND_DISPLAY -u DISPLAY GDK_BACKEND=broadway \\
        BROADWAY_DISPLAY=:112 uv run --active pytest tests/test_gtk_screens.py

Where there is no display at all they skip, and the pure-logic tests -- which
are the ones that carry the guarantee -- carry on. That is the SDK's rule and
the CI floor: *GTK tests may skip; logic tests may not.*
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from conftest import HAVE_SDK

if not HAVE_SDK:  # pragma: no cover - no SDK, no window
    pytest.skip("kidnix_activity is not importable here", allow_module_level=True)

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

if not Gtk.init_check() or Gdk.Display.get_default() is None:  # pragma: no cover
    pytest.skip("no usable display; run under gtk4-broadwayd", allow_module_level=True)
Adw.init()

from kidnix_activity.app import ActivityWindow  # noqa: E402
from kidnix_activity.captions import CaptionClient  # noqa: E402
from kidnix_activity.keyboard import focusables  # noqa: E402
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.speech import ActivitySpeech  # noqa: E402
from kidnix_shell.metrics import Metrics  # noqa: E402
from kidnix_shell.speech import FakeBackend  # noqa: E402
from kidnix_shell.widgets import ChildButton, SpeechUI  # noqa: E402

from numbers_activity.activity import BondFrame, NumbersActivity, NumberTile  # noqa: E402
from numbers_activity.items import HowMany, MakeBond, Response  # noqa: E402
from numbers_activity.settings import NumberRange, ParentSettings  # noqa: E402

WINDOWS: list[ActivityWindow] = []


class Sink(CaptionClient):
    """A caption client that goes nowhere. No shell is listening in a test."""

    def send(self, text: str) -> bool:
        return False


class FakeApp:
    """Just enough of ActivityApplication for the activity to be built.

    A stub rather than the real thing because ``save_entry`` writes into the
    child's own Journal, and a test must never do that to somebody's home
    directory.
    """

    class Access:
        calm = False

    def __init__(self) -> None:
        self.title = "Numbers"
        self.access = FakeApp.Access()
        self.saved: list[dict] = []
        self.sounds: list[str] = []

    def save_entry(self, kind, files, caption=None, voice=None, meta=None):
        self.saved.append(
            {"kind": kind, "files": [Path(f) for f in files], "caption": caption, "meta": meta}
        )
        return type("Entry", (), {"id": "test-entry"})()

    def play(self, earcon: str = "tap") -> bool:
        self.sounds.append(earcon)
        return True


def _window() -> ActivityWindow:
    speech = ActivitySpeech("numbers", backend=FakeBackend(), captions=Sink("test"))
    speech.ui = SpeechUI(speech.manager)
    area = ContentArea.from_panel(Metrics.for_screen(1280, 800, dpi=102.0))
    application = Adw.Application(application_id="org.kidnix.test.numbers")
    window = ActivityWindow(application, title="Numbers", area=area, speech=speech)
    WINDOWS.append(window)
    return window


def _built(settings: ParentSettings | None = None, seed: int = 5, scratch: Path | None = None):
    app = FakeApp()
    activity = NumbersActivity(
        app,
        settings if settings is not None else ParentSettings(),
        rng=random.Random(seed),
        scratch=scratch,
    )
    window = _window()
    activity.build(window)
    return app, activity, window


def teardown_module(_module) -> None:  # pragma: no cover - tidying
    for window in WINDOWS:
        window.destroy()
    WINDOWS.clear()


# -- it builds ---------------------------------------------------------------


def test_the_screen_builds(tmp_path: Path) -> None:
    _app, activity, window = _built(scratch=tmp_path)
    assert activity.prompt is not None
    assert activity.stage is not None
    assert window.get_title() == "Numbers"


def test_the_first_item_is_a_how_many_with_its_picture_up(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    assert isinstance(activity.item, HowMany)
    assert activity.card is not None
    assert activity.card.showing is True


def test_there_is_one_numeral_tile_per_choice(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    assert set(activity.tiles) == set(activity.settings.choices) == {1, 2, 3, 4, 5}
    for tile in activity.tiles.values():
        assert isinstance(tile, NumberTile)


def test_the_ten_range_gets_ten_tiles(tmp_path: Path) -> None:
    _app, activity, _window = _built(ParentSettings(range=NumberRange.TEN), scratch=tmp_path)
    assert set(activity.tiles) == set(range(1, 11))


def test_turning_numerals_off_leaves_the_dots(tmp_path: Path) -> None:
    _app, activity, _window = _built(ParentSettings(numerals=False), scratch=tmp_path)
    for tile in activity.tiles.values():
        assert tile.label is None
        assert tile.pattern is not None


# -- targets, speech and the ring --------------------------------------------


def test_every_numeral_tile_is_at_least_the_floor(tmp_path: Path) -> None:
    _app, activity, window = _built(scratch=tmp_path)
    floor = window.area.min_target
    for tile in activity.tiles.values():
        width, height = tile.get_size_request()
        assert width >= floor and height >= floor
        assert window.area.mm_of(width) >= 19.9


def test_every_numeral_tile_says_its_number(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    for number, tile in activity.tiles.items():
        assert tile.speak_text.lower() in {
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        }
        assert str(number) not in tile.speak_text


def test_the_focus_ring_reaches_the_tiles(tmp_path: Path) -> None:
    _app, activity, window = _built(scratch=tmp_path)
    ring = focusables(window.content)
    assert set(activity.tiles.values()) <= set(ring)


def test_escape_is_not_consumed(tmp_path: Path) -> None:
    # It belongs to the shell, one screen up (SDK section 3.4).
    _app, _activity, window = _built(scratch=tmp_path)
    assert window.keys.key(Gdk.KEY_Escape) is False
    assert window.keys.key(Gdk.KEY_BackSpace) is False


def test_a_digit_key_answers(tmp_path: Path) -> None:
    _app, activity, window = _built(scratch=tmp_path)
    item = activity.item
    assert isinstance(item, HowMany)
    assert window.keys.key(Gdk.KEY_1 + item.count - 1) is True
    assert activity.played is True


# -- answering ---------------------------------------------------------------


def test_the_right_answer_moves_on(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    item = activity.item
    assert isinstance(item, HowMany)
    activity.answer(item.count)
    activity.next_item()
    assert activity.index == 1


def test_a_wrong_answer_brings_the_picture_back(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    item = activity.item
    assert isinstance(item, HowMany)
    activity._hide_card()
    assert activity.card is not None and activity.card.showing is False
    wrong = 1 + (item.count % 5)
    activity.answer(wrong)
    activity._count_out(item, Response.TRY_AGAIN)
    assert activity.card.showing is True
    assert activity.attempts == 1


def test_show_me_again_is_free_and_unlimited(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    activity._hide_card()
    for _ in range(5):
        activity.flash_again()
    assert activity.card is not None and activity.card.showing is True
    assert activity.attempts == 0, "asking to look again is not an attempt"


# -- the frame ---------------------------------------------------------------


def _bond_activity(tmp_path: Path):
    app, activity, window = _built(scratch=tmp_path)
    for index, item in enumerate(activity.items):
        if isinstance(item, MakeBond):
            activity.index = index
            break
    activity.start_item()
    return app, activity, window


def test_the_bond_screen_has_one_target_per_empty_box(tmp_path: Path) -> None:
    _app, activity, _window = _bond_activity(tmp_path)
    item = activity.item
    assert isinstance(item, MakeBond)
    assert isinstance(activity.frame, BondFrame)
    assert len(activity.frame.targets) == item.missing


def test_the_counters_already_there_are_not_controls(tmp_path: Path) -> None:
    _app, activity, _window = _bond_activity(tmp_path)
    item = activity.item
    assert isinstance(item, MakeBond)
    assert all(index >= item.shown for index in activity.frame.targets)


def test_every_box_target_is_at_least_the_floor(tmp_path: Path) -> None:
    _app, activity, window = _bond_activity(tmp_path)
    floor = window.area.min_target
    for button in activity.frame.targets.values():
        width, height = button.get_size_request()
        assert width >= floor and height >= floor


def test_filling_the_frame_completes_the_bond(tmp_path: Path) -> None:
    app, activity, _window = _bond_activity(tmp_path)
    item = activity.item
    assert isinstance(item, MakeBond)
    for button in list(activity.frame.targets.values()):
        button.fire()
    assert activity.practised.bonds == [item.bond]
    assert "tap" in app.sounds


def test_a_counter_can_be_taken_back_out(tmp_path: Path) -> None:
    _app, activity, _window = _bond_activity(tmp_path)
    index, button = next(iter(sorted(activity.frame.targets.items())))
    activity.frame._pressed(index)
    assert activity.frame.added == 1
    activity.frame._pressed(index)
    assert activity.frame.added == 0
    assert isinstance(button, ChildButton)


def test_pressing_the_missing_number_completes_the_bond(tmp_path: Path) -> None:
    _app, activity, _window = _bond_activity(tmp_path)
    item = activity.item
    assert isinstance(item, MakeBond)
    activity.answer(item.missing)
    assert activity.frame.added == item.missing
    assert activity.practised.bonds == [item.bond]


def test_the_second_wrong_number_fills_it_in_and_moves_on(tmp_path: Path) -> None:
    _app, activity, _window = _bond_activity(tmp_path)
    item = activity.item
    assert isinstance(item, MakeBond)
    wrong = 1 + (item.missing % 4)
    activity.answer(wrong)
    assert activity.practised.bonds == []
    activity.answer(wrong)
    assert activity.practised.bonds == [item.bond]


# -- the end of the loop -----------------------------------------------------


def test_the_end_of_the_loop_keeps_a_card(tmp_path: Path) -> None:
    app, activity, _window = _built(scratch=tmp_path)
    activity.practised.add_bond((3, 2, 5))
    activity.practised.add_count(4)
    activity.index = len(activity.items)
    activity.start_item()
    assert app.saved, "the loop must leave something in My Things"
    entry = app.saved[0]
    assert entry["kind"] == "picture"
    assert entry["files"][0].suffix == ".png"
    assert entry["caption"] == "Today: three and two make five"
    assert "bonds" in entry["meta"]
    assert not any("score" in str(key) for key in entry["meta"])


def test_the_numerals_go_away_when_there_is_nothing_to_answer(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    activity.index = len(activity.items)
    activity.start_item()
    assert activity.tile_row is not None
    assert activity.tile_row.get_visible() is False


def test_the_end_offers_more_only_when_it_is_pressed(tmp_path: Path) -> None:
    _app, activity, _window = _built(scratch=tmp_path)
    activity.index = len(activity.items)
    activity.start_item()
    assert activity.finished is True
    activity.again()
    assert activity.finished is False
    assert activity.index == 0
    assert activity.tile_row.get_visible() is True


def test_nothing_is_kept_when_nothing_was_played(tmp_path: Path) -> None:
    app, activity, _window = _built(scratch=tmp_path)
    activity.finish()
    assert app.saved == []


def test_the_way_out_keeps_whatever_has_not_been_kept(tmp_path: Path) -> None:
    app, activity, _window = _built(scratch=tmp_path)
    activity.played = True
    activity.practised.add_bond((1, 4, 5))
    activity.finish()
    assert len(app.saved) == 1
    activity.finish()
    assert len(app.saved) == 1, "a second SIGTERM must not write a second card"
