"""The compositor's half of the band: gnome-kiosk's ``window-config.ini``.

The band stays on screen during an activity because gnome-kiosk is told where
to put windows, not because the shell fights for the top of the stack. All the
evidence is in ``docs/spikes/band-over-activity.md``; this module is the part
of it that runs. Nothing here imports GTK, so every rule below is tested
headless.

Four rules from the spike decide the whole design, and each one is why a line
here looks the way it does:

**R1 — the config is resolved once, at compositor start, and gnome-kiosk arms
its file monitor only if the user's file already existed.**
``kiosk_window_config_load()`` runs at construction and
``setup_file_monitoring()`` returns early when ``user_config_file_path`` is
``NULL``. A ``window-config.ini`` created *after* gnome-kiosk is running is
never seen, however often it is rewritten. So ``/usr/bin/kidnix-shell`` — which
runs before ``gnome-session``, and therefore before the compositor — installs
:data:`SEED` into ``$HOME/.config/gnome-kiosk/window-config.ini`` on every
login. Once that file exists at start-up, every subsequent write *is* picked up
live.

**R2 — geometry is applied only while a window is "initial", during its first
configure.** ``set-x/-y/-width/-height``, ``set-fullscreen`` and
``lock-on-area`` are consumed inside ``apply_initial_config()``'s
``kiosk_window_config_is_initial()`` branch. A section that only starts matching
later has its geometry read and discarded.

**R3 — at that first configure a window's identity may not exist yet, and
whether it does is toolkit-dependent.** GTK4 sets ``app_id`` before its first
configure; SDL2 (Tux Paint) does not, so ``match-class`` cannot place it. **Only
a catch-all section is guaranteed to match early enough to place any window**,
which is why nothing here ever matches an activity by name.

**R4 — ``set-above`` is exempt from R2 and is one-way.** It is applied on every
pass, so matching the band by *title* works for it; and gnome-kiosk only ever
calls ``meta_window_make_above()``, never ``unmake_above()``, so a later
``set-above=false`` cannot lower a window that is already raised.

R2 + R3 mean one static file cannot say "the band at the top, everything else
below": there is no negation syntax and the catch-all would drag the band down
too. So the catch-all is **sequenced in time** instead of by name, exactly once
per shell start-up:

======================= ================================ =======================
When                    File in place                    What the catch-all says
======================= ================================ =======================
before the band window  :data:`BAND_PHASE` (phase A)     the band strip
after the band is mapped :data:`ACTIVITY_PHASE` (phase B) everything below it
======================= ================================ =======================

The band window's initial configure is consumed under phase A, so phase B's
``lock-on-area`` never reaches it (R2), and phase B's ``set-above=false`` cannot
lower it (R4). Every window created afterwards — the content window and every
activity of the session — lands below the band. There is exactly one transition,
and it is not per-activity.

**Geometry is absolute pixels only.** ``CONFIG.md`` (shipped in the image at
``/usr/share/doc/gnome-kiosk/CONFIG.md``) types ``set-x``/``set-y``/
``set-width``/``set-height`` as integers and ``lock-on-area`` as the literal
format ``"x,y WxH"``. There are no percentages and no monitor-relative form
except ``set-on-monitor`` + ``lock-on-monitor-area``, which needs a monitor
*name* the session wrapper cannot know either. That is why the seed carries no
geometry at all (see :data:`SEED`) and why the real numbers can only be written
by the shell, which is the first thing in the session that can measure a
monitor.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

#: The two toplevels' titles. gnome-kiosk matches on these with
#: ``g_pattern_match_simple``, so they must not contain ``*`` or ``?``. They are
#: also the only thing that distinguishes the two windows to the compositor:
#: both are the same process and the same ``app_id`` (``org.kidnix.Shell``),
#: because two processes sharing a ``GtkApplication`` id do not get two windows.
BAND_TITLE = "kidnix-band"
CONTENT_TITLE = "kidnix-content"

#: Where the rendered file goes, under ``$XDG_CONFIG_HOME``.
CONFIG_RELATIVE = Path("gnome-kiosk") / "window-config.ini"

#: Where the image keeps the shipped copies of the three files below.
SHIPPED_DIR = Path("/usr/share/kidnix/kiosk")

_TOKEN_RE = re.compile(r"@[A-Z_]+@")


# --------------------------------------------------------------------------- #
# The three files. `system_files/usr/share/kidnix/kiosk/*.ini` are byte-for-byte
# these strings; `tests/test_kiosk.py` asserts that, so the copy the session
# wrapper installs and the copy the shell writes can never drift apart.
# --------------------------------------------------------------------------- #

SEED = """\
# kidnix: the seed, installed by /usr/bin/kidnix-shell BEFORE gnome-session.
#
# THIS FILE EXISTS SO THAT IT EXISTS. gnome-kiosk resolves the user config path
# once, at compositor start-up, and arms its GFileMonitor only if the user's
# file was already there (kiosk-window-config.c, setup_file_monitoring()
# returns early when user_config_file_path is NULL). A window-config.ini
# created afterwards is never noticed, however many times it is rewritten --
# this cost the spike its first three runs. See
# docs/spikes/band-over-activity.md rule R1.
#
# IT DELIBERATELY CARRIES NO GEOMETRY. The wrapper runs before the compositor,
# so it cannot know the panel's size, and gnome-kiosk's geometry keys are
# absolute pixels with no percentage or monitor-relative form. Guessing would
# be worse than saying nothing: if the shell then failed to start, a guessed
# catch-all would squeeze every activity into a strip nobody can use, whereas
# this file leaves gnome-kiosk's own defaults alone and the session behaves
# exactly as it did before the band existed. The shell overwrites this with
# measured numbers within a second of starting.
#
# The wrapper rewrites it on every login, which matters: the file left behind
# by the previous session is phase B, and a band window created against phase B
# would be placed *below* itself.

[band]
match-title=kidnix-band
set-above=true
"""

BAND_PHASE = """\
# kidnix: phase A -- the band is about to be created.
#
# Written by the shell immediately before it creates the band window, and
# replaced by the phase B file as soon as that window is mapped.
# See ./README.md and docs/spikes/band-over-activity.md.
#
# The catch-all is load-bearing: gnome-kiosk only honours geometry while a
# window is still "initial" (its first configure), and at that moment a Wayland
# toplevel has no app_id, so a `match-class` section is too late to place it.

[all]
set-fullscreen=false
set-x=0
set-y=0
set-width=@WIDTH@
set-height=@BAND_HEIGHT@
lock-on-area=0,0 @WIDTH@x@BAND_HEIGHT@

# Keeps the band above a fullscreen-sized activity. `set-above` is applied on
# every pass, not only the initial one, so matching on title works here even
# though matching on title would NOT work for geometry above.
[band]
match-title=kidnix-band
set-above=true
"""

ACTIVITY_PHASE = """\
# kidnix: phase B -- everything from here on lives below the band.
#
# Written by the shell once the band window is mapped, and left in place for the
# rest of the session. The shell's own content window and every activity
# launched afterwards are placed and locked into the area below the band.
# See ./README.md and docs/spikes/band-over-activity.md.

[all]
set-fullscreen=false
set-x=0
set-y=@BAND_HEIGHT@
set-width=@WIDTH@
set-height=@CONTENT_HEIGHT@
set-above=false
# `lock-on-area` is a real constraint, not just an initial placement: it is what
# stops an activity taking the whole screen back when it asks to be fullscreen.
# It is still installed only at a window's first configure, which is why the
# band -- created and configured under phase A -- never gets this one.
lock-on-area=0,@BAND_HEIGHT@ @WIDTH@x@CONTENT_HEIGHT@

# The band was already raised under phase A and stays raised: gnome-kiosk only
# ever calls meta_window_make_above(), never unmake_above, so `set-above=false`
# above cannot lower it. Repeated here so a shell restart re-raises it.
[band]
match-title=kidnix-band
set-above=true
"""


class GeometryError(ValueError):
    """The numbers do not describe a screen with a band on it."""


#: How far a window's allocation may be from what we asked for and still count
#: as "the compositor placed it". Non-zero because a fractional scale or a
#: shadow can cost a pixel, and small because the failure this catches is off
#: by hundreds (the band landing in the *content* rectangle).
PLACEMENT_TOLERANCE_PX = 2


def placed(width: int, height: int, want_width: int, want_height: int) -> bool:
    """Did the compositor actually give this window the rectangle we asked for?

    This is the check that had to exist. v0.1.5's first cut trusted GTK's
    ``map`` signal as "the band has its strip", and ``map`` is far too early:
    it fires when GTK maps the widget, *before* the compositor has answered
    with the toplevel's initial configure. So the shell wrote phase B into the
    window a few microseconds later, gnome-kiosk's file monitor coalesced the
    whole burst, and the only content it ever read was phase B -- which placed
    the band in the content rectangle, above everything, with the content
    window invisible underneath it. Measured in the VM: the band came up
    1280x708 when it had asked for 1280x92.

    A window's *allocation* is the honest signal, because it is the compositor's
    own answer. ``width``/``height`` of 0 mean "no configure yet", which is not
    a failure, just "not yet" -- the caller keeps waiting.
    """
    if width <= 0 or height <= 0:
        return False
    if want_height <= 0:
        return False
    if abs(height - want_height) > PLACEMENT_TOLERANCE_PX:
        return False
    return want_width <= 0 or abs(width - want_width) <= PLACEMENT_TOLERANCE_PX


def render(template: str, *, width: int, height: int, band_height: int) -> str:
    """Fill a template's ``@TOKENS@`` from a measured monitor.

    Raises :class:`GeometryError` if the numbers cannot describe a band with a
    content area under it, and :class:`ValueError` if any token is left over --
    an unreplaced ``@WIDTH@`` would be silently ignored by gnome-kiosk's ini
    parser and the failure would only show up as a window in the wrong place.
    """
    if width <= 0 or height <= 0:
        raise GeometryError(f"no monitor to write a window config for ({width}x{height})")
    if band_height <= 0 or band_height >= height:
        raise GeometryError(f"a {band_height} px band does not fit a {height} px screen")

    text = (
        template.replace("@WIDTH@", str(width))
        .replace("@HEIGHT@", str(height))
        .replace("@BAND_HEIGHT@", str(band_height))
        .replace("@CONTENT_HEIGHT@", str(height - band_height))
    )
    leftover = _TOKEN_RE.search(text)
    if leftover is not None:
        raise ValueError(f"window-config template has an unknown token {leftover.group(0)}")
    return text


def config_path(config_home: Path) -> Path:
    """``$XDG_CONFIG_HOME/gnome-kiosk/window-config.ini``."""
    return config_home / CONFIG_RELATIVE


class WindowConfig:
    """Writes the file gnome-kiosk watches, in the two phases R2 forces.

    Every method returns ``True`` if the file on disk changed. Writing the same
    bytes twice is skipped on purpose: gnome-kiosk reloads on every
    ``G_FILE_MONITOR_EVENT_CHANGED``, and a reload that changes nothing is a
    reload that can only cost us a race.
    """

    def __init__(self, config_home: Path) -> None:
        self.path = config_path(config_home)
        #: The last geometry written, for the log line and for tests.
        self.written: tuple[int, int, int] | None = None
        self.phase: str | None = None

    # -- the two phases --

    def band_phase(self, width: int, height: int, band_height: int) -> bool:
        """Phase A: the catch-all *is* the band strip. Write before creating it."""
        return self._write("band", BAND_PHASE, width, height, band_height)

    def activity_phase(self, width: int, height: int, band_height: int) -> bool:
        """Phase B: the catch-all is everything below the band. Write after it maps."""
        return self._write("activity", ACTIVITY_PHASE, width, height, band_height)

    def seed(self) -> bool:
        """Install the geometry-free seed. The session wrapper's job; here for tests."""
        return self._write_text("seed", SEED)

    # -- plumbing --

    def _write(self, phase: str, template: str, width: int, height: int, band: int) -> bool:
        try:
            text = render(template, width=width, height=height, band_height=band)
        except GeometryError as exc:
            # Headless, or a monitor we could not measure. Leaving the seed in
            # place is the safe answer: no geometry at all beats wrong geometry.
            log.info("not writing a window config: %s", exc)
            return False
        changed = self._write_text(phase, text)
        self.written = (width, height, band)
        return changed

    def _write_text(self, phase: str, text: str) -> bool:
        self.phase = phase
        try:
            if self.path.is_file() and self.path.read_text(encoding="utf-8") == text:
                log.debug("window config already says phase %s", phase)
                return False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(text, encoding="utf-8")
        except OSError as exc:  # pragma: no cover - a read-only or full home
            # Not fatal. The band simply will not be placed, which is v0.1.4's
            # behaviour, and a child gets a working computer either way.
            log.warning("could not write %s: %s", self.path, exc)
            return False
        log.info("wrote %s (phase %s)", self.path, phase)
        return True

    def describe(self) -> str:
        if self.written is None:
            return f"{self.path} (nothing written)"
        width, height, band = self.written
        return (
            f"{self.path}: phase {self.phase}, band 0,0 {width}x{band}, "
            f"content 0,{band} {width}x{height - band}"
        )
