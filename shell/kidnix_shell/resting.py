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

# --- the words -----------------------------------------------------------

#: Daytime. Named for what the machine is doing, not for a time of day.
RESTING_TITLE = "Resting"
#: Bedtime. The one place the night vocabulary is true.
SLEEPING_TITLE = "Goodnight"

#: Daytime, when there is a window later today.
RESTING_LATER_TODAY = "kidnix is resting. Back after tea."
#: Daytime, when there is not.
RESTING_TOMORROW = "kidnix is resting. Back tomorrow."
#: Bedtime. No demand in it: the child is not being sent to find anybody.
SLEEPING_LINE = "kidnix is sleeping."

#: What "Goodnight" is called at four in the afternoon. The child already
#: knows this phrase -- it is the Home tile they press when they have had
#: enough -- and it is true at any hour.
DAYTIME_GOODNIGHT_LABEL = "All done"
BEDTIME_GOODNIGHT_LABEL = "Goodnight"

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
DAYTIME_GOODNIGHT_SPEECH = "All done. Time to rest."
BEDTIME_GOODNIGHT_SPEECH = "Goodnight"

#: Who's here, when the day's computer time is gone. Warm, non-explanatory,
#: and it points at something to do rather than at the machine's own return
#: (D6: the system has no interest in whether the child comes back). No
#: "tomorrow", no "next time" -- see forum #28, #47.
BUDGET_SPENT_REFUSAL = "That's all the computer time for today. Ready to go and play?"
#: The same shape at bedtime, where night words are true.
BEDTIME_REFUSAL = "It's night time. kidnix is going to sleep."

#: Goodbye's headline when the child chose no destination. Warm, about the
#: turn being over rather than about producing anything, and it never promises
#: a return (forum #28: "See you next time" was firing on the flattest day).
ALL_DONE_HEADLINE = "All done for today."


def back_when_words(now: datetime, next_open: datetime) -> str:
    """ "after tea" if the machine opens again later today, else "tomorrow".

    Child terms, not a clock: "after tea" is the unit a five-year-old owns,
    and there are no digits anywhere in the child-facing shell.
    """
    if next_open > now and next_open.date() == now.date():
        return "after tea"
    return "tomorrow"


def resting_line(now: datetime, next_open: datetime) -> str:
    """The daytime line, with when in it."""
    if back_when_words(now, next_open) == "after tea":
        return RESTING_LATER_TODAY
    return RESTING_TOMORROW


def rest_title(*, bedtime: bool) -> str:
    return SLEEPING_TITLE if bedtime else RESTING_TITLE


def rest_line(now: datetime, next_open: datetime, *, bedtime: bool) -> str:
    return SLEEPING_LINE if bedtime else resting_line(now, next_open)


def goodnight_label(*, bedtime: bool) -> str:
    return BEDTIME_GOODNIGHT_LABEL if bedtime else DAYTIME_GOODNIGHT_LABEL


def goodnight_speech(*, bedtime: bool) -> str:
    """What the same button says out loud, and is captioned as.

    Separate from :func:`goodnight_label` because the button is 20 mm of text
    and the utterance can afford a second clause -- not because the two may
    disagree about what time of day it is.
    """
    return BEDTIME_GOODNIGHT_SPEECH if bedtime else DAYTIME_GOODNIGHT_SPEECH


def refusal_line(*, bedtime: bool) -> str:
    return BEDTIME_REFUSAL if bedtime else BUDGET_SPENT_REFUSAL


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
