"""The environment the shell hands an activity, read once.

:meth:`kidnix_shell.launcher.build_env` gives a child's process a deliberately
small environment: an allow-list of display/bus variables, XDG directories
under the kid home, ``no_proxy=*`` (SYNTHESIS H1: the child session has no
egress) and two variables of our own.

============================ =================================================
``KIDNIX_ACTIVITY_ID``       the manifest ``id`` this process was launched as
``KIDNIX_PROFILE_ID``        **which child is sitting there**
============================ =================================================

The profile id is the one that matters here and it is new (2026-08-23). Every
child's things live under ``$XDG_DATA_HOME/kidnix/profiles/<id>/`` since the
shell stopped sharing one Journal between siblings, and an activity that wrote
into ``kidnix/journal`` -- the pre-profiles spelling -- would put one child's
drawing into a directory the shell no longer reads. So the shell exports which
profile is active and we ask :class:`kidnix_shell.settings.Paths` for the
spelling rather than composing a path ourselves.

**Nothing here guesses.** An activity started by hand from a terminal has no
``KIDNIX_ACTIVITY_ID``; :attr:`LaunchEnv.launched_by_shell` is False, the
Journal writer refuses rather than inventing an id, and the developer gets a
sentence saying which variable to set. A wrong id is a card in My Things that
resumes the wrong program.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from kidnix_shell.settings import Paths

#: The manifest id, exported by the launcher since v0.1.0.
ACTIVITY_ID_VAR = "KIDNIX_ACTIVITY_ID"
#: Which child. Exported by the launcher since 2026-08-23 -- see the module
#: docstring, and ``docs/design/activity-sdk.md`` section 3.
PROFILE_ID_VAR = "KIDNIX_PROFILE_ID"

#: Where the shell's caption listener lives, under ``$XDG_RUNTIME_DIR``.
RUNTIME_SUBDIR = "kidnix"


@dataclass(frozen=True)
class LaunchEnv:
    """What this process was told about the machine it is running on."""

    activity_id: str
    profile_id: str
    paths: Paths
    runtime_dir: Path | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LaunchEnv:
        """Read the environment. Never raises, never guesses a missing id."""
        environ = dict(os.environ if env is None else env)
        activity_id = environ.get(ACTIVITY_ID_VAR, "").strip()
        profile_id = environ.get(PROFILE_ID_VAR, "").strip()
        paths = Paths.from_env(environ)
        return cls(
            activity_id=activity_id,
            profile_id=profile_id,
            # ``for_profile("")`` is the legacy, pre-profiles layout, which is
            # exactly the right answer on a machine that has never had
            # profiles -- and the only one we are entitled to when the shell
            # did not say.
            paths=paths.for_profile(profile_id),
            runtime_dir=paths.runtime_dir,
        )

    @property
    def launched_by_shell(self) -> bool:
        """Did the kidnix shell start this process?

        The activity id is the tell: it is set by the launcher and by nothing
        else. A developer running ``python -m my_activity`` from a terminal is
        not the shell and should be told so rather than quietly writing into
        somebody's Journal under an empty id.
        """
        return bool(self.activity_id)

    @property
    def journal_root(self) -> Path:
        """``$XDG_DATA_HOME/kidnix/profiles/<id>/journal`` -- this child's."""
        return self.paths.journal_root

    @property
    def runtime_root(self) -> Path | None:
        """``$XDG_RUNTIME_DIR/kidnix``, or ``None`` when there is no runtime dir."""
        return None if self.runtime_dir is None else self.runtime_dir / RUNTIME_SUBDIR

    def describe(self) -> str:
        """One line for the log, so a failed launch says what it was given."""
        return (
            f"activity={self.activity_id or '(unset)'} "
            f"profile={self.profile_id or '(none)'} "
            f"journal={self.journal_root} "
            f"runtime={self.runtime_root or '(none)'}"
        )
