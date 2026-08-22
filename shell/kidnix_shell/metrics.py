"""Physical sizing, clamped to the screen we actually have.

SYNTHESIS section 3 specifies child-facing targets in *millimetres*, because a
tile that is 40 mm on a 1080p 14" ThinkPad is 25 mm on a 4K one and a
five-year-old's finger does not care about pixels. Everything the child touches
is therefore sized here, from the monitor's real geometry where the compositor
reports it and from 96 dpi where it does not.

Design pixel values (the 160 x 160 tile, the 96 px band) come from
08-shell-ux-patterns section 3.2 and are treated as a *floor* at 96 dpi: the
physical minimum wins whenever it is larger.

**Fit beats physics.** v0.1.0 sized purely from millimetres and produced a
layout 6% larger than a 1280x800 panel: the band's buttons were clipped off the
top of the first real boot (``docs/design/screenshots/boot-home.png``). A
control the child cannot see is worse than one that is 3 mm small, so
:class:`Metrics` carries a ``fit`` factor: the mm-based ideal is computed first,
then shrunk uniformly until the band, the Home grid and the pager provably fit
inside the monitor's geometry. ``fit`` is 1.0 whenever the ideal already fits,
which is every screen from 1920x1080 up.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, replace

from .labels import line_height_px

log = logging.getLogger(__name__)

MM_PER_INCH = 25.4
DEFAULT_DPI = 96.0

# SYNTHESIS section 3, "The numbers".
MIN_TARGET_MM = 18.0  # any interactive thing
PRIMARY_TILE_MM = 40.0  # activity tile, journal card, big ritual button
JOURNAL_CARD_MM = 20.0  # 08 section 4.3
AVATAR_TILE_MM = 30.0  # spec S1
MIN_GAP_MM = 12.0  # 8 mm floor, 12 mm preferred
BAND_HEIGHT_PX = 96  # design px; scaled by DPI like everything else

# Design pixels at 96 dpi (08 section 3.2 / 3.3).
TILE_PX = 160

#: theme.css ``.tile-label``: the size a label gets when it fits on one line.
TILE_LABEL_BASE_PT = 24.0
#: SYNTHESIS B4 / spec S2: a child-facing label is never smaller than this.
#: Below it we add a third line rather than shrink again.
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
TILE_ICON_FRACTION = 0.52
TILE_ICON_MIN_FRACTION = 0.36
TILE_ICON_MIN_PX = 24

#: Spec 7a: "the band scales with the same factor, clamped to 80-128 px".
BAND_MIN_PX = 80
BAND_MAX_PX = 128
#: theme.css: ``.band`` has 8 px of vertical padding either side of the row and
#: a 4 px bottom border. The band's buttons have to live inside what is left,
#: or GTK grows the band past the clamp and the tops get cut off.
BAND_CHROME_PX = 20
#: A band button never shrinks below this, whatever the clamp says.
BAND_TARGET_MIN_PX = 44

# Plausibility clamp. VMs and some docks report a 0 mm or 10 mm wide monitor;
# believing them would make the shell microscopic or enormous.
MIN_DPI = 60.0
MAX_DPI = 400.0

#: Home grids we are willing to draw, largest first (columns, rows). A screen
#: too small for 4 x 3 at a legible size gets fewer, bigger tiles rather than
#: twelve unreadable ones.
GRIDS: tuple[tuple[int, int], ...] = ((4, 3), (4, 2), (3, 2))
#: A grid is acceptable while its tiles are still this big. Below it we drop to
#: the next grid down rather than shrinking further: on a small panel, eight
#: tiles a child can hit beat twelve they cannot. (128 px is a 34 mm tile at
#: 96 dpi -- under the 40 mm ideal, still comfortably a five-year-old's target.)
MIN_GRID_TILE_PX = 128
#: Absolute floor. Below this the screen is too small for kidnix and we would
#: rather draw something too big than something illegible.
MIN_FIT = 0.45

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
    #: Uniform shrink applied to every size so the layout fits the screen.
    fit: float = 1.0
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
            ).shrunk_to_fit()
            if best is None or candidate.tile_size > best.tile_size:
                best = candidate
            if candidate.tile_size >= MIN_GRID_TILE_PX:
                return candidate
        assert best is not None
        return best

    # --- unit conversion --------------------------------------------------

    def mm(self, millimetres: float) -> int:
        """Millimetres to logical pixels, rounded up (never undersize)."""
        return _ceil(millimetres * self.px_per_mm * self.fit)

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

    # --- the sizes the UI actually asks for ------------------------------

    @property
    def tile_size(self) -> int:
        """Activity tile edge: 160 design px, but never under 40 mm."""
        return self.at_least_mm(TILE_PX, PRIMARY_TILE_MM)

    # --- the label box (see kidnix_shell.labels) --------------------------

    @property
    def tile_label_pt(self) -> float:
        """The size a tile label starts at, before any fitting."""
        return self.points(TILE_LABEL_BASE_PT)

    @property
    def label_floor_pt(self) -> float:
        """The floor: 18 pt, or its equivalent on a layout we had to shrink."""
        return self.points(TILE_LABEL_MIN_PT)

    @property
    def tile_label_height(self) -> int:
        """Two label lines, always reserved, so the grid never jumps."""
        return TILE_LABEL_LINES * line_height_px(self.label_floor_pt)

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
        """Spec 7a: scales with everything else, clamped to 80-128 px."""
        ideal = self.at_least_mm(BAND_HEIGHT_PX, MIN_TARGET_MM + 6.0)
        return max(BAND_MIN_PX, min(BAND_MAX_PX, ideal))

    @property
    def band_target(self) -> int:
        """A band button. Sized to live *inside* the band's clamped height."""
        wanted = self.at_least_mm(80, MIN_TARGET_MM)
        return max(BAND_TARGET_MIN_PX, min(wanted, self.band_height - BAND_CHROME_PX))

    @property
    def band_small_target(self) -> int:
        """The grown-up gate: small, desaturated, far right (spec section 2)."""
        return max(BAND_TARGET_MIN_PX, min(self.design(56), self.band_target))

    @property
    def min_target(self) -> int:
        return self.mm(MIN_TARGET_MM)

    @property
    def gap(self) -> int:
        return self.mm(MIN_GAP_MM)

    @property
    def card_size(self) -> int:
        """Journal card edge (08 section 4.3: >= 20 mm, thumbnail-dominant)."""
        return self.at_least_mm(200, JOURNAL_CARD_MM)

    @property
    def avatar_size(self) -> int:
        return self.at_least_mm(220, AVATAR_TILE_MM)

    @property
    def pager_height(self) -> int:
        """The big page arrows under Home and My Things."""
        return max(self.min_target, self.design(96))

    @property
    def per_page(self) -> int:
        """Tiles on one Home page (spec S2 says 12; small screens get fewer)."""
        return self.columns * self.rows

    # --- fitting ----------------------------------------------------------

    def band_width(self) -> int:
        """What the band needs horizontally.

        ``Gtk.CenterBox`` keeps the centre widget centred, so it needs twice
        the wider of the two end groups plus the centre's own minimum.
        """
        left = 3 * self.band_target + 2 * self.gap
        right = self.band_target + self.band_small_target + self.gap
        centre = self.design(320)
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
        height = self.band_height + grid_height + self.pager_height + 3 * self.gap
        return width, height

    def required_size(self) -> tuple[int, int]:
        """The whole shell's minimum, in logical pixels."""
        home_width, home_height = self.home_size()
        return max(home_width, self.band_width()), home_height

    def fits(self) -> bool:
        if self.screen_width <= 0 or self.screen_height <= 0:
            return True
        width, height = self.required_size()
        return width <= self.screen_width and height <= self.screen_height

    def shrunk_to_fit(self) -> Metrics:
        """Shrink uniformly until :meth:`required_size` fits the screen."""
        if self.screen_width <= 0 or self.screen_height <= 0:
            return self
        candidate = self
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

    def shrunk_by(self, ratio: float) -> Metrics:
        """Shrink by a measured overflow ratio (the app's belt-and-braces)."""
        return replace(self, fit=max(MIN_FIT, round(self.fit * ratio, 4)))

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
            f"fit {self.fit:.2f}, tile {self.tile_size} px ({self.mm_of(self.tile_size):.0f} mm), "
            f"band {self.band_height} px, grid {self.columns}x{self.rows}, "
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


def detect_metrics(override: ScreenOverride | None = None) -> Metrics:
    """Measure the monitor and return metrics that fit on it.

    ``override`` (from ``--screen``) wins; then ``KIDNIX_SCREEN`` /
    ``KIDNIX_FORCE_DPI``; then the real monitor; then a 96 dpi guess.
    """
    override = override or override_from_env()
    geometry = monitor_geometry()

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
        return Metrics(dpi=clamp_dpi(dpi) if dpi is not None else DEFAULT_DPI)

    return Metrics.for_screen(width, height, width_mm=width_mm, scale_factor=scale, dpi=dpi)
