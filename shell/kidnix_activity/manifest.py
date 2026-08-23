"""Validating an activity's manifest, and the template a new one starts from.

The manifest is the shell's input contract (spec section 4) and
:mod:`kidnix_shell.activities` is the parser. Everything it rejects is rejected
here too, by calling it -- there is deliberately no second parser, because two
parsers is how a manifest comes to validate in CI and be skipped on the machine.

What this module adds is the half of the contract the *shell* cannot enforce,
because a third-party manifest is allowed to break it and ours is not:

============================= ================================================
``network_required = false``  SUITE section 1. The child session has no egress
                              (SYNTHESIS H1); a first-party activity that
                              wanted the network would be a design error, not
                              a configuration one.
``quit = "signal"``           :mod:`kidnix_activity.lifecycle`. We save on
                              SIGTERM. A quit dialogue asks a five-year-old to
                              read a question at the exact moment the session
                              is ending.
``goal``                      One honest line for a parent. An activity with
                              nothing to say about what it is for has not
                              finished being designed.
``audio_label``               Pre-reader first: the tile's label is spoken
                              before it is read.
``icon``                      A representational picture. For a child with no
                              English, low vision or CVD it is the only
                              persistent channel there is (ADR-0011).
``kind = "activity"``         A shelf is a shell construct, not an SDK one.
============================= ================================================

The result is :class:`Report` -- errors and warnings, both as plain sentences,
because the audience is whoever is writing their first activity and the useful
form of "this is wrong" names the fix.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kidnix_shell.activities import (
    KIND_ACTIVITY,
    Activity,
    ManifestError,
    parse_manifest,
)

from .lifecycle import QUIT_MODE

__all__ = [
    "TEMPLATE",
    "Report",
    "render_manifest",
    "validate_data",
    "validate_file",
]

#: The template ``kidnix-activity new`` writes, and the one a hand-written
#: manifest should be copied from. Every field the SDK insists on is here with
#: a real value; every field it merely likes is here with a comment.
TEMPLATE = """\
# {name} -- a kidnix activity.
#
# The shell reads this at start-up (spec section 4). `kidnix-activity validate`
# checks it, and the image build refuses a manifest that does not parse.
schema = 1

id = "{activity_id}"
name = "{name}"
# What the shell says aloud when a child hovers or focuses the tile. Written
# for the ear: a name, then one short sentence about what happens.
audio_label = "{name}. {goal}"
# One honest line for a parent. Not marketing, and never a claim about learning
# outcomes we cannot evidence.
goal = "{goal}"

# A representational picture, not a glyph. `icon_kind = "path"` for a file.
icon = "{activity_id}"
icon_kind = "icon-name"

category = "{category}"
# Overlap, not containment: a 4-5 profile sees anything whose band includes 4.
age_band = "{age_band}"

exec = ["{command}"]

# The SDK saves on SIGTERM and never shows a quit dialogue
# (kidnix_activity.lifecycle). Five seconds is spec 7a's autosave grace.
quit = "signal"
quit_grace = 5.0

# The child session has no egress. This is always false for a first-party
# activity (SUITE section 1).
network_required = false

# An SDK activity writes its own Journal entries (kidnix_activity.journal), so
# there is nothing for the shell's importer to watch. Leave these out.
"""

#: Sensible defaults for the template, so a scaffolded activity validates
#: before anybody has written a line of it.
DEFAULT_CATEGORY = "make"
DEFAULT_AGE_BAND = "4-8"
DEFAULT_GOAL = "Say what this is for, honestly, in one line."


@dataclass
class Report:
    """What validation found. ``ok`` is what CI exits on."""

    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    activity: Activity | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    def lines(self) -> list[str]:
        """The report as text, one problem per line, error first."""
        return [f"{self.path}: {message}" for message in self.errors] + [
            f"{self.path}: warning: {message}" for message in self.warnings
        ]


def render_manifest(
    activity_id: str,
    name: str,
    *,
    goal: str = DEFAULT_GOAL,
    category: str = DEFAULT_CATEGORY,
    age_band: str = DEFAULT_AGE_BAND,
    command: str = "",
) -> str:
    """Fill :data:`TEMPLATE` in. What the scaffolder writes."""
    return TEMPLATE.format(
        activity_id=activity_id,
        name=name,
        goal=goal,
        category=category,
        age_band=age_band,
        command=command or activity_id,
    )


def validate_data(data: dict[str, Any], path: Path) -> Report:
    """Check already-parsed TOML. The shell's parser first, then our rules."""
    report = Report(path=path)
    try:
        activity = parse_manifest(data, path)
    except ManifestError as exc:
        report.errors.append(exc.message)
        return report
    report.activity = activity

    if activity.network_required:
        report.errors.append(
            "network_required must be false: the child session has no egress "
            "(SYNTHESIS H1), so a tile that needed it would be a button that lies"
        )
    if activity.quit != QUIT_MODE:
        report.errors.append(
            f'quit must be "{QUIT_MODE}": a first-party activity saves on SIGTERM '
            "(kidnix_activity.lifecycle) instead of asking a five-year-old to read "
            "a dialogue while the session is ending"
        )
    if activity.kind != KIND_ACTIVITY:
        report.errors.append(
            f'kind must be "{KIND_ACTIVITY}": a shelf is a screen the shell draws, '
            "not something an activity can be"
        )
    if not activity.goal.strip():
        report.errors.append("goal is required: one honest line telling a parent what this is for")
    if not activity.audio_label.strip():
        report.errors.append(
            "audio_label is required: a pre-reader hears the tile before they read it"
        )
    if not activity.icon.strip():
        report.errors.append(
            "icon is required: the picture is the only channel that works for a child "
            "with no English, low vision or colour-vision deficiency"
        )

    if activity.journal_watch:
        report.warnings.append(
            "journal_watch is set, but an SDK activity writes its own entries "
            "(kidnix_activity.journal.save_entry) -- the watcher would import the "
            "same work a second time"
        )
    if activity.age_min is None and activity.age_max is None:
        report.warnings.append(
            "no age_band: this activity will be shown to every profile, including a four-year-old"
        )
    if activity.exec_resume:
        report.warnings.append(
            "exec_resume is set: make sure the activity really can open one of its own "
            "Journal files, or a card in My Things will resume to an empty screen"
        )
    return report


def validate_file(path: Path) -> Report:
    """Read and check one manifest. Never raises."""
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        return Report(path=path, errors=[f"cannot be read: {exc}"])
    except tomllib.TOMLDecodeError as exc:
        return Report(path=path, errors=[f"is not valid TOML: {exc}"])
    return validate_data(data, path)


#: TOML files in an activity's directory that are not manifests. Named rather
#: than sniffed: a directory scan that decided what a manifest *looked like*
#: would eventually decide wrongly about a real one, and the useful failure is
#: "this manifest is broken", not "this manifest was skipped".
NOT_MANIFESTS = frozenset({"pyproject.toml", "uv.toml", "ruff.toml", "mypy.toml"})


def validate_paths(paths: list[Path]) -> list[Report]:
    """Check every manifest given, and every ``*.toml`` inside a directory.

    A path named explicitly is always checked, even ``pyproject.toml``: if
    somebody asks about a file by name, answering about a different one would
    be worse than an odd error message.
    """
    reports: list[Report] = []
    for path in paths:
        if path.is_dir():
            reports.extend(
                validate_file(child)
                for child in sorted(path.glob("*.toml"))
                if child.name not in NOT_MANIFESTS
            )
        else:
            reports.append(validate_file(path))
    return reports
