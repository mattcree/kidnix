"""The panel's data model. Pure: no GTK, no filesystem, no subprocesses.

Everything the parent can change is one :class:`PanelModel`, and the whole
write path is ``PanelModel -> payload dict -> TOML text -> kidnix-config``. That
shape is on purpose: the model is what the tests exercise, the payload is what
crosses the pkexec boundary, and the TOML is what the shell reads. Three
representations, each one checkable on its own.

**Names and spellings match the shell's schema** (``kidnix_shell.settings``)
wherever a key already exists, because the shell is the reader and a panel that
invented its own spelling would be a panel that silently did nothing.

Three keys here were written ahead of the shell and are now **read by it**. The
panel used to label them "not switched on yet"; that label was left standing
after the shell caught up, which is the worst of both worlds -- a parent told a
control does nothing either stops using it or, with schedule windows, sets one
carelessly and locks their child out. What is true today:

* ``[[windows]]`` in ``session.toml`` -- weekday/weekend schedule windows.
  ``kidnix_shell.session.parse_windows`` reads them and ``Session.may_start``
  refuses with ``StartRefusal.OUT_OF_HOURS`` outside every one of them. No
  windows means no restriction.
* ``allowed_activity_ids`` **inside a profile** -- a per-child allow-list, and
  the one ``ParentConfig.allows()`` consults first. The machine-wide list at
  the top of the file is the fallback for a child who has no list of their own,
  and the panel writes it as the union of theirs.
* ``[access] speech_rate`` -- how fast read-aloud goes, read by
  ``kidnix_shell.access`` and applied to the voice (calm mode is a floor on
  it). ``tts.env`` deliberately refuses to carry ``length_scale`` (the shell
  would keep overriding it), so the rate belongs next to the other ``[access]``
  keys.

And one thing that is **not** a new key at all: removing a child moves their
``[[profiles]]`` table to ``[[retired_profiles]]``. The shell only ever reads
``profiles``, so the face disappears from "Who's here?" the next time a session
starts, while the id -- and therefore
``~/.local/share/kidnix/profiles/<id>/journal`` -- is still written down where a
parent can restore it. "Remove" that quietly deleted a child's drawings would
be the opposite of SYNTHESIS C2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

# --- what the shell's schema allows --------------------------------------
#
# Duplicated from kidnix_shell.settings / kidnix_shell.session rather than
# imported, because the panel's pure layer must be testable on a machine that
# has no kidnix_shell at all. `validate.cross_check_against_shell` imports the
# real thing and asserts these agree, so the copy cannot rot in silence.

#: :data:`kidnix_shell.settings.PROFILE_COLOURS`.
PROFILE_COLOURS: tuple[tuple[str, str], ...] = (
    ("#0f8a8a", "#f06292"),  # teal / pink
    ("#1a237e", "#ffd54f"),  # navy / butter
    ("#5e35b1", "#80deea"),  # violet / cyan
    ("#bf360c", "#aed581"),  # rust / leaf
)
#: :data:`kidnix_shell.settings.PROFILE_BADGES`. Shape is the half of identity
#: that survives colour blindness, so every child gets one whether or not the
#: parent thinks about it.
PROFILE_BADGES: tuple[str, ...] = ("star", "leaf", "moon", "wave")

#: The two age bands the panel offers. The shell parses any ``"LOW-HIGH"``, and
#: a parent who wants ``"3-9"`` can still write it by hand; the panel offers the
#: two the activity manifests were actually banded for.
AGE_BANDS: tuple[tuple[str, str], ...] = (
    ("4-5", "4 to 5"),
    ("6-8", "6 to 8"),
)

#: ``kidnix_shell.session``: 10-45 is the supported range, and the floor
#: (``min_session_minutes``, 5 by default, 3 absolute) is separate.
MIN_SESSION_MINUTES = 5
MAX_SESSION_MINUTES = 45
#: Below this the two-beat ending ritual does not fit inside the session it is
#: ending (``MIN_SESSION_FLOOR_SECONDS``).
ABSOLUTE_FLOOR_MINUTES = 3
MIN_DAILY_BUDGET_MINUTES = 5
MAX_DAILY_BUDGET_MINUTES = 8 * 60

#: The two voices ``/etc/kidnix/tts.env`` documents. Same speaker, two model
#: sizes; the small one is for a Raspberry Pi or an older laptop.
VOICES: tuple[tuple[str, str, str], ...] = (
    (
        "cori-high",
        "Cori (full)",
        "114 MB, about 110-300 ms a line. The default.",
    ),
    (
        "cori-medium",
        "Cori (small)",
        "64 MB, about 25-50 ms a line. Use this if read-aloud feels laggy.",
    ),
)
VOICE_MODELS = {
    "cori-high": "/usr/share/kidnix/voices/en_GB-cori-high.onnx",
    "cori-medium": "/usr/share/kidnix/voices/en_GB-cori-medium.onnx",
}

#: speech-dispatcher rate -> piper length_scale, quantised to 0.05, exactly as
#: ``kidnix-piperd`` maps it (``/etc/kidnix/tts.env``: ``length_scale = 1.0 -
#: rate / 200``). The panel shows the resulting number so a parent moving the
#: slider can see it is a real quantity and not a mood.
READ_ALOUD_RATES: tuple[tuple[int, str], ...] = (
    (0, "Ordinary pace"),
    (-20, "A little slower"),
    (-35, "Slower (what calm mode uses)"),
    (-50, "Slowest"),
)
#: The rate the shell asks for today (``kidnix_shell.access.SPEECH_RATE``).
DEFAULT_SPEECH_RATE = -20

#: ``[[windows]]``: the day sets the panel offers. A window with no days is not
#: a window, and a window listing every day is the same as no windows at all --
#: both are refused by :mod:`kidnix_parent_panel.validate` rather than quietly
#: normalised, because a parent who set a schedule and got no schedule would
#: never find out.
DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri")
WEEKEND: tuple[str, ...] = ("sat", "sun")

_CLOCK = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def parse_clock(text: str) -> tuple[int, int] | None:
    """``"19:00"`` -> ``(19, 0)``. ``None`` if it is not a 24-hour time."""
    match = _CLOCK.match(text.strip()) if isinstance(text, str) else None
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def clock_minutes(text: str) -> int | None:
    """Minutes past midnight, or ``None``."""
    parsed = parse_clock(text)
    return None if parsed is None else parsed[0] * 60 + parsed[1]


def is_colour(text: str) -> bool:
    """``#rrggbb``. The shell writes colours nowhere else and reads them raw."""
    return bool(_COLOUR.match(text)) if isinstance(text, str) else False


def is_valid_id(text: str) -> bool:
    """A profile or recipient id: lower-case, short, filesystem-safe.

    It becomes a **directory name** under
    ``~/.local/share/kidnix/profiles/``, so this is not cosmetic: a slash or a
    ``..`` in an id would aim the child's Journal somewhere else entirely.
    """
    return bool(_ID.match(text)) if isinstance(text, str) else False


def slugify(name: str, taken: tuple[str, ...] = ()) -> str:
    """A stable id from a child's name, unique against ``taken``.

    A parent types "Rosie", not an identifier, and the id is what the Journal
    directory is named -- so it is derived once, here, and then never changes
    when the name is edited. Renaming a child must not orphan their drawings.
    """
    base = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")[:24]
    base = base or "child"
    if not _ID.match(base):
        base = "child"
    if base not in taken:
        return base
    for n in range(2, 100):
        candidate = f"{base}-{n}"
        if candidate not in taken:
            return candidate
    return f"{base}-{len(taken) + 1}"


# --- the pieces -----------------------------------------------------------


@dataclass(frozen=True)
class Child:
    """One child. ``[[profiles]]`` in ``parent.toml``.

    ``retired`` is the panel's own flag and never reaches the shell as a key:
    it decides whether this table is written as ``[[profiles]]`` (the shell
    shows the face) or ``[[retired_profiles]]`` (it does not). Nothing on disk
    is deleted either way.
    """

    id: str
    name: str
    colour_primary: str = PROFILE_COLOURS[0][0]
    colour_secondary: str = PROFILE_COLOURS[0][1]
    avatar: str = "face-smile"
    badge: str = PROFILE_BADGES[0]
    age_band: str = "4-5"
    skip_next_choice: bool = False
    #: **This child's language** (ADR-0012), ``kidnix_shell.settings.Profile
    #: .language``. ``""`` means "the machine's". The panel has no UI for it
    #: yet and sets it nowhere -- it is here so that a value written by hand,
    #: which is the only way to set one today, SURVIVES an Apply. Re-rendering
    #: ``parent.toml`` without this field silently dropped it, which turned a
    #: bilingual household's Welsh profile back into an English one the first
    #: time a parent changed the bedtime.
    language: str = ""
    #: Per-child allow-list. ``()`` means "everything this child's age band
    #: leaves", matching the shell's empty-means-all reading -- unticking the
    #: last box must never hand a five-year-old an empty Home.
    allowed_activity_ids: tuple[str, ...] = ()
    retired: bool = False

    @property
    def colours(self) -> tuple[str, str]:
        return (self.colour_primary, self.colour_secondary)

    def with_colour_pair(self, index: int) -> Child:
        primary, secondary = PROFILE_COLOURS[index % len(PROFILE_COLOURS)]
        return replace(self, colour_primary=primary, colour_secondary=secondary)


@dataclass(frozen=True)
class ScheduleWindow:
    """``[[windows]]`` in ``session.toml``: when the computer may be used.

    **Enforced.** ``kidnix_shell.session.parse_windows`` reads them,
    ``SessionPolicy.in_window`` answers "is now inside one?" and
    ``Session.may_start`` refuses with ``StartRefusal.OUT_OF_HOURS`` when it is
    not -- the Resting screen, which reads the next window's start to say when
    the computer is awake again. **No windows at all means no restriction**, the
    same empty-means-all rule as ``allowed_activity_ids``: a parent who removes
    their last window gets "any time bedtime allows" back, not a machine that
    never opens.
    """

    days: tuple[str, ...]
    start: str = "09:00"
    end: str = "18:30"
    label: str = ""

    @property
    def spans_midnight(self) -> bool:
        start, end = clock_minutes(self.start), clock_minutes(self.end)
        return start is not None and end is not None and end <= start

    def covers(self, day: str, hhmm: str) -> bool:
        """Is ``hhmm`` on ``day`` inside this window? Used by the preview line.

        A window that wraps midnight belongs to the day it *starts* on, which
        is the reading a parent means by "Friday evening until nine".
        """
        minute = clock_minutes(hhmm)
        start, end = clock_minutes(self.start), clock_minutes(self.end)
        if minute is None or start is None or end is None or day not in self.days:
            return False
        if end > start:
            return start <= minute < end
        return minute >= start or minute < end


@dataclass(frozen=True)
class TimeSettings:
    """``session.toml``. Minutes throughout; the shell converts to seconds."""

    length_minutes: int = 25
    daily_budget_minutes: int = 60
    min_session_minutes: int = 5
    bedtime_start: str = "19:00"
    bedtime_end: str = "07:00"
    #: Both ending windows are **ceilings**: the real window is a proportion of
    #: what was actually granted (20% and 10%), clamped. The panel says so.
    ending_offer_minutes: int = 4
    put_away_minutes: int = 2
    windows: tuple[ScheduleWindow, ...] = ()

    @property
    def bedtime_off(self) -> bool:
        """Equal start and end switches bedtime off entirely (session.toml)."""
        return self.bedtime_start == self.bedtime_end

    def sittings_in_budget(self) -> int:
        """How many full sittings today's budget holds. Shown, not enforced."""
        if self.length_minutes <= 0:
            return 0
        return self.daily_budget_minutes // self.length_minutes


@dataclass(frozen=True)
class SoundSettings:
    """``[access]`` in ``parent.toml``, plus the voice from ``tts.env``."""

    captions: bool = True
    calm: bool = False
    sound_volume: float = 1.0
    mute: bool = False
    voice: str = "cori-high"
    speech_rate: int = DEFAULT_SPEECH_RATE

    @property
    def length_scale(self) -> float:
        """What ``kidnix-piperd`` will actually ask piper for.

        ``1.0 - rate/200``, quantised to 0.05. Shown next to the slider because
        "a little slower" is a feeling and 1.10 is a number, and a parent who
        has read ``tts.env`` should see the same arithmetic here.
        """
        raw = 1.0 - (self.speech_rate / 200.0)
        return round(round(raw / 0.05) * 0.05, 2)

    @property
    def effective_volume(self) -> float:
        """Mute wins. Matches ``AccessConfig.effective_volume``."""
        return 0.0 if self.mute else max(0.0, min(1.0, self.sound_volume))


@dataclass(frozen=True)
class HomeSettings:
    """``[home]``: how fast Home grows.

    ``keep_the_grid_the_same`` is Dan's sentence, and it is the inverse of the
    shell's key: the switch ON means ``show_everything = true``, i.e. no
    progressive disclosure, i.e. no new button appearing on a Tuesday. It is
    the shipped default; the switch exists so that turning disclosure *on* is
    an opt-in a parent can find, which is the panel's whole job.
    """

    keep_the_grid_the_same: bool = True
    initial_tiles: int = 6
    reveal_every_sessions: int = 2

    @property
    def show_everything(self) -> bool:
        return self.keep_the_grid_the_same


@dataclass(frozen=True)
class Recipient:
    """``[[family]]``: someone a letter goes to.

    **Read by the Letters activity**, which shows these people as the faces on
    its "Who is your letter for?" screen (``letters_to_family.recipients``).
    There is deliberately no address of any kind on this object: the child
    session has no egress, so a posted letter lands in
    ``/var/lib/kidnix/outbox/<profile>/`` and a grown-up carries it. ``photo``
    is a path the *child's* account has to be able to read -- the Family tab
    copies whatever a parent picks into ``/var/lib/kidnix/photos/`` and stores
    that path, because a file under ``/var/home/parent`` (0700) resolves to a
    permission error and a drawn placeholder.
    """

    id: str
    name: str
    photo: str = ""
    relation: str = ""


@dataclass
class PanelModel:
    """Everything the parent can change, in one object.

    Mutable on purpose -- it is the thing a GTK window edits -- while every
    piece inside it is frozen, so a change is always a replacement and never a
    surprise held by two widgets at once.
    """

    children: list[Child] = field(default_factory=list)
    time: TimeSettings = field(default_factory=TimeSettings)
    sound: SoundSettings = field(default_factory=SoundSettings)
    home: HomeSettings = field(default_factory=HomeSettings)
    family: list[Recipient] = field(default_factory=list)
    hover_dwell_ms: int = 450
    #: Kept verbatim from the file so a round-trip cannot lose a parent's
    #: hand-edited "What's next after?" options. The panel does not edit them
    #: in v0 -- eight pictures is a screen of its own -- but it must not eat
    #: them either.
    next_after: list[dict[str, Any]] = field(default_factory=list)
    #: Ditto: the PIN hash is never shown, never edited here (that is
    #: ``kidnix-set-pin``) and never dropped on the way past.
    pin_salt: str = ""
    pin_hash: str = ""

    # -- children --

    @property
    def active_children(self) -> list[Child]:
        return [c for c in self.children if not c.retired]

    @property
    def retired_children(self) -> list[Child]:
        return [c for c in self.children if c.retired]

    def child(self, child_id: str) -> Child | None:
        return next((c for c in self.children if c.id == child_id), None)

    def add_child(self, name: str, age_band: str = "4-5") -> Child:
        """A new face. Colour and badge follow position, so two children are
        never handed the same pair by accident."""
        taken = tuple(c.id for c in self.children)
        index = len(self.active_children)
        primary, secondary = PROFILE_COLOURS[index % len(PROFILE_COLOURS)]
        child = Child(
            id=slugify(name, taken),
            name=str(name).strip() or "Child",
            colour_primary=primary,
            colour_secondary=secondary,
            badge=PROFILE_BADGES[index % len(PROFILE_BADGES)],
            age_band=age_band,
        )
        self.children.append(child)
        return child

    def update_child(self, child_id: str, **changes: Any) -> Child | None:
        for index, child in enumerate(self.children):
            if child.id == child_id:
                updated = replace(child, **changes)
                self.children[index] = updated
                return updated
        return None

    def retire_child(self, child_id: str) -> Child | None:
        """Hide the face; keep every drawing. The Wipe button is the delete."""
        return self.update_child(child_id, retired=True)

    def restore_child(self, child_id: str) -> Child | None:
        return self.update_child(child_id, retired=False)

    def move_child(self, child_id: str, delta: int) -> bool:
        """Reorder. The order is the order of faces on "Who's here?"."""
        ids = [c.id for c in self.children]
        if child_id not in ids:
            return False
        index = ids.index(child_id)
        target = index + delta
        if not 0 <= target < len(self.children):
            return False
        self.children[index], self.children[target] = (
            self.children[target],
            self.children[index],
        )
        return True

    # -- the allow-list --

    def allowed_for(self, child_id: str) -> tuple[str, ...]:
        child = self.child(child_id)
        return () if child is None else child.allowed_activity_ids

    def set_allowed(self, child_id: str, ids: tuple[str, ...]) -> None:
        self.update_child(child_id, allowed_activity_ids=tuple(sorted(set(ids))))

    @property
    def machine_allow_list(self) -> tuple[str, ...]:
        """The machine-wide **fallback** list: ``allowed_activity_ids`` at the
        top of ``parent.toml``.

        Not the rule any child with a list of their own is held to.
        ``ParentConfig.allows()`` reads the signed-in profile's
        ``allowed_activity_ids`` first and only consults this when that list is
        empty -- so this is what a child with no list of their own gets, and
        what the shell falls back to when it cannot tell whose session it is.
        The union is the right value for that: it is the widest thing any of
        them may open, and narrowing it would deny a child something their own
        list allows. Age bands still apply per child, which is what stops a
        four-year-old meeting TuxMath. If *any* active child is on "everything",
        this is everything -- an empty list means all, and a union with "all" is
        "all".
        """
        active = self.active_children
        if not active:
            return ()
        if any(not c.allowed_activity_ids for c in active):
            return ()
        merged: set[str] = set()
        for child in active:
            merged.update(child.allowed_activity_ids)
        return tuple(sorted(merged))

    @property
    def allow_list_is_shared(self) -> bool:
        """True when there is more than one child and their lists differ, which
        is worth a sentence on the tab: what each of them may open is their own
        list, and the union above is only the machine's fallback."""
        active = self.active_children
        if len(active) < 2:
            return False
        first = active[0].allowed_activity_ids
        return any(c.allowed_activity_ids != first for c in active[1:])

    # -- family --

    def add_recipient(self, name: str, relation: str = "", photo: str = "") -> Recipient:
        taken = tuple(r.id for r in self.family)
        recipient = Recipient(
            id=slugify(name, taken),
            name=str(name).strip() or "Someone",
            relation=relation.strip(),
            photo=photo.strip(),
        )
        self.family.append(recipient)
        return recipient

    def remove_recipient(self, recipient_id: str) -> bool:
        before = len(self.family)
        self.family = [r for r in self.family if r.id != recipient_id]
        return len(self.family) != before

    # -- the payload that crosses the pkexec boundary --

    def to_payload(self) -> dict[str, Any]:
        """JSON-able. This is exactly what ``kidnix-config`` reads on stdin.

        Flat, explicit and free of any type JSON cannot carry, because the
        thing on the other side of ``pkexec`` runs as **root** and must be able
        to check every field without guessing what a value meant.
        """
        return {
            "schema": 1,
            "parent": {
                "pin_salt": self.pin_salt,
                "pin_hash": self.pin_hash,
                # **The two files agree by construction.** `parent.toml`'s
                # `default_session_minutes` and `session.toml`'s
                # `length_minutes` are the same quantity written down twice --
                # the shell reads the second for the session and the first for
                # the grown-up sheet's "default session length" -- and a
                # machine where they had drifted would answer "how long is a
                # sitting?" differently depending on who asked. The panel has
                # one control and writes it to both.
                "default_session_minutes": self.time.length_minutes,
                "hover_dwell_ms": self.hover_dwell_ms,
                "allowed_activity_ids": list(self.machine_allow_list),
                "access": {
                    "captions": self.sound.captions,
                    "calm": self.sound.calm,
                    "sound_volume": self.sound.sound_volume,
                    "mute": self.sound.mute,
                    "speech_rate": self.sound.speech_rate,
                },
                "home": {
                    "initial_tiles": self.home.initial_tiles,
                    "reveal_every_sessions": self.home.reveal_every_sessions,
                    "show_everything": self.home.show_everything,
                },
                "profiles": [_child_payload(c) for c in self.children if not c.retired],
                "retired_profiles": [_child_payload(c) for c in self.children if c.retired],
                "next_after": list(self.next_after),
                "family": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "relation": r.relation,
                        "photo": r.photo,
                    }
                    for r in self.family
                ],
            },
            "session": {
                "length_minutes": self.time.length_minutes,
                "daily_budget_minutes": self.time.daily_budget_minutes,
                "min_session_minutes": self.time.min_session_minutes,
                "ending_offer_minutes": self.time.ending_offer_minutes,
                "put_away_minutes": self.time.put_away_minutes,
                "bedtime_start": self.time.bedtime_start,
                "bedtime_end": self.time.bedtime_end,
                "windows": [
                    {
                        "days": list(w.days),
                        "start": w.start,
                        "end": w.end,
                        "label": w.label,
                    }
                    for w in self.time.windows
                ],
            },
            "tts": {"voice": self.sound.voice, "model": VOICE_MODELS.get(self.sound.voice, "")},
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PanelModel:
        """The inverse. Tolerant: a missing key is a default, never a crash.

        The helper reads a payload it did not build (a parent scripting the
        machine, a future panel version), so every field is coerced rather than
        trusted. A payload that survives this **and** :mod:`validate` is one
        the shell can read.
        """
        parent = _table(payload.get("parent"))
        session = _table(payload.get("session"))
        access = _table(parent.get("access"))
        home = _table(parent.get("home"))
        tts = _table(payload.get("tts"))

        children = [_child_from(raw, False) for raw in _rows(parent.get("profiles"))]
        children += [_child_from(raw, True) for raw in _rows(parent.get("retired_profiles"))]

        windows = tuple(
            ScheduleWindow(
                days=tuple(str(d).lower()[:3] for d in _rows_of_str(raw.get("days"))),
                start=str(raw.get("start", "09:00")),
                end=str(raw.get("end", "18:30")),
                label=str(raw.get("label", "")),
            )
            for raw in _rows(session.get("windows"))
        )

        voice = str(tts.get("voice", "cori-high"))
        if voice not in VOICE_MODELS:
            # A model *path* is what tts.env actually carries, so accept one
            # and name it. Anything else falls back rather than writing a
            # path nobody has verified exists.
            voice = next(
                (name for name, path in VOICE_MODELS.items() if path == str(tts.get("model", ""))),
                "cori-high",
            )

        return cls(
            children=children,
            time=TimeSettings(
                length_minutes=_int(session.get("length_minutes"), 25),
                daily_budget_minutes=_int(session.get("daily_budget_minutes"), 60),
                min_session_minutes=_int(session.get("min_session_minutes"), 5),
                bedtime_start=str(session.get("bedtime_start", "19:00")),
                bedtime_end=str(session.get("bedtime_end", "07:00")),
                ending_offer_minutes=_int(session.get("ending_offer_minutes"), 4),
                put_away_minutes=_int(session.get("put_away_minutes"), 2),
                windows=windows,
            ),
            sound=SoundSettings(
                captions=_bool(access.get("captions"), True),
                calm=_bool(access.get("calm"), False),
                sound_volume=_float(access.get("sound_volume"), 1.0),
                mute=_bool(access.get("mute"), False),
                voice=voice,
                speech_rate=_int(access.get("speech_rate"), DEFAULT_SPEECH_RATE),
            ),
            home=HomeSettings(
                keep_the_grid_the_same=_bool(home.get("show_everything"), True),
                initial_tiles=_int(home.get("initial_tiles"), 6),
                reveal_every_sessions=_int(home.get("reveal_every_sessions"), 2),
            ),
            family=[
                Recipient(
                    id=str(raw.get("id", "")) or slugify(str(raw.get("name", ""))),
                    name=str(raw.get("name", "")),
                    photo=str(raw.get("photo", "")),
                    relation=str(raw.get("relation", "")),
                )
                for raw in _rows(parent.get("family"))
            ],
            hover_dwell_ms=_int(parent.get("hover_dwell_ms"), 450),
            next_after=[dict(raw) for raw in _rows(parent.get("next_after"))],
            pin_salt=str(parent.get("pin_salt", "")),
            pin_hash=str(parent.get("pin_hash", "")),
        )


def _child_payload(child: Child) -> dict[str, Any]:
    return {
        "id": child.id,
        "name": child.name,
        "colour_primary": child.colour_primary,
        "colour_secondary": child.colour_secondary,
        "avatar": child.avatar,
        "badge": child.badge,
        "age_band": child.age_band,
        "skip_next_choice": child.skip_next_choice,
        "language": child.language,
        "allowed_activity_ids": list(child.allowed_activity_ids),
    }


def _child_from(raw: dict[str, Any], retired: bool) -> Child:
    name = str(raw.get("name", "")).strip() or "Child"
    identifier = str(raw.get("id", "")).strip() or slugify(name)
    return Child(
        id=identifier,
        name=name,
        colour_primary=str(raw.get("colour_primary", PROFILE_COLOURS[0][0])),
        colour_secondary=str(raw.get("colour_secondary", PROFILE_COLOURS[0][1])),
        avatar=str(raw.get("avatar", "face-smile")),
        badge=str(raw.get("badge", PROFILE_BADGES[0])),
        age_band=str(raw.get("age_band", "4-5")),
        skip_next_choice=_bool(raw.get("skip_next_choice"), False),
        language=str(raw.get("language", "")).strip(),
        allowed_activity_ids=tuple(_rows_of_str(raw.get("allowed_activity_ids"))),
        retired=retired,
    )


def _table(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _rows_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int))]


def _int(value: Any, fallback: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return int(value)


def _float(value: Any, fallback: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return float(value)


def _bool(value: Any, fallback: bool) -> bool:
    return value if isinstance(value, bool) else fallback


__all__ = [
    "ABSOLUTE_FLOOR_MINUTES",
    "AGE_BANDS",
    "DAYS",
    "DEFAULT_SPEECH_RATE",
    "MAX_DAILY_BUDGET_MINUTES",
    "MAX_SESSION_MINUTES",
    "MIN_DAILY_BUDGET_MINUTES",
    "MIN_SESSION_MINUTES",
    "PROFILE_BADGES",
    "PROFILE_COLOURS",
    "READ_ALOUD_RATES",
    "VOICES",
    "VOICE_MODELS",
    "WEEKDAYS",
    "WEEKEND",
    "Child",
    "HomeSettings",
    "PanelModel",
    "Recipient",
    "ScheduleWindow",
    "SoundSettings",
    "TimeSettings",
    "clock_minutes",
    "is_colour",
    "is_valid_id",
    "parse_clock",
    "slugify",
]
