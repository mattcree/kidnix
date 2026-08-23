"""Where the sun is, given how much of the session is left (spec 7b).

**The sun no longer travels.** v0.1.3 drew it crossing the sky left to right,
which asks a five-year-old to read a *directional mental timeline* -- and
Tillman, Tulagan, Fukuda & Barner (2018, *Developmental Science*) found that
most preschoolers do not represent time that way at all. What they *can* read
is a quantity that visibly gets smaller: that is the only claim Time Timer's
own evidence supports, and it is what 09 section 1 asks kidnix to encode.

So depletion is **size and height**, at a fixed horizontal centre:

* the sun's **radius** falls from :data:`MAX_RADIUS_FRACTION` of the band's
  height to :data:`MIN_RADIUS_FRACTION` of it;
* its **centre** falls from high in the sky to exactly on the horizon, where
  the drawing clips it, so the last minute of a session is a small half-disc
  sitting on the line;
* its **x is constant**, always the centre of the widget.

09 section 1's other ruling matters as much and is not geometry: the sun is
*state*, not a warning, and not the mechanism that buys a calm ending. Four
JABA single-case experiments say an antecedent cue on its own is inert. Nobody
should tune these numbers expecting them to buy anything.

Pure arithmetic, no GTK, so the mapping is unit-tested headless
(:mod:`tests.test_sun`) and :class:`kidnix_shell.band.Sun` only paints it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .state import State

#: Where the horizon sits in the widget, as a fraction of its height. The sun
#: needs room to sink *to*, and the line needs room under it to read as ground.
HORIZON_FRACTION = 0.80

#: The sun at the start of a session, as a fraction of the widget's height.
MAX_RADIUS_FRACTION = 0.30
#: The sun at the hard stop. Not zero: a sun that vanishes is a sun that broke,
#: and the child still has to be able to tap it (08 section 4.6).
MIN_RADIUS_FRACTION = 0.13

#: Clearance kept between the top of the full-size sun and the top of the
#: widget, in the same fraction-of-height units, so it never looks clipped.
TOP_PAD_FRACTION = 0.06


@dataclass(frozen=True)
class SunGeometry:
    """Everything the drawing needs, in device pixels."""

    #: Always the centre of the widget. There is no horizontal travel.
    centre_x: float
    centre_y: float
    radius: float
    #: The line the sun sinks behind.
    horizon_y: float
    #: Where the sun was, and how big, at the start of the session. Drawn as a
    #: faint outline so "how much has gone" is visible and not just remembered.
    start_centre_y: float
    start_radius: float


def sun_geometry(fraction_spent: float, width: float, height: float) -> SunGeometry:
    """Map "how much of the sitting has gone" onto a size and a height.

    ``fraction_spent`` is :meth:`kidnix_shell.session.Session.fraction_spent`:
    0.0 at the start of the session, 1.0 at the hard stop. Any float is
    accepted -- a clock that jumped must not throw at a five-year-old.
    """
    spent = max(0.0, min(1.0, fraction_spent))
    left = 1.0 - spent

    horizon = height * HORIZON_FRACTION
    max_radius = height * MAX_RADIUS_FRACTION
    min_radius = height * MIN_RADIUS_FRACTION
    top_pad = height * TOP_PAD_FRACTION

    radius = min_radius + (max_radius - min_radius) * left
    # The full sun starts as high as it can go without touching the top edge,
    # and sinks until its centre is on the horizon.
    start_centre_y = min(horizon, top_pad + max_radius)
    centre_y = horizon - (horizon - start_centre_y) * left

    return SunGeometry(
        centre_x=width / 2.0,
        centre_y=centre_y,
        radius=radius,
        horizon_y=horizon,
        start_centre_y=start_centre_y,
        start_radius=max_radius,
    )


# --- what the sun says when no session is running (panel ruling, 2026-08-23)


#: The states in which the sun is **down**. The session is over on all of them,
#: and the picture has to agree with the sentence: ``app._tick`` used to set
#: ``set_progress(0.0)`` whenever the session was not running, and fraction 0
#: means *start of day*. So Goodbye showed a full, high sun over "the sun has
#: gone down for today" -- for a pre-reader the picture wins, and the one
#: ambient state the product has contradicted the ritual at the exact second
#: the child was checking whether it was really over (forum #7, #49, #51).
DOWN_STATES = frozenset(
    {
        State.ENDING_OFFER,
        State.PUT_AWAY,
        State.GOODBYE,
        State.SHOWING,
        State.SLEEPING,
    }
)


def idle_fraction(state: State, previous: float) -> float:
    """Where the sun sits when the clock is not driving it.

    Down (1.0) through the whole ending, back up to 0.0 **only** on entering
    "Who's here?" -- which is the one moment a new day of computer time really
    does begin. Anywhere else it holds what it had, so nothing jumps.
    """
    if state is State.CHOOSING:
        return 0.0
    if state in DOWN_STATES:
        return 1.0
    return max(0.0, min(1.0, previous))
