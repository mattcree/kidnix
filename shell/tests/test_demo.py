"""The --demo world. Built with the real loader, so this also guards the schema."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from kidnix_shell.demo import (
    DEMO_ACTIVITIES,
    NEEDS_CONTENT,
    NOT_ALLOWED,
    STUBBORN,
    TOO_OLD,
    build_demo_world,
)
from kidnix_shell.journal import Journal
from kidnix_shell.session import DailyUsage, Phase, Session, SessionPolicy

from .conftest import NOW, write_png


def test_the_demo_world_loads_through_the_real_manifest_loader(tmp_path: Path) -> None:
    root, activities, _allowed = build_demo_world(tmp_path)
    assert len(activities) == len(DEMO_ACTIVITIES)
    assert root == tmp_path


def test_the_demo_has_more_than_one_page_of_tiles(tmp_path: Path) -> None:
    """So --demo exercises the pager, not just the grid."""
    _, activities, _ = build_demo_world(tmp_path)
    assert len(activities) > 12


def test_one_demo_activity_is_outside_the_allow_list(tmp_path: Path) -> None:
    """So --demo shows an outline-only tile (spec S2)."""
    _, activities, allowed = build_demo_world(tmp_path)
    ids = {a.id for a in activities}
    assert ids >= NOT_ALLOWED
    assert not (NOT_ALLOWED & set(allowed))


def test_one_demo_activity_refuses_to_quit_politely(tmp_path: Path) -> None:
    """So --demo exercises the SIGKILL escalation in Put away, not just SIGTERM."""
    _, activities, _ = build_demo_world(tmp_path)
    stubborn = [a for a in activities if a.id in STUBBORN]
    assert stubborn
    assert "--stubborn" in stubborn[0].exec_argv


def test_every_demo_activity_watches_its_own_directory(tmp_path: Path) -> None:
    _, activities, _ = build_demo_world(tmp_path)
    seen: set[Path] = set()
    for activity in activities:
        assert len(activity.journal_watch) == 1
        directory = activity.journal_watch[0]
        assert directory.is_dir()
        assert directory not in seen
        seen.add(directory)
        assert activity.journal_glob == "*.png"


def test_the_resumable_demo_activities_take_a_file(tmp_path: Path) -> None:
    _, activities, _ = build_demo_world(tmp_path)
    resumable = [a for a in activities if a.supports_resume]
    assert resumable
    argv = resumable[0].resume_argv(Path("/tmp/x.png"))
    assert argv[-2:] == ["--open", "/tmp/x.png"]


def test_a_demo_journal_import_works_end_to_end(tmp_path: Path) -> None:
    _, activities, _ = build_demo_world(tmp_path)
    activity = next(a for a in activities if a.id == "scribble")
    journal = Journal(tmp_path / "journal")
    write_png(activity.journal_watch[0] / "scribble.png")
    entry = journal.import_file(
        activity.journal_watch[0] / "scribble.png",
        activity.id,
        activity_name=activity.name,
        now=NOW,
    )
    assert entry is not None
    assert entry.activity_id == "scribble"


def test_the_demo_session_reaches_goodbye_in_three_minutes() -> None:
    """The whole ritual has to fit in a demo, and in a CI run."""
    policy = SessionPolicy.demo()
    session = Session(policy=policy, usage=DailyUsage(day=NOW.date()))
    assert session.start(NOW)
    assert session.phase(NOW + timedelta(seconds=30)) is Phase.RUNNING
    assert session.phase(NOW + timedelta(seconds=125)) is Phase.ENDING_OFFER
    assert session.phase(NOW + timedelta(seconds=165)) is Phase.PUT_AWAY
    assert session.phase(NOW + timedelta(seconds=181)) is Phase.ENDED


def test_the_demo_never_touches_a_real_bedtime() -> None:
    """A demo at 8pm must still run."""
    assert not SessionPolicy.demo().is_bedtime(NOW.replace(hour=20))


def test_one_demo_activity_has_nothing_to_open_yet(tmp_path: Path) -> None:
    """So --demo exercises the content_required predicate (05 Lib-4).

    The Library's directory is created and left empty, which is exactly the
    state of a freshly installed machine before a parent adds a ZIM.
    """
    _, activities, _ = build_demo_world(tmp_path)
    library = next(a for a in activities if a.id in NEEDS_CONTENT)
    assert library.content_required
    assert library.available is True, "the fake program is there"
    assert library.has_content is False
    assert library.usable is False
    assert library.on_home is False


def test_one_demo_activity_is_above_the_demo_profile_age_band(tmp_path: Path) -> None:
    """So --demo shows the age filter as well: no tile, and nothing to ask for."""
    from kidnix_shell.activities import in_age_band

    _, activities, _ = build_demo_world(tmp_path)
    too_old = next(a for a in activities if a.id in TOO_OLD)
    assert (too_old.age_min, too_old.age_max) == (7, 10)
    assert in_age_band(too_old, (4, 5)) is False
    assert in_age_band(too_old, (7, 10)) is True


def test_the_demo_still_has_more_than_one_page_after_the_new_filters(
    tmp_path: Path,
) -> None:
    """Eight tiles a page now, so the pager matters more than it did."""
    _, activities, _ = build_demo_world(tmp_path)
    shown = [a for a in activities if a.on_home and a.id not in TOO_OLD]
    assert len(shown) > 8
