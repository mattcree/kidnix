"""S8 -- Sleeping.

Dim, warm, quiet. A sleeping moon, no controls, nothing to press. Touching
anywhere says "kidnix is sleeping. Ask a grown-up." The only way out is the
session becoming allowed again, or the grown-up gate in the band.

This is the one state with no visible way back to Home, and that is the point
(spec section 2).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..widgets import big_label, icon_image  # noqa: E402
from . import Screen  # noqa: E402

SLEEPING_LINE = "kidnix is sleeping. Ask a grown-up."


class SleepingScreen(Screen):
    name = "Sleeping"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.add_css_class("sleeping")
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_spacing(metrics.gap * 2)

        moon = icon_image("kidnix-moon", "icon-name", metrics.mm(45))
        moon.set_halign(Gtk.Align.CENTER)
        self.append(moon)
        self.append(big_label("Sleeping"))

        # The whole surface answers, so a child pressing anywhere gets a reply
        # rather than a screen that appears broken.
        click = Gtk.GestureClick.new()
        click.set_button(0)
        click.connect("pressed", lambda g, n, x, y: self.ctx.speech.speak(SLEEPING_LINE))
        self.add_controller(click)

    def on_enter(self) -> None:
        self.ctx.speech.speak(SLEEPING_LINE)
