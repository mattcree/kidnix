"""Earcons: five generated sounds, one per 250 ms, and never over speech.

Spec 7a as revised by 7b: four of the five are now **auditory icons** -- they
imitate an everyday sound rather than encoding a musical interval -- and all
five are <= 400 ms and normalised.
"""

from __future__ import annotations

import os
import struct
import wave
from pathlib import Path

import pytest

from kidnix_shell.sound import (
    ATTACK_FLOOR_MS,
    BACK,
    EARCONS,
    GLIDE,
    KEEP,
    MAX_EARCON_MS,
    MIN_GAP_SECONDS,
    NAMES,
    NOISE,
    PEAK,
    PHASE,
    SAMPLE_RATE,
    SLEEP,
    TAP,
    TONE,
    Earcon,
    Earcons,
    Layer,
    NullPlayer,
    generate,
    mix,
    render,
    with_attack_floor,
)


def samples(name: str) -> list[float]:
    return mix(EARCONS[name])


def test_there_are_exactly_five_sounds() -> None:
    """Spec 7a ruled four; the CCI audit restored 08 section 3.6b's fifth.

    The sixth, *ask sent*, still waits for the Ask queue.
    """
    assert set(EARCONS) == {KEEP, TAP, BACK, PHASE, SLEEP} == set(NAMES)


# --- the representational turn (spec 7b, 09 section 10 #7) ----------------


@pytest.mark.parametrize("name", [KEEP, TAP, BACK, SLEEP])
def test_the_four_with_referents_say_what_they_imitate(name: str) -> None:
    """Jacko 1997: recognition rides on everyday-sound exposure, not intervals.

    The referent is data, not a comment, so the honesty note in the module
    docstring cannot drift away from the sound it describes.
    """
    referent = EARCONS[name].referent
    assert referent and "none" not in referent


def test_the_one_without_a_referent_says_so() -> None:
    """ "The session moved on" is not a thing that makes a noise."""
    assert EARCONS[PHASE].referent.startswith("none")
    assert all(layer.kind == TONE for layer in EARCONS[PHASE].layers)


def test_keep_is_noise_not_a_chord() -> None:
    """Paper rustling: several bursts of filtered noise, none of them a note."""
    layers = EARCONS[KEEP].layers
    assert len(layers) >= 4
    assert all(layer.kind == NOISE for layer in layers)
    assert all(layer.highpass_hz > 0 and layer.shimmer_hz > 0 for layer in layers)
    # Staggered, not simultaneous: a rustle is a sequence of small events.
    starts = [layer.start_ms for layer in layers]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)


def test_back_is_two_knocks() -> None:
    """A soft door. Two transients, each a click over a low resonance."""
    layers = EARCONS[BACK].layers
    knock_starts = sorted({layer.start_ms for layer in layers})
    assert len(knock_starts) == 2
    lows = [layer for layer in layers if layer.kind == TONE and layer.frequency < 250]
    assert len(lows) == 2
    assert any(layer.kind == NOISE for layer in layers)
    # The second knock is the quieter one: a knock is not an alarm.
    first, second = knock_starts
    quiet = max(layer.level for layer in layers if layer.start_ms == second)
    loud = max(layer.level for layer in layers if layer.start_ms == first)
    assert quiet < loud


def test_sleep_is_a_yawn_shaped_downward_glide() -> None:
    layers = EARCONS[SLEEP].layers
    glides = [layer for layer in layers if layer.kind == GLIDE]
    assert glides, "a yawn is a glide, not a pair of notes"
    for glide in glides:
        assert glide.frequency_end is not None
        assert glide.frequency_end < glide.frequency, "it falls"
        assert glide.attack_ms >= 60, "a yawn opens slowly"
    assert any(layer.kind == NOISE for layer in layers), "and it is breathy"


def test_tap_is_the_shortest_thing_in_the_shell() -> None:
    assert EARCONS[TAP].milliseconds <= 100
    assert any(layer.kind == NOISE for layer in EARCONS[TAP].layers)


def test_the_phase_motif_is_still_the_quietest_of_the_five() -> None:
    """ "The light changed" is news about the room, not about the child."""
    for name in (KEEP, TAP, BACK, SLEEP):
        assert EARCONS[PHASE].level < EARCONS[name].level, name


# --- rendering ------------------------------------------------------------


@pytest.mark.parametrize("name", list(EARCONS))
def test_every_earcon_renders(name: str) -> None:
    """The rendered length is the length *after* the attack floor is applied.

    ``mix`` runs :func:`with_attack_floor` first, so the declared earcon and
    the one that reaches a speaker are not the same object -- and it is the
    one that reaches the speaker that has to be the right length.
    """
    played = with_attack_floor(EARCONS[name])
    frames = render(EARCONS[name])
    assert frames
    assert len(frames) % 2 == 0
    expected = int(SAMPLE_RATE * played.milliseconds / 1000.0)
    assert len(frames) // 2 == pytest.approx(expected, abs=2)


@pytest.mark.parametrize("name", list(EARCONS))
def test_every_earcon_fades_in_over_at_least_150_ms(name: str) -> None:
    """06 section 7.4 #26 / panel ruling 7d #7 -- and #39's measurement.

    "Sudden unexpected sound is the most frequently identified auditory
    sensory trigger" for autistic children, and four of the five earcons used
    to attack in 0.4-4.0 ms. Every layer of every earcon now has a real
    fade-in, and every layer is long enough to *have* one.
    """
    played = with_attack_floor(EARCONS[name])
    for layer in played.layers:
        assert layer.attack_ms >= ATTACK_FLOOR_MS, (name, layer.kind)
        assert layer.milliseconds >= ATTACK_FLOOR_MS, (name, layer.kind)


@pytest.mark.parametrize("name", list(EARCONS))
def test_every_earcon_is_short(name: str) -> None:
    """08 section 3.6's ceiling, moved by exactly the fade-in it now has."""
    assert with_attack_floor(EARCONS[name]).milliseconds <= MAX_EARCON_MS


@pytest.mark.parametrize("name", list(EARCONS))
def test_every_earcon_is_normalised(name: str) -> None:
    """A noise burst and a sine have nothing in common until this makes them.

    The peak lands exactly on ``PEAK * level``, so the five sit at a designed
    loudness relative to each other rather than at an arithmetic accident.
    """
    peak = max(abs(value) for value in samples(name))
    assert peak == pytest.approx(PEAK * EARCONS[name].level, rel=1e-6)


@pytest.mark.parametrize("name", list(EARCONS))
def test_nothing_clips(name: str) -> None:
    raw = render(EARCONS[name])
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    assert max(abs(value) for value in values) < 32767


@pytest.mark.parametrize("name", list(EARCONS))
def test_every_earcon_starts_and_ends_at_silence(name: str) -> None:
    """A click at the edge of a 90 ms sound *is* the sound. Fades, always."""
    raw = render(EARCONS[name])
    first = struct.unpack("<h", raw[:2])[0]
    last = struct.unpack("<h", raw[-2:])[0]
    assert abs(first) < 400
    assert abs(last) < 400


def test_the_level_is_in_the_quiet_half_of_the_scale() -> None:
    """-14 LUFS by construction. Nothing here was measured with a meter."""
    for name in NAMES:
        peak = max(abs(value) for value in samples(name))
        assert 0.2 < peak <= 0.5


def test_synthesis_is_deterministic() -> None:
    """Noise with a fixed seed: the same source always makes the same WAV."""
    for name in NAMES:
        assert render(EARCONS[name]) == render(EARCONS[name])


def test_a_silent_earcon_does_not_divide_by_zero() -> None:
    quiet = Earcon(name="quiet", layers=(Layer(kind=TONE, milliseconds=10.0, level=0.0),))
    assert set(mix(quiet)) == {0.0}


# --- files ----------------------------------------------------------------


def test_generating_writes_five_playable_wav_files(tmp_path: Path) -> None:
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
