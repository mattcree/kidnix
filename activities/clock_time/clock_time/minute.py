"""How long is a minute? -- a duration you can see, in the sun's own language.

The second half of the activity, and the half with the sharpest constraint on
it. SYNTHESIS **D6** says *"no fabricated time pressure; countdown timers with
no real stake are a named manipulative pattern -- the session timer is real and
nothing else should imitate it."* 02 section 2.8 says a timer for a five-year-old
is *"not an information display, it is an emotional object"*, and a visible
countdown "can itself generate anticipatory anxiety".

So this is **not a countdown**, and three design decisions keep it from
becoming one:

1. **Nothing is at stake and nothing ends.** No deadline arrives, nothing is
   lost, and the child decides when it stops. The disc is a record of time that
   has passed, not a warning about time that has not.
2. **The guess is made with the picture hidden.** A disc that shrank over
   exactly a minute while the child was asked *to judge a minute* would be
   showing them the answer, and the activity would be a reaction test. So
   :data:`Phase.GUESSING` draws nothing that depletes; the disc comes back
   afterwards, as the *explanation*.
3. **There is a "show me" that is not a test at all.** :data:`Phase.SHOWING`
   runs the same disc with nobody being asked anything. A child who wants to
   watch a minute go past may simply watch one.

The shape itself is the shell's session sun and not a second picture of one --
the panel's one-sun ruling (2026-08-23, ``kidnix_shell/band.py``). It shrinks
and **sinks in place**: 09 Q1's ruling is *"encode depletion as shrinking
filled area / falling height, not horizontal travel"*, because Tillman et al.
(2018) found most preschoolers do not represent time as a directional line at
all. ``tests/test_sun_agreement.py`` re-derives every number below from
``kidnix_shell.sun`` and fails if the two ever drift.

No numbers, anywhere a child can see or hear one (01 #19, 03 #32). The verdict
is three words about *this* interval and nothing else: no seconds, no
percentage, no score, no best-ever, no streak (SUITE section 5, SYNTHESIS E1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .i18n import N_, _

__all__ = [
    "EARLY_BAND",
    "HORIZON_FRACTION",
    "JUST_RIGHT_SENTENCE",
    "LATE_BAND",
    "LENGTHS",
    "LENGTH_LABELS",
    "LENGTH_WORDS",
    "MAX_RADIUS_FRACTION",
    "MIN_RADIUS_FRACTION",
    "PRESS_STOP",
    "SUN_EDGE_INNER",
    "SUN_EDGE_OUTER",
    "SUN_FILL",
    "TOP_PAD_FRACTION",
    "VERDICT_SENTENCE",
    "DiscGeometry",
    "Length",
    "Phase",
    "Verdict",
    "disc_geometry",
    "verdict_for",
]


# --- how long we are asking about ------------------------------------------


class Length(Enum):
    """The three intervals the activity offers. Named, never numbered.

    A minute is the one the brief asks for and the one Year 1 has a word for.
    Half a minute and two minutes are there because a child who has only ever
    judged one interval has learnt a reflex rather than a duration -- and
    because "two minutes" is the phrase adults actually use at the end of a
    session, so it is worth having a picture of.
    """

    HALF_MINUTE = 30.0
    MINUTE = 60.0
    TWO_MINUTES = 120.0

    @property
    def seconds(self) -> float:
        return float(self.value)

    @property
    def words(self) -> str:
        """"half a minute". Translated here, at the moment it is said."""
        return _(LENGTH_WORDS[self])

    @property
    def label(self) -> str:
        """The one short word on the button. Never a digit (01 #19).

        The button says "Half"; the ear gets "Try half a minute." A label that
        wrapped -- and at this size every one of the three full phrases does --
        is a label a five-year-old reads as a shape rather than a word.
        """
        return _(LENGTH_LABELS[self])

    @property
    def prompt(self) -> str:
        """The question, in the imperative, under twelve words (SYNTHESIS B5)."""
        return _(PRESS_STOP).format(length=self.words)


#: What each interval is *called*, as msgids (ADR-0012). A dict beside the enum
#: rather than the enum's own values, because the values are seconds -- and
#: because a table is what a translator can read without reading Python.
LENGTH_WORDS: dict[Length, str] = {
    Length.HALF_MINUTE: N_("half a minute"),
    Length.MINUTE: N_("a minute"),
    Length.TWO_MINUTES: N_("two minutes"),
}

#: TRANSLATORS: the one short word on each interval button. Keep it short: it
#: sits under a picture on a 26 mm control and a wrapped label is a shape
#: rather than a word to a five-year-old.
LENGTH_LABELS: dict[Length, str] = {
    Length.HALF_MINUTE: N_("Half"),
    Length.MINUTE: N_("One"),
    Length.TWO_MINUTES: N_("Two"),
}

#: TRANSLATORS: {length} is an interval -- "half a minute", "two minutes".
PRESS_STOP = N_("Press stop when you think {length} has gone.")

#: In the order the buttons sit in, shortest first.
LENGTHS: tuple[Length, ...] = (Length.HALF_MINUTE, Length.MINUTE, Length.TWO_MINUTES)


# --- what happened ----------------------------------------------------------

#: Below this fraction of the target the child stopped early. Wide on purpose:
#: 02 section 2.8 -- duration judgement at this age is "immature and highly
#: susceptible to emotional and attentional state", so a band that a
#: five-year-old lands in only by luck would be measuring luck. A quarter
#: either way is what an adult would call "about right".
EARLY_BAND = 0.75
#: And above this, late.
LATE_BAND = 1.25


class Verdict(Enum):
    """Three answers. Not a score, not a mark, and never a number.

    The words are the ones an adult in the room would use, and none of them is
    praise or blame: "a bit early" describes the interval, not the child. There
    is deliberately no fourth band for "a very long way out" -- a child who sat
    for four minutes was doing something else, and the activity has nothing
    useful to say about it that is not a judgement.
    """

    #: The value **is** the msgid: the words are what this band is, and there
    #: is nothing else it could be keyed by. `N_` marks it for extraction and
    #: :attr:`words` is what translates it, once a child is sitting down.
    EARLY = N_("a bit early")
    JUST_RIGHT = N_("just right!")
    LATE = N_("a bit late")

    @property
    def words(self) -> str:
        return _(self.value)

    def sentence(self, length: Length) -> str:
        """What the voice says. One clause, and it names what was being judged."""
        if self is Verdict.JUST_RIGHT:
            return _(JUST_RIGHT_SENTENCE).format(length=length.words)
        return _(VERDICT_SENTENCE).format(verdict=self.words, length=length.words)


#: TRANSLATORS: {length} is an interval -- "a minute". The exclamation mark is
#: the whole of the celebration; there is no praise adjective anywhere here.
JUST_RIGHT_SENTENCE = N_("That was {length}. Just right!")
#: TRANSLATORS: {verdict} is "a bit early" or "a bit late", {length} is the
#: interval that was being judged -- "That was a bit early for a minute."
VERDICT_SENTENCE = N_("That was {verdict} for {length}.")


def verdict_for(elapsed: float, length: Length) -> Verdict:
    """Which band ``elapsed`` seconds falls in, for this interval.

    Boundaries are inclusive at the *generous* end on both sides: exactly
    three-quarters of a minute is "just right", and so is exactly a quarter
    over. A boundary that went the other way would put a child who was
    arguably right into the wrong band on a rounding error nobody can see.
    """
    if elapsed <= 0:
        return Verdict.EARLY
    ratio = float(elapsed) / length.seconds
    if ratio < EARLY_BAND:
        return Verdict.EARLY
    if ratio <= LATE_BAND:
        return Verdict.JUST_RIGHT
    return Verdict.LATE


class Phase(Enum):
    """Where the minute screen is. Four states and no dialogue between them."""

    #: Nothing running. Two buttons: show me, and let me try.
    READY = "ready"
    #: The disc is depleting and nobody is being asked anything.
    SHOWING = "showing"
    #: The child is judging. **The disc is not drawn.** See the module docstring.
    GUESSING = "guessing"
    #: What happened, as a picture and three words.
    RESULT = "result"

    @property
    def draws_disc(self) -> bool:
        return self in (Phase.SHOWING, Phase.RESULT)


# --- the shape (kidnix_shell.sun, restated) ---------------------------------
#
# Restated rather than imported for the reason `clock_time.words` has no GTK in
# it: the pure half of this activity must be importable, and testable, on a
# machine with no shell and no GTK at all. `tests/test_sun_agreement.py` imports
# both wherever the shell *is* importable and asserts they agree, which is what
# stops them drifting -- the same trick `sounds_and_words.settings.progress_dir`
# uses against `kidnix_activity`.

#: Where the horizon sits, as a fraction of the widget's height.
HORIZON_FRACTION = 0.80
#: The disc at the start, as a fraction of the widget's height.
MAX_RADIUS_FRACTION = 0.30
#: And at the end. **Not zero**: a sun that vanishes is a sun that broke.
MIN_RADIUS_FRACTION = 0.13
#: Clearance above the full-size disc so it never looks clipped.
TOP_PAD_FRACTION = 0.06

#: The fill. Contrast is carried by the double stroke, not by the yellow --
#: no yellow clears 3:1 against the band, so the *outline* is what meets
#: WCAG 1.4.11 (``kidnix_shell/sun.py``, and the four measured failures there).
SUN_FILL = "#ffd64f"
#: The inner stroke, against the disc's own fill. @kid-ink.
SUN_EDGE_INNER = "#16181d"
#: The outer stroke, against whatever is behind it. @kid-paper.
SUN_EDGE_OUTER = "#fbf7ef"
SUN_EDGE_INNER_PX = 3.0
SUN_EDGE_OUTER_PX = 2.5


@dataclass(frozen=True)
class DiscGeometry:
    """Everything the drawing needs, in device pixels."""

    #: Always the centre. There is no horizontal travel (09 Q1).
    centre_x: float
    centre_y: float
    radius: float
    horizon_y: float
    #: Where it started, and how big. Drawn as a faint outline, because that
    #: ghost is what makes the shrinking legible as *loss of quantity* rather
    #: than as a picture that happens to be small today.
    start_centre_y: float
    start_radius: float


def disc_geometry(fraction_spent: float, width: float, height: float) -> DiscGeometry:
    """Map "how much has gone" onto a size and a height.

    ``fraction_spent`` is 0.0 at the start and 1.0 at the full interval. Any
    float is accepted and clamped -- a clock that jumped must not throw at a
    five-year-old.
    """
    spent = max(0.0, min(1.0, float(fraction_spent)))
    left = 1.0 - spent

    horizon = height * HORIZON_FRACTION
    max_radius = height * MAX_RADIUS_FRACTION
    min_radius = height * MIN_RADIUS_FRACTION
    top_pad = height * TOP_PAD_FRACTION

    radius = min_radius + (max_radius - min_radius) * left
    start_centre_y = min(horizon, top_pad + max_radius)
    centre_y = horizon - (horizon - start_centre_y) * left

    return DiscGeometry(
        centre_x=width / 2.0,
        centre_y=centre_y,
        radius=radius,
        horizon_y=horizon,
        start_centre_y=start_centre_y,
        start_radius=max_radius,
    )
