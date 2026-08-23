"""Shelves: the data half (spec 7d #12, ``docs/spikes/panel-wave-c.md`` §2).

The contract wave C wrote for this wave is that there is **no new parser and no
new schema**: a shelf's children are ordinary activity manifests in a
subdirectory, loaded by the same ``load_directory``. So most of what is tested
here is that nothing special happens -- and the two things that must: the
children never reach Home, and ``children_dir`` can never be a path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kidnix_shell.activities import (
    KIND_SHELF,
    Activity,
    Availability,
    ManifestError,
    load_activities,
    load_directory,
    load_shelf_children,
    parse_manifest,
    resolve_shelves,
    shelf_groups,
)

SHELF = """
schema = 1
id = "gcompris"
name = "Letters & numbers"
audio_label = "Letters, counting and shapes. Choose a game."
kind = "shelf"
children_dir = "gcompris"
order = 40
icon = "kidnix-act-gcompris"
exec = ["gcompris-qt", "--launch", "erase", "--hide-home-button"]
category = "learn"
age_band = "4-8"
"""


def child(activity_id: str, order: int, group: str, group_name: str, band: str = "4-7") -> str:
    return f"""
schema = 1
id = "gcompris.{activity_id}"
name = "{activity_id.title()}"
audio_label = "{activity_id}. Do the thing."
order = {order}
icon = "kidnix-act-gcompris"
exec = ["gcompris-qt", "--launch", "{activity_id}", "--hide-home-button"]
category = "learn"
age_band = "{band}"
shelf_group = "{group}"
shelf_group_name = "{group_name}"
shelf_group_audio_label = "{group_name}"
gcompris_difficulty = 2
gcompris_intro_voice_en_GB = true
"""


@pytest.fixture
def shelf_dir(tmp_path: Path) -> Path:
    """The image's shape: a shelf manifest, and its children one level down."""
    (tmp_path / "gcompris.toml").write_text(SHELF, encoding="utf-8")
    children = tmp_path / "gcompris"
    children.mkdir()
    rows = [
        ("erase", 10, "point-and-click", "Point and click", "4-6"),
        ("clickgame", 20, "point-and-click", "Point and click", "4-6"),
        ("gletters", 30, "letters", "Letters", "5-8"),
        ("click_on_letter", 40, "letters", "Letters", "4-7"),
        ("smallnumbers", 50, "counting", "Counting", "4-7"),
    ]
    for activity_id, order, group, name, band in rows:
        (children / f"gcompris.{activity_id}.toml").write_text(
            child(activity_id, order, group, name, band), encoding="utf-8"
        )
    return tmp_path


# --- parsing -------------------------------------------------------------


def test_a_shelf_says_it_is_one_and_where_its_children_are(shelf_dir: Path) -> None:
    result = load_directory(shelf_dir)
    assert result.ok
    shelf = result.activities[0]
    assert shelf.kind == KIND_SHELF
    assert shelf.is_shelf
    # Relative to the manifest, so a dev override resolves beside itself.
    assert shelf.children_path == shelf_dir / "gcompris"


def test_an_ordinary_manifest_is_not_a_shelf() -> None:
    activity = parse_manifest(
        {"id": "tuxpaint", "name": "Draw", "exec": ["tuxpaint"]}, Path("/nowhere/x.toml")
    )
    assert not activity.is_shelf
    assert activity.children_path is None
    assert activity.children_dir == ""


def test_a_shelf_must_say_where_its_children_are() -> None:
    with pytest.raises(ManifestError, match="which directory"):
        parse_manifest(
            {"id": "x", "name": "X", "exec": ["x"], "kind": "shelf"}, Path("/nowhere/x.toml")
        )


@pytest.mark.parametrize("escape", ["../..", "/etc", "a/b", "..", "./x"])
def test_children_dir_can_never_be_a_path(escape: str) -> None:
    """A manifest is data the shell reads at start-up, not a path it follows."""
    with pytest.raises(ManifestError, match="plain directory name"):
        parse_manifest(
            {"id": "x", "name": "X", "exec": ["x"], "kind": "shelf", "children_dir": escape},
            Path("/nowhere/x.toml"),
        )


def test_an_unknown_kind_is_rejected() -> None:
    with pytest.raises(ManifestError, match="kind"):
        parse_manifest(
            {"id": "x", "name": "X", "exec": ["x"], "kind": "folder"}, Path("/nowhere/x.toml")
        )


# --- loading -------------------------------------------------------------


def test_the_children_never_become_tiles_on_home(shelf_dir: Path) -> None:
    """**The guarantee the subdirectory buys** (panel-wave-c section 2 #4).

    ``load_directory`` globs one directory and does not recurse, so eighteen
    curated GCompris activities cannot appear as eighteen extra tiles.
    """
    home = load_activities([shelf_dir])
    assert [a.id for a in home.activities] == ["gcompris"]


def test_a_shelfs_children_load_through_the_same_parser_in_order(shelf_dir: Path) -> None:
    shelf = load_directory(shelf_dir).activities[0]
    children = load_shelf_children(shelf)
    assert [c.id for c in children] == [
        "gcompris.erase",
        "gcompris.clickgame",
        "gcompris.gletters",
        "gcompris.click_on_letter",
        "gcompris.smallnumbers",
    ]
    assert all(isinstance(c, Activity) for c in children)
    assert children[0].exec_argv[:2] == ("gcompris-qt", "--launch")


def test_a_shelf_with_no_directory_loads_as_an_empty_shelf(tmp_path: Path) -> None:
    """Home then hides the tile, exactly as it hides an uninstalled activity."""
    (tmp_path / "gcompris.toml").write_text(SHELF, encoding="utf-8")
    shelf = load_directory(tmp_path).activities[0]
    assert load_shelf_children(shelf) == []


def test_a_broken_child_is_skipped_not_fatal(shelf_dir: Path) -> None:
    (shelf_dir / "gcompris" / "broken.toml").write_text("id = 'x'\n", encoding="utf-8")
    shelf = load_directory(shelf_dir).activities[0]
    assert len(load_shelf_children(shelf)) == 5


def test_resolve_shelves_stamps_availability_on_the_children(shelf_dir: Path) -> None:
    activities = load_directory(shelf_dir).activities
    nothing_installed = Availability(which=lambda _p: None)
    shelves = resolve_shelves(activities, availability=nothing_installed)
    assert set(shelves) == {"gcompris"}
    assert all(not c.available for c in shelves["gcompris"])
    # ...and so none of them would draw a tile, which is what hides the shelf.
    assert not any(c.on_home for c in shelves["gcompris"])


# --- groups --------------------------------------------------------------


def test_groups_come_out_in_the_order_the_children_arrive(shelf_dir: Path) -> None:
    """Sorting by ``order`` alone already produces correctly grouped output --
    ``curated.toml`` numbers the activities group by group, so first appearance
    *is* the curated group order and there is nothing else to look up."""
    shelf = load_directory(shelf_dir).activities[0]
    groups = shelf_groups(load_shelf_children(shelf))
    assert [g.id for g in groups] == ["point-and-click", "letters", "counting"]
    assert [g.name for g in groups] == ["Point and click", "Letters", "Counting"]
    assert [len(g.activities) for g in groups] == [2, 2, 1]
    assert groups[0].speak_text == "Point and click"


def test_children_with_no_group_fall_into_one_named_after_the_shelf() -> None:
    """A hand-written shelf with no groups in it is still one page of tiles."""
    activities = [
        parse_manifest({"id": "a", "name": "A", "exec": ["a"]}, Path("/nowhere/a.toml")),
        parse_manifest({"id": "b", "name": "B", "exec": ["b"]}, Path("/nowhere/b.toml")),
    ]
    groups = shelf_groups(activities, default_name="Games")
    assert len(groups) == 1
    assert groups[0].name == "Games"
    assert len(groups[0].activities) == 2


def test_an_empty_shelf_has_no_groups() -> None:
    assert shelf_groups([], default_name="Games") == []


# --- the age band bites on the children, not on the shelf ----------------


def test_the_band_filters_the_children(shelf_dir: Path) -> None:
    """panel-wave-c section 2: "age filtering applies to the children".

    A four-year-old loses the 5-8 ones; a five-year-old sees everything. The
    shelf itself spans its children's bands and is not filtered.
    """
    from kidnix_shell.activities import in_age_band, parse_age_band

    children = load_shelf_children(load_directory(shelf_dir).activities[0])
    four = [c.id for c in children if in_age_band(c, parse_age_band("4"))]
    four_five = [c.id for c in children if in_age_band(c, parse_age_band("4-5"))]
    assert "gcompris.gletters" not in four
    assert "gcompris.gletters" in four_five
    assert len(four) == 4
    assert len(four_five) == 5


# --- the shipped shelf ---------------------------------------------------

SYSTEM = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"


def test_the_shipped_gcompris_tile_is_a_shelf() -> None:
    """The image's own manifest, parsed by the shell that has to render it.

    Its children are generated at build time (``55-gcompris.sh``) and so are
    not in the repository; what is here is the half this wave has to agree
    with, and the half that used to open a 198-activity menu.
    """
    result = load_directory(SYSTEM)
    assert result.ok, [str(e) for e in result.errors]
    shelf = next(a for a in result.activities if a.id == "gcompris")
    assert shelf.is_shelf
    assert shelf.children_dir == "gcompris"
    assert shelf.children_path == SYSTEM / "gcompris"
    # The fallback exec is never run once shelves render, and it must never be
    # the bare `gcompris-qt`: an unrecognised --launch id silently opens the
    # full menu, which is the blocker this shelf closes.
    assert shelf.exec_argv[:2] == ("gcompris-qt", "--launch")


def test_no_shipped_manifest_declares_an_undo_key_we_cannot_send() -> None:
    """``undo_key`` is read and never sent (see ``ritual.undo_line``).

    Leaving it unset everywhere is deliberate: the shell has no mechanism for
    injecting a keystroke into another Wayland client that a child's session
    may safely have, so a manifest that named one would make the band say
    something the child could not act on without a keyboard.
    """
    for activity in load_directory(SYSTEM).activities:
        assert activity.undo_key == "", activity.id
