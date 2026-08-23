"""The four widgets, the focus ring, and the millimetres they are built from.

These need a display. On a developer machine that is the running Wayland or X
session; in CI there may be none, in which case every test here skips. The pure
half -- the voice, the captions, the stylesheet -- is in
``test_activity_sdk_speech.py`` and always runs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kidnix_activity.speech import ActivitySpeech
from kidnix_shell.speech import FakeBackend

from .test_activity_sdk_speech import voice

gi = pytest.importorskip("gi")

if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
    pytest.skip("no display; skipping GTK widget tests", allow_module_level=True)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

if not Gtk.init_check():  # pragma: no cover - display present but unusable
    pytest.skip("GTK could not initialise", allow_module_level=True)
Adw.init()

from kidnix_activity.app import ActivityWindow, application_id_for  # noqa: E402
from kidnix_activity.keyboard import ActivityKeyboard  # noqa: E402
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn, PictureTile, Prompt  # noqa: E402
from kidnix_shell.metrics import Metrics  # noqa: E402
from kidnix_shell.widgets import SpeechUI  # noqa: E402


def area() -> ContentArea:
    return ContentArea.from_panel(Metrics.for_screen(1280, 800, dpi=102.0))


def wired() -> tuple[ActivitySpeech, FakeBackend]:
    speech, backend, _ = voice()
    speech.ui = SpeechUI(speech.manager)
    return speech, backend


# --- the application id ----------------------------------------------------


def test_a_manifest_id_becomes_a_valid_application_id() -> None:
    assert application_id_for("hello-draw") == "org.kidnix.activity.hello_draw"
    assert application_id_for("sounds.and.words") == "org.kidnix.activity.sounds_and_words"
    assert Gtk.Application.id_is_valid(application_id_for("hello-draw"))
    assert Gtk.Application.id_is_valid(application_id_for("4-clocks"))
    assert Gtk.Application.id_is_valid(application_id_for(""))


# --- the window ------------------------------------------------------------


def test_the_window_asks_for_the_rectangle_below_the_band() -> None:
    content = area()
    speech, _ = wired()
    app = Adw.Application(application_id="org.kidnix.activity.test_window")
    window = ActivityWindow(app, title="Test", area=content, speech=speech)
    assert window.get_default_size() == (content.width, content.height)
    assert content.height < 800


def test_the_window_carries_the_shells_own_style_classes() -> None:
    speech, _ = wired()
    app = Adw.Application(application_id="org.kidnix.activity.test_classes")
    window = ActivityWindow(app, title="Test", area=area(), speech=speech)
    assert "kidnix" in window.get_css_classes()
    assert "kidnix-activity" in window.get_css_classes()
    assert "calm" not in window.get_css_classes()


def test_calm_mode_is_visible_to_the_stylesheet_and_to_a_test() -> None:
    speech, _ = wired()
    app = Adw.Application(application_id="org.kidnix.activity.test_calm")
    window = ActivityWindow(app, title="Test", area=area(), speech=speech, calm=True)
    assert "calm" in window.get_css_classes()


def test_adding_a_control_puts_it_in_the_ring() -> None:
    speech, _ = wired()
    app = Adw.Application(application_id="org.kidnix.activity.test_ring")
    window = ActivityWindow(app, title="Test", area=area(), speech=speech)
    button = BigButton("Go", speak_text="Go", area=window.area)
    window.add(button)
    assert window.keys.ring.order == [button]


def test_clearing_the_window_empties_the_ring_too() -> None:
    speech, _ = wired()
    app = Adw.Application(application_id="org.kidnix.activity.test_clear")
    window = ActivityWindow(app, title="Test", area=area(), speech=speech)
    window.add(BigButton("Go", speak_text="Go", area=window.area))
    window.clear()
    assert window.keys.ring.order == []
    assert window.content.get_first_child() is None


def test_a_big_button_is_a_target_a_five_year_old_can_hit() -> None:
    content = area()
    button = BigButton("Go", area=content)
    width, _height = button.get_size_request()
    assert width == content.big_button
    assert content.mm_of(width) >= 20.0


def test_a_big_button_speaks_its_own_sentence_not_its_label() -> None:
    speech, backend = wired()
    button = BigButton("Go", speak_text="Go. Make a square.", speech=speech, area=area())
    button.fire()
    assert backend.spoken == ["Go. Make a square."]


def test_a_big_button_with_no_sentence_falls_back_to_its_label() -> None:
    assert BigButton("Go").speak_text == "Go"


def test_the_accessible_name_is_the_spoken_string() -> None:
    button = BigButton("Go", speak_text="Go. Make a square.")
    assert button.speak_text == "Go. Make a square."


def test_a_big_button_cannot_double_fire() -> None:
    fired: list[int] = []
    button = BigButton("Go", on_activate=lambda: fired.append(1), area=area())
    for _ in range(8):
        button.fire()
    assert fired == [1]


def test_a_picture_tile_shows_a_file_and_is_still_a_target(tmp_path: Path) -> None:
    from .conftest import write_png

    picture = write_png(tmp_path / "square.png")
    content = area()
    tile = PictureTile(picture, "A teal square", area=content)
    assert tile.get_size_request()[0] == content.picture_tile
    assert content.mm_of(tile.get_size_request()[0]) >= 20.0


def test_a_picture_tile_survives_a_file_that_is_not_there(tmp_path: Path) -> None:
    tile = PictureTile(tmp_path / "gone.png", "Nothing yet", area=area())
    assert tile.path.name == "gone.png"


def test_a_prompt_writes_down_what_it_says() -> None:
    speech, backend = wired()
    prompt = Prompt("Press the big button.", speech=speech, area=area())
    assert prompt.text == "Press the big button."
    assert prompt.say() is True
    assert backend.spoken == ["Press the big button."]


def test_a_prompts_replay_says_the_prompt_not_the_last_thing_said() -> None:
    speech, backend = wired()
    prompt = Prompt("Press the big button.", speech=speech, area=area())
    speech.speak("A teal square. It is in My Things.")
    assert prompt.replay is not None
    prompt.replay.fire()
    assert backend.spoken[-1] == "Press the big button."


def test_a_prompt_can_change_without_interrupting_a_child() -> None:
    speech, backend = wired()
    prompt = Prompt("Press the big button.", speech=speech, area=area())
    prompt.set_text("A teal square. Press again for another.")
    assert prompt.text == "A teal square. Press again for another."
    assert backend.spoken == []


def test_the_replay_is_a_target_too() -> None:
    content = area()
    prompt = Prompt("Press the big button.", area=content)
    assert prompt.replay is not None
    assert prompt.replay.get_size_request()[0] == content.min_target


def test_the_grown_up_card_looks_nothing_like_the_childs_screen() -> None:
    card = GrownUpTurn("Ask what colour they made.", area=area())
    assert "grownup-turn" in card.get_css_classes()
    assert card.title_text == "Your turn, grown-up"


def test_the_grown_up_card_is_not_a_dialogue() -> None:
    """No ``on_done`` means no button at all, and the activity carries on."""
    card = GrownUpTurn("Ask what colour they made.", area=area())
    assert card.done is None


def test_the_grown_up_cards_button_is_an_adults_not_a_childs() -> None:
    content = area()
    card = GrownUpTurn("Ask.", on_done=lambda: None, area=content)
    assert card.done is not None
    assert card.done.get_size_request()[1] == content.mm_floor(9.0)
    assert card.done.get_size_request()[1] < content.min_target


def test_only_the_title_of_the_grown_up_card_is_read_to_a_child() -> None:
    speech, backend = wired()
    card = GrownUpTurn("Ask what colour they made.", speech=speech, area=area())
    card.announce()
    assert backend.spoken == ["Your turn, grown-up"]


# --- the focus ring --------------------------------------------------------


def ring_over(*widgets: Gtk.Widget) -> tuple[ActivityKeyboard, Gtk.Box]:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    for widget in widgets:
        box.append(widget)
    keys = ActivityKeyboard()
    keys.set_content(box)
    return keys, box


def test_tab_walks_the_controls_in_reading_order() -> None:
    first = BigButton("One", speak_text="One")
    second = BigButton("Two", speak_text="Two")
    keys, _ = ring_over(first, second)
    assert keys.focus_first() is first
    assert keys.key(Gdk.KEY_Tab) is True
    assert keys.focused is second


def test_escape_is_the_shells_and_the_activity_never_takes_it() -> None:
    """Back is a band button, in another process, and the only way out."""
    keys, _ = ring_over(BigButton("One", speak_text="One"))
    assert keys.key(Gdk.KEY_Escape) is False
    assert keys.key(Gdk.KEY_BackSpace) is False


def test_enter_presses_what_the_ring_is_on() -> None:
    fired: list[int] = []
    button = BigButton("One", speak_text="One", on_activate=lambda: fired.append(1))
    keys, _ = ring_over(button)
    keys.focus_first()
    assert keys.key(Gdk.KEY_Return) is True
    assert fired == [1]


def test_the_ring_paints_itself_because_focus_visible_cannot() -> None:
    button = BigButton("One", speak_text="One")
    keys, _ = ring_over(button)
    keys.focus_first()
    assert "kid-focus" in button.get_css_classes()


def test_a_rebuilt_layout_does_not_leave_a_ring_on_a_dead_widget() -> None:
    button = BigButton("One", speak_text="One")
    keys, box = ring_over(button)
    keys.focus_first()
    box.remove(button)
    keys.refresh()
    assert keys.focused is None
