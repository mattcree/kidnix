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

from ..labels import text_width_px  # noqa: E402
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
        # One gap, not two, above and below the faces. Who's here is the
        # tallest surface in the shell on a dense panel -- a 30 mm face floor,
        # a 20 mm corner tile and a 40 pt headline are all floors that cannot
        # be traded -- so its *dead space* is what gives way, and 8 mm is still
        # 08 section 3.1c's floor. Spending it here rather than in `fit` is
        # what keeps Home's 40 mm tile at 118 dpi.
        title.set_margin_bottom(metrics.gap)
        self.append(title)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap * 2)
        row.set_halign(Gtk.Align.CENTER)
        for profile in self.ctx.config.profiles:
            row.append(self._avatar(profile))
        self.append(row)

        # The grown-up tile is plain on purpose: it must not look like a
        # tempting choice next to a child's own face -- and it is **not
        # voiced** (spec 7b, SYNTHESIS G2). No ``speech_ui``, so it says
        # nothing on hover, on focus or on activation; ``ChildButton`` still
        # sets the accessible name, so an assistive technology can find it.
        corner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        corner.set_halign(Gtk.Align.END)
        corner.set_valign(Gtk.Align.END)
        corner.set_vexpand(True)
        corner.set_margin_top(metrics.gap)
        grownup = ChildButton(
            speak_text="Grown-up",
            on_activate=self.ctx.host.open_grownup,
            width=metrics.target_mm(40),
            height=metrics.min_target,
        )
        grownup.set_child(Gtk.Label(label="Grown-up"))
        corner.append(grownup)
        self.append(corner)

    def _avatar(self, profile: Profile) -> Gtk.Widget:
        metrics = self.ctx.metrics
        size = metrics.avatar_size

        # **A child's own name is the last thing in this shell that may be cut**
        # (SYNTHESIS B4), and on a panel whose chrome has been spent the face
        # falls to its 30 mm floor -- 93 px of label, which "Bartholomew" does
        # not fit on one line at the 18 pt floor. Every other label in the
        # shell is inside a grid and has to keep its column's width; this one
        # is not, so the tile is allowed to be wider than it is tall rather
        # than break a name between characters.
        longest = max(
            (text_width_px(word, metrics.label_floor_pt) for word in profile.name.split()),
            default=0,
        )
        width = max(size, longest + TILE_CHROME_X_PX)

        button = ChildButton(
            speak_text=profile.speak_text,
            on_activate=partial(self.ctx.host.choose_profile, profile),
            speech_ui=self.ctx.speech_ui,
            css_classes=("tile",),
            width=width,
            height=size,
            key=next_key(f"profile-{profile.id}"),
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)

        # **Colour is whose it is; so is shape** (accessibility review M2).
        # The band tint is the only per-child signal after S1, and the old
        # palette's green and rust simulated to the same colour under
        # deuteranopia -- so identity gets a silhouette as well, in the corner
        # of the child's own face where they meet it first. ~8% of boys are
        # colour-blind and about 40% leave school not knowing it.
        face = Gtk.Overlay()
        face.set_child(icon_image(profile.avatar, "icon-name", int(size * 0.55), "kidnix-child"))
        badge = icon_image(f"kidnix-badge-{profile.badge}", "icon-name", max(24, int(size * 0.22)))
        badge.set_halign(Gtk.Align.END)
        badge.set_valign(Gtk.Align.START)
        badge.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
        face.add_overlay(badge)
        box.append(face)
        # A child's own name is the last thing in this shell that may be cut
        # short: it wraps and shrinks like every other label (SYNTHESIS B4).
        label = Gtk.Label()
        label.add_css_class("tile-label")
        fit_gtk_label(
            label,
            profile.name,
            width=max(1, width - TILE_CHROME_X_PX),
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=metrics.tile_label_height,
        )
        box.append(label)
        button.set_child(box)
        return button
