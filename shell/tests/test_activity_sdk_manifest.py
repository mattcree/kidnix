"""Manifest validation, the scaffolder, and the example that keeps them honest."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from kidnix_activity import cli, manifest, scaffold
from kidnix_activity.examples import hello_draw
from kidnix_activity.manifest import render_manifest, validate_data, validate_file

EXAMPLE = Path(hello_draw.__file__).parent / "hello-draw.toml"


def good() -> dict[str, object]:
    return {
        "schema": 1,
        "id": "clock-and-time",
        "name": "Clock and time",
        "audio_label": "Clock and time. Play with the clock.",
        "goal": "A clock a child can turn, and a routine strip.",
        "icon": "kidnix-clock",
        "category": "learn",
        "age_band": "5-7",
        "exec": ["/usr/bin/kidnix-clock-and-time"],
        "quit": "signal",
        "network_required": False,
    }


def report(**changes: object) -> manifest.Report:
    data = good()
    data.update(changes)
    for key, value in list(data.items()):
        if value is None:
            del data[key]
    return validate_data(data, Path("clock-and-time.toml"))


# --- the rules the shell cannot enforce and we must -----------------------


def test_a_good_manifest_passes_with_nothing_to_say() -> None:
    result = report()
    assert result.ok
    assert result.warnings == []
    assert result.activity is not None
    assert result.activity.id == "clock-and-time"


def test_the_network_is_never_allowed() -> None:
    result = report(network_required=True)
    assert not result.ok
    assert any("egress" in line for line in result.errors)


def test_a_quit_dialogue_is_never_allowed() -> None:
    result = report(quit="confirm")
    assert not result.ok
    assert any("SIGTERM" in line for line in result.errors)


def test_an_activity_must_say_what_it_is_for() -> None:
    assert any("goal" in line for line in report(goal=None).errors)


def test_an_activity_must_have_something_to_say_aloud() -> None:
    assert any("audio_label" in line for line in report(audio_label=None).errors)


def test_an_activity_must_have_a_picture() -> None:
    assert any("icon" in line for line in report(icon=None).errors)


def test_a_shelf_is_not_something_an_activity_can_be() -> None:
    result = report(kind="shelf", children_dir="children")
    assert not result.ok
    assert any("shelf" in line for line in result.errors)


def test_the_shells_own_parser_still_gets_the_first_word() -> None:
    result = report(id="Clock And Time")
    assert not result.ok
    assert any("lowercase" in line for line in result.errors)


def test_a_manifest_that_is_not_toml_at_all_is_a_report_not_a_traceback(
    tmp_path: Path,
) -> None:
    path = tmp_path / "broken.toml"
    path.write_text("id = [", encoding="utf-8")
    result = validate_file(path)
    assert not result.ok
    assert "not valid TOML" in result.errors[0]


def test_a_manifest_that_is_not_there_is_a_report_not_a_traceback(tmp_path: Path) -> None:
    result = validate_file(tmp_path / "absent.toml")
    assert not result.ok
    assert "cannot be read" in result.errors[0]


# --- warnings: true, but not fatal ---------------------------------------


def test_watching_a_directory_is_a_warning_because_the_sdk_writes_directly() -> None:
    result = report(journal_watch=["~/Pictures"])
    assert result.ok
    assert any("save_entry" in line for line in result.warnings)


def test_no_age_band_is_a_warning_not_an_error() -> None:
    result = report(age_band=None)
    assert result.ok
    assert any("four-year-old" in line for line in result.warnings)


def test_resume_is_a_warning_because_it_is_easy_to_claim_and_hard_to_keep() -> None:
    result = report(exec_resume=["/usr/bin/kidnix-clock-and-time", "%f"])
    assert result.ok
    assert any("resume" in line for line in result.warnings)


def test_the_report_reads_as_sentences_with_the_path_on_them() -> None:
    lines = report(network_required=True, age_band=None).lines()
    assert all(line.startswith("clock-and-time.toml:") for line in lines)
    assert any("warning:" in line for line in lines)


# --- the template ---------------------------------------------------------


def test_the_template_the_scaffolder_writes_validates() -> None:
    text = render_manifest("clock-and-time", "Clock and time", goal="A clock a child can turn.")
    data = tomllib.loads(text)
    result = validate_data(data, Path("clock-and-time.toml"))
    assert result.ok, result.lines()


def test_the_template_never_ships_the_network_or_a_dialogue() -> None:
    data = tomllib.loads(render_manifest("x", "X"))
    assert data["network_required"] is False
    assert data["quit"] == "signal"


# --- the scaffolder -------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "activity_id", "module"),
    [
        ("Clock and time", "clock-and-time", "clock_and_time"),
        ("Sounds & Words", "sounds-words", "sounds_words"),
        ("listen", "listen", "listen"),
        ("Letters  to   family", "letters-to-family", "letters_to_family"),
    ],
)
def test_one_name_becomes_three_spellings(given: str, activity_id: str, module: str) -> None:
    names = scaffold.names_for(given)
    assert names.activity_id == activity_id
    assert names.module == module
    assert names.title == " ".join(given.split())


@pytest.mark.parametrize("given", ["", "   ", "!!!", "-"])
def test_a_name_with_nothing_in_it_is_refused(given: str) -> None:
    with pytest.raises(ValueError, match="activity id"):
        scaffold.names_for(given)


def test_the_skeleton_is_a_package_with_a_manifest_and_a_test(tmp_path: Path) -> None:
    written = scaffold.scaffold("Clock and time", tmp_path)
    names = {path.relative_to(tmp_path / "clock-and-time").as_posix() for path in written}
    assert names == {
        "clock-and-time.toml",
        "pyproject.toml",
        "README.md",
        "clock_and_time/__init__.py",
        "clock_and_time/__main__.py",
        "clock_and_time/activity.py",
        "tests/__init__.py",
        "tests/test_clock_and_time.py",
    }


def test_the_scaffolded_manifest_validates(tmp_path: Path) -> None:
    scaffold.scaffold("Clock and time", tmp_path, goal="A clock a child can turn.")
    result = validate_file(tmp_path / "clock-and-time" / "clock-and-time.toml")
    assert result.ok, result.lines()


def test_the_scaffolded_python_is_syntactically_real(tmp_path: Path) -> None:
    scaffold.scaffold("Clock and time", tmp_path)
    for name in ("clock_and_time/activity.py", "clock_and_time/__main__.py"):
        source = (tmp_path / "clock-and-time" / name).read_text(encoding="utf-8")
        compile(source, name, "exec")


def test_the_scaffolder_refuses_to_clobber_a_weeks_work(tmp_path: Path) -> None:
    scaffold.scaffold("Clock and time", tmp_path)
    with pytest.raises(FileExistsError, match="--force"):
        scaffold.scaffold("Clock and time", tmp_path)
    scaffold.scaffold("Clock and time", tmp_path, overwrite=True)


# --- the command ----------------------------------------------------------


def test_validate_exits_zero_on_a_good_manifest(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate", str(EXAMPLE)]) == 0
    assert "ok" in capsys.readouterr().out


def test_validate_exits_non_zero_on_a_bad_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.toml"
    path.write_text('id = "x"\nname = "X"\nexec = ["/bin/true"]\n', encoding="utf-8")
    assert cli.main(["validate", str(path)]) == 1
    assert "goal" in capsys.readouterr().err


def test_validate_takes_a_directory(tmp_path: Path) -> None:
    scaffold.scaffold("Clock and time", tmp_path)
    assert cli.main(["validate", str(tmp_path / "clock-and-time")]) == 0


def test_validate_says_so_when_there_is_nothing_to_check(tmp_path: Path) -> None:
    assert cli.main(["validate", str(tmp_path)]) == 1


def test_new_writes_the_skeleton_and_lists_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["new", "Clock and time", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "clock-and-time.toml" in out
    assert (tmp_path / "clock-and-time" / "pyproject.toml").is_file()


def test_new_refuses_a_name_it_cannot_turn_into_an_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["new", "!!!", "--dir", str(tmp_path)]) == 1
    assert "activity id" in capsys.readouterr().err


# --- the example ----------------------------------------------------------


def test_the_example_manifest_validates() -> None:
    result = validate_file(EXAMPLE)
    assert result.ok, result.lines()
    assert result.warnings == [] or all("age_band" not in w for w in result.warnings)


def test_the_example_is_not_installed_on_the_image() -> None:
    """It is a demonstration. A child's Home has room for about eight things."""
    shipped = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"
    assert shipped.is_dir()
    assert not (shipped / "hello-draw.toml").exists()
