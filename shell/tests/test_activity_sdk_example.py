"""hello_draw: the example, run headless, saving a real Journal entry.

An example nobody executes is documentation with a bug in it. This is the
execution.
"""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path

import pytest

from kidnix_activity.env import ACTIVITY_ID_VAR, PROFILE_ID_VAR, LaunchEnv
from kidnix_activity.examples.hello_draw import ACTIVITY_ID, TITLE
from kidnix_activity.examples.hello_draw.logic import (
    LOST_LINE,
    PROMPT,
    HelloDraw,
    caption_for,
    make_and_keep,
)
from kidnix_activity.examples.hello_draw.picture import COLOURS, solid_png, write_square
from kidnix_activity.journal import META_NAME, JournalError, save_entry
from kidnix_shell.journal import Journal


@pytest.fixture
def launch(tmp_path: Path) -> LaunchEnv:
    home = tmp_path / "home"
    return LaunchEnv.from_env(
        {
            "HOME": str(home),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            ACTIVITY_ID_VAR: ACTIVITY_ID,
            PROFILE_ID_VAR: "robin",
        }
    )


def saver(launch: LaunchEnv):  # type: ignore[no-untyped-def]
    """``app.save_entry``, without the application."""
    return partial(save_entry, activity_name=TITLE, launch=launch)


# --- the picture -----------------------------------------------------------


def test_the_square_really_is_a_png() -> None:
    data = solid_png((0x0F, 0x8A, 0x8A), size=8)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"IHDR" in data and b"IDAT" in data and data.endswith(b"IEND\xae\x42\x60\x82")


def test_gdkpixbuf_can_read_what_we_wrote(tmp_path: Path) -> None:
    """The one property the hand-rolled encoder has to have."""
    gi = pytest.importorskip("gi")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf

    path = tmp_path / "square.png"
    path.write_bytes(solid_png((0xF0, 0x62, 0x92), size=32))
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
    assert (pixbuf.get_width(), pixbuf.get_height()) == (32, 32)


def test_the_colours_cycle_and_are_named(tmp_path: Path) -> None:
    names = [write_square(tmp_path / f"{i}.png", i, size=4) for i in range(len(COLOURS) + 1)]
    assert names[: len(COLOURS)] == [name for name, _ in COLOURS]
    assert names[-1] == names[0]


def test_two_colours_are_two_different_files(tmp_path: Path) -> None:
    write_square(tmp_path / "a.png", 0, size=4)
    write_square(tmp_path / "b.png", 1, size=4)
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()


# --- pressing the button ---------------------------------------------------


def test_one_press_makes_one_entry_a_child_can_find(launch: LaunchEnv) -> None:
    state = HelloDraw()
    entry, caption = make_and_keep(state, saver(launch))
    assert caption == caption_for("teal")

    journal = Journal(launch.journal_root)
    journal.load()
    assert [e.id for e in journal.entries] == [entry.id]
    assert journal.entries[0].title == "A teal square"
    assert journal.entries[0].activity_id == ACTIVITY_ID
    latest = journal.entries[0].latest_path
    assert latest is not None and latest.read_bytes().startswith(b"\x89PNG")


def test_three_presses_make_three_entries(launch: LaunchEnv) -> None:
    state = HelloDraw()
    save = saver(launch)
    captions = [make_and_keep(state, save)[1] for _ in range(3)]
    assert captions == ["A teal square", "A pink square", "A yellow square"]
    journal = Journal(launch.journal_root)
    journal.load()
    assert len(journal.entries) == 3


def test_the_colour_comes_back_in_the_entrys_own_meta(launch: LaunchEnv) -> None:
    entry, _ = make_and_keep(HelloDraw(), saver(launch))
    data = json.loads((entry.directory / META_NAME).read_text(encoding="utf-8"))
    assert data["meta"] == {"colour": "teal"}
    assert data["kind"] == "picture"


def test_the_working_file_is_not_left_in_the_childs_home(launch: LaunchEnv, tmp_path: Path) -> None:
    state = HelloDraw()
    make_and_keep(state, saver(launch))
    assert state.last is not None
    assert (tmp_path / "home") not in state.last.parents


def test_a_journal_that_cannot_be_written_is_said_out_loud_not_swallowed(
    tmp_path: Path,
) -> None:
    """The activity's error path exists and the sentence is a child's."""
    nameless = LaunchEnv.from_env({"HOME": str(tmp_path / "home")})
    with pytest.raises(JournalError):
        make_and_keep(HelloDraw(), partial(save_entry, launch=nameless))
    assert "grown-up" in LOST_LINE
    assert not any(char.isdigit() for char in LOST_LINE)


# --- the words -------------------------------------------------------------


def test_no_line_the_child_hears_contains_a_digit() -> None:
    for line in (PROMPT, LOST_LINE, caption_for("teal")):
        assert not any(char.isdigit() for char in line)


def test_the_example_never_praises_or_scores() -> None:
    """SUITE section 5: no reward economy, and no example that teaches one."""
    from kidnix_activity.examples.hello_draw import logic

    text = Path(logic.__file__).read_text(encoding="utf-8").lower()
    for banned in ("well done", "score", "star", "streak", "level up", "points"):
        assert banned not in text
