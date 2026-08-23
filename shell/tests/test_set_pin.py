"""The shell's half of the ``kidnix-set-pin`` contract (wave F).

``docs/spikes/pin-flow.md`` section 5 left one thing open: the sheet sent
**one** line where the helper's ``--stdin`` protocol has two -- line 1 the new
PIN, line 2 the current one -- so the *first* set from the grown-up sheet
persisted and a later **change** came back exit 4 and quietly degraded to a PIN
that lasted until the next restart. That is the gap these tests hold shut.

They run a **fake helper**: a shell script that speaks the same four exit codes
and records what arrived on its stdin. Nothing here needs pkexec, root, a
display or the image, and the one thing that cannot be faked -- polkit actually
saying yes to the `kid` account -- is asserted on a booted machine by
``tests/boot/bcvk_boot_test.py::assert_pin``.

The other rule under test is the quiet one: **no digit ever reaches a message
or a log line.** A PIN a grown-up can read off the sheet after the fact, or a
child can find in the journal, is the same failure as an echoed one.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

import pytest

from kidnix_shell.screens.grownup import (
    ALREADY_SET_MESSAGE,
    EXIT_ALREADY_SET,
    EXIT_BAD_PIN,
    EXIT_REFUSED,
    SET_PIN_READ_ONLY,
    TOO_MANY_TRIES,
    WRONG_CURRENT_PIN,
    HelperOutcome,
    call_set_pin,
    helper_outcome,
)

#: Not 1234: the helper refuses that one, and a test that used it would be
#: asserting the wrong refusal.
NEW_PIN = "8471"
CURRENT_PIN = "2468"

WRITTEN_PATH = "/etc/kidnix/parent.toml"

#: The helper's own wording for the two answers that share exit 3. The shell
#: tells them apart by this sentence, so the test uses the real one.
LOCKED_OUT_STDERR = "kidnix-set-pin: too many wrong PINs in the last minute; wait a minute"
WRONG_PIN_STDERR = "kidnix-set-pin: that is not the current PIN; nothing was changed"


def fake_helper(tmp_path: Path, *, exit_code: int = 0, stderr: str = "") -> tuple[list[str], Path]:
    """A stand-in for ``pkexec kidnix-set-pin --stdin``.

    Returns ``(argv, transcript)``. The transcript is everything the helper was
    given on stdin, verbatim and in order, which is the only way to prove the
    two lines go in the order the contract names.
    """
    transcript = tmp_path / "stdin.txt"
    script = tmp_path / "fake-set-pin"
    script.write_text(
        "#!/usr/bin/bash\n"
        f"cat > {transcript}\n"
        + (f"printf '%s\\n' {stderr!r} >&2\n" if stderr else "")
        + (f"printf '%s\\n' {WRITTEN_PATH}\n" if exit_code == 0 else "")
        + f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return ([str(script)], transcript)


# --- the stdin protocol ----------------------------------------------------


def test_the_first_set_sends_one_line_and_nothing_else(tmp_path: Path) -> None:
    """No PIN on the machine means nothing to prove: the first-set path is
    unchanged, and must stay that way (pin-flow.md section 2, rule 1)."""
    argv, transcript = fake_helper(tmp_path)

    outcome = call_set_pin(NEW_PIN, None, argv=argv)

    assert outcome.written
    assert transcript.read_text(encoding="utf-8") == f"{NEW_PIN}\n"


def test_a_change_sends_the_new_pin_then_the_current_one(tmp_path: Path) -> None:
    """**The order is the contract.** Line 1 is the new PIN and line 2 the
    current one; swapping them would set the child's guess as the new PIN on a
    machine where the guess happened to be right."""
    argv, transcript = fake_helper(tmp_path)

    outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    assert outcome.written
    assert transcript.read_text(encoding="utf-8") == f"{NEW_PIN}\n{CURRENT_PIN}\n"


def test_neither_pin_is_ever_an_argument(tmp_path: Path) -> None:
    """``argv`` is world-readable in ``/proc`` for as long as the helper runs."""
    argv, _ = fake_helper(tmp_path)
    marker = tmp_path / "argv.txt"
    script = Path(argv[0])
    script.write_text(
        f"#!/usr/bin/bash\ncat > /dev/null\nprintf '%s\\n' \"$@\" > {marker}\n"
        f"printf '%s\\n' {WRITTEN_PATH}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)

    call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    assert NEW_PIN not in marker.read_text(encoding="utf-8")
    assert CURRENT_PIN not in marker.read_text(encoding="utf-8")


# --- the exit codes, which are the contract --------------------------------


def test_a_written_pin_says_where_it_went(tmp_path: Path) -> None:
    argv, _ = fake_helper(tmp_path, exit_code=0)

    outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    assert outcome == HelperOutcome(True, f"New PIN saved to {WRITTEN_PATH}.", False)


def test_a_wrong_current_pin_is_said_in_those_words(tmp_path: Path) -> None:
    argv, _ = fake_helper(tmp_path, exit_code=EXIT_BAD_PIN, stderr=WRONG_PIN_STDERR)

    outcome = call_set_pin(NEW_PIN, "0000", argv=argv)

    assert not outcome.written
    assert outcome.warn
    assert outcome.message.startswith(WRONG_CURRENT_PIN)


def test_the_lockout_is_told_apart_from_a_wrong_pin(tmp_path: Path) -> None:
    """Both are exit 3, and only the helper's own sentence separates them. It
    matters: "wait a minute" is actionable and "that was wrong" is not, and a
    parent told the wrong one will keep typing into a rate limiter."""
    argv, _ = fake_helper(tmp_path, exit_code=EXIT_BAD_PIN, stderr=LOCKED_OUT_STDERR)

    outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    assert not outcome.written
    assert outcome.message.startswith(TOO_MANY_TRIES)
    assert WRONG_CURRENT_PIN not in outcome.message


def test_exit_four_is_the_shell_having_sent_too_little(tmp_path: Path) -> None:
    """Exit 4 is "a PIN is set and none was proved" -- i.e. a bug in this file
    rather than anything the grown-up did, phrased for the grown-up anyway."""
    argv, _ = fake_helper(tmp_path, exit_code=EXIT_ALREADY_SET)

    outcome = call_set_pin(NEW_PIN, None, argv=argv)

    assert outcome == HelperOutcome(False, ALREADY_SET_MESSAGE, True)


def test_a_refusal_falls_back_to_the_honest_sentence(tmp_path: Path) -> None:
    argv, _ = fake_helper(tmp_path, exit_code=EXIT_REFUSED, stderr="kidnix-set-pin: refused")

    outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    assert outcome == HelperOutcome(False, SET_PIN_READ_ONLY, True)


def test_a_helper_that_is_not_there_is_not_a_crash(tmp_path: Path) -> None:
    outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=[str(tmp_path / "nope")])

    assert outcome == HelperOutcome(False, SET_PIN_READ_ONLY, True)


def test_a_helper_that_hangs_is_not_a_frozen_shell(tmp_path: Path) -> None:
    """A polkit prompt nobody can answer must not become a shell that has
    stopped responding to a five-year-old."""
    script = tmp_path / "slow"
    script.write_text("#!/usr/bin/bash\nsleep 30\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)

    outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=[str(script)], timeout=0.5)

    assert outcome == HelperOutcome(False, SET_PIN_READ_ONLY, True)


# --- nothing anywhere says a digit -----------------------------------------


@pytest.mark.parametrize(
    ("code", "stderr"),
    [
        (0, ""),
        (EXIT_REFUSED, "kidnix-set-pin: refused"),
        (EXIT_BAD_PIN, WRONG_PIN_STDERR),
        (EXIT_BAD_PIN, LOCKED_OUT_STDERR),
        (EXIT_ALREADY_SET, ""),
    ],
)
def test_no_outcome_and_no_log_line_carries_a_digit(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, code: int, stderr: str
) -> None:
    argv, _ = fake_helper(tmp_path, exit_code=code, stderr=stderr)

    with caplog.at_level(logging.DEBUG, logger="kidnix_shell.screens.grownup"):
        outcome = call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    written = outcome.message + "\n" + caplog.text
    assert NEW_PIN not in written
    assert CURRENT_PIN not in written
    # Not a length or a first character either.
    assert "4 digits" not in written.lower()


def test_the_environment_never_carries_a_pin(tmp_path: Path) -> None:
    """The other route an argument-shaped mistake takes. ``call_set_pin``
    inherits the environment and adds nothing to it, so this is a regression
    guard rather than a discovery."""
    argv, _ = fake_helper(tmp_path)
    dumped = tmp_path / "env.txt"
    script = Path(argv[0])
    script.write_text(
        f"#!/usr/bin/bash\ncat > /dev/null\nenv > {dumped}\nprintf '%s\\n' {WRITTEN_PATH}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)

    call_set_pin(NEW_PIN, CURRENT_PIN, argv=argv)

    body = dumped.read_text(encoding="utf-8")
    assert NEW_PIN not in body
    assert CURRENT_PIN not in body
    assert os.environ.get("PATH", "") in body or "PATH=" in body


# --- the mapping on its own ------------------------------------------------


def test_an_empty_stdout_still_names_a_file() -> None:
    """The helper prints the path it wrote; a build that stopped printing it
    must not turn "saved" into a sentence with a hole in it."""
    outcome = helper_outcome(0, "", "")

    assert outcome.written
    assert WRITTEN_PATH in outcome.message


def test_an_unknown_exit_code_is_treated_as_a_refusal() -> None:
    """64 is usage, and anything else is a helper we do not know. Both mean
    the file was not written, which is the only thing the sheet may claim."""
    assert helper_outcome(64, "", "").message == SET_PIN_READ_ONLY
    assert helper_outcome(199, "", "").message == SET_PIN_READ_ONLY
