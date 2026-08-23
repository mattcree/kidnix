"""The manifest, checked by the same validator the image build runs.

There is deliberately no second parser here: ``kidnix_activity.manifest`` calls
the shell's own ``parse_manifest``, because two parsers is how a manifest comes
to validate in CI and be skipped on the machine
(``docs/design/activity-sdk.md`` section 9).

The honesty tests are the other half. A goal line is the one sentence a parent
reads about this activity, and *"teaches your child to read"* is a claim no
product in this space has the evidence for -- two of the best-funded attempts
produced -1 month and +0.08 (research 10 section 4.6 #8).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from conftest import HAVE_SDK

MANIFEST = Path(__file__).resolve().parent.parent / "manifest.toml"


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
    """An SDK activity writes its own Journal entries, so `journal_watch`
    would make the importer keep the same card twice -- which the validator
    warns about rather than refuses."""
    from kidnix_activity.manifest import validate_file

    assert validate_file(MANIFEST).warnings == []


# --- what it says -----------------------------------------------------------


def test_the_id_is_the_one_the_journal_files_entries_under(manifest):
    from sounds_and_words import ACTIVITY_ID

    assert manifest["id"] == ACTIVITY_ID


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


def test_the_age_band_is_reception_and_year_one(manifest):
    assert manifest["age_band"] == "4-6"


def test_the_exec_is_the_console_script(manifest):
    assert manifest["exec"] == ["/usr/bin/kidnix-sounds-and-words"]


def test_the_tile_is_heard_before_it_is_read(manifest):
    """Pre-reader first (SYNTHESIS B4): a name, then one short sentence."""
    assert manifest["audio_label"].lower().startswith("sounds and words")
    assert len(manifest["audio_label"]) < 140


def test_there_is_a_picture_as_well_as_a_word(manifest):
    assert manifest["icon"]
    assert manifest["icon_kind"] in {"icon-name", "path"}


# --- the goal line ----------------------------------------------------------


def test_the_goal_line_is_the_honest_one(manifest):
    assert manifest["goal"] == (
        "Practises the letter sounds the school has already taught. "
        "Not a reading programme."
    )


@pytest.mark.parametrize(
    "claim",
    [
        "teaches your child to read",
        "teach your child to read",
        "reading age",
        "screening check",
        "phonics programme",
        "level",
        "score",
        "star",
        "reward",
        "fun",
    ],
)
def test_the_goal_line_claims_none_of_these(manifest, claim):
    assert claim not in manifest["goal"].lower()


def test_the_goal_line_says_what_it_is_not(manifest):
    """The refusal is the load-bearing half of the sentence."""
    assert "not a reading programme" in manifest["goal"].lower()


def test_the_manifest_carries_the_licence_the_corpus_needs(manifest):
    assert "Letters and Sounds" in manifest["notes"]
    assert "OGL" in manifest["notes"]
