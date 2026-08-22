"""The shell's surfaces, S1-S9 (spec section 2).

Each screen is a plain ``Gtk.Box`` that lays itself out from
:class:`~kidnix_shell.context.ShellContext` and calls the host for anything
that changes state. Screens never own policy.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..context import ShellContext  # noqa: E402


class Screen(Gtk.Box):
    """Base surface: a vertical box that fills the area under the band."""

    #: Stack name, also the accessible name of the surface.
    name = "screen"
    #: Spoken once when the child arrives here. Empty means "say nothing".
    intro = ""

    def __init__(self, ctx: ShellContext) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=ctx.metrics.gap)
        self.ctx = ctx
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.add_css_class("surface")
        self.update_property([Gtk.AccessibleProperty.LABEL], [self.name])
        self.build()

    def build(self) -> None:
        """Construct the widgets. Called once, from ``__init__``."""

    def on_enter(self) -> None:
        """The child just arrived. Refresh anything stale and speak the intro."""
        if self.intro:
            self.ctx.speech.speak(self.intro)

    def on_leave(self) -> None:
        """The child just left."""


__all__ = ["Screen", "ShellContext"]
