"""A quick drawing, when there is nothing in the Journal worth sending yet.

Deliberately **not a paint program**. Draw is a whole tile on Home (Tux Paint,
tuned), it is better than anything that would fit on half of this screen, and a
second, worse one here would be the "interface complexity degrades touch
accuracy" finding (05 section 3, Couse & Chen) arriving by the back door. What
is here is the smallest thing that makes "I have nothing to send" untrue:

* **Three colours.** Not a palette, not a picker, not a wheel. Every extra item
  on a drawing surface costs a five-year-old touch accuracy, and three is what
  fits beside the canvas at 20 mm each without pushing the canvas under it.
* **Press to draw.** Press starts a stroke, moving with the button down extends
  it, release ends it. The same press-not-click rule as every other control
  (A3); no double-click, no right-click, no modifier, no tool modes.
* **One big undo**, which removes the whole last stroke, not the last point. A
  child who has drawn a line they do not want expects the line to go, and C1
  puts undo in a fixed place and makes it always available.
* **No eraser and no clear-all button on the child's screen.** C2: destructive
  actions are spatial and recoverable, and repeated undo already gets to an
  empty page one stroke at a time -- which is recoverable and a clear button is
  not.

The model is pure: a list of strokes, each a colour and a list of points in
**canvas coordinates normalised to 0..1**, so the same scribble renders
identically into a 320 px preview and a 900 px letter card without anybody
having to remember which one it was drawn at.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "COLOURS",
    "COLOUR_NAMES",
    "Colour",
    "Scribble",
    "Stroke",
]


@dataclass(frozen=True)
class Colour:
    """One crayon. A name for the ear, a hex for the eye, RGB for cairo."""

    key: str
    name: str
    hex: str

    @property
    def rgb(self) -> tuple[float, float, float]:
        raw = self.hex.lstrip("#")
        return tuple(int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]

    @property
    def speak_text(self) -> str:
        return self.name


#: The three. They are the shell's own tokens -- ``@kid-primary``,
#: ``@kid-secondary`` and ``@kid-ink`` from ``kidnix_shell/theme.css`` -- so a
#: scribble looks like it was made on this machine, and a test re-reads that
#: file and fails if they ever drift. Three hues that also differ in *lightness*
#: (B6: colour is never the sole carrier), so a child with a colour-vision
#: deficiency can still tell which crayon is which and so can a photocopy.
COLOURS: tuple[Colour, ...] = (
    Colour(key="teal", name="Teal", hex="#0f8a8a"),
    Colour(key="pink", name="Pink", hex="#f06292"),
    Colour(key="black", name="Black", hex="#16181d"),
)

COLOUR_NAMES = tuple(colour.name for colour in COLOURS)


def colour_for(key: str) -> Colour:
    """Look one up by key, falling back to the first. Never raises."""
    for colour in COLOURS:
        if colour.key == key:
            return colour
    return COLOURS[0]


@dataclass
class Stroke:
    """One press-drag-release. Points are 0..1 of the canvas, in order."""

    colour: Colour
    points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.points

    def add(self, x: float, y: float) -> None:
        """Add a point, clamped to the canvas.

        Clamped rather than dropped: a finger that slides off the edge of the
        canvas mid-stroke should leave a line that reaches the edge, not a line
        that stops short of it and then jumps back on.
        """
        self.points.append((min(1.0, max(0.0, x)), min(1.0, max(0.0, y))))


@dataclass
class Scribble:
    """The drawing so far. Strokes in the order they were made."""

    strokes: list[Stroke] = field(default_factory=list)
    colour: Colour = COLOURS[0]
    _open: Stroke | None = field(default=None, repr=False)

    # -- drawing --

    def choose(self, colour: Colour | str) -> Colour:
        """Pick a crayon. Ends any stroke in progress, so a colour never
        changes halfway along a line the child is still drawing."""
        self.end()
        self.colour = colour_for(colour) if isinstance(colour, str) else colour
        return self.colour

    def start(self, x: float, y: float) -> Stroke:
        """Press. A new stroke in the current colour, with its first point."""
        self.end()
        stroke = Stroke(colour=self.colour)
        stroke.add(x, y)
        self.strokes.append(stroke)
        self._open = stroke
        return stroke

    def extend(self, x: float, y: float) -> bool:
        """Move, with the button still down. False when nothing is open."""
        if self._open is None:
            return False
        self._open.add(x, y)
        return True

    def end(self) -> None:
        """Release. A stroke that never got a second point stays: a single
        press *is* a dot, and a dot is a mark a four-year-old meant to make."""
        self._open = None

    @property
    def drawing(self) -> bool:
        return self._open is not None

    # -- taking it back --

    def undo(self) -> bool:
        """Remove the last whole stroke. False when there is nothing left.

        Returning False rather than raising is what lets the button be pressed
        by a child eight times a second on an empty page without anything
        happening -- which is A3, and which is also what a child does.
        """
        self.end()
        if not self.strokes:
            return False
        self.strokes.pop()
        return True

    @property
    def is_empty(self) -> bool:
        return not any(stroke.points for stroke in self.strokes)

    @property
    def stroke_count(self) -> int:
        return len(self.strokes)
