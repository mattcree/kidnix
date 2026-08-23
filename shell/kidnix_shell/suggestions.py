"""One concrete offline continuation for the Goodbye screen (spec S7).

SYNTHESIS D4 asks the ending to hand the child something to do *away* from the
machine, tied to what they just did. The rules the lines follow:

* concrete and doable in the next five minutes, in a normal room, alone;
* about the thing the child just made, not about coming back tomorrow;
* never a promise about the device, never "see you next time" (D6 -- the
  system has no interest in whether the child returns).

Keyed by activity id first, then by category, then a general fallback. The
choice is deterministic (seeded by the day) so a child who ends two sessions in
one day is not told two different things about the same drawing.
"""

from __future__ import annotations

from datetime import date

from .i18n import N_, _

BY_ACTIVITY: dict[str, tuple[str, ...]] = {
    "tuxpaint": (
        N_("You drew something. Can you find something the same colour in the room?"),
        N_("You drew something. Can you draw it again on paper, bigger?"),
    ),
    "gcompris": (N_("Can you teach a grown-up one of the games you played?"),),
    "ktuberling": (N_("Can you make a funny face with your own face in a mirror?"),),
    "klettres": (N_("Can you find a letter you know somewhere in the room?"),),
    "blinken": (N_("Can you clap a pattern and see if someone can copy it?"),),
    "supertux": (N_("Can you jump over three things in the garden?"),),
    "tuxmath": (N_("Can you count how many chairs are in the house?"),),
    "kolf": (N_("Can you roll something into a cup on the floor?"),),
    "kiwix": (N_("Can you tell someone one thing you found out today?"),),
}

BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "make": (
        N_("Can you make one more, out of paper?"),
        N_("Can you show someone what you made and tell them about it?"),
    ),
    "learn": (N_("Can you tell someone one thing you found out today?"),),
    "play": (N_("Can you play that game outside, with your feet?"),),
}

GENERAL: tuple[str, ...] = (
    N_("Can you find three things in the room that are the same colour?"),
    N_("Can you draw what you did today on paper?"),
)


def offline_suggestion(
    activity_id: str = "",
    category: str = "",
    today: date | None = None,
) -> str:
    """Pick the line for the Goodbye screen. Always returns something."""
    options = BY_ACTIVITY.get(activity_id) or BY_CATEGORY.get(category) or GENERAL
    day = today or date.today()
    return _(options[day.toordinal() % len(options)])
