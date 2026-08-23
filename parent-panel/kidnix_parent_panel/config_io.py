"""Reading and rendering the three files the panel owns. Pure over strings.

``/etc/kidnix/parent.toml``, ``/etc/kidnix/session.toml`` and
``/etc/kidnix/tts.env``. Nothing here writes anything -- the write happens as
root in :mod:`kidnix_parent_panel.helper` -- so every function in this module
takes text and returns text, which is what makes the whole format testable
without a filesystem or a privilege.

**Why the two TOML files are re-rendered whole and the env file is not.**
``tts.env`` is systemd ``EnvironmentFile`` syntax with about eighty lines of
measurements in it (why 0.25 and not 0.35; why pitch is not a knob), and the
only thing the panel changes is one path -- so it is edited **in place**, the
way ``kidnix_shell.settings.rewrite_pin`` edits the PIN, and every other line
survives byte for byte.

``parent.toml`` cannot be treated that way. Its own shipped comments run to
fourteen kilobytes and the panel changes structure, not just values: profiles
appear and disappear, tables move between ``[[profiles]]`` and
``[[retired_profiles]]``. An in-place editor for that is a TOML round-tripper,
which is a dependency this image does not have and a class of bug nobody wants
between a parent and their child's PIN. So the panel renders the file whole,
and the header it writes points at ``/usr/share/kidnix/parent.toml`` -- the
byte-identical shipped copy, still in the image, still carrying every word of
the reasoning, and *replaced by every upgrade* so it never goes stale. Nothing
is lost; it moves one path along, and the header says where.

Two things are carried across a re-render even though the panel does not edit
them: the PIN hash and salt (that is ``kidnix-set-pin``'s file too), and the
``[[next_after]]`` blocks (eight pictures a household may well have replaced
with their own -- ``parent.toml`` invites exactly that).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from . import model as M

ETC = Path("/etc/kidnix")
USR = Path("/usr/share/kidnix")

PARENT_TOML = "parent.toml"
SESSION_TOML = "session.toml"
TTS_ENV = "tts.env"

#: The env key ``tts.env`` uses for the voice model, and the only line in that
#: file the panel ever touches.
TTS_MODEL_KEY = "KIDNIX_PIPER_MODEL"


# --- TOML out -------------------------------------------------------------


def toml_str(value: Any) -> str:
    """Quote a string for TOML. Same rule as ``kidnix_shell.settings._toml_str``."""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def toml_list(values: Any) -> str:
    return "[" + ", ".join(toml_str(v) for v in values) + "]"


def _bool(value: bool) -> str:
    return "true" if value else "false"


PARENT_HEADER = """\
# kidnix parent config -- WRITTEN BY THE PARENT PANEL.
#
# Everything below was chosen in the kidnix parent panel (Applications ->
# Parent Panel on the grown-up's account) and written by the root helper
# /usr/bin/kidnix-config. You can still edit it by hand; the panel reads
# whatever it finds here the next time it opens.
#
# THE EXPLANATIONS ARE NOT GONE. This file used to carry about a hundred lines
# of reasoning -- why 450 ms, why "empty means all", what a badge is for. Every
# word of it is still on this machine, in the copy the image ships:
#
#     /usr/share/kidnix/parent.toml
#
# That copy is read-only, is replaced by every upgrade (so it never goes
# stale), and is what the shell falls back to if this file is ever lost. Read
# it there; change things here.
#
# The keys and their spellings are kidnix_shell.settings.ParentConfig.
"""

SESSION_HEADER = """\
# kidnix session policy -- WRITTEN BY THE PARENT PANEL.
#
# How long a sitting is and how it ends. Root-owned and read-only to the child
# on purpose: the machine ends the session, and the child cannot argue with it.
#
# The reasoning behind every number here -- why the ending windows are ceilings
# and not fixed points, why the floor exists, why the budget resets at 04:00 --
# is in the copy the image ships, which this file replaced:
#
#     /usr/share/kidnix/session.toml   (if present)
#     docs/design/parent-panel.md      (the panel's own reasoning)
#
# Read by kidnix_shell.session.load_policy(). Every key is optional and every
# unparseable value falls back to the built-in default with a warning: a broken
# config must never stop a child logging in.
"""


def render_parent_toml(panel: M.PanelModel) -> str:
    """The whole of ``parent.toml``, from the model."""
    out: list[str] = [PARENT_HEADER]

    if panel.pin_hash:
        out += [
            "# The grown-up PIN, PBKDF2-HMAC-SHA256 over 200000 rounds. Change it with",
            "# `sudo kidnix-set-pin`, or from the grown-up gate in the child's session;",
            "# the PIN itself is not stored and is not recoverable from these two lines.",
            f"pin_salt = {toml_str(panel.pin_salt)}",
            f"pin_hash = {toml_str(panel.pin_hash)}",
        ]
    else:
        out += [
            "# No pin_hash: the grown-up gate opens on 'choose a PIN' before anything",
            "# else in the sheet is reachable. Do this before the child touches it.",
        ]

    out += [
        "",
        f"default_session_minutes = {panel.time.length_minutes}",
        f"hover_dwell_ms = {panel.hover_dwell_ms}",
        "",
        "# Which activities Home lets a child open. AN EMPTY LIST MEANS ALL OF THEM,",
        "# never none -- unticking the last box must not leave a five-year-old looking",
        "# at a Home screen with nothing on it but 'All done'.",
    ]
    allowed = panel.machine_allow_list
    out.append(f"allowed_activity_ids = {toml_list(allowed)}")
    if panel.allow_list_is_shared:
        out += [
            "#",
            "# NOTE: this machine has more than one child and they were given different",
            "# lists. The shell reads ONE list, so the line above is the union of them;",
            "# each child's own list is written in their [[profiles]] block below and",
            "# will be honoured when the shell learns to read it. Age bands are already",
            "# per child, so the youngest still does not see the six-plus activities.",
        ]

    out += [
        "",
        "[access]",
        f"captions = {_bool(panel.sound.captions)}",
        f"calm = {_bool(panel.sound.calm)}",
        f"sound_volume = {round(panel.sound.sound_volume, 3)}",
        f"mute = {_bool(panel.sound.mute)}",
        "# Read-aloud pace, as a speech-dispatcher rate (-100..100). The shell asks",
        f"# for {M.DEFAULT_SPEECH_RATE} today; kidnix-piperd turns this into piper's length_scale",
        f"# (1.0 - rate/200 = {panel.sound.length_scale:.2f}). NOT READ BY THE SHELL YET --",
        "# docs/design/parent-panel.md section 7.3.",
        f"speech_rate = {panel.sound.speech_rate}",
        "",
        "# How fast Home grows. show_everything = true is 'keep the grid the same':",
        "# no new button appears on a schedule the child cannot perceive.",
        "[home]",
        f"initial_tiles = {panel.home.initial_tiles}",
        f"reveal_every_sessions = {panel.home.reveal_every_sessions}",
        f"show_everything = {_bool(panel.home.show_everything)}",
    ]

    for child in panel.children:
        if child.retired:
            continue
        out += ["", "[[profiles]]", *_profile_lines(child)]

    for child in panel.children:
        if not child.retired:
            continue
        out += [
            "",
            "# Removed from 'Who's here?' by the parent panel. NOTHING THIS CHILD MADE",
            "# HAS BEEN DELETED: their Journal is still at",
            f"#   ~/.local/share/kidnix/profiles/{child.id}/journal",
            "# Put the face back from the panel's Children tab, or delete the work for",
            "# good with `kidnix-wipe`.",
            "[[retired_profiles]]",
            *_profile_lines(child),
        ]

    for recipient in panel.family:
        out += [
            "",
            "# Someone a drawing or a letter could be sent to. DATA ONLY: nothing on",
            "# this machine sends anything anywhere yet.",
            "[[family]]",
            f"id = {toml_str(recipient.id)}",
            f"name = {toml_str(recipient.name)}",
            f"relation = {toml_str(recipient.relation)}",
            f"photo = {toml_str(recipient.photo)}",
        ]

    for option in panel.next_after:
        out += ["", "[[next_after]]"]
        for key in ("id", "label", "audio_label", "phrase", "icon"):
            if key in option and option[key] != "":
                out.append(f"{key} = {toml_str(option[key])}")

    return "\n".join(out).rstrip() + "\n"


def _profile_lines(child: M.Child) -> list[str]:
    return [
        f"id = {toml_str(child.id)}",
        f"name = {toml_str(child.name)}",
        f"colour_primary = {toml_str(child.colour_primary)}",
        f"colour_secondary = {toml_str(child.colour_secondary)}",
        f"avatar = {toml_str(child.avatar)}",
        f"badge = {toml_str(child.badge)}",
        f"age_band = {toml_str(child.age_band)}",
        f"skip_next_choice = {_bool(child.skip_next_choice)}",
        "# This child's own allow-list. Empty means everything their age band leaves.",
        "# Not read by the shell yet -- see allowed_activity_ids at the top.",
        f"allowed_activity_ids = {toml_list(child.allowed_activity_ids)}",
    ]


def render_session_toml(panel: M.PanelModel) -> str:
    """The whole of ``session.toml``, from the model."""
    time = panel.time
    out: list[str] = [
        SESSION_HEADER,
        f"length_minutes = {time.length_minutes}",
        f"daily_budget_minutes = {time.daily_budget_minutes}",
        "",
        "# THE SHORTEST SITTING THERE IS. Below this the shell does not start a",
        "# session at all and answers with a warm no at the door, rather than",
        "# beginning a sitting that opens inside its own ending. The floor on this",
        f"# floor is {M.ABSOLUTE_FLOOR_MINUTES} minutes.",
        f"min_session_minutes = {time.min_session_minutes}",
        "",
        "# THE ENDING RITUAL. Both numbers are CEILINGS, not fixed points: the real",
        "# windows are 20% and 10% of what was actually granted, clamped to 2-4 and",
        "# 1-2 minutes. Lower these to shorten the ending.",
        f"ending_offer_minutes = {time.ending_offer_minutes}",
        f"put_away_minutes = {time.put_away_minutes}",
        "",
        "# Outside this window the shell shows the Sleeping screen instead of starting",
        "# a session. Equal values switch bedtime off entirely.",
        f"bedtime_start = {toml_str(time.bedtime_start)}",
        f"bedtime_end = {toml_str(time.bedtime_end)}",
    ]

    if time.windows:
        out += [
            "",
            "# --- WHEN THE COMPUTER MAY BE USED AT ALL --------------------------------",
            "#",
            "# Weekday and weekend windows, set in the parent panel. Days are the first",
            "# three letters, lower case; times are 24-hour; a window whose end is at or",
            "# before its start runs past midnight into the next morning.",
            "#",
            "# **THE SHELL DOES NOT READ THIS YET.** It is valid TOML and load_policy()",
            "# ignores unknown keys, so writing it costs nothing today and means a",
            "# household that has already told the machine 'weekends after lunch' gets",
            "# it honoured by an upgrade rather than by setting everything up again.",
            "# The follow-up is specified in docs/design/parent-panel.md section 7.1:",
            "# Session.may_start gains a StartRefusal.OUT_OF_HOURS and the Resting",
            "# screen's 'when' reads the next window's start.",
            "#",
            "# Bedtime still applies on top of these, and the stricter of the two wins.",
        ]
        for window in time.windows:
            out += ["", "[[windows]]"]
            if window.label:
                out.append(f"label = {toml_str(window.label)}")
            out += [
                f"days = {toml_list(window.days)}",
                f"start = {toml_str(window.start)}",
                f"end = {toml_str(window.end)}",
            ]

    return "\n".join(out).rstrip() + "\n"


def render_tts_env(current: str, voice: str) -> str:
    """``tts.env`` with one line changed and every other byte kept.

    The file is systemd ``EnvironmentFile`` syntax, so the edit is textual and
    line-oriented: find ``KIDNIX_PIPER_MODEL=``, replace the value, leave the
    eighty lines of measurements around it exactly where they are. An unknown
    voice is refused by :mod:`validate` before it ever reaches here; a file with
    no such key at all gains one at the end rather than being rebuilt.
    """
    model = M.VOICE_MODELS.get(voice)
    if model is None:
        raise ValueError(f"unknown voice {voice!r}")
    lines = current.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith(f"{TTS_MODEL_KEY}=") and not replaced:
            lines[index] = f"{TTS_MODEL_KEY}={model}"
            replaced = True
    if not replaced:
        lines += ["", "# Set by the kidnix parent panel.", f"{TTS_MODEL_KEY}={model}"]
    return "\n".join(lines) + "\n"


def voice_from_tts_env(current: str) -> str:
    """Which of the two shipped voices ``tts.env`` names. Defaults to the big one."""
    match = re.search(rf"^{TTS_MODEL_KEY}=(.*)$", current, re.MULTILINE)
    if match is None:
        return "cori-high"
    path = match.group(1).strip()
    for name, known in M.VOICE_MODELS.items():
        if path == known:
            return name
    # A hand-picked model we do not ship. Naming it "cori-high" would be a lie
    # the parent could not see, so fall back on the filename's own stem.
    stem = Path(path).stem.replace("en_GB-", "")
    return stem if stem in M.VOICE_MODELS else "cori-high"


# --- TOML in --------------------------------------------------------------


def payload_from_toml(parent_text: str, session_text: str, tts_text: str = "") -> dict[str, Any]:
    """Turn what is on disk into the payload shape :class:`PanelModel` reads.

    Tolerant by design and never raising on content: a machine whose
    ``session.toml`` a parent broke with a text editor must still open the
    panel, showing the defaults, so that the panel is the way back rather than
    one more thing that will not start.
    """
    parent = _load(parent_text)
    session = _load(session_text)
    return {
        "schema": 1,
        "parent": parent,
        "session": session,
        "tts": {"voice": voice_from_tts_env(tts_text)} if tts_text else {},
    }


def _load(text: str) -> dict[str, Any]:
    try:
        return tomllib.loads(text)
    except (tomllib.TOMLDecodeError, ValueError):
        return {}


def read_files(etc: Path = ETC, usr: Path = USR) -> tuple[str, str, str]:
    """``(parent.toml, session.toml, tts.env)`` as text, ``/etc`` then ``/usr``.

    Same search order as ``kidnix_shell.settings.CONFIG_SEARCH_PATH``: the
    machine's copy first, the image's shipped copy as the fallback, and empty
    text if the machine has neither -- which the panel renders as the defaults
    rather than as an error, because a first run is not a failure.
    """
    out: list[str] = []
    for name in (PARENT_TOML, SESSION_TOML, TTS_ENV):
        text = ""
        for directory in (etc, usr):
            candidate = directory / name
            try:
                if candidate.is_file():
                    text = candidate.read_text(encoding="utf-8")
                    break
            except OSError:
                continue
        out.append(text)
    return out[0], out[1], out[2]


def load_model(etc: Path = ETC, usr: Path = USR) -> M.PanelModel:
    """What the panel opens with."""
    parent_text, session_text, tts_text = read_files(etc, usr)
    return M.PanelModel.from_payload(payload_from_toml(parent_text, session_text, tts_text))


__all__ = [
    "ETC",
    "PARENT_TOML",
    "SESSION_TOML",
    "TTS_ENV",
    "TTS_MODEL_KEY",
    "USR",
    "load_model",
    "payload_from_toml",
    "read_files",
    "render_parent_toml",
    "render_session_toml",
    "render_tts_env",
    "toml_list",
    "toml_str",
    "voice_from_tts_env",
]
