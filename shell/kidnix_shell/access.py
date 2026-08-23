"""Access: captions, calm mode, sound level, and the focus ring's order.

Everything in this module is **pure**. It is the half of the accessibility
work that can be proved without a display, which matters because the finding
that produced it was that none of it existed at all: the accessibility review
of 2026-08-23 filed three blockers -- nothing in the band reachable without a
pointer, read-aloud with no fallback for a child who cannot hear it, and no
reduced-motion or sound control anywhere -- and the shell had no place to put
the answers.

Four ideas, in the order a child meets them:

* **Captions** (:data:`CAPTION_SECONDS`). Every spoken line is also written
  down, for about four seconds, in the band. On by default. The rule the
  constitution was missing is the inverse of its own: *nothing essential is
  audio-only*. 13 messages in ``app.py`` had no on-screen counterpart, and the
  one that matters most -- "{name} is asking if you're done." -- is the moment
  a deaf child loses a drawing.
* **Calm** (:class:`AccessConfig.calm`). One switch that owns reduced motion,
  a quieter soundscape and a slower voice, because the children it serves --
  autistic, ADHD, sensory-defensive, anxious -- are not four different
  settings.
* **Volume** (:class:`AccessConfig.sound_volume`, :attr:`AccessConfig.mute`).
  The image has an unbypassable 70% *ceiling*; a ceiling is not a control.
* **The ring** (:class:`FocusRing`). One cycle over both toplevels, band
  first. Modelled here on anything with ``visible`` and ``sensitive``, so the
  order is a headless test rather than a screenshot.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol, TypeVar

log = logging.getLogger(__name__)

# --- captions -------------------------------------------------------------

#: How long a caption stays up. Long enough to read a short sentence at five
#: (the shell's lines are one or two clauses), short enough that it is gone
#: before the next thing happens. The reviewer asked for "~4 s".
CAPTION_SECONDS = 4.0
#: **A floor.** The caption is child-facing text and takes the same 18 pt floor
#: as every other child-facing size (SYNTHESIS B4).
CAPTION_MIN_PT = 18.0
#: What the caption is actually set at, and what ``theme.css`` states for
#: ``.kid-captions``. **The band's height budget is computed from this one**,
#: so the two may not drift: budgeting the floor while drawing 20 pt made the
#: band window's tree 4 px taller than the strip gnome-kiosk gave it, which is
#: a band that cannot be placed at all (measured in the VM, 2026-08-23).
CAPTION_PT = 20.0
#: **One** line, reserved whether it is used or not: a strip that changes
#: height is a band that moves under a child's hand, and two reserved lines
#: cost a 1280x800 panel a whole row of tiles.
#:
#: One line across the panel is ~57 characters at the 18 pt floor on the
#: narrowest screen kidnix ships for, and the longest thing the shell says is
#: 50. ``tests/test_access.py`` asserts that, walking the package's own string
#: literals -- a caption that wrapped would be clipped by the strip the
#: compositor gave the band window, and a clipped caption is a cut label.
CAPTION_LINES = 1

# --- calm -----------------------------------------------------------------

#: speech-dispatcher rate, -100..100. The ordinary voice is already "slightly
#: slower than default"; calm takes another step down rather than a stride --
#: a voice slow enough to sound wrong is a voice a child stops listening to.
SPEECH_RATE = -20
CALM_SPEECH_RATE = -35

#: The one earcon calm mode keeps. "Something was kept" is the only sound in
#: the shell that reports an *outcome* rather than punctuating an action, and
#: it is the one a child would miss.
CALM_EARCONS: frozenset[str] = frozenset({"keep"})

#: 08 section 3.5's spatial transition. Calm (or ``gtk-enable-animations``
#: being off) makes it a cut instead.
TRANSITION_MS = 400


@dataclass(frozen=True)
class AccessConfig:
    """``[access]`` in ``parent.toml``.

    Defaults are the ones a household that never opens the file gets, and they
    are chosen for the child who needs them most: captions **on**, calm off,
    full (still hardware-capped) volume.
    """

    #: Mirror every spoken line as text. On by default -- see the module
    #: docstring; a caption costs a hearing child nothing.
    captions: bool = True
    #: Reduced motion, a smaller soundscape, a slower voice.
    calm: bool = False
    #: 0.0-1.0, applied by the shell on top of the image's 70% hardware cap.
    sound_volume: float = 1.0
    #: Silence: no earcons, no read-aloud. Safe *because* captions default on.
    mute: bool = False
    #: **The machine's language** (ADR-0012). ``""`` means "whatever the
    #: environment says", which on the image is ``en_GB``. A profile's own
    #: ``language`` wins over this one, because a bilingual household is a
    #: household where the *children* differ (docs/research/06 §4.7).
    #: Anything gettext understands: ``"cy"``, ``"pl"``, ``"en_GB"``.
    language: str = ""

    def with_overrides(self, **changes: Any) -> AccessConfig:
        return replace(self, **changes)

    @property
    def effective_volume(self) -> float:
        """What the shell should actually play at, 0.0-1.0."""
        return 0.0 if self.mute else max(0.0, min(1.0, self.sound_volume))

    @property
    def speech_rate(self) -> int:
        return CALM_SPEECH_RATE if self.calm else SPEECH_RATE

    def earcon_allowed(self, name: str) -> bool:
        """May this earcon play at all? Calm keeps ``keep`` and drops the rest."""
        if self.effective_volume <= 0.0:
            return False
        return name in CALM_EARCONS if self.calm else True

    def transition_ms(self, animations_enabled: bool = True) -> int:
        """Stack transition length. Zero is a cut, which is the reduced-motion answer."""
        return 0 if self.reduced_motion(animations_enabled) else TRANSITION_MS

    def reduced_motion(self, animations_enabled: bool = True) -> bool:
        """``calm`` **or** the desktop already saying so.

        WCAG 2.2 SC 2.3.3 is about interaction-triggered motion, and GTK
        already has the user's answer in ``gtk-enable-animations`` (which the
        image's own dconf sets, and which nothing in the shell read until
        now). A parent who turned motion off system-wide should not have to
        find a second switch.
        """
        return self.calm or not animations_enabled


def parse_access(raw: Any, source: str = "parent.toml") -> AccessConfig:
    """``[access]`` out of TOML, clamped, with a log line on anything odd.

    Missing table means the defaults, which is the point of choosing them
    carefully: the machine that nobody configured is the one a SEND child is
    most likely to be handed.
    """
    if raw is None:
        return AccessConfig()
    if not isinstance(raw, dict):
        log.warning("%s: [access] must be a table; using the defaults", source)
        return AccessConfig()

    def flag(key: str, fallback: bool) -> bool:
        value = raw.get(key, fallback)
        if not isinstance(value, bool):
            log.warning("%s: access.%s must be true or false; using %s", source, key, fallback)
            return fallback
        return value

    volume = raw.get("sound_volume", 1.0)
    if isinstance(volume, bool) or not isinstance(volume, int | float):
        if volume is not None:
            log.warning("%s: access.sound_volume must be a number 0.0-1.0", source)
        volume = 1.0
    elif not 0.0 <= float(volume) <= 1.0:
        log.warning("%s: access.sound_volume %r is outside 0.0-1.0; clamping", source, volume)
    language = raw.get("language", "")
    if not isinstance(language, str):
        log.warning('%s: access.language must be a string like "cy"; ignoring', source)
        language = ""

    return AccessConfig(
        captions=flag("captions", True),
        calm=flag("calm", False),
        sound_volume=max(0.0, min(1.0, float(volume))),
        mute=flag("mute", False),
        language=language.strip(),
    )


# --- the grown-up gate, without a pointer ----------------------------------

#: How long the keyboard hold is. The same three seconds the pointer hold is:
#: a gate that is easier to open with a keyboard is not a gate.
HOLD_SECONDS = 3.0
#: The switch-user's alternative to holding. A switch is a *button*, and many
#: switch interfaces cannot express "and keep it down"; five deliberate presses
#: inside three seconds is the same statement -- "I meant this" -- in the only
#: grammar a single switch has. It is still not something a five-year-old
#: arrives at by drumming: :data:`SWITCH_PRESSES` presses inside
#: :data:`SWITCH_WINDOW_SECONDS`, and a slower rhythm simply resets.
SWITCH_PRESSES = 5
SWITCH_WINDOW_SECONDS = 3.0


class SwitchHold:
    """Counts deliberate presses inside a window. Pure; the clock is injected.

    ``press(now)`` returns True on the press that completes the pattern, and
    the count resets afterwards so the gate cannot be opened twice by one
    burst.
    """

    def __init__(
        self,
        presses: int = SWITCH_PRESSES,
        window_seconds: float = SWITCH_WINDOW_SECONDS,
    ) -> None:
        self.presses = max(2, presses)
        self.window_seconds = window_seconds
        self._times: list[float] = []

    def press(self, now: float) -> bool:
        cutoff = now - self.window_seconds
        self._times = [t for t in self._times if t >= cutoff]
        self._times.append(now)
        if len(self._times) >= self.presses:
            self._times.clear()
            return True
        return False

    def reset(self) -> None:
        self._times.clear()

    @property
    def pending(self) -> int:
        """How many presses have counted so far. For the progress bar."""
        return len(self._times)


# --- the focus ring --------------------------------------------------------


class Focusable(Protocol):
    """The little of a widget the ring order depends on."""

    def get_visible(self) -> bool: ...

    def get_sensitive(self) -> bool: ...


T = TypeVar("T")


def reachable(controls: Sequence[T]) -> list[T]:
    """Only the controls a child could actually land on.

    A ring that stops on an invisible Undo (put away) or an insensitive My
    Things (the ending ritual) is a ring that appears to have swallowed a
    press. Anything without the two getters is treated as reachable, which is
    what lets the headless tests use plain objects.
    """
    out = []
    for control in controls:
        visible = getattr(control, "get_visible", None)
        sensitive = getattr(control, "get_sensitive", None)
        if visible is not None and not visible():
            continue
        if sensitive is not None and not sensitive():
            continue
        out.append(control)
    return out


class FocusRing:
    """One cycle over both toplevels: **the band first, then the screen**.

    Tab does not cross toplevels -- that is a Wayland fact, not a GTK bug --
    and since v0.1.5 the band is a toplevel of its own, so there is no
    arrangement of ordinary focus chains that reaches Back from Home. The
    shell therefore keeps the order itself and moves focus explicitly.

    Band first is deliberate and is the opposite of what a desktop does. The
    band is the child's fixed point: Back, Undo, My Things, the Ear and the sun
    are in the same place on every surface, so a child who tabs from a standing
    start meets the same five controls in the same order every time, and the
    part that changes comes after the part that does not.

    The ring is rebuilt on every screen change, and ``index`` is kept on the
    *widget* rather than on its position, so a band that gains the two ending
    choices does not move the focus out from under a hand.
    """

    def __init__(self) -> None:
        self._order: list[Any] = []
        self._band_count = 0
        self._current: Any | None = None

    def rebuild(self, band: Sequence[Any], content: Sequence[Any]) -> list[Any]:
        """Set the ring to the band's controls followed by the screen's."""
        band_controls = reachable(band)
        self._band_count = len(band_controls)
        self._order = [*band_controls, *reachable(content)]
        if self._current is not None and self._current not in self._order:
            self._current = None
        return list(self._order)

    @property
    def order(self) -> list[Any]:
        return list(self._order)

    @property
    def current(self) -> Any | None:
        return self._current

    def focus(self, control: Any) -> Any | None:
        """Put the ring on ``control`` if it is in it. Returns what got focus."""
        if control in self._order:
            self._current = control
        return self._current

    def move(self, forward: bool = True) -> Any | None:
        """The next control, wrapping. From nowhere, the first (or the last)."""
        if not self._order:
            self._current = None
            return None
        if self._current is None or self._current not in self._order:
            self._current = self._order[0 if forward else -1]
            return self._current
        index = self._order.index(self._current)
        self._current = self._order[(index + (1 if forward else -1)) % len(self._order)]
        return self._current

    def first(self) -> Any | None:
        """The control a screen should start on: the first *content* control.

        Not the first control in the ring. The ring starts with the band
        because that is the stable half; arriving on a surface should still put
        the child on the surface, so this is the first thing after the band --
        and on a surface with nothing to press (Put away, Resting) it falls
        back to the band's first, because focus has to be somewhere.
        """
        if len(self._order) > self._band_count:
            return self._order[self._band_count]
        return self._order[0] if self._order else None
