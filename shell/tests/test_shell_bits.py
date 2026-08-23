"""Pagination, offline suggestions, count words, and the CLI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from kidnix_shell.cli import build_parser, main
from kidnix_shell.suggestions import BY_ACTIVITY, GENERAL, offline_suggestion
from kidnix_shell.util import clamp, paginate


def test_paginate_splits_evenly() -> None:
    assert paginate(list(range(8)), 4) == [[0, 1, 2, 3], [4, 5, 6, 7]]


def test_paginate_keeps_a_short_last_page() -> None:
    assert paginate(list(range(5)), 4) == [[0, 1, 2, 3], [4]]


def test_paginate_gives_one_empty_page_for_nothing() -> None:
    assert paginate([], 12) == [[]]


def test_paginate_rejects_a_nonsense_page_size() -> None:
    with pytest.raises(ValueError):
        paginate([1, 2], 0)


def test_twelve_activities_fit_on_one_page() -> None:
    """Spec S2 / SYNTHESIS B2: at most 12 tiles, one page."""
    assert len(paginate(list(range(12)), 12)) == 1
    assert len(paginate(list(range(13)), 12)) == 2


def test_clamp() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(99, 0, 10) == 10


def test_an_offline_suggestion_is_keyed_to_the_activity() -> None:
    line = offline_suggestion("tuxpaint", "make", today=date(2026, 8, 18))
    assert line in BY_ACTIVITY["tuxpaint"]


def test_an_unknown_activity_falls_back_to_its_category() -> None:
    line = offline_suggestion("something-new", "make", today=date(2026, 8, 18))
    assert "paper" in line or "show" in line


def test_there_is_always_a_line() -> None:
    assert offline_suggestion("", "", today=date(2026, 8, 18)) in GENERAL


def test_the_suggestion_is_stable_within_a_day() -> None:
    first = offline_suggestion("tuxpaint", "make", today=date(2026, 8, 18))
    second = offline_suggestion("tuxpaint", "make", today=date(2026, 8, 18))
    assert first == second


def test_no_suggestion_promises_the_child_will_come_back() -> None:
    """SYNTHESIS D6: the system has no interest in whether the child returns."""
    everything = [line for lines in [*BY_ACTIVITY.values(), GENERAL] for line in lines]
    for line in everything:
        lowered = line.lower()
        assert "tomorrow" not in lowered
        assert "next time" not in lowered
        assert "come back" not in lowered


def test_the_goodbye_headline_uses_words_not_digits() -> None:
    pytest.importorskip("gi")
    from kidnix_shell.screens.goodbye import count_phrase

    assert count_phrase(0) == "nothing"
    assert count_phrase(3) == "three things"
    assert count_phrase(12) == "12 things"


# --- CLI -----------------------------------------------------------------


def test_the_parser_accepts_the_documented_flags() -> None:
    args = build_parser().parse_args(["--demo", "--windowed", "--run-seconds", "5"])
    assert args.demo and args.windowed and args.run_seconds == 5


def test_validate_manifests_takes_an_optional_directory() -> None:
    assert build_parser().parse_args(["--validate-manifests"]).validate_manifests == ""
    assert build_parser().parse_args(["--validate-manifests", "/x"]).validate_manifests == "/x"


def test_validate_manifests_passes_on_good_files(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.toml").write_text('id = "a"\nname = "A"\nexec = ["a"]\n', encoding="utf-8")
    assert main(["--validate-manifests", str(tmp_path)]) == 0
    assert "1 valid, 0 invalid" in capsys.readouterr().out


def test_validate_manifests_fails_on_a_bad_file(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.toml").write_text('id = "a"\n', encoding="utf-8")
    assert main(["--validate-manifests", str(tmp_path)]) == 1
    assert "0 valid, 1 invalid" in capsys.readouterr().out


def test_validate_manifests_reports_a_missing_directory(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--validate-manifests", str(tmp_path / "nope")]) == 0
    assert "no such directory" in capsys.readouterr().out


def test_the_shipped_manifests_pass_the_ci_gate() -> None:
    shipped = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"
    if not shipped.is_dir():
        pytest.skip("running outside the kidnix checkout")
    assert main(["--validate-manifests", str(shipped)]) == 0


# --- "All done" has one cell and never leaves it (panel ruling, 2026-08-23)


def test_all_done_is_the_last_cell_of_the_second_row() -> None:
    from kidnix_shell.screens.home import ALL_DONE, ALL_DONE_INDEX, all_done_index, lay_out

    assert ALL_DONE_INDEX == 7
    assert all_done_index(8) == 7
    assert all_done_index(12) == 7
    cells = lay_out([f"a{i}" for i in range(11)], all_done_index(12))
    assert cells[7] is ALL_DONE


def test_all_done_does_not_move_as_tiles_are_revealed() -> None:
    """forum #5, #41: it used to shift one cell every reveal."""
    from kidnix_shell.screens.home import ALL_DONE, all_done_index, lay_out

    index = all_done_index(8)
    for revealed in range(0, 12):
        cells = lay_out([f"a{i}" for i in range(revealed)], index)
        assert cells[index] is ALL_DONE
        assert cells.count(ALL_DONE) == 1


def test_a_grid_too_small_for_cell_seven_keeps_it_on_the_page() -> None:
    """An escape hatch on page two is not an escape hatch."""
    from kidnix_shell.screens.home import ALL_DONE, all_done_index, lay_out

    index = all_done_index(6)  # a 3x2 panel
    assert index == 5
    cells = lay_out([f"a{i}" for i in range(9)], index)
    assert cells[5] is ALL_DONE


def test_the_cells_before_it_stay_empty_rather_than_closing_up() -> None:
    from kidnix_shell.screens.home import ALL_DONE, lay_out

    cells = lay_out(["a", "b"], 7)
    assert cells == ["a", "b", None, None, None, None, None, ALL_DONE]


def test_activities_past_the_pinned_cell_carry_on_after_it() -> None:
    from kidnix_shell.screens.home import ALL_DONE, lay_out

    cells = lay_out([f"a{i}" for i in range(9)], 7)
    assert cells[7] is ALL_DONE
    assert cells[8:] == ["a7", "a8"]


# --- the grown-up sheet says no in words (forum #59, #60) ----------------


def test_a_refused_grant_names_the_minimum() -> None:
    from kidnix_shell.screens.grownup import grant_refusal

    line = grant_refusal(5, floor_minutes=5, left_minutes=2)
    assert "5 minutes" in line
    assert "2 minutes" in line
    assert line.startswith("Not added")


def test_the_refusal_is_singular_when_it_should_be() -> None:
    from kidnix_shell.screens.grownup import grant_refusal

    assert "1 minute left" in grant_refusal(5, floor_minutes=5, left_minutes=1)


def test_the_sheet_points_at_a_command_that_exists() -> None:
    """ "do not pretend": the sheet's fallback has to be runnable."""
    from kidnix_shell.screens.grownup import SET_PIN_COMMAND

    # `kidnix-set-pin` is the image's own wrapper; `kidnix-shell --set-pin` is
    # what it runs, and is still the command on a machine without the wrapper.
    assert SET_PIN_COMMAND == "sudo kidnix-set-pin"
    assert build_parser().parse_args(["--set-pin"]).set_pin == ""


# --- and says how long its own settings last -----------------------------


def test_a_memory_only_control_keeps_its_own_sentence_and_gains_one() -> None:
    """Volume, mute, calm mode and captions apply now and are gone at reboot.

    They go through ``host.set_access`` and touch no file -- the config is
    root-owned on purpose -- so the row has to say so. Its own first sentence
    is untouched; the shared one is appended.
    """
    from kidnix_shell.screens.grownup import UNTIL_SWITCHED_OFF, until_off

    line = until_off("Silence, not a broken machine.")
    assert line.startswith("Silence, not a broken machine.")
    assert line.endswith(UNTIL_SWITCHED_OFF)
    assert "Parent Panel" in line


def test_the_sheet_tells_the_truth_about_the_panel_and_the_way_to_it() -> None:
    """The panel shipped; the sheet used to say it was "not yet built".

    It is still not opened from the child's session -- it is the parent
    login's -- so what this row owes a grown-up is the route, and every step
    of it has to be real: the Log out row below, the `parent` account, and the
    `Parent Panel` entry in Applications
    (``system_files/usr/share/applications/kidnix-parent-panel.desktop``).
    """
    from kidnix_shell.screens.grownup import PANEL_ROUTE, PANEL_SUBTITLE, PANEL_TITLE

    assert PANEL_TITLE == "Parent panel"
    for text in (PANEL_ROUTE, PANEL_SUBTITLE):
        for lie in ("not in v0.1", "not yet built", "will hold"):
            assert lie not in text
    assert "Log out" in PANEL_ROUTE
    assert "parent" in PANEL_ROUTE
    assert "Parent Panel" in PANEL_ROUTE and "Applications" in PANEL_ROUTE


def test_the_desktop_entry_the_sheet_names_is_the_one_the_image_ships() -> None:
    """The two halves of the route, checked against each other.

    A sentence naming a menu entry is a promise about a file, and this is the
    file. If somebody renames the desktop entry, this fails here rather than
    in front of a parent at a login screen.
    """
    from pathlib import Path

    from kidnix_shell.screens.grownup import PANEL_ROUTE

    entry = (
        Path(__file__).resolve().parents[2]
        / "system_files/usr/share/applications/kidnix-parent-panel.desktop"
    )
    text = entry.read_text(encoding="utf-8")
    assert "Name=Parent Panel" in text
    assert "Name=Parent Panel".removeprefix("Name=") in PANEL_ROUTE
    assert "Exec=/usr/bin/kidnix-parent-panel" in text


# --- no return promises anywhere the child can hear one (D6) ------------


def test_no_child_facing_string_in_the_shell_promises_a_return() -> None:
    """forum #28, #47: "See you next time" and "See you tomorrow" were both
    shipped, and both fired on the child's flattest day. The daytime
    vocabulary has no "tomorrow" in it at all."""
    import ast

    import kidnix_shell

    root = Path(kidnix_shell.__file__).parent
    banned = ("see you next time", "see you tomorrow", "see you next")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            id(ast.get_docstring(node, clean=False))
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node.value) in docstrings:
                continue
            for phrase in banned:
                assert phrase not in node.value.lower(), f"{path.name} still says {phrase!r}"


# --- night words live in one file, and are reached through one pair of
#     functions (forum #17) ------------------------------------------------


def test_the_word_goodnight_exists_in_exactly_one_module() -> None:
    """The mirror of the test above, for the *other* thing a four-o'clock
    session used to say.

    "Goodnight" is true between 19:00 and 07:00 and is a sleep-onset cue at any
    other hour, so it belongs to :mod:`kidnix_shell.resting`'s bedtime
    vocabulary and is reached only through ``goodnight_label`` /
    ``goodnight_speech``. It escaped once already: the Goodbye button's printed
    label was switched on ``is_bedtime`` and its ``speak_text`` -- the
    accessible name, the read-aloud *and* the caption, one string for all three
    -- was the literal "Goodnight", so the cue kept arriving through the two
    channels a pre-reader actually has. A literal anywhere else is that bug
    again, whether or not anyone notices which channel it took.
    """
    import ast

    import kidnix_shell

    root = Path(kidnix_shell.__file__).parent
    #: Where the bedtime vocabulary is defined, and may say its own name.
    home = "resting.py"
    #: `State.GOODNIGHT` / `Event.GOODNIGHT` -- internal tokens in the state
    #: machine's own alphabet. Never rendered, never spoken, never captioned.
    tokens = {"goodnight"}
    for path in root.rglob("*.py"):
        if path.name == home:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            id(ast.get_docstring(node, clean=False))
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node.value) in docstrings or node.value in tokens:
                continue
            assert "goodnight" not in node.value.lower(), (
                f"{path.name} has a literal 'Goodnight'; take it from "
                f"kidnix_shell.{home[:-3]} so it only appears at bedtime"
            )


# --- "Show a grown-up" is not on a two-minute clock any more --------------


def test_showing_is_not_revoked_mid_narration() -> None:
    """forum #52: co-use is the strongest protective moderator in the corpus,
    and it was on a two-minute timer that yanked the screen back."""
    from kidnix_shell.app import SHOWING_SECONDS

    assert SHOWING_SECONDS >= 600


def test_back_out_of_whats_next_after_goes_to_whos_here() -> None:
    """Spec 7b: no exit friction, and S1b has a way out that is not a plan."""
    from kidnix_shell.state import TRANSITIONS, Event, State

    assert TRANSITIONS[State.NEXT_CHOICE][Event.BACK] is State.CHOOSING


def test_not_sure_yet_is_an_option_that_is_not_a_plan() -> None:
    from kidnix_shell.next_after import DEFAULT_NEXT_AFTER, SKIP_ID

    skips = [option for option in DEFAULT_NEXT_AFTER if option.skips]
    assert [option.id for option in skips] == [SKIP_ID]
    assert all(not option.skips for option in DEFAULT_NEXT_AFTER if option.id != SKIP_ID)


# --- the root helper the sheet points at ---------------------------------


def test_set_pin_refuses_a_directory_it_cannot_write(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    from kidnix_shell.cli import set_pin

    missing = tmp_path / "nowhere" / "parent.toml"
    assert set_pin(str(missing)) == 1
    assert "sudo kidnix-shell --set-pin" in capsys.readouterr().out


def test_set_pin_refuses_the_shipped_pin(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    """ "still 1234 means unconfigured, never secured" (hardening.md section 6)."""
    import getpass

    from kidnix_shell.cli import set_pin

    path = tmp_path / "parent.toml"
    path.write_text("default_session_minutes = 25\n", encoding="utf-8")
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: "1234")
    assert set_pin(str(path)) == 1
    assert "Pick another" in capsys.readouterr().out


def test_set_pin_writes_a_pin_it_can_write(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import getpass

    from kidnix_shell.cli import set_pin
    from kidnix_shell.settings import ParentConfig

    path = tmp_path / "parent.toml"
    path.write_text("default_session_minutes = 25\n", encoding="utf-8")
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: "8351")
    assert set_pin(str(path)) == 0
    assert ParentConfig.load(path).check_pin("8351")
