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
TILE_LABEL_PX = 40
TILE_LABEL_PT = 18  # spec S2: label >= 18 pt

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

    @property
    def tile_label_height(self) -> int:
        return self.design(TILE_LABEL_PX)

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
        grid_height = self.rows * self.tile_size + (self.rows - 1) * self.gap
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
