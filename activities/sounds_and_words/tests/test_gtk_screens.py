"""The two screens, built for real, under Broadway.

These need a display. On a developer's machine that must **not** be the
developer's own desktop (AGENTS.md; ``docs/design/activity-sdk.md`` section
10) -- run them under GTK's Broadway backend::

    gtk4-broadwayd :108 &
    env -u WAYLAND_DISPLAY -u DISPLAY GDK_BACKEND=broadway \\
        BROADWAY_DISPLAY=:108 uv run --active pytest tests/test_gtk_screens.py

Where there is no display at all they skip, and the pure-logic tests -- which
are the ones that carry the guarantee -- carry on. That is the SDK's rule and
the CI floor: *GTK tests may skip; logic tests may not.*
"""

from __future__ import annotations

import random
from datetime import date
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
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.speech import ActivitySpeech  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn  # noqa: E402
from kidnix_shell.metrics import Metrics  # noqa: E402
from kidnix_shell.speech import FakeBackend  # noqa: E402
from kidnix_shell.widgets import ChildButton, SpeechUI  # noqa: E402

from sounds_and_words.activity import (  # noqa: E402
    SoundsAndWords,
    build_blend_it,
    build_find_it,
)
from sounds_and_words.blend import Stage  # noqa: E402
from sounds_and_words.ceiling import ceiling_for_grapheme  # noqa: E402
from sounds_and_words.distractors import board_graphemes  # noqa: E402
from sounds_and_words.phonemes import say_label  # noqa: E402
from sounds_and_words.reader import (  # noqa: E402
    READING_MIN_PT,
    BookShelf,
    ReadIt,
    build_read_it,
    build_shelf,
)
from sounds_and_words.reading import illustration_for, text_by_slug, texts_for  # noqa: E402
from sounds_and_words.schedule import ItemKind  # noqa: E402
from sounds_and_words.settings import Narration  # noqa: E402
from sounds_and_words.text import FIND_IT, names_a_grapheme, tokens  # noqa: E402

WINDOWS: list[ActivityWindow] = []


class Sink(CaptionClient):
    """A caption client that goes nowhere, and writes down what it was given.

    No shell is listening in a test, so ``send`` returns ``False`` and the
    activity speaks the line itself -- the real behaviour on a developer's
    desktop. The list is how a test reads the caption strip: everything kidnix
    says passes through here *before* the "is speech even on?" check, which is
    the invariant that makes mute safe to offer.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lines: list[str] = []

    def send(self, text: str) -> bool:
        self.lines.append(text)
        return False


class FakeApp:
    """Just enough of ActivityApplication for the activity to be built.

    A stub rather than the real thing because ``save_entry`` writes into the
    child's own Journal, and a test must never do that to somebody's home
    directory.
    """

    def __init__(self) -> None:
        self.title = "Sounds & words"
        self.saved: list[dict] = []

    def save_entry(self, kind, files, caption=None, voice=None, meta=None):
        self.saved.append(
            {"kind": kind, "files": [Path(f) for f in files], "caption": caption, "meta": meta}
        )
        return type("Entry", (), {"id": f"fake-{len(self.saved)}"})()


def area() -> ContentArea:
    return ContentArea.from_panel(Metrics.for_screen(1280, 800, dpi=102.0))


def window(name: str) -> ActivityWindow:
    speech = ActivitySpeech("sounds-and-words", backend=FakeBackend(), captions=Sink("test"))
    speech.ui = SpeechUI(speech.manager)
    app = Adw.Application(application_id=f"org.kidnix.activity.saw_{name}")
    made = ActivityWindow(app, title="Sounds & words", area=area(), speech=speech)
    WINDOWS.append(made)
    return made


@pytest.fixture
def activity(corpus, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("KIDNIX_PROFILE_ID", "test")
    made = SoundsAndWords(
        FakeApp(),
        corpus=corpus,
        ceiling=ceiling_for_grapheme(corpus, "ng"),
        seed=5,
        today=date(2026, 8, 23),
    )
    made.rng = random.Random(5)
    return made


def tiles(screen) -> list[BigButton]:
    return list(screen.tiles.values())


# --- Find it ----------------------------------------------------------------


def test_a_find_it_board_is_four_tiles_and_a_prompt(activity):
    win = window("find")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    assert len(screen.tiles) == 4
    assert screen.prompt.text == FIND_IT


# --- the prompt does not print the answer ------------------------------------
#
# The checkpoint-2 audit's first defect against this activity: the screen said
# "Find the one that says k." over four tiles, one of which was `k`. The task
# is to match a *sound* to a grapheme, so the sound is a separate utterance and
# the sentence stops at an ellipsis. The rule itself is tested headless in
# `tests/test_text.py`; these are the assertions about what is on the glass.


def test_the_prompt_never_prints_the_grapheme_it_is_asking_for(activity):
    win = window("find_no_answer")
    activity.window = win
    for gpc_id in ("s", "m", "k", "sh", "ng"):
        target = activity.corpus.gpc_by_id[gpc_id]
        screen = build_find_it(win, activity, target)
        assert names_a_grapheme(screen.prompt.text, board_graphemes(screen.board)) is None
        assert target.grapheme not in tokens(screen.prompt.text)


def test_the_instruction_and_the_sound_are_two_utterances(activity):
    """Joined, they would put the answer back in the caption strip -- which is
    where the audit found it."""
    win = window("find_two_lines")
    activity.window = win
    target = activity.corpus.gpc_by_id["s"]
    screen = build_find_it(win, activity, target)
    activity.screen = screen

    screen.announce()
    assert win.speech.last_utterance == screen.prompt.text
    assert names_a_grapheme(win.speech.last_utterance, board_graphemes(screen.board)) is None

    screen.say_sound()
    assert win.speech.last_utterance == say_label(target)


def test_no_caption_of_the_instruction_carries_a_grapheme(activity):
    """The caption strip is a deaf child's accommodation, not everybody's
    answer key. The sound's own caption is the label -- that one *is* the
    accommodation, and it is a separate line."""
    win = window("find_caption")
    activity.window = win
    target = activity.corpus.gpc_by_id["k"]
    screen = build_find_it(win, activity, target)
    win.speech.captions.lines.clear()
    screen.announce()
    assert win.speech.captions.lines == [screen.prompt.text]
    assert names_a_grapheme(win.speech.captions.lines[0], board_graphemes(screen.board)) is None


def test_a_prompt_edited_to_name_a_tile_is_refused(activity, monkeypatch):
    """`parent_text.toml` is copy a grown-up can edit and a translator will
    rewrite. "Find the one that says k." is exactly the helpful edit somebody
    makes, and the screen must not take it."""
    monkeypatch.setitem(
        activity.corpus.parent_text["child"], "find_it", "Find the one that says k."
    )
    win = window("find_bad_copy")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["k"])
    assert screen.prompt.text == FIND_IT


def test_the_blend_it_prompt_says_what_to_do_and_not_the_word(activity):
    win = window("blend_no_answer")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    assert "ship" not in tokens(screen.prompt.text)
    assert names_a_grapheme(screen.prompt.text, board_graphemes(activity.corpus.gpcs)) is None


def test_every_tile_is_forty_millimetres(activity):
    win = window("find_size")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    for tile in tiles(screen):
        width, height = tile.get_size_request()
        assert win.area.mm_of(width) >= 40.0
        assert win.area.mm_of(height) >= 40.0


def test_every_tile_says_its_sound_rather_than_its_name(activity):
    win = window("find_speak")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["s"])
    spoken = {tile.speak_text for tile in tiles(screen)}
    assert "sss" in spoken
    assert "ess" not in spoken


def test_the_tiles_are_in_the_keyboard_ring(activity):
    win = window("find_ring")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    ring = win.keys.refresh()
    for tile in tiles(screen):
        assert tile in ring


def test_the_replay_button_is_a_target_too(activity):
    win = window("find_replay")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    assert screen.prompt.replay is not None
    width, _ = screen.prompt.replay.get_size_request()
    assert win.area.mm_of(width) >= 20.0


def test_pressing_the_right_tile_lights_it_and_writes_the_box(activity):
    win = window("find_right")
    activity.window = win
    target = activity.corpus.gpc_by_id["m"]
    activity.runner.plan.items[0]  # the plan exists; we drive the screen directly
    screen = build_find_it(win, activity, target)
    activity.screen = screen
    screen.choose("m")
    assert "correct" in screen.tiles["m"].get_css_classes()
    assert screen.answered


def test_pressing_a_wrong_tile_pulses_the_right_one_and_leaves_the_other_alone(activity):
    win = window("find_wrong")
    activity.window = win
    target = activity.corpus.gpc_by_id["m"]
    screen = build_find_it(win, activity, target)
    activity.screen = screen
    wrong = next(g for g in screen.tiles if g != "m")
    screen.choose(wrong)
    assert "pulse" in screen.tiles["m"].get_css_classes()
    assert "pulse" not in screen.tiles[wrong].get_css_classes()
    assert "correct" not in screen.tiles[wrong].get_css_classes()
    assert not screen.answered


def test_nothing_anywhere_on_the_board_is_red_or_a_cross(activity):
    win = window("find_no_red")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    screen.choose(next(g for g in screen.tiles if g != "m"))
    classes = {css for tile in tiles(screen) for css in tile.get_css_classes()}
    assert not {"error", "wrong", "destructive-action"} & classes


def test_two_wrong_answers_move_on_without_comment(activity):
    win = window("find_two")
    activity.window = win
    target = activity.corpus.gpc_by_id["m"]
    screen = build_find_it(win, activity, target)
    activity.screen = screen
    wrong = next(g for g in screen.tiles if g != "m")
    screen.choose(wrong)
    screen.choose(wrong)
    assert screen.answered


def test_a_letter_key_chooses_the_tile(activity):
    win = window("find_key")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    activity.screen = screen
    assert screen.key("m")
    assert "correct" in screen.tiles["m"].get_css_classes()


def test_a_capital_key_chooses_the_same_tile(activity):
    win = window("find_caps")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    activity.screen = screen
    assert screen.key("M")
    assert "correct" in screen.tiles["m"].get_css_classes()


def test_a_digraph_takes_two_keys_and_the_first_is_not_wrong(activity):
    win = window("find_digraph")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["sh"])
    activity.screen = screen
    assert screen.key("s")
    assert "correct" not in screen.tiles["sh"].get_css_classes()
    assert screen.key("h")
    assert "correct" in screen.tiles["sh"].get_css_classes()


def test_a_key_that_is_not_on_the_board_costs_nothing(activity):
    win = window("find_unknown")
    activity.window = win
    screen = build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    activity.screen = screen
    screen.key("z")
    assert not screen.answered
    assert activity.runner.attempts == 0


def test_escape_is_not_ours(activity):
    """Back is the band's, one screen up, in every activity (SDK 3.4)."""
    win = window("find_escape")
    activity.window = win
    build_find_it(win, activity, activity.corpus.gpc_by_id["m"])
    assert win.keys.key(Gdk.KEY_Escape) is False
    assert win.keys.key(Gdk.KEY_BackSpace) is False


# --- Blend it ---------------------------------------------------------------


def test_a_word_becomes_one_sound_button_per_sound(activity):
    win = window("blend")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    assert len(screen.buttons) == 3


def test_every_sound_button_clears_the_twenty_millimetre_floor(activity):
    win = window("blend_size")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    for button in screen.buttons:
        width, height = button.get_size_request()
        assert win.area.mm_of(width) >= 20.0
        assert win.area.mm_of(height) >= 20.0


def test_the_sound_buttons_say_sounds(activity):
    win = window("blend_speak")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    assert [button.speak_text for button in screen.buttons] == ["shh", "iii", "p"]


def test_a_word_with_a_picture_shows_it_and_it_is_not_pressable(activity):
    win = window("blend_picture")
    activity.window = win
    screen = build_blend_it(win, activity, "cat")
    pictures = [
        child
        for child in _walk(win.content)
        if isinstance(child, Gtk.Picture) and "word-picture" in child.get_css_classes()
    ]
    assert pictures
    assert not isinstance(pictures[0], ChildButton)
    assert screen.state.word.picture is not None


def test_pressing_a_sound_button_says_that_sound_and_nothing_else(activity):
    win = window("blend_sound")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    screen.sound(0)
    assert win.speech.last_utterance == "shh"
    assert screen.state.sounded == {0}


def test_the_arrow_pushes_the_tiles_together_and_says_the_word(activity):
    win = window("blend_push")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    activity.screen = screen
    screen.push()
    assert screen.state.stage is Stage.PUSHED
    assert screen.row.get_spacing() == 0
    assert win.speech.last_utterance == "ship"


def test_the_arrow_works_before_any_sound_button_has_been_pressed(activity):
    win = window("blend_push_first")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    activity.screen = screen
    assert screen.push_button.get_sensitive()
    screen.push()
    assert screen.state.stage is Stage.PUSHED


def test_after_the_push_a_grown_up_is_asked_and_the_software_stops(activity):
    win = window("blend_say")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    activity.screen = screen
    screen.push()
    screen.say_it()
    cards = [child for child in _walk(win.content) if isinstance(child, GrownUpTurn)]
    assert cards
    assert screen.state.stage is Stage.SAY_IT
    assert "out loud" in screen.prompt.text.lower()


def test_the_grown_up_card_never_takes_the_childs_place(activity):
    """Not a dialogue and not modal: if nobody presses anything the child can
    carry on (SDK section 7)."""
    win = window("blend_card")
    activity.window = win
    screen = build_blend_it(win, activity, "ship")
    activity.screen = screen
    screen.push()
    screen.say_it()
    assert not isinstance(win.content.get_first_child(), GrownUpTurn)


def test_a_word_above_the_ceiling_never_reaches_a_screen(activity):
    win = window("blend_gate")
    activity.window = win
    with pytest.raises(ValueError):
        build_blend_it(win, activity, "night")


# --- the whole loop ---------------------------------------------------------


def test_a_session_walks_find_it_then_blend_it_then_stops(activity):
    win = window("loop")
    activity.build(win)
    kinds = []
    for _ in range(len(activity.plan) + 1):
        item = activity.runner.current
        kinds.append(item.kind if item is not None else None)
        activity.next_item()
    assert kinds[0] is ItemKind.FIND_IT
    assert ItemKind.BLEND_IT in kinds
    assert kinds[-1] is None
    assert activity.runner.done


def test_the_end_keeps_a_card_with_the_words_and_no_score(activity):
    win = window("loop_end")
    activity.build(win)
    activity.runner.blend("cat")
    activity.runner.blend("sat")
    activity.show_done()
    kept = activity.app.saved
    assert len(kept) == 1
    assert kept[0]["kind"] == "sounds"
    assert kept[0]["caption"] == "Read today: cat, sat"
    assert kept[0]["files"][0].is_file()
    assert set(kept[0]["meta"]) == {"gpcs_practised", "words", "date", "ceiling"}


def test_a_session_where_nothing_was_blended_keeps_nothing(activity):
    """kidnix does not manufacture an artefact for a session that produced
    none, and it does not tell the child off for it either."""
    win = window("loop_empty")
    activity.build(win)
    activity.show_done()
    assert activity.app.saved == []


def test_sigterm_saves_the_schedule_once_and_asks_nothing(activity, tmp_path):
    activity.progress_path = tmp_path / "history.json"
    win = window("loop_finish")
    activity.build(win)
    activity.runner.attempt(correct=True)
    activity.runner.blend("cat")
    activity.finish()
    activity.finish()
    assert activity.progress_path.is_file()
    assert len(activity.app.saved) == 1


def test_reaching_the_end_and_then_being_stopped_keeps_one_card_not_two(activity, tmp_path):
    """The done screen keeps the card; SIGTERM arrives a moment later. Two
    identical cards in My Things is a bug a child would have to live with."""
    activity.progress_path = tmp_path / "history.json"
    win = window("loop_double")
    activity.build(win)
    activity.runner.blend("cat")
    activity.show_done()
    activity.finish()
    assert len(activity.app.saved) == 1


def test_a_word_blended_after_the_card_was_kept_gets_its_own_card(activity, tmp_path):
    activity.progress_path = tmp_path / "history.json"
    win = window("loop_more")
    activity.build(win)
    activity.runner.blend("cat")
    activity.keep()
    activity.runner.blend("sat")
    activity.keep()
    assert [entry["caption"] for entry in activity.app.saved] == [
        "Read today: cat",
        "Read today: cat, sat",
    ]


def test_no_screen_in_this_activity_shows_a_digit(activity):
    """01 #19 / 03 #32: no digits where a child can see them."""
    win = window("loop_digits")
    activity.build(win)
    for _ in range(len(activity.plan)):
        text = " ".join(
            label.get_text() for label in _walk(win.content) if isinstance(label, Gtk.Label)
        )
        assert not any(character.isdigit() for character in text), text
        activity.next_item()


def _walk(root: Gtk.Widget):
    child = root.get_first_child()
    while child is not None:
        yield child
        yield from _walk(child)
        child = child.get_next_sibling()


# --- the clip player ---------------------------------------------------------
#
# `sounds_and_words.clips` is tested on its own, with a fake GStreamer, in
# `tests/test_clips.py`. What is tested here is the *wiring*: which of the two
# sounds a child gets, and what the caption strip is left holding.


class FakePlayer:
    """A clip player that makes no noise and remembers being asked."""

    def __init__(self, *, ok: bool = True) -> None:
        self.played: list[tuple[Path, float]] = []
        self.ok = ok
        self.closed = False

    def play(self, path, *, volume: float = 1.0) -> bool:
        self.played.append((Path(path), volume))
        return self.ok

    def stop(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def with_clip(activity, tmp_path, gpc_id="s", *, ok=True):
    """An activity whose `s` has a recording, and a player that will take it."""
    (tmp_path / f"{gpc_id}.ogg").write_bytes(b"OggS-not-really")
    activity.clip_dir = tmp_path
    player = FakePlayer(ok=ok)
    activity._player = player
    return player


def test_a_recorded_phoneme_is_played_and_not_spoken(activity, tmp_path):
    """The whole point of the recordings: a person saying /s/, not an engine
    saying "sss"."""
    win = window("clip_played")
    activity.window = win
    player = with_clip(activity, tmp_path)
    win.speech.speak("something else")
    activity.say_phoneme(activity.corpus.gpc_by_id["s"])
    assert [path.name for path, _volume in player.played] == ["s.ogg"]
    assert win.speech.last_utterance == "something else"


def test_a_phoneme_with_no_recording_falls_back_to_the_spelled_label(activity, tmp_path):
    win = window("clip_missing")
    activity.window = win
    activity.clip_dir = tmp_path  # empty: no clip for anything
    player = FakePlayer()
    activity._player = player
    activity.say_phoneme(activity.corpus.gpc_by_id["s"])
    assert player.played == []
    assert win.speech.last_utterance == "sss"


def test_a_player_that_cannot_play_still_leaves_the_child_a_sound(activity, tmp_path):
    """Every failure path ends in a sound. A silent tile is the one outcome a
    five-year-old cannot act on."""
    win = window("clip_failed")
    activity.window = win
    with_clip(activity, tmp_path, ok=False)
    activity.say_phoneme(activity.corpus.gpc_by_id["s"])
    assert win.speech.last_utterance == "sss"


def test_mute_takes_the_clip_away_and_leaves_the_caption(activity, tmp_path):
    """Mute is silence *with the captions still running*. A clip played into a
    muted sink would be silence with nothing on the strip, so the label's path
    is taken instead -- it is the one that goes through the caption hook."""
    win = window("clip_muted")
    activity.window = win
    player = with_clip(activity, tmp_path)
    win.speech.apply_access(win.speech.access.with_overrides(mute=True))
    win.speech.captions.lines.clear()
    activity.say_phoneme(activity.corpus.gpc_by_id["s"])
    assert player.played == []
    assert win.speech.captions.lines == ["sss"]


def test_the_clip_is_played_at_the_volume_the_parent_set(activity, tmp_path):
    win = window("clip_volume")
    activity.window = win
    player = with_clip(activity, tmp_path)
    win.speech.apply_access(win.speech.access.with_overrides(sound_volume=0.5))
    activity.say_phoneme(activity.corpus.gpc_by_id["s"])
    assert player.played[-1][1] == 0.5


def test_the_player_is_let_go_when_the_session_ends(activity, tmp_path):
    win = window("clip_finish")
    activity.window = win
    player = with_clip(activity, tmp_path)
    activity.finish()
    assert player.closed


# --- Read it (module E) ------------------------------------------------------
#
# Takacs, Swart & Bus (2015) is the meta-analysis this whole screen is shaped
# by: narration with congruent illustration helps, and hotspots, tap-to-animate
# and tap-a-word dictionaries hurt. The tests that matter most here are
# therefore the ones about what is *absent* -- that the sentence is one label
# and not one control per word, and that nothing on the page responds to being
# tapped except the three buttons at the bottom.


def a_book(activity, slug="ducks-at-the-pond"):
    found = text_by_slug(slug)
    assert found is not None, slug
    return found


def reader(activity, name, slug="ducks-at-the-pond", narration=Narration.OPTIONAL, on_done=None):
    win = window(name)
    activity.window = win
    screen = build_read_it(
        win, activity, a_book(activity, slug), narration=narration, on_done=on_done
    )
    return win, screen


# --- the shelf ---------------------------------------------------------------


def test_a_shelf_page_never_holds_more_than_five_books(activity):
    """ADR-0013: five is the bound on a choice the child has to weigh, and
    picking a book off a shelf is squarely that."""
    win = window("shelf")
    activity.window = win
    books = texts_for(activity.corpus, activity.ceiling)
    screen = build_shelf(win, activity, books, lambda book: None)
    assert len(screen.tiles) <= 5
    assert len(screen.tiles) == len(screen.books)


def test_every_book_says_its_own_name(activity):
    """PictureTile speaks on hover and on focus, so a child sweeping the shelf
    hears what each book is called without having to open one."""
    win = window("shelf_speak")
    activity.window = win
    screen = build_shelf(win, activity, texts_for(activity.corpus, activity.ceiling), lambda b: None)
    for tile, book in zip(screen.tiles, screen.books, strict=True):
        assert book.title in tile.speak_text


def test_every_book_shows_its_title_and_its_picture(activity):
    win = window("shelf_tiles")
    activity.window = win
    screen = build_shelf(win, activity, texts_for(activity.corpus, activity.ceiling), lambda b: None)
    for tile, book in zip(screen.tiles, screen.books, strict=True):
        assert tile.label is not None
        assert tile.label.get_text() == book.title
        assert tile.path.is_file()


def test_a_long_shelf_pages_rather_than_growing(activity):
    win = window("shelf_paging")
    activity.window = win
    books = texts_for(activity.corpus, activity.ceiling)
    assert len(books) > 5, "this ceiling was chosen to need more than one page"
    screen = build_shelf(win, activity, books, lambda b: None)
    first = list(screen.books)
    screen.next_page()
    assert list(screen.books) != first
    screen.previous_page()
    assert list(screen.books) == first


def test_the_shelf_does_not_wrap_round(activity):
    """A shelf that wrapped would be one a child could walk round for ever
    without noticing they had seen everything."""
    win = window("shelf_ends")
    activity.window = win
    screen = build_shelf(win, activity, texts_for(activity.corpus, activity.ceiling), lambda b: None)
    assert not screen.back.get_sensitive()
    while screen.index < len(screen.pages) - 1:
        screen.next_page()
    assert not screen.forward.get_sensitive()
    screen.next_page()
    assert screen.index == len(screen.pages) - 1


def test_a_shelf_of_one_page_has_no_arrows_at_all(activity, corpus):
    win = window("shelf_one")
    activity.window = win
    books = texts_for(corpus, ceiling_for_grapheme(corpus, "d"))
    screen = build_shelf(win, activity, books, lambda b: None)
    assert screen.back is None and screen.forward is None


def test_the_shelf_prompt_says_what_to_do_and_names_no_book(activity):
    win = window("shelf_prompt")
    activity.window = win
    screen = build_shelf(win, activity, texts_for(activity.corpus, activity.ceiling), lambda b: None)
    assert screen.prompt.text == "Pick a book."
    screen.announce()
    assert win.speech.last_utterance == "Pick a book."


def test_the_books_are_in_the_keyboard_ring(activity):
    win = window("shelf_ring")
    activity.window = win
    screen = build_shelf(win, activity, texts_for(activity.corpus, activity.ceiling), lambda b: None)
    ring = win.keys.refresh()
    for tile in screen.tiles:
        assert tile in ring


def test_picking_a_book_opens_it(activity):
    win = window("shelf_pick")
    activity.window = win
    chosen = []
    screen = build_shelf(
        win, activity, texts_for(activity.corpus, activity.ceiling), chosen.append
    )
    screen.choose(screen.books[0])
    assert chosen == [screen.books[0]]


def test_the_shelf_never_offers_a_book_above_the_ceiling(activity, corpus):
    from sounds_and_words.ceiling import check_lines

    win = window("shelf_gate")
    activity.window = win
    screen = build_shelf(win, activity, texts_for(corpus, activity.ceiling), lambda b: None)
    for page in screen.pages:
        for book in page:
            assert check_lines(corpus, book.all_lines, activity.ceiling).allowed, book.slug


# --- the book ----------------------------------------------------------------


def test_a_book_opens_at_its_first_sentence(activity):
    _win, screen = reader(activity, "read_first")
    assert screen.index == 0
    assert screen.page.sentence == a_book(activity).lines[0]
    assert screen.line.get_text() == screen.page.sentence


def test_the_sentence_is_one_label_and_not_one_control_per_word(activity):
    """The finding, implemented. A child can tap any word as hard as they like
    and nothing happens, because there is nothing there to happen."""
    _win, screen = reader(activity, "read_no_hotspots")
    controls = [w for w in _walk(screen.body) if isinstance(w, ChildButton)]
    assert controls == []
    labels = [w for w in _walk(screen.body) if isinstance(w, Gtk.Label)]
    assert len(labels) == 1


def test_the_sentence_is_set_at_twenty_eight_points_or_more(activity):
    """Research 10 4.1 E asks for big; this is the text a child is decoding
    letter by letter, not a label they glance at."""
    _win, screen = reader(activity, "read_size")
    assert screen.points >= READING_MIN_PT


def test_the_picture_is_congruent_with_the_line_it_sits_over(activity):
    _win, screen = reader(activity, "read_picture")
    assert screen.page.picture == a_book(activity).pictures[0]
    assert illustration_for(screen.page.picture) is not None


def test_next_turns_the_page_and_back_comes_back(activity):
    _win, screen = reader(activity, "read_turn")
    first = screen.page.sentence
    screen.next_page()
    assert screen.index == 1
    assert screen.line.get_text() != first
    screen.previous_page()
    assert screen.index == 0
    assert screen.line.get_text() == first


def test_back_does_nothing_on_the_first_page(activity):
    _win, screen = reader(activity, "read_first_back")
    assert not screen.back.get_sensitive()
    screen.previous_page()
    assert screen.index == 0


def test_next_on_the_last_page_ends_the_book(activity):
    _win, screen = reader(activity, "read_last")
    for _ in range(len(a_book(activity)) - 1):
        screen.next_page()
    assert screen.page.last
    screen.next_page()
    assert screen.finished


def test_the_page_arrows_are_at_least_the_target_floor(activity):
    win, screen = reader(activity, "read_targets")
    for control in (screen.back, screen.forward, screen.listen):
        width, height = control.get_size_request()
        assert win.area.mm_of(width) >= 20.0
        assert win.area.mm_of(height) >= 20.0


def test_no_page_number_appears_anywhere_on_a_book(activity):
    """01 #19: no digits where a child can see them -- and a page count is a
    progress bar with a serif on it."""
    win, screen = reader(activity, "read_digits")
    for _ in range(len(a_book(activity))):
        text = " ".join(
            label.get_text() for label in _walk(win.content) if isinstance(label, Gtk.Label)
        )
        assert not any(character.isdigit() for character in text), text
        if not screen.page.last:
            screen.next_page()


# --- narration ---------------------------------------------------------------


def test_optional_narration_offers_a_button_and_stays_quiet(activity):
    win, screen = reader(activity, "read_optional", narration=Narration.OPTIONAL)
    assert screen.listen is not None
    win.speech.captions.lines.clear()
    screen.show_page(win)
    assert win.speech.captions.lines == []


def test_pressing_read_it_to_me_says_the_sentence(activity):
    win, screen = reader(activity, "read_button")
    screen.read_aloud()
    assert win.speech.last_utterance == screen.page.sentence


def test_the_caption_of_a_read_sentence_is_the_sentence(activity):
    """Everywhere else in kidnix a caption that repeated what is on screen
    would be redundant. Here the child is *reading* it, so the words being
    written down is the content."""
    win, screen = reader(activity, "read_caption")
    win.speech.captions.lines.clear()
    screen.read_aloud()
    assert win.speech.captions.lines == [screen.page.sentence]


def test_always_narration_reads_the_page_as_it_arrives(activity):
    win, screen = reader(activity, "read_always", narration=Narration.ALWAYS)
    assert win.speech.last_utterance == screen.page.sentence
    win.speech.captions.lines.clear()
    screen.next_page()
    assert win.speech.captions.lines == [screen.page.sentence]


def test_never_narration_offers_nothing_and_says_nothing(activity):
    win, screen = reader(activity, "read_never", narration=Narration.NEVER)
    assert screen.listen is None
    win.speech.captions.lines.clear()
    screen.read_aloud()
    screen.next_page()
    assert win.speech.captions.lines == []


def test_the_lit_word_is_marked_in_the_line_and_only_that_word(activity):
    _win, screen = reader(activity, "read_highlight")
    screen.highlight(1)
    markup = screen.markup()
    assert markup.count("<span background=") == 1
    assert screen.page.words[1] in markup
    assert screen.line.get_text() == screen.page.sentence


def test_the_highlight_has_a_span_for_every_written_word(activity):
    _win, screen = reader(activity, "read_spans")
    assert len(screen.spans()) == len(screen.page.words)


def test_turning_the_page_puts_the_highlight_out(activity):
    """A child who has turned the page is not waiting for the last one."""
    _win, screen = reader(activity, "read_highlight_cancel")
    screen.highlight(0)
    assert screen.lit == 0
    screen.next_page()
    assert screen.lit is None


def test_a_slower_voice_gets_a_slower_highlight_on_the_screen_too(activity):
    win, screen = reader(activity, "read_rate")
    normal = screen.spans()[-1].end_ms
    win.speech.apply_access(win.speech.access.with_overrides(speech_rate=-90))
    assert screen.spans()[-1].end_ms > normal


# --- the end of a book -------------------------------------------------------


def finish_book(activity, name, slug="ducks-at-the-pond", on_done=None):
    win, screen = reader(activity, name, slug=slug, on_done=on_done)
    for _ in range(len(a_book(activity, slug))):
        screen.next_page()
    return win, screen


def test_the_end_of_a_book_hands_it_to_a_person(activity):
    win, _screen = finish_book(activity, "read_end")
    cards = [w for w in _walk(win.content) if isinstance(w, GrownUpTurn)]
    assert len(cards) == 1
    assert "read it to you" in cards[0].body_text


def test_the_end_says_read_it_to_someone(activity):
    win, _screen = finish_book(activity, "read_end_line")
    assert win.speech.last_utterance == "Read it to someone!"


def test_the_end_keeps_a_card_naming_the_book(activity):
    _win, _screen = finish_book(activity, "read_end_card")
    kept = activity.app.saved
    assert len(kept) == 1
    assert kept[0]["kind"] == "read"
    assert kept[0]["caption"] == "I read: ducks at the pond"
    assert kept[0]["files"][0].is_file()
    assert kept[0]["meta"]["phase"] == 2
    assert "ducks" in kept[0]["meta"]["words"]


def test_a_book_nobody_finished_keeps_nothing(activity):
    """A card saying "I read: ..." about a book a child stopped halfway
    through would be a lie about a person."""
    _win, screen = reader(activity, "read_half")
    screen.next_page()
    assert activity.app.saved == []


def test_reading_the_same_book_twice_keeps_one_card(activity):
    _win, _screen = finish_book(activity, "read_twice")
    activity.keep_reading(a_book(activity))
    assert len(activity.app.saved) == 1


def test_the_next_button_at_the_end_moves_the_session_on(activity):
    moved = []
    _win, screen = finish_book(activity, "read_onwards", on_done=lambda: moved.append(True))
    screen._onwards()
    assert moved == [True]


# --- the loop ----------------------------------------------------------------


def test_the_session_ends_with_a_book(activity):
    win = window("loop_read")
    activity.build(win)
    kinds = []
    while activity.runner.current is not None:
        kinds.append(activity.runner.current.kind)
        activity.next_item()
    assert kinds[-1] is ItemKind.READ_TEXT


def test_read_it_opens_on_the_book_the_schedule_picked(activity):
    win = window("loop_shelf")
    activity.window = win
    item = next(i for i in activity.plan.items if i.kind is ItemKind.READ_TEXT)
    activity.show_read_text(item)
    assert isinstance(activity.screen, BookShelf)
    assert activity.screen.books[0].slug == item.payload


def test_opening_a_book_from_the_shelf_starts_at_page_one(activity):
    win = window("loop_open")
    activity.window = win
    activity.open_book(a_book(activity))
    assert isinstance(activity.screen, ReadIt)
    assert activity.screen.index == 0
