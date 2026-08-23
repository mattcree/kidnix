"""What a key press means. Pure, so the mapping is a table and not a guess.

SYNTHESIS **A6**: the keyboard is never *required*, and everything here can be
done by pressing something on the screen. It is here because a child who cannot
use a mouse must still be able to move the hands, and because a keyboard is how
an automated test drives an activity that has no synthetic pointer.

The SDK owns the focus ring (:class:`kidnix_activity.keyboard.ActivityKeyboard`)
and it consumes Tab, the arrows, Enter and Space. This activity takes **two** of
those back and leaves the rest alone:

=========== ====================================================================
Tab         the SDK's. Walks the ring, in reading order.
Enter       the SDK's. Presses whatever the ring is on.
Left/Right  **ours.** One position round the rim -- five minutes in Year 2, half
Up/Down     an hour in Year 1. The ring has Tab; the hands have nothing else.
Space       **ours.** Now, on the clock screen; start or stop, on the minute one.
Escape      **nobody's here.** It belongs to the shell, one screen up, and an
            activity that handled it would have invented a second way out that
            is invisible, unlabelled and unspoken (SDK section 3.4).
=========== ====================================================================

Taking the arrows is a real trade: it costs arrow-key navigation of the ring.
It is worth it because moving the hands is the *content* of this activity and
a ring position is not, and because Tab and Shift-Tab still walk everything --
so A6 is kept, and no control has become unreachable.

The mapping is expressed over **key names** rather than GDK keyvals so that it
can be tested with no GTK present at all; :func:`action_for_keyval` does the
one lookup that needs the library, and only the window imports it.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["KEY_NAMES", "Action", "Screen", "action_for", "action_for_keyval"]


class Screen(Enum):
    """Which of the two screens the key was pressed on."""

    #: Play with the clock.
    CLOCK = "clock"
    #: How long is a minute?
    MINUTE = "minute"


class Action(Enum):
    """What the activity should do about it. ``None`` means "not ours"."""

    #: One position clockwise round the rim.
    MINUTE_FORWARD = "minute-forward"
    #: One position anticlockwise.
    MINUTE_BACK = "minute-back"
    #: Jump the hands to the real time and say it.
    NOW = "now"
    #: Start the interval, or stop it if it is already running.
    START_OR_STOP = "start-or-stop"


#: The names this module understands, spelled as GDK spells them. Listed so a
#: test can assert the table is complete without importing Gdk.
KEY_NAMES: tuple[str, ...] = (
    "Left",
    "KP_Left",
    "Down",
    "KP_Down",
    "Right",
    "KP_Right",
    "Up",
    "KP_Up",
    "space",
    "KP_Space",
)

_FORWARD = frozenset({"Right", "KP_Right", "Up", "KP_Up"})
_BACK = frozenset({"Left", "KP_Left", "Down", "KP_Down"})
_SPACE = frozenset({"space", "KP_Space"})


def action_for(name: str, screen: Screen = Screen.CLOCK) -> Action | None:
    """``("Right", Screen.CLOCK)`` -> :data:`Action.MINUTE_FORWARD`.

    Returns ``None`` for everything the activity does not claim, which is the
    signal the caller passes back to the SDK as "I did not consume that". Every
    key not in :data:`KEY_NAMES` -- Escape and Backspace above all -- comes back
    ``None``, and a test asserts it for both of them by name.
    """
    if screen is Screen.MINUTE:
        return Action.START_OR_STOP if name in _SPACE else None
    if name in _FORWARD:
        return Action.MINUTE_FORWARD
    if name in _BACK:
        return Action.MINUTE_BACK
    if name in _SPACE:
        return Action.NOW
    return None


def action_for_keyval(keyval: int, screen: Screen = Screen.CLOCK) -> Action | None:
    """The same, for a raw GDK keyval. The one function that needs GTK."""
    from gi.repository import Gdk

    name = Gdk.keyval_name(keyval) or ""
    return action_for(name, screen)
