"""Physical sizing.

SYNTHESIS section 3 specifies child-facing targets in *millimetres*, because a
tile that is 40 mm on a 1080p 14" ThinkPad is 25 mm on a 4K one and a
five-year-old's finger does not care about pixels. Everything the child touches
is therefore sized here, from the monitor's real geometry where the compositor
reports it and from 96 dpi where it does not.

Design pixel values (the 160 x 160 tile, the 96 px band) come from
08-shell-ux-patterns section 3.2 and are treated as a *floor* at 96 dpi: the
physical minimum wins whenever it is larger.
"""

from __future__ import annotations

from dataclasses import dataclass

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

# Plausibility clamp. VMs and some docks report a 0 mm or 10 mm wide monitor;
# believing them would make the shell microscopic or enormous.
MIN_DPI = 60.0
MAX_DPI = 400.0


@dataclass(frozen=True)
class Metrics:
    """Converts physical millimetres and design pixels into device pixels."""

    dpi: float = DEFAULT_DPI
    scale_factor: int = 1

    @property
    def px_per_mm(self) -> float:
        return self.dpi / MM_PER_INCH

    @classmethod
    def from_monitor(cls, width_px: int, width_mm: int, scale_factor: int = 1) -> Metrics:
        """Build metrics from a monitor's reported geometry.

        ``width_px`` is the logical width GTK reports; multiply by the scale
        factor to get the physical pixels that ``width_mm`` actually covers.
        """
        scale = max(1, scale_factor)
        if width_px <= 0 or width_mm <= 0:
            return cls(DEFAULT_DPI, scale)
        dpi = (width_px * scale) / (width_mm / MM_PER_INCH)
        if not MIN_DPI <= dpi <= MAX_DPI:
            return cls(DEFAULT_DPI, scale)
        # GTK lays out in logical pixels, so express the density in those.
        return cls(dpi / scale, scale)

    def mm(self, millimetres: float) -> int:
        """Millimetres to logical pixels, rounded up (never undersize)."""
        return int(millimetres * self.px_per_mm + 0.999)

    def design(self, pixels: float) -> int:
        """A design pixel value at 96 dpi, scaled to this display's density."""
        return int(pixels * (self.dpi / DEFAULT_DPI) + 0.999)

    def at_least_mm(self, design_px: float, millimetres: float) -> int:
        """The larger of a scaled design value and a physical minimum."""
        return max(self.design(design_px), self.mm(millimetres))

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
        return self.at_least_mm(BAND_HEIGHT_PX, MIN_TARGET_MM + 6.0)

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


def detect_metrics() -> Metrics:
    """Ask GDK for the primary monitor's geometry; fall back to 96 dpi.

    Imports ``gi`` lazily so that headless unit tests never touch GTK.
    """
    try:  # pragma: no cover - requires a display
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            return Metrics()
        monitors = display.get_monitors()
        monitor = monitors.get_item(0) if monitors.get_n_items() else None
        if monitor is None:
            return Metrics()
        geometry = monitor.get_geometry()
        return Metrics.from_monitor(
            geometry.width, monitor.get_width_mm(), monitor.get_scale_factor()
        )
    except Exception:  # pragma: no cover - any GDK failure means "use 96 dpi"
        return Metrics()
