"""hello_draw -- the smallest activity that is actually correct.

One big button. Pressing it makes a coloured square, keeps it in the Journal
with a caption, and says so. That is the whole thing, and it is deliberately
the whole thing: what it demonstrates is not drawing but the four obligations
every activity has and every first draft forgets --

1. sizes come from :class:`~kidnix_activity.metrics.ContentArea` (millimetres,
   floored), not from pixels somebody liked the look of;
2. every control speaks, and every spoken line is captioned;
3. the work is written into the child's own Journal with
   :func:`~kidnix_activity.journal.save_entry`, not into a scratch directory
   for the shell to notice later;
4. SIGTERM saves and exits. There is no quit dialogue and no "are you sure?".

The PNG is generated in pure Python (:mod:`kidnix_activity.examples.
hello_draw.picture`) so that the example has no image dependency and its tests
are ordinary headless tests.
"""

from __future__ import annotations

__version__ = "0.1.0"

ACTIVITY_ID = "hello-draw"
TITLE = "Hello draw"
