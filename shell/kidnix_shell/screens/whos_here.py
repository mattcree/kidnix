"""S1 -- Who's here?

Avatar tiles >= 30 mm in each child's own colours, name spoken on focus, plus a
deliberately plain Grown-up tile in the bottom-right corner.

v0.1 ships one profile. The screen is written for N because the data model is
(spec section 1.7) and because "colour = whose it is" is how multi-child
switching is meant to work later (08 section 4.4).

**A face whose sitting is over is still a face** (ADR-0014). Resting moved
from the machine to the profile, so this screen is where a household with two
children meets it: the child who has just pressed "All done" gets their own
face back, dimmed, with the reason attached to it, while their sibling's is
untouched. It is dimmed and not removed, not greyed out and not disabled --

* **removed** would be the worst of the three: a five-year-old navigates by
  position, and a face that is not there is a machine that has forgotten them;
* it keeps its size (>= 30 mm), its focus ring and its voice, and hover says
  the name **and** the reason, so the answer is available before the press;
* the press is answered out loud and **stays here**. No state change, no
  Resting screen: the machine is not resting, this child is, and the machine
  saying otherwise in front of a sibling who may still start would be a lie
  the sibling can disprove by pressing their own face.
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..i18n import N_, _  # noqa: E402
from ..labels import text_width_px  # noqa: E402
from ..metrics import TILE_CHROME_X_PX  # noqa: E402
from ..settings import Profile  # noqa: E402
from ..widgets import ChildButton, big_label, fit_gtk_label, icon_image, next_key  # noqa: E402
from . import Screen  # noqa: E402

#: The headline, and the plain corner tile. Both msgids: they are read at
#: build time, which is after the language is chosen.
WHOS_HERE_TITLE = N_("Who's here?")
GROWNUP_TILE = N_("Grown-up")


class WhosHereScreen(Screen):
    name = N_("Who's here?")
    intro = N_("Who's here?")

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_valign(Gtk.Align.CENTER)
        # Nothing sits flush against the edge of the panel: on the first real
        # boot the Grown-up tile ran off the bottom-right corner.
        self.set_margin_start(metrics.gap)
        self.set_margin_end(metrics.gap)
        self.set_margin_bottom(metrics.gap)

        title = big_label(_(WHOS_HERE_TITLE), "screen-title")
        # One gap, not two, above and below the faces. Who's here is the
        # tallest surface in the shell on a dense panel -- a 30 mm face floor,
        # a 20 mm corner tile and a 40 pt headline are all floors that cannot
        # be traded -- so its *dead space* is what gives way, and 8 mm is still
        # 08 section 3.1c's floor. Spending it here rather than in `fit` is
        # what keeps Home's 40 mm tile at 118 dpi.
        title.set_margin_bottom(metrics.gap)
        self.append(title)

        self._row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap * 2)
        self._row.set_halign(Gtk.Align.CENTER)
        self._faces: list[Gtk.Widget] = []
        self._fill_faces()
        self.append(self._row)

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
            speak_text=_(GROWNUP_TILE),
            on_activate=self.ctx.host.open_grownup,
            width=metrics.target_mm(40),
            height=metrics.min_target,
        )
        grownup.set_child(Gtk.Label(label=_(GROWNUP_TILE)))
        corner.append(grownup)
        self.append(corner)

    def _fill_faces(self) -> None:
        """Draw the row of faces for *now* (ADR-0014).

        Whether a face is resting is a fact about this minute, not about when
        the screen was constructed -- and this screen is constructed once and
        then arrived at again and again, including the arrival straight after
        a sibling's Goodbye, which is the whole case the ADR exists for. So the
        row is rebuilt on every :meth:`on_enter`.

        The old buttons are unregistered on the way out: the read-aloud ring
        is put on a widget looked up by key, and a registry pointing at a
        button that is no longer in the tree is a ring nobody sees.
        """
        for face in self._faces:
            key = getattr(face, "key", "")
            if key:
                self.ctx.speech_ui.unregister(key)
            self._row.remove(face)
        self._faces = [self._avatar(profile) for profile in self.ctx.config.profiles]
        for face in self._faces:
            self._row.append(face)

    def on_enter(self) -> None:
        self._fill_faces()
        super().on_enter()

    def _resting_line(self, profile: Profile) -> str:
        """Why this child cannot start, in the Resting screen's own words, or ``""``.

        Asked of the host rather than computed here, because the answer needs
        *that child's* usage file and a screen may not go reading other
        people's state. ``or ""`` because a stand-in host in a test answers
        every question with ``None``.
        """
        return self.ctx.host.profile_resting_line(profile) or ""

    def _avatar(self, profile: Profile) -> Gtk.Widget:
        metrics = self.ctx.metrics
        size = metrics.avatar_size
        resting = self._resting_line(profile)

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
            # Hover and focus: the name, and then -- for a rested face -- why
            # (ADR-0014). One utterance rather than two, so a child who moves
            # on mid-sentence has still heard whose face it is.
            speak_text=f"{profile.speak_text}. {resting}" if resting else profile.speak_text,
            # The press is the shell's to answer: it goes through the same rate
            # limiter as the Resting screen, so a child hammering a dimmed face
            # is answered once and then left alone. See ``app.ShellWindow.
            # _refuse``.
            activate_text="" if resting else None,
            on_activate=partial(self.ctx.host.choose_profile, profile),
            speech_ui=self.ctx.speech_ui,
            css_classes=("tile", "resting-face") if resting else ("tile",),
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
