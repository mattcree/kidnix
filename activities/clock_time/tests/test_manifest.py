"""The manifest, checked by the same validator the image build runs.

There is deliberately no second parser here: ``kidnix_activity.manifest`` calls
the shell's own ``parse_manifest``, because two parsers is how a manifest comes
to validate in CI and be skipped on the machine
(``docs/design/activity-sdk.md`` section 9).

The honesty tests are the other half. The goal line is the one sentence a
parent reads about this activity, and *"teaches your child to tell the time"*
is a claim ten minutes of playing with a dial does not support.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from conftest import HAVE_SDK

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.toml"


@pytest.fixture(scope="module")
def manifest() -> dict:
    with MANIFEST.open("rb") as handle:
        return tomllib.load(handle)


# --- the validator ----------------------------------------------------------


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_manifest_validates_against_the_shells_own_parser():
    from kidnix_activity.manifest import validate_file

    report = validate_file(MANIFEST)
    assert report.ok, report.errors


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_manifest_has_no_warnings_either():
    from kidnix_activity.manifest import validate_file

    assert validate_file(MANIFEST).warnings == []


# --- what it says -----------------------------------------------------------


def test_the_id_is_the_one_the_journal_files_entries_under(manifest):
    from clock_time import ACTIVITY_ID

    assert manifest["id"] == ACTIVITY_ID


def test_the_name_is_the_window_title(manifest):
    from clock_time import TITLE

    assert manifest["name"] == TITLE


def test_it_is_an_activity_and_not_a_shelf(manifest):
    assert manifest.get("kind", "activity") == "activity"


def test_it_saves_on_sigterm_and_never_asks(manifest):
    assert manifest["quit"] == "signal"
    assert manifest["quit_grace"] == 5.0


def test_it_has_no_use_for_the_network(manifest):
    assert manifest["network_required"] is False


def test_it_writes_its_own_journal_entries(manifest):
    assert "journal_watch" not in manifest
    assert "journal_glob" not in manifest


def test_the_age_band_is_the_one_the_brief_asked_for(manifest):
    assert manifest["age_band"] == "4-8"


def test_the_category_is_learn(manifest):
    assert manifest["category"] == "learn"


def test_the_exec_is_the_console_script(manifest):
    assert manifest["exec"] == ["/usr/bin/kidnix-clock-time"]


def test_the_console_script_is_the_one_pyproject_declares():
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)
    assert "kidnix-clock-time" in project["project"]["scripts"]
    assert project["project"]["scripts"]["kidnix-clock-time"] == "clock_time.activity:main"


def test_the_tile_is_heard_before_it_is_read(manifest):
    """Pre-reader first (SYNTHESIS B4): what happens, in one short sentence."""
    assert manifest["audio_label"].lower().startswith("play with the clock")
    assert len(manifest["audio_label"]) < 140


def test_there_is_a_picture_as_well_as_a_word(manifest):
    """For a child with no English, low vision or CVD the icon is the only
    persistent channel there is (ADR-0011)."""
    assert manifest["icon"]
    assert manifest["icon_kind"] == "path"


def test_the_icon_the_manifest_points_at_is_the_one_in_the_package(manifest):
    """The manifest names where the package lands on the image; the file must
    exist here, under the same name, or the tile is a broken image."""
    shipped = ROOT / "clock_time" / Path(manifest["icon"]).name
    assert shipped.is_file()
    assert shipped.read_text(encoding="utf-8").lstrip().startswith("<svg")


# --- the goal line ----------------------------------------------------------


def test_the_goal_line_is_the_honest_one(manifest):
    assert manifest["goal"] == (
        "Playing with a clock: o'clock and half past, and what happens when. "
        "Not a test."
    )


@pytest.mark.parametrize(
    "claim",
    [
        "teaches",
        "teach your child",
        "score",
        "star",
        "reward",
        "level",
        "assessment",
        "progress report",
        "fun",
    ],
)
def test_the_goal_line_claims_none_of_these(manifest, claim):
    assert claim not in manifest["goal"].lower()


def test_the_goal_line_says_what_it_is_not(manifest):
    """The refusal is the load-bearing half of the sentence (SUITE section 5)."""
    assert "not a test" in manifest["goal"].lower()


def test_the_notes_tell_a_parent_where_their_day_is_configured(manifest):
    assert "/etc/kidnix/clock_time.toml" in manifest["notes"]
