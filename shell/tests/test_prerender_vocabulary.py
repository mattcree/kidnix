"""The build-time enumeration of what the shell says.

``tools/prerender/vocabulary.py`` is a build tool, but the thing it is a tool
*about* is this package's own strings, so its test lives with them: the failure
this file exists to catch is "somebody added a spoken literal and the catalogue
did not notice", and that is a change to ``shell/``, not to ``tools/``.

No model, no onnxruntime, no audio -- this is all enumeration.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

prerender = pytest.importorskip("prerender.vocabulary", reason="tools/prerender is not present")

Vocabulary = prerender.Vocabulary
collect = prerender.collect
msgids_in_source = prerender.msgids_in_source

SHELL = REPO / "shell" / "kidnix_shell"
ACTIVITY_SDK = REPO / "shell" / "kidnix_activity"
POT = REPO / "shell" / "po" / "kidnix.pot"
MANIFESTS = REPO / "system_files" / "usr" / "share" / "kidnix" / "activities"
GCOMPRIS = REPO / "system_files" / "usr" / "share" / "kidnix" / "gcompris"

#: A floor, not a target. If the enumeration silently starts returning six
#: strings the image would still build and the shell would still talk -- in the
#: wrong voice, for everything. This is the tripwire for that.
MINIMUM_STRINGS = 200


# --- the AST walk ------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "want"),
    [
        ('_("Draw")', ["Draw"]),
        ('N_("Who\'s here?")', ["Who's here?"]),
        ('gettext("Back")', ["Back"]),
        ('NP_("{count} thing", "{count} things", n)', ["{count} thing", "{count} things"]),
        ('ngettext("one", "many", n)', ["one", "many"]),
        # A *use* of a msgid marked elsewhere. Skipped here, collected there.
        ("_(SOME_CONSTANT)", []),
        # Not a gettext call at all.
        ('print("Draw")', []),
        # Attribute calls are not the shell's keywords.
        ('self._("Draw")', []),
    ],
)
def test_the_walk_finds_literal_msgids(source: str, want: list[str]) -> None:
    assert msgids_in_source(source) == want


def test_a_file_that_does_not_parse_is_skipped_rather_than_fatal() -> None:
    assert msgids_in_source("def (:::") == []


# --- the placeholder rule -----------------------------------------------------


def test_a_placeholder_string_is_left_to_the_runtime_backend() -> None:
    vocabulary = Vocabulary()
    vocabulary.add("You {verb} {count} {noun}", "test")
    assert vocabulary.texts == []
    assert vocabulary.skipped["You {verb} {count} {noun}"] == "placeholder"


def test_a_plain_string_is_kept() -> None:
    vocabulary = Vocabulary()
    vocabulary.add("  Draw  ", "test")
    assert vocabulary.texts == ["Draw"]


def test_an_empty_msgid_is_not_a_clip() -> None:
    # The .pot header is `msgid ""`.
    vocabulary = Vocabulary()
    vocabulary.add("", "test")
    vocabulary.add("   ", "test")
    assert vocabulary.texts == []


def test_the_same_string_from_two_sources_is_one_clip() -> None:
    vocabulary = Vocabulary()
    vocabulary.add("Draw", "catalogue")
    vocabulary.add("Draw", "manifest:tuxpaint.toml")
    assert vocabulary.texts == ["Draw"]
    assert vocabulary.entries["Draw"] == {"catalogue", "manifest:tuxpaint.toml"}


def test_the_order_is_stable_so_a_rebuild_renders_the_same_list() -> None:
    vocabulary = Vocabulary()
    for text in ("zebra", "apple", "Draw"):
        vocabulary.add(text, "test")
    assert vocabulary.texts == sorted(vocabulary.texts)


# --- .pot parsing -------------------------------------------------------------


def test_pot_msgids_are_read_including_continuations(tmp_path: Path) -> None:
    pot = tmp_path / "x.pot"
    pot.write_text(
        'msgid ""\n"Project-Id-Version: x\\n"\n\n'
        'msgid "Draw"\nmsgstr ""\n\n'
        'msgid ""\n"a long "\n"one"\nmsgstr ""\n\n'
        'msgid "{count} thing"\nmsgid_plural "{count} things"\nmsgstr[0] ""\n'
    )
    vocabulary = Vocabulary()
    prerender.from_pot(pot, vocabulary)
    assert "Draw" in vocabulary.texts
    assert "a long one" in vocabulary.texts
    assert "{count} thing" not in vocabulary.texts


def test_a_missing_pot_is_not_an_error(tmp_path: Path) -> None:
    assert prerender.from_pot(tmp_path / "nope.pot", Vocabulary()) == 0


# --- the real thing -----------------------------------------------------------


@pytest.fixture(scope="module")
def real() -> Any:
    return collect(
        python_roots=[SHELL, ACTIVITY_SDK],
        pot=POT if POT.is_file() else None,
        manifest_dirs=[MANIFESTS, GCOMPRIS],
    )


def test_the_shell_yields_a_real_catalogue(real: Any) -> None:
    assert len(real.texts) >= MINIMUM_STRINGS


def test_the_lines_a_child_hears_most_are_all_in_it(real: Any) -> None:
    # Hand-picked because these are the ones a regression would be least
    # audible in: the greeting, the Ear, Back, and a tile label.
    for text in ("Who's here?", "Say it again", "Back", "Ready to go outside?"):
        assert text in real.entries, f"{text!r} is not in the pre-render catalogue"


def test_the_weekday_expansion_is_the_shells_own_tuple(real: Any) -> None:
    from kidnix_shell import resting

    for day in resting.WEEKDAY_WORDS:
        assert resting.RESTING_ON_DAY.format(day=day) in real.entries
        assert resting.OUT_OF_HOURS_ON_DAY.format(day=day) in real.entries


def test_the_next_after_expansion_skips_the_way_out_of_the_question(real: Any) -> None:
    # "Not sure" has no phrase, so its ready_line is the ungrammatical
    # "Ready to not sure?" -- a sentence Goodbye never asks.
    assert "Ready to not sure?" not in real.entries
    assert "Ready to have a bath?" in real.entries


def test_numbers_nought_to_twenty_are_rendered(real: Any) -> None:
    for value in range(21):
        assert str(value) in real.entries
    assert "21" not in real.entries


def test_number_words_come_free_with_the_catalogue(real: Any) -> None:
    from kidnix_shell import words

    spoken = {word for word in getattr(words, "NUMBER_WORDS", ()) if word}
    assert spoken, "kidnix_shell.words has no NUMBER_WORDS to check against"
    assert spoken <= set(real.entries)


def test_activity_labels_are_in_it(real: Any) -> None:
    manifest_sourced = {
        text
        for text, sources in real.entries.items()
        if any(s.startswith("manifest:") for s in sources)
    }
    assert len(manifest_sourced) >= 10


def test_no_rendered_string_carries_a_placeholder(real: Any) -> None:
    # The constraint, restated as an assertion: a clip for a template would be
    # a clip that says "You verb count noun".
    assert [text for text in real.texts if "{" in text or "}" in text] == []


def test_every_skipped_string_has_a_recorded_reason(real: Any) -> None:
    assert all(reason for reason in real.skipped.values())
