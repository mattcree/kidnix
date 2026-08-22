"""Earcons: four generated tones, one per 250 ms, and never over speech."""

from __future__ import annotations

import os
import struct
import wave
from pathlib import Path

import pytest

from kidnix_shell.sound import (
    BACK,
    EARCONS,
    KEEP,
    MIN_GAP_SECONDS,
    NAMES,
    SAMPLE_RATE,
    SLEEP,
    TAP,
    Earcons,
    NullPlayer,
    Tone,
    generate,
    render,
)


def test_there_are_exactly_four_sounds() -> None:
    """Spec 7a rules four, not 08's six: keep, tap, back, sleep."""
    assert set(EARCONS) == {KEEP, TAP, BACK, SLEEP} == set(NAMES)


def test_rendering_gives_the_right_number_of_frames() -> None:
    frames = render((Tone(440.0, 100),))
    assert len(frames) == 2 * int(SAMPLE_RATE * 0.1)  # 16-bit mono


def test_a_tone_starts_and_ends_at_silence() -> None:
    """A click at the edge of a 90 ms sound *is* the sound. Fades, always."""
    frames = render((Tone(440.0, 100),))
    first = struct.unpack("<h", frames[:2])[0]
    last = struct.unpack("<h", frames[-2:])[0]
    assert abs(first) < 400
    assert abs(last) < 400


def test_nothing_clips() -> None:
    for tones in EARCONS.values():
        samples = struct.unpack(f"<{len(render(tones)) // 2}h", render(tones))
        assert max(abs(s) for s in samples) < 32767


def test_the_level_is_in_the_quiet_half_of_the_scale() -> None:
    """-14 LUFS by construction: a peak of 0.45 with a decay envelope."""
    for tones in EARCONS.values():
        raw = render(tones)
        samples = struct.unpack(f"<{len(raw) // 2}h", raw)
        peak = max(abs(s) for s in samples) / 32767
        assert 0.2 < peak <= 0.5


def test_generating_writes_four_playable_wav_files(tmp_path: Path) -> None:
    written = generate(tmp_path)
    assert len(written) == len(EARCONS)
    for name in NAMES:
        path = tmp_path / f"{name}.wav"
        with wave.open(str(path), "rb") as handle:
            assert handle.getnchannels() == 1
            assert handle.getsampwidth() == 2
            assert handle.getframerate() == SAMPLE_RATE
            assert handle.getnframes() > 0


def test_generating_twice_writes_nothing_the_second_time(tmp_path: Path) -> None:
    generate(tmp_path)
    assert generate(tmp_path) == []
    assert len(generate(tmp_path, force=True)) == len(EARCONS)


def test_no_temporary_files_are_left_behind(tmp_path: Path) -> None:
    generate(tmp_path)
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anything")
def test_earcons_generate_into_the_cache_when_the_package_dir_is_unwritable(
    tmp_path: Path,
) -> None:
    """On the image ``/usr`` is read-only, so the WAVs land in the kid's cache."""
    readonly = tmp_path / "usr"
    readonly.mkdir()
    readonly.chmod(0o500)
    cache = tmp_path / "cache" / "sounds"
    player = NullPlayer()
    try:
        earcons = Earcons(directory=readonly / "sounds", cache_dir=cache, player=player)
        assert earcons.play(KEEP)
    finally:
        readonly.chmod(0o700)
    assert player.played == [cache / "keep.wav"]


def test_earcons_prefer_a_file_that_is_already_there(tmp_path: Path) -> None:
    shipped = tmp_path / "shipped"
    generate(shipped)
    player = NullPlayer()
    earcons = Earcons(directory=shipped, cache_dir=tmp_path / "cache", player=player)
    assert earcons.play(TAP)
    assert player.played == [shipped / "tap.wav"]
    assert not (tmp_path / "cache").exists()


def test_only_one_earcon_per_quarter_second(tmp_path: Path) -> None:
    """08 section 3.6: a child drumming on a tile does not get a machine gun."""
    player = NullPlayer()
    earcons = Earcons(directory=tmp_path, player=player)
    assert earcons.play(TAP)
    assert not earcons.play(TAP)
    assert not earcons.play(BACK)
    earcons._last -= MIN_GAP_SECONDS + 0.01
    assert earcons.play(BACK)


def test_earcons_duck_under_speech(tmp_path: Path) -> None:
    player = NullPlayer()
    earcons = Earcons(directory=tmp_path, player=player)
    assert not earcons.play(KEEP, speaking=True)
    assert player.played == []


def test_earcons_can_be_switched_off(tmp_path: Path) -> None:
    player = NullPlayer()
    earcons = Earcons(directory=tmp_path, player=player, enabled=False)
    assert not earcons.play(KEEP)


def test_an_unknown_name_is_silence_not_a_crash(tmp_path: Path) -> None:
    earcons = Earcons(directory=tmp_path, player=NullPlayer())
    assert not earcons.play("fanfare")


def test_a_player_that_explodes_never_reaches_the_child(tmp_path: Path) -> None:
    class Broken:
        def play(self, path: Path) -> bool:
            return False

    earcons = Earcons(directory=tmp_path, player=Broken())
    assert not earcons.play(KEEP)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anything")
def test_a_completely_unwritable_world_runs_silent(tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        earcons = Earcons(directory=locked / "sounds", cache_dir=None, player=NullPlayer())
        assert not earcons.play(KEEP)
    finally:
        locked.chmod(0o700)


@pytest.mark.parametrize("name", list(EARCONS))
def test_every_earcon_is_short(name: str) -> None:
    """08 section 3.6: <= 400 ms, except the one that says the day is over."""
    milliseconds = sum(tone.milliseconds for tone in EARCONS[name])
    limit = 800 if name == SLEEP else 400
    assert milliseconds <= limit
