"""Launching and stopping activities: clean env, and a stop that always stops."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from kidnix_shell.launcher import Launcher, Outcome, build_env

from .conftest import make_activity

DIRTY_ENV = {
    "HOME": "/home/someone-else",
    "PATH": "/usr/bin",
    "WAYLAND_DISPLAY": "wayland-0",
    "XDG_RUNTIME_DIR": "/run/user/1000",
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "LANG": "en_GB.UTF-8",
    "LC_TIME": "en_GB.UTF-8",
    "SSH_AUTH_SOCK": "/run/user/1000/keyring/ssh",
    "AWS_SECRET_ACCESS_KEY": "hunter2",
    "KIDNIX_INTERNAL": "do not leak",
    "EDITOR": "vim",
}


def test_only_allow_listed_variables_survive() -> None:
    env = build_env(Path("/var/home/kid"), DIRTY_ENV)
    for leaked in ("SSH_AUTH_SOCK", "AWS_SECRET_ACCESS_KEY", "KIDNIX_INTERNAL", "EDITOR"):
        assert leaked not in env


def test_the_display_and_bus_do_survive() -> None:
    env = build_env(Path("/var/home/kid"), DIRTY_ENV)
    assert env["WAYLAND_DISPLAY"] == "wayland-0"
    assert env["XDG_RUNTIME_DIR"] == "/run/user/1000"
    assert env["DBUS_SESSION_BUS_ADDRESS"].startswith("unix:")


def test_locale_variables_survive_by_prefix() -> None:
    env = build_env(Path("/var/home/kid"), DIRTY_ENV)
    assert env["LC_TIME"] == "en_GB.UTF-8"
    assert env["LANG"] == "en_GB.UTF-8"


def test_home_and_xdg_dirs_are_forced_under_the_kid_home() -> None:
    env = build_env(Path("/var/home/kid"), DIRTY_ENV)
    assert env["HOME"] == "/var/home/kid"
    assert env["XDG_DATA_HOME"] == "/var/home/kid/.local/share"
    assert env["XDG_CONFIG_HOME"] == "/var/home/kid/.config"
    assert env["XDG_CACHE_HOME"] == "/var/home/kid/.cache"
    assert env["XDG_STATE_HOME"] == "/var/home/kid/.local/state"


def test_a_path_is_always_present() -> None:
    assert build_env(Path("/var/home/kid"), {})["PATH"]


def test_no_proxy_is_set_because_there_is_no_egress() -> None:
    assert build_env(Path("/var/home/kid"), {})["no_proxy"] == "*"


def test_the_activity_id_is_passed_through(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path, DIRTY_ENV)
    running = launcher.launch(make_activity(exec_argv=("/bin/sleep", "5")))
    assert running is not None
    assert running.env["KIDNIX_ACTIVITY_ID"] == "scribble"
    launcher.stop(grace=1)


def test_launching_a_missing_program_fails_gracefully(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path)
    assert launcher.launch(make_activity(exec_argv=("/definitely/not/here",))) is None
    assert not launcher.running


def test_only_one_activity_runs_at_a_time(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path)
    assert launcher.launch(make_activity("a", exec_argv=("/bin/sleep", "5"))) is not None
    assert launcher.launch(make_activity("b", exec_argv=("/bin/sleep", "5"))) is None
    launcher.stop(grace=1)


def test_a_polite_activity_exits_on_sigterm(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path)
    launcher.launch(make_activity(exec_argv=("/bin/sleep", "30")))
    assert launcher.stop(grace=3) == Outcome.TERMINATED
    assert not launcher.running


def test_a_stubborn_activity_gets_killed(tmp_path: Path) -> None:
    """Spec S6: SIGTERM, five seconds of autosave grace, then SIGKILL."""
    script = tmp_path / "stubborn.py"
    script.write_text(
        "import signal, time\n"
        "signal.signal(signal.SIGTERM, lambda *a: None)\n"
        "print('ready', flush=True)\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    launcher = Launcher(tmp_path)
    launcher.launch(make_activity(exec_argv=(sys.executable, str(script))))
    time.sleep(0.5)  # let the handler be installed
    assert launcher.stop(grace=1) == Outcome.KILLED
    assert not launcher.running


def test_stopping_nothing_is_harmless(tmp_path: Path) -> None:
    assert Launcher(tmp_path).stop() == Outcome.NOT_RUNNING


def test_stopping_an_already_exited_activity_reports_exited(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path)
    launcher.launch(make_activity(exec_argv=("/bin/true",)))
    time.sleep(0.3)
    assert launcher.stop() == Outcome.EXITED


def test_request_stop_then_force_stop(tmp_path: Path) -> None:
    """The asynchronous path Put away actually uses."""
    launcher = Launcher(tmp_path)
    launcher.launch(make_activity(exec_argv=("/bin/sleep", "30")))
    assert launcher.request_stop() is True
    time.sleep(0.5)
    assert launcher.force_stop() in (Outcome.TERMINATED, Outcome.KILLED)
    assert not launcher.running


def test_on_exit_fires_once_when_the_activity_goes_away(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path)
    seen: list[int] = []
    launcher.on_exit = lambda running, code: seen.append(code)
    launcher.launch(make_activity(exec_argv=("/bin/true",)))
    for _ in range(50):
        if launcher.check() is not None:
            break
        time.sleep(0.05)
    assert seen == [0]
    assert launcher.check() is None  # not fired twice


def test_the_activity_gets_its_own_process_group(tmp_path: Path) -> None:
    launcher = Launcher(tmp_path)
    running = launcher.launch(make_activity(exec_argv=("/bin/sleep", "5")))
    assert running is not None
    assert os.getpgid(running.pid) != os.getpgid(os.getpid())
    launcher.stop(grace=1)


def test_resume_passes_the_file_to_the_activity(tmp_path: Path) -> None:
    recorded: dict[str, object] = {}

    class FakeProcess:
        pid = 4242

        def poll(self) -> int | None:
            return None

    def fake_spawn(argv: list[str], **kwargs: object) -> FakeProcess:
        recorded["argv"] = argv
        return FakeProcess()

    launcher = Launcher(tmp_path, spawn=fake_spawn)
    activity = make_activity(exec_argv=("draw",), exec_resume=("draw", "--open", "{file}"))
    launcher.launch(activity, resume_path=tmp_path / "picture.png")
    assert recorded["argv"] == ["draw", "--open", str(tmp_path / "picture.png")]
