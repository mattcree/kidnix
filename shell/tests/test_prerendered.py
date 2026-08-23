"""The pre-rendered catalogue: lookup, fallback, cancel, and the rate gate.

Headless throughout -- no GTK, no GStreamer, no speech-dispatcher, and above
all **no sound**: every test here drives :class:`NullClipPlayer` and
:class:`kidnix_shell.speech.FakeBackend`, so the suite can run on a developer's
own desktop without the machine talking to the room (AGENTS.md 5).

The thing being protected is the fallback. Every fault in this subsystem is
inaudible -- a missing clip, a missing index, a rate the catalogue cannot serve
-- because each one ends at the backend that spoke before the catalogue
existed. That is exactly why it needs tests: nothing else would ever notice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kidnix_shell.prerendered import (
    PLAYED_LOG,
    SUPPORTED_VERSION,
    Catalogue,
    NullClipPlayer,
    PrerenderedVoice,
    load_catalogue,
    normalise_language,
    select_prerendered,
)
from kidnix_shell.speech import FakeBackend, FakeScheduler, SpeechManager

GREETING = "Who's here?"
TILE = "Potato faces"

#: The rate `shell/kidnix_shell/access.py` ships, and the one
#: `build_files/66-prerender-speech.sh` renders for.
RENDERED_RATE = -20


def write_catalogue(
    root: Path,
    language: str = "en_GB",
    texts: tuple[str, ...] = (GREETING, TILE),
    *,
    version: int = SUPPORTED_VERSION,
    rate: int = RENDERED_RATE,
    write_files: bool = True,
) -> Path:
    """A catalogue on disk, shaped exactly as the build stage writes one."""
    directory = root / language
    directory.mkdir(parents=True, exist_ok=True)
    clips = {}
    for index, text in enumerate(texts):
        name = f"{index:040x}.ogg"
        clips[text] = {"file": name, "ms": 900}
        if write_files:
            (directory / name).write_bytes(b"OggS-not-really-but-nothing-decodes-it-here")
    (directory / "index.json").write_text(
        json.dumps(
            {
                "version": version,
                "language": language,
                "voice": "bf_emma",
                "engine": "kokoro-82m-v1.0",
                "speed": 0.9091,
                "sample_rate": 24000,
                "speechd_rate": rate,
                "clips": clips,
            }
        )
    )
    return directory


@pytest.fixture
def voice(tmp_path: Path) -> PrerenderedVoice:
    write_catalogue(tmp_path)
    return PrerenderedVoice(root=tmp_path, language="en-GB", player=NullClipPlayer())


# --- the index ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "want"),
    [("en-GB", "en_GB"), ("en_gb", "en_GB"), ("EN-gb", "en_GB"), ("cy", "cy"), ("", "")],
)
def test_language_tags_normalise_to_the_directory_on_disk(given: str, want: str) -> None:
    # speech-dispatcher says `en-GB` and gettext says `en_GB`; the shell passes
    # whichever it happens to have.
    assert normalise_language(given) == want


def test_catalogue_loads(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    catalogue = load_catalogue(tmp_path, "en-GB")
    assert catalogue is not None
    assert catalogue.voice == "bf_emma"
    assert catalogue.speechd_rate == RENDERED_RATE
    assert set(catalogue.clips) == {GREETING, TILE}


def test_a_missing_index_is_not_an_error(tmp_path: Path) -> None:
    assert load_catalogue(tmp_path, "en-GB") is None
    assert select_prerendered(root=tmp_path, language="en-GB") is None


def test_an_index_from_the_future_is_ignored_rather_than_half_read(tmp_path: Path) -> None:
    # A rolled-back shell must not guess at a newer build's schema.
    write_catalogue(tmp_path, version=SUPPORTED_VERSION + 1)
    assert load_catalogue(tmp_path, "en-GB") is None


def test_a_corrupt_index_falls_back_rather_than_raising(tmp_path: Path) -> None:
    directory = tmp_path / "en_GB"
    directory.mkdir(parents=True)
    (directory / "index.json").write_text("{not json")
    assert load_catalogue(tmp_path, "en-GB") is None


def test_another_language_finds_nothing(tmp_path: Path) -> None:
    # Kokoro v1.0 has no Welsh voice, so a Welsh profile must fall through to
    # Piper/espeak-ng for everything rather than hear English vowels.
    write_catalogue(tmp_path)
    assert load_catalogue(tmp_path, "cy") is None


# --- lookup and fallback ------------------------------------------------------


def test_an_exact_hit_plays_the_clip(voice: PrerenderedVoice) -> None:
    assert voice.speak(GREETING) is True
    assert voice.hits == 1
    assert len(voice.player.played) == 1


def test_lookup_is_exact_text_and_nothing_cleverer(voice: PrerenderedVoice) -> None:
    # No normalisation, no case folding, no punctuation stripping. A near-miss
    # is a miss: a clip that says something slightly different is worse than
    # the ordinary voice saying the right thing.
    near_misses = ("who's here?", "Who's here", " Who's here?", "Who\u2019s here?")
    for near_miss in near_misses:
        assert voice.speak(near_miss) is False
    assert voice.hits == 0
    assert voice.misses == 4


def test_a_clip_whose_file_vanished_is_a_miss(tmp_path: Path) -> None:
    write_catalogue(tmp_path, write_files=False)
    voice = PrerenderedVoice(root=tmp_path, language="en-GB", player=NullClipPlayer())
    assert voice.speak(GREETING) is False


def test_a_player_that_refuses_is_a_miss(tmp_path: Path) -> None:
    class Refuses(NullClipPlayer):
        def play(self, path: Path) -> bool:
            return False

    write_catalogue(tmp_path)
    voice = PrerenderedVoice(root=tmp_path, language="en-GB", player=Refuses())
    assert voice.speak(GREETING) is False
    assert voice.misses == 1


# --- the rate gate ------------------------------------------------------------


def test_the_shipped_rate_keeps_the_catalogue_on(voice: PrerenderedVoice) -> None:
    voice.set_rate(RENDERED_RATE)
    assert voice.usable is True
    assert voice.speak(GREETING) is True


def test_calm_mode_switches_the_catalogue_off(voice: PrerenderedVoice) -> None:
    # A recording has one tempo. `[access] speech_rate` and calm mode are
    # settings a parent made for their child, and they win over the voice.
    voice.set_rate(-35)
    assert voice.usable is False
    assert voice.speak(GREETING) is False


def test_going_back_to_the_shipped_rate_switches_it_on_again(voice: PrerenderedVoice) -> None:
    voice.set_rate(-35)
    voice.set_rate(RENDERED_RATE)
    assert voice.speak(GREETING) is True


def test_a_profile_switch_drops_the_catalogue(voice: PrerenderedVoice) -> None:
    voice.set_language("cy")
    assert voice.catalogue is None
    assert voice.speak(GREETING) is False


# --- cancel -------------------------------------------------------------------


def test_cancel_stops_the_clip(voice: PrerenderedVoice) -> None:
    voice.speak(GREETING)
    voice.cancel()
    assert voice.player.cancels == 1


def test_cancel_never_raises_even_with_a_broken_player(tmp_path: Path) -> None:
    class Explodes(NullClipPlayer):
        def cancel(self) -> None:
            raise RuntimeError("the sink went away")

    write_catalogue(tmp_path)
    PrerenderedVoice(root=tmp_path, language="en-GB", player=Explodes()).cancel()


# --- the hook in SpeechManager ------------------------------------------------


def manager(root: Path) -> tuple[SpeechManager, FakeBackend, PrerenderedVoice]:
    """A real SpeechManager with a fake mouth on both halves."""
    backend = FakeBackend()
    voice = PrerenderedVoice(root=root, language="en-GB", player=NullClipPlayer())
    return (
        SpeechManager(backend=backend, scheduler=FakeScheduler(), prerendered=voice),
        backend,
        voice,
    )


def test_a_hit_plays_the_clip_instead_of_the_backend(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    speech, backend, voice = manager(tmp_path)
    assert speech.speak(GREETING) is True
    assert backend.spoken == []
    assert voice.hits == 1


def test_a_miss_goes_to_the_backend_untouched(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    speech, backend, _voice = manager(tmp_path)
    assert speech.speak("You drew two pictures today.") is True
    assert backend.spoken == ["You drew two pictures today."]


def test_no_catalogue_at_all_is_exactly_todays_behaviour(tmp_path: Path) -> None:
    backend = FakeBackend()
    speech = SpeechManager(backend=backend, scheduler=FakeScheduler(), prerendered=None)
    assert speech.speak(GREETING) is True
    assert backend.spoken == [GREETING]


def test_captions_and_the_ear_are_unchanged_by_a_hit(tmp_path: Path) -> None:
    # The whole claim of the hook: it changes *who makes the sound* and nothing
    # else. The caption, the highlight and `last_utterance` are all upstream of
    # it and must behave identically.
    write_catalogue(tmp_path)
    speech, backend, voice = manager(tmp_path)
    captioned: list[str] = []
    speech.on_caption = captioned.append
    rings: list[tuple[str, bool]] = []
    speech.on_highlight = lambda key, on: rings.append((key, on))

    speech.speak(GREETING, key="title")

    assert captioned == [GREETING]
    assert speech.last_utterance == GREETING
    assert speech.speaking_key == "title"
    assert rings[0] == ("title", True)

    assert speech.repeat() is True
    assert voice.hits == 2
    assert backend.spoken == []


def test_a_hit_closes_the_backends_mouth_too(tmp_path: Path) -> None:
    # "A new utterance cancels the old one" has to hold ACROSS the two halves,
    # or a clip would play over a sentence the backend was still saying.
    write_catalogue(tmp_path)
    speech, backend, _voice = manager(tmp_path)
    speech.speak("something long and dynamic, said by Piper")
    assert backend.spoken == ["something long and dynamic, said by Piper"]
    speech.speak(GREETING)
    assert backend.cancels == 1


def test_a_miss_stops_a_clip_that_is_still_playing(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    speech, _backend, voice = manager(tmp_path)
    speech.speak(GREETING)
    speech.speak("a dynamic sentence")
    assert voice.player.cancels >= 1


def test_manager_cancel_stops_both(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    speech, backend, voice = manager(tmp_path)
    speech.speak(GREETING)
    speech.cancel()
    assert voice.player.cancels >= 1
    assert backend.cancels >= 1


def test_speak_then_plays_both_clips_in_order(tmp_path: Path) -> None:
    write_catalogue(tmp_path, texts=(GREETING, TILE))
    scheduler = FakeScheduler()
    voice = PrerenderedVoice(root=tmp_path, language="en-GB", player=NullClipPlayer())
    speech = SpeechManager(backend=FakeBackend(), scheduler=scheduler, prerendered=voice)

    assert speech.speak_then(GREETING, TILE) is True
    assert voice.hits == 1
    scheduler.advance(10_000)
    assert voice.hits == 2
    played = [path.name for path in voice.player.played]
    assert played[0] != played[1]


def test_muting_the_shell_plays_no_clip(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    speech, _backend, voice = manager(tmp_path)
    speech.set_volume(0.0)
    assert speech.speak(GREETING) is False
    assert voice.hits == 0


def test_calm_mode_reaches_the_catalogue_through_the_manager(tmp_path: Path) -> None:
    write_catalogue(tmp_path)
    speech, backend, voice = manager(tmp_path)
    speech.set_rate(-35)
    assert speech.speak(GREETING) is True
    assert backend.spoken == [GREETING]  # Piper, which can actually go slower
    assert voice.hits == 0


def test_the_played_log_line_carries_the_file_and_not_the_text(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # The boot test greps for this; the text is already in "speaking: ...".
    write_catalogue(tmp_path)
    speech, _backend, _voice = manager(tmp_path)
    with caplog.at_level("INFO"):
        speech.speak(GREETING)
    lines = [record.getMessage() for record in caplog.records if PLAYED_LOG in record.getMessage()]
    assert len(lines) == 1
    assert GREETING not in lines[0]
    assert lines[0].endswith(".ogg")


def test_catalogue_dataclass_path_is_none_for_an_unknown_string(tmp_path: Path) -> None:
    catalogue = Catalogue("en_GB", "bf_emma", tmp_path, {"a": "1.ogg"}, RENDERED_RATE)
    assert catalogue.path("b") is None
    assert catalogue.path("a") == tmp_path / "1.ogg"


def test_kidnix_speech_off_silences_the_clips_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AGENTS.md 5: on a developer's workstation, nothing makes a sound.

    `select_backend` has honoured `KIDNIX_SPEECH=off` since the incident of
    2026-08-23. The catalogue is a SECOND mouth, and an off-switch that closed
    only one of them would be worse than none -- it would look like it worked
    while the machine talked through the other.
    """
    write_catalogue(tmp_path)
    for value in ("off", "0", "false", "none", "null", "OFF", " off "):
        monkeypatch.setenv("KIDNIX_SPEECH", value)
        assert select_prerendered(root=tmp_path, language="en-GB") is None, value


def test_speech_left_unset_is_a_real_kiosk_and_keeps_the_catalogue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_catalogue(tmp_path)
    monkeypatch.delenv("KIDNIX_SPEECH", raising=False)
    assert select_prerendered(root=tmp_path, language="en-GB") is not None
