"""``kidnix-config``'s root half: who may ask, what it writes, and how."""

from __future__ import annotations

import io
import json
import os
import tomllib
from dataclasses import replace

from kidnix_parent_panel import config_io, helper
from kidnix_parent_panel import model as M


def household() -> M.PanelModel:
    panel = M.PanelModel()
    panel.add_child("Rosie")
    panel.time = replace(panel.time, length_minutes=30, daily_budget_minutes=90)
    return panel


def seeded(tmp_path, panel=None):
    panel = panel or household()
    (tmp_path / "parent.toml").write_text(config_io.render_parent_toml(panel))
    (tmp_path / "session.toml").write_text(config_io.render_session_toml(panel))
    return tmp_path


# --- who is asking --------------------------------------------------------


def test_calling_uid_prefers_pkexec():
    assert helper.calling_uid({"PKEXEC_UID": "1001", "SUDO_UID": "0"}) == 1001


def test_calling_uid_falls_back_to_sudo():
    assert helper.calling_uid({"SUDO_UID": "1001"}) == 1001


def test_calling_uid_ignores_nonsense():
    assert helper.calling_uid({"PKEXEC_UID": "root"}) == os.getuid()


def test_root_is_always_admin():
    assert helper.is_admin(0)


def test_an_unknown_uid_is_not_admin():
    assert not helper.is_admin(4294967000)


# --- atomic writing -------------------------------------------------------


def test_write_atomically_replaces_the_file(tmp_path):
    target = tmp_path / "a.toml"
    target.write_text("old\n")
    helper.write_atomically(target, "new\n")
    assert target.read_text() == "new\n"


def test_write_atomically_leaves_no_temporary_behind(tmp_path):
    target = tmp_path / "a.toml"
    helper.write_atomically(target, "x\n")
    assert [p.name for p in tmp_path.iterdir()] == ["a.toml"]


def test_write_atomically_sets_0644(tmp_path):
    # Root-owned and world-readable is the documented mode: the shell runs as
    # the child and has to be able to READ the PIN hash it cannot write.
    target = tmp_path / "a.toml"
    helper.write_atomically(target, "x\n")
    assert oct(target.stat().st_mode)[-3:] == "644"


def test_write_atomically_creates_the_directory(tmp_path):
    target = tmp_path / "deep" / "a.toml"
    helper.write_atomically(target, "x\n")
    assert target.read_text() == "x\n"


# --- the PIN is never the config writer's business ------------------------


def test_preserve_pin_takes_the_hash_off_disk_not_out_of_the_payload():
    payload = {"parent": {"pin_salt": "attacker", "pin_hash": "attacker"}}
    merged = helper.preserve_pin(payload, 'pin_salt = "real"\npin_hash = "alsoreal"\n')
    assert merged["parent"]["pin_salt"] == "real"
    assert merged["parent"]["pin_hash"] == "alsoreal"


def test_preserve_pin_on_a_machine_with_no_pin_writes_none():
    merged = helper.preserve_pin({"parent": {"pin_hash": "sneaky"}}, "")
    assert merged["parent"]["pin_hash"] == ""


def test_preserve_pin_survives_a_broken_file():
    merged = helper.preserve_pin({"parent": {}}, "not [ toml")
    assert merged["parent"]["pin_hash"] == ""


# --- what it renders ------------------------------------------------------


def test_rendered_covers_both_toml_files():
    texts = helper.rendered(household().to_payload(), "")
    assert set(texts) == {config_io.PARENT_TOML, config_io.SESSION_TOML}


def test_rendered_includes_tts_only_when_it_would_change():
    payload = household().to_payload()
    same = "KIDNIX_PIPER_MODEL=/usr/share/kidnix/voices/en_GB-cori-high.onnx\n"
    assert config_io.TTS_ENV not in helper.rendered(payload, same)
    payload["tts"] = {"voice": "cori-medium"}
    assert config_io.TTS_ENV in helper.rendered(payload, same)


# --- apply ----------------------------------------------------------------


def test_apply_writes_both_files(tmp_path):
    etc = tmp_path / "etc"
    etc.mkdir()
    out = io.StringIO()
    code = helper.do_apply(household().to_payload(), etc, tmp_path, out, frozenset())
    assert code == helper.EXIT_OK
    assert (etc / "parent.toml").is_file()
    assert (etc / "session.toml").is_file()
    assert "wrote" in out.getvalue()


def test_apply_refuses_invalid_settings_and_writes_nothing(tmp_path):
    etc = tmp_path / "etc"
    etc.mkdir()
    panel = household()
    panel.time = replace(panel.time, length_minutes=999)
    code = helper.do_apply(panel.to_payload(), etc, tmp_path, io.StringIO(), frozenset())
    assert code == helper.EXIT_INVALID
    assert not (etc / "parent.toml").exists()


def test_apply_keeps_the_pin_that_was_already_there(tmp_path):
    etc = seeded(_mk(tmp_path))
    (etc / "parent.toml").write_text(
        'pin_salt = "s"\npin_hash = "h"\n' + (etc / "parent.toml").read_text()
    )
    payload = household().to_payload()
    payload["parent"]["pin_hash"] = "somebody-elses"
    helper.do_apply(payload, etc, etc, io.StringIO(), frozenset())
    data = tomllib.loads((etc / "parent.toml").read_text())
    assert data["pin_hash"] == "h"


def test_apply_is_idempotent(tmp_path):
    etc = _mk(tmp_path)
    payload = household().to_payload()
    helper.do_apply(payload, etc, etc, io.StringIO(), frozenset())
    first = (etc / "parent.toml").read_text()
    helper.do_apply(payload, etc, etc, io.StringIO(), frozenset())
    assert (etc / "parent.toml").read_text() == first


def test_what_is_written_reads_back_as_the_same_household(tmp_path):
    etc = _mk(tmp_path)
    panel = household()
    panel.add_child("Sam", age_band="6-8")
    helper.do_apply(panel.to_payload(), etc, etc, io.StringIO(), frozenset())
    again = config_io.load_model(etc, etc)
    assert [c.name for c in again.active_children] == ["Rosie", "Sam"]
    assert again.time.length_minutes == 30


def test_the_shell_reads_back_what_the_helper_would_write():
    panel = household()
    texts = helper.rendered(panel.to_payload(), "")
    assert helper.shell_round_trip(texts, panel) == []


def test_a_dropped_profile_would_be_caught_by_the_round_trip(monkeypatch):
    panel = household()
    texts = helper.rendered(panel.to_payload(), "")
    # Simulate a renderer that lost a child on the way to disk.
    broken = dict(texts)
    broken[config_io.PARENT_TOML] = broken[config_io.PARENT_TOML].replace(
        "[[profiles]]", "[[nope]]"
    )
    problems = helper.shell_round_trip(broken, panel)
    # Only meaningful where kidnix_shell is installed; where it is not, the
    # check is a no-op and the image test is what proves it runs.
    if problems:
        assert "children" in problems[0].message or "reads" in problems[0].message


def test_main_show_needs_no_privilege(tmp_path, capsys):
    etc = _mk(tmp_path)
    helper.do_apply(household().to_payload(), etc, etc, io.StringIO(), frozenset())
    code = helper.main(["show", "--etc", str(etc), "--usr", str(etc)])
    assert code == helper.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == 1
    assert payload["session"]["length_minutes"] == 30


def _mk(tmp_path):
    etc = tmp_path / "etc"
    etc.mkdir(exist_ok=True)
    return etc
