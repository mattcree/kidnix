"""S1b -- "What's next after?" (spec 7b, SYNTHESIS D4).

The single highest-value change in `docs/research/09-gap-sweep-checkpoint-1.md`.
Hiniker, Heung, Hong & Kientz, *Coco's Videos* (CHI 2018) -- 24 families, three
weeks, randomised condition order -- had the child **choose the offline
activity that would follow before they began**, from nine picture options, and
showed it back at the end: "Now it's time to [activity]. Are you ready to
[activity]?" Children answered the character out loud, pre-empted the line, and
announced the transition to their families. Castillo et al. (2018) says why it
works: the aversive event at an ending is the *destination* thinning out, not
the signal that it is coming.

So kidnix asks first and tells back later. This module is the option set: a
small list of picture choices, parent-configurable in ``parent.toml``, that
sits between "Who's here?" and Home.

The nine categories in Coco's were derived empirically, by clustering 381 diary
entries of what children actually did after screen time. Ours are the eight the
thinker took from that list; the honest thing to say about them is that they
are somebody else's household, which is exactly why they are configurable and
why `parent.toml` says so in a comment.

Pure data -- no GTK -- so the parsing and the fallbacks are unit-tested
headless.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .i18n import N_, _

log = logging.getLogger(__name__)

#: 09 section 6 / spec 7b: "6-9 picture options". Fewer than six is not a
#: choice; more than nine is a Home screen with a second job.
MIN_OPTIONS = 6
MAX_OPTIONS = 9

#: The id of the "I would rather not answer" option. Coco's own set had a
#: ninth, "something else"; ours is "Not sure yet", which is the same escape
#: worded for a child who has not thought about it yet rather than for one who
#: has an answer the list does not contain.
SKIP_ID = "unsure"


@dataclass(frozen=True)
class NextAfter:
    """One picture option: what the child says they will do next."""

    id: str
    #: What the tile reads. **Short**: it lives in Home's two-line label box at
    #: the 18 pt floor, and a third line makes the tile taller than the grid
    #: budgeted for. One or two short words.
    label: str
    #: What hover, focus and activation read aloud. Defaults to the label --
    #: and is usually longer than it, because the voice has no label box.
    audio_label: str = ""
    #: A bundled SVG in ``data/icons`` (or any icon-theme name).
    icon: str = ""
    #: How the option reads mid-sentence in S7's "Ready to ...?". Defaults to
    #: the lower-cased label, which is right for a label that is already a verb
    #: phrase and wrong for a noun -- "Ready to a book?" is why this exists.
    phrase_override: str = ""

    @property
    def skips(self) -> bool:
        """ "Not sure yet": an answer that is not a plan (:data:`SKIP_ID`).

        The screen has to have a way *out* that is not Back. Coco's named
        failure mode is a child treating the machine's statements as inviolable
        rules, and a question with no "don't know" on it is how a five-year-old
        gets committed to a plan they did not have. Choosing it goes to Home
        and leaves Goodbye on its generated fallback line.
        """
        return self.id == SKIP_ID

    # -- what the widgets ask for (the same shape as an Activity) --

    @property
    def name(self) -> str:
        return _(self.label)

    @property
    def icon_kind(self) -> str:
        return "icon-name"

    @property
    def category(self) -> str:
        return "play"

    @property
    def speak_text(self) -> str:
        return _(self.audio_label or self.label)

    @property
    def phrase(self) -> str:
        """How it reads mid-sentence: "Outside" -> "go outside"."""
        if self.phrase_override:
            return _(self.phrase_override)
        if not self.label:
            return ""
        label = _(self.label)
        return label[0].lower() + label[1:]

    @property
    def ready_line(self) -> str:
        """S7's line, in Coco's own words: "Ready to go outside?"."""
        return _(READY_LINE).format(phrase=self.phrase)


#: S7's line, in Coco's own words. A named placeholder, because "Ready to go
#: outside?" puts the verb where English puts it and nowhere else does.
READY_LINE = N_("Ready to {phrase}?")

#: The shipped set. Nine, at the top of 09's 6-9: eight things a five-year-old
#: can start on their own, in a normal house, in the next five minutes -- which
#: is the only test that matters for those -- and a ninth that is a way out of
#: the question (:data:`SKIP_ID`).
DEFAULT_NEXT_AFTER: tuple[NextAfter, ...] = (
    NextAfter(
        "outside", N_("Outside"), N_("Going outside"), "kidnix-next-outside", N_("go outside")
    ),
    NextAfter("book", N_("A book"), N_("Reading a book"), "kidnix-next-book", N_("read a book")),
    NextAfter(
        "build",
        N_("Building"),
        N_("Building with blocks"),
        "kidnix-next-build",
        N_("build something"),
    ),
    NextAfter(
        "draw", N_("Drawing"), N_("Drawing on paper"), "kidnix-next-draw", N_("draw on paper")
    ),
    NextAfter(
        "snack", N_("A snack"), N_("Having a snack"), "kidnix-next-snack", N_("have a snack")
    ),
    NextAfter("bath", N_("Bath time"), N_("Bath time"), "kidnix-next-bath", N_("have a bath")),
    NextAfter("cook", N_("Help cook"), N_("Helping cook"), "kidnix-next-cook", N_("help cook")),
    NextAfter(
        "someone",
        N_("With someone"),
        N_("Playing with someone"),
        "kidnix-next-someone",
        N_("play with someone"),
    ),
    # The ninth. It is deliberately last and deliberately plain: it is a way
    # out of the question, not a competing answer to it.
    NextAfter(SKIP_ID, N_("Not sure"), N_("Not sure yet. That's fine."), "kidnix-ask", ""),
)


def parse_next_after(raw: Any, source: str = "parent.toml") -> tuple[NextAfter, ...]:
    """Read the ``next_after`` list out of a parsed TOML document.

    Accepts both spellings TOML gives a parent -- an array of inline tables
    (``next_after = [{ id = "outside", ... }]``) and an array of tables
    (``[[next_after]]``) -- because they land as the same Python list, and a
    parent should not have to know which one we meant.

    Anything malformed is skipped with a log line rather than refused: a
    mistyped option must not cost a child the whole screen. An empty or
    entirely unusable list falls back to :data:`DEFAULT_NEXT_AFTER`, and more
    than :data:`MAX_OPTIONS` is truncated.
    """
    if raw is None:
        return DEFAULT_NEXT_AFTER
    if not isinstance(raw, list):
        log.warning("%s: next_after must be a list of options; using the defaults", source)
        return DEFAULT_NEXT_AFTER

    options: list[NextAfter] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            log.warning("%s: skipping malformed next_after entry %r", source, entry)
            continue
        identifier = str(entry.get("id", "")).strip()
        label = str(entry.get("label", "")).strip()
        if not identifier or not label:
            log.warning("%s: next_after entries need an id and a label (%r)", source, entry)
            continue
        if identifier in seen:
            log.warning("%s: duplicate next_after id %r; keeping the first", source, identifier)
            continue
        seen.add(identifier)
        options.append(
            NextAfter(
                id=identifier,
                label=label,
                audio_label=str(entry.get("audio_label", "") or label),
                icon=str(entry.get("icon", "") or ""),
                phrase_override=str(entry.get("phrase", "") or ""),
            )
        )

    if not options:
        log.warning("%s: no usable next_after options; using the defaults", source)
        return DEFAULT_NEXT_AFTER
    if len(options) > MAX_OPTIONS:
        log.warning(
            "%s: %d next_after options is more than %d; using the first %d",
            source,
            len(options),
            MAX_OPTIONS,
            MAX_OPTIONS,
        )
        options = options[:MAX_OPTIONS]
    if len(options) < MIN_OPTIONS:
        # Not an error: a household with four real answers should be allowed to
        # say four. Recorded so the number is a decision, not a typo.
        log.info("%s: %d next_after options (09 section 6 suggests 6-9)", source, len(options))
    return tuple(options)


def find(options: tuple[NextAfter, ...], option_id: str) -> NextAfter | None:
    return next((option for option in options if option.id == option_id), None)
