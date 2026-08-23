"""Clock -- playing with a clock, and finding out how long a minute is.

Two screens, one activity (``docs/plan/ACTIVITY-IDEAS.md``, Matt, 2026-08-22):

**Play with the clock.** A big teaching clock the child moves by pressing the
rim. The hands snap to the positions their year has been taught -- o'clock and
half past in Year 1, the quarters and the five-minute marks in Year 2 -- the
voice says what they made ("half past three"), and beside it this family's day
changes with the hands: the sky, the picture, the name of the thing that
happens then. That last part is the point of the whole activity. 02 #18 found
that *context* is what actually ends screen time, not clocks, and a child who
can connect "half past six" to "when we have tea" has learnt something about
their house as well as about a dial.

**How long is a minute?** A duration made visible, in the session sun's own
language: a disc that shrinks and sinks in place, never travels sideways
(09 Q1, Tillman et al. 2018), never turns red and never pulses (08 section 4.6).
The child presses stop when they think the interval has gone and is told, in
three words with no number in them, how it went.

**Importing this package imports no GTK.** Everything the activity knows --
what the hands are showing, where a tap lands, which moment of the day that is,
what the sky is doing, whether a guess was early -- is in the pure modules
here, and is tested headless. :mod:`clock_time.dial` imports ``cairo``, which
is also displayless, so even the drawing is exercised without a window. The
window lives in :mod:`clock_time.activity` and is imported only by the entry
point.

The one-line acceptance test: *a Year 1 child can put the hands on half past
three, hear it said, see that half past three is when they come home, and find
the clock they made in My Things.*
"""

from .dial import draw_dial, draw_disc, draw_sky, render_card, total_from_point
from .i18n import N_
from .keys import Action, Screen, action_for
from .minute import DiscGeometry, Length, Phase, Verdict, disc_geometry, verdict_for
from .routine import DEFAULT_ROUTINE, Routine, RoutineItem, Sky, parse_hhmm
from .settings import ParentSettings, load_settings, settings_from_document
from .words import ClockTime, Mode, hour_name, snap

#: The manifest id the shell launches this as, and the id every Journal entry
#: is filed under. A slug, and the identity everywhere that matters.
ACTIVITY_ID = "clock-time"
#: The window title, and the fallback title of a Journal card. A msgid: the
#: use site calls ``_()`` on it once a child's language is known (ADR-0012).
TITLE = N_("Clock")

__all__ = [
    "ACTIVITY_ID",
    "DEFAULT_ROUTINE",
    "TITLE",
    "Action",
    "ClockTime",
    "DiscGeometry",
    "Length",
    "Mode",
    "ParentSettings",
    "Phase",
    "Routine",
    "RoutineItem",
    "Screen",
    "Sky",
    "Verdict",
    "action_for",
    "disc_geometry",
    "draw_dial",
    "draw_disc",
    "draw_sky",
    "hour_name",
    "load_settings",
    "parse_hhmm",
    "render_card",
    "settings_from_document",
    "snap",
    "total_from_point",
    "verdict_for",
]

__version__ = "0.1.0"
