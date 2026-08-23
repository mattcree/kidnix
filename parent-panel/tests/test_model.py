"""The pure model: children, ids, the allow-list union, the payload round trip."""

from __future__ import annotations

from dataclasses import replace

import pytest

from kidnix_parent_panel import model as M


def test_slugify_makes_a_directory_safe_id():
    assert M.slugify("Rosie") == "rosie"
    assert M.slugify("Sam & Jo!") == "sam-jo"
    assert M.slugify("  ") == "child"


def test_slugify_is_unique_against_what_is_taken():
    assert M.slugify("Rosie", ("rosie",)) == "rosie-2"
    assert M.slugify("Rosie", ("rosie", "rosie-2")) == "rosie-3"


def test_slugify_refuses_a_path_traversal():
    # The id becomes a directory name under the child's data home, so "../"
    # would aim a Journal somewhere else entirely.
    assert "/" not in M.slugify("../../etc")
    assert ".." not in M.slugify("../../etc")


def test_is_valid_id_rejects_the_dangerous_shapes():
    assert M.is_valid_id("rosie")
    assert M.is_valid_id("rosie-2")
    assert not M.is_valid_id("Rosie")
    assert not M.is_valid_id("../etc")
    assert not M.is_valid_id("")
    assert not M.is_valid_id("a" * 40)


def test_parse_clock():
    assert M.parse_clock("19:00") == (19, 0)
    assert M.parse_clock("7:05") == (7, 5)
    assert M.parse_clock("24:00") is None
    assert M.parse_clock("19:60") is None
    assert M.parse_clock("nineteen") is None


def test_clock_minutes():
    assert M.clock_minutes("00:00") == 0
    assert M.clock_minutes("19:30") == 19 * 60 + 30
    assert M.clock_minutes("nope") is None


def test_add_child_gives_distinct_colours_and_badges():
    panel = M.PanelModel()
    first = panel.add_child("Rosie")
    second = panel.add_child("Sam")
    assert first.colours != second.colours
    assert first.badge != second.badge


def test_retiring_a_child_keeps_them_in_the_model():
    panel = M.PanelModel()
    child = panel.add_child("Rosie")
    panel.retire_child(child.id)
    assert panel.active_children == []
    assert [c.id for c in panel.retired_children] == [child.id]
    # The id survives, which is what keeps ~/.local/share/kidnix/profiles/<id>
    # findable and restorable.
    panel.restore_child(child.id)
    assert [c.id for c in panel.active_children] == [child.id]


def test_renaming_does_not_change_the_id():
    panel = M.PanelModel()
    child = panel.add_child("Rosie")
    panel.update_child(child.id, name="Rosemary")
    assert panel.child(child.id).name == "Rosemary"
    assert panel.child(child.id).id == "rosie"


def test_move_child_reorders_and_refuses_off_the_ends():
    panel = M.PanelModel()
    a = panel.add_child("A")
    b = panel.add_child("B")
    assert panel.move_child(b.id, -1)
    assert [c.id for c in panel.children] == [b.id, a.id]
    assert not panel.move_child(b.id, -1)
    assert not panel.move_child("nobody", 1)


def test_machine_allow_list_is_empty_when_any_child_has_everything():
    panel = M.PanelModel()
    a = panel.add_child("A")
    b = panel.add_child("B")
    panel.set_allowed(a.id, ("tuxpaint",))
    panel.set_allowed(b.id, ())
    # Empty means "all", and a union with "all" is "all".
    assert panel.machine_allow_list == ()


def test_machine_allow_list_is_the_union_of_explicit_lists():
    panel = M.PanelModel()
    a = panel.add_child("A")
    b = panel.add_child("B")
    panel.set_allowed(a.id, ("tuxpaint", "blinken"))
    panel.set_allowed(b.id, ("kolf",))
    assert panel.machine_allow_list == ("blinken", "kolf", "tuxpaint")


def test_a_retired_child_does_not_widen_the_machine_list():
    panel = M.PanelModel()
    a = panel.add_child("A")
    b = panel.add_child("B")
    panel.set_allowed(a.id, ("tuxpaint",))
    panel.set_allowed(b.id, ("supertux",))
    panel.retire_child(b.id)
    assert panel.machine_allow_list == ("tuxpaint",)


def test_allow_list_is_shared_only_when_lists_actually_differ():
    panel = M.PanelModel()
    a = panel.add_child("A")
    b = panel.add_child("B")
    panel.set_allowed(a.id, ("tuxpaint",))
    panel.set_allowed(b.id, ("tuxpaint",))
    assert not panel.allow_list_is_shared
    panel.set_allowed(b.id, ("kolf",))
    assert panel.allow_list_is_shared


def test_one_child_never_reports_a_shared_list():
    panel = M.PanelModel()
    child = panel.add_child("Only")
    panel.set_allowed(child.id, ("tuxpaint",))
    assert not panel.allow_list_is_shared


def test_length_scale_matches_the_documented_mapping():
    # tts.env: length_scale = 1.0 - (rate / 200), quantised to 0.05.
    assert M.SoundSettings(speech_rate=0).length_scale == 1.0
    assert M.SoundSettings(speech_rate=-20).length_scale == 1.10
    assert M.SoundSettings(speech_rate=-60).length_scale == 1.30


def test_mute_beats_volume():
    assert M.SoundSettings(sound_volume=0.8, mute=True).effective_volume == 0.0
    assert M.SoundSettings(sound_volume=0.8).effective_volume == 0.8


def test_bedtime_off_when_the_two_times_are_equal():
    assert M.TimeSettings(bedtime_start="19:00", bedtime_end="19:00").bedtime_off
    assert not M.TimeSettings().bedtime_off


def test_sittings_in_budget_is_integer_division():
    assert M.TimeSettings(length_minutes=25, daily_budget_minutes=60).sittings_in_budget() == 2
    assert M.TimeSettings(length_minutes=25, daily_budget_minutes=20).sittings_in_budget() == 0


def test_schedule_window_covers_a_plain_afternoon():
    window = M.ScheduleWindow(days=M.WEEKDAYS, start="15:30", end="18:00")
    assert window.covers("mon", "16:00")
    assert not window.covers("sat", "16:00")
    assert not window.covers("mon", "19:00")
    assert not window.spans_midnight


def test_schedule_window_wrapping_midnight():
    window = M.ScheduleWindow(days=("fri",), start="20:00", end="01:00")
    assert window.spans_midnight
    assert window.covers("fri", "23:30")
    assert window.covers("fri", "00:30")
    assert not window.covers("fri", "12:00")


def test_keep_the_grid_the_same_is_show_everything():
    assert M.HomeSettings(keep_the_grid_the_same=True).show_everything is True
    assert M.HomeSettings(keep_the_grid_the_same=False).show_everything is False


def test_payload_round_trip_keeps_everything():
    panel = M.PanelModel()
    rosie = panel.add_child("Rosie")
    sam = panel.add_child("Sam", age_band="6-8")
    panel.set_allowed(sam.id, ("tuxpaint", "kolf"))
    panel.retire_child(rosie.id)
    panel.time = replace(
        panel.time,
        length_minutes=30,
        windows=(M.ScheduleWindow(days=M.WEEKEND, start="09:00", end="12:00", label="Weekends"),),
    )
    panel.sound = replace(panel.sound, calm=True, voice="cori-medium", speech_rate=-35)
    panel.add_recipient("Granny", relation="grandmother")
    panel.pin_salt, panel.pin_hash = "aa", "bb"

    again = M.PanelModel.from_payload(panel.to_payload())
    assert [c.id for c in again.active_children] == [sam.id]
    assert [c.id for c in again.retired_children] == [rosie.id]
    assert again.child(sam.id).allowed_activity_ids == ("kolf", "tuxpaint")
    assert again.time.length_minutes == 30
    assert again.time.windows[0].days == M.WEEKEND
    assert again.sound.calm and again.sound.voice == "cori-medium"
    assert again.sound.speech_rate == -35
    assert [r.name for r in again.family] == ["Granny"]
    assert (again.pin_salt, again.pin_hash) == ("aa", "bb")


def test_from_payload_survives_rubbish():
    panel = M.PanelModel.from_payload(
        {
            "parent": {"profiles": "not a list", "access": 7, "hover_dwell_ms": "soon"},
            "session": {"length_minutes": None, "windows": [{"days": "mon"}]},
            "tts": {"voice": "nonesuch"},
        }
    )
    assert panel.children == []
    assert panel.time.length_minutes == 25
    assert panel.hover_dwell_ms == 450
    assert panel.sound.voice == "cori-high"


def test_from_payload_accepts_a_voice_named_by_model_path():
    panel = M.PanelModel.from_payload(
        {"tts": {"voice": "", "model": M.VOICE_MODELS["cori-medium"]}}
    )
    assert panel.sound.voice == "cori-medium"


def test_from_payload_defaults_a_child_with_no_id():
    panel = M.PanelModel.from_payload({"parent": {"profiles": [{"name": "Bo"}]}})
    assert panel.children[0].id == "bo"


def test_a_boolean_is_not_an_integer():
    # TOML has no separate boolean-as-number, but JSON does, and True == 1.
    panel = M.PanelModel.from_payload({"session": {"length_minutes": True}})
    assert panel.time.length_minutes == 25


@pytest.mark.parametrize("index", range(4))
def test_every_shipped_colour_pair_has_a_badge(index):
    assert M.PROFILE_BADGES[index]
    assert M.is_colour(M.PROFILE_COLOURS[index][0])
    assert M.is_colour(M.PROFILE_COLOURS[index][1])


def test_remove_recipient():
    panel = M.PanelModel()
    granny = panel.add_recipient("Granny")
    assert panel.remove_recipient(granny.id)
    assert not panel.remove_recipient(granny.id)
