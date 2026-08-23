"""Every rule, in one pure module. Returns problems; never repairs in silence.

Two callers, deliberately the same code:

* the **panel**, before it offers to save, so a parent sees the sentence before
  they see a polkit prompt; and
* **kidnix-config**, running as root, before it replaces anything at all -- see
  :mod:`kidnix_parent_panel.helper`. A privileged writer that trusts its caller
  is not a privileged writer, it is a permission bug with a JSON parser.

Every problem carries a ``field`` (which control to point at), a ``message``
written for a parent rather than for a log, and a ``fatal`` flag. Fatal means
nothing is written. Non-fatal means "this is not what you probably meant, and
the shell will fall back": the shell's own readers clamp and warn rather than
refuse, so refusing here where it clamps there would leave a parent unable to
save a file the machine would have accepted.

The one rule that is *not* here is the PIN. Changing it is
``kidnix-set-pin``'s job (it hashes, it rate-limits, it demands the current
one), and a panel that validated a PIN would be a panel that had one in memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import model as M


@dataclass(frozen=True)
class Problem:
    """One thing wrong, said in a sentence a parent can act on."""

    field: str
    message: str
    fatal: bool = True

    def __str__(self) -> str:
        return f"{'error' if self.fatal else 'note'}: {self.field}: {self.message}"


def fatal(problems: list[Problem]) -> list[Problem]:
    return [p for p in problems if p.fatal]


def ok(problems: list[Problem]) -> bool:
    """True when nothing fatal is left. Notes do not block a save."""
    return not fatal(problems)


# --- children -------------------------------------------------------------


def validate_children(children: list[M.Child]) -> list[Problem]:
    problems: list[Problem] = []
    seen: set[str] = set()

    if not [c for c in children if not c.retired]:
        # The shell defaults to one profile called "Me" when the list is empty,
        # so this is recoverable -- but a machine with no faces on "Who's here?"
        # is a machine a parent thinks is broken.
        problems.append(
            Problem(
                "children",
                "There is nobody on this machine. Add at least one child, "
                "or the computer will show its own default face.",
            )
        )

    for child in children:
        where = f"children.{child.id or '?'}"
        if not M.is_valid_id(child.id):
            problems.append(
                Problem(
                    where,
                    "This child's short name is not usable as a folder name. "
                    "Letters, numbers and dashes only.",
                )
            )
        if child.id in seen:
            # Two children sharing an id share a Journal directory, which is
            # exactly the "profiles are cosmetic" defect the panel exists to
            # close (forum #4).
            problems.append(
                Problem(
                    where,
                    f"Two children both use the short name '{child.id}'. "
                    "They would share the same drawings.",
                )
            )
        seen.add(child.id)

        if not child.name.strip():
            problems.append(Problem(where, "This child has no name."))
        if len(child.name) > 24:
            problems.append(
                Problem(
                    where,
                    "That name is too long to fit under a face on 'Who's here?'. "
                    "Twenty-four letters at most.",
                    fatal=False,
                )
            )
        for key, colour in (
            ("colour_primary", child.colour_primary),
            ("colour_secondary", child.colour_secondary),
        ):
            if not M.is_colour(colour or ""):
                problems.append(
                    Problem(f"{where}.{key}", f"'{colour}' is not a colour like #0f8a8a.")
                )
        if child.badge not in M.PROFILE_BADGES:
            problems.append(
                Problem(
                    f"{where}.badge",
                    "Every child needs a shape as well as a colour: "
                    + ", ".join(M.PROFILE_BADGES)
                    + ".",
                )
            )
        problems.extend(_age_band_problems(child, where))

    problems.extend(_colour_clash_problems(children))
    return problems


def _age_band_problems(child: M.Child, where: str) -> list[Problem]:
    """An age band is ``LOW-HIGH`` or a single year, or it is not set.

    Empty is legal and means "the parent has not said", and then nothing is
    filtered: ``parent.toml`` is explicit that we do not guess a child's age.
    """
    band = (child.age_band or "").strip()
    if not band:
        return []
    parts = band.split("-")
    try:
        numbers = [int(p) for p in parts]
    except ValueError:
        return [Problem(f"{where}.age_band", f"'{band}' is not an age band like 4-5.")]
    if len(numbers) not in (1, 2):
        return [Problem(f"{where}.age_band", f"'{band}' is not an age band like 4-5.")]
    low, high = (numbers[0], numbers[0]) if len(numbers) == 1 else (numbers[0], numbers[1])
    if low > high:
        return [Problem(f"{where}.age_band", f"'{band}' runs backwards.")]
    if not 1 <= low <= 18 or not 1 <= high <= 18:
        return [Problem(f"{where}.age_band", f"'{band}' is outside 1 to 18.")]
    return []


def _colour_clash_problems(children: list[M.Child]) -> list[Problem]:
    """Two active children must not share a colour pair **or** a badge.

    Colour says whose computer this is and shape is the half of that which
    survives colour blindness (settings.py: ~8% of boys, most of whom do not
    know). Two children with the same pair is the one mistake a parent will
    make and never diagnose, because to them the two faces look different.
    """
    problems: list[Problem] = []
    active = [c for c in children if not c.retired]
    for key, label in (("colours", "colour"), ("badge", "shape")):
        seen: dict[Any, str] = {}
        for child in active:
            value = child.colours if key == "colours" else child.badge
            if value in seen:
                problems.append(
                    Problem(
                        f"children.{child.id}.{key}",
                        f"{child.name} and {seen[value]} have the same {label}. "
                        "Give them different ones so each child can tell "
                        "which face is theirs.",
                        fatal=False,
                    )
                )
            seen[value] = child.name
    return problems


# --- time -----------------------------------------------------------------


def validate_time(time: M.TimeSettings) -> list[Problem]:
    problems: list[Problem] = []

    if not M.MIN_SESSION_MINUTES <= time.length_minutes <= M.MAX_SESSION_MINUTES:
        problems.append(
            Problem(
                "time.length_minutes",
                f"A sitting is {M.MIN_SESSION_MINUTES} to {M.MAX_SESSION_MINUTES} minutes.",
            )
        )
    if not M.ABSOLUTE_FLOOR_MINUTES <= time.min_session_minutes <= M.MAX_SESSION_MINUTES:
        problems.append(
            Problem(
                "time.min_session_minutes",
                f"The shortest sitting is at least {M.ABSOLUTE_FLOOR_MINUTES} minutes -- "
                "below that the ending does not fit inside the session it is ending.",
            )
        )
    if time.min_session_minutes > time.length_minutes:
        problems.append(
            Problem(
                "time.min_session_minutes",
                "The shortest sitting is longer than a whole sitting. "
                "Every session would open inside its own ending.",
            )
        )
    if not M.MIN_DAILY_BUDGET_MINUTES <= time.daily_budget_minutes <= M.MAX_DAILY_BUDGET_MINUTES:
        problems.append(
            Problem(
                "time.daily_budget_minutes",
                f"A day's total is {M.MIN_DAILY_BUDGET_MINUTES} to "
                f"{M.MAX_DAILY_BUDGET_MINUTES} minutes.",
            )
        )
    if time.daily_budget_minutes < time.min_session_minutes:
        problems.append(
            Problem(
                "time.daily_budget_minutes",
                "Today's total is shorter than the shortest sitting, so no "
                "session could ever start.",
            )
        )
    elif time.daily_budget_minutes < time.length_minutes:
        problems.append(
            Problem(
                "time.daily_budget_minutes",
                "The day's total is less than one sitting, so every sitting "
                "will be cut short by the budget.",
                fatal=False,
            )
        )

    for key, value in (
        ("ending_offer_minutes", time.ending_offer_minutes),
        ("put_away_minutes", time.put_away_minutes),
    ):
        if not 1 <= value <= 10:
            problems.append(Problem(f"time.{key}", "This window is 1 to 10 minutes."))
    if time.put_away_minutes >= time.ending_offer_minutes:
        problems.append(
            Problem(
                "time.put_away_minutes",
                "'Put your things away' has to come after the offer to finish, "
                "or the ending loses one of its two beats.",
            )
        )

    for key, value in (("bedtime_start", time.bedtime_start), ("bedtime_end", time.bedtime_end)):
        if M.parse_clock(value) is None:
            problems.append(Problem(f"time.{key}", f"'{value}' is not a time like 19:00."))

    problems.extend(validate_windows(time.windows))
    problems.extend(_window_bedtime_problems(time))
    return problems


def validate_windows(windows: tuple[M.ScheduleWindow, ...]) -> list[Problem]:
    """``[[windows]]``: at least one day, a real start and end, and not empty.

    A zero-length window is refused rather than normalised: a parent who set
    "Saturday 10:00 to 10:00" and got a machine that never turned on would have
    no way to find out why.
    """
    problems: list[Problem] = []
    for index, window in enumerate(windows):
        where = f"time.windows.{index}"
        if not window.days:
            problems.append(Problem(where, "This time of day is not set for any day of the week."))
        unknown = [d for d in window.days if d not in M.DAYS]
        if unknown:
            problems.append(Problem(where, f"Not a day of the week: {', '.join(unknown)}."))
        if len(set(window.days)) != len(window.days):
            problems.append(Problem(where, "The same day is listed twice.", fatal=False))
        start, end = M.clock_minutes(window.start), M.clock_minutes(window.end)
        if start is None:
            problems.append(
                Problem(f"{where}.start", f"'{window.start}' is not a time like 09:00.")
            )
        if end is None:
            problems.append(Problem(f"{where}.end", f"'{window.end}' is not a time like 18:30."))
        if start is not None and end is not None and start == end:
            problems.append(
                Problem(
                    where,
                    "This window starts and finishes at the same minute, so the "
                    "computer would never be usable on those days.",
                )
            )
    return problems


def _window_bedtime_problems(time: M.TimeSettings) -> list[Problem]:
    """Warn when a window is entirely inside bedtime.

    Not fatal -- two settings can honestly disagree and the stricter one should
    win -- but a window nobody can ever use is worth a sentence, because the
    parent's mental model ("I said Saturday morning") and the machine's ("that
    is bedtime") differ and only the machine is right.
    """
    if time.bedtime_off or not time.windows:
        return []
    start, end = M.clock_minutes(time.bedtime_start), M.clock_minutes(time.bedtime_end)
    if start is None or end is None:
        return []

    def asleep(minute: int) -> bool:
        return start <= minute < end if start < end else (minute >= start or minute < end)

    problems: list[Problem] = []
    for index, window in enumerate(time.windows):
        w_start, w_end = M.clock_minutes(window.start), M.clock_minutes(window.end)
        if w_start is None or w_end is None:
            continue
        minutes = range(w_start, w_end) if w_end > w_start else list(range(w_start, 24 * 60))
        if all(asleep(m % (24 * 60)) for m in minutes):
            problems.append(
                Problem(
                    f"time.windows.{index}",
                    f"{window.start}-{window.end} is entirely inside bedtime "
                    f"({time.bedtime_start}-{time.bedtime_end}), so it will never "
                    "let a session start.",
                    fatal=False,
                )
            )
    return problems


# --- sound, home, family, allow-list --------------------------------------


def validate_sound(sound: M.SoundSettings) -> list[Problem]:
    problems: list[Problem] = []
    if not 0.0 <= sound.sound_volume <= 1.0:
        problems.append(Problem("sound.sound_volume", "The volume is 0 to 100%."))
    if sound.voice not in M.VOICE_MODELS:
        problems.append(
            Problem("sound.voice", f"'{sound.voice}' is not one of: {', '.join(M.VOICE_MODELS)}.")
        )
    if not -100 <= sound.speech_rate <= 100:
        problems.append(Problem("sound.speech_rate", "The reading speed is -100 to 100."))
    if sound.mute and not sound.captions:
        # Mute is safe *because* captions are on -- a muted shell still shows
        # every line it would have said. Without them it is not quiet, it is
        # broken, and a pre-reader has nothing left at all.
        problems.append(
            Problem(
                "sound.captions",
                "With the sound off and the captions off, a child who cannot "
                "read yet is told nothing at all. Turn the captions back on.",
            )
        )
    return problems


def validate_home(home: M.HomeSettings) -> list[Problem]:
    problems: list[Problem] = []
    if not 2 <= home.initial_tiles <= 64:
        problems.append(Problem("home.initial_tiles", "Home starts with 2 to 64 pictures."))
    if not 1 <= home.reveal_every_sessions <= 1000:
        problems.append(
            Problem("home.reveal_every_sessions", "A new picture arrives every 1 to 1000 sessions.")
        )
    return problems


def validate_family(family: list[M.Recipient]) -> list[Problem]:
    problems: list[Problem] = []
    seen: set[str] = set()
    for recipient in family:
        where = f"family.{recipient.id or '?'}"
        if not M.is_valid_id(recipient.id):
            problems.append(Problem(where, "This person's short name is not usable."))
        if recipient.id in seen:
            problems.append(Problem(where, f"'{recipient.id}' is listed twice."))
        seen.add(recipient.id)
        if not recipient.name.strip():
            problems.append(Problem(where, "This person has no name."))
        if recipient.photo and not recipient.photo.startswith("/"):
            problems.append(
                Problem(
                    f"{where}.photo",
                    "A photo has to be a full path, so the machine can still "
                    "find it when nobody is logged in.",
                    fatal=False,
                )
            )
    return problems


def validate_allow_lists(children: list[M.Child], known_ids: frozenset[str]) -> list[Problem]:
    """Every id a child is allowed must be an activity this machine has.

    Not fatal: an id for an activity a future image adds is a reasonable thing
    to have written down, and the shell ignores ids it does not recognise. But
    a typo that quietly removes a tile is worth a sentence.
    """
    problems: list[Problem] = []
    if not known_ids:
        return problems
    for child in children:
        unknown = sorted(set(child.allowed_activity_ids) - known_ids)
        if unknown:
            problems.append(
                Problem(
                    f"children.{child.id}.allowed_activity_ids",
                    "This machine has nothing called " + ", ".join(unknown) + ".",
                    fatal=False,
                )
            )
    return problems


# --- the whole thing ------------------------------------------------------


def validate(panel: M.PanelModel, known_ids: frozenset[str] = frozenset()) -> list[Problem]:
    """Everything, in the order the tabs are in."""
    return [
        *validate_children(panel.children),
        *validate_time(panel.time),
        *validate_allow_lists(panel.children, known_ids),
        *validate_sound(panel.sound),
        *validate_home(panel.home),
        *validate_family(panel.family),
        *_hover_problems(panel),
    ]


def _hover_problems(panel: M.PanelModel) -> list[Problem]:
    if not 150 <= panel.hover_dwell_ms <= 3000:
        return [
            Problem(
                "hover_dwell_ms",
                "How long a pointer has to rest before the computer reads "
                "something aloud is 150 to 3000 milliseconds.",
            )
        ]
    return []


def validate_payload(
    payload: dict[str, Any], known_ids: frozenset[str] = frozenset()
) -> list[Problem]:
    """What ``kidnix-config`` runs on the JSON it was handed.

    Rebuilding the model from the payload is the point: it means the root half
    validates *the thing it is about to write*, not a description of it that a
    caller supplied alongside.
    """
    if not isinstance(payload, dict):
        return [Problem("payload", "That is not a settings payload.")]
    if payload.get("schema") != 1:
        return [
            Problem(
                "payload.schema",
                f"This helper understands schema 1, not {payload.get('schema')!r}.",
            )
        ]
    return validate(M.PanelModel.from_payload(payload), known_ids)


# --- the cross-check against the shell's own schema -----------------------


def cross_check_against_shell() -> list[Problem]:
    """Assert the constants copied into :mod:`model` still match the shell's.

    The panel duplicates a handful of the shell's constants so that its pure
    layer imports nothing. That is a copy, and a copy rots. This is the tripwire:
    it imports ``kidnix_shell`` read-only, compares, and is run by the panel's
    tests and by ``kidnix-parent-panel --self-check`` on the image itself.

    Returns an empty list when ``kidnix_shell`` is not installed at all -- a
    developer's laptop is allowed not to have it; the image is not, and
    ``build_files/62-parent-panel.sh`` fails the build if this finds anything.
    """
    try:
        from kidnix_shell import session as shell_session
        from kidnix_shell import settings as shell_settings
    except ImportError:  # pragma: no cover - exercised by the image test
        return []

    problems: list[Problem] = []

    def compare(field: str, ours: Any, theirs: Any) -> None:
        if ours != theirs:
            problems.append(
                Problem(field, f"the panel says {ours!r}, kidnix_shell says {theirs!r}")
            )

    compare("PROFILE_COLOURS", M.PROFILE_COLOURS, shell_settings.PROFILE_COLOURS)
    compare("PROFILE_BADGES", M.PROFILE_BADGES, shell_settings.PROFILE_BADGES)
    compare("MAX_SESSION_MINUTES", M.MAX_SESSION_MINUTES, shell_session.MAX_SESSION_MINUTES)
    compare(
        "MIN_SESSION_MINUTES",
        M.MIN_SESSION_MINUTES,
        shell_session.MIN_SESSION_SECONDS // 60,
    )
    compare(
        "ABSOLUTE_FLOOR_MINUTES",
        M.ABSOLUTE_FLOOR_MINUTES,
        shell_session.MIN_SESSION_FLOOR_SECONDS // 60,
    )
    compare("DEFAULT_SPEECH_RATE", M.DEFAULT_SPEECH_RATE, _shell_speech_rate())
    return problems


def _shell_speech_rate() -> int:
    from kidnix_shell.access import SPEECH_RATE

    return int(SPEECH_RATE)


__all__ = [
    "Problem",
    "cross_check_against_shell",
    "fatal",
    "ok",
    "validate",
    "validate_allow_lists",
    "validate_children",
    "validate_family",
    "validate_home",
    "validate_payload",
    "validate_sound",
    "validate_time",
    "validate_windows",
]
