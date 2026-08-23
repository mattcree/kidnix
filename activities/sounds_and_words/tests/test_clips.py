"""The clip player, with a fake GStreamer.

``sounds_and_words.clips`` is the answer to the checkpoint-2 audit's item 6:
until it existed, the day somebody recorded a real /s/ the activity would have
failed as a **missing player** rather than as a wrong sound. It is the one
module here that touches an audio device, so none of these tests goes near one
-- the element and the ``Gst`` namespace are both fakes, which is also the only
way to assert the thing that matters most: *a new sound cancels the old one.*
"""

from __future__ import annotations

from pathlib import Path

from sounds_and_words.clips import (
    ClipPlayer,
    GstClipPlayer,
    NullClipPlayer,
    make_player,
)

# --- the fakes --------------------------------------------------------------


class FakeState:
    NULL = "NULL"
    PLAYING = "PLAYING"


class FakeStateChangeReturn:
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"


class FakeGst:
    State = FakeState
    StateChangeReturn = FakeStateChangeReturn

    @staticmethod
    def filename_to_uri(path: str) -> str:
        return f"file://{path}"


class FakeBus:
    def __init__(self) -> None:
        self.watched = False
        self.connected: list[str] = []

    def add_signal_watch(self) -> None:
        self.watched = True

    def connect(self, signal: str, _callback) -> None:
        self.connected.append(signal)


class FakeElement:
    """One playbin, with its state changes written down."""

    def __init__(self, *, fail: bool = False) -> None:
        self.bus = FakeBus()
        self.states: list[str] = []
        self.props: dict[str, object] = {}
        self.fail = fail

    def get_bus(self) -> FakeBus:
        return self.bus

    def set_state(self, state: str) -> str:
        self.states.append(state)
        if state == FakeState.PLAYING and self.fail:
            return FakeStateChangeReturn.FAILURE
        return FakeStateChangeReturn.SUCCESS

    def set_property(self, name: str, value: object) -> None:
        self.props[name] = value


def player(**kwargs) -> tuple[GstClipPlayer, FakeElement]:
    element = FakeElement(**kwargs)
    return GstClipPlayer(element, FakeGst), element


# --- playing ----------------------------------------------------------------


def test_a_clip_is_played_from_its_file(tmp_path):
    clip = tmp_path / "s.ogg"
    clip.write_bytes(b"OggS")
    made, element = player()
    assert made.play(clip) is True
    assert element.props["uri"] == f"file://{clip}"
    assert element.states[-1] == FakeState.PLAYING


def test_a_new_sound_cancels_the_old_one(tmp_path):
    """One voice (08 section 3.6). A child sweeping four tiles must not build
    up four phonemes they have to wait out."""
    made, element = player()
    made.play(tmp_path / "a.ogg")
    made.play(tmp_path / "t.ogg")
    # NULL, PLAYING, NULL, PLAYING -- the second sound goes back to NULL first.
    assert element.states == [
        FakeState.NULL,
        FakeState.PLAYING,
        FakeState.NULL,
        FakeState.PLAYING,
    ]
    assert element.props["uri"].endswith("t.ogg")


def test_the_volume_is_the_parents_and_is_clamped(tmp_path):
    made, element = player()
    made.play(tmp_path / "s.ogg", volume=0.4)
    assert element.props["volume"] == 0.4
    made.play(tmp_path / "s.ogg", volume=7.0)
    assert element.props["volume"] == 1.0
    made.play(tmp_path / "s.ogg", volume=-1.0)
    assert element.props["volume"] == 0.0


def test_a_sink_that_refuses_is_not_an_exception(tmp_path):
    """Every failure path ends in "say the label instead", never in a
    traceback in front of a five-year-old."""
    made, element = player(fail=True)
    assert made.play(tmp_path / "s.ogg") is False
    assert element.states[-1] == FakeState.NULL


def test_the_end_of_a_clip_puts_it_back_to_null(tmp_path):
    made, element = player()
    made.play(tmp_path / "s.ogg")
    made._done(None, None)
    assert element.states[-1] == FakeState.NULL


def test_closing_is_idempotent_and_stops_playing(tmp_path):
    made, element = player()
    made.play(tmp_path / "s.ogg")
    made.close()
    made.close()
    assert element.states[-1] == FakeState.NULL
    assert made.play(tmp_path / "s.ogg") is False


def test_the_bus_is_watched_for_the_two_things_that_end_a_clip():
    _made, element = player()
    assert element.bus.watched
    assert element.bus.connected == ["message::eos", "message::error"]


# --- no player at all -------------------------------------------------------


def test_the_null_player_plays_nothing_and_says_so(tmp_path, caplog):
    made = NullClipPlayer("no GStreamer here")
    with caplog.at_level("INFO"):
        assert made.play(tmp_path / "s.ogg") is False
    assert made.played == [tmp_path / "s.ogg"]
    assert "no GStreamer here" in caplog.text


def test_the_null_player_only_complains_once(tmp_path, caplog):
    """A child pressing a tile eleven times must not fill the journal with the
    same line eleven times."""
    made = NullClipPlayer("nope")
    with caplog.at_level("INFO"):
        for _ in range(5):
            made.play(tmp_path / "s.ogg")
    assert caplog.text.count("nope") == 1
    assert len(made.played) == 5


def test_the_null_player_answers_the_whole_protocol():
    made = NullClipPlayer()
    made.stop()
    made.close()
    assert isinstance(made, ClipPlayer)


# --- choosing one -----------------------------------------------------------


def test_a_factory_is_what_the_tests_inject():
    fake = NullClipPlayer("injected")
    assert make_player(factory=lambda: fake) is fake


def test_a_factory_that_cannot_build_one_still_returns_a_player():
    made = make_player(factory=lambda: None)
    assert isinstance(made, NullClipPlayer)
    assert "declined" in made.reason


def test_asking_this_machine_for_a_player_never_raises():
    """Whatever is or is not installed, an activity gets an object with a
    ``play`` on it. Nothing here plays anything."""
    made = make_player()
    assert isinstance(made, ClipPlayer)
    made.close()


def test_a_clip_path_is_a_path_not_a_string(tmp_path):
    made = NullClipPlayer()
    made.play(str(tmp_path / "s.ogg"))
    assert made.played == [Path(tmp_path / "s.ogg")]
