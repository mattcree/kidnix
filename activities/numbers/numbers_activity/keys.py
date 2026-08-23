"""What a key press means. Pure, so the mapping is a table and not a guess.

SYNTHESIS **A6**: the keyboard is never *required*, and every answer here can
be given by pressing a tile or a box on the screen. The digits are here because
a child who cannot use a mouse must still be able to answer, because a child who
is learning where the numerals are on a keyboard is doing something worth doing,
and because a keyboard is how an automated test drives an activity that has no
synthetic pointer.

This activity takes **one** thing back from the SDK's focus ring
(:class:`kidnix_activity.keyboard.ActivityKeyboard`), and it is the one thing
the ring does not want:

=========== ====================================================================
1 - 9, 0    **ours.** The answer, directly. ``0`` means *ten*, which is what the
            key is next to on a keyboard and what a ten-key means everywhere
            else; there is no zero to answer, so the key is free.
Tab         the SDK's. Walks every control in reading order.
Arrows      the SDK's. Also walk the ring -- unlike Clock, nothing here is
            positional, so there is no reason to take them.
Enter/Space the SDK's. Press whatever the ring is on.
Escape      **nobody's here.** It belongs to the shell, one screen up, and an
            activity that handled it would have invented a second way out that
            is invisible, unlabelled and unspoken (SDK section 3.4).
=========== ====================================================================

A digit that is not on offer -- ``7`` in a session that counts to five -- comes
back as a number all the same, and the *activity* decides it is not one of its
choices. Two reasons: this module has no business knowing a parent's settings,
and a press that silently does nothing is better answered by the caller, which
can at least say the number out loud.

The mapping is expressed over **key names** rather than GDK keyvals so that it
can be tested with no GTK present at all; :func:`number_for_keyval` does the one
lookup that needs the library, and only the window imports it.
"""

from __future__ import annotations

__all__ = ["KEY_NAMES", "TEN_KEY", "number_for", "number_for_keyval"]

#: The key that means ten. There is no zero to answer in this activity -- a
#: bond's parts are both at least one and you cannot subitise nothing -- so the
#: key is spare, and it is where a hand already is.
TEN_KEY = 10

_DIGITS: dict[str, int] = {}
for _digit in range(10):
    _number = _digit if _digit != 0 else TEN_KEY
    _DIGITS[str(_digit)] = _number
    _DIGITS[f"KP_{_digit}"] = _number

#: Every name this module understands, spelled as GDK spells it. Listed so a
#: test can assert the table is complete without importing Gdk.
KEY_NAMES: tuple[str, ...] = tuple(_DIGITS)


def number_for(name: str) -> int | None:
    """``"4"`` -> ``4``; ``"KP_0"`` -> ``10``; everything else -> ``None``.

    ``None`` is the signal the caller passes back to the SDK as "I did not
    consume that". Every key not in :data:`KEY_NAMES` -- Escape and Backspace
    above all -- comes back ``None``, and a test asserts it for both by name.
    """
    return _DIGITS.get(name)


def number_for_keyval(keyval: int) -> int | None:
    """The same, for a raw GDK keyval. The one function that needs GTK."""
    from gi.repository import Gdk

    return number_for(Gdk.keyval_name(keyval) or "")
