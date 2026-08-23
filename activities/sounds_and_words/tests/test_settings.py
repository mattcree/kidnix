"""The parent's ceiling, and this child's history file.

The two things a session is built from, and the two things that must not be
guessed. Everything here is headless.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from sounds_and_words.schedule import History
from sounds_and_words.settings import (
    DEFAULT_NARRATION,
    DEV_DEFAULT_LAST_GRAPHEME,
    DEV_DEFAULT_SCHEME,
    Narration,
    ParentCeiling,
    Progress,
    config_candidates,
    load_narration,
    load_parent_ceiling,
    load_progress,
    progress_dir,
    resolve,
    save_progress,
)


def write_config(tmp_path, body: str):
    (tmp_path / "sounds_and_words.toml").write_text(body, encoding="utf-8")
    return [tmp_path]


# --- where the ceiling is read from ---------------------------------------


def test_the_ceiling_is_looked_for_in_etc_first():
    """/etc is the parent's copy; /usr/share is the image's default (bootc)."""
    paths = config_candidates()
    assert [str(p) for p in paths] == [
        "/etc/kidnix/sounds_and_words.toml",
        "/usr/share/kidnix/sounds_and_words.toml",
    ]


def test_no_config_anywhere_is_phase_two_set_three(tmp_path):
    parent = load_parent_ceiling(search=[tmp_path])
    assert parent.is_default
    assert parent.source is None
    assert parent.scheme == DEV_DEFAULT_SCHEME
    assert parent.last_grapheme == DEV_DEFAULT_LAST_GRAPHEME


def test_the_dev_default_is_twelve_taught_gpcs(corpus):
    """s a t p i n m d g o c k -- and the two variants that share a spelling."""
    ceiling = resolve(corpus, ParentCeiling())
    assert sorted(ceiling.graphemes) == list("acdgikmnopst")


def test_the_dev_default_can_never_reach_phase_three(corpus):
    ceiling = resolve(corpus, ParentCeiling())
    assert ceiling.phase == 2
    assert "sh" not in ceiling.graphemes
    assert "ck" not in ceiling.graphemes


def test_a_config_file_wins(tmp_path, corpus):
    search = write_config(tmp_path, '[ceiling]\nscheme = "letters_and_sounds"\nlast_grapheme = "ck"\n')
    parent = load_parent_ceiling(search=search)
    assert not parent.is_default
    assert parent.last_grapheme == "ck"
    assert "ck" in resolve(corpus, parent).graphemes


def test_the_first_readable_file_wins(tmp_path, corpus):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    (first / "sounds_and_words.toml").write_text('[ceiling]\nlast_grapheme = "ck"\n')
    (second / "sounds_and_words.toml").write_text('[ceiling]\nlast_grapheme = "ear"\n')
    assert load_parent_ceiling(search=[first, second]).last_grapheme == "ck"


def test_a_missing_directory_is_not_an_error(tmp_path, corpus):
    parent = load_parent_ceiling(search=[tmp_path / "nope"])
    assert parent.is_default


def test_broken_toml_falls_back_rather_than_refusing_to_start(tmp_path):
    """A grown-up's typo must not become "the computer is broken" to a child."""
    search = write_config(tmp_path, "[ceiling\nlast_grapheme =\n")
    assert load_parent_ceiling(search=search).is_default


def test_a_file_with_no_ceiling_table_falls_back(tmp_path):
    search = write_config(tmp_path, "[something_else]\nkey = 1\n")
    assert load_parent_ceiling(search=search).is_default


def test_an_empty_last_grapheme_falls_back(tmp_path):
    search = write_config(tmp_path, '[ceiling]\nlast_grapheme = ""\n')
    assert load_parent_ceiling(search=search).is_default


def test_an_unknown_grapheme_falls_back_to_the_default_ceiling(corpus):
    """Never up. A grapheme we cannot resolve resolves *lower*, not higher."""
    ceiling = resolve(corpus, ParentCeiling(last_grapheme="zzzz"))
    assert sorted(ceiling.graphemes) == list("acdgikmnopst")


def test_an_unknown_scheme_falls_back_too(corpus):
    ceiling = resolve(corpus, ParentCeiling(scheme="not_a_scheme", last_grapheme="k"))
    assert sorted(ceiling.graphemes) == list("acdgikmnopst")


def test_i_dont_know_is_conservative_and_says_so(corpus):
    ceiling = resolve(corpus, ParentCeiling(scheme="unknown", last_grapheme="k"))
    assert ceiling.conservative
    assert ceiling.notes


def test_describe_names_the_file_that_decided(tmp_path):
    search = write_config(tmp_path, '[ceiling]\nlast_grapheme = "ck"\n')
    assert "sounds_and_words.toml" in load_parent_ceiling(search=search).describe()
    assert "dev default" in ParentCeiling().describe()


# --- where the history is kept ---------------------------------------------


def test_history_is_per_profile(tmp_path):
    env = {"HOME": str(tmp_path), "KIDNIX_PROFILE_ID": "sam"}
    assert progress_dir(env).parts[-3:] == ("profiles", "sam", "sounds-and-words")


def test_two_children_do_not_share_a_leitner_box(tmp_path):
    base = {"HOME": str(tmp_path)}
    sam = progress_dir({**base, "KIDNIX_PROFILE_ID": "sam"})
    alex = progress_dir({**base, "KIDNIX_PROFILE_ID": "alex"})
    assert sam != alex


def test_no_profile_id_is_the_pre_profiles_layout(tmp_path):
    """Exactly what the SDK does: never invent a profile called ""."""
    directory = progress_dir({"HOME": str(tmp_path), "KIDNIX_PROFILE_ID": ""})
    assert "profiles" not in directory.parts
    assert directory.parts[-1] == "sounds-and-words"


def test_xdg_state_home_is_honoured(tmp_path):
    env = {"HOME": str(tmp_path), "XDG_STATE_HOME": str(tmp_path / "state")}
    assert str(progress_dir(env)).startswith(str(tmp_path / "state"))


# --- the history file itself ------------------------------------------------


def test_a_missing_history_file_is_an_empty_schedule(tmp_path):
    progress = load_progress(tmp_path / "history.json")
    assert progress.history.states == {}
    assert progress.first_day is None


def test_history_round_trips(tmp_path):
    progress = Progress(History())
    progress.touch(date(2026, 8, 23))
    progress.history.record("s", 0, correct=True)
    progress.history.record("a", 0, correct=False)
    path = save_progress(tmp_path / "history.json", progress)

    back = load_progress(path)
    assert back.first_day == date(2026, 8, 23)
    assert back.history.state("s").box == 1
    assert back.history.state("a").box == 1
    assert back.history.state("a").streak == 0


def test_the_history_file_is_readable_by_a_parent(tmp_path):
    """Research 10 4.3: a parent can read the model in a text editor."""
    progress = Progress(History())
    progress.touch(date(2026, 8, 23))
    progress.history.record("s", 0, correct=True)
    path = save_progress(tmp_path / "history.json", progress)
    text = path.read_text(encoding="utf-8")
    assert "\n" in text
    assert "2026-08-23" in text
    assert json.loads(text)["gpcs"]["s"]["box"] == 1


def test_a_corrupt_history_file_is_left_alone_and_the_session_still_opens(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not json", encoding="utf-8")
    progress = load_progress(path)
    assert progress.history.states == {}
    assert path.read_text(encoding="utf-8") == "{not json"


def test_a_history_file_that_is_a_list_is_ignored(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_progress(path).history.states == {}


def test_a_nonsense_date_is_dropped_not_fatal(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps({"first_day": "yesterday", "gpcs": {}}), encoding="utf-8")
    assert load_progress(path).first_day is None


def test_saving_creates_the_directory(tmp_path):
    path = save_progress(tmp_path / "deep" / "down" / "history.json", Progress(History()))
    assert path.is_file()


def test_saving_leaves_no_temporary_file_behind(tmp_path):
    save_progress(tmp_path / "history.json", Progress(History()))
    assert [p.name for p in tmp_path.iterdir()] == ["history.json"]


# --- the day counter --------------------------------------------------------


def test_the_first_ever_session_is_day_zero():
    progress = Progress(History())
    assert progress.touch(date(2026, 8, 23)) == 0


def test_days_are_counted_from_the_first_session():
    progress = Progress(History())
    progress.touch(date(2026, 8, 23))
    assert progress.touch(date(2026, 8, 30)) == 7


def test_a_fortnight_away_costs_nothing_but_a_bigger_day_number():
    """No streaks, no gating on time (research 10 4.6 #12)."""
    progress = Progress(History())
    progress.touch(date(2026, 8, 1))
    assert progress.touch(date(2026, 8, 15)) == 14


def test_a_clock_that_went_backwards_rebases_rather_than_going_negative():
    progress = Progress(History())
    progress.touch(date(2026, 8, 23))
    assert progress.touch(date(2026, 1, 1)) == 0
    assert progress.first_day == date(2026, 1, 1)


@pytest.mark.parametrize("day", [date(2026, 8, 23), date(2027, 1, 1)])
def test_day_index_is_never_negative(day):
    progress = Progress(History(), first_day=date(2026, 8, 23))
    assert progress.day_index(day) >= 0


# --- narration: the parent's answer, in the same file as the ceiling --------
#
# Read it can read a page out loud. Takacs, Swart & Bus (2015) is why it can at
# all -- narrated text with congruent illustration beats a plain adult reading
# -- and it is also why the default is not `always`: the point of the module is
# a child reading it themselves, and a voice that starts on its own every page
# is a voice that reads the book for them.


def test_no_config_anywhere_means_narration_is_optional(tmp_path):
    assert load_narration(search=[tmp_path]) is Narration.OPTIONAL
    assert DEFAULT_NARRATION is Narration.OPTIONAL


def test_a_parent_can_ask_for_it_always(tmp_path):
    search = write_config(tmp_path, '[read]\nnarration = "always"\n')
    assert load_narration(search=search) is Narration.ALWAYS


def test_a_parent_can_turn_it_off(tmp_path):
    search = write_config(tmp_path, '[read]\nnarration = "never"\n')
    assert load_narration(search=search) is Narration.NEVER


def test_the_value_is_folded_and_trimmed(tmp_path):
    search = write_config(tmp_path, '[read]\nnarration = "  ALWAYS  "\n')
    assert load_narration(search=search) is Narration.ALWAYS


def test_an_unknown_value_falls_back_rather_than_refusing_to_start(tmp_path):
    """A grown-up's typo must not become "the computer is broken" to a child."""
    search = write_config(tmp_path, '[read]\nnarration = "sometimes"\n')
    assert load_narration(search=search) is DEFAULT_NARRATION


def test_a_broken_file_falls_back_too(tmp_path):
    search = write_config(tmp_path, "this is not toml [[[")
    assert load_narration(search=search) is DEFAULT_NARRATION


def test_a_file_with_no_read_table_falls_back(tmp_path):
    search = write_config(tmp_path, '[ceiling]\nlast_grapheme = "ck"\n')
    assert load_narration(search=search) is DEFAULT_NARRATION


def test_the_ceiling_and_the_narration_come_out_of_one_file(tmp_path):
    """One root-owned file, one set of answers. A parent who edits the ceiling
    should not have to find a second place for the voice."""
    search = write_config(
        tmp_path, '[ceiling]\nlast_grapheme = "ck"\n\n[read]\nnarration = "never"\n'
    )
    assert load_parent_ceiling(search=search).last_grapheme == "ck"
    assert load_narration(search=search) is Narration.NEVER


def test_optional_offers_the_button_and_says_nothing_by_itself():
    assert Narration.OPTIONAL.offers_button
    assert not Narration.OPTIONAL.speaks_on_arrival


def test_always_offers_the_button_as_well_because_it_is_not_a_gate():
    """A child who wants to hear the page again presses it again."""
    assert Narration.ALWAYS.offers_button
    assert Narration.ALWAYS.speaks_on_arrival


def test_never_offers_nothing_at_all():
    assert not Narration.NEVER.offers_button
    assert not Narration.NEVER.speaks_on_arrival


def test_there_are_exactly_three_answers():
    """A fourth would be a per-book override, and there is no evidence that a
    five-year-old should be answering this question at all."""
    assert [option.value for option in Narration] == ["optional", "always", "never"]
