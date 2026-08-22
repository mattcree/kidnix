"""Read-aloud: queue policy, hover dwell, the Ear (spec section 3)."""

from __future__ import annotations

from kidnix_shell.speech import (
    HOVER_DWELL_MS,
    FakeBackend,
    FakeScheduler,
    NullBackend,
    SpeechManager,
    select_backend,
)


def make() -> tuple[SpeechManager, FakeBackend, FakeScheduler]:
    backend = FakeBackend()
    scheduler = FakeScheduler()
    return SpeechManager(backend=backend, scheduler=scheduler), backend, scheduler


def test_speaking_says_the_thing() -> None:
    speech, backend, _ = make()
    assert speech.speak("Draw")
    assert backend.spoken == ["Draw"]


def test_a_new_utterance_cancels_the_previous() -> None:
    """No backlog: a child sweeping the grid hears the tile under the pointer."""
    speech, backend, _ = make()
    speech.speak("Draw", key="a")
    speech.speak("Music", key="b")
    speech.speak("Books", key="c")
    assert backend.spoken == ["Draw", "Music", "Books"]
    # Each speak stops the highlight of the last, which is our cancel signal.
    assert speech.speaking_key == "c"


def test_empty_text_says_nothing() -> None:
    speech, backend, _ = make()
    assert not speech.speak("")
    assert not speech.speak("   ")
    assert backend.spoken == []


def test_the_ear_repeats_the_last_utterance() -> None:
    speech, backend, _ = make()
    speech.speak("Tux Paint. Draw a picture.")
    assert speech.repeat()
    assert backend.spoken == ["Tux Paint. Draw a picture."] * 2


def test_the_ear_is_silent_before_anything_was_said() -> None:
    speech, backend, _ = make()
    assert not speech.repeat()
    assert backend.spoken == []


def test_hover_speaks_only_after_the_dwell() -> None:
    speech, backend, scheduler = make()
    speech.hover_enter("tile", "Draw")
    scheduler.advance(HOVER_DWELL_MS - 50)
    assert backend.spoken == []
    scheduler.advance(100)
    assert backend.spoken == ["Draw"]


def test_leaving_before_the_dwell_says_nothing() -> None:
    speech, backend, scheduler = make()
    speech.hover_enter("tile", "Draw")
    scheduler.advance(100)
    speech.hover_leave("tile")
    scheduler.advance(1000)
    assert backend.spoken == []


def test_hover_speaks_once_per_enter() -> None:
    speech, backend, scheduler = make()
    for _ in range(5):
        speech.hover_enter("tile", "Draw")
        scheduler.advance(HOVER_DWELL_MS + 10)
    assert backend.spoken == ["Draw"]


def test_leaving_and_returning_speaks_again() -> None:
    speech, backend, scheduler = make()
    speech.hover_enter("tile", "Draw")
    scheduler.advance(HOVER_DWELL_MS + 10)
    speech.hover_leave("tile")
    speech.hover_enter("tile", "Draw")
    scheduler.advance(HOVER_DWELL_MS + 10)
    assert backend.spoken == ["Draw", "Draw"]


def test_moving_between_tiles_only_speaks_the_last_one() -> None:
    speech, backend, scheduler = make()
    speech.hover_enter("a", "Draw")
    scheduler.advance(100)
    speech.hover_leave("a")
    speech.hover_enter("b", "Music")
    scheduler.advance(HOVER_DWELL_MS + 10)
    assert backend.spoken == ["Music"]


def test_focus_and_activation_speak_immediately() -> None:
    speech, backend, _ = make()
    speech.speak_focus("Draw", key="a")
    speech.speak_activation("Draw", key="a")
    assert backend.spoken == ["Draw", "Draw"]


def test_the_highlight_ring_goes_on_and_comes_off() -> None:
    speech, _, scheduler = make()
    seen: list[tuple[str, bool]] = []
    speech.on_highlight = lambda key, on: seen.append((key, on))

    speech.speak("Draw", key="tile")
    assert seen == [("tile", True)]
    scheduler.advance(10_000)
    assert seen == [("tile", True), ("tile", False)]
    assert speech.speaking_key is None


def test_a_new_utterance_moves_the_ring() -> None:
    speech, _, _ = make()
    seen: list[tuple[str, bool]] = []
    speech.on_highlight = lambda key, on: seen.append((key, on))
    speech.speak("Draw", key="a")
    speech.speak("Music", key="b")
    assert seen == [("a", True), ("a", False), ("b", True)]


def test_cancel_clears_the_ring_and_tells_the_backend() -> None:
    speech, backend, _ = make()
    speech.speak("Draw", key="a")
    speech.cancel()
    assert backend.cancels == 1
    assert speech.speaking_key is None


def test_disabled_speech_still_remembers_for_the_ear() -> None:
    speech, backend, _ = make()
    speech.enabled = False
    assert not speech.speak("Draw")
    assert backend.spoken == []
    assert speech.last_utterance == "Draw"


def test_the_null_backend_never_raises() -> None:
    backend = NullBackend()
    backend.speak("hello")
    backend.speak("hello again")
    backend.cancel()
    backend.close()


def test_selecting_the_null_backend_is_explicit() -> None:
    assert select_backend("null").name == "null"


def test_closing_shuts_the_backend_down() -> None:
    speech, backend, _ = make()
    speech.speak("Draw", key="a")
    speech.close()
    assert backend.closed


def test_the_fake_scheduler_cancels_cleanly() -> None:
    scheduler = FakeScheduler()
    fired: list[str] = []
    handle = scheduler.schedule(100, lambda: fired.append("x"))
    scheduler.cancel(handle)
    scheduler.advance(1000)
    assert fired == []
