"""The manifest, checked with the validator the image build runs.

Two parsers is how a manifest comes to validate in CI and be skipped on the
machine (SDK section 9), so this calls the same one ``kidnix-activity validate``
does rather than re-reading the TOML itself.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from conftest import HAVE_SDK

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.toml"
ICON = ROOT / "letters_to_family" / "icon.svg"


def _document() -> dict:
    return tomllib.loads(MANIFEST.read_text())


def test_the_manifest_parses() -> None:
    assert _document()["id"] == "letters"


def test_the_name_and_the_spoken_label_are_both_there() -> None:
    doc = _document()
    assert doc["name"] == "Letters"
    # Written for the ear: it says what *happens*, not what it is.
    assert doc["audio_label"] == "Send a letter"


def test_the_goal_names_all_three_parts_and_who_does_the_sending() -> None:
    goal = _document()["goal"]
    assert goal == (
        "Make a letter for someone in your family: a picture, a few words, "
        "your voice. A grown-up sends it."
    )
    assert "grown-up sends it" in goal


def test_it_quits_on_a_signal_and_never_asks() -> None:
    assert _document()["quit"] == "signal"


def test_it_needs_no_network() -> None:
    """The load-bearing line: the activity whose name most sounds like it needs
    egress is the one that must most visibly not have any (SYNTHESIS H1)."""
    assert _document()["network_required"] is False


def test_it_does_not_ask_the_shell_to_import_its_files() -> None:
    doc = _document()
    assert "journal_watch" not in doc
    assert "journal_glob" not in doc


def test_the_age_band_is_four_to_eight() -> None:
    assert _document()["age_band"] == "4-8"


def test_it_is_a_making_activity() -> None:
    assert _document()["category"] == "make"


def test_the_icon_is_a_depictive_drawing_that_exists() -> None:
    doc = _document()
    assert doc["icon_kind"] == "path"
    assert doc["icon"].endswith("letters_to_family/icon.svg")
    assert ICON.is_file()
    svg = ICON.read_text()
    # An envelope with a drawing peeking out: two rectangles, a sun and a line
    # of hills. A picture of the thing, not a glyph (ADR-0011).
    assert svg.count("<rect") == 2
    assert "<circle" in svg
    assert "<text" not in svg, "an icon a pre-reader cannot read is not an icon"


def test_the_notes_tell_a_grown_up_where_the_letters_go() -> None:
    notes = _document()["notes"]
    assert "/var/lib/kidnix/outbox" in notes
    assert "/var/lib/kidnix/inbox" in notes
    assert "[[family]]" in notes


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_sdk_validator_accepts_it() -> None:
    from kidnix_activity.manifest import validate_file

    report = validate_file(MANIFEST)
    assert report.errors == [], report.errors


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_validator_has_nothing_to_warn_about_either() -> None:
    from kidnix_activity.manifest import validate_file

    assert validate_file(MANIFEST).warnings == []


def test_the_console_script_is_the_one_the_manifest_execs() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "kidnix-letters" in pyproject["project"]["scripts"]
    assert _document()["exec"] == ["/usr/bin/kidnix-letters"]
