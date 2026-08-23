"""The activity SDK's pure half: the launch environment, SIGTERM, captions.

Everything here runs without a display, a shell, a socket or a voice -- which
is the point. The contract in ``docs/design/activity-sdk.md`` is a contract
precisely to the extent that it can be asserted here.
"""

from __future__ import annotations

import json
import signal
from pathlib import Path

import pytest

from kidnix_activity import captions, lifecycle
from kidnix_activity.captions import CaptionClient
from kidnix_activity.env import ACTIVITY_ID_VAR, PROFILE_ID_VAR, LaunchEnv
from kidnix_activity.lifecycle import (
    FAILED_EXIT_CODE,
    QUIT_MODE,
    SUCCESS_EXIT_CODE,
    FinishHandler,
)

# --- the launch environment ------------------------------------------------


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    home = tmp_path / "home"
    base = {
        "HOME": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
    }
    base.update(extra)
    return base


def test_the_journal_root_is_the_profiles_not_the_machines(tmp_path: Path) -> None:
    launch = LaunchEnv.from_env(_env(tmp_path, **{ACTIVITY_ID_VAR: "a", PROFILE_ID_VAR: "robin"}))
    assert launch.journal_root.parts[-3:] == ("robin", "journal") or "profiles" in str(
        launch.journal_root
    )
    assert "profiles/robin/journal" in launch.journal_root.as_posix()


def test_no_profile_means_the_legacy_layout_not_a_guess(tmp_path: Path) -> None:
    launch = LaunchEnv.from_env(_env(tmp_path, **{ACTIVITY_ID_VAR: "a"}))
    assert launch.profile_id == ""
    assert launch.journal_root.as_posix().endswith("kidnix/journal")
    assert "profiles" not in launch.journal_root.as_posix()


def test_an_activity_started_by_hand_knows_it_was_not_the_shell(tmp_path: Path) -> None:
    assert LaunchEnv.from_env(_env(tmp_path)).launched_by_shell is False
    assert LaunchEnv.from_env(_env(tmp_path, **{ACTIVITY_ID_VAR: "x"})).launched_by_shell is True


def test_whitespace_around_an_id_is_not_an_id(tmp_path: Path) -> None:
    launch = LaunchEnv.from_env(_env(tmp_path, **{ACTIVITY_ID_VAR: "  ", PROFILE_ID_VAR: " "}))
    assert launch.activity_id == ""
    assert launch.profile_id == ""


def test_the_runtime_root_is_under_the_runtime_dir(tmp_path: Path) -> None:
    launch = LaunchEnv.from_env(_env(tmp_path, XDG_RUNTIME_DIR=str(tmp_path / "run")))
    assert launch.runtime_root == tmp_path / "run" / "kidnix"


def test_no_runtime_dir_is_not_an_error(tmp_path: Path) -> None:
    assert LaunchEnv.from_env(_env(tmp_path)).runtime_root is None


def test_describe_names_every_variable_a_failed_launch_would_want(tmp_path: Path) -> None:
    line = LaunchEnv.from_env(_env(tmp_path, **{ACTIVITY_ID_VAR: "draw"})).describe()
    assert "draw" in line
    assert "(none)" in line  # the profile
    assert "journal=" in line


# --- the shell really exports both variables -------------------------------


def test_the_launcher_exports_the_profile_id(tmp_path: Path) -> None:
    """The one shell-side change the SDK depends on."""
    from kidnix_shell.launcher import Launcher

    from .conftest import make_activity

    spawned: dict[str, object] = {}

    def spawn(argv: list[str], **kwargs: object) -> object:
        spawned.update(kwargs)
        spawned["argv"] = argv

        class Fake:
            pid = 4321

            def poll(self) -> int | None:
                return None

        return Fake()

    launcher = Launcher(tmp_path, parent_env={}, spawn=spawn)
    launcher.profile_id = "robin"
    launcher.launch(make_activity())
    env = spawned["env"]
    assert isinstance(env, dict)
    assert env[PROFILE_ID_VAR] == "robin"
    assert env[ACTIVITY_ID_VAR] == "scribble"


def test_no_profile_chosen_means_the_variable_is_absent_not_empty(tmp_path: Path) -> None:
    """An empty string would be a profile id called "", which is not one."""
    from kidnix_shell.launcher import Launcher

    from .conftest import make_activity

    spawned: dict[str, object] = {}

    def spawn(argv: list[str], **kwargs: object) -> object:
        spawned.update(kwargs)

        class Fake:
            pid = 1

            def poll(self) -> int | None:
                return None

        return Fake()

    launcher = Launcher(tmp_path, parent_env={}, spawn=spawn)
    launcher.launch(make_activity())
    env = spawned["env"]
    assert isinstance(env, dict)
    assert PROFILE_ID_VAR not in env


# --- SIGTERM ---------------------------------------------------------------


def test_sigterm_calls_on_finish_then_exits_zero() -> None:
    saved: list[str] = []
    codes: list[int] = []
    handler = FinishHandler(lambda: saved.append("saved"), exiter=codes.append)
    handler._on_signal(signal.SIGTERM)
    assert saved == ["saved"]
    assert codes == [SUCCESS_EXIT_CODE]
    assert handler.finished is True
    assert handler.signal_number == int(signal.SIGTERM)


def test_the_second_sigterm_does_not_save_again() -> None:
    """Put away re-asks at the end of the grace. Saving twice would race."""
    saved: list[str] = []
    codes: list[int] = []
    handler = FinishHandler(lambda: saved.append("x"), exiter=codes.append)
    handler._on_signal(signal.SIGTERM)
    handler._on_signal(signal.SIGTERM)
    assert saved == ["x"]
    assert codes == [SUCCESS_EXIT_CODE, SUCCESS_EXIT_CODE]


def test_a_save_that_raises_still_exits_but_not_zero() -> None:
    codes: list[int] = []

    def boom() -> None:
        raise OSError("the disk is full")

    handler = FinishHandler(boom, exiter=codes.append)
    handler.finish()
    assert codes == [FAILED_EXIT_CODE]
    assert handler.exit_code == FAILED_EXIT_CODE


def test_a_keyboard_interrupt_is_deliberately_not_swallowed() -> None:
    codes: list[int] = []

    def boom() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        FinishHandler(boom, exiter=codes.append).finish()
    # BaseException is deliberately NOT swallowed: a KeyboardInterrupt is the
    # interpreter being told to stop, and catching it here would make Ctrl-C
    # in a terminal do nothing twice.


def test_no_on_finish_at_all_is_a_clean_exit() -> None:
    codes: list[int] = []
    FinishHandler(None, exiter=codes.append).finish()
    assert codes == [SUCCESS_EXIT_CODE]


def test_finish_can_be_asked_not_to_exit() -> None:
    codes: list[int] = []
    handler = FinishHandler(lambda: None, exiter=codes.append)
    assert handler.finish(exit_process=False) == SUCCESS_EXIT_CODE
    assert codes == []


def test_install_arms_sigterm_and_sigint() -> None:
    armed: list[int] = []
    handler = FinishHandler(lambda: None)
    result = handler.install(lambda number, _h: armed.append(number))
    assert set(armed) == {int(signal.SIGTERM), int(signal.SIGINT)}
    assert result == lifecycle.FINISH_SIGNALS


def test_a_signal_that_cannot_be_armed_is_skipped_not_fatal() -> None:
    def refuse(number: int, _handler: object) -> None:
        if number == int(signal.SIGINT):
            raise ValueError("not from this thread")

    armed = FinishHandler(lambda: None).install(refuse)
    assert armed == (signal.SIGTERM,)


def test_first_party_activities_are_signal_quitters() -> None:
    assert QUIT_MODE == "signal"


# --- the caption client ----------------------------------------------------


def test_the_socket_path_is_the_documented_one(tmp_path: Path) -> None:
    path = captions.socket_path({"XDG_RUNTIME_DIR": str(tmp_path)})
    assert path == tmp_path / "kidnix" / "captions.sock"


def test_no_runtime_dir_means_no_socket() -> None:
    assert captions.socket_path({}) is None
    assert captions.socket_path({"XDG_RUNTIME_DIR": "  "}) is None


def test_the_payload_is_the_documented_json() -> None:
    data = json.loads(captions.encode("Press the big button.", "hello-draw"))
    assert data == {"speak": "Press the big button.", "source": "hello-draw"}


def test_a_caption_is_one_line_however_it_arrives() -> None:
    assert captions.tidy("  two\n  lines  ") == "two lines"


def test_a_runaway_caption_is_bounded() -> None:
    payload = captions.encode("x" * 5000, "a")
    assert len(json.loads(payload)["speak"]) == captions.MAX_TEXT_CHARS


def test_encode_and_decode_are_the_two_halves_of_one_wire() -> None:
    payload = captions.encode("It is ready.", "sounds-and-words")
    assert captions.decode(payload) == ("It is ready.", "sounds-and-words")


def test_decode_refuses_anything_that_is_not_a_caption() -> None:
    assert captions.decode(b"not json") is None
    assert captions.decode(b"[]") is None
    assert captions.decode(b'{"source": "x"}') is None
    assert captions.decode(b'{"speak": 7}') is None
    assert captions.decode(b'{"speak": "   "}') is None


def test_decode_tolerates_a_missing_source() -> None:
    assert captions.decode(b'{"speak": "hello"}') == ("hello", "")


def test_a_plain_file_is_not_a_socket_and_is_never_written_to(tmp_path: Path) -> None:
    path = tmp_path / "captions.sock"
    path.touch()
    sent: list[bytes] = []

    def sender(_path: Path, payload: bytes) -> bool:
        sent.append(payload)
        return True

    client = CaptionClient("hello-draw", path, sender=sender)
    # ``is_socket`` is what gates the send, and a touched file is not one.
    assert client.send("hi") is False
    assert sent == []


def test_a_real_socket_is_written_to(tmp_path: Path) -> None:
    import socket as socketlib

    path = tmp_path / "captions.sock"
    with socketlib.socket(socketlib.AF_UNIX, socketlib.SOCK_DGRAM) as listener:
        listener.bind(str(path))
        listener.settimeout(1.0)
        client = CaptionClient("hello-draw", path)
        assert client.send("Press the big button.") is True
        assert captions.decode(listener.recv(4096)) == (
            "Press the big button.",
            "hello-draw",
        )


def test_a_missing_socket_is_survivable_and_logged_once(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    client = CaptionClient("hello-draw", tmp_path / "nothing.sock")
    with caplog.at_level("INFO", logger="kidnix_activity.captions"):
        assert client.send("one") is False
        assert client.send("two") is False
    assert sum("captions are not reaching" in r.message for r in caplog.records) == 1


def test_no_runtime_directory_at_all_is_survivable() -> None:
    client = CaptionClient("hello-draw", env={})
    assert client.path is None
    assert client.available is False
    assert client.send("anything") is False


def test_an_empty_caption_is_not_sent(tmp_path: Path) -> None:
    sent: list[bytes] = []

    def sender(_path: Path, payload: bytes) -> bool:
        sent.append(payload)
        return True

    client = CaptionClient("a", tmp_path / "s.sock", sender=sender)
    assert client.send("   ") is False
    assert sent == []


def test_the_last_text_is_remembered_even_when_it_did_not_arrive(tmp_path: Path) -> None:
    client = CaptionClient("a", tmp_path / "missing.sock")
    client.send("  the  line ")
    assert client.last_text == "the line"


def test_availability_is_asked_afresh_so_a_restarted_shell_is_found(tmp_path: Path) -> None:
    import socket as socketlib

    path = tmp_path / "captions.sock"
    client = CaptionClient("a", path)
    assert client.available is False
    with socketlib.socket(socketlib.AF_UNIX, socketlib.SOCK_DGRAM) as listener:
        listener.bind(str(path))
        assert client.available is True
