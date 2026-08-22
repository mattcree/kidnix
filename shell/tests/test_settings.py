"""Paths, the parent config, and the PIN."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from kidnix_shell import settings
from kidnix_shell.settings import (
    DEFAULT_PIN,
    ParentConfig,
    Paths,
    Profile,
    hash_pin,
    verify_pin,
)


def test_paths_come_from_the_environment(tmp_path: Path) -> None:
    paths = Paths.from_env(
        {
            "HOME": str(tmp_path),
            "XDG_DATA_HOME": str(tmp_path / "d"),
            "XDG_CONFIG_HOME": str(tmp_path / "c"),
        }
    )
    assert paths.home == tmp_path
    assert paths.data_home == tmp_path / "d"
    assert paths.journal_root == tmp_path / "d" / "kidnix" / "journal"


def test_paths_fall_back_to_the_xdg_defaults(tmp_path: Path) -> None:
    paths = Paths.from_env({"HOME": str(tmp_path)})
    assert paths.data_home == tmp_path / ".local" / "share"
    assert paths.state_home == tmp_path / ".local" / "state"
    assert paths.usage_state.name == "usage.toml"


def test_the_pin_is_never_stored_in_the_clear() -> None:
    salt, digest = hash_pin("1234")
    assert "1234" not in salt + digest
    assert len(digest) == 64


def test_the_same_pin_and_salt_hash_the_same() -> None:
    salt, digest = hash_pin("4321")
    assert hash_pin("4321", salt) == (salt, digest)


def test_different_salts_give_different_hashes() -> None:
    assert hash_pin("1234")[1] != hash_pin("1234")[1]


def test_verifying_a_pin() -> None:
    salt, digest = hash_pin("9876")
    assert verify_pin("9876", salt, digest)
    assert not verify_pin("9875", salt, digest)
    assert not verify_pin("9876", "", digest)
    assert not verify_pin("9876", "not-hex", digest)


def test_a_fresh_config_takes_the_dev_default_pin() -> None:
    config = ParentConfig()
    assert config.check_pin(DEFAULT_PIN)
    assert not config.check_pin("0000")


def test_changing_the_pin() -> None:
    config = ParentConfig()
    config.set_pin("2468")
    assert config.check_pin("2468")
    assert not config.check_pin(DEFAULT_PIN)


def test_the_allow_list_defaults_to_everything() -> None:
    config = ParentConfig()
    assert config.is_allowed("anything-at-all")


def test_the_allow_list_restricts_when_set() -> None:
    config = ParentConfig(allowed_activity_ids=["tuxpaint"])
    assert config.is_allowed("tuxpaint")
    assert not config.is_allowed("supertux")


def test_a_config_round_trips_through_toml(tmp_path: Path) -> None:
    config = ParentConfig(
        default_session_minutes=30,
        allowed_activity_ids=["tuxpaint", "gcompris"],
        profiles=[Profile(id="rosa", name="Rosa", colour_primary="#0f8a8a")],
    )
    config.set_pin("5555")
    path = config.save(tmp_path / "parent.toml")

    reloaded = ParentConfig.load(path)
    assert reloaded.check_pin("5555")
    assert reloaded.default_session_minutes == 30
    assert reloaded.allowed_activity_ids == ["tuxpaint", "gcompris"]
    assert reloaded.profiles[0].name == "Rosa"
    assert reloaded.profiles[0].colour_primary == "#0f8a8a"


def test_an_absent_allow_list_round_trips_as_none(tmp_path: Path) -> None:
    path = ParentConfig().save(tmp_path / "parent.toml")
    assert ParentConfig.load(path).allowed_activity_ids is None


def test_a_missing_config_file_gives_workable_defaults(tmp_path: Path) -> None:
    config = ParentConfig.load(tmp_path / "nope.toml")
    assert config.check_pin(DEFAULT_PIN)
    assert config.profiles


def test_a_corrupt_config_file_does_not_lock_the_parent_out(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text("this is not toml [[[", encoding="utf-8")
    config = ParentConfig.load(path)
    assert config.check_pin(DEFAULT_PIN)


def test_malformed_profiles_are_skipped_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text(
        '[[profiles]]\nname = "no id here"\n\n[[profiles]]\nid = "ok"\nname = "Ok"\n',
        encoding="utf-8",
    )
    config = ParentConfig.load(path)
    assert [p.id for p in config.profiles] == ["ok"]


def test_a_config_with_no_profiles_still_has_one() -> None:
    assert ParentConfig(profiles=[]).profiles


def test_looking_a_profile_up_by_id() -> None:
    config = ParentConfig(profiles=[Profile(id="sam", name="Sam")])
    assert config.profile("sam") is not None
    assert config.profile("nobody") is None


def test_quotes_in_a_name_do_not_break_the_toml(tmp_path: Path) -> None:
    config = ParentConfig(profiles=[Profile(id="x", name='Sam "The Boss"')])
    path = config.save(tmp_path / "parent.toml")
    assert ParentConfig.load(path).profiles[0].name == 'Sam "The Boss"'


# --- ownership (v0.1.1) --------------------------------------------------
#
# docs/spikes/session-integration.md open question 2: parent.toml was falling
# back to ~/.config/kidnix/parent.toml, which the child owns -- so the PIN, the
# allow-list and the profiles were child-writable in principle. The shell now
# reads the parent config *only* from root-owned locations.


@pytest.fixture
def system_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Stand-ins for /etc/kidnix and /usr/share/kidnix."""
    etc = tmp_path / "etc" / "kidnix"
    usr = tmp_path / "usr" / "share" / "kidnix"
    etc.mkdir(parents=True)
    usr.mkdir(parents=True)
    monkeypatch.setattr(settings, "CONFIG_SEARCH_PATH", [etc, usr])
    return etc, usr


def kid_paths(tmp_path: Path) -> Paths:
    home = tmp_path / "home"
    return Paths(
        home=home,
        data_home=home / ".local" / "share",
        config_home=home / ".config",
        cache_home=home / ".cache",
        state_home=home / ".local" / "state",
    )


def test_the_parent_config_comes_from_etc_first(
    tmp_path: Path, system_dirs: tuple[Path, Path]
) -> None:
    etc, usr = system_dirs
    (usr / "parent.toml").write_text("default_session_minutes = 15\n", encoding="utf-8")
    (etc / "parent.toml").write_text("default_session_minutes = 40\n", encoding="utf-8")
    assert kid_paths(tmp_path).parent_config == etc / "parent.toml"
    assert ParentConfig.discover().default_session_minutes == 40


def test_the_image_defaults_are_the_fallback(
    tmp_path: Path, system_dirs: tuple[Path, Path]
) -> None:
    _etc, usr = system_dirs
    (usr / "parent.toml").write_text("default_session_minutes = 15\n", encoding="utf-8")
    assert kid_paths(tmp_path).parent_config == usr / "parent.toml"
    assert ParentConfig.discover().default_session_minutes == 15


def test_the_child_can_never_supply_the_pin_or_the_allow_list(
    tmp_path: Path, system_dirs: tuple[Path, Path]
) -> None:
    """The whole point: a file in the kid's home is not a parent config."""
    paths = kid_paths(tmp_path)
    kid_copy = paths.config_home / "kidnix" / "parent.toml"
    kid_copy.parent.mkdir(parents=True)
    salt, digest = hash_pin("0000")
    kid_copy.write_text(
        f'pin_salt = "{salt}"\npin_hash = "{digest}"\nallowed_activity_ids = ["everything"]\n',
        encoding="utf-8",
    )
    assert paths.parent_config is None

    config = ParentConfig.discover()
    assert not config.check_pin("0000")  # the child's PIN is not the PIN
    assert config.check_pin(DEFAULT_PIN)  # the built-in default is
    assert config.is_default and config.read_only


def test_no_parent_config_anywhere_warns_loudly(system_dirs: tuple[Path, Path]) -> None:
    out = io.StringIO()
    settings.warn_no_parent_config(out)
    text = out.getvalue()
    assert DEFAULT_PIN in text
    assert "NO PARENT CONFIG" in text
    for directory in settings.CONFIG_SEARCH_PATH:
        assert str(directory) in text


def test_a_root_owned_config_is_read_only_to_the_shell(system_dirs: tuple[Path, Path]) -> None:
    etc, _usr = system_dirs
    (etc / "parent.toml").write_text("default_session_minutes = 20\n", encoding="utf-8")
    config = ParentConfig.discover()
    assert config.read_only
    with pytest.raises(PermissionError):
        config.save()


def test_a_read_only_config_can_still_be_written_somewhere_else(
    tmp_path: Path, system_dirs: tuple[Path, Path]
) -> None:
    """The parent's own tooling writes it; the child's shell does not."""
    etc, _usr = system_dirs
    (etc / "parent.toml").write_text("default_session_minutes = 20\n", encoding="utf-8")
    config = ParentConfig.discover()
    written = config.save(tmp_path / "copy.toml")
    assert written.is_file()


def test_an_explicit_config_path_is_still_honoured(
    tmp_path: Path, system_dirs: tuple[Path, Path]
) -> None:
    """--config is a developer naming a file, not the child's environment."""
    path = tmp_path / "dev.toml"
    path.write_text("default_session_minutes = 12\n", encoding="utf-8")
    config = ParentConfig.discover(path)
    assert config.default_session_minutes == 12
    assert not config.read_only


def test_a_config_with_no_pin_at_all_is_flagged_as_default(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text("default_session_minutes = 20\n", encoding="utf-8")
    config = ParentConfig.load(path)
    assert config.is_default
    assert config.check_pin(DEFAULT_PIN)


def test_the_session_policy_has_the_same_ownership_rule(
    tmp_path: Path, system_dirs: tuple[Path, Path]
) -> None:
    etc, _usr = system_dirs
    paths = kid_paths(tmp_path)
    kid_copy = paths.config_home / "kidnix" / "session.toml"
    kid_copy.parent.mkdir(parents=True)
    kid_copy.write_text("daily_budget_minutes = 600\n", encoding="utf-8")
    assert paths.session_config is None
    (etc / "session.toml").write_text("daily_budget_minutes = 45\n", encoding="utf-8")
    assert paths.session_config == etc / "session.toml"


def test_the_kid_writable_state_stays_in_the_kid_s_home(tmp_path: Path) -> None:
    """Usage, favourites and the things they made are theirs, and harmless."""
    paths = kid_paths(tmp_path)
    assert paths.state_home in paths.usage_state.parents
    assert paths.data_home in paths.journal_root.parents
    assert paths.cache_home in paths.sounds_cache.parents
