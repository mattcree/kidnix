"""The grown-up's file: read it, and never fall over it.

The rule this module is held to is that **nothing here ever raises**. A missing
file, a malformed one, a typo in a time, a list where a table should be -- all
of them come back as the defaults with a line in the log. A five-year-old told
the computer is broken because a grown-up mistyped a TOML key has been failed
twice.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from clock_time.routine import DEFAULT_ROUTINE
from clock_time.settings import (
    CONFIG_NAME,
    MAX_ROUTINE_ITEMS,
    ParentSettings,
    config_candidates,
    load_settings,
    read_document,
    settings_from_document,
)
from clock_time.words import Mode

SHIPPED = Path(__file__).resolve().parent.parent / CONFIG_NAME


def write(directory: Path, text: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CONFIG_NAME
    path.write_text(text, encoding="utf-8")
    return path


# --- where it is read from --------------------------------------------------


def test_the_parents_copy_is_read_before_the_images():
    """bootc's three-way merge makes /etc theirs and /usr/share ours."""
    assert [str(path) for path in config_candidates()] == [
        f"/etc/kidnix/{CONFIG_NAME}",
        f"/usr/share/kidnix/{CONFIG_NAME}",
    ]


def test_the_search_path_is_root_owned_and_never_the_childs_own_config():
    """The child owns $XDG_CONFIG_HOME; a year band a child can edit is not a
    statement about what their school has taught."""
    for path in config_candidates():
        assert str(path).startswith(("/etc/", "/usr/"))


def test_the_first_readable_file_wins(tmp_path):
    write(tmp_path / "etc", '[clock]\nmode = "y2"\n')
    write(tmp_path / "usr", '[clock]\nmode = "y1"\n')
    settings = load_settings(search=[tmp_path / "etc", tmp_path / "usr"])
    assert settings.mode is Mode.Y2


def test_a_missing_first_file_falls_through_to_the_second(tmp_path):
    write(tmp_path / "usr", '[clock]\nmode = "y2"\n')
    settings = load_settings(search=[tmp_path / "nothing", tmp_path / "usr"])
    assert settings.mode is Mode.Y2


def test_no_file_anywhere_is_the_defaults_and_says_so(tmp_path):
    settings = load_settings(search=[tmp_path / "nope"])
    assert settings.is_default
    assert settings.source is None
    assert settings.mode is Mode.Y1
    assert settings.routine.items == DEFAULT_ROUTINE


def test_a_file_that_was_read_is_named_so_a_parent_pane_can_say_whose_it_is(tmp_path):
    path = write(tmp_path / "etc", '[clock]\nmode = "y2"\n')
    settings = load_settings(search=[tmp_path / "etc"])
    assert settings.source == path
    assert not settings.is_default


def test_a_file_with_every_line_commented_out_is_not_an_answer(tmp_path):
    """What the image actually ships as /etc/kidnix/clock_time.toml.

    It parses -- it is valid TOML -- and it says nothing. A reader that took
    "this file exists" for "a grown-up decided" would hand kidnix's own default
    day back to a parent as their own statement, and the parent pane would have
    no way to say *nobody has told us yet*. So an empty document falls through
    to the next candidate, and then to the built-in day.
    """
    write(tmp_path / "etc", "# mode = \"y2\"\n# nothing is set here at all\n")
    settings = load_settings(search=[tmp_path / "etc"])
    assert settings.is_default
    assert settings.source is None
    assert settings.mode is Mode.Y1
    assert settings.routine.items == DEFAULT_ROUTINE


def test_an_empty_first_file_falls_through_to_a_second_that_says_something(tmp_path):
    """/etc is the parent's and /usr/share is ours. A parent who has not
    written anything must not shadow the image's own default file."""
    write(tmp_path / "etc", "# nothing\n")
    write(tmp_path / "usr", '[clock]\nmode = "y2"\n')
    settings = load_settings(search=[tmp_path / "etc", tmp_path / "usr"])
    assert settings.mode is Mode.Y2
    assert settings.source == tmp_path / "usr" / CONFIG_NAME


def test_an_unreadable_file_is_not_an_exception(tmp_path):
    directory = tmp_path / "etc"
    write(directory, "this is not toml = = =\n")
    assert read_document(directory / CONFIG_NAME) is None
    assert load_settings(search=[directory]).is_default


def test_a_directory_where_a_file_should_be_is_not_an_exception(tmp_path):
    (tmp_path / "etc" / CONFIG_NAME).mkdir(parents=True)
    assert load_settings(search=[tmp_path / "etc"]).is_default


# --- the mode ---------------------------------------------------------------


def test_the_default_is_year_one_because_starting_low_costs_nothing():
    assert ParentSettings().mode is Mode.Y1


def test_year_two_is_read_when_it_is_asked_for():
    assert settings_from_document({"clock": {"mode": "y2"}}).mode is Mode.Y2


def test_a_mode_nobody_recognises_falls_back_rather_than_refusing():
    assert settings_from_document({"clock": {"mode": "year 7"}}).mode is Mode.Y1


def test_no_clock_table_at_all_is_year_one():
    assert settings_from_document({}).mode is Mode.Y1
    assert settings_from_document({"clock": "not a table"}).mode is Mode.Y1


# --- the routine ------------------------------------------------------------


def test_a_configured_day_replaces_the_default_one():
    doc = {
        "routine": [
            {"id": "tea", "name": "Dinner", "time": "18:00"},
            {"id": "wake", "name": "Up", "time": "06:45"},
        ]
    }
    settings = settings_from_document(doc)
    assert [item.id for item in settings.routine] == ["wake", "tea"]
    assert settings.routine.by_id("tea").name == "Dinner"


def test_a_moment_may_name_a_picture_that_is_not_its_id():
    doc = {"routine": [{"id": "dinner", "name": "Dinner", "time": "18:00", "picture": "tea"}]}
    assert settings_from_document(doc).routine[0].picture == "tea"


def test_a_moment_with_no_name_is_named_after_its_id():
    doc = {"routine": [{"id": "quiet_time", "time": "13:00"}]}
    assert settings_from_document(doc).routine[0].name == "Quiet time"


def test_one_broken_entry_does_not_lose_the_others():
    """Partial credit: an all-or-nothing reader would throw away a grown-up's
    whole afternoon over a missing colon."""
    doc = {
        "routine": [
            {"id": "wake", "name": "Up", "time": "07:00"},
            {"id": "tea", "name": "Tea", "time": "half six"},
            {"id": "bed", "name": "Bed", "time": "19:00"},
        ]
    }
    assert [item.id for item in settings_from_document(doc).routine] == ["wake", "bed"]


def test_an_entry_with_no_id_is_dropped():
    doc = {"routine": [{"name": "Something", "time": "10:00"}]}
    assert settings_from_document(doc).routine.items == DEFAULT_ROUTINE


def test_an_entry_that_is_not_a_table_is_dropped():
    doc = {"routine": ["tea", 7, None]}
    assert settings_from_document(doc).routine.items == DEFAULT_ROUTINE


def test_a_routine_that_is_not_a_list_is_the_default_day():
    assert settings_from_document({"routine": {"id": "tea"}}).routine.items == DEFAULT_ROUTINE


def test_no_usable_entries_falls_back_to_the_default_day():
    doc = {"routine": [{"id": "tea", "time": "nonsense"}]}
    assert settings_from_document(doc).routine.items == DEFAULT_ROUTINE


def test_a_ninth_moment_is_dropped_rather_than_shrinking_the_other_eight():
    """A ninth tile takes the strip below ADR-0011's 20 mm floor, and a target
    under the floor is not a target."""
    doc = {
        "routine": [
            {"id": f"m{index}", "name": f"M{index}", "time": f"{index + 6:02d}:00"}
            for index in range(12)
        ]
    }
    settings = settings_from_document(doc)
    assert len(settings.routine) == MAX_ROUTINE_ITEMS == 8
    assert [item.id for item in settings.routine] == [f"m{index}" for index in range(8)]


def test_the_mode_survives_a_completely_broken_routine():
    doc = {"clock": {"mode": "y2"}, "routine": "nonsense"}
    assert settings_from_document(doc).mode is Mode.Y2


# --- the file the image ships -----------------------------------------------


def test_the_shipped_default_file_parses():
    with SHIPPED.open("rb") as handle:
        assert tomllib.load(handle)


def test_the_shipped_default_file_says_the_same_thing_the_code_does():
    """Two spellings of the default day would be one bug waiting to happen."""
    with SHIPPED.open("rb") as handle:
        settings = settings_from_document(tomllib.load(handle), source=SHIPPED)
    assert settings.mode is Mode.Y1
    assert [item.id for item in settings.routine] == [item.id for item in DEFAULT_ROUTINE]
    assert [item.at for item in settings.routine] == [item.at for item in DEFAULT_ROUTINE]
    assert [item.name for item in settings.routine] == [item.name for item in DEFAULT_ROUTINE]


def test_describe_names_the_file_that_decided_it(tmp_path):
    path = write(tmp_path / "etc", '[clock]\nmode = "y2"\n')
    assert str(path) in load_settings(search=[tmp_path / "etc"]).describe()
    assert "no config" in ParentSettings().describe()


@pytest.mark.parametrize("text", ["", "\n\n", "# only a comment\n"])
def test_an_empty_file_is_the_defaults_and_not_a_crash(tmp_path, text):
    write(tmp_path / "etc", text)
    settings = load_settings(search=[tmp_path / "etc"])
    assert settings.mode is Mode.Y1
    assert settings.routine.items == DEFAULT_ROUTINE
