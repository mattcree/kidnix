"""Paths, the parent config, and the PIN."""

from __future__ import annotations

from pathlib import Path

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
