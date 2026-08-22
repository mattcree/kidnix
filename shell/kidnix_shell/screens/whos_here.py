"""S1 -- Who's here?

Avatar tiles >= 30 mm in each child's own colours, name spoken on focus, plus a
deliberately plain Grown-up tile in the bottom-right corner.

v0.1 ships one profile. The screen is written for N because the data model is
(spec section 1.7) and because "colour = whose it is" is how multi-child
switching is meant to work later (08 section 4.4).
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..metrics import TILE_CHROME_X_PX  # noqa: E402
from ..settings import Profile  # noqa: E402
from ..widgets import ChildButton, big_label, fit_gtk_label, icon_image, next_key  # noqa: E402
from . import Screen  # noqa: E402


class WhosHereScreen(Screen):
    name = "Who's here?"
    intro = "Who's here?"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_valign(Gtk.Align.CENTER)
        # Nothing sits flush against the edge of the panel: on the first real
        # boot the Grown-up tile ran off the bottom-right corner.
        self.set_margin_start(metrics.gap)
        self.set_margin_end(metrics.gap)
        self.set_margin_bottom(metrics.gap)

        title = big_label("Who's here?", "screen-title")
        title.set_margin_bottom(metrics.gap * 2)
        self.append(title)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap * 2)
        row.set_halign(Gtk.Align.CENTER)
        for profile in self.ctx.config.profiles:
            row.append(self._avatar(profile))
        self.append(row)

        # The grown-up tile is plain on purpose: it must not look like a
        # tempting choice next to a child's own face.
        corner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        corner.set_halign(Gtk.Align.END)
        corner.set_valign(Gtk.Align.END)
        corner.set_vexpand(True)
        corner.set_margin_top(metrics.gap * 2)
        grownup = ChildButton(
            speak_text="Grown-up",
            on_activate=self.ctx.host.open_grownup,
            speech_ui=self.ctx.speech_ui,
            width=metrics.target_mm(40),
            height=metrics.min_target,
        )
        grownup.set_child(Gtk.Label(label="Grown-up"))
        corner.append(grownup)
        self.append(corner)

    def _avatar(self, profile: Profile) -> Gtk.Widget:
        metrics = self.ctx.metrics
        size = metrics.avatar_size

        button = ChildButton(
            speak_text=profile.speak_text,
            on_activate=partial(self.ctx.host.choose_profile, profile),
            speech_ui=self.ctx.speech_ui,
            css_classes=("tile",),
            size=size,
            key=next_key(f"profile-{profile.id}"),
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)
        box.append(icon_image(profile.avatar, "icon-name", int(size * 0.55), "kidnix-child"))
        # A child's own name is the last thing in this shell that may be cut
        # short: it wraps and shrinks like every other label (SYNTHESIS B4).
        label = Gtk.Label()
        label.add_css_class("tile-label")
        fit_gtk_label(
            label,
            profile.name,
            width=max(1, size - TILE_CHROME_X_PX),
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=metrics.tile_label_height,
        )
        box.append(label)
        button.set_child(box)
        return button
