"""Per-profile data, and the PIN the image no longer ships (spec 7d #11).

Two blockers in one file, because they are the same finding from two sides:
what a machine hands a *second* child, and what a machine hands a parent who
has never opened a config file.

* "Profiles are cosmetic -- one journal, one budget, one disclosure counter per
  machine" (forum #4; safety review #18).
* "The one signal that the gate is open is suppressed by the file that opens
  it" (forum #44), and Mags: "the only way I would ever learn my lock is not a
  lock is by reading a file I would never open" (#56).
"""

from __future__ import annotations

import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from kidnix_shell.journal import Journal
from kidnix_shell.session import DailyUsage, SessionPolicy, StartRefusal, refusal_for
from kidnix_shell.settings import (
    DEFAULT_PIN,
    PROFILES_DIR,
    KidState,
    ParentConfig,
    Paths,
    Profile,
    migrate_profile_data,
)

SHIPPED = Path(__file__).resolve().parents[2] / "system_files/etc/kidnix/parent.toml"
SHIPPED_FALLBACK = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/parent.toml"


# --- one directory per child ---------------------------------------------


def test_every_thing_a_child_owns_moves_together(paths: Paths) -> None:
    """A whole ``Paths``, not three extra properties: the Journal, the budget
    and the progress counter move together or none of them does."""
    mine = paths.for_profile("ada")
    assert mine.profile == "ada"
    assert mine.journal_root == paths.data_home / "kidnix" / PROFILES_DIR / "ada" / "journal"
    assert mine.usage_state == paths.state_home / "kidnix" / PROFILES_DIR / "ada" / "usage.toml"
    assert (
        mine.progress_state == paths.state_home / "kidnix" / PROFILES_DIR / "ada" / "progress.toml"
    )


def test_two_children_share_nothing_of_their_own(paths: Paths) -> None:
    ada, bob = paths.for_profile("ada"), paths.for_profile("bob")
    for attribute in ("journal_root", "usage_state", "progress_state", "profile_data"):
        assert getattr(ada, attribute) != getattr(bob, attribute), attribute
    # ...but the machine's own things are still the machine's.
    assert ada.sounds_cache == bob.sounds_cache
    assert ada.parent_config == bob.parent_config


def test_a_profiles_things_stay_inside_kidnix(paths: Paths) -> None:
    """One export, one wipe, one backup still take everything: a parent
    reasoning about "where does my child's work live" gets one answer, and
    ``kidnix-export`` tars ``~/.local/share/kidnix`` whole."""
    mine = paths.for_profile("ada")
    assert (paths.data_home / "kidnix") in mine.journal_root.parents
    assert (paths.state_home / "kidnix") in mine.usage_state.parents


def test_the_pre_profiles_layout_is_still_addressable(paths: Paths) -> None:
    """``profile=""`` is what every machine built before this has on disk."""
    assert paths.journal_root == paths.data_home / "kidnix" / "journal"
    assert paths.usage_state == paths.state_home / "kidnix" / "usage.toml"


# --- the migration -------------------------------------------------------


def legacy(paths: Paths) -> tuple[Path, Path, Path]:
    """Write a pre-profiles machine's data where it used to live."""
    journal = paths.data_home / "kidnix" / "journal" / "2026" / "08" / "18" / "tuxpaint-1"
    journal.mkdir(parents=True)
    (journal / "entry.json").write_text("{}", encoding="utf-8")
    usage = paths.state_home / "kidnix" / "usage.toml"
    usage.parent.mkdir(parents=True, exist_ok=True)
    usage.write_text('day = "2026-08-18"\nseconds = 900\n', encoding="utf-8")
    progress = paths.state_home / "kidnix" / "progress.toml"
    progress.write_text("sessions_completed = 7\n", encoding="utf-8")
    return journal, usage, progress


def test_an_upgraded_machines_things_move_into_the_first_profile(paths: Paths) -> None:
    """**Nobody's drawings disappear on the morning of an upgrade.**"""
    legacy(paths)
    moved = migrate_profile_data(paths, "child")
    mine = paths.for_profile("child")

    assert mine.journal_root.is_dir()
    assert (mine.journal_root / "2026" / "08" / "18" / "tuxpaint-1" / "entry.json").is_file()
    assert mine.usage_state.is_file()
    assert mine.progress_state.is_file()
    assert len(moved) == 3

    # Moved, not copied: two Journals with the same entries in them is a child
    # seeing everything twice the first time they open My Things.
    assert not (paths.data_home / "kidnix" / "journal").exists()
    assert not (paths.state_home / "kidnix" / "usage.toml").exists()


def test_the_migration_is_idempotent(paths: Paths) -> None:
    legacy(paths)
    assert len(migrate_profile_data(paths, "child")) == 3
    assert migrate_profile_data(paths, "child") == []
    assert migrate_profile_data(paths, "child") == []


def test_the_migration_never_overwrites_a_profile_that_already_has_things(paths: Paths) -> None:
    """If a machine somehow has both, the profile's own copy wins and the old
    one is left where a parent can find it -- never merged, never clobbered."""
    legacy(paths)
    mine = paths.for_profile("child")
    mine.journal_root.mkdir(parents=True)
    (mine.journal_root / "keep-me").write_text("mine", encoding="utf-8")

    migrate_profile_data(paths, "child")
    assert (mine.journal_root / "keep-me").is_file()
    assert (paths.data_home / "kidnix" / "journal").is_dir()  # untouched


def test_a_fresh_machine_has_nothing_to_migrate(paths: Paths) -> None:
    assert migrate_profile_data(paths, "child") == []
    assert migrate_profile_data(paths, "") == []


def test_the_migrated_journal_actually_loads(paths: Paths) -> None:
    """The end of the chain: what the child sees in My Things afterwards."""
    from .conftest import write_png

    entry_dir = paths.data_home / "kidnix" / "journal" / "2026" / "08" / "18" / "tuxpaint-1"
    entry_dir.mkdir(parents=True)
    (entry_dir / "entry.json").write_text(
        '{"id": "tuxpaint-1", "activity_id": "tuxpaint", "created": "2026-08-18T14:00:00",'
        ' "updated": "2026-08-18T14:00:00", "title": "Draw", "source_path": "/x.png",'
        ' "mime": "image/png", "versions": []}',
        encoding="utf-8",
    )
    write_png(entry_dir / "thumb.png")

    migrate_profile_data(paths, "child")
    journal = Journal(paths.for_profile("child").journal_root)
    journal.load()
    assert [e.id for e in journal.entries] == ["tuxpaint-1"]
    assert journal.entries[0].thumbnail is not None


# --- the budget and the grid are this child's ----------------------------


def test_the_daily_budget_is_per_child(paths: Paths) -> None:
    """A second child's first sitting must not start with a sibling's hour
    already spent: the budget is a policy about one child's afternoon."""
    today = date(2026, 8, 18)
    ada = DailyUsage.load(paths.for_profile("ada").usage_state, today)
    ada.add(45 * 60)
    ada.save()

    bob = DailyUsage.load(paths.for_profile("bob").usage_state, today)
    assert bob.seconds == 0
    assert DailyUsage.load(paths.for_profile("ada").usage_state, today).seconds == 45 * 60


def test_progressive_disclosure_counts_this_childs_sessions(paths: Paths) -> None:
    """A younger sibling does not inherit an older one's grown grid."""
    ada = KidState.load(paths.for_profile("ada").progress_state)
    for _ in range(6):
        ada.complete_session()
    assert KidState.load(paths.for_profile("bob").progress_state).sessions_completed == 0
    assert KidState.load(paths.for_profile("ada").progress_state).sessions_completed == 6


# --- the PIN the image no longer ships -----------------------------------


@pytest.mark.parametrize("path", [SHIPPED, SHIPPED_FALLBACK])
def test_the_shipped_parent_config_carries_no_pin(path: Path) -> None:
    """**The blocker, inverted.** ``is_default`` is only ever true when no
    ``pin_hash`` was found, and the file used to have one -- so the warning
    that would have told a parent their gate was open never appeared."""
    assert path.is_file(), path
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert "pin_hash" not in data
    assert "pin_salt" not in data


def test_the_two_shipped_copies_are_byte_identical() -> None:
    assert SHIPPED.read_bytes() == SHIPPED_FALLBACK.read_bytes()


def test_the_shell_treats_the_shipped_file_as_must_set_a_pin() -> None:
    config = ParentConfig.load(SHIPPED)
    assert config.must_set_pin
    assert config.is_default
    assert config.pin_is_starter
    # The rest of the file still has to work, or the gate would be the only
    # thing on a machine that could not start a session.
    assert config.default_session_minutes == 25
    assert [p.id for p in config.profiles] == ["child"]
    assert config.is_allowed("tuxpaint")


def test_choosing_a_pin_closes_the_gate_even_when_nothing_could_be_written() -> None:
    """The PIN is in force the moment it is chosen. Whether it survives a
    restart is a separate question the sheet answers in words."""
    config = ParentConfig.load(SHIPPED)
    assert config.must_set_pin
    config.set_pin("8471")
    assert not config.must_set_pin
    assert not config.is_default
    assert config.check_pin("8471")
    assert not config.check_pin(DEFAULT_PIN)


def test_a_config_with_a_pin_does_not_ask_for_a_new_one(tmp_path: Path) -> None:
    path = tmp_path / "parent.toml"
    config = ParentConfig()
    config.set_pin("2468")
    config.save(path)
    reloaded = ParentConfig.load(path)
    assert not reloaded.must_set_pin
    assert reloaded.check_pin("2468")


def test_writing_a_config_that_has_no_pin_does_not_invent_one(tmp_path: Path) -> None:
    """``__post_init__`` supplies a fallback hash so nothing has to cope with
    an empty one; round-tripping it to disk would silently re-open the gate."""
    path = tmp_path / "parent.toml"
    ParentConfig().save(path)
    text = path.read_text(encoding="utf-8")
    assert "pin_hash =" not in text
    assert ParentConfig.load(path).must_set_pin


def test_a_hand_written_config_with_a_pin_is_believed(tmp_path: Path) -> None:
    """A parent pre-seeding a PIN in an image build is a supported thing."""
    from kidnix_shell.settings import hash_pin

    salt, digest = hash_pin("9182")
    path = tmp_path / "parent.toml"
    path.write_text(f'pin_salt = "{salt}"\npin_hash = "{digest}"\n', encoding="utf-8")
    config = ParentConfig.load(path)
    assert not config.must_set_pin
    assert config.check_pin("9182")
    assert not config.pin_is_starter


# --- Who's here lists every profile ---------------------------------------


def test_every_profile_in_the_config_is_a_profile(tmp_path: Path) -> None:
    """ "Who's here?" draws ``config.profiles``; two children in the file are
    two faces on the screen and two sets of everything behind them."""
    path = tmp_path / "parent.toml"
    path.write_text(
        '[[profiles]]\nid = "ada"\nname = "Ada"\n\n[[profiles]]\nid = "bob"\nname = "Bob"\n',
        encoding="utf-8",
    )
    config = ParentConfig.load(path)
    assert [p.id for p in config.profiles] == ["ada", "bob"]
    # Distinct identities, so the band tint and the badge say whose turn it is.
    assert config.profiles[0].badge != config.profiles[1].badge
    assert config.profile("bob") == config.profiles[1]
    assert config.profile("nobody") is None


def test_a_profiles_own_paths_are_keyed_on_its_id(paths: Paths) -> None:
    ada = Profile(id="ada", name="Ada")
    assert paths.for_profile(ada.id).journal_root.parent.name == "ada"


def test_a_session_started_now_spends_the_right_childs_budget(paths: Paths) -> None:
    """The integration the shell does on "Who's here?": the usage file the
    session counts against is the one belonging to the child who just pressed
    their own face."""
    now = datetime(2026, 8, 18, 12, 0)
    ada = DailyUsage.for_now(paths.for_profile("ada").usage_state, now)
    ada.add(30 * 60)
    ada.save()
    bob = DailyUsage.for_now(paths.for_profile("bob").usage_state, now)
    assert bob.remaining(60 * 60) == 60 * 60
    assert ada.remaining(60 * 60) == 30 * 60


# --- and so is "your sitting is over" (ADR-0014) --------------------------


def test_one_childs_ending_does_not_end_their_siblings_afternoon(paths: Paths) -> None:
    """The defect the ADR is about, at the level the fix lives at.

    Ada presses "All done" at ten past four. Before ADR-0014 the *machine*
    rested until the next window or tomorrow, so Bob could not start without a
    grown-up at the gate. Now the mark is Ada's, in Ada's own usage file, and
    Bob's is untouched.
    """
    now = datetime(2026, 8, 18, 16, 10)
    policy = SessionPolicy()
    ada = DailyUsage.for_now(paths.for_profile("ada").usage_state, now)
    bob = DailyUsage.for_now(paths.for_profile("bob").usage_state, now)

    ada.add(25 * 60)
    ada.rest(now)

    later = now + timedelta(minutes=1)
    assert refusal_for(policy, ada, later) is StartRefusal.RESTED
    assert refusal_for(policy, bob, later) is StartRefusal.OK
    # Read back off the disk, which is how the shell asks about a child who is
    # not the live one: nothing of Ada's is in Bob's file.
    assert DailyUsage.for_now(paths.for_profile("bob").usage_state, later).rested_at is None
    assert DailyUsage.for_now(paths.for_profile("ada").usage_state, later).rested_at == now


def test_the_machine_only_rests_when_every_child_has(paths: Paths) -> None:
    """What ``app.ShellWindow.anyone_may_start`` is asking, in one line."""
    now = datetime(2026, 8, 18, 16, 10)
    policy = SessionPolicy()
    children = [
        DailyUsage.for_now(paths.for_profile(name).usage_state, now) for name in ("ada", "bob")
    ]

    def anyone_may_start() -> bool:
        return any(refusal_for(policy, usage, now) is StartRefusal.OK for usage in children)

    assert anyone_may_start()
    children[0].rest(now)
    assert anyone_may_start()  # Bob still has an afternoon
    children[1].rest(now)
    assert not anyone_may_start()  # *now* the machine is resting


def test_a_one_child_machine_behaves_exactly_as_it_did(paths: Paths) -> None:
    """The ADR's own constraint. One profile, one mark, one Resting screen."""
    now = datetime(2026, 8, 18, 16, 10)
    policy = SessionPolicy()
    only = DailyUsage.for_now(paths.for_profile("child").usage_state, now)
    only.rest(now)
    assert refusal_for(policy, only, now + timedelta(seconds=30)) is StartRefusal.RESTED
    tomorrow = datetime(2026, 8, 19, 8, 0)
    fresh = DailyUsage.for_now(paths.for_profile("child").usage_state, tomorrow)
    assert refusal_for(policy, fresh, tomorrow) is StartRefusal.OK
