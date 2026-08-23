"""Honesty, enforced by grep.

Research 10, section 4.4: *"To the child: nothing numeric, ever."* and *"Never:
percentiles, ages, comparison to other children, predicted screening-check
outcome, or a green/amber/red flag."*

These are product rules that are very easy to lose the moment somebody adds a
progress bar "just for the parent". So they are tests.
"""

from __future__ import annotations

import re

import pytest

# Words that must not appear anywhere in the parent- or child-facing copy.
# Each is here because research 10 section 4.4 or 4.6 names it.
#
# One section is exempt: `what_this_is_not`, whose entire job is to name these
# things and refuse them. "There are no stars, streaks, badges or coins" has to
# be sayable. Separate tests below check that section actually does say it.
EXEMPT_SECTIONS = {"what_this_is_not"}

BANNED = [
    "percentile", "reading age", "grade", "grading", "rank", "ranking",
    "average", "percentage", "%", "streak", "badge", "trophy", "coin",
    "leaderboard", "level up", "top of the class", "ahead of other",
    "behind other", "compared to other", "amber", "red flag",
    "screening check", "assessment of your child", "reading level",
    "teaches your child to read", "guaranteed", "well done", "clever",
]

BANNED_PATTERNS = [
    re.compile(r"\blevel\b", re.I),
    re.compile(r"\bstars?\b", re.I),
    re.compile(r"\bscored?\b", re.I),
    re.compile(r"\b\d+\s*%"),
    re.compile(r"\breading age\b", re.I),
    re.compile(r"\b\d+\s*(?:years?|yrs?)\s*old\b", re.I),
]


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


@pytest.fixture(scope="module")
def strings(corpus):
    return [
        (path, text)
        for path, text in walk(corpus.parent_text)
        if path.split(".")[0] not in EXEMPT_SECTIONS
    ]


def test_parent_text_loads(corpus):
    assert corpus.parent_text
    assert corpus.parent_text["version"] == 1


def test_there_is_something_to_show(strings):
    assert len(strings) > 30


@pytest.mark.parametrize("banned", BANNED)
def test_no_banned_word_anywhere(strings, banned):
    for path, text in strings:
        assert banned not in text.lower(), f"{banned!r} appears in {path}"


@pytest.mark.parametrize("pattern", BANNED_PATTERNS, ids=lambda p: p.pattern)
def test_no_banned_pattern_anywhere(strings, pattern):
    for path, text in strings:
        assert not pattern.search(text), f"{pattern.pattern} matches {path}: {text!r}"


def test_the_three_panes_exist(corpus):
    t = corpus.parent_text
    assert t["pane_school"]["title"] == "What the school has taught"
    assert t["pane_seen"]["title"] == "What we've seen him read here"
    assert t["pane_made"]["title"] == "What he made"


def test_the_three_grapheme_states_are_the_only_ones(corpus):
    seen = corpus.parent_text["pane_seen"]
    assert seen["state_not_tried"] == "not tried"
    assert seen["state_tried"] == "tried"
    assert seen["state_correct"] == "read correctly on 3 different days"


def test_the_grapheme_states_match_the_schedule_code(corpus):
    from sounds_and_words.schedule import History

    h = History()
    seen = corpus.parent_text["pane_seen"]
    assert h.state("s").parent_state() == seen["state_not_tried"]
    h.record("s", 0, correct=True)
    assert h.state("s").parent_state() == seen["state_tried"]
    h.record("s", 1, correct=True)
    h.record("s", 2, correct=True)
    assert h.state("s").parent_state() == seen["state_correct"]


def test_the_honesty_paragraph_is_present_and_verbatim(corpus):
    """Research 10, section 4.4 gives this wording verbatim. It stays verbatim."""
    expected = (
        "This is what happened on this computer. It is not an assessment, and it "
        "is not a substitute for what his teacher sees. Children read differently "
        "for a machine than for a person."
    )
    assert corpus.parent_text["pane_seen"]["honesty"] == expected


def test_the_school_pane_is_framed_as_the_parents_statement(corpus):
    body = corpus.parent_text["pane_school"]["body"].lower()
    assert "your statement, not ours" in body


# ----------------------------------------------------- "what this is not"
def test_what_this_is_not_covers_everything_it_must(corpus):
    section = corpus.parent_text["what_this_is_not"]
    for key in (
        "not_a_reading_programme",
        "not_handwriting",
        "not_the_school",
        "not_an_assessment",
        "not_graded_aloud",
        "no_rewards",
    ):
        assert key in section, key
        assert len(section[key]) > 100, f"{key} needs to actually say something"


def test_it_says_it_is_not_a_reading_programme(corpus):
    text = corpus.parent_text["what_this_is_not"]["not_a_reading_programme"].lower()
    assert "not a reading programme" in text
    assert "does not teach your child to read" in text


def test_it_says_handwriting_stays_on_paper(corpus):
    text = corpus.parent_text["what_this_is_not"]["not_handwriting"].lower()
    assert "does not teach handwriting" in text
    assert "pencil" in text and "paper" in text
    assert "letter formation" in text


def test_it_says_the_school_decides_the_next_sound(corpus):
    text = corpus.parent_text["what_this_is_not"]["not_the_school"].lower()
    assert "the school decides the next sound" in text


def test_it_points_a_worried_parent_at_the_teacher(corpus):
    text = corpus.parent_text["what_this_is_not"]["not_an_assessment"].lower()
    assert "his teacher" in text


def test_it_refuses_to_grade_reading_aloud(corpus):
    text = corpus.parent_text["what_this_is_not"]["not_graded_aloud"].lower()
    assert "never listens" in text or "never" in text
    assert "marks it" in text


# ---------------------------------------------------------- the grown-up turn
def test_the_grown_up_turn_exists_and_says_why(corpus):
    turn = corpus.parent_text["grown_up_turn"]
    assert len(turn["prompts"]) >= 3
    assert "adult" in turn["why"].lower()


def test_the_setup_asks_the_two_questions(corpus):
    setup = corpus.parent_text["setup"]
    assert "phonics programme" in setup["scheme_question"].lower()
    assert "most recent sound" in setup["grapheme_question"].lower()
    assert setup["scheme_unknown_label"] == "I don't know"


def test_i_dont_know_is_treated_as_a_good_answer(corpus):
    setup = corpus.parent_text["setup"]
    assert "perfectly good answer" in setup["scheme_help"]
    assert "very beginning" in setup["scheme_unknown_result"]


def test_there_is_no_silent_auto_advance(corpus):
    body = corpus.parent_text["setup"]["recheck_body"].lower()
    assert "never moves on by itself" in body


def test_the_conservative_notice_matches_what_the_code_says(corpus):
    from sounds_and_words.ceiling import ceiling_for_grapheme  # noqa: F401
    from sounds_and_words.schemes import load_schemes

    notice = corpus.parent_text["setup"]["conservative_notice"]
    assert "never go ahead of them" in notice
    for scheme in load_schemes().values():
        if scheme.status == "stub":
            assert "never go ahead of them" in scheme.note


def test_the_child_lines_never_correct_or_grade(corpus):
    child = corpus.parent_text["child"]
    assert child["no_correction"] == "Have another go."
    assert "push them together" in child["blend_it"]
    assert "book" in child["nothing_due"].lower()


# ----------------------------------------- the exempt section earns its exemption
def test_the_exempt_section_actually_names_what_it_refuses(corpus):
    """`what_this_is_not` is the only place these words may appear, and it must
    use them to refuse, not to offer."""
    rewards = corpus.parent_text["what_this_is_not"]["no_rewards"].lower()
    for word in ("stars", "streaks", "badges", "coins"):
        assert word in rewards, word
    assert rewards.startswith("there are no ")

    assessment = corpus.parent_text["what_this_is_not"]["not_an_assessment"].lower()
    assert "no scores" in assessment
    assert "no levels" in assessment
    assert "no comparisons" in assessment


def test_only_that_one_section_is_exempt(corpus):
    assert {"what_this_is_not"} == EXEMPT_SECTIONS
    assert "what_this_is_not" in corpus.parent_text
