"""Manifest loading (spec section 4): valid, invalid, and missing optionals."""

from __future__ import annotations

from pathlib import Path

import pytest

from kidnix_shell.activities import (
    ManifestError,
    load_activities,
    load_directory,
    load_manifest,
    parse_manifest,
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
