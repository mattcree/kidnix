"""The rules. Fatal problems block a save; notes do not."""

from __future__ import annotations

from dataclasses import replace

from kidnix_parent_panel import model as M
from kidnix_parent_panel import validate as V


def fields(problems, fatal_only=True):
    chosen = V.fatal(problems) if fatal_only else problems
    return {p.field for p in chosen}


def one_child(**changes) -> M.PanelModel:
    panel = M.PanelModel()
    panel.add_child("Rosie")
    for key, value in changes.items():
        panel.update_child("rosie", **{key: value})
    return panel


# --- children -------------------------------------------------------------


def test_a_machine_with_no_children_is_a_fatal_problem():
    assert "children" in fields(V.validate_children([]))


def test_a_valid_child_produces_nothing():
    assert V.validate_children(one_child().children) == []


def test_two_children_may_not_share_an_id():
    child = M.Child(id="rosie", name="Rosie")
    problems = V.validate_children([child, replace(child, name="Other")])
    assert any("both use the short name" in p.message for p in V.fatal(problems))


def test_a_child_with_no_name_is_fatal():
    problems = V.validate_children([M.Child(id="rosie", name="  ")])
    assert any("no name" in p.message for p in V.fatal(problems))


def test_an_unusable_id_is_fatal():
    problems = V.validate_children([M.Child(id="../etc", name="Rosie")])
    assert any("folder name" in p.message for p in V.fatal(problems))


def test_a_bad_colour_is_fatal():
    problems = V.validate_children([M.Child(id="a", name="A", colour_primary="teal")])
    assert any("colour like" in p.message for p in V.fatal(problems))


def test_an_unknown_badge_is_fatal():
    problems = V.validate_children([M.Child(id="a", name="A", badge="triangle")])
    assert any("shape as well as a colour" in p.message for p in V.fatal(problems))


def test_a_shared_colour_is_a_note_not_a_blocker():
    a = M.Child(id="a", name="A")
    b = M.Child(id="b", name="B", badge="leaf")
    problems = V.validate_children([a, b])
    assert V.ok(problems)
    assert any("same colour" in p.message for p in problems)


def test_a_shared_badge_is_a_note():
    a = M.Child(id="a", name="A")
    b = M.Child(id="b", name="B", colour_primary="#1a237e", colour_secondary="#ffd54f")
    problems = V.validate_children([a, b])
    assert V.ok(problems)
    assert any("same shape" in p.message for p in problems)


def test_a_retired_child_does_not_clash_with_an_active_one():
    a = M.Child(id="a", name="A")
    b = M.Child(id="b", name="B", retired=True)
    assert not [p for p in V.validate_children([a, b]) if "same colour" in p.message]


def test_an_empty_age_band_is_allowed():
    assert V.ok(V.validate_children([M.Child(id="a", name="A", age_band="")]))


def test_a_backwards_age_band_is_fatal():
    problems = V.validate_children([M.Child(id="a", name="A", age_band="8-4")])
    assert any("runs backwards" in p.message for p in V.fatal(problems))


def test_a_nonsense_age_band_is_fatal():
    problems = V.validate_children([M.Child(id="a", name="A", age_band="four")])
    assert any("age band like" in p.message for p in V.fatal(problems))


def test_a_single_year_age_band_is_fine():
    assert V.ok(V.validate_children([M.Child(id="a", name="A", age_band="5")]))


def test_a_very_long_name_is_only_a_note():
    problems = V.validate_children([M.Child(id="a", name="A" * 40)])
    assert V.ok(problems)
    assert any("too long" in p.message for p in problems)


# --- time -----------------------------------------------------------------


def test_default_time_settings_validate():
    assert V.validate_time(M.TimeSettings()) == []


def test_a_sitting_outside_the_supported_range_is_fatal():
    assert not V.ok(V.validate_time(M.TimeSettings(length_minutes=90)))
    assert not V.ok(V.validate_time(M.TimeSettings(length_minutes=2)))


def test_a_floor_below_three_minutes_is_fatal():
    # Below three the two-beat ending does not fit inside the session it ends.
    problems = V.validate_time(M.TimeSettings(min_session_minutes=2))
    assert not V.ok(problems)


def test_a_floor_longer_than_a_sitting_is_fatal():
    problems = V.validate_time(M.TimeSettings(length_minutes=10, min_session_minutes=20))
    assert any("open inside its own ending" in p.message for p in V.fatal(problems))


def test_a_budget_shorter_than_the_floor_is_fatal():
    problems = V.validate_time(
        M.TimeSettings(length_minutes=25, min_session_minutes=10, daily_budget_minutes=8)
    )
    assert any("no session could ever start" in p.message for p in V.fatal(problems))


def test_a_budget_shorter_than_a_sitting_is_only_a_note():
    problems = V.validate_time(
        M.TimeSettings(length_minutes=25, min_session_minutes=5, daily_budget_minutes=15)
    )
    assert V.ok(problems)
    assert any("cut short by the budget" in p.message for p in problems)


def test_put_away_must_come_after_the_offer():
    problems = V.validate_time(M.TimeSettings(ending_offer_minutes=2, put_away_minutes=2))
    assert any("two beats" in p.message for p in V.fatal(problems))


def test_a_bad_bedtime_is_fatal():
    assert not V.ok(V.validate_time(M.TimeSettings(bedtime_start="seven")))


def test_equal_bedtimes_are_allowed_and_mean_off():
    assert V.ok(V.validate_time(M.TimeSettings(bedtime_start="00:00", bedtime_end="00:00")))


# --- schedule windows -----------------------------------------------------


def test_a_window_with_no_days_is_fatal():
    problems = V.validate_windows((M.ScheduleWindow(days=()),))
    assert any("not set for any day" in p.message for p in V.fatal(problems))


def test_a_window_with_an_unknown_day_is_fatal():
    problems = V.validate_windows((M.ScheduleWindow(days=("funday",)),))
    assert any("Not a day of the week" in p.message for p in V.fatal(problems))


def test_a_zero_length_window_is_fatal():
    problems = V.validate_windows((M.ScheduleWindow(days=("sat",), start="10:00", end="10:00"),))
    assert any("never be usable" in p.message for p in V.fatal(problems))


def test_a_duplicated_day_is_only_a_note():
    problems = V.validate_windows((M.ScheduleWindow(days=("sat", "sat")),))
    assert V.ok(problems)


def test_a_window_wrapping_midnight_is_allowed():
    assert V.ok(V.validate_windows((M.ScheduleWindow(days=("fri",), start="20:00", end="01:00"),)))


def test_a_window_entirely_inside_bedtime_is_a_note():
    time = M.TimeSettings(
        bedtime_start="19:00",
        bedtime_end="07:00",
        windows=(M.ScheduleWindow(days=("sat",), start="20:00", end="21:00"),),
    )
    problems = V.validate_time(time)
    assert V.ok(problems)
    assert any("entirely inside bedtime" in p.message for p in problems)


def test_a_normal_window_is_not_flagged_against_bedtime():
    time = M.TimeSettings(windows=(M.ScheduleWindow(days=("sat",), start="09:00", end="12:00"),))
    assert not [p for p in V.validate_time(time) if "inside bedtime" in p.message]


# --- sound, home, family, allow-lists -------------------------------------


def test_default_sound_validates():
    assert V.validate_sound(M.SoundSettings()) == []


def test_mute_without_captions_is_fatal():
    problems = V.validate_sound(M.SoundSettings(mute=True, captions=False))
    assert any("told nothing at all" in p.message for p in V.fatal(problems))


def test_mute_with_captions_is_fine():
    assert V.ok(V.validate_sound(M.SoundSettings(mute=True, captions=True)))


def test_an_unknown_voice_is_fatal():
    assert not V.ok(V.validate_sound(M.SoundSettings(voice="brian")))


def test_a_volume_out_of_range_is_fatal():
    assert not V.ok(V.validate_sound(M.SoundSettings(sound_volume=1.5)))


def test_home_bounds():
    assert V.validate_home(M.HomeSettings()) == []
    assert not V.ok(V.validate_home(M.HomeSettings(initial_tiles=1)))
    assert not V.ok(V.validate_home(M.HomeSettings(reveal_every_sessions=0)))


def test_family_needs_names_and_unique_ids():
    problems = V.validate_family(
        [M.Recipient(id="granny", name="Granny"), M.Recipient(id="granny", name="Nan")]
    )
    assert any("listed twice" in p.message for p in V.fatal(problems))


def test_a_relative_photo_path_is_only_a_note():
    problems = V.validate_family([M.Recipient(id="granny", name="Granny", photo="granny.png")])
    assert V.ok(problems)
    assert any("full path" in p.message for p in problems)


def test_an_unknown_activity_id_is_only_a_note():
    child = M.Child(id="a", name="A", allowed_activity_ids=("tuxpaint", "nosuchthing"))
    problems = V.validate_allow_lists([child], frozenset({"tuxpaint"}))
    assert V.ok(problems)
    assert any("nosuchthing" in p.message for p in problems)


def test_no_known_ids_means_no_allow_list_complaints():
    child = M.Child(id="a", name="A", allowed_activity_ids=("whatever",))
    assert V.validate_allow_lists([child], frozenset()) == []


# --- the whole thing ------------------------------------------------------


def test_a_default_machine_with_one_child_validates():
    assert V.ok(V.validate(one_child()))


def test_hover_dwell_is_bounded():
    panel = one_child()
    panel.hover_dwell_ms = 10
    assert not V.ok(V.validate(panel))


def test_validate_payload_rejects_a_wrong_schema():
    assert not V.ok(V.validate_payload({"schema": 99}))


def test_validate_payload_rejects_a_non_dict():
    assert not V.ok(V.validate_payload("nope"))


def test_validate_payload_accepts_a_real_one():
    assert V.ok(V.validate_payload(one_child().to_payload()))


def test_problem_str_says_error_or_note():
    assert str(V.Problem("f", "m")).startswith("error:")
    assert str(V.Problem("f", "m", fatal=False)).startswith("note:")


def test_cross_check_against_the_shell_finds_no_drift():
    # Empty when kidnix_shell is not installed; empty when it agrees. A
    # non-empty list means the copied constants have rotted.
    assert V.cross_check_against_shell() == []
