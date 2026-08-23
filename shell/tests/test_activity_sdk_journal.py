"""``save_entry``: the activity writes its own card in My Things.

The property under all of these is that the shell's own loader
(:class:`kidnix_shell.journal.Journal`) reads what the SDK writes. Anything
else is an entry a child cannot find.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from kidnix_activity.env import ACTIVITY_ID_VAR, PROFILE_ID_VAR, LaunchEnv
from kidnix_activity.journal import (
    CAPTION_NAME,
    META_NAME,
    JournalError,
    save_entry,
    title_for,
)
from kidnix_shell.journal import Journal
from kidnix_shell.voice import NOTE_NAME

from .conftest import NOW, write_png


def launch_env(tmp_path: Path, profile: str = "robin") -> LaunchEnv:
    home = tmp_path / "home"
    return LaunchEnv.from_env(
        {
            "HOME": str(home),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            ACTIVITY_ID_VAR: "hello-draw",
            PROFILE_ID_VAR: profile,
        }
    )


def keep(tmp_path: Path, **kwargs: object) -> tuple[LaunchEnv, Path]:
    launch = launch_env(tmp_path)
    source = write_png(tmp_path / "work" / "square.png")
    return launch, source


# --- the layout is the shell's -------------------------------------------


def test_the_entry_lands_in_the_profiles_journal(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch, now=NOW)
    assert entry.directory.is_dir()
    assert "profiles/robin/journal" in entry.directory.as_posix()
    assert entry.directory.parent.parent.parent.name == "2026"
    assert entry.directory.parent.parent.name == "08"
    assert entry.directory.parent.name == "18"


def test_the_shells_own_loader_reads_it(tmp_path: Path) -> None:
    """The whole contract in one assertion."""
    launch, source = keep(tmp_path)
    save_entry("picture", [source], caption="A teal square", launch=launch, now=NOW)
    journal = Journal(launch.journal_root)
    journal.load()
    assert len(journal.entries) == 1
    assert journal.entries[0].title == "A teal square"
    assert journal.entries[0].activity_id == "hello-draw"
    assert journal.entries[0].latest_path is not None
    assert journal.entries[0].latest_path.is_file()


def test_the_entry_id_is_spelt_the_way_the_importer_spells_it(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch, now=NOW)
    assert entry.id.startswith("hello-draw-120000-")
    assert entry.directory.name == entry.id


def test_the_file_is_copied_not_moved(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch, now=NOW)
    assert source.is_file()
    assert (entry.directory / "v001.png").read_bytes() == source.read_bytes()


def test_several_files_become_several_versions(tmp_path: Path) -> None:
    launch = launch_env(tmp_path)
    first = write_png(tmp_path / "work" / "one.png", colour=(255, 0, 0))
    second = write_png(tmp_path / "work" / "two.png", colour=(0, 255, 0))
    entry = save_entry("picture", [first, second], launch=launch, now=NOW)
    assert [v.filename for v in entry.versions] == ["v001.png", "v002.png"]
    assert entry.latest_path is not None
    assert entry.latest_path.name == "v002.png"


def test_the_same_file_twice_is_stored_once(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source, source], launch=launch, now=NOW)
    assert len(entry.versions) == 1


def test_two_saves_in_the_same_second_do_not_collide(tmp_path: Path) -> None:
    launch = launch_env(tmp_path)
    first = write_png(tmp_path / "work" / "a.png", colour=(1, 2, 3))
    second = write_png(tmp_path / "work" / "b.png", colour=(1, 2, 3))
    one = save_entry("picture", [first], launch=launch, now=NOW)
    two = save_entry("picture", [second], launch=launch, now=NOW)
    assert one.directory != two.directory
    journal = Journal(launch.journal_root)
    journal.load()
    assert len(journal.entries) == 2


def test_nothing_half_written_is_ever_visible_to_the_loader(tmp_path: Path) -> None:
    """The entry is assembled outside the four-level glob and renamed in."""
    launch, source = keep(tmp_path)
    save_entry("picture", [source], launch=launch, now=NOW)
    incoming = launch.journal_root / ".incoming"
    assert not incoming.exists()


# --- caption, voice and meta ----------------------------------------------


def test_the_caption_is_written_and_becomes_the_title(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], caption=" A teal  square ", launch=launch, now=NOW)
    assert (entry.directory / CAPTION_NAME).read_text(encoding="utf-8") == "A teal square\n"
    assert entry.title == "A teal square"


def test_a_long_caption_is_kept_but_is_not_the_title(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    long_caption = "I made a square and then I made another one and it was teal"
    entry = save_entry(
        "picture", [source], caption=long_caption, activity_name="Hello draw", launch=launch
    )
    assert entry.title == "Hello draw"
    assert (entry.directory / CAPTION_NAME).read_text(encoding="utf-8").strip() == long_caption


def test_no_caption_means_no_caption_file(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch, now=NOW)
    assert not (entry.directory / CAPTION_NAME).exists()


def test_a_title_never_carries_a_timestamp(tmp_path: Path) -> None:
    assert title_for("picture", "20260818", "Hello draw") == "Hello draw"
    assert title_for("picture", "A square", "Hello draw") == "A square"
    assert title_for("picture", None, "") == "Picture"


def test_the_voice_note_is_stored_where_the_shell_looks(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    voice = tmp_path / "work" / "note.ogg"
    voice.write_bytes(b"OggS-not-really")
    entry = save_entry("picture", [source], voice=voice, launch=launch, now=NOW)
    assert (entry.directory / NOTE_NAME).read_bytes() == b"OggS-not-really"


def test_a_missing_voice_note_does_not_lose_the_drawing(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], voice=tmp_path / "gone.ogg", launch=launch)
    assert entry.directory.is_dir()
    assert not (entry.directory / NOTE_NAME).exists()


def test_meta_goes_in_its_own_file_where_the_shell_cannot_drop_it(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry(
        "picture", [source], caption="A teal square", meta={"colour": "teal"}, launch=launch
    )
    data = json.loads((entry.directory / META_NAME).read_text(encoding="utf-8"))
    assert data["kind"] == "picture"
    assert data["meta"] == {"colour": "teal"}
    assert data["files"] == ["v001.png"]
    # And entry.json is untouched by it, so a star toggle cannot lose it.
    stored = json.loads((entry.directory / "entry.json").read_text(encoding="utf-8"))
    assert "meta" not in stored


def test_starring_an_sdk_entry_does_not_lose_its_meta(tmp_path: Path) -> None:
    """The reason meta.json exists, asserted end to end."""
    launch, source = keep(tmp_path)
    save_entry("picture", [source], meta={"colour": "teal"}, launch=launch)
    journal = Journal(launch.journal_root)
    journal.load()
    journal.toggle_star(journal.entries[0])
    data = json.loads((journal.entries[0].directory / META_NAME).read_text(encoding="utf-8"))
    assert data["meta"] == {"colour": "teal"}


def test_meta_that_cannot_be_json_is_refused_before_anything_is_copied(
    tmp_path: Path,
) -> None:
    launch, source = keep(tmp_path)
    with pytest.raises(JournalError, match="JSON"):
        save_entry("picture", [source], meta={"when": datetime.now()}, launch=launch)
    assert not (launch.journal_root / ".incoming").exists()
    assert not launch.journal_root.exists() or not list(launch.journal_root.glob("2*"))


# --- source_path and resume ----------------------------------------------


def test_source_path_is_empty_so_the_importer_never_matches_it(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch, now=NOW)
    assert entry.source_path == ""
    journal = Journal(launch.journal_root)
    journal.load()
    assert journal.entry_for_source(source) is None


def test_resume_has_a_real_file_to_open(tmp_path: Path) -> None:
    """The shell resumes from ``latest_path``, not from ``source_path``."""
    launch, source = keep(tmp_path)
    save_entry("picture", [source], launch=launch, now=NOW)
    journal = Journal(launch.journal_root)
    journal.load()
    latest = journal.entries[0].latest_path
    assert latest is not None and latest.is_file()


# --- thumbnails -----------------------------------------------------------


def test_a_thumbnail_is_asked_for_when_the_thing_is_a_picture(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    asked: list[tuple[Path, Path]] = []

    def thumbnailer(src: Path, dst: Path) -> bool:
        asked.append((src, dst))
        dst.write_bytes(b"thumb")
        return True

    entry = save_entry("picture", [source], launch=launch, thumbnailer=thumbnailer)
    assert len(asked) == 1
    assert asked[0][0].name == "v001.png"
    assert asked[0][1].name == "thumb.png"
    assert entry.thumbnail is not None


def test_a_thumbnail_is_not_asked_for_when_it_is_not_a_picture(tmp_path: Path) -> None:
    launch = launch_env(tmp_path)
    source = tmp_path / "work" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text("once upon a time", encoding="utf-8")
    asked: list[Path] = []

    def thumbnailer(source_path: Path, _destination: Path) -> bool:
        asked.append(source_path)
        return True

    entry = save_entry("writing", [source], launch=launch, thumbnailer=thumbnailer)
    assert asked == []
    assert entry.thumbnail is None


def test_a_thumbnailer_that_fails_does_not_lose_the_drawing(tmp_path: Path) -> None:
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch, thumbnailer=lambda _s, _d: False)
    assert entry.directory.is_dir()
    assert entry.thumbnail is None


def test_a_png_really_does_get_a_thumbnail(tmp_path: Path) -> None:
    """The default thumbnailer is the shell's, i.e. GdkPixbuf.

    The shell's own contract is "no thumbnail, fall back to the activity icon",
    so a host without the loaders is not a failure -- but the one it *does*
    produce has to be a real PNG.
    """
    launch, source = keep(tmp_path)
    entry = save_entry("picture", [source], launch=launch)
    if entry.thumbnail is not None:
        assert entry.thumbnail.name == "thumb.png"
        assert entry.thumbnail.read_bytes().startswith(b"\x89PNG")


# --- refusing ------------------------------------------------------------


def test_an_entry_without_an_activity_id_is_refused(tmp_path: Path) -> None:
    launch = LaunchEnv.from_env({"HOME": str(tmp_path / "home")})
    source = write_png(tmp_path / "work" / "square.png")
    with pytest.raises(JournalError, match="KIDNIX_ACTIVITY_ID"):
        save_entry("picture", [source], launch=launch)


def test_an_entry_with_nothing_in_it_is_refused(tmp_path: Path) -> None:
    launch = launch_env(tmp_path)
    with pytest.raises(JournalError, match="nothing to save"):
        save_entry("picture", [], launch=launch)
    with pytest.raises(JournalError, match="nothing to save"):
        save_entry("picture", [tmp_path / "gone.png"], launch=launch)


@pytest.mark.parametrize("kind", ["", "Picture", "a picture", "picture!", "-picture"])
def test_a_kind_that_is_not_a_slug_is_refused(tmp_path: Path, kind: str) -> None:
    launch, source = keep(tmp_path)
    with pytest.raises(JournalError, match="lowercase slug"):
        save_entry(kind, [source], launch=launch)


def test_an_explicit_journal_root_wins_over_the_environment(tmp_path: Path) -> None:
    """What ``--demo`` and every test need: a scratch journal."""
    launch, source = keep(tmp_path)
    elsewhere = tmp_path / "scratch"
    entry = save_entry("picture", [source], journal_root=elsewhere, launch=launch)
    assert elsewhere in entry.directory.parents
