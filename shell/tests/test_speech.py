"""Read-aloud: queue policy, hover dwell, the Ear (spec section 3)."""

from __future__ import annotations

from kidnix_shell.speech import (
    HOVER_DWELL_MS,
    RECONNECT_SECONDS,
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
