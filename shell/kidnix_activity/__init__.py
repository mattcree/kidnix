"""kidnix activity SDK -- what a first-party activity is built from.

An activity is a **separate program** (SUITE section 2). The shell owns launch,
the band, the session, read-aloud of *its own* chrome and the Journal's shelf;
the activity owns one window and everything in it. This package is the part of
the shell a well-behaved activity is allowed to borrow, so that Sounds & Words,
Clock, Numbers, Letters to family and Listen all feel like the same machine
without each of them re-deriving 20 mm from first principles.

Module map -- the pure half first, because that is the half that is provable
without a display and therefore the half that carries the contract:

  Pure logic (no GTK, unit-tested headless)
    env         the launch environment the shell hands us (KIDNIX_* + XDG)
    lifecycle   SIGTERM -> ``on_finish()`` -> exit. There is no quit dialogue.
    captions    the caption IPC client (a datagram to the shell's socket)
    metrics     :class:`~kidnix_activity.metrics.ContentArea` -- mm sizing for
                the rectangle *below* the band, which is all we are given
    journal     ``save_entry()``: write into the child's Journal directly
    manifest    validate a manifest, and the template a new one starts from
    scaffold    what ``kidnix-activity new`` writes
    speech      one voice: speech-dispatcher plus the caption hook

  GTK
    app         :class:`~kidnix_activity.app.ActivityApplication`
    widgets     BigButton, PictureTile, Prompt, GrownUpTurn
    keyboard    the focus ring (Escape is the **shell's**, never ours)

The contract, the lifecycle and the rules an activity may not break are in
``docs/design/activity-sdk.md``. The two shortest ones: **no network**, and
**never a quit dialogue** -- a first-party activity is ``quit = "signal"`` and
saves on SIGTERM, because a five-year-old at put-away time cannot be asked a
question they have to read.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "ACTIVITY_ID_VAR",
    "PROFILE_ID_VAR",
    "ContentArea",
    "FinishHandler",
    "LaunchEnv",
    "__version__",
    "save_entry",
]

from .env import ACTIVITY_ID_VAR, PROFILE_ID_VAR, LaunchEnv
from .journal import save_entry
from .lifecycle import FinishHandler
from .metrics import ContentArea
