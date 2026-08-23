""" "Tell me about it" -- the twenty-second voice note (spec 7d #9).

All of it with a :class:`~kidnix_shell.voice.FakeRecorder`: no microphone, no
GStreamer, no audio hardware. What is under test is the *behaviour the child
meets* -- one press starts, a second stops, twenty seconds stops it anyway,
the meter runs while it runs, the note lands beside the drawing, and a machine
with no microphone offers nothing at all.
"""

from __future__ import annotations

from pathlib import Path

from kidnix_shell.speech import FakeScheduler
from kidnix_shell.voice import (
    MAX_SECONDS,
    NOTE_NAME,
    FakeRecorder,
    NullRecorder,
    VoiceNote,
    has_note,
    note_path,
)


class FakePlayer:
    """Stands in for ``sound.GstPlayer``: records what it was asked to play."""

    def __init__(self) -> None:
        self.played: list[Path] = []

    def play(self, path: Path) -> bool:
        self.played.append(path)
        return True

    def close(self) -> None:
        pass


def make(available: bool = True) -> tuple[VoiceNote, FakeRecorder, FakeScheduler, FakePlayer]:
    recorder = FakeRecorder(available=available)
    scheduler = FakeScheduler()
    player = FakePlayer()
    return (
        VoiceNote(recorder=recorder, scheduler=scheduler, player=player),
        recorder,
        scheduler,
        player,
    )


# --- where a note lives --------------------------------------------------


def test_a_note_lives_beside_the_drawing_it_is_about(tmp_path: Path) -> None:
    """Beside ``entry.json`` and ``v001.png``, so one export takes both.

    ``kidnix-export`` tars ``~/.local/share/kidnix`` whole and ``kidnix-wipe``
    deletes it whole, so putting the note anywhere else would be a file the
    child's data exit does not know about.
    """
    entry = tmp_path / "2026" / "08" / "23" / "tuxpaint-140102-ab12"
    assert note_path(entry) == entry / NOTE_NAME
    assert NOTE_NAME.endswith(".ogg")
    assert not has_note(entry)
    entry.mkdir(parents=True)
    (entry / NOTE_NAME).write_bytes(b"OggS...")
    assert has_note(entry)


def test_an_empty_file_is_not_a_note(tmp_path: Path) -> None:
    """A recording that never got any audio must not put an ear on a card."""
    (tmp_path / NOTE_NAME).write_bytes(b"")
    assert not has_note(tmp_path)
    assert not has_note(None)


# --- one press, then another ---------------------------------------------


def test_one_press_starts_and_a_second_stops(tmp_path: Path) -> None:
    note, recorder, _scheduler, _player = make()
    states: list[bool] = []
    note.on_state = states.append

    assert note.toggle(tmp_path) is True
    assert note.recording
    assert recorder.started == [tmp_path / NOTE_NAME]

    assert note.toggle(tmp_path) is False
    assert not note.recording
    assert has_note(tmp_path)
    assert states == [True, False]


def test_it_stops_itself_after_twenty_seconds(tmp_path: Path) -> None:
    """The ceiling is the point: a forgotten recording is not an afternoon."""
    note, _recorder, scheduler, _player = make()
    note.start(tmp_path)
    scheduler.advance(int(MAX_SECONDS * 1000) - 1)
    assert note.recording
    scheduler.advance(2)
    assert not note.recording
    assert has_note(tmp_path)


def test_the_meter_runs_while_it_records_and_stops_when_it_does(tmp_path: Path) -> None:
    """The only thing that tells a pre-reader "it is listening" is this."""
    note, recorder, scheduler, _player = make()
    levels: list[float] = []
    note.on_level = levels.append

    note.start(tmp_path)
    recorder.level = 0.7
    scheduler.advance(100)
    scheduler.advance(100)
    assert levels[:2] == [0.7, 0.7]

    note.stop()
    assert levels[-1] == 0.0
    before = len(levels)
    scheduler.advance(1000)
    assert len(levels) == before  # the polling stopped with the recording


def test_the_meter_is_clamped_whatever_the_recorder_says(tmp_path: Path) -> None:
    note, recorder, scheduler, _player = make()
    levels: list[float] = []
    note.on_level = levels.append
    note.start(tmp_path)
    recorder.level = 4.2
    scheduler.advance(100)
    recorder.level = -1.0
    scheduler.advance(100)
    assert levels[:2] == [1.0, 0.0]


def test_stopping_hands_back_the_path_and_announces_it(tmp_path: Path) -> None:
    note, _recorder, _scheduler, _player = make()
    saved: list[Path] = []
    note.on_saved = saved.append
    note.start(tmp_path)
    assert note.stop() == tmp_path / NOTE_NAME
    assert saved == [tmp_path / NOTE_NAME]


def test_stopping_when_nothing_is_recording_is_a_no_op(tmp_path: Path) -> None:
    """Back, the ritual moving on, and shutdown all reach this."""
    note, _recorder, _scheduler, _player = make()
    assert note.stop() is None
    assert not has_note(tmp_path)


# --- a second recording replaces the first -------------------------------


def test_recording_again_replaces_the_note_and_is_counted(tmp_path: Path) -> None:
    """No retakes UI: the second recording simply is the note now.

    The count exists only so the screen can say one quiet "Again?" -- asking a
    five-year-old to judge their own recording is a different product.
    """
    note, _recorder, _scheduler, _player = make()
    note.start(tmp_path)
    note.stop()
    assert note.retakes == 0

    note.start(tmp_path)
    note.stop()
    assert note.retakes == 1
    assert len(list(tmp_path.glob("*.ogg"))) == 1


# --- playback ------------------------------------------------------------


def test_playing_back_needs_a_note_to_play(tmp_path: Path) -> None:
    note, _recorder, _scheduler, player = make()
    assert note.play(tmp_path) is False
    assert player.played == []

    note.start(tmp_path)
    note.stop()
    assert note.play(tmp_path) is True
    assert player.played == [tmp_path / NOTE_NAME]


# --- no microphone -------------------------------------------------------


def test_a_machine_with_no_microphone_offers_nothing(tmp_path: Path) -> None:
    """**Degrade silently.** A mic button that does nothing teaches a child
    that buttons lie, which is why spec 7a took Ask out of the band."""
    note, _recorder, _scheduler, _player = make(available=False)
    assert not note.available
    assert note.start(tmp_path) is False
    assert not note.recording
    assert not has_note(tmp_path)


def test_the_null_recorder_is_never_available_and_never_raises(tmp_path: Path) -> None:
    note = VoiceNote(recorder=NullRecorder("no GStreamer"), scheduler=FakeScheduler())
    assert not note.available
    assert note.toggle(tmp_path) is False
    assert note.stop() is None
    note.close()


def test_closing_stops_a_running_recording(tmp_path: Path) -> None:
    """Shutdown mid-note must close the file, not truncate it."""
    note, recorder, _scheduler, _player = make()
    note.start(tmp_path)
    note.close()
    assert recorder.closed
    assert not note.recording
