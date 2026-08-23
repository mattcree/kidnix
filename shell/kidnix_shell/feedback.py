"""One line of descriptive feedback for the Goodbye screen (SYNTHESIS E1).

Two reviewers found the same hole from different directions (forum #30, #52):
E1's *specific descriptive feedback* -- "you used five colours" -- "is in
SYNTHESIS and nowhere in the code", and it is not decoration. It is the only
**informational-competence** channel in the product: the one kind of feedback
Deci's meta-analysis says raises intrinsic motivation rather than eroding it,
precisely because it is descriptive rather than evaluative. "You made three
things today" is a count; "You drew two pictures and used five colours" is the
machine having noticed what the child actually did.

The rules the line follows:

* **descriptive, never evaluative.** No "well done", no "great", no stars, no
  comparison with last time. It says what happened and stops.
* **words, never digits** (01 #19, 03 #32), and never an awkward number: past
  :data:`MANY_ABOVE` colours it says "lots of colours", which is both true and
  what an adult would say.
* **only what is in the Journal.** If put away had to kill an activity at the
  hard stop, whatever was on that canvas was never imported, so it is not
  counted here -- the same rule that makes the count safe to say out loud
  (spec 7c).
* **it is allowed to say nothing.** A session with nothing kept gets no line,
  not a consolation prize.

Pure. The one impure part -- actually counting the colours in a PNG -- is
:func:`count_colours`, which is a best-effort read that returns ``None`` on any
problem at all, because a missing colour count must never cost a child their
Goodbye screen.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

#: Words, not digits. Shared with the Goodbye headline.
WORDS = ("nothing", "one", "two", "three", "four", "five")

#: Above this the shell stops counting out loud and says "lots". A five-year-old
#: has no use for "eleven colours", and neither has the sentence.
MANY_ABOVE = 5


def count_phrase(count: int) -> str:
    """ "two things", "five things" -- and never a numeral (03 #32)."""
    if count <= 0:
        return "nothing"
    if count == 1:
        return "one thing"
    if count < len(WORDS):
        return f"{WORDS[count]} things"
    return f"{count} things"


def number_word(count: int) -> str:
    """ "two", or "lots" once the number stops being useful."""
    if count > MANY_ABOVE or count >= len(WORDS):
        return "lots of"
    return WORDS[count]


#: What the child did, by activity, then by category. Present tense is wrong
#: here: the session is over, and the sentence is about what happened.
BY_ACTIVITY: dict[str, tuple[str, str, str]] = {
    "tuxpaint": ("drew", "picture", "pictures"),
    "ktuberling": ("made", "face", "faces"),
}
BY_CATEGORY: dict[str, tuple[str, str, str]] = {
    "make": ("made", "thing", "things"),
    "learn": ("found out about", "thing", "things"),
    "play": ("played", "game", "games"),
}
DEFAULT_WORDS = ("made", "thing", "things")


def words_for(activity_ids: Iterable[str], categories: Iterable[str]) -> tuple[str, str, str]:
    """The verb and nouns for a session, or the general ones if it was mixed.

    A child who drew *and* played gets "made things", because a sentence that
    picked one of the two would be describing half the session as if it were
    all of it.
    """
    ids = {i for i in activity_ids if i}
    if len(ids) == 1:
        only = next(iter(ids))
        if only in BY_ACTIVITY:
            return BY_ACTIVITY[only]
    kinds = {c for c in categories if c}
    if len(kinds) == 1:
        return BY_CATEGORY.get(next(iter(kinds)), DEFAULT_WORDS)
    return DEFAULT_WORDS


@dataclass(frozen=True)
class MadeSummary:
    """What this sitting put in the Journal, in the shape the sentence needs."""

    count: int = 0
    verb: str = DEFAULT_WORDS[0]
    singular: str = DEFAULT_WORDS[1]
    plural: str = DEFAULT_WORDS[2]
    #: Distinct colours across the things that were made, or ``None`` when
    #: nobody could count them (no images, no GdkPixbuf, an unreadable file).
    colours: int | None = None


def descriptive_line(summary: MadeSummary) -> str:
    """E1's line. Empty string when there is nothing true to say."""
    if summary.count <= 0:
        return ""
    noun = summary.singular if summary.count == 1 else summary.plural
    what = f"You {summary.verb} {number_word(summary.count)} {noun}"
    if summary.colours and summary.colours > 1:
        what += f" and used {number_word(summary.colours)} colours"
    return what + "."


# --- counting the colours in a picture -----------------------------------
#
# Cheap on purpose: it runs on the 256 px thumbnails the Journal already
# wrote, samples rather than reading every pixel, and quantises hard. The
# question is "did this child use a lot of colours or a few?", not "what is
# the palette?" -- and the answer has to be ready before the Goodbye screen
# paints.

#: Bits kept per channel. Four is 16 levels: enough to tell red from pink,
#: coarse enough that anti-aliasing along a crayon stroke is not a colour.
QUANTISE_BITS = 4
#: Sample at most this many pixels per picture.
MAX_SAMPLES = 4096
#: A colour has to be at least this share of the sampled pixels to count, so
#: the halo around a stroke does not become "another colour".
MIN_SHARE = 0.005
#: One colour covering more than this much of a picture is its paper.
PAPER_SHARE = 0.40


def count_colours(paths: Iterable[Path]) -> int | None:
    """Distinct colours across some images, or ``None`` if they cannot be read.

    Best effort in every direction: a missing GdkPixbuf, an unreadable file, a
    non-image, or an exception from anywhere in the stack all come back as
    ``None``, and the Goodbye line simply drops the colour clause.
    """
    seen: dict[tuple[int, int, int], int] = {}
    total = 0
    for path in paths:
        counted = _sample_one(path, seen)
        if counted is None:
            continue
        total += counted
    if not total:
        return None
    floor = max(1, int(total * MIN_SHARE))
    counts = sorted((count for count in seen.values() if count >= floor), reverse=True)
    if counts and counts[0] > total * PAPER_SHARE:
        # The paper is not a colour the child chose. One colour covering most
        # of the picture is the background, and counting it would make every
        # blank-ish drawing claim one more colour than it has.
        counts = counts[1:]
    return len(counts)


def _sample_one(path: Path, seen: dict[tuple[int, int, int], int]) -> int | None:
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
        width, height = pixbuf.get_width(), pixbuf.get_height()
        channels = pixbuf.get_n_channels()
        rowstride = pixbuf.get_rowstride()
        data = pixbuf.get_pixels()
        if width <= 0 or height <= 0 or channels < 3:
            return None
        step = max(1, int(((width * height) / MAX_SAMPLES) ** 0.5))
        shift = 8 - QUANTISE_BITS
        counted = 0
        for y in range(0, height, step):
            row = y * rowstride
            for x in range(0, width, step):
                offset = row + x * channels
                if channels == 4 and data[offset + 3] < 128:
                    continue  # transparent: not a colour the child chose
                key = (
                    data[offset] >> shift,
                    data[offset + 1] >> shift,
                    data[offset + 2] >> shift,
                )
                seen[key] = seen.get(key, 0) + 1
                counted += 1
        return counted
    except Exception as exc:  # pragma: no cover - depends on the image stack
        log.debug("could not count the colours in %s: %s", path, exc)
        return None
