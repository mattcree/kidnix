"""Paths, the parent config, and the PIN."""

from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import pytest

from kidnix_shell import settings
from kidnix_shell.next_after import DEFAULT_NEXT_AFTER
from kidnix_shell.settings import (
    DEFAULT_HOVER_DWELL_MS,
    DEFAULT_PIN,
    DEFAULT_PROFILE,
    MAX_HOVER_DWELL_MS,
    MIN_HOVER_DWELL_MS,
    HomeConfig,
    KidState,
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


# --- the allow-list (spec S2, SYNTHESIS G3) -------------------------------


def test_an_empty_allow_list_means_all_not_none() -> None:
    """A parent panel that unticks the last box must not empty Home.

    Home with nothing on it but "All done" is not a setting anybody wants by
    accident, and there is no UI to get out of it. Empty means all.
    """
    config = ParentConfig(allowed_activity_ids=[])
    assert config.is_allowed("tuxpaint")
    assert config.is_allowed("anything-at-all")


def test_a_missing_allow_list_means_all() -> None:
    assert ParentConfig(allowed_activity_ids=None).is_allowed("tuxpaint")


def test_a_named_allow_list_restricts_home() -> None:
    config = ParentConfig(allowed_activity_ids=["tuxpaint", "ktuberling"])
    assert config.is_allowed("tuxpaint")
    assert config.is_allowed("ktuberling")
    assert not config.is_allowed("supertux")


def test_an_empty_allow_list_round_trips_through_toml(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    ParentConfig(allowed_activity_ids=[]).save(path)
    reloaded = ParentConfig.load(path)
    assert reloaded.allowed_activity_ids == []
    assert reloaded.is_allowed("tuxpaint")


def test_the_shipped_parent_config_allows_everything() -> None:
    """system_files ships `allowed_activity_ids = []`, i.e. no restriction."""
    shipped = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/parent.toml"
    if not shipped.is_file():  # pragma: no cover - outside the checkout
        pytest.skip("running outside the kidnix checkout")
    config = ParentConfig.load(shipped)
    assert config.allowed_activity_ids == []
    assert config.is_allowed("tuxpaint")


def test_the_two_shipped_parent_configs_are_byte_identical() -> None:
    root = Path(__file__).resolve().parents[2] / "system_files"
    usr, etc = root / "usr/share/kidnix/parent.toml", root / "etc/kidnix/parent.toml"
    if not usr.is_file() or not etc.is_file():  # pragma: no cover
        pytest.skip("running outside the kidnix checkout")
    assert usr.read_bytes() == etc.read_bytes()


# --- the profile's age band (01 #35, SYNTHESIS B8) -------------------------


def test_the_default_profile_is_banded_four_to_five() -> None:
    assert DEFAULT_PROFILE.age_band == "4-5"
    assert DEFAULT_PROFILE.age_range == (4, 5)


def test_the_shipped_profile_is_banded_four_to_five() -> None:
    shipped = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/parent.toml"
    if not shipped.is_file():  # pragma: no cover
        pytest.skip("running outside the kidnix checkout")
    profile = ParentConfig.load(shipped).profiles[0]
    assert profile.age_range == (4, 5)


def test_a_profile_with_no_band_has_no_range() -> None:
    assert replace(DEFAULT_PROFILE, age_band="").age_range is None
    assert replace(DEFAULT_PROFILE, age_band="nonsense").age_range is None


def test_a_band_round_trips_through_toml(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    ParentConfig(profiles=[replace(DEFAULT_PROFILE, age_band="6-8")]).save(path)
    assert ParentConfig.load(path).profiles[0].age_range == (6, 8)


# --- spec 7b: hover dwell, progressive disclosure, S1b's options ----------


def test_the_hover_dwell_defaults_to_450_ms() -> None:
    """09 section 2. It is a key, not a constant, because P5 will move it."""
    assert ParentConfig().hover_dwell_ms == DEFAULT_HOVER_DWELL_MS == 450


def test_a_parent_can_set_the_hover_dwell(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text("hover_dwell_ms = 350\n", encoding="utf-8")
    assert ParentConfig.load(path).hover_dwell_ms == 350


def test_a_nonsense_hover_dwell_falls_back_rather_than_muting_the_shell(
    tmp_path: Path,
) -> None:
    path = tmp_path / "parent.toml"
    path.write_text('hover_dwell_ms = "soon"\n', encoding="utf-8")
    assert ParentConfig.load(path).hover_dwell_ms == DEFAULT_HOVER_DWELL_MS


def test_an_absurd_hover_dwell_is_clamped(tmp_path: Path) -> None:
    """A hand edit of 0 would make the shell chatter at every tile crossed."""
    path = tmp_path / "parent.toml"
    path.write_text("hover_dwell_ms = 0\n", encoding="utf-8")
    assert ParentConfig.load(path).hover_dwell_ms == MIN_HOVER_DWELL_MS
    path.write_text("hover_dwell_ms = 99999\n", encoding="utf-8")
    assert ParentConfig.load(path).hover_dwell_ms == MAX_HOVER_DWELL_MS


def test_home_starts_at_six_tiles_and_grows_every_two_sessions() -> None:
    """SYNTHESIS B2: first-run default 5-6, growing toward the allow-list."""
    home = HomeConfig()
    assert home.initial_tiles == 6
    assert home.reveal_every_sessions == 2
    assert home.tiles_visible(total=12, sessions_completed=0) == 6
    assert home.tiles_visible(total=12, sessions_completed=1) == 6
    assert home.tiles_visible(total=12, sessions_completed=2) == 7
    assert home.tiles_visible(total=12, sessions_completed=3) == 7
    assert home.tiles_visible(total=12, sessions_completed=4) == 8


def test_home_never_shows_more_than_there_is() -> None:
    """The ceiling is the allow-list and availability, not the counter."""
    assert HomeConfig().tiles_visible(total=4, sessions_completed=500) == 4


def test_a_tile_once_revealed_never_goes_away() -> None:
    home = HomeConfig()
    counts = [home.tiles_visible(12, sessions) for sessions in range(20)]
    assert counts == sorted(counts)


def test_show_everything_overrides_the_whole_mechanism() -> None:
    home = HomeConfig(show_everything=True)
    assert home.tiles_visible(total=12, sessions_completed=0) == 12


def test_the_home_table_is_read_from_the_parent_config(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text(
        "[home]\ninitial_tiles = 4\nreveal_every_sessions = 5\nshow_everything = true\n",
        encoding="utf-8",
    )
    home = ParentConfig.load(path).home
    assert (home.initial_tiles, home.reveal_every_sessions, home.show_everything) == (4, 5, True)


def test_a_missing_home_table_is_the_defaults(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text("default_session_minutes = 25\n", encoding="utf-8")
    assert ParentConfig.load(path).home == HomeConfig()


def test_a_zero_reveal_interval_does_not_divide_by_zero(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text("[home]\nreveal_every_sessions = 0\n", encoding="utf-8")
    home = ParentConfig.load(path).home
    assert home.tiles_visible(12, 3) >= home.initial_tiles


def test_the_next_after_options_come_from_the_parent_config(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text(
        '[[next_after]]\nid = "swing"\nlabel = "Go on the swing"\n',
        encoding="utf-8",
    )
    options = ParentConfig.load(path).next_after
    assert [option.id for option in options] == ["swing"]


def test_a_config_with_no_next_after_gets_the_shipped_set(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text("default_session_minutes = 25\n", encoding="utf-8")
    assert ParentConfig.load(path).next_after == DEFAULT_NEXT_AFTER


def test_a_profile_can_skip_s1b(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    path.write_text(
        '[[profiles]]\nid = "kid"\nname = "Sam"\nskip_next_choice = true\n',
        encoding="utf-8",
    )
    assert ParentConfig.load(path).profiles[0].skip_next_choice is True


def test_a_profile_is_asked_by_default() -> None:
    assert DEFAULT_PROFILE.skip_next_choice is False


def test_the_new_keys_round_trip_through_toml(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    original = ParentConfig(
        hover_dwell_ms=350,
        home=HomeConfig(initial_tiles=5, reveal_every_sessions=3, show_everything=True),
        profiles=[replace(DEFAULT_PROFILE, skip_next_choice=True)],
    )
    original.save(path)
    reloaded = ParentConfig.load(path)
    assert reloaded.hover_dwell_ms == 350
    assert reloaded.home == original.home
    assert reloaded.profiles[0].skip_next_choice is True
    assert [o.id for o in reloaded.next_after] == [o.id for o in DEFAULT_NEXT_AFTER]


# --- kid state (progress.toml) -------------------------------------------


def test_a_fresh_machine_has_completed_no_sessions(tmp_path: Path) -> None:
    assert KidState.load(tmp_path / "progress.toml").sessions_completed == 0


def test_completing_a_session_counts_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "progress.toml"
    state = KidState.load(path)
    assert state.complete_session() == 1
    assert state.complete_session() == 2
    assert KidState.load(path).sessions_completed == 2


def test_a_corrupt_progress_file_starts_fresh_rather_than_crashing(tmp_path: Path) -> None:
    path = tmp_path / "progress.toml"
    path.write_text("this is not toml at all {{{", encoding="utf-8")
    assert KidState.load(path).sessions_completed == 0


def test_a_negative_count_is_not_believed(tmp_path: Path) -> None:
    path = tmp_path / "progress.toml"
    path.write_text("sessions_completed = -4\n", encoding="utf-8")
    assert KidState.load(path).sessions_completed == 0


def test_the_progress_file_is_kid_owned_and_separate_from_the_daily_usage(
    paths: Paths,
) -> None:
    """It counts across the life of the machine; usage.toml resets at 04:00."""
    assert paths.progress_state != paths.usage_state
    assert paths.state_home in paths.progress_state.parents


def test_saving_progress_to_an_unwritable_place_is_not_fatal(tmp_path: Path) -> None:
    """A full disk must never be the thing that ends a child's session."""
    blocked = tmp_path / "blocked"
    blocked.write_text("I am a file, not a directory", encoding="utf-8")
    state = KidState.load(blocked / "progress.toml")
    state.complete_session()  # must not raise
    assert state.sessions_completed == 1
