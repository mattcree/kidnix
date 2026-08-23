"""Rendering and reading the three files, and what survives a round trip."""

from __future__ import annotations

import tomllib
from dataclasses import replace

from kidnix_parent_panel import config_io
from kidnix_parent_panel import model as M

TTS = """\
# a comment that must survive
KIDNIX_PIPER_MODEL=/usr/share/kidnix/voices/en_GB-cori-high.onnx
KIDNIX_PIPER_SENTENCE_SILENCE=0.25
# another comment
"""


def household() -> M.PanelModel:
    panel = M.PanelModel()
    panel.add_child("Rosie")
    sam = panel.add_child("Sam", age_band="6-8")
    panel.set_allowed(sam.id, ("tuxpaint", "kolf"))
    panel.time = replace(
        panel.time,
        windows=(M.ScheduleWindow(days=M.WEEKEND, start="09:30", end="12:00", label="Weekends"),),
    )
    panel.add_recipient("Granny", relation="grandmother")
    return panel


def test_toml_str_escapes():
    assert config_io.toml_str('a"b') == '"a\\"b"'
    assert config_io.toml_str("a\\b") == '"a\\\\b"'


def test_rendered_parent_toml_is_valid_toml():
    tomllib.loads(config_io.render_parent_toml(household()))


def test_rendered_session_toml_is_valid_toml():
    tomllib.loads(config_io.render_session_toml(household()))


def test_rendered_parent_toml_points_at_the_documented_copy():
    text = config_io.render_parent_toml(M.PanelModel())
    assert "/usr/share/kidnix/parent.toml" in text


def test_a_machine_with_no_pin_says_so_rather_than_writing_one():
    text = config_io.render_parent_toml(M.PanelModel())
    assert "pin_hash =" not in text
    assert "pin_salt =" not in text
    assert "choose a PIN" in text


def test_a_pin_is_carried_through_verbatim():
    panel = M.PanelModel()
    panel.pin_salt, panel.pin_hash = "abc", "def"
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert data["pin_salt"] == "abc"
    assert data["pin_hash"] == "def"


def test_active_and_retired_children_go_to_different_tables():
    panel = household()
    panel.retire_child("rosie")
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert [p["id"] for p in data["profiles"]] == ["sam"]
    assert [p["id"] for p in data["retired_profiles"]] == ["rosie"]


def test_the_shell_only_ever_sees_active_children():
    # The shell reads `profiles` and nothing else, which is exactly why a
    # removed child's face disappears without their drawings going anywhere.
    panel = household()
    panel.retire_child("sam")
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert "sam" not in [p["id"] for p in data["profiles"]]


def test_the_machine_allow_list_is_written_at_the_top():
    panel = household()
    panel.set_allowed("rosie", ("blinken",))
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert data["allowed_activity_ids"] == ["blinken", "kolf", "tuxpaint"]


def test_the_shared_list_note_appears_only_when_lists_differ():
    panel = household()
    panel.set_allowed("rosie", ("blinken",))
    assert "the union here is the machine-wide default" in config_io.render_parent_toml(panel)
    panel.set_allowed("rosie", ("tuxpaint", "kolf"))
    assert "the union here is the machine-wide default" not in config_io.render_parent_toml(panel)


def test_per_child_lists_are_written_inside_each_profile():
    data = tomllib.loads(config_io.render_parent_toml(household()))
    sam = next(p for p in data["profiles"] if p["id"] == "sam")
    assert sam["allowed_activity_ids"] == ["kolf", "tuxpaint"]


def test_access_keys_use_the_shell_spellings():
    data = tomllib.loads(config_io.render_parent_toml(household()))
    assert set(data["access"]) >= {"captions", "calm", "sound_volume", "mute"}


def test_home_show_everything_is_the_inverse_of_the_switch_label():
    panel = household()
    panel.home = replace(panel.home, keep_the_grid_the_same=False)
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert data["home"]["show_everything"] is False


def test_next_after_blocks_survive_a_round_trip():
    panel = household()
    panel.next_after = [
        {"id": "trampoline", "label": "Trampoline", "audio_label": "The trampoline", "icon": "x"}
    ]
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert data["next_after"][0]["id"] == "trampoline"


def test_session_toml_carries_the_windows_and_says_they_are_enforced():
    """The comment used to say the shell did not read `[[windows]]`. It does --
    `session.parse_windows` plus `StartRefusal.OUT_OF_HOURS` -- and a file that
    tells a parent their schedule is inert is how a child gets locked out by
    somebody who thought they were writing a note to the future."""
    text = config_io.render_session_toml(household())
    data = tomllib.loads(text)
    assert data["windows"][0]["days"] == list(M.WEEKEND)
    assert "THESE ARE ENFORCED" in text
    assert "NO windows at all means NO restriction" in text
    assert "DOES NOT READ THIS YET" not in text


def test_session_toml_omits_the_windows_section_when_there_are_none():
    text = config_io.render_session_toml(M.PanelModel())
    assert "[[windows]]" not in text


def test_session_toml_has_every_key_the_build_requires():
    # build_files/60-shell.sh fails the build without these six.
    data = tomllib.loads(config_io.render_session_toml(household()))
    assert {
        "length_minutes",
        "daily_budget_minutes",
        "ending_offer_minutes",
        "put_away_minutes",
        "bedtime_start",
        "bedtime_end",
    } <= set(data)


def test_render_tts_env_changes_one_line_and_keeps_the_rest():
    out = config_io.render_tts_env(TTS, "cori-medium")
    assert "en_GB-cori-medium.onnx" in out
    assert "# a comment that must survive" in out
    assert "KIDNIX_PIPER_SENTENCE_SILENCE=0.25" in out
    assert out.count("KIDNIX_PIPER_MODEL=") == 1


def test_render_tts_env_adds_the_key_when_it_is_missing():
    out = config_io.render_tts_env("# nothing here\n", "cori-high")
    assert "KIDNIX_PIPER_MODEL=/usr/share/kidnix/voices/en_GB-cori-high.onnx" in out


def test_render_tts_env_refuses_an_unknown_voice():
    try:
        config_io.render_tts_env(TTS, "brian")
    except ValueError as exc:
        assert "brian" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("an unknown voice should not render")


def test_voice_from_tts_env():
    assert config_io.voice_from_tts_env(TTS) == "cori-high"
    assert config_io.voice_from_tts_env("") == "cori-high"
    assert (
        config_io.voice_from_tts_env(
            "KIDNIX_PIPER_MODEL=/usr/share/kidnix/voices/en_GB-cori-medium.onnx"
        )
        == "cori-medium"
    )


def test_payload_from_broken_toml_is_the_defaults_not_a_crash():
    payload = config_io.payload_from_toml("this is not [ toml", "nor is this", "")
    panel = M.PanelModel.from_payload(payload)
    assert panel.time.length_minutes == 25


def test_read_files_prefers_etc_then_usr(tmp_path):
    etc, usr = tmp_path / "etc", tmp_path / "usr"
    etc.mkdir()
    usr.mkdir()
    (usr / "parent.toml").write_text("default_session_minutes = 11\n")
    (etc / "session.toml").write_text("length_minutes = 12\n")
    parent_text, session_text, _ = config_io.read_files(etc, usr)
    assert "11" in parent_text
    assert "12" in session_text


def test_load_model_from_a_directory(tmp_path):
    panel = household()
    (tmp_path / "parent.toml").write_text(config_io.render_parent_toml(panel))
    (tmp_path / "session.toml").write_text(config_io.render_session_toml(panel))
    again = config_io.load_model(tmp_path, tmp_path)
    assert [c.name for c in again.active_children] == ["Rosie", "Sam"]
    assert again.time.windows[0].label == "Weekends"


def test_a_full_file_round_trip_is_stable(tmp_path):
    """Render, read, render again: byte-identical. A renderer that was not a
    fixed point would slowly rewrite a parent's machine on every save."""
    panel = household()
    first_parent = config_io.render_parent_toml(panel)
    first_session = config_io.render_session_toml(panel)
    (tmp_path / "parent.toml").write_text(first_parent)
    (tmp_path / "session.toml").write_text(first_session)
    again = config_io.load_model(tmp_path, tmp_path)
    assert config_io.render_parent_toml(again) == first_parent
    assert config_io.render_session_toml(again) == first_session


# --- a per-child language, which only a hand-edit can set today -------------


def test_a_hand_set_language_survives_apply(tmp_path):
    """The panel offers no UI for ``[[profiles]] language`` and the shell reads
    it (ADR-0012). Until the audit, re-rendering ``parent.toml`` -- which is
    what pressing Apply does, over the whole file -- silently dropped the key,
    so a bilingual household's Welsh profile turned back into an English one
    the first time a parent changed the bedtime."""
    panel = household()
    (tmp_path / "parent.toml").write_text(
        config_io.render_parent_toml(panel).replace(
            'name = "Rosie"', 'name = "Rosie"\nlanguage = "cy_GB"', 1
        )
    )
    (tmp_path / "session.toml").write_text(config_io.render_session_toml(panel))

    again = config_io.load_model(tmp_path, tmp_path)
    assert again.child("rosie").language == "cy_GB"
    assert again.child("sam").language == ""

    # ... and it is still there after the panel has written the file back.
    data = tomllib.loads(config_io.render_parent_toml(again))
    by_id = {p["id"]: p for p in data["profiles"]}
    assert by_id["rosie"]["language"] == "cy_GB"
    assert "language" not in by_id["sam"], 'an empty language is left out, not written as ""'


def test_a_language_survives_the_payload_as_well(tmp_path):
    """Apply does not hand the model to the renderer: it goes model -> payload
    -> pkexec -> model -> TOML, and a field missing from either half of the
    payload is a field that dies crossing the boundary."""
    panel = household()
    panel.update_child("rosie", language="pl_PL")
    again = M.PanelModel.from_payload(panel.to_payload())
    assert again.child("rosie").language == "pl_PL"
    assert 'language = "pl_PL"' in config_io.render_parent_toml(again)


def test_a_retired_child_keeps_their_language_too(tmp_path):
    """Retiring is a move between two tables, not a deletion, and the whole
    point is that putting the face back puts everything back."""
    panel = household()
    panel.update_child("sam", language="cy_GB")
    panel.retire_child("sam")
    data = tomllib.loads(config_io.render_parent_toml(panel))
    assert data["retired_profiles"][0]["language"] == "cy_GB"
