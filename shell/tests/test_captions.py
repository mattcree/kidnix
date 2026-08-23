"""The shell's caption listener: the other end of the activity SDK's wire.

An activity owns everything below the band and the caption strip is in the
shell's band window, so a line an activity speaks is captionless unless it
comes back here (accessibility review B2, ``docs/design/activity-sdk.md`` §4).

Everything below is headless. The socket tests need ``gi`` for ``Gio.Socket``
but no display and no compositor -- a datagram socket does not care whether
anything is on screen, and neither should the proof that captions work.
"""

from __future__ import annotations

import logging
import stat
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from kidnix_activity.captions import MAX_TEXT_CHARS, CaptionClient, encode
from kidnix_activity.speech import ActivitySpeech
from kidnix_shell.captions import (
    MAX_TRACKED_SOURCES,
    RATE_LIMIT_PER_SECOND,
    UNKNOWN_SOURCE,
    CaptionListener,
    CaptionRouter,
    safe_source,
)
from kidnix_shell.speech import FakeBackend, FakeScheduler, SpeechManager


class _DeliveringClient(CaptionClient):
    """A caption sink that always gets there. The shell's listener, faked."""

    def send(self, text: str) -> bool:
        self.last_text = text
        return True


class FakeSpeech:
    """The shell's voice, as the router sees it. Records what it was given."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def speak(self, text: str, key: str | None = None) -> bool:
        self.said.append(text)
        return True


class FakeClock:
    """A hand-wound monotonic clock, so the rate limiter needs no sleeping."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def shell_voice() -> tuple[SpeechManager, FakeBackend, list[str]]:
    """A real :class:`SpeechManager` with the shell's caption hook on it."""
    backend = FakeBackend()
    captioned: list[str] = []
    speech = SpeechManager(backend=backend, scheduler=FakeScheduler())
    speech.on_caption = captioned.append  # what `ShellWindow._on_caption` does
    return speech, backend, captioned


# --- the socket ------------------------------------------------------------


@pytest.fixture
def glib() -> Any:
    return pytest.importorskip("gi.repository.GLib")


def pump(glib: Any, until: Callable[[], bool], seconds: float = 2.0) -> bool:
    """Run the main context until ``until`` is true or the time runs out."""
    context = glib.MainContext.default()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if until():
            return True
        time.sleep(0.005)
    return until()


@pytest.fixture
def listening(glib: Any, tmp_path: Path) -> Iterator[tuple[CaptionListener, FakeSpeech, Path]]:
    assert glib is not None
    speech = FakeSpeech()
    path = tmp_path / "kidnix" / "captions.sock"
    listener = CaptionListener(speech, path=path)
    assert listener.start() is True
    yield listener, speech, path
    listener.stop()


def test_a_datagram_from_an_activity_is_spoken_and_captioned_by_the_shell(
    glib: Any, tmp_path: Path
) -> None:
    """The whole point, end to end, with the SDK's own client on the far end.

    The line goes through ``SpeechManager.speak``, which means it reaches the
    strip *and* the voice -- the same path a line the shell wrote itself takes.
    """
    speech, backend, captioned = shell_voice()
    path = tmp_path / "kidnix" / "captions.sock"
    listener = CaptionListener(speech, path=path)
    assert listener.start() is True
    try:
        client = CaptionClient("hello-draw", path)
        assert client.send("Press the big button.") is True
        assert pump(glib, lambda: bool(captioned))
    finally:
        listener.stop()
    assert captioned == ["Press the big button."]
    assert backend.spoken == ["Press the big button."]


def test_the_socket_is_the_childs_own_and_nobody_elses(
    listening: tuple[CaptionListener, FakeSpeech, Path],
) -> None:
    """0700 on the directory, 0600 on the socket.

    One Unix user runs the whole session, so this is intent rather than a wall
    -- but a socket anything on the machine may write to is a way to put words
    under the band, and that is not worth offering.
    """
    _listener, _speech, path = listening
    assert path.is_socket()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_a_socket_left_by_a_crashed_shell_is_replaced(glib: Any, tmp_path: Path) -> None:
    """Nothing unlinks it on SIGKILL, so start-up has to."""
    speech = FakeSpeech()
    path = tmp_path / "kidnix" / "captions.sock"
    first = CaptionListener(FakeSpeech(), path=path)
    assert first.start() is True
    stale = path.stat().st_ino
    # ...and now the shell "crashes" without stopping: the file is still there.
    second = CaptionListener(speech, path=path)
    assert second.start() is True
    try:
        assert path.stat().st_ino != stale
        assert CaptionClient("hello-draw", path).send("Hello.") is True
        assert pump(glib, lambda: bool(speech.said))
    finally:
        second.stop()
        first.stop()
    assert speech.said == ["Hello."]


def test_stopping_takes_the_socket_with_it(
    glib: Any, listening: tuple[CaptionListener, FakeSpeech, Path]
) -> None:
    """And the activity notices: `send` fails, so it speaks the line itself."""
    listener, _speech, path = listening
    listener.stop()
    assert listener.listening is False
    assert not path.exists()
    client = CaptionClient("hello-draw", path)
    assert client.available is False
    assert client.send("Press the big button.") is False


def test_the_listener_says_so_and_carries_on_when_it_cannot_bind(tmp_path: Path) -> None:
    """A shell that cannot listen is still a shell. It must not raise."""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    path = blocked / "kidnix" / "captions.sock"
    path.parent.mkdir()
    path.write_text("not a socket")  # something else already owns the name
    listener = CaptionListener(FakeSpeech(), path=path)
    assert listener.start() is False
    assert listener.listening is False


# --- what comes off the wire is not trusted --------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"not json at all",
        b'{"speak": "unterminated',
        b'["speak", "a list is not an object"]',
        b'{"source": "hello-draw"}',  # no `speak`
        b'{"speak": 12}',
        b'{"speak": "   "}',
        b"\xff\xfe not utf-8",
    ],
)
def test_a_datagram_that_is_not_a_caption_is_dropped(payload: bytes) -> None:
    speech = FakeSpeech()
    router = CaptionRouter(speech)
    assert router.handle(payload) is False
    assert speech.said == []
    assert router.malformed == 1


def test_an_unknown_key_is_ignored_rather_than_refused() -> None:
    """§4.1: unknown keys are reserved, so an older shell keeps working."""
    speech = FakeSpeech()
    router = CaptionRouter(speech)
    assert router.handle(b'{"speak": "Hello.", "source": "x", "colour": "teal"}') is True
    assert speech.said == ["Hello."]


def test_a_caption_is_one_line_however_it_arrives() -> None:
    """A newline on this wire would otherwise forge a second line in the log."""
    speech = FakeSpeech()
    router = CaptionRouter(speech)
    router.handle(encode("Two\nlines  and   spaces", "hello-draw"))
    router.handle(encode("x" * (MAX_TEXT_CHARS * 2), "hello-draw"))
    assert speech.said[0] == "Two lines and spaces"
    assert len(speech.said[1]) == MAX_TEXT_CHARS


def test_a_source_id_cannot_forge_a_log_line() -> None:
    assert safe_source("hello-draw") == "hello-draw"
    assert safe_source("") == UNKNOWN_SOURCE
    forged = safe_source("hello draw: WARNING nothing\nis wrong")
    assert forged == "hellodrawWARNINGnothingiswrong"
    assert " " not in forged and "\n" not in forged
    assert len(safe_source("a" * 200)) == 32


# --- the gate: only while a child is inside an activity ---------------------


def test_nothing_is_said_unless_a_child_is_inside_an_activity(
    caplog: pytest.LogCaptureFixture,
) -> None:
    speech = FakeSpeech()
    inside = False
    router = CaptionRouter(speech, is_active=lambda: inside)
    with caplog.at_level(logging.DEBUG, logger="kidnix_shell.captions"):
        assert router.handle(encode("Press the big button.", "hello-draw")) is False
    assert speech.said == []
    assert router.ignored == 1
    assert "no activity is on screen" in caplog.text
    inside = True
    assert router.handle(encode("Press the big button.", "hello-draw")) is True
    assert speech.said == ["Press the big button."]


# --- the rate limit --------------------------------------------------------


def test_a_flood_costs_one_warning_and_then_silence(caplog: pytest.LogCaptureFixture) -> None:
    """A warning per dropped datagram would *be* the denial of service."""
    speech = FakeSpeech()
    clock = FakeClock()
    router = CaptionRouter(speech, clock=clock)
    with caplog.at_level(logging.WARNING, logger="kidnix_shell.captions"):
        for index in range(50):
            router.handle(encode(f"line {index}", "hello-draw"))
    assert len(speech.said) == RATE_LIMIT_PER_SECOND
    assert router.limited == 50 - RATE_LIMIT_PER_SECOND
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "hello-draw" in warnings[0].getMessage()


def test_the_limit_is_per_source_so_one_bad_activity_cannot_silence_another() -> None:
    speech = FakeSpeech()
    clock = FakeClock()
    router = CaptionRouter(speech, clock=clock)
    for index in range(20):
        router.handle(encode(f"noise {index}", "shouty"))
    assert router.handle(encode("Press the big button.", "hello-draw")) is True
    assert speech.said[-1] == "Press the big button."


def test_a_source_that_slows_down_is_heard_again_and_warns_again() -> None:
    speech = FakeSpeech()
    clock = FakeClock()
    router = CaptionRouter(speech, clock=clock)
    for index in range(10):
        router.handle(encode(f"line {index}", "hello-draw"))
    assert len(speech.said) == RATE_LIMIT_PER_SECOND
    clock.advance(2.0)
    assert router.handle(encode("Back under the limit.", "hello-draw")) is True
    assert speech.said[-1] == "Back under the limit."


def test_a_sender_that_invents_a_new_name_every_time_cannot_grow_the_table() -> None:
    """The id is off the wire, so the limiter's own memory is bounded."""
    speech = FakeSpeech()
    router = CaptionRouter(speech, clock=FakeClock())
    for index in range(MAX_TRACKED_SOURCES * 3):
        router.handle(encode("Hello.", f"made-up-{index}"))
    assert len(router._recent) <= MAX_TRACKED_SOURCES + 1


# --- one voice, across the process boundary --------------------------------


def test_an_activity_whose_line_reached_the_shell_does_not_say_it_twice() -> None:
    """The one-voice rule (08 §3.6) with two processes in it.

    ``on_caption`` returning True means "the shell owns this utterance now",
    and the activity's own backend is left alone.
    """
    backend = FakeBackend()
    speech = ActivitySpeech(
        "hello-draw",
        manager=SpeechManager(backend=backend, scheduler=FakeScheduler()),
        captions=_DeliveringClient("hello-draw", None),
    )
    assert speech.speak("Press the big button.") is True
    assert backend.spoken == []
    # ...and the Ear still has something to repeat.
    assert speech.last_utterance == "Press the big button."


def test_an_activity_with_no_shell_behind_it_speaks_for_itself(tmp_path: Path) -> None:
    backend = FakeBackend()
    speech = ActivitySpeech(
        "hello-draw",
        manager=SpeechManager(backend=backend, scheduler=FakeScheduler()),
        env={"XDG_RUNTIME_DIR": str(tmp_path)},  # a runtime dir with no socket
    )
    assert speech.speak("Press the big button.") is True
    assert backend.spoken == ["Press the big button."]


def test_the_two_ends_meet_on_a_real_socket(glib: Any, tmp_path: Path) -> None:
    """The whole contract in one test: the activity is silent, the shell says it."""
    path = tmp_path / "kidnix" / "captions.sock"
    shell_speech, shell_backend, captioned = shell_voice()
    listener = CaptionListener(shell_speech, path=path)
    assert listener.start() is True
    activity_backend = FakeBackend()
    activity = ActivitySpeech(
        "hello-draw",
        manager=SpeechManager(backend=activity_backend, scheduler=FakeScheduler()),
        socket_path=path,
    )
    try:
        activity.speak("Press the big button.")
        assert pump(glib, lambda: bool(captioned))
    finally:
        listener.stop()
    assert activity_backend.spoken == []  # not a second voice
    assert shell_backend.spoken == ["Press the big button."]
    assert captioned == ["Press the big button."]


def test_the_default_path_is_the_one_the_sdk_sends_to(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    assert CaptionListener.default_path() == Path("/run/user/1000/kidnix/captions.sock")
    monkeypatch.delenv("XDG_RUNTIME_DIR")
    assert CaptionListener.default_path() is None
    # ...and a shell without one says so instead of raising.
    assert CaptionListener(FakeSpeech()).start() is False
