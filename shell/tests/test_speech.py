"""Read-aloud: queue policy, hover dwell, the settle gate, the Ear.

Spec section 3, as revised by 7b.
"""

from __future__ import annotations

import logging

import pytest

from kidnix_shell.speech import (
    HOVER_DWELL_MS,
    HOVER_LOG_PREFIX,
    HOVER_SELECTION_WINDOW_MS,
    RECONNECT_SECONDS,
    SETTLE_VELOCITY_PX_S,
    VELOCITY_WINDOW_MS,
    FakeBackend,
    FakeScheduler,
    NullBackend,
    SpeechdBackend,
    SpeechManager,
    select_backend,
)


def make() -> tuple[SpeechManager, FakeBackend, FakeScheduler]:
    backend = FakeBackend()
    scheduler = FakeScheduler()
    return SpeechManager(backend=backend, scheduler=scheduler), backend, scheduler


class Pointer:
    """A fake clock and a fake pointer, moved together.

    ``FakeScheduler`` already fires timers on demand; this keeps the manager's
    own clock in step with it so a test can say "the hand moved 200 px in
    50 ms" and mean it.
    """

    def __init__(self) -> None:
        self.backend = FakeBackend()
        self.scheduler = FakeScheduler()
        self.seconds = 0.0
        self.speech = SpeechManager(
            backend=self.backend, scheduler=self.scheduler, clock=lambda: self.seconds
        )
        self.x = 0.0
        self.y = 0.0

    def advance(self, ms: float) -> None:
        self.seconds += ms / 1000.0
        self.scheduler.advance(int(ms))

    def enter(self, key: str, text: str, log_id: str | None = None) -> None:
        self.speech.hover_enter(key, text, log_id)
        self.speech.hover_motion(key, self.x, self.y)

    def glide(self, key: str, px_per_second: float, ms: float, step_ms: float = 10.0) -> None:
        """Move at a steady speed, sampling like a real motion controller."""
        steps = max(1, int(ms / step_ms))
        for _ in range(steps):
            self.advance(step_ms)
            self.x += px_per_second * step_ms / 1000.0
            self.speech.hover_motion(key, self.x, self.y)


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


# --- connecting lazily and reconnecting (v0.1.1) -------------------------
#
# docs/spikes/session-integration.md section 5.1: connecting at startup is what
# made python3-speechd autospawn a daemon inside the shell's own cgroup and
# turned every crash into eleven seconds of black screen. The unit now wants
# speech-dispatcher.socket, and the client here connects on first use and
# reconnects on its own -- logging the state change once, not per event.


class FakeClient:
    """A speech-dispatcher client that can be told to fall over."""

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.cancels = 0
        self.closed = False
        self.broken = False

    def speak(self, text: str) -> None:
        if self.broken:
            raise ConnectionError("the daemon went away")
        self.spoken.append(text)

    def cancel(self) -> None:
        if self.broken:
            raise ConnectionError("the daemon went away")
        self.cancels += 1

    def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_selecting_a_backend_opens_no_socket() -> None:
    """Startup must never block on a daemon that has not come up yet."""
    opened: list[int] = []

    def connect() -> FakeClient:
        opened.append(1)
        return FakeClient()

    backend = SpeechdBackend(connect=connect)
    assert not backend.connected
    assert opened == []


def test_the_socket_opens_on_the_first_thing_said() -> None:
    client = FakeClient()
    backend = SpeechdBackend(connect=lambda: client)
    backend.speak("Draw")
    assert backend.connected
    assert client.spoken == ["Draw"]
    assert backend.connects == 1


def test_cancelling_before_anything_was_said_does_not_connect() -> None:
    connects: list[int] = []

    def connect() -> FakeClient:
        connects.append(1)
        return FakeClient()

    backend = SpeechdBackend(connect=connect)
    backend.cancel()
    assert connects == []


def test_a_dead_daemon_is_silence_not_a_crash() -> None:
    def refuse() -> FakeClient:
        raise ConnectionRefusedError("nothing is listening")

    backend = SpeechdBackend(connect=refuse, clock=FakeClock())
    backend.speak("Draw")  # must not raise
    assert not backend.connected
    assert backend.failures == 1


def test_a_dead_daemon_is_not_retried_on_every_utterance() -> None:
    """A child sweeping a grid of tiles must not open a socket per tile."""
    attempts: list[int] = []

    def refuse() -> FakeClient:
        attempts.append(1)
        raise ConnectionRefusedError("nothing is listening")

    clock = FakeClock()
    backend = SpeechdBackend(connect=refuse, clock=clock)
    for _ in range(20):
        backend.speak("Draw")
    assert len(attempts) == 1
    clock.now += RECONNECT_SECONDS + 0.1
    backend.speak("Draw")
    assert len(attempts) == 2


def test_the_client_reconnects_when_speech_dispatcher_restarts() -> None:
    clients = [FakeClient(), FakeClient()]
    clock = FakeClock()
    backend = SpeechdBackend(connect=lambda: clients[min(backend.connects, 1)], clock=clock)

    backend.speak("Draw")
    assert clients[0].spoken == ["Draw"]

    clients[0].broken = True  # speech-dispatcher restarts under us
    backend.speak("Music")
    assert not backend.connected
    assert clients[0].closed

    clock.now += RECONNECT_SECONDS + 0.1
    backend.speak("Books")
    assert clients[1].spoken == ["Books"]
    assert backend.connects == 2


def test_closing_lets_go_of_the_client() -> None:
    client = FakeClient()
    backend = SpeechdBackend(connect=lambda: client)
    backend.speak("Draw")
    backend.close()
    assert client.closed
    assert not backend.connected


def test_a_backend_given_a_client_is_already_connected() -> None:
    backend = SpeechdBackend(FakeClient())
    assert backend.connected


# --- the settle gate and the dwell (spec 7b, 09 section 2) ----------------


def test_the_dwell_is_450_ms_not_300() -> None:
    """09 section 2: 300 ms is the bottom of the range adults rate usable."""
    assert HOVER_DWELL_MS == 450


def test_a_still_pointer_is_spoken_after_the_dwell() -> None:
    pointer = Pointer()
    pointer.enter("tile", "Draw")
    pointer.advance(HOVER_DWELL_MS - 50)
    assert pointer.backend.spoken == []
    pointer.advance(60)
    assert pointer.backend.spoken == ["Draw"]


def test_a_pointer_sweeping_across_a_tile_says_nothing() -> None:
    """The failure mode this gate exists for: half a grid of half-utterances.

    A child overshooting a target crosses several tiles at speed. None of them
    may speak, however long the crossing takes.
    """
    pointer = Pointer()
    pointer.enter("tile", "Draw")
    pointer.glide("tile", px_per_second=600.0, ms=HOVER_DWELL_MS * 3)
    assert pointer.backend.spoken == []


def test_a_pointer_that_arrives_and_stops_speaks_a_dwell_after_it_stopped() -> None:
    """The clock starts when the hand stops, not when it crossed the border."""
    pointer = Pointer()
    pointer.enter("tile", "Draw")
    pointer.glide("tile", px_per_second=600.0, ms=200.0)  # still travelling
    pointer.advance(HOVER_DWELL_MS - 50)  # settled, but not for long enough
    assert pointer.backend.spoken == []
    pointer.advance(60)
    assert pointer.backend.spoken == ["Draw"]


def test_a_slow_drift_still_counts_as_settled() -> None:
    """A five-year-old's hand is never perfectly still; the gate knows that."""
    pointer = Pointer()
    pointer.enter("tile", "Draw")
    pointer.glide("tile", px_per_second=SETTLE_VELOCITY_PX_S / 4, ms=HOVER_DWELL_MS + 60)
    assert pointer.backend.spoken == ["Draw"]


def test_velocity_is_measured_over_a_window_not_over_one_sample() -> None:
    pointer = Pointer()
    pointer.enter("tile", "Draw")
    pointer.glide("tile", px_per_second=200.0, ms=VELOCITY_WINDOW_MS)
    assert pointer.speech.pointer_velocity() == pytest.approx(200.0, rel=0.2)
    # And a pointer that never moved has no velocity at all, rather than a
    # division by zero.
    fresh = Pointer()
    fresh.enter("other", "Music")
    assert fresh.speech.pointer_velocity() == 0.0


def test_leaving_mid_settle_says_nothing_and_re_arms() -> None:
    pointer = Pointer()
    pointer.enter("tile", "Draw")
    pointer.advance(200)
    pointer.speech.hover_leave("tile")
    pointer.advance(2000)
    assert pointer.backend.spoken == []
    pointer.enter("tile", "Draw")
    pointer.advance(HOVER_DWELL_MS + 10)
    assert pointer.backend.spoken == ["Draw"]


def test_keyboard_focus_is_not_gated_at_all() -> None:
    """09 section 2: focus is deliberate in a way hover is not. No delay."""
    pointer = Pointer()
    pointer.speech.speak_focus("Draw", key="tile")
    assert pointer.backend.spoken == ["Draw"]


def test_a_configured_dwell_is_honoured() -> None:
    speech = SpeechManager(
        backend=FakeBackend(), scheduler=(scheduler := FakeScheduler()), dwell_ms=900
    )
    speech.hover_enter("tile", "Draw")
    scheduler.advance(500)
    assert speech.backend.spoken == []  # type: ignore[attr-defined]
    scheduler.advance(450)
    assert speech.backend.spoken == ["Draw"]  # type: ignore[attr-defined]


# --- protocol P5's instrumentation ---------------------------------------


def test_every_hover_utterance_is_logged_with_its_dwell(caplog: pytest.LogCaptureFixture) -> None:
    pointer = Pointer()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.speech"):
        pointer.enter("tile-7", "Draw", log_id="tuxpaint")
        pointer.advance(HOVER_DWELL_MS)
        assert pointer.backend.spoken == ["Draw"]
        # The line waits three seconds to find out whether it was wanted.
        assert HOVER_LOG_PREFIX not in caplog.text
        pointer.advance(HOVER_SELECTION_WINDOW_MS + 10)
    lines = [line for line in caplog.messages if line.startswith(HOVER_LOG_PREFIX)]
    assert lines == [f"{HOVER_LOG_PREFIX}: id=tuxpaint dwell_ms={HOVER_DWELL_MS} selected=False"]


def test_a_hover_followed_by_a_tap_is_logged_as_selected(
    caplog: pytest.LogCaptureFixture,
) -> None:
    pointer = Pointer()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.speech"):
        pointer.enter("tile-7", "Draw", log_id="tuxpaint")
        pointer.advance(HOVER_DWELL_MS)
        pointer.advance(500)
        pointer.speech.speak_activation("Draw", key="tile-7")
    lines = [line for line in caplog.messages if line.startswith(HOVER_LOG_PREFIX)]
    assert lines == [f"{HOVER_LOG_PREFIX}: id=tuxpaint dwell_ms={HOVER_DWELL_MS} selected=True"]


def test_tapping_a_different_control_does_not_count_as_a_follow_through(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """P5's metric is "was *that* speech wanted", not "did anything happen"."""
    pointer = Pointer()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.speech"):
        pointer.enter("tile-7", "Draw", log_id="tuxpaint")
        pointer.advance(HOVER_DWELL_MS)
        pointer.speech.speak_activation("Music", key="tile-9")
        pointer.advance(HOVER_SELECTION_WINDOW_MS + 10)
    lines = [line for line in caplog.messages if line.startswith(HOVER_LOG_PREFIX)]
    assert lines == [f"{HOVER_LOG_PREFIX}: id=tuxpaint dwell_ms={HOVER_DWELL_MS} selected=False"]


def test_a_tap_after_the_window_is_too_late(caplog: pytest.LogCaptureFixture) -> None:
    pointer = Pointer()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.speech"):
        pointer.enter("tile-7", "Draw", log_id="tuxpaint")
        pointer.advance(HOVER_DWELL_MS + 10)
        pointer.advance(HOVER_SELECTION_WINDOW_MS + 100)
        pointer.speech.speak_activation("Draw", key="tile-7")
    assert "selected=False" in caplog.text
    assert "selected=True" not in caplog.text


def test_the_log_never_carries_anything_but_the_control_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No utterance text, no child's work, no times of day. An id and a number."""
    pointer = Pointer()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.speech"):
        pointer.enter("tile-7", "My drawing of a dinosaur", log_id="tuxpaint")
        pointer.advance(HOVER_DWELL_MS + 10)
        pointer.advance(HOVER_SELECTION_WINDOW_MS + 10)
    line = next(m for m in caplog.messages if m.startswith(HOVER_LOG_PREFIX))
    assert "dinosaur" not in line


def test_closing_flushes_the_last_hover(caplog: pytest.LogCaptureFixture) -> None:
    pointer = Pointer()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.speech"):
        pointer.enter("tile-7", "Draw", log_id="tuxpaint")
        pointer.advance(HOVER_DWELL_MS + 10)
        pointer.speech.close()
    assert HOVER_LOG_PREFIX in caplog.text
