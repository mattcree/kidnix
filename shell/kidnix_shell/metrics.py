"""Physical sizing, clamped to the screen we actually have.

SYNTHESIS section 3 specifies child-facing targets in *millimetres*, because a
tile that is 40 mm on a 1080p 14" ThinkPad is 25 mm on a 4K one and a
five-year-old's finger does not care about pixels. Everything the child touches
is therefore sized here, from the monitor's real geometry where the compositor
reports it and from 96 dpi where it does not.

Design pixel values (the 160 x 160 tile, the 96 px band) come from
08-shell-ux-patterns section 3.2 and are treated as a *floor* at 96 dpi: the
physical minimum wins whenever it is larger.

**Fit beats physics -- but never below a floor.** v0.1.0 sized purely from
millimetres and produced a layout 6% larger than a 1280x800 panel: the band's
buttons were clipped off the top of the first real boot
(``docs/design/screenshots/boot-home.png``). A control the child cannot see is
worse than one that is 3 mm small, so :class:`Metrics` carries a ``fit`` factor:
the mm-based ideal is computed first, then shrunk uniformly until the band, the
Home grid and the pager provably fit inside the monitor's geometry.

v0.1.2 shrank the *floors* with it, which the CCI audit of 2026-08-22 called
correctly: "a floor that moves is not a floor". At 1280x800@102 the minimum
target was 14.9 mm and the 18 pt label floor was 14.9 pt. So there are now two
kinds of number here:

* **Floors** -- :data:`MIN_TARGET_MM` (20 mm since ADR-0011, any interactive
  thing),
  :data:`GAP_FLOOR_MM` (8 mm between targets) and :data:`TILE_LABEL_MIN_PT`
  (18 pt). ``fit`` never touches these. They are computed from the panel's real
  density and that is the end of it.
* **Preferences** -- the 160 design px tile, the 40 mm primary tile, the 12 mm
  preferred gap, the 96 px band, the icon's share of the tile, the margins.
  ``fit`` shrinks all of these, in step, until the layout fits.

When the preferences at ``fit = 1.0`` do not fit, the **grid** gives way before
the tile does: 4 x 3 -> 4 x 2 -> 3 x 2, and the rest of the activities paginate
(:data:`GRIDS`). Eight 42 mm tiles a child can hit beat twelve 26 mm ones, and
01 #12 wanted fewer choices anyway. Only when no grid can hold a
:data:`MIN_GRID_TILE_MM` tile does ``fit`` start shrinking the tile itself, and
even then it stops at :data:`MIN_TARGET_MM`.

**A point is not 4/3 of a pixel either.** See :attr:`Metrics.font_dpi` and
:func:`pin_font_dpi`: the image sets a 1.3 text-scaling factor, which was being
applied on top of the shell's own child type scale.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, replace

from .access import CAPTION_LINES, CAPTION_PT
from .labels import FONT_DPI, line_height_px

log = logging.getLogger(__name__)

MM_PER_INCH = 25.4
DEFAULT_DPI = 96.0

#: Believe GTK's own text density only if it is physically plausible. A
#: ``gtk-xft-dpi`` of 0 means "GTK has not decided yet", which is not a density.
MIN_FONT_DPI = 60.0
MAX_FONT_DPI = 300.0

# SYNTHESIS section 3, "The numbers".
#: **A floor. 20 mm since ADR-0011 (2026-08-23).**
#:
#: The 18 mm this carried was a unit-conversion artefact: Hourcade et al.
#: 2004's 64 px was on a ~75-80 dpi CRT, i.e. 20-24 mm, and the study's own
#: physical figure is 23.7 mm. Checkpoint 1 ruled "keep 18 / prefer 24"
#: without noticing. The panel resolved it the other way and the ADR makes it
#: binding: **20 mm minimum, 24 mm preferred, 40 mm for a primary tile.**
#:
#: It is the *measured hit area* that has to clear this, not the number the
#: layout asks for -- the accessibility review measured the band's buttons at
#: 69x77 px (17.2 mm) against a 72 px request, because ``theme.css`` took
#: ``margin: 0 4px`` off each side afterwards. The margin is gone and the gap
#: lives in the container's spacing, where it costs the target nothing.
MIN_TARGET_MM = 20.0
PRIMARY_TILE_MM = 40.0  # activity tile, journal card, big ritual button: preferred
JOURNAL_CARD_MM = 20.0  # 08 section 4.3
AVATAR_TILE_MM = 30.0  # spec S1
MIN_GAP_MM = 12.0  # preferred dead space between targets (01 #2)
#: **A floor.** 08 section 3.1c: gaps >= 8 mm, 12 preferred. ``fit`` may take
#: the preference away; it may not take this.
GAP_FLOOR_MM = 8.0
BAND_HEIGHT_PX = 96  # design px; scaled by DPI like everything else

# Design pixels at 96 dpi (08 section 3.2 / 3.3).
TILE_PX = 160

#: theme.css ``.tile-label``: the size a label gets when it fits on one line.
TILE_LABEL_BASE_PT = 24.0
#: **A floor.** SYNTHESIS B4 / spec S2: a child-facing label is never smaller
#: than this, on any panel. Below it we add a third line rather than shrink
#: again. ``fit`` does not apply -- a point is a physical unit and 18 pt is the
#: size at which a five-year-old can still match the shape to the word.
TILE_LABEL_MIN_PT = 18.0
#: Reserved in the tile's height whether the label uses them or not, so the
#: grid does not jump between a page of short names and a page of long ones.
#:
#: The box is two lines *at the floor*, and that is a deliberate budget, not a
#: coincidence: two lines at 24 pt would leave a 1280x800 panel's tiles under
#: the size at which we keep a 4 x 3 grid, i.e. buying a bigger wrapped label
#: with four fewer activities on the page. So a label that fits on one line
#: may be as big as the theme's 24 pt, and a label that has to wrap is stepped
#: down until two lines fit this box -- which in practice is the 18 pt floor.
TILE_LABEL_LINES = 2

#: theme.css: ``button.tile`` has 12 px of padding and 2/6 px borders. Fixed
#: pixels, so they do *not* shrink with the layout and have to be budgeted for.
TILE_CHROME_PX = 32  # vertical: 12 + 12 padding, 2 + 6 border
TILE_CHROME_X_PX = 28  # horizontal: 12 + 12 padding, 2 + 2 border
TILE_SPACING_PX = 6  # the box's spacing between icon and label
#: The icon may be squeezed by the label box, but only so far: below this
#: fraction of the tile the picture stops being the thing you recognise.
#: **The floor is 45% since ADR-0011.** For a pre-reader with low vision, no
#: English or CVD the picture is the only persistent channel there is, so it
#: does not get to be the thing that gives way when a label wraps.
TILE_ICON_FRACTION = 0.52
TILE_ICON_MIN_FRACTION = 0.45
TILE_ICON_MIN_PX = 24

# --- Goodbye (S7), which is a *fourth* shape ------------------------------
#
# **The screen that was not budgeted.** ``required_size()`` modelled Home, a
# titled grid and the chooser; S7 is none of the three -- a 40 mm picture, a
# 40 pt headline, a row of thumbnails, a line of feedback and two ritual
# buttons, stacked. It came in taller than the content window on the panel we
# ship for, and the e2e photographed the consequence: the "Show a grown-up" and
# "Goodnight" row cut off by the bottom edge of a 1280x800 panel
# (``docs/design/screenshots/e2e-goodbye-v2-clipped.png``), i.e. the two
# controls that end the session, on the screen whose entire job is ending the
# session.
#
# The order of what gives way is the ruling's own hierarchy (spec 7d #3): the
# **thumbnails** go first (they are the smallest claim on the screen and there
# are already three of them), then the spacing, and the destination picture and
# the buttons only shrink when the whole layout does -- and never below the
# 20 mm floor.

#: The chosen destination, spec 7d #3's ">= 40 mm picture". Fit-scaled like a
#: tile, floored at :data:`MIN_TARGET_MM` like everything else.
GOODBYE_DESTINATION_MM = 40.0
#: One of the day's thumbnails. Chrome-scaled: this is the cheapest thing on
#: the screen and it is what gets spent first.
GOODBYE_THUMBNAIL_MM = 24.0
#: ...but never smaller than this, or it stops being a picture of a drawing.
GOODBYE_THUMBNAIL_MIN_MM = 14.0
#: Journal thumbnails are landscape canvases, so the row is budgeted as boxes
#: rather than as squares -- a square request lets the picture grow taller than
#: the row allowed for, which is how the buttons ended up on the panel's edge.
GOODBYE_THUMBNAIL_ASPECT = 4 / 3
#: How many are shown (``screens.goodbye.MAX_THUMBNAILS``).
GOODBYE_THUMBNAILS = 3
#: The two ritual buttons: preferred height, floored at the 20 mm target.
GOODBYE_BUTTON_MM = 28.0
#: ...and their preferred width, from ``screens.goodbye``.
GOODBYE_BUTTON_WIDTH_MM = 60.0
#: ``theme.css`` ``.quiet-line``: the descriptive-feedback line under the work.
QUIET_LINE_PT = 22.0

#: Spec 7a: "the band scales with the same factor, clamped to 80-128 px" --
#: **80-136 since ADR-0011**, which raised the target floor to 20 mm and said
#: in as many words that the clamp may rise to hold one. 136 px is 20 mm plus
#: :data:`BAND_CHROME_PX` at the densest panel we ship for (118 dpi).
BAND_MIN_PX = 80
BAND_MAX_PX = 136
#: theme.css: ``.band`` has 8 px of vertical padding either side of the row and
#: a 4 px bottom border. The band's buttons have to live inside what is left,
#: or GTK grows the band past the clamp and the tops get cut off.
BAND_CHROME_PX = 20
#: A band button never shrinks below this, whatever the clamp says.
BAND_TARGET_MIN_PX = 44
#: ``theme.css`` ``.kid-captions``: 4 px of padding either side and a 2 px top
#: rule. Fixed pixels, so they are budgeted rather than scaled.
CAPTION_CHROME_PX = 10

# Plausibility clamp. VMs and some docks report a 0 mm or 10 mm wide monitor;
# believing them would make the shell microscopic or enormous.
MIN_DPI = 60.0
MAX_DPI = 400.0

#: Home grids we are willing to draw, largest first (columns, rows). A screen
#: too small for 4 x 3 at a legible size gets fewer, bigger tiles rather than
#: twelve unreadable ones; what does not fit on the page paginates.
GRIDS: tuple[tuple[int, int], ...] = ((4, 3), (4, 2), (3, 2))
#: A grid is acceptable while its tiles are still this big **in millimetres**.
#: Below it we drop to the next grid down rather than shrinking further: on a
#: small panel, eight tiles a child can hit beat twelve they cannot (01 #2 wants
#: 40-60 mm; 01 #12 wants fewer choices anyway). Only when no grid clears this
#: does ``fit`` shrink the tile, and never past :data:`MIN_TARGET_MM`.
MIN_GRID_TILE_MM = PRIMARY_TILE_MM
#: Absolute floor. Below this the screen is too small for kidnix and we would
#: rather draw something too big than something illegible.
MIN_FIT = 0.45

#: Chrome -- the gaps, the band's spare height, the pager's arrows -- is what
#: gets spent first when the layout is a little too tall. These are the steps
#: :meth:`Metrics.shrunk_to_fit` tries *before* it touches the tile, and each
#: one still stops at its own floor (8 mm gaps, a 20 mm band button, a 20 mm
#: pager arrow). Only when the last of them still overflows does ``fit`` start.
CHROME_STEPS: tuple[float, ...] = (1.0, 0.94, 0.88, 0.82, 0.76, 0.7, 0.62, 0.54, 0.45, 0.35)

#: ``--screen 1280x800@102`` / ``KIDNIX_SCREEN=1280x800@102``.
SCREEN_RE = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+)\s*(?:@\s*([\d.]+))?\s*$")


def _ceil(value: float) -> int:
    return int(value) if value == int(value) else int(value) + 1


@dataclass(frozen=True)
class Metrics:
    """Converts physical millimetres and design pixels into device pixels.

    ``screen_width``/``screen_height`` are the monitor's *logical* pixels (what
    GTK lays out in); 0 means "unknown", which disables fitting.
    """

    dpi: float = DEFAULT_DPI
    scale_factor: int = 1
    screen_width: int = 0
    screen_height: int = 0
    #: **What a CSS point is actually drawn at**, from GTK's ``gtk-xft-dpi``.
    #:
    #: :mod:`kidnix_shell.labels` assumed 96 -- "kidnix never sets a text
    #: scaling factor, so a point is 4/3 of a pixel on every panel". The image
    #: does set one: ``system_files/usr/share/kidnix/dconf/kid.d/10-input``
    #: has ``text-scaling-factor=1.3``, deliberately, so a five-year-old gets
    #: bigger type. GTK therefore reports **124.8 dpi**, every point size is
    #: drawn 30% larger than the layout budgeted for, and the two-line label
    #: box a tile reserves was never big enough to hold two real lines.
    #:
    #: The symptom was not a clipped label -- :func:`~kidnix_shell.labels.
    #: fit_label` falls through to its unbounded "third line" branch rather
    #: than cut anything -- it was a **content window 100 px taller than the
    #: strip gnome-kiosk had for it**, and the shell logging ``shell geometry
    #: WRONG`` on the real machine while every headless test passed.
    #:
    #: So it is measured, not assumed. 96 is only the headless default.
    font_dpi: float = FONT_DPI
    #: Is the caption strip on? It is part of the band window's height, so the
    #: layout has to know (``[access] captions``, on by default).
    captions: bool = True
    #: Uniform shrink applied to every *preferred* size so the layout fits the
    #: screen. Floors (:data:`MIN_TARGET_MM`, :data:`GAP_FLOOR_MM`,
    #: :data:`TILE_LABEL_MIN_PT`) ignore it.
    fit: float = 1.0
    #: Shrink applied to chrome only -- gaps, the band's spare height, the
    #: pager. Spent before ``fit``, because a narrower gap costs the child
    #: nothing and a smaller tile costs them the target.
    chrome_fit: float = 1.0
    columns: int = GRIDS[0][0]
    rows: int = GRIDS[0][1]

    @property
    def px_per_mm(self) -> float:
        """Logical pixels per millimetre *before* the fit factor."""
        return self.dpi / MM_PER_INCH

    @property
    def effective_px_per_mm(self) -> float:
        """What a millimetre is actually drawn at after fitting."""
        return self.px_per_mm * self.fit

    @classmethod
    def from_monitor(cls, width_px: int, width_mm: int, scale_factor: int = 1) -> Metrics:
        """Build metrics from a monitor's reported geometry (no fitting).

        ``width_px`` is the logical width GTK reports; multiply by the scale
        factor to get the physical pixels that ``width_mm`` actually covers.
        """
        return cls(dpi=dpi_for(width_px, width_mm, scale_factor), scale_factor=max(1, scale_factor))

    @classmethod
    def for_screen(
        cls,
        width_px: int,
        height_px: int,
        *,
        width_mm: int = 0,
        scale_factor: int = 1,
        dpi: float | None = None,
        font_dpi: float | None = None,
        captions: bool = True,
    ) -> Metrics:
        """The constructor the shell uses: physical sizing, clamped to the panel.

        Picks the largest Home grid that fits at a legible size, then shrinks
        every size uniformly until the band, the grid and the pager provably
        fit inside ``width_px`` x ``height_px``.
        """
        scale = max(1, scale_factor)
        density = clamp_dpi(dpi) if dpi is not None else dpi_for(width_px, width_mm, scale)

        best: Metrics | None = None
        for columns, rows in GRIDS:
            candidate = cls(
                dpi=density,
                scale_factor=scale,
                screen_width=max(0, width_px),
                screen_height=max(0, height_px),
                columns=columns,
                rows=rows,
                font_dpi=clamp_font_dpi(font_dpi),
                captions=captions,
            ).shrunk_to_fit()
            if candidate.mm_of(candidate.tile_size) >= MIN_GRID_TILE_MM:
                return candidate
            if best is None or candidate._grid_rank() > best._grid_rank():
                best = candidate
        assert best is not None
        return best

    def _grid_rank(self) -> tuple[int, int, int]:
        """How good a fallback grid is: **fitting first**, then a bigger tile.

        Ranking on ``tile_size`` alone had a hole with a floor under it: once
        every grid has been shrunk to :data:`MIN_FIT` their tiles are all the
        same size, the comparison is a tie, and the *first* grid wins -- 4 x 3,
        three rows, on exactly the panel that could not fit two. Fitting is the
        thing that was actually being relied on, so it is the thing compared
        first, and **fewer rows** breaks the remaining tie: rows are what
        height costs, and a page a child can see beats a page they cannot.
        """
        return (1 if self.fits() else 0, self.tile_size, -self.rows)

    # --- unit conversion --------------------------------------------------

    def line_height(self, points: float) -> int:
        """One line box at ``points``, at the density GTK really draws text at.

        The single place the shell converts a point size into a height. Every
        label box in the layout comes through here, which is what makes
        :attr:`font_dpi` a one-line fix rather than a hunt.
        """
        return line_height_px(points, self.font_dpi)

    def mm(self, millimetres: float) -> int:
        """A *preferred* size in millimetres, in logical pixels after fitting.

        Rounded up: undersizing a target is the one error that matters.
        """
        return _ceil(millimetres * self.px_per_mm * self.fit)

    def mm_floor(self, millimetres: float) -> int:
        """A **floor** in millimetres. ``fit`` does not apply to these.

        This is the whole point of specifying in millimetres: 20 mm is 20 mm on
        a 1080p ThinkPad and on the 1280x800 panel we test on. When the ideal
        layout will not fit, the grid gives way (:data:`GRIDS`) and the
        preferences shrink -- the floors do not move.
        """
        return _ceil(millimetres * self.px_per_mm)

    def chrome(self, pixels: float) -> int:
        """A piece of chrome, shrunk toward (never past) its own floor."""
        return _ceil(pixels * self.chrome_fit)

    def target_mm(self, millimetres: float) -> int:
        """A size for something the child touches: preferred, but never sub-floor."""
        return max(self.min_target, self.mm(millimetres))

    def design(self, pixels: float) -> int:
        """A design pixel value at 96 dpi, scaled to this display's density."""
        return _ceil(pixels * (self.dpi / DEFAULT_DPI) * self.fit)

    def at_least_mm(self, design_px: float, millimetres: float) -> int:
        """The larger of a scaled design value and a physical minimum."""
        return max(self.design(design_px), self.mm(millimetres))

    def mm_of(self, pixels: float) -> float:
        """How many real millimetres ``pixels`` logical pixels cover."""
        if self.px_per_mm <= 0:
            return 0.0
        return pixels / self.px_per_mm

    def points(self, base_pt: float) -> float:
        """A theme.css point size, shrunk by the same factor as the layout."""
        return round(base_pt * self.fit, 1)

    def child_points(self, base_pt: float) -> float:
        """A theme.css point size for text a *child* reads: 18 pt floor.

        06 #21 / SYNTHESIS B4. ``.quiet-line`` at 22 pt on a panel we had to
        shrink by a third is 14.7 pt, which is smaller than the floor we just
        spent a tile column defending on the same screen.
        """
        return max(self.points(base_pt), TILE_LABEL_MIN_PT)

    # --- the sizes the UI actually asks for ------------------------------

    @property
    def tile_size(self) -> int:
        """Activity tile edge: 160 design px, 40 mm preferred, 20 mm floor."""
        return max(self.min_target, self.at_least_mm(TILE_PX, PRIMARY_TILE_MM))

    # --- the label box (see kidnix_shell.labels) --------------------------

    @property
    def tile_label_pt(self) -> float:
        """The size a tile label starts at: theme.css's 24 pt, shrunk to fit.

        Never below :attr:`label_floor_pt` -- the starting size cannot be under
        the size we refuse to go below.
        """
        return max(self.points(TILE_LABEL_BASE_PT), self.label_floor_pt)

    @property
    def label_floor_pt(self) -> float:
        """**The floor: 18 pt, on every panel.**

        v0.1.2 ran this through :meth:`points` and got 14.9 pt at 1280x800@102.
        A floor that moves is not a floor (CCI audit section 3.2): a label
        smaller than this is one a pre-reader cannot match to a shape, and no
        amount of panel arithmetic changes that. The layout gives up a tile
        column instead.
        """
        return TILE_LABEL_MIN_PT

    @property
    def tile_label_height(self) -> int:
        """Two label lines, always reserved, so the grid never jumps."""
        return TILE_LABEL_LINES * self.line_height(self.label_floor_pt)

    @property
    def tile_label_width(self) -> int:
        """What a label has to fit into across the tile, inside the padding."""
        return max(1, self.tile_size - TILE_CHROME_X_PX)

    def tile_icon_for(self, label_height: int) -> int:
        """The icon takes what the label box leaves, within limits.

        ``label_height`` is the *reserved* two lines when sizing the layout,
        and what a page's labels actually came out at when building one: a page
        of one-word names gets its icon back rather than staring at an empty
        second line it never uses.
        """
        room = self.tile_size - label_height - TILE_CHROME_PX - TILE_SPACING_PX
        floor = max(TILE_ICON_MIN_PX, _ceil(self.tile_size * TILE_ICON_MIN_FRACTION))
        ideal = int(self.tile_size * TILE_ICON_FRACTION)
        return max(floor, min(ideal, room))

    @property
    def tile_icon_size(self) -> int:
        """The icon at the reserved label height -- what the layout budgets."""
        return self.tile_icon_for(self.tile_label_height)

    @property
    def tile_height(self) -> int:
        """A tile is 40 mm square *or* taller, if two label lines need it.

        Spec S2 says "160 x 160 px + 40 px label"; two legible lines are more
        than 40 px, so the tile is allowed to be the taller of the square and
        what its contents actually need. :meth:`home_size` uses this, which is
        what stops the grid from growing off the bottom of a small panel.
        """
        contents = TILE_CHROME_PX + self.tile_icon_size + TILE_SPACING_PX + self.tile_label_height
        return max(self.tile_size, contents)

    @property
    def band_height(self) -> int:
        """Spec 7a / ADR-0011: scales with everything else, clamped to 80-136 px.

        The clamp may not squeeze a band *button* below the 20 mm floor, so the
        band is at least tall enough to hold one plus its CSS chrome. The
        ceiling rose from 128 to 136 with the floor: 20 mm at the densest panel
        we ship for (118 dpi) is 93 px, and 93 + 20 of chrome is 113, so 136
        leaves room and still cannot eat a small panel.

        **This is the row of controls only.** The caption strip underneath it
        is :attr:`caption_height`, and what the compositor gives the band
        window is the two together (:attr:`band_window_height`).
        """
        ideal = self.chrome(self.at_least_mm(BAND_HEIGHT_PX, MIN_TARGET_MM + 6.0))
        floor = min(BAND_MAX_PX, self.min_target + BAND_CHROME_PX)
        return max(BAND_MIN_PX, floor, min(BAND_MAX_PX, ideal))

    @property
    def caption_height(self) -> int:
        """The strip under the band that mirrors what the shell just said.

        Two lines at the 18 pt floor plus its own padding, reserved whether
        they are used or not -- a strip that changes height is a band that
        moves under a child's hand, and the band is the one thing in the shell
        that never moves.

        It is part of the band *window*, not of the content window, for one
        reason: during an activity the content window is behind the child's
        drawing, and the lines that matter most -- "Draw is asking if you're
        done.", the ending offer -- are all said while it is. A caption a deaf
        child cannot see at put-away is the whole finding, unfixed.
        """
        if not self.captions:
            return 0
        return CAPTION_LINES * self.line_height(CAPTION_PT) + CAPTION_CHROME_PX

    @property
    def band_window_height(self) -> int:
        """The whole strip the compositor gives the band window."""
        return self.band_height + self.caption_height

    @property
    def content_height(self) -> int:
        """What is left of the panel once the band has its strip.

        Since v0.1.5 the band and the surfaces under it are **two separate
        toplevels** (``docs/spikes/band-over-activity.md``), so "the height the
        shell may lay out in" is no longer the monitor's height: the content
        window is given ``0,band_height W x content_height`` by
        ``window-config.ini`` and gets nothing else, whatever it asks for.
        0 means "unknown screen", which disables the measured-fit backstop
        exactly as ``screen_height`` already does.
        """
        if self.screen_height <= 0:
            return 0
        return max(1, self.screen_height - self.band_window_height)

    @property
    def band_target(self) -> int:
        """A band button: **20 mm floor**, 80 design px preferred, inside the band.

        And 20 mm of *hit area*: ``theme.css`` no longer puts a margin on
        ``.band button``, because a CSS margin comes off the widget's own
        allocation and the accessibility review measured the result at 17.2 mm
        against this number's 72 px. The gap between band buttons is the
        container's ``spacing`` now, which is dead space rather than target.
        """
        wanted = max(self.design(80), self.min_target)
        room = self.band_height - BAND_CHROME_PX
        return max(BAND_TARGET_MIN_PX, min(wanted, max(room, self.min_target)))

    @property
    def band_small_target(self) -> int:
        """The grown-up gate: small, desaturated, far right (spec section 2).

        An *adult* control, so 08 section 3.1e's 9 mm applies, not the child's
        20 mm -- being small is the point (08 section 4.5: unenticing).
        """
        return max(BAND_TARGET_MIN_PX, self.mm_floor(9.0), min(self.design(56), self.band_target))

    @property
    def min_target(self) -> int:
        """**The floor.** 20 mm of real panel, whatever ``fit`` says (ADR-0011)."""
        return self.mm_floor(MIN_TARGET_MM)

    @property
    def gap(self) -> int:
        """Dead space between targets: 12 mm preferred, **8 mm floor**."""
        return max(self.chrome(self.mm(MIN_GAP_MM)), self.mm_floor(GAP_FLOOR_MM))

    @property
    def card_size(self) -> int:
        """Journal card edge. **Floor 20 mm** (08 section 4.3), 200 design px preferred."""
        return max(self.min_target, self.mm_floor(JOURNAL_CARD_MM), self.chrome(self.design(200)))

    @property
    def avatar_size(self) -> int:
        """Who's-here face tile. **Floor 30 mm** (08 section 4.4), 220 design px preferred.

        Chrome-scaled because Who's here is the tallest surface in the stack on
        a small dense panel, and a 40 mm face is still a face. The floor is the
        one number that does not move.
        """
        return max(self.min_target, self.mm_floor(AVATAR_TILE_MM), self.chrome(self.design(220)))

    @property
    def pager_height(self) -> int:
        """The big page arrows under Home and My Things. 20 mm floor."""
        return max(self.min_target, self.chrome(self.design(96)))

    @property
    def screen_title_height(self) -> int:
        """A ``.screen-title`` line, plus the gap under it.

        **Budgeted since 2026-08-23, because the tallest surface is not Home.**
        ``home_size`` modelled Home -- a grid and a pager -- and What's next
        after is Home *plus a 40 pt title*, so the arithmetic was ~85 px
        optimistic about the one screen that decides whether the content window
        fits. The measured-fit backstop then had to close that gap on every
        boot, and a backstop that always fires is a model that is wrong.
        """
        return self.line_height(self.child_points(40.0)) + self.gap

    @property
    def per_page(self) -> int:
        """Tiles on one Home page (spec S2 says 12; small screens get fewer)."""
        return self.columns * self.rows

    @property
    def choice_rows(self) -> int:
        """Rows on a titled choice screen: one fewer than Home, never zero."""
        return max(1, self.rows - 1)

    @property
    def choice_per_page(self) -> int:
        """Pictures on one page of "What's next after?" -- and of any choice.

        SYNTHESIS B2 asks for at most five options on a choice screen; spec 7b
        allows six to nine and the conflict was never recorded. This resolves
        it the way the layout already wanted to: four on the panel we ship for,
        eight on a big one, and the rest one page along.
        """
        return self.columns * self.choice_rows

    # --- fitting ----------------------------------------------------------

    def band_width(self) -> int:
        """What the band needs horizontally.

        ``Gtk.CenterBox`` keeps the centre widget centred, so it needs twice
        the wider of the two end groups plus the centre's own minimum.
        """
        left = 3 * self.band_target + 2 * self.gap
        right = self.band_target + self.band_small_target + self.gap
        centre = self.chrome(self.design(320))
        return 2 * max(left, right) + centre

    def home_size(self) -> tuple[int, int]:
        """What Home needs: the grid, its margins, the band and the pager."""
        grid_width = self.columns * self.tile_size + (self.columns - 1) * self.gap
        # Height, not width: a tile with two reserved label lines is taller
        # than it is wide, and pretending otherwise is how v0.1.0 clipped.
        grid_height = self.rows * self.tile_height + (self.rows - 1) * self.gap
        width = grid_width + 4 * self.gap  # HomeScreen: gap * 2 either side
        # Three gaps down the page: HomeScreen's top margin, the Screen box's
        # own spacing between the grid and the pager, and the pager's bottom
        # margin. Getting this wrong by one gap is how v0.1.0 clipped.
        height = self.band_window_height + grid_height + self.pager_height + 3 * self.gap
        return width, height

    def choice_size(self) -> tuple[int, int]:
        """What a *titled* grid screen needs: What's next after, and S1.

        Home has no title. S1b is Home **plus a 40 pt headline**, and modelling
        only Home is how the arithmetic came to be ~85 px optimistic about the
        one surface that decides whether the content window fits at all -- the
        measured backstop then had to close that gap on every single boot.

        It is not paid for by shrinking every tile in the shell. S1b is a
        *choice* screen and SYNTHESIS B2 wants at most five choices on one, so
        it gets :attr:`choice_rows` -- one row fewer than Home -- and pages the
        rest. Fewer, bigger pictures on the screen that asks a question, and
        Home keeps its 40 mm tile.
        """
        grid_width = self.columns * self.tile_size + (self.columns - 1) * self.gap
        grid_height = self.choice_rows * self.tile_height + (self.choice_rows - 1) * self.gap
        width = grid_width + 4 * self.gap
        height = (
            self.band_window_height
            + self.screen_title_height
            + grid_height
            + self.pager_height
            + 3 * self.gap
        )
        return width, height

    def chooser_size(self) -> tuple[int, int]:
        """What "Who's here?" needs: a title, a face, and the grown-up corner.

        The third shape in the shell, and the third one the arithmetic did not
        know about. Its face is floored at 30 mm and its corner tile at the
        20 mm target floor, so ``fit`` cannot shrink it away -- which is
        exactly why it has to be *budgeted* rather than discovered by the
        measured backstop and then shrunk at.
        """
        height = (
            self.band_window_height
            + self.screen_title_height
            + self.avatar_tile_height
            + self.min_target  # the plain grown-up tile in the corner
            # The screen's own dead space: its bottom margin, the gap under
            # the title, the gap over the corner, and the box's two spacings
            # -- one of which `screen_title_height` already carries.
            + 4 * self.gap
        )
        width = max(2 * self.avatar_size + 4 * self.gap, self.target_mm(40) + 2 * self.gap)
        return width, height

    @property
    def avatar_tile_height(self) -> int:
        """A face tile: the picture, its name, and the tile's own chrome."""
        return self.avatar_size + self.tile_label_height + TILE_CHROME_PX + TILE_SPACING_PX

    # --- Goodbye's own sizes, so the screen and the budget cannot drift ---

    @property
    def goodbye_destination(self) -> int:
        """The chosen picture: 40 mm preferred, the 20 mm floor underneath."""
        return self.target_mm(GOODBYE_DESTINATION_MM)

    @property
    def goodbye_thumbnail(self) -> int:
        """One thumbnail's height. **The first thing S7 spends.**"""
        return max(
            self.mm_floor(GOODBYE_THUMBNAIL_MIN_MM),
            self.chrome(self.mm(GOODBYE_THUMBNAIL_MM)),
        )

    @property
    def goodbye_button(self) -> int:
        """A ritual button's height. Never under the 20 mm target floor."""
        return self.target_mm(GOODBYE_BUTTON_MM)

    def goodbye_size(self) -> tuple[int, int]:
        """What S7 needs: destination, headline, thumbnails, a line, two buttons.

        Modelled here rather than discovered by the measured backstop, for the
        reason the whole of ``required_size`` exists: a backstop that has to
        close the same gap on every boot is a model that is wrong, and on this
        screen the gap it could not close was the two buttons.
        """
        thumbnails = self.goodbye_thumbnail
        height = (
            self.band_window_height
            + self.goodbye_destination
            # The headline, plus the one gap `screen_title_height` carries.
            + self.screen_title_height
            + thumbnails
            + self.line_height(self.child_points(QUIET_LINE_PT))
            + self.goodbye_button
            # Five children in the box: four spacings, minus the one already in
            # `screen_title_height`, plus the screen's own bottom margin.
            + 4 * self.gap
        )
        row = (
            GOODBYE_THUMBNAILS * _ceil(thumbnails * GOODBYE_THUMBNAIL_ASPECT)
            + (GOODBYE_THUMBNAILS - 1) * self.gap
        )
        buttons = 2 * self.target_mm(GOODBYE_BUTTON_WIDTH_MM) + 2 * self.gap
        return max(row, buttons, self.goodbye_destination) + 2 * self.gap, height

    def required_size(self) -> tuple[int, int]:
        """The whole shell's minimum: the **tallest** surface, not just Home.

        **Four** shapes, because the shell has four: Home's untitled grid, a
        titled grid (What's next after), the chooser (Who's here) and Goodbye.
        Until 2026-08-23 only the first was modelled, so the measured backstop
        was left to discover the others on every boot -- and on the panel we
        ship for it could not close the gap, which is a content window taller
        than the strip gnome-kiosk gives it. Goodbye was the last one in, and
        the e2e caught it in the worst possible place: its two buttons off the
        bottom edge of a 1280x800 panel.
        """
        home_width, home_height = self.home_size()
        choice_width, choice_height = self.choice_size()
        chooser_width, chooser_height = self.chooser_size()
        goodbye_width, goodbye_height = self.goodbye_size()
        return (
            max(home_width, choice_width, chooser_width, goodbye_width, self.band_width()),
            max(home_height, choice_height, chooser_height, goodbye_height),
        )

    def fits(self) -> bool:
        if self.screen_width <= 0 or self.screen_height <= 0:
            return True
        width, height = self.required_size()
        return width <= self.screen_width and height <= self.screen_height

    def shrunk_to_fit(self) -> Metrics:
        """Fit the layout to the screen, spending the cheapest thing first.

        Two stages, in the order the CCI audit's fix #1 asks for:

        1. **Chrome.** Walk :data:`CHROME_STEPS`, narrowing the gaps, the band's
           spare height and the pager toward (never past) their own floors. A
           child loses nothing when 12 mm of dead space becomes 9 mm.
        2. **Everything.** Only if the whole of stage 1 still overflows does
           ``fit`` start, and even then the floors stay where they are -- what
           actually gives is the tile, and before the tile it is the *grid*
           (:meth:`for_screen` tries 4x3, then 4x2, then 3x2).
        """
        if self.screen_width <= 0 or self.screen_height <= 0:
            return self
        candidate = self
        for chrome_fit in CHROME_STEPS:
            candidate = replace(self, chrome_fit=chrome_fit)
            if candidate.fits():
                return candidate
        for _ in range(64):
            if candidate.fits():
                return candidate
            width, height = candidate.required_size()
            ratio = min(self.screen_width / width, self.screen_height / height)
            # Always make progress even when the ratio rounds back to 1.0
            # (the band clamp and the mm rounding are both step functions).
            nxt = min(candidate.fit * ratio, candidate.fit - 0.005)
            if nxt <= MIN_FIT:
                return replace(candidate, fit=MIN_FIT)
            candidate = replace(candidate, fit=round(nxt, 4))
        return candidate

    def chrome_signature(self) -> tuple[int, ...]:
        """Every size ``chrome_fit`` can still move. Also the test hook.

        Two metrics with the same signature lay out identically however
        different their ``chrome_fit`` is, because each of these has hit its
        own floor: the 8 mm gap, the 80 px band, the 20 mm pager arrow, the
        20 mm card, the 30 mm face.
        """
        return (
            self.gap,
            self.band_window_height,
            self.pager_height,
            self.card_size,
            self.avatar_size,
            self.goodbye_thumbnail,
            self.chrome(self.design(320)),
        )

    def chrome_is_spent(self, ratio: float = 0.99) -> bool:
        """Would another chrome step change any size at all?

        The v0.1.7 geometry regression in one predicate. ``shrunk_by`` used to
        spend chrome until ``chrome_fit`` reached :data:`CHROME_STEPS`'s last
        value, on the assumption that spending chrome always buys pixels. It
        does not: the gap, the band and the pager all bottom out at their own
        floors long before ``chrome_fit`` reaches 0.35, and every step after
        that is a step that changes nothing. Measured in the VM: seven passes
        of the backstop, each logging "shrinking by 0.874", each relaying out
        to exactly the same ``904x632`` -- so the content tree stayed 802 px
        tall inside a 708 px window, GTK sent *that* as the toplevel's minimum
        size, and gnome-kiosk's ``lock-on-area`` could not be honoured. The
        window came up 1280x790 and the shell logged ``shell geometry WRONG``.
        """
        floor = CHROME_STEPS[-1]
        if self.chrome_fit <= floor:
            return True
        nxt = replace(self, chrome_fit=max(floor, round(self.chrome_fit * ratio, 4)))
        return nxt.chrome_signature() == self.chrome_signature()

    def shrunk_by(self, ratio: float, *, force_fit: bool = False) -> Metrics:
        """Shrink by a *measured* overflow ratio (the app's belt-and-braces).

        Same order of spending as :meth:`shrunk_to_fit`: chrome first, and only
        once the chrome is exhausted does the tile give way. GTK's measurement
        includes CSS padding and real font metrics that the arithmetic cannot
        know, and it typically overshoots by a few pixels -- exactly the size
        of a gap, not of a target.

        "Exhausted" is :meth:`chrome_is_spent`, not "``chrome_fit`` reached its
        last step". A backstop that keeps spending a currency it has run out of
        never buys anything, and the overflow it was called to close stays on
        the screen.

        ``force_fit`` is the caller's own evidence: a chrome step that changed
        some size but did not change what GTK *measured* has bought nothing
        either, and only the caller can see that. See
        ``ShellWindow._check_measured_fit``.
        """
        step = max(0.5, min(0.995, ratio))
        if not force_fit and not self.chrome_is_spent(step):
            floor = CHROME_STEPS[-1]
            return replace(self, chrome_fit=max(floor, round(self.chrome_fit * step, 4)))
        # ``fit`` is a multiplier on sizes that are rounded up to whole pixels,
        # so a small enough step can leave every one of them where it was. Keep
        # walking until something actually moves, or until the floor says no.
        candidate = replace(self, fit=max(MIN_FIT, round(self.fit * step, 4)))
        signature = self.layout_signature()
        for _ in range(64):
            if candidate.fit <= MIN_FIT or candidate.layout_signature() != signature:
                break
            candidate = replace(candidate, fit=max(MIN_FIT, round(candidate.fit - 0.01, 4)))
        return candidate

    def layout_signature(self) -> tuple[int, ...]:
        """Every size the layout is built from. Two equal signatures lay out alike."""
        return (self.tile_size, self.tile_height, *self.chrome_signature())

    # --- reporting --------------------------------------------------------

    def describe(self) -> str:
        width, height = self.required_size()
        screen = (
            f"{self.screen_width}x{self.screen_height}"
            if self.screen_width and self.screen_height
            else "unknown screen"
        )
        return (
            f"{screen} at {self.dpi:.0f} dpi (scale {self.scale_factor}), "
            f"fit {self.fit:.2f}, tile {self.tile_size} px ({self.mm_of(self.tile_size):.1f} mm), "
            f"gap {self.mm_of(self.gap):.1f} mm, target {self.mm_of(self.min_target):.1f} mm, "
            f"band {self.band_window_height} px "
            f"(row {self.band_height}, captions {self.caption_height}, "
            f"button {self.mm_of(self.band_target):.1f} mm), "
            f"label floor {self.label_floor_pt:.0f} pt at {self.font_dpi:.0f} font dpi, "
            f"grid {self.columns}x{self.rows}, "
            f"needs {width}x{height}"
        )


def clamp_dpi(dpi: float | None) -> float:
    """Believe a density only if it is physically plausible."""
    if dpi is None or not MIN_DPI <= dpi <= MAX_DPI:
        return DEFAULT_DPI
    return dpi


def dpi_for(width_px: int, width_mm: int, scale_factor: int = 1) -> float:
    """Logical dpi from a monitor's geometry, or 96 if it reports nonsense."""
    scale = max(1, scale_factor)
    if width_px <= 0 or width_mm <= 0:
        return DEFAULT_DPI
    physical = (width_px * scale) / (width_mm / MM_PER_INCH)
    if not MIN_DPI <= physical <= MAX_DPI:
        return DEFAULT_DPI
    # GTK lays out in logical pixels, so express the density in those.
    return physical / scale


@dataclass(frozen=True)
class ScreenOverride:
    """``--screen 1280x800@102``: pretend we are on somebody else's panel."""

    width: int
    height: int
    dpi: float | None = None


def parse_screen(text: str) -> ScreenOverride:
    """Parse ``WIDTHxHEIGHT`` or ``WIDTHxHEIGHT@DPI``. Raises ValueError."""
    match = SCREEN_RE.match(text)
    if match is None:
        raise ValueError(f"{text!r} is not WIDTHxHEIGHT[@DPI], e.g. 1280x800@102")
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise ValueError(f"{text!r}: width and height must be positive")
    dpi = float(match.group(3)) if match.group(3) else None
    return ScreenOverride(width=width, height=height, dpi=dpi)


def override_from_env(env: dict[str, str] | None = None) -> ScreenOverride | None:
    """``KIDNIX_SCREEN`` and ``KIDNIX_FORCE_DPI``, for testing on the wrong panel."""
    environ = dict(os.environ if env is None else env)
    screen = environ.get("KIDNIX_SCREEN", "").strip()
    forced = environ.get("KIDNIX_FORCE_DPI", "").strip()
    override: ScreenOverride | None = None
    if screen:
        try:
            override = parse_screen(screen)
        except ValueError as exc:
            log.warning("ignoring KIDNIX_SCREEN: %s", exc)
    if forced:
        try:
            dpi = float(forced)
        except ValueError:
            log.warning("ignoring KIDNIX_FORCE_DPI=%r: not a number", forced)
            return override
        override = (
            ScreenOverride(override.width, override.height, dpi)
            if override is not None
            else ScreenOverride(0, 0, dpi)
        )
    return override


def clamp_font_dpi(font_dpi: float | None) -> float:
    """Believe GTK's text density only if it is a density."""
    if font_dpi is None or not MIN_FONT_DPI <= font_dpi <= MAX_FONT_DPI:
        return FONT_DPI
    return font_dpi


def gtk_font_dpi() -> float | None:
    """What GTK will actually draw a CSS ``pt`` at, or ``None`` if we cannot ask.

    ``gtk-xft-dpi`` is in 1024ths of a dot per inch and is where the desktop's
    text-scaling factor arrives: 96 dpi times 1.3 is the 127794 the image's own
    dconf produces. Imports ``gi`` lazily so headless unit tests never touch
    GTK, exactly like :func:`monitor_geometry`.
    """
    try:  # pragma: no cover - requires a display
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        settings = Gtk.Settings.get_default()
        if settings is None:
            return None
        raw = settings.get_property("gtk-xft-dpi")
        return float(raw) / 1024.0 if raw and raw > 0 else None
    except Exception:  # pragma: no cover - any GTK failure means "assume 96"
        return None


def pin_font_dpi(font_dpi: float = FONT_DPI) -> float | None:
    """Draw the shell's own points at the density the shell's type scale means.

    **The accessibility decision is already taken, once, here.** Every
    child-facing size in ``theme.css`` goes through
    :meth:`Metrics.child_points` and its 18 pt floor, and every box around it
    is computed in millimetres from the panel's real density. The desktop's
    ``text-scaling-factor`` is a second, independent multiplier on the same
    quantity, and the image sets it to **1.3**
    (``system_files/usr/share/kidnix/dconf/kid.d/10-input``). Applied on top,
    the shell's 18 pt floor is drawn at 23.4 pt, its 40 pt headline at 52 pt,
    and the two-line label box a 42 mm tile reserves stops fitting two lines --
    which is how the content window came to be 150 px taller than the strip
    gnome-kiosk gives it, with the shell logging ``shell geometry WRONG``.

    So the shell pins its own ``gtk-xft-dpi`` for its own process and leaves
    the session setting alone: every other program in the child's session --
    Tux Paint's dialogs, GCompris' menus, none of which has a mm-based layout
    system -- keeps the larger text the image asked for.

    Returns the density that was in force before, or ``None`` if GTK could not
    be asked. Call it **before** :func:`detect_metrics`.
    """
    try:  # pragma: no cover - requires a display
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        settings = Gtk.Settings.get_default()
        if settings is None:
            return None
        raw = settings.get_property("gtk-xft-dpi")
        before = float(raw) / 1024.0 if raw and raw > 0 else None
        settings.set_property("gtk-xft-dpi", round(font_dpi * 1024))
        return before
    except Exception:  # pragma: no cover - any GTK failure means "leave it"
        return None


def monitor_geometry() -> tuple[int, int, int, int] | None:
    """``(width_px, height_px, width_mm, scale_factor)`` for the monitor we are on.

    Imports ``gi`` lazily so that headless unit tests never touch GTK.
    """
    try:  # pragma: no cover - requires a display
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            return None
        monitors = display.get_monitors()
        monitor = monitors.get_item(0) if monitors.get_n_items() else None
        if monitor is None:
            return None
        geometry = monitor.get_geometry()
        return (
            geometry.width,
            geometry.height,
            monitor.get_width_mm(),
            monitor.get_scale_factor(),
        )
    except Exception:  # pragma: no cover - any GDK failure means "use 96 dpi"
        return None


def detect_metrics(override: ScreenOverride | None = None, captions: bool = True) -> Metrics:
    """Measure the monitor and return metrics that fit on it.

    ``override`` (from ``--screen``) wins; then ``KIDNIX_SCREEN`` /
    ``KIDNIX_FORCE_DPI``; then the real monitor; then a 96 dpi guess.

    The *font* density is asked of GTK separately and is never overridden by
    ``--screen``: it is a property of the session's settings, not of the panel
    we are pretending to be on, and pretending about it is what hid the
    1.3 text-scaling factor the image ships (see :attr:`Metrics.font_dpi`).
    """
    override = override or override_from_env()
    geometry = monitor_geometry()
    text_dpi = gtk_font_dpi()

    width = height = 0
    width_mm = 0
    scale = 1
    if geometry is not None:
        width, height, width_mm, scale = geometry

    dpi: float | None = None
    if override is not None:
        if override.width and override.height:
            width, height, width_mm = override.width, override.height, 0
            scale = 1
        dpi = override.dpi

    if not width or not height:
        # No display at all (headless tests): the design values are the answer.
        return Metrics(
            dpi=clamp_dpi(dpi) if dpi is not None else DEFAULT_DPI,
            font_dpi=clamp_font_dpi(text_dpi),
            captions=captions,
        )

    return Metrics.for_screen(
        width,
        height,
        width_mm=width_mm,
        scale_factor=scale,
        dpi=dpi,
        font_dpi=text_dpi,
        captions=captions,
    )
