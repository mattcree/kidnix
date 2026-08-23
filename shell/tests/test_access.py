"""Captions, calm mode, sound level and the focus ring -- all without a display.

The accessibility review of 2026-08-23 filed three blockers, and the thing they
had in common was that none of the machinery existed to test. This module is
the half that can be proved by arithmetic and by reading the package's own
source: what ``[access]`` means, what calm mode changes, what order the focus
ring goes in, and -- the important one -- that **there is no way to speak
without captioning**.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from kidnix_shell.access import (
    CALM_EARCONS,
    CALM_SPEECH_RATE,
    CAPTION_LINES,
    CAPTION_MIN_PT,
    CAPTION_SECONDS,
    SPEECH_RATE,
    SWITCH_PRESSES,
    SWITCH_WINDOW_SECONDS,
    AccessConfig,
    FocusRing,
    SwitchHold,
    parse_access,
    reachable,
)
from kidnix_shell.labels import text_width_px
from kidnix_shell.metrics import Metrics
from kidnix_shell.sound import NAMES, Earcons, NullPlayer
from kidnix_shell.speech import FakeBackend, FakeScheduler, SpeechManager

PACKAGE = Path(__file__).resolve().parents[1] / "kidnix_shell"


# --- the defaults, which are the ones most children will get ---------------


def test_captions_are_on_by_default() -> None:
    """B2's answer, and it has to be the default to be an answer at all.

    A caption costs a hearing child nothing and is the only thing standing
    between a deaf child and a lost drawing at put-away.
    """
    assert AccessConfig().captions is True
    assert parse_access(None).captions is True
    assert parse_access({}).captions is True


def test_calm_is_off_by_default_and_full_volume_is_the_default() -> None:
    config = AccessConfig()
    assert config.calm is False
    assert config.mute is False
    assert config.effective_volume == 1.0


def test_the_access_table_is_read_out_of_the_parent_config() -> None:
    config = parse_access({"captions": False, "calm": True, "sound_volume": 0.4, "mute": False})
    assert config == AccessConfig(captions=False, calm=True, sound_volume=0.4, mute=False)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"sound_volume": 2.0}, 1.0),
        ({"sound_volume": -1}, 0.0),
        ({"sound_volume": "loud"}, 1.0),
        ({"sound_volume": True}, 1.0),
    ],
)
def test_a_hand_edited_volume_is_clamped_rather_than_believed(
    raw: dict[str, object], expected: float
) -> None:
    assert parse_access(raw).sound_volume == expected


def test_a_malformed_access_table_falls_back_to_the_defaults() -> None:
    """Never leave a child with captions off because somebody mistyped TOML."""
    assert parse_access("captions").captions is True
    assert parse_access({"calm": "yes"}).calm is False


# --- calm mode -------------------------------------------------------------


def test_calm_keeps_only_the_sound_that_reports_an_outcome() -> None:
    """Everything else in the soundscape punctuates an action the child took.

    "Something was kept" is the one a child would miss, so it is the one calm
    keeps. `tap` in particular fires on *every* child-facing press, which is
    the transient forum #39 named.
    """
    calm = AccessConfig(calm=True)
    for name in NAMES:
        assert calm.earcon_allowed(name) is (name in CALM_EARCONS)
    assert {"keep"} == CALM_EARCONS
    ordinary = AccessConfig()
    assert all(ordinary.earcon_allowed(name) for name in NAMES)


def test_mute_silences_every_earcon_including_the_one_calm_keeps() -> None:
    for config in (AccessConfig(mute=True), AccessConfig(sound_volume=0.0)):
        assert not any(config.earcon_allowed(name) for name in NAMES)


def test_calm_slows_the_voice_a_step_and_not_a_stride() -> None:
    assert AccessConfig().speech_rate == SPEECH_RATE
    assert AccessConfig(calm=True).speech_rate == CALM_SPEECH_RATE
    assert CALM_SPEECH_RATE < SPEECH_RATE
    # A voice slow enough to sound wrong is a voice a child stops listening to.
    assert CALM_SPEECH_RATE > -60


def test_reduced_motion_is_calm_or_the_desktop_already_saying_so() -> None:
    """WCAG 2.2 SC 2.3.3, and ``gtk-enable-animations`` which the image sets.

    A parent who turned motion off system-wide should not have to find a
    second switch -- and the shell read neither until 2026-08-23.
    """
    assert AccessConfig().reduced_motion(animations_enabled=True) is False
    assert AccessConfig().reduced_motion(animations_enabled=False) is True
    assert AccessConfig(calm=True).reduced_motion(animations_enabled=True) is True


def test_reduced_motion_makes_a_transition_a_cut() -> None:
    assert AccessConfig().transition_ms(True) > 0
    assert AccessConfig(calm=True).transition_ms(True) == 0
    assert AccessConfig().transition_ms(False) == 0


def test_the_earcons_layer_asks_the_config_rather_than_deciding_for_itself(
    tmp_path: Path,
) -> None:
    player = NullPlayer()
    earcons = Earcons(
        directory=tmp_path, cache_dir=tmp_path, player=player, access=AccessConfig(calm=True)
    )
    earcons.ensure_sounds()
    assert earcons.play("keep") is True
    assert earcons.play("tap") is False
    assert player.volume == 1.0

    earcons.set_access(AccessConfig(mute=True))
    assert player.volume == 0.0
    assert earcons.play("keep") is False


# --- captions --------------------------------------------------------------


def test_the_caption_strip_is_reserved_and_legible() -> None:
    assert CAPTION_LINES >= 1
    assert CAPTION_MIN_PT >= 18.0  # SYNTHESIS B4's floor, like every other size
    assert 3.0 <= CAPTION_SECONDS <= 6.0  # "~4 s"


def test_the_band_window_grows_by_exactly_the_caption_strip() -> None:
    """It is part of the band *window*, so the compositor gives it the room.

    Which is also why it can never cover content: ``content_height`` is what
    is left after the band window's whole strip.
    """
    with_captions = Metrics.for_screen(1280, 800, dpi=102.0, captions=True)
    without = Metrics.for_screen(1280, 800, dpi=102.0, captions=False)
    assert with_captions.caption_height > 0
    assert without.caption_height == 0
    assert with_captions.band_window_height == (
        with_captions.band_height + with_captions.caption_height
    )
    assert with_captions.content_height == (
        with_captions.screen_height - with_captions.band_window_height
    )


def spoken_lines() -> set[str]:
    """Every string literal the package hands to something called ``speak``.

    Walked out of the AST rather than grepped, so a line that moved into a
    helper is still found.
    """
    found: set[str] = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else None
            if name not in {"speak", "speak_then", "speak_focus", "speak_activation"}:
                continue
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    found.add(argument.value)
    return found


def test_every_shipped_line_fits_one_caption_line_on_the_narrowest_panel() -> None:
    """A caption that wrapped would be clipped by the strip's reserved height.

    The estimator is deliberately a few percent wide, so a line it says fits
    will fit in Pango too -- which is what makes this provable with no display.
    """
    metrics = Metrics.for_screen(1024, 600, dpi=96.0)
    width = metrics.screen_width - 2 * 16  # theme.css `.kid-caption-strip` padding
    for line in spoken_lines():
        assert text_width_px(line, CAPTION_MIN_PT) <= width * CAPTION_LINES, line


def test_nothing_can_be_spoken_without_being_shown() -> None:
    """**The B2 assertion.** One funnel, and the caption is before the gate.

    ``SpeechManager.speak`` is the only thing in the shell that reaches a
    backend, and it calls ``on_caption`` *before* it asks whether speech is
    even enabled -- so a muted shell, or one whose speech-dispatcher is dead,
    still shows the sentence. That last case is when a caption is worth most.
    """
    captions: list[str] = []
    speech = SpeechManager(backend=FakeBackend(), scheduler=FakeScheduler())
    speech.on_caption = captions.append

    speech.speak("You're home.")
    speech.speak_focus("Draw")
    speech.speak_activation("My Things")
    speech.speak_then("You made two things.", "Ready to go outside?")
    assert captions == ["You're home.", "Draw", "My Things", "You made two things."]

    # ...and with no voice at all.
    speech.set_volume(0.0)
    assert speech.enabled is False
    speech.speak("Nothing to undo.")
    assert captions[-1] == "Nothing to undo."


def test_every_speak_call_in_the_package_goes_through_the_captioned_hook() -> None:
    """No call site may reach a backend directly and skip the caption.

    Walks the package's AST for anything calling ``.speak(...)`` and checks the
    receiver is a :class:`SpeechManager` -- ``self.speech``, ``ctx.speech``,
    ``self.ctx.speech``, ``speech_ui.speech``. ``speech.py`` itself is the one
    file allowed to talk to a backend, because it is the file that captions.
    """
    allowed_receivers = {"speech", "backend"}
    offenders: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name == "speech.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"speak", "speak_then"}:
                continue
            receiver = node.func.value
            tail = receiver.attr if isinstance(receiver, ast.Attribute) else None
            if isinstance(receiver, ast.Name):
                tail = receiver.id
            if tail not in allowed_receivers:
                offenders.append(f"{path.name}:{node.lineno} -> {ast.dump(receiver)[:60]}")
    assert not offenders, offenders


def test_the_speech_manager_is_the_only_thing_that_reaches_a_backend() -> None:
    """``backend.speak`` appears in exactly one module, and it captions first."""
    users = [
        path.name
        for path in sorted(PACKAGE.rglob("*.py"))
        if "backend.speak(" in path.read_text(encoding="utf-8")
    ]
    assert users == ["speech.py"]


# --- the grown-up gate, without a pointer ---------------------------------


def test_five_presses_inside_the_window_open_the_gate() -> None:
    """A switch cannot say "and keep it down"; this is the same statement."""
    hold = SwitchHold()
    now = 100.0
    for index in range(SWITCH_PRESSES - 1):
        assert hold.press(now + index * 0.2) is False
    assert hold.press(now + 1.0) is True
    # ...and one burst opens it once, not twice.
    assert hold.press(now + 1.1) is False


def test_a_slower_rhythm_is_not_the_pattern() -> None:
    """A five-year-old drumming on the band must not arrive here by accident."""
    hold = SwitchHold()
    now = 0.0
    for _ in range(20):
        now += SWITCH_WINDOW_SECONDS / (SWITCH_PRESSES - 1) + 0.05
        assert hold.press(now) is False


def test_the_keyboard_hold_is_the_same_three_seconds_as_the_pointer_one() -> None:
    """A gate that is easier to open with a keyboard is not a gate."""
    from kidnix_shell.access import HOLD_SECONDS

    assert HOLD_SECONDS == 3.0


# --- the focus ring --------------------------------------------------------


class Control:
    """Just enough of a widget for the ring: a name and two states."""

    def __init__(self, name: str, visible: bool = True, sensitive: bool = True) -> None:
        self.name = name
        self._visible = visible
        self._sensitive = sensitive

    def get_visible(self) -> bool:
        return self._visible

    def get_sensitive(self) -> bool:
        return self._sensitive

    def __repr__(self) -> str:  # pragma: no cover - test output only
        return self.name


def named(control: object) -> str:
    """The control the ring landed on, by name. Fails loudly on ``None``."""
    assert control is not None, "the ring landed on nothing"
    return str(control.name)  # type: ignore[attr-defined]


def ring_of(band: list[Control], content: list[Control]) -> tuple[FocusRing, list[str]]:
    ring = FocusRing()
    order = ring.rebuild(band, content)
    return ring, [control.name for control in order]


def test_the_ring_is_one_cycle_with_the_band_first() -> None:
    """Band first because it is the half that never changes.

    A child who tabs from a standing start meets the same controls in the same
    order on every surface, and the part that changes comes after the part
    that does not.
    """
    band = [Control(name) for name in ("Back", "Undo", "My Things", "Sun", "Ear", "Grown-up")]
    content = [Control(name) for name in ("Draw", "Potato faces", "All done")]
    _ring, order = ring_of(band, content)
    assert order == [
        "Back",
        "Undo",
        "My Things",
        "Sun",
        "Ear",
        "Grown-up",
        "Draw",
        "Potato faces",
        "All done",
    ]


def test_tab_wraps_in_both_directions() -> None:
    band = [Control("Back"), Control("Ear")]
    content = [Control("Draw")]
    ring, _ = ring_of(band, content)
    assert named(ring.move()) == "Back"
    assert named(ring.move()) == "Ear"
    assert named(ring.move()) == "Draw"
    assert named(ring.move()) == "Back"  # round the loop
    assert named(ring.move(forward=False)) == "Draw"


def test_the_ring_skips_what_a_child_could_not_press() -> None:
    """Undo goes away during put-away; My Things is insensitive in the ritual.

    A ring that stops on either is a ring that appears to have swallowed a
    press.
    """
    band = [
        Control("Back"),
        Control("Undo", visible=False),
        Control("My Things", sensitive=False),
        Control("Ear"),
    ]
    _ring, order = ring_of(band, [Control("Draw")])
    assert order == ["Back", "Ear", "Draw"]
    assert [control.name for control in reachable(band)] == ["Back", "Ear"]


def test_arriving_on_a_screen_focuses_the_screen_and_not_the_band() -> None:
    """``first()`` is the first *content* control: the child is put on the surface."""
    band = [Control("Back"), Control("Ear")]
    ring, _ = ring_of(band, [Control("Draw"), Control("All done")])
    assert named(ring.first()) == "Draw"


def test_a_surface_with_nothing_to_press_still_puts_focus_somewhere() -> None:
    """Put away and Resting have no controls; focus has to be *somewhere*."""
    ring, _ = ring_of([Control("Back"), Control("Ear")], [])
    assert named(ring.first()) == "Back"


def test_focus_survives_a_rebuild_that_keeps_the_control() -> None:
    """The offer adds two band buttons; that must not move a child's focus."""
    back, ear = Control("Back"), Control("Ear")
    ring = FocusRing()
    ring.rebuild([back, ear], [Control("Draw")])
    ring.focus(ear)
    ring.rebuild([back, Control("Finish this one"), ear], [Control("Draw")])
    assert ring.current is ear


def test_focus_is_dropped_when_the_control_it_was_on_goes_away() -> None:
    ring = FocusRing()
    tile = Control("Draw")
    ring.rebuild([Control("Back")], [tile])
    ring.focus(tile)
    ring.rebuild([Control("Back")], [])
    assert ring.current is None
    assert named(ring.move()) == "Back"
