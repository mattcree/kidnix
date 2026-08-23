"""The GTK half. Everything that needs a display lives under here.

Nothing in :mod:`kidnix_parent_panel` outside this package imports ``gi``, which
is what lets the model, the validator, the renderer and the root helper be
tested on a machine with no GTK and run in a build container with no display.

**Adult typography, on purpose.** The child's shell has an 18 pt floor, 20 mm
targets, hover-to-speak and no digits anywhere. None of that belongs here. This
is a libadwaita preferences app on the parent's stock GNOME session (ADR-0005):
default font size, default row heights, real numbers in real spin buttons, and
the GNOME conventions a parent already knows from Settings. The one thing it
borrows from the child's side is the *identity colours*, and only where they
say whose child a row is about.
"""

from __future__ import annotations

__all__ = ["run"]


def run(argv: list[str] | None = None) -> int:
    """Start the application. Imported lazily so ``--version`` needs no display."""
    from .app import ParentPanelApplication

    return ParentPanelApplication().run(argv or [])
