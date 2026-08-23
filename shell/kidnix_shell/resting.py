"""Two vocabularies for "the computer is not available now" (panel ruling, 2026-08-23).

The ordinary four-o'clock session used to end in **night** vocabulary: a moon,
the word "Goodnight", a yawn earcon, and a screen called Sleeping -- while the
default bedtime window is 19:00-07:00. The clinician's blocker (forum #17) is
two findings in one:

* **it is not true**, and this codebase holds itself to "the words have to be
  true" everywhere else. Coco's Videos documents the mirror-image failure -- a
  child who could not go to bed because the character had not said so;
* a moon, "goodnight" and a yawn are **sleep-onset cues**. Conditioning them to
  the moment the nice thing stops is backwards for the bedtime-resistant and
  bedtime-anxious children who are most of that clinician's caseload.

So there are two vocabularies now, switched on :meth:`SessionPolicy.is_bedtime`:

============  ==========================  ==============================
              daytime                     bedtime
============  ==========================  ==============================
state name    Resting                     Goodnight
picture       none (a warm, dim screen)   the moon
earcon        none                        the sleep motif (a yawn)
line          "kidnix is resting.         "kidnix is sleeping."
              Back after tea."
============  ==========================  ==============================

And the daytime line **says when**, in child terms (forum #31): a child who
cannot tell whether the computer comes back after tea, tomorrow or never is a
child who asks an adult repeatedly, which is precisely what the ending ritual
exists to stop.

Since ``[[windows]]`` landed (parent-panel section 7.1) the daytime vocabulary
has a **third** "when" -- *on Saturday* -- and a refusal of its own. Neither is
reachable on a machine with no schedule windows: the budget rolls at 04:00 and
bedtime ends in the morning, so before windows existed nothing was ever
further off than tomorrow. A weekends-only machine is five days off on a
Monday, and telling that child "tomorrow" is a promise the machine breaks
every Tuesday.

Nothing here demands anything of the child. The old line was "kidnix is
sleeping. **Ask a grown-up.**" -- a demand issued to a child whose executive
function has gone offline, and finding an adult is not a five-year-old's task
(forum #23).

Pure: no GTK, no clock of its own. Everything is an argument, so the whole
vocabulary and the rate limit are unit-tested headless.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .i18n import N_, _

# --- the words -----------------------------------------------------------

#: Daytime. Named for what the machine is doing, not for a time of day.
RESTING_TITLE = N_("Resting")
#: Bedtime. The one place the night vocabulary is true.
SLEEPING_TITLE = N_("Goodnight")

#: Daytime, when there is a window later today.
RESTING_LATER_TODAY = N_("kidnix is resting. Back after tea.")
#: Daytime, when there is not.
RESTING_TOMORROW = N_("kidnix is resting. Back tomorrow.")
#: Daytime, when the next window is further off than tomorrow -- which only
#: happens once a parent has set ``[[windows]]`` (parent-panel section 7.1):
#: "weekends only" on a Monday afternoon is five days away, and "tomorrow"
#: would be a lie the child finds out about tomorrow.
#:
#: ``{day}`` is one of :data:`WEEKDAY_WORDS`, already translated. It is a whole
#: phrase and not a bare name so that a translator can put the preposition,
#: the case and the word order where their language wants them.
RESTING_ON_DAY = N_("kidnix is resting. Back {day}.")
#: Bedtime. No demand in it: the child is not being sent to find anybody.
SLEEPING_LINE = N_("kidnix is sleeping.")

#: What "Goodnight" is called at four in the afternoon. The child already
#: knows this phrase -- it is the Home tile they press when they have had
#: enough -- and it is true at any hour.
DAYTIME_GOODNIGHT_LABEL = N_("All done")
BEDTIME_GOODNIGHT_LABEL = N_("Goodnight")

#: **What that button says out loud, and what the caption under the band
#: carries.** The label was switched on ``is_bedtime`` and the *voice* was not,
#: so an ordinary four-o'clock session ended with a button reading "All done"
#: speaking, and captioning, "Goodnight" -- the exact sleep-onset cue forum #17
#: took out of the picture and the screen title, arriving instead through the
#: two channels a pre-reader and a screen-reader user actually get it from.
#: (The last two frames of ``docs/design/screenshots/e2e-contact-sheet.png``.)
#:
#: "Time to rest" is the *machine* resting -- it is the name of the screen this
#: button leads to (:data:`RESTING_TITLE`) and the line that screen speaks. It
#: is not an instruction to the child to go and rest; nothing here instructs.
DAYTIME_GOODNIGHT_SPEECH = N_("All done. Time to rest.")
BEDTIME_GOODNIGHT_SPEECH = N_("Goodnight")

#: **And the picture, which was the last channel still stuck on night.** Home's
#: "All done" tile carried ``kidnix-moon`` at every hour, so the table at the
#: top of this module held for the word, the voice and the caption and not for
#: the one channel a pre-reader actually uses: a four-year-old finds that tile
#: by its picture. A moon on a button pressed at ten in the morning is the
#: sleep-onset cue forum #17 took out of the screen title arriving by the front
#: door -- and it is not true, which is the other half of the ruling.
#:
#: The daytime drawing says what *pressing it does* rather than what time it
#: is: hands lowering a picture into a tidy-away box. It was drawn for this
#: (``data/icons/kidnix-act-all-done-day.svg``) and then wired to nothing.
#:
#: These are icon **names**, resolved by :func:`kidnix_shell.widgets.icon_image`
#: -- the theme first, then our own bundled SVG -- so they are strings here and
#: not paths, and nothing in this module imports GTK to say so.
DAYTIME_GOODNIGHT_ICON = "kidnix-act-all-done-day"
#: Bedtime. The one time of day a moon is the truth.
BEDTIME_GOODNIGHT_ICON = "kidnix-moon"

#: Who's here, when the day's computer time is gone. Warm, non-explanatory,
#: and it points at something to do rather than at the machine's own return
#: (D6: the system has no interest in whether the child comes back). No
#: "tomorrow", no "next time" -- see forum #28, #47.
BUDGET_SPENT_REFUSAL = N_("That's all the computer time for today. Ready to go and play?")
#: The same shape at bedtime, where night words are true.
BEDTIME_REFUSAL = N_("It's night time. kidnix is going to sleep.")

#: Who's here, outside every ``[[windows]]`` a parent set (parent-panel
#: section 7.1). **Daytime words**: this fires at half past three on a
#: Wednesday as readily as at half past eight, and a moon or a "goodnight"
#: here would be the sleep-onset cue forum #17 took out of the picture.
#:
#: Unlike the budget refusal it **says when**, because it can: a window has an
#: opening time, and a child who cannot tell whether the computer comes back
#: after tea, tomorrow or on Saturday asks an adult repeatedly (forum #31).
#: Three phrasings rather than one interpolation for the two common answers,
#: so a translator can shape the whole sentence around the unit.
OUT_OF_HOURS_LATER_TODAY = N_("Not computer time just now. Back after tea.")
OUT_OF_HOURS_TOMORROW = N_("Not computer time just now. Back tomorrow.")
#: ``{day}`` is one of :data:`WEEKDAY_WORDS`, already translated.
OUT_OF_HOURS_ON_DAY = N_("Not computer time just now. Back {day}.")
#: The fallback when nothing can say *when* -- a window list that parsed but
#: whose days never come round again. Still no demand in it, and still true.
OUT_OF_HOURS_REFUSAL = N_("Not computer time just now.")

#: Goodbye's headline when the child chose no destination. Warm, about the
#: turn being over rather than about producing anything, and it never promises
#: a return (forum #28: "See you next time" was firing on the flattest day).
ALL_DONE_HEADLINE = N_("All done for today.")


#: The answers :func:`back_when_words` gives, as msgids. "After tea" is a
#: unit a five-year-old owns and a clock is not; a translator gets to pick the
#: meal their households actually name.
LATER_TODAY_WORDS = N_("after tea")
TOMORROW_WORDS = N_("tomorrow")

#: The third answer, and it exists because ``[[windows]]`` made it reachable
#: (parent-panel section 7.1). Monday first, so the index is
#: :meth:`datetime.date.weekday`'s own -- the same order as
#: :data:`kidnix_shell.session.DAYS`, which is what stops the two drifting.
#:
#: Named days are the one place the daytime vocabulary reaches past tomorrow.
#: They are still not a clock and still not a digit: "on Saturday" is a word a
#: five-year-old hears every week, and a child on a weekends-only machine who
#: is told "tomorrow" every Monday learns that the machine does not mean it.
WEEKDAY_WORDS: tuple[str, ...] = (
    N_("on Monday"),
    N_("on Tuesday"),
    N_("on Wednesday"),
    N_("on Thursday"),
    N_("on Friday"),
    N_("on Saturday"),
    N_("on Sunday"),
)


def back_when_words(now: datetime, next_open: datetime) -> str:
    """When the machine comes back, in words a five-year-old owns.

    Three answers, in order of how far off it is: *after tea* later the same
    day, *tomorrow* the next, and *on Saturday* for anything further -- which
    is only reachable on a machine with schedule windows on it, because the
    budget and the bedtime gate never look past tomorrow morning.

    Child terms, not a clock, and no digits anywhere. A ``next_open`` in the
    past is treated as tomorrow: it is the answer that promises least.
    """
    days = (next_open.date() - now.date()).days
    if days <= 0:
        return _(LATER_TODAY_WORDS) if next_open > now else _(TOMORROW_WORDS)
    if days == 1:
        return _(TOMORROW_WORDS)
    return _(WEEKDAY_WORDS[next_open.weekday()])


def resting_line(now: datetime, next_open: datetime) -> str:
    """The daytime line, with when in it."""
    when = back_when_words(now, next_open)
    if when == _(LATER_TODAY_WORDS):
        return _(RESTING_LATER_TODAY)
    if when == _(TOMORROW_WORDS):
        return _(RESTING_TOMORROW)
    return _(RESTING_ON_DAY).format(day=when)


def rest_title(*, bedtime: bool) -> str:
    return _(SLEEPING_TITLE) if bedtime else _(RESTING_TITLE)


def rest_line(now: datetime, next_open: datetime, *, bedtime: bool) -> str:
    return _(SLEEPING_LINE) if bedtime else resting_line(now, next_open)


def goodnight_label(*, bedtime: bool) -> str:
    return _(BEDTIME_GOODNIGHT_LABEL) if bedtime else _(DAYTIME_GOODNIGHT_LABEL)


def goodnight_speech(*, bedtime: bool) -> str:
    """What the same button says out loud, and is captioned as.

    Separate from :func:`goodnight_label` because the button is 20 mm of text
    and the utterance can afford a second clause -- not because the two may
    disagree about what time of day it is.
    """
    return _(BEDTIME_GOODNIGHT_SPEECH) if bedtime else _(DAYTIME_GOODNIGHT_SPEECH)


def goodnight_icon(*, bedtime: bool) -> str:
    """The picture on the same button. Not translated -- it is an icon name.

    The fourth channel of the same switch (:data:`DAYTIME_GOODNIGHT_ICON`).
    Kept beside the label and the speech so a future edit that moves one of
    them has to walk past the other two.
    """
    return BEDTIME_GOODNIGHT_ICON if bedtime else DAYTIME_GOODNIGHT_ICON


def out_of_hours_line(now: datetime, next_open: datetime | None) -> str:
    """Who's here's answer outside every schedule window, with when in it."""
    if next_open is None:
        return _(OUT_OF_HOURS_REFUSAL)
    when = back_when_words(now, next_open)
    if when == _(LATER_TODAY_WORDS):
        return _(OUT_OF_HOURS_LATER_TODAY)
    if when == _(TOMORROW_WORDS):
        return _(OUT_OF_HOURS_TOMORROW)
    return _(OUT_OF_HOURS_ON_DAY).format(day=when)


def refusal_line(
    *,
    bedtime: bool,
    out_of_hours: bool = False,
    rested: bool = False,
    now: datetime | None = None,
    next_open: datetime | None = None,
) -> str:
    """What Who's here says when there is no turn to be had.

    Four refusals, in the order :class:`kidnix_shell.session.StartRefusal`
    ranks them: bedtime first because night words are true then and nothing
    else needs saying, out-of-hours next because it can say *when*, the spent
    budget after that because it is the one that points at something to do
    instead of at the machine's own return (D6), and **rested** last
    (ADR-0014).

    Rested has **no words of its own**, and that is the decision rather than an
    omission: it says exactly what the Resting screen says, through
    :func:`resting_line`, because it is the same sentence about the same
    machine -- one arriving at a face the child pressed and one arriving on a
    screen. A second phrasing would be two answers to one question, and a
    five-year-old who hears them both would have to work out that they agree.
    Daytime words only: bedtime outranks rested, so this branch never runs at
    night.
    """
    if bedtime:
        return _(BEDTIME_REFUSAL)
    if out_of_hours:
        return out_of_hours_line(now, next_open) if now is not None else _(OUT_OF_HOURS_REFUSAL)
    if rested:
        if now is None or next_open is None:  # pragma: no cover - callers pass both
            return _(RESTING_TOMORROW)
        return resting_line(now, next_open)
    return _(BUDGET_SPENT_REFUSAL)


# --- what the screen does when a child hits it ---------------------------
#
# ``sleeping.py`` bound *every* press anywhere on the surface to
# ``speech.speak(...)``, and ``SpeechManager.speak`` cancels the previous
# utterance mid-word. So a crying child hammering the screen -- the exact
# population this state exists for -- got "kidnix is sleep-- kidnix is sleep--
# kidnix is sleeping" indefinitely, chopped, in a synthetic voice (forum #23).
#
# Three rules, and they are policy, not widget behaviour, which is why they
# live here where a test can hold them:
#
# 1. at most one utterance per :data:`SPEECH_INTERVAL_SECONDS`;
# 2. a press inside that window is simply ignored -- nothing is cancelled, so
#    nothing is ever cut off mid-word;
# 3. after :data:`SILENCE_AFTER_TAPS` presses inside
#    :data:`SILENCE_WINDOW_SECONDS` the screen goes **silent**, and stays
#    silent until the pressing stops. Repeated demands during dysregulation
#    escalate; it is why we teach parents to stop talking.

#: The floor between two utterances on this screen.
SPEECH_INTERVAL_SECONDS = 8.0
#: This many presses inside the window and the screen stops answering at all.
SILENCE_AFTER_TAPS = 3
SILENCE_WINDOW_SECONDS = 30.0


@dataclass
class TapSpeechLimiter:
    """Should this press be answered out loud? Pure, clock-injected.

    ``at`` is a monotonic time in seconds. Every press is recorded, including
    the ones that are not answered -- a child hammering the screen has to be
    able to *earn* the silence, and a limiter that only counted the presses it
    replied to could never notice the hammering.
    """

    interval: float = SPEECH_INTERVAL_SECONDS
    silence_after: int = SILENCE_AFTER_TAPS
    window: float = SILENCE_WINDOW_SECONDS
    _taps: list[float] = field(default_factory=list)
    _last_spoken: float | None = None

    def reset(self) -> None:
        """A fresh arrival at the screen. Speaks once, then the rules apply."""
        self._taps.clear()
        self._last_spoken = None

    @property
    def silent(self) -> bool:
        """True while the screen has decided to say nothing at all."""
        return len(self._taps) >= self.silence_after

    def should_speak(self, at: float) -> bool:
        self._taps = [t for t in self._taps if at - t < self.window]
        self._taps.append(at)
        if self.silent:
            return False
        if self._last_spoken is not None and at - self._last_spoken < self.interval:
            return False
        self._last_spoken = at
        return True
