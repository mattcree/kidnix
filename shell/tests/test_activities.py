"""Manifest loading (spec section 4): valid, invalid, and missing optionals."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from kidnix_shell.activities import (
    DEFAULT_QUIT_GRACE,
    MAX_QUIT_GRACE,
    QUIT_CONFIRM,
    QUIT_SIGNAL,
    Activity,
    Availability,
    ManifestError,
    in_age_band,
    load_activities,
    load_directory,
    load_manifest,
    parse_age_band,
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
content_required = []
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
        ('id = "a"\nname = "A"\nexec = ["a"]\nquit = "kill"\n', "quit"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nquit = true\n', "must be a string"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nquit_grace = 0\n', "more than zero"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nquit_grace = -5\n', "more than zero"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nquit_grace = 600\n', "not be more than"),
        ('id = "a"\nname = "A"\nexec = ["a"]\nquit_grace = "30s"\n', "number of seconds"),
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
    "gcompris": ("Letters & numbers", "Letters, counting and shapes. Choose a game."),
    "klettres": ("Letter names", "Listen to the letter, then press it on the keyboard"),
    "tuxmath": ("Number game", "Number game"),
    "blinken": ("Copy the lights", "Copy the lights"),
    "kolf": ("Mini golf", "Mini golf"),
    "supertux": ("Jump and run", "Jump and run"),
    "kiwix": ("Library", "Library"),
}


def shipped_activities() -> list[Activity]:
    directory = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"
    if not directory.is_dir():
        pytest.skip("running outside the kidnix checkout")
    result = load_activities([directory], home=Path("/var/home/kid"))
    assert result.ok, [str(e) for e in result.errors]
    return result.activities


def test_the_shipped_tiles_are_named_for_what_the_child_does() -> None:
    for activity in shipped_activities():
        name, audio = SHIPPED_LABELS[activity.id]
        assert activity.name == name
        assert activity.speak_text == audio


def test_no_shipped_tile_says_a_product_name() -> None:
    """The label is a verb phrase, not a brand. "Library" is the one noun."""
    banned = ("tux", "gcompris", "kde", "klettres", "kolf", "blinken", "turbowarp", "scratch")
    for activity in shipped_activities():
        spoken = f"{activity.name} {activity.speak_text}".lower()
        for word in banned:
            assert word not in spoken, f"{activity.id} still says {word!r}"


def test_every_shipped_activity_has_an_order_and_a_goal() -> None:
    for activity in shipped_activities():
        assert activity.order is not None, activity.id
        assert activity.goal, activity.id


def test_draw_is_the_first_tile_on_home() -> None:
    """The one a four-year-old gets furthest with unaided, first."""
    assert shipped_activities()[0].id == "tuxpaint"


def test_the_unshipped_flatpak_does_not_get_an_outline_tile() -> None:
    """TurboWarp is not installed until an online boot has happened."""
    turbowarp = next(a for a in shipped_activities() if a.id == "turbowarp")
    assert turbowarp.show_when_unavailable is False
    assert turbowarp.flatpak_ref == "org.turbowarp.TurboWarp"


# --- content_required (05 Lib-4, CCI audit 3.2) ---------------------------
#
# kiwix-serve is installed on every image, so `which` says the Library works
# and the child opens an empty library. The predicate below is the fix.

CONTENT = """
id = "library"
name = "Library"
exec = ["kiwix-serve"]
content_required = ["/var/lib/kidnix/library/*.zim"]
"""


def _check(installed: bool = True, present: tuple[str, ...] = ()) -> Availability:
    return Availability(
        which=lambda p: "/usr/bin/x" if installed else None,
        flatpak=lambda ref: installed,
        globber=lambda pattern: pattern in present,
    )


def test_content_required_parses_as_a_list_of_globs(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", CONTENT))
    assert activity.content_required == ("/var/lib/kidnix/library/*.zim",)


def test_content_required_defaults_to_nothing_to_check(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", MINIMAL))
    assert activity.content_required == ()
    assert activity.has_content is True


def test_a_bare_true_content_required_is_now_a_manifest_error(tmp_path: Path) -> None:
    """v0.1.1's spelling said nothing checkable, so it silently did nothing."""
    with pytest.raises(ManifestError, match="list of path globs"):
        load_manifest(
            write(tmp_path, "a.toml", "id='a'\nname='A'\nexec=['x']\ncontent_required=true\n")
        )


def test_content_globs_expand_the_kid_home(tmp_path: Path) -> None:
    activity = load_manifest(
        write(
            tmp_path, "a.toml", "id='a'\nname='A'\nexec=['x']\ncontent_required=['~/books/*.zim']\n"
        ),
        home=Path("/var/home/kid"),
    )
    assert activity.content_required == ("/var/home/kid/books/*.zim",)


def test_an_installed_activity_with_no_content_is_not_on_home(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", CONTENT))
    resolved = resolve_availability([activity], _check(present=()))[0]
    assert resolved.available is True, "kiwix-serve is installed"
    assert resolved.has_content is False
    assert resolved.usable is False
    assert resolved.on_home is False


def test_content_that_is_there_puts_the_tile_back(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", CONTENT))
    resolved = resolve_availability([activity], _check(present=("/var/lib/kidnix/library/*.zim",)))[
        0
    ]
    assert (resolved.has_content, resolved.usable, resolved.on_home) == (True, True, True)


def test_every_content_glob_has_to_match_not_just_one(tmp_path: Path) -> None:
    text = "id='a'\nname='A'\nexec=['x']\ncontent_required=['/one/*.zim', '/two/*.zim']\n"
    activity = load_manifest(write(tmp_path, "a.toml", text))
    resolved = resolve_availability([activity], _check(present=("/one/*.zim",)))[0]
    assert resolved.has_content is False


def test_a_missing_program_short_circuits_the_content_check(tmp_path: Path) -> None:
    """Not installed is already the answer; do not stat the disk to confirm it."""
    activity = load_manifest(write(tmp_path, "a.toml", CONTENT))
    resolved = resolve_availability([activity], _check(installed=False))[0]
    assert (resolved.available, resolved.on_home) == (False, False)


def test_show_when_unavailable_still_outlines_a_contentless_activity(tmp_path: Path) -> None:
    text = CONTENT + "show_when_unavailable = true\n"
    activity = load_manifest(write(tmp_path, "a.toml", text))
    resolved = resolve_availability([activity], _check(present=()))[0]
    assert resolved.usable is False
    assert resolved.on_home is True  # drawn outline-only, and it says why


def test_the_shipped_library_names_a_real_directory() -> None:
    """The tile the audit found opening nothing now declares what it needs."""
    kiwix = next(a for a in shipped_activities() if a.id == "kiwix")
    assert kiwix.content_required == ("/var/lib/kidnix/library/*.zim",)
    assert resolve_availability([kiwix], _check(present=()))[0].on_home is False


# --- age bands (01 #35, SYNTHESIS B8) -------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4-5", (4, 5)),
        ("6-8", (6, 8)),
        ("5", (5, 5)),
        (" 4 - 5 ", (4, 5)),
        ("5-4", (4, 5)),
        ("", None),
        ("toddler", None),
        ("4-", None),
        ("4 to 5", None),
    ],
)
def test_parsing_an_age_band(text: str, expected: tuple[int, int] | None) -> None:
    assert parse_age_band(text) == expected


def _banded(age_min: int | None = None, age_max: int | None = None) -> Activity:
    return parse_manifest(
        {
            "id": "a",
            "name": "A",
            "exec": ["x"],
            **({"age_min": age_min} if age_min is not None else {}),
            **({"age_max": age_max} if age_max is not None else {}),
        },
        Path("a.toml"),
    )


def test_an_activity_above_the_band_is_out() -> None:
    """tuxmath: 6-10 against a 4-5 profile. Its own manifest says so."""
    assert in_age_band(_banded(6, 10), (4, 5)) is False


def test_an_activity_below_the_band_is_out() -> None:
    assert in_age_band(_banded(2, 3), (6, 8)) is False


def test_an_overlapping_activity_is_in() -> None:
    """The Library is banded 5-12 and is right for a five-year-old."""
    assert in_age_band(_banded(5, 12), (4, 5)) is True
    assert in_age_band(_banded(3, 10), (4, 5)) is True


def test_an_unbanded_activity_is_in_for_everybody() -> None:
    assert in_age_band(_banded(), (4, 5)) is True
    assert in_age_band(_banded(), (6, 8)) is True


def test_a_half_open_band_only_closes_the_end_it_states() -> None:
    assert in_age_band(_banded(age_min=6), (4, 5)) is False
    assert in_age_band(_banded(age_max=3), (4, 5)) is False
    assert in_age_band(_banded(age_min=4), (4, 5)) is True


def test_a_profile_with_no_band_filters_nothing() -> None:
    """We do not guess a child's age from silence."""
    assert in_age_band(_banded(6, 10), None) is True


def test_the_age_band_shorthand_sets_the_bounds(tmp_path: Path) -> None:
    activity = load_manifest(
        write(tmp_path, "a.toml", "id='a'\nname='A'\nexec=['x']\nage_band='6-8'\n")
    )
    assert (activity.age_min, activity.age_max) == (6, 8)


def test_explicit_bounds_win_over_the_shorthand(tmp_path: Path) -> None:
    activity = load_manifest(
        write(tmp_path, "a.toml", "id='a'\nname='A'\nexec=['x']\nage_band='6-8'\nage_min=4\n")
    )
    assert (activity.age_min, activity.age_max) == (4, 8)


def test_a_nonsense_age_band_is_a_manifest_error(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="age_band"):
        load_manifest(write(tmp_path, "a.toml", "id='a'\nname='A'\nexec=['x']\nage_band='big'\n"))


def test_the_default_profile_band_hides_the_six_plus_activities() -> None:
    """The shipped set against the shipped 4-5 profile.

    Each manifest says so in its own ``goal``: tuxmath is typed arithmetic,
    TurboWarp is "realistically a six-plus activity", and SuperTux was re-banded
    to 7+ by the panel's ruling on the 4-6 band (spec 7d #8). Until v0.1.3 the
    shell showed the first two to a four-year-old.
    """
    out = sorted(a.id for a in shipped_activities() if not in_age_band(a, (4, 5)))
    assert out == ["supertux", "turbowarp", "tuxmath"]


def test_a_six_to_eight_year_old_gets_the_number_game_back() -> None:
    band = (6, 8)
    out = [a.id for a in shipped_activities() if not in_age_band(a, band)]
    assert out == []


# --- the quit contract (spec 7c) ------------------------------------------
#
# The shell has to know, before it asks an activity to finish, whether SIGTERM
# ends the program or makes the program ask the *child* a question. Getting
# this wrong is not a cosmetic bug: it is a deleted drawing (§19.3).


def test_quit_defaults_to_signal_and_five_seconds(tmp_path: Path) -> None:
    activity = load_manifest(write(tmp_path, "a.toml", MINIMAL))
    assert activity.quit == QUIT_SIGNAL
    assert activity.quit_grace == DEFAULT_QUIT_GRACE[QUIT_SIGNAL] == 5.0
    assert activity.asks_before_quitting is False


def test_confirm_gets_the_longer_default_grace(tmp_path: Path) -> None:
    """The thing being waited for is a five-year-old with a mouse."""
    text = MINIMAL + '\nquit = "confirm"\n'
    activity = load_manifest(write(tmp_path, "a.toml", text))
    assert activity.quit == QUIT_CONFIRM
    assert activity.quit_grace == DEFAULT_QUIT_GRACE[QUIT_CONFIRM] == 30.0
    assert activity.asks_before_quitting is True


def test_an_explicit_grace_wins_over_the_default(tmp_path: Path) -> None:
    text = MINIMAL + '\nquit = "confirm"\nquit_grace = 12\n'
    assert load_manifest(write(tmp_path, "a.toml", text)).quit_grace == 12.0


def test_a_fractional_grace_is_allowed(tmp_path: Path) -> None:
    text = MINIMAL + "\nquit_grace = 2.5\n"
    assert load_manifest(write(tmp_path, "a.toml", text)).quit_grace == 2.5


def test_the_grace_is_bounded_by_the_put_away_window(tmp_path: Path) -> None:
    """Put away is two minutes wide; a grace longer than MAX_QUIT_GRACE would
    mean the shell never got to ask a second time before the hard stop."""
    assert MAX_QUIT_GRACE <= 120
    text = MINIMAL + f"\nquit_grace = {MAX_QUIT_GRACE}\n"
    assert load_manifest(write(tmp_path, "a.toml", text)).quit_grace == MAX_QUIT_GRACE


def test_draw_is_the_one_shipped_activity_that_asks_the_child() -> None:
    """Measured, not assumed (§19.2): Tux Paint answers SIGTERM with a tick and
    a cross and autosaves only when the tick is pressed."""
    asking = {a.id: a for a in shipped_activities() if a.asks_before_quitting}
    assert list(asking) == ["tuxpaint"]
    assert asking["tuxpaint"].quit_grace == 30.0


def test_every_other_shipped_activity_goes_on_the_signal() -> None:
    for activity in shipped_activities():
        if activity.id == "tuxpaint":
            continue
        assert activity.quit == QUIT_SIGNAL, activity.id
        assert activity.quit_grace == 5.0, activity.id
