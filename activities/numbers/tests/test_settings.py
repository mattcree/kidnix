"""The grown-up's file: what it can say, and what a mistake in it costs.

The rule the whole module is built around is that **nothing here ever raises**.
A missing file, a malformed one, a typo in a key: all of them come back as the
defaults with a line in the log, because a five-year-old told the computer is
broken because a grown-up mistyped a TOML key has been failed twice.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from numbers_activity.settings import (
    CONFIG_NAME,
    FIVE_FRAME,
    TEN_FRAME,
    FrameStyle,
    NumberRange,
    ParentSettings,
    config_candidates,
    load_settings,
    read_document,
    settings_from_document,
)

SHIPPED = Path(__file__).resolve().parents[1] / CONFIG_NAME


def _from(text: str) -> ParentSettings:
    return settings_from_document(tomllib.loads(text))


# -- the defaults ------------------------------------------------------------


def test_the_default_is_the_elgs_floor() -> None:
    settings = ParentSettings()
    assert settings.range is NumberRange.FIVE
    assert settings.numerals is True
    assert settings.frames is FrameStyle.AUTO
    assert settings.is_default


def test_the_default_choices_are_one_to_five() -> None:
    assert ParentSettings().choices == (1, 2, 3, 4, 5)


def test_the_ten_range_offers_one_to_ten() -> None:
    assert ParentSettings(range=NumberRange.TEN).choices == tuple(range(1, 11))


def test_settings_know_which_file_decided_them() -> None:
    settings = settings_from_document({}, source=Path("/etc/kidnix/numbers.toml"))
    assert not settings.is_default
    assert "numbers.toml" in settings.describe()


# -- reading the file --------------------------------------------------------


def test_a_full_file_is_read() -> None:
    settings = _from(
        """
        [numbers]
        range = "ten"
        numerals = false
        frames = "ten"
        """
    )
    assert settings.range is NumberRange.TEN
    assert settings.numerals is False
    assert settings.frames is FrameStyle.TEN


def test_a_grown_up_who_wrote_ten_as_a_number_still_means_ten() -> None:
    assert _from('[numbers]\nrange = 10\n').range is NumberRange.TEN


def test_an_unknown_range_falls_back_rather_than_failing() -> None:
    assert _from('[numbers]\nrange = "twenty"\n').range is NumberRange.FIVE


def test_an_unknown_frame_style_falls_back_to_auto() -> None:
    assert _from('[numbers]\nframes = "hexagon"\n').frames is FrameStyle.AUTO


def test_a_non_boolean_numerals_keeps_showing_them() -> None:
    assert _from('[numbers]\nnumerals = "yes"\n').numerals is True


def test_one_bad_key_does_not_lose_the_others() -> None:
    settings = _from(
        """
        [numbers]
        range = "ten"
        frames = "nonsense"
        """
    )
    assert settings.range is NumberRange.TEN
    assert settings.frames is FrameStyle.AUTO


def test_a_numbers_section_that_is_not_a_table_is_ignored() -> None:
    assert _from('numbers = "please"\n').range is NumberRange.FIVE


def test_an_empty_document_is_the_defaults() -> None:
    assert settings_from_document({}).range is NumberRange.FIVE


def test_a_missing_file_reads_as_nothing() -> None:
    assert read_document(Path("/nowhere/at/all/numbers.toml")) is None


def test_a_malformed_file_reads_as_nothing(tmp_path: Path) -> None:
    path = tmp_path / CONFIG_NAME
    path.write_text("[numbers\nrange =\n")
    assert read_document(path) is None


def test_load_falls_back_to_the_defaults_when_nobody_has_answered(tmp_path: Path) -> None:
    settings = load_settings(search=[tmp_path])
    assert settings.is_default
    assert settings.range is NumberRange.FIVE


def test_a_file_with_every_line_commented_out_is_not_an_answer(tmp_path: Path) -> None:
    """What the image actually ships as /etc/kidnix/numbers.toml.

    It parses -- it is valid TOML -- and it says nothing. A reader that took
    "this file exists" for "a grown-up decided" would hand kidnix's own default
    range back to a parent as their own statement, and the parent pane would
    have no way to say *nobody has told us yet*.
    """
    (tmp_path / CONFIG_NAME).write_text("# range = \"ten\"\n# nothing is set here\n")
    settings = load_settings(search=[tmp_path])
    assert settings.is_default
    assert settings.source is None
    assert settings.range is NumberRange.FIVE


def test_an_empty_first_file_falls_through_to_a_second_that_says_something(
    tmp_path: Path,
) -> None:
    """/etc is the parent's and /usr/share is ours. A parent who has not
    written anything must not shadow the image's own default file."""
    first, second = tmp_path / "etc", tmp_path / "usr"
    first.mkdir()
    second.mkdir()
    (first / CONFIG_NAME).write_text("# nothing\n")
    (second / CONFIG_NAME).write_text('[numbers]\nrange = "ten"\n')
    settings = load_settings(search=[first, second])
    assert settings.range is NumberRange.TEN
    assert settings.source == second / CONFIG_NAME


def test_load_reads_the_first_directory_that_has_one(tmp_path: Path) -> None:
    first, second = tmp_path / "etc", tmp_path / "usr"
    first.mkdir()
    second.mkdir()
    (first / CONFIG_NAME).write_text('[numbers]\nrange = "ten"\n')
    (second / CONFIG_NAME).write_text('[numbers]\nrange = "five"\n')
    settings = load_settings(search=[first, second])
    assert settings.range is NumberRange.TEN
    assert settings.source == first / CONFIG_NAME


def test_etc_is_read_before_usr_share() -> None:
    # bootc's three-way merge makes /etc the parent's and /usr/share ours.
    assert [str(path) for path in config_candidates()] == [
        "/etc/kidnix/numbers.toml",
        "/usr/share/kidnix/numbers.toml",
    ]


# -- which frame gets drawn --------------------------------------------------


def test_auto_gives_a_five_frame_for_five_and_a_ten_frame_for_ten() -> None:
    settings = ParentSettings()
    assert settings.frame_for(5) is FIVE_FRAME
    assert settings.frame_for(10) is TEN_FRAME


def test_asking_for_ten_frames_gets_ten_frames_throughout() -> None:
    settings = ParentSettings(frames=FrameStyle.TEN)
    assert settings.frame_for(5) is TEN_FRAME
    assert settings.frame_for(10) is TEN_FRAME


def test_ten_counters_never_go_in_five_boxes() -> None:
    # The one correction the settings make without being asked.
    settings = ParentSettings(frames=FrameStyle.FIVE)
    assert settings.frame_for(5) is FIVE_FRAME
    assert settings.frame_for(10) is TEN_FRAME


def test_a_frame_knows_how_much_it_holds() -> None:
    assert FIVE_FRAME.capacity == 5
    assert TEN_FRAME.capacity == 10


# -- the file we ship --------------------------------------------------------


def test_the_shipped_file_parses_and_is_the_documented_default() -> None:
    settings = settings_from_document(tomllib.loads(SHIPPED.read_text()), source=SHIPPED)
    assert settings.range is NumberRange.FIVE
    assert settings.numerals is True
    assert settings.frames is FrameStyle.AUTO


def test_the_shipped_file_explains_every_key_it_sets() -> None:
    text = SHIPPED.read_text()
    for key in ("range", "numerals", "frames"):
        assert f"{key} =" in text
    # A parent reading this file is the audience; a key with no comment above it
    # is a key nobody outside this repository can use.
    assert text.count("#") > 20


@pytest.mark.parametrize("value", ["five", "ten"])
def test_every_documented_range_is_a_real_one(value: str) -> None:
    assert NumberRange.parse(value).value == value


@pytest.mark.parametrize("value", ["auto", "five", "ten"])
def test_every_documented_frame_style_is_a_real_one(value: str) -> None:
    assert FrameStyle.parse(value).value == value
