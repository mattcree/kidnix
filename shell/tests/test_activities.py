"""Manifest loading (spec section 4): valid, invalid, and missing optionals."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from kidnix_shell.activities import (
    Availability,
    ManifestError,
    load_activities,
    load_directory,
    load_manifest,
    parse_manifest,
    resolve_availability,
)

MINIMAL = """
id = "scribble"
name = "Scribble"
exec = ["scribble"]
"""

FULL = """
schema = 1
id = "tuxpaint"
name = "Tux Paint"
audio_label = "Tux Paint. Draw a picture."
icon = "tuxpaint"
icon_kind = "icon-name"
exec = ["tuxpaint"]
exec_resume = ["tuxpaint", "--open", "{file}"]
category = "make"
age_min = 3
age_max = 10
oars_rating = "none"
network_required = false
journal_watch = ["~/.tuxpaint/saved", "~/Pictures/TuxPaint"]
journal_glob = "*.png"
goal = "Making pictures."
wayland_native = true
content_required = false
notes = "hello"
source = "rpm"
package = "tuxpaint"
licence = "GPL-2.0-or-later"
"""


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_minimal_manifest_loads(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", MINIMAL))
    assert activity.id == "scribble"
    assert activity.exec_argv == ("scribble",)


def test_optional_fields_get_sensible_defaults(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", MINIMAL))
    assert activity.category == "play"
    assert activity.journal_watch == ()
    assert activity.journal_glob == "*"
    assert activity.network_required is False
    assert activity.age_min is None
    assert activity.goal == ""


def test_speak_text_falls_back_to_the_name(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", MINIMAL))
    assert activity.speak_text == "Scribble"


def test_audio_label_wins_over_the_name(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", FULL))
    assert activity.speak_text == "Tux Paint. Draw a picture."


def test_full_manifest_round_trips(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", FULL), home=Path("/home/kid"))
    assert activity.age_max == 10
    assert activity.journal_watch[0] == Path("/home/kid/.tuxpaint/saved")
    assert activity.journal_glob == "*.png"
    assert activity.supports_resume


def test_tilde_expands_against_the_given_home(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", FULL), home=tmp_path)
    assert activity.journal_watch[1] == tmp_path / "Pictures/TuxPaint"


def test_resume_argv_substitutes_the_file_token(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", FULL))
    argv = activity.resume_argv(Path("/tmp/x.png"))
    assert argv == ["tuxpaint", "--open", "/tmp/x.png"]


def test_resume_argv_appends_when_there_is_no_token() -> None:
    activity = parse_manifest(
        {"id": "a", "name": "A", "exec": ["a"], "exec_resume": ["a", "--open"]},
        Path("x.toml"),
    )
    assert activity.resume_argv(Path("/tmp/x.png")) == ["a", "--open", "/tmp/x.png"]


def test_resume_without_exec_resume_is_a_plain_launch(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", MINIMAL))
    assert not activity.supports_resume
    assert activity.resume_argv(Path("/tmp/x.png")) == ["scribble"]


@pytest.mark.parametrize(
    "text,fragment",
    [
        ('name = "A"\nexec = ["a"]\n', "id"),
        ('id = "a"\nexec = ["a"]\n', "name"),
        ('id = "a"\nname = "A"\n', "exec"),
        ('id = "a"\nname = "A"\nexec = []\n', "must not be empty"),
        ('id = "A"\nname = "A"\nexec = ["a"]\n', "lowercase"),
        ('id = "a"\nname = "A"\nexec = "a"\n', "list of strings"),
        ('id = "a"\nname = "A"\nexec = ["a"]\ncategory = "fun"\n', "category"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nicon_kind = "emoji"\n', "icon_kind"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nage_min = 8\nage_max = 4\n', "age_max"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nage_min = -1\n', "negative"),
        ('id = "a"\nname = "A"\nexec = ["a"]\njournal_watch = "x"\n', "journal_watch"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nnetwork_required = "yes"\n', "true or false"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nschema = 99\n', "newer than this shell"),
        ("this is not toml [[[", "not valid TOML"),
    ],
)
def test_invalid_manifests_are_rejected_with_a_reason(
    tmp_path: Path, text: str, fragment: str
) -> None:
    with pytest.raises(ManifestError) as caught:
        load_manifest(write(tmp_path, "bad.toml", text))
    assert fragment in caught.value.message


def test_unknown_fields_are_tolerated(tmp_path: Path) -> None:
    text = MINIMAL + '\nfuture_field = "whatever"\n'
    assert load_manifest(write(tmp_path, "a.toml", text)).id == "scribble"


def test_a_bad_file_does_not_stop_the_good_ones(tmp_path: Path) -> None:
    write(tmp_path, "good.toml", MINIMAL)
    write(tmp_path, "bad.toml", 'id = "x"\n')
    result = load_directory(tmp_path)
    assert [a.id for a in result.activities] == ["scribble"]
    assert len(result.errors) == 1
    assert not result.ok


def test_missing_directory_is_not_an_error(tmp_path: Path) -> None:
    result = load_directory(tmp_path / "nope")
    assert result.ok and result.activities == []


def test_a_later_directory_overrides_an_earlier_one(tmp_path: Path) -> None:
    system = tmp_path / "system"
    user = tmp_path / "user"
    system.mkdir()
    user.mkdir()
    write(system, "a.toml", MINIMAL)
    write(user, "a.toml", MINIMAL.replace('name = "Scribble"', 'name = "Dev Scribble"'))
    result = load_activities([system, user])
    assert [a.name for a in result.activities] == ["Dev Scribble"]


def test_the_shipped_manifests_all_validate() -> None:
    """The activities implementer's real files must load in this shell."""
    shipped = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"
    if not shipped.is_dir():
        pytest.skip("running outside the kidnix checkout")
    result = load_directory(shipped, home=Path("/var/home/kid"))
    assert result.ok, [str(e) for e in result.errors]
    assert len(result.activities) >= 5


# --- order (spec section 4: Home's grid, not the alphabet) ---------------


def test_order_sorts_home_and_missing_order_goes_to_the_back(tmp_path: Path) -> None:
    write(tmp_path, "zulu.toml", 'id = "z"\nname = "Z"\nexec = ["z"]\norder = 10\n')
    write(tmp_path, "alpha.toml", 'id = "a"\nname = "A"\nexec = ["a"]\norder = 20\n')
    write(tmp_path, "bravo.toml", 'id = "b"\nname = "B"\nexec = ["b"]\n')
    result = load_activities([tmp_path])
    assert [a.id for a in result.activities] == ["z", "a", "b"]


def test_activities_without_an_order_fall_back_to_the_filename(tmp_path: Path) -> None:
    for name in ("charlie", "alpha", "bravo"):
        write(tmp_path, f"{name}.toml", f'id = "{name}"\nname = "{name}"\nexec = ["x"]\n')
    result = load_activities([tmp_path])
    assert [a.id for a in result.activities] == ["alpha", "bravo", "charlie"]


def test_order_must_be_a_whole_number(tmp_path: Path) -> None:
    with pytest.raises(ManifestError) as caught:
        load_manifest(write(tmp_path, "a.toml", MINIMAL + '\norder = "first"\n'))
    assert "order" in caught.value.message


# --- availability (a tile that cannot work is worse than no tile) --------


def installed(*programs: str) -> Callable[[str], str | None]:
    return lambda program: f"/usr/bin/{program}" if program in programs else None


def test_an_activity_whose_program_is_missing_is_unavailable() -> None:
    activity = parse_manifest({"id": "a", "name": "A", "exec": ["nope"]}, Path("a.toml"))
    assert Availability(which=installed("yes")).check(activity) is False


def test_an_installed_program_is_available() -> None:
    activity = parse_manifest({"id": "a", "name": "A", "exec": ["yes"]}, Path("a.toml"))
    assert Availability(which=installed("yes")).check(activity) is True


def test_a_flatpak_exec_also_has_to_be_installed() -> None:
    """`flatpak` being on PATH says nothing about the app (e2e spike 3.1)."""
    activity = parse_manifest(
        {"id": "a", "name": "A", "exec": ["flatpak", "run", "org.example.App"]}, Path("a.toml")
    )
    assert activity.flatpak_ref == "org.example.App"
    check = Availability(which=installed("flatpak"), flatpak=lambda ref: False)
    assert check.check(activity) is False
    assert Availability(which=installed("flatpak"), flatpak=lambda ref: True).check(activity)


def test_flatpak_options_do_not_confuse_the_ref() -> None:
    activity = parse_manifest(
        {"id": "a", "name": "A", "exec": ["flatpak", "run", "--branch=stable", "org.example.App"]},
        Path("a.toml"),
    )
    assert activity.flatpak_ref == "org.example.App"


def test_a_plain_exec_has_no_flatpak_ref() -> None:
    activity = parse_manifest({"id": "a", "name": "A", "exec": ["yes"]}, Path("a.toml"))
    assert activity.flatpak_ref == ""


def test_each_program_is_probed_once_per_boot() -> None:
    seen: list[str] = []

    def which(program: str) -> str | None:
        seen.append(program)
        return "/usr/bin/x"

    check = Availability(which=which)
    activities = [
        parse_manifest({"id": f"a{i}", "name": "A", "exec": ["same"]}, Path("a.toml"))
        for i in range(5)
    ]
    for activity in activities:
        assert check.check(activity)
    assert seen == ["same"]


def test_resolve_availability_stamps_every_activity() -> None:
    here = parse_manifest({"id": "here", "name": "H", "exec": ["yes"]}, Path("h.toml"))
    gone = parse_manifest({"id": "gone", "name": "G", "exec": ["nope"]}, Path("g.toml"))
    resolved = resolve_availability([here, gone], Availability(which=installed("yes")))
    assert [a.available for a in resolved] == [True, False]


def test_an_unavailable_activity_is_off_home_unless_it_asks_to_be_seen() -> None:
    hidden = parse_manifest({"id": "a", "name": "A", "exec": ["nope"]}, Path("a.toml"))
    shown = parse_manifest(
        {"id": "b", "name": "B", "exec": ["nope"], "show_when_unavailable": True},
        Path("b.toml"),
    )
    check = Availability(which=installed("yes"))
    resolved = {a.id: a for a in resolve_availability([hidden, shown], check)}
    assert resolved["a"].on_home is False
    assert resolved["b"].on_home is True
    # Anything installed is on Home whatever the flag says.
    assert parse_manifest({"id": "c", "name": "C", "exec": ["x"]}, Path("c.toml")).on_home


def test_show_when_unavailable_defaults_to_false(tmp_path: Path) -> None:
    assert load_manifest(write(tmp_path, "a.toml", MINIMAL)).show_when_unavailable is False


# --- the shipped set, as a child meets it --------------------------------

#: What each tile is called, and what it says. Product names are not activities
#: (SYNTHESIS B4, 05 section 3): a five-year-old is choosing what to *do*.
SHIPPED_LABELS = {
    "tuxpaint": ("Draw", "Draw"),
    "ktuberling": ("Potato faces", "Make a potato face"),
    "turbowarp": ("Make a game", "Make a game"),
    "gcompris": ("Letters & numbers", "Letters and numbers"),
    "klettres": ("Letter sounds", "Letter sounds"),
    "tuxmath": ("Number game", "Number game"),
    "blinken": ("Copy the lights", "Copy the lights"),
    "kolf": ("Mini golf", "Mini golf"),
    "supertux": ("Jump and run", "Jump and run"),
    "kiwix": ("Library", "Library"),
}


def shipped_activities() -> list[object]:
    directory = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"
    if not directory.is_dir():
        pytest.skip("running outside the kidnix checkout")
    result = load_activities([directory], home=Path("/var/home/kid"))
    assert result.ok, [str(e) for e in result.errors]
    return result.activities  # type: ignore[return-value]


def test_the_shipped_tiles_are_named_for_what_the_child_does() -> None:
    for activity in shipped_activities():
        name, audio = SHIPPED_LABELS[activity.id]  # type: ignore[attr-defined]
        assert activity.name == name  # type: ignore[attr-defined]
        assert activity.speak_text == audio  # type: ignore[attr-defined]


def test_no_shipped_tile_says_a_product_name() -> None:
    """The label is a verb phrase, not a brand. "Library" is the one noun."""
    banned = ("tux", "gcompris", "kde", "klettres", "kolf", "blinken", "turbowarp", "scratch")
    for activity in shipped_activities():
        spoken = f"{activity.name} {activity.speak_text}".lower()  # type: ignore[attr-defined]
        for word in banned:
            assert word not in spoken, f"{activity.id} still says {word!r}"  # type: ignore[attr-defined]


def test_every_shipped_activity_has_an_order_and_a_goal() -> None:
    for activity in shipped_activities():
        assert activity.order is not None, activity.id  # type: ignore[attr-defined]
        assert activity.goal, activity.id  # type: ignore[attr-defined]


def test_draw_is_the_first_tile_on_home() -> None:
    """The one a four-year-old gets furthest with unaided, first."""
    assert shipped_activities()[0].id == "tuxpaint"  # type: ignore[attr-defined]


def test_the_unshipped_flatpak_does_not_get_an_outline_tile() -> None:
    """TurboWarp is not installed until an online boot has happened."""
    turbowarp = next(a for a in shipped_activities() if a.id == "turbowarp")  # type: ignore[attr-defined]
    assert turbowarp.show_when_unavailable is False  # type: ignore[attr-defined]
    assert turbowarp.flatpak_ref == "org.turbowarp.TurboWarp"  # type: ignore[attr-defined]
