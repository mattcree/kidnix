"""The manifest, checked with the validator the image build runs.

Two parsers is how a manifest comes to validate in CI and be skipped on the
machine (SDK section 9), so this test calls the same one
``kidnix-activity validate`` does rather than re-reading the TOML itself.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from conftest import HAVE_SDK

MANIFEST = Path(__file__).resolve().parents[1] / "manifest.toml"
ICON = Path(__file__).resolve().parents[1] / "numbers_activity" / "icon.svg"


def _document() -> dict:
    return tomllib.loads(MANIFEST.read_text())


def test_the_manifest_parses() -> None:
    assert _document()["id"] == "numbers"


def test_the_name_and_the_spoken_label_are_both_there() -> None:
    doc = _document()
    assert doc["name"] == "Numbers"
    assert doc["audio_label"] == "Numbers"


def test_the_goal_is_the_honest_line_the_activity_is_held_to() -> None:
    goal = _document()["goal"]
    assert "Practice, not a test." in goal
    assert "subitis" not in goal.lower(), "the goal line is for a parent, not a curriculum"


def test_it_quits_on_a_signal_and_never_asks() -> None:
    assert _document()["quit"] == "signal"


def test_it_needs_no_network() -> None:
    assert _document()["network_required"] is False


def test_it_does_not_ask_the_shell_to_import_its_files() -> None:
    # The activity writes its own Journal entry; an importer watching a scratch
    # directory would keep the same card twice (SDK section 8).
    doc = _document()
    assert "journal_watch" not in doc
    assert "journal_glob" not in doc


def test_the_age_band_covers_reception_to_year_two() -> None:
    assert _document()["age_band"] == "4-7"


def test_the_icon_is_a_drawing_that_exists() -> None:
    doc = _document()
    assert doc["icon_kind"] == "path"
    assert doc["icon"].endswith("numbers_activity/icon.svg")
    assert ICON.is_file()
    svg = ICON.read_text()
    assert "<circle" in svg, "the icon is a picture of five things, not a glyph"
    assert svg.count("<circle") == 5


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_sdk_validator_accepts_it() -> None:
    from kidnix_activity.manifest import validate_file

    report = validate_file(MANIFEST)
    assert report.errors == [], report.errors
