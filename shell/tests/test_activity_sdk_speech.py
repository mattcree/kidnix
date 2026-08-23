"""The activity's voice and its stylesheet. Pure: no display, no daemon.

The widgets that use both are in ``test_activity_sdk_widgets.py``, which skips
without a display. These do not, because "every spoken line is captioned" is
the accessibility contract and a contract that only holds where there is a
monitor is not one.
"""

from __future__ import annotations

import re
from pathlib import Path

from kidnix_activity.captions import CaptionClient
from kidnix_activity.speech import ActivitySpeech
from kidnix_shell.access import AccessConfig
from kidnix_shell.speech import FakeBackend, SpeechManager

SHELL_CSS = Path(__file__).resolve().parents[1] / "kidnix_shell" / "theme.css"
ACTIVITY_CSS = Path(__file__).resolve().parents[1] / "kidnix_activity" / "activity.css"

_COLOUR = re.compile(r"@define-color\s+([a-z0-9-]+)\s+(#[0-9a-fA-F]{3,8});")


def colours(path: Path) -> dict[str, str]:
    return {
        name: value.lower() for name, value in _COLOUR.findall(path.read_text(encoding="utf-8"))
    }


# --- one voice, one caption ------------------------------------------------


def voice(**kwargs: object) -> tuple[ActivitySpeech, FakeBackend, list[str]]:
    backend = FakeBackend()
    captioned: list[str] = []

    class Sink(CaptionClient):
        def send(self, text: str) -> bool:
            captioned.append(text)
            return True

    speech = ActivitySpeech(
        "hello-draw",
        manager=SpeechManager(backend=backend),
        captions=Sink("hello-draw", None),
        **kwargs,  # type: ignore[arg-type]
    )
    return speech, backend, captioned


def test_every_spoken_line_is_also_captioned() -> None:
    speech, backend, captioned = voice()
    speech.speak("Press the big button.")
    assert backend.spoken == ["Press the big button."]
    assert captioned == ["Press the big button."]


def test_a_muted_machine_still_shows_the_caption() -> None:
    """Why mute is safe to offer at all (accessibility review B2/B3)."""
    speech, backend, captioned = voice()
    speech.apply_access(AccessConfig(mute=True))
    speech.speak("Press the big button.")
    assert backend.spoken == []
    assert captioned == ["Press the big button."]


def test_calm_mode_slows_the_activitys_voice_the_same_way_it_slows_the_shells() -> None:
    speech, backend, _ = voice()
    speech.apply_access(AccessConfig(calm=True))
    assert backend.rate == AccessConfig(calm=True).speech_rate


def test_there_is_no_queue_a_child_would_have_to_wait_out() -> None:
    """A new line replaces the old one; nothing stacks up behind it."""
    speech, backend, _ = voice()
    speech.speak("one")
    speech.speak("two")
    assert backend.spoken == ["one", "two"]
    assert speech.last_utterance == "two"


def test_cancel_reaches_the_backend() -> None:
    speech, backend, _ = voice()
    speech.speak("one")
    speech.cancel()
    assert backend.cancels == 1


def test_closing_lets_go_of_the_backend() -> None:
    speech, backend, _ = voice()
    speech.close()
    assert backend.closed is True


def test_the_replay_says_the_last_line_again() -> None:
    speech, backend, _ = voice()
    speech.speak("Press the big button.")
    assert speech.repeat() is True
    assert backend.spoken == ["Press the big button."] * 2


def test_there_is_nothing_to_repeat_before_anything_is_said() -> None:
    speech, _, _ = voice()
    assert speech.repeat() is False


def test_an_activity_with_no_caption_socket_still_speaks(tmp_path: Path) -> None:
    backend = FakeBackend()
    speech = ActivitySpeech(
        "hello-draw",
        manager=SpeechManager(backend=backend),
        env={"XDG_RUNTIME_DIR": str(tmp_path)},
    )
    assert speech.speak("Press the big button.") is True
    assert backend.spoken == ["Press the big button."]


# --- the stylesheet --------------------------------------------------------


def test_the_activitys_colour_tokens_are_the_shells_to_the_byte() -> None:
    shell = colours(SHELL_CSS)
    activity = colours(ACTIVITY_CSS)
    assert activity, "activity.css defines no colours"
    for name, value in activity.items():
        assert name in shell, f"{name} is not a shell token"
        assert value == shell[name], f"{name} drifted: {value} vs {shell[name]}"


def test_the_activity_stylesheet_does_not_redefine_the_shells_own_selectors() -> None:
    """Additive, not a fork. The shell's rules are loaded first and stay."""
    text = ACTIVITY_CSS.read_text(encoding="utf-8")
    for shell_only in ("button.tile", "button.ritual", ".band ", ".pin-pad"):
        assert shell_only not in text


def test_the_reserved_highlight_is_not_spent_on_anything_new() -> None:
    """08 section 3.4b: one highlight colour, one meaning."""
    text = ACTIVITY_CSS.read_text(encoding="utf-8")
    uses = [line for line in text.splitlines() if "@kid-highlight" in line]
    assert all(line.strip().startswith("@define-color") for line in uses)
