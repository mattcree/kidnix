"""The bits of the theme that only exist at runtime.

``theme.css`` holds everything that is fixed. Two things are not:

* **Colour = whose it is** (08 section 3.4): the band and the focus tint come
  from the active child's profile colours.
* **Type scales with the layout.** Font sizes in ``theme.css`` are points, and
  points do not know about :attr:`kidnix_shell.metrics.Metrics.fit`. On a panel
  the shell had to shrink to fit, a 24 pt tile label would still be 24 pt and
  would push the tile past the size we just carefully computed. So the point
  sizes are re-emitted here, multiplied by the same factor as everything else.

Pure string building, so the whole thing is testable without a display.
"""

from __future__ import annotations

from .metrics import Metrics
from .settings import Profile

#: Selector -> the point size ``theme.css`` states. Keep in step with it.
BASE_POINTS: dict[str, float] = {
    ".tile-label": 24,
    ".day-heading": 26,
    ".shelf-heading": 22,
    ".big-line": 34,
    ".screen-title": 40,
    ".quiet-line": 22,
    "button.ritual": 30,
    "button.ritual.secondary": 22,
}


def points_for(metrics: Metrics, selector: str) -> float:
    """What ``selector`` is actually drawn at on this panel.

    The single source of truth for "how big is this text" -- widgets that have
    to fit a label into a known width ask here rather than repeating a number
    that ``theme.css`` might change under them.
    """
    return metrics.points(BASE_POINTS[selector])


def tint_css(profile: Profile) -> str:
    return (
        f".band {{ background-color: {profile.colour_primary};"
        f" border-bottom-color: {profile.colour_secondary}; }}"
    )


def font_css(metrics: Metrics) -> str:
    """Re-state every child-facing point size at the layout's own scale."""
    if metrics.fit >= 0.999:
        return ""
    rules = []
    for selector, points in BASE_POINTS.items():
        rules.append(f"{selector} {{ font-size: {metrics.points(points)}pt; }}")
    return "\n".join(rules)


def dynamic_css(metrics: Metrics, profile: Profile) -> str:
    """Everything the display-level provider needs for this profile and panel."""
    return "\n".join(part for part in (tint_css(profile), font_css(metrics)) if part)
