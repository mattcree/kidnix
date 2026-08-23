"""The keyboard, and the one place the SDK's focus ring has to stand aside.

`kidnix_activity.keyboard.ActivityKeyboard` puts a key controller on the window
in the **capture** phase and consumes Tab, the arrow keys, Enter and Space to
drive its focus ring. That is exactly right for every activity built so far,
where every control is a button -- and it is wrong for the one screen in the
suite that has a **text entry** on it. A child typing ``i luv u`` into a caption
would find that Space moved the ring and fired a button, and the arrow keys
never reached the cursor.

This module is that exception, made explicit, small and testable:

* :func:`ring_consumes` is a **pure predicate** -- a keyval, a shift flag, and
  whether the caret is in a text entry -- and it is where the rule lives.
* :func:`guard_ring` wraps one :class:`ActivityKeyboard` instance's ``key``
  method with it. It is per-instance, so nothing about the SDK changes for any
  other activity, and it is one line at build time.

The rule, and why each half of it:

============ ==================== =========================================
key          typing               why
============ ==================== =========================================
Tab          **still the ring's**  Tab is how you leave a text box on every
                                   computer there has ever been, and A6 says
                                   the keyboard must be able to reach and
                                   leave every surface. If Tab went to the
                                   entry there would be no way out.
arrows       the entry's           moving the caret
Enter        the entry's           commits what was typed
Space        the entry's           it is a **word separator**. This is the
                                   one that makes the difference between a
                                   caption and a captionwithnospaces.
Escape       nobody's, ever        Back is the shell's, one screen up, in a
                                   fixed place (SDK section 3.4)
Backspace    nobody's, ever        the ring never consumed it either
============ ==================== =========================================

The keyvals are written out as integers rather than imported from ``Gdk`` so
this module -- and the test that pins the rule -- runs with no GTK at all. The
GTK smoke test asserts that every one of them still equals the ``Gdk.KEY_*``
constant it is named after, so the two cannot drift.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = [
    "ACTIVATE",
    "BACKSPACE",
    "ESCAPE",
    "KEYVALS",
    "MOVE",
    "RING_ALWAYS",
    "guard_ring",
    "ring_consumes",
]

#: ``Gdk.KEY_*``, by name, so the smoke test can check every one.
KEYVALS: dict[str, int] = {
    "Tab": 0xFF09,
    "KP_Tab": 0xFF89,
    "ISO_Left_Tab": 0xFE20,
    "Left": 0xFF51,
    "Up": 0xFF52,
    "Right": 0xFF53,
    "Down": 0xFF54,
    "Return": 0xFF0D,
    "KP_Enter": 0xFF8D,
    "ISO_Enter": 0xFE34,
    "space": 0x020,
    "Escape": 0xFF1B,
    "BackSpace": 0xFF08,
}

#: Keys the ring uses to move between controls.
MOVE = frozenset(
    KEYVALS[name]
    for name in ("Tab", "KP_Tab", "ISO_Left_Tab", "Left", "Up", "Right", "Down")
)
#: Keys the ring uses to press the control it is on.
ACTIVATE = frozenset(KEYVALS[name] for name in ("Return", "KP_Enter", "ISO_Enter", "space"))

#: The ring keeps these **even while somebody is typing**, because they are the
#: only way out of a text box for a keyboard user (A6).
RING_ALWAYS = frozenset(KEYVALS[name] for name in ("Tab", "KP_Tab", "ISO_Left_Tab"))

ESCAPE = KEYVALS["Escape"]
BACKSPACE = KEYVALS["BackSpace"]


def ring_consumes(keyval: int, shift: bool = False, typing: bool = False) -> bool:
    """Should the SDK's focus ring take this key? The whole rule, in one place.

    ``shift`` is carried because ``Shift+Tab`` walks the ring backwards and must
    keep doing so while typing, for the same reason plain Tab does.
    """
    if keyval in (ESCAPE, BACKSPACE):
        return False
    if typing:
        return keyval in RING_ALWAYS
    return keyval in MOVE or keyval in ACTIVATE


def guard_ring(keyboard: Any, is_typing: Callable[[], bool]) -> Callable[[], None]:
    """Let a text entry have the keyboard back. Returns an undo callable.

    Wraps ``keyboard.key`` on **this instance only**. The SDK calls it from its
    own controller (``ActivityKeyboard._on_key_pressed`` -> ``self.key``), so
    overriding the attribute is enough and no subclass, no second controller and
    no change to the SDK is needed.
    """
    original = keyboard.key
    #: Was ``key`` already an attribute of the *instance* (a test double, a
    #: previous guard) or does it come from the class? Restoring has to put
    #: back whichever it was, or a second ``guard_ring`` on the same object
    #: would leave a bound method frozen onto the instance for ever.
    was_own = "key" in vars(keyboard)

    def key(keyval: int, shift: bool = False) -> bool:
        if is_typing() and not ring_consumes(keyval, shift, typing=True):
            return False
        return bool(original(keyval, shift))

    keyboard.key = key

    def restore() -> None:
        if was_own:
            keyboard.key = original
        else:
            del keyboard.key

    return restore
