"""Child-facing widgets.

Everything a child can touch in the shell is built from :class:`ChildButton`,
which is where the input rules from SYNTHESIS section 2A live in one place:

* **A2** every mouse button does the same thing; no double-click, no
  right-click, no long-press, no scroll, no modifiers.
* **A3** the affordance fires on *press*, and eight clicks a second produce one
  action, not eight (a 150 ms debounce, not a queue).
* **B4** icon + label + audio, always: every button carries ``speak_text``,
  speaks on hover dwell, on focus and on activation, and exposes the same
  string as its accessible name -- which is also the test hook.

Nothing here decides *what* happens; screens pass callbacks.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk, Pango  # noqa: E402

from .labels import (  # noqa: E402
    LabelFit,
    Wrapper,
    approx_char_px,
    fit_label,
    line_height_px,
    step_points,
    wrap_estimate,
)
from .metrics import (  # noqa: E402
    TILE_CHROME_PX,
    TILE_CHROME_X_PX,
    TILE_SPACING_PX,
    Metrics,
)
from .speech import SpeechManager  # noqa: E402

#: SYNTHESIS A3. Long enough to swallow a burst, short enough that two
#: deliberate presses still read as two.
DEBOUNCE_MS = 150

__all__ = [
    "MIC_AGAIN_SPEAK",
    "MIC_SPEAK",
    "MIC_STOP_SPEAK",
    "TILE_CHROME_PX",
    "TILE_CHROME_X_PX",
    "TILE_SPACING_PX",
    "ActivityTile",
    "ChildButton",
    "MicButton",
    "PageDots",
    "Pager",
    "SpeechUI",
    "big_label",
    "bundled_icon",
    "carousel_page",
    "category_icon",
    "data_dir",
    "fit_gtk_label",
    "icon_image",
    "next_key",
    "page_label_fit",
    "quiet_carousel",
    "spatial_stack",
]

#: 08 section 3.5: spatial transitions 350-450 ms so the journey is legible.
TRANSITION_MS = 400

_KEY_COUNTER = [0]


def next_key(prefix: str) -> str:
    _KEY_COUNTER[0] += 1
    return f"{prefix}-{_KEY_COUNTER[0]}"


def _log_id_from(key: str) -> str:
    """``tile-tuxpaint-17`` -> ``tile-tuxpaint``: the stable half of a key."""
    stem, _, tail = key.rpartition("-")
    return stem if stem and tail.isdigit() else key


# --- labels that are never cut (see kidnix_shell.labels) -------------------


#: theme.css: ``window.kidnix`` is Andika with Cantarell behind it, and every
#: child-facing label is semibold. Stated here rather than read back off the
#: widget, because a widget that is not in a window yet has no computed style
#: and would be measured in whatever the system font happens to be. Keep the
#: family list in step with ``theme.css``: measuring in a face we do not draw
#: in is how a label that "fits" gets clipped on the machine that has the real
#: font installed.
CHILD_FACE = "Andika,Andika New Basic,Cantarell,Sans"


def _base_font(points: float, face: str = CHILD_FACE) -> Pango.FontDescription:
    """The description the theme will draw this text with, at ``points``."""
    description = Pango.FontDescription.from_string(face)
    description.set_weight(Pango.Weight.SEMIBOLD)
    description.set_size(max(1, int(points * Pango.SCALE)))
    return description


def pango_wrapper(widget: Gtk.Widget) -> tuple[Wrapper, Callable[[float], int]]:
    """``(wrap, line_height)`` measured by the engine that will draw the text.

    The pure-Python estimate in :mod:`kidnix_shell.labels` exists so the tests
    can run without a display; when there *is* a display we ask Pango, because
    the only measurement that matters is the one the child sees.
    """
    context = widget.get_pango_context()

    def layout_for(points: float) -> Pango.Layout:
        layout = Pango.Layout.new(context)
        layout.set_font_description(_base_font(points))
        return layout

    def wrap(text: str, points: float, width: int) -> tuple[tuple[str, ...], int]:
        layout = layout_for(points)
        layout.set_text(text, -1)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_width(max(1, width) * Pango.SCALE)
        raw = text.encode("utf-8")
        lines: list[str] = []
        for index in range(layout.get_line_count()):
            line = layout.get_line_readonly(index)
            start, length = line.start_index, line.length
            lines.append(raw[start : start + length].decode("utf-8", "replace"))
        widest = layout.get_pixel_size()[0]
        return (tuple(lines) or ("",)), widest

    def line_height(points: float) -> int:
        layout = layout_for(points)
        # A cap and a descender: the tallest a single line of this face gets.
        layout.set_text("Xgy", -1)
        return max(1, layout.get_pixel_size()[1])

    return wrap, line_height


def _measurers(widget: Gtk.Widget) -> tuple[Wrapper | None, Callable[[float], int]]:
    try:
        return pango_wrapper(widget)
    except Exception:  # pragma: no cover - no display, no Pango context
        return None, line_height_px


def fit_gtk_label(
    label: Gtk.Label,
    text: str,
    *,
    width: int,
    base_pt: float,
    floor_pt: float,
    height: int | None = None,
    points: float | None = None,
    max_lines: int = 2,
) -> LabelFit:
    """Set ``text`` on ``label`` so that all of it is visible. Always.

    Wrapping is word-then-character and centred, ``ellipsize`` is ``NONE``,
    and the point size is whatever :func:`kidnix_shell.labels.fit_label`
    decided -- ``points`` overrides it when a whole page has agreed on one
    size, which is what keeps a grid of tiles typographically even.
    """
    wrap, line_height = _measurers(label)
    if points is not None:
        lines, widest = (wrap or _estimate)(text, points, width)
        fit = LabelFit(
            text, lines, points, widest, len(lines) * line_height(points), widest <= width
        )
    else:
        fit = fit_label(
            text,
            width,
            base_pt=base_pt,
            floor_pt=floor_pt,
            max_lines=max_lines,
            height=height,
            wrap=wrap,
            line_height=line_height,
        )

    # **Inside a box, the wrapping is ours.** :func:`fit_label` has already
    # chosen where the lines break, with Pango, at the size we are about to
    # set, inside the width we were given -- so the label is handed the text
    # with those breaks in it and asked not to wrap again. Left to itself a
    # ``Gtk.Label`` wraps at ``max-width-chars``, which GTK converts to pixels
    # with the *style* font (24 pt) rather than the size the text is actually
    # set at, and the two answers are not the same: "With someone" fitted as
    # two lines came out as three, 34 px taller than the box the grid had
    # budgeted, on the panel we ship for.
    #
    # Nothing is cut either way -- ``ellipsize`` stays ``NONE`` -- and
    # ``fit.lines`` is the same text with the same words in the same order, so
    # the accessible name and the spoken string are untouched.
    boxed = height is not None
    label.set_label("\n".join(fit.lines) if boxed else text)
    label.set_wrap(not boxed)
    label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    label.set_justify(Gtk.Justification.CENTER)
    label.set_ellipsize(Pango.EllipsizeMode.NONE)
    label.set_lines(-1)
    label.set_single_line_mode(False)
    if not boxed:
        label.set_max_width_chars(_chars_across(label, width, base_pt))

    attributes = Pango.AttrList.new()
    attributes.insert(Pango.attr_size_new(max(1, int(fit.points * Pango.SCALE))))
    label.set_attributes(attributes)
    # **Both**, and only when the caller named a box.
    #
    # The reserved label box is what stops the grid from jumping between a page
    # of short names and a page of long ones, and it is a *box*: a wrapping
    # `Gtk.Label` otherwise reports a minimum width of its widest single word
    # (39 px for "Outside"), so the tile it lives in could be laid out at a
    # width the label was never fitted to. Asking for the width as well is safe
    # precisely because `height is not None` means a caller with a box -- a
    # tile, an avatar -- whose button already requests at least this much.
    #
    # A headline in open space passes no height, keeps no request at all, and
    # so still cannot push a page wider than the panel.
    if height is not None:
        label.set_size_request(width, height)
    else:
        label.set_size_request(-1, -1)
    return fit


def _estimate(text: str, points: float, width: int) -> tuple[tuple[str, ...], int]:
    from .labels import wrap_estimate

    return wrap_estimate(text, points, width)


def _chars_across(label: Gtk.Label, width: int, css_pt: float) -> int:
    """How many characters fit across ``width``, in Pango's own reckoning.

    ``max-width-chars`` is what a wrapping ``Gtk.Label`` asks its parent for,
    and GTK turns it into pixels with the *style* font's average character --
    the size ``theme.css`` states, not the smaller size we may have fitted the
    text to. Measure with that one and the label's natural width lands on the
    space we have: the tile neither grows to fit the text nor asks the grid for
    a width it cannot give.
    """
    per_char = approx_char_px(css_pt)
    try:
        metrics = label.get_pango_context().get_metrics(_base_font(css_pt), None)
        measured = metrics.get_approximate_char_width() / Pango.SCALE
        if measured > 0:
            per_char = measured
    except Exception:  # pragma: no cover - no display
        pass
    return max(2, int(width / per_char))


def page_label_fit(
    texts: Sequence[str],
    width: int,
    *,
    base_pt: float,
    floor_pt: float,
    height: int | None = None,
    widget: Gtk.Widget | None = None,
) -> tuple[float, int]:
    """``(points, label_height)`` for a whole page of labels.

    Two decisions, both taken per page rather than per tile:

    * **One size.** A grid where "Draw" is 24 pt and "Letters & numbers" is
      18 pt reads as a mistake, not as a hierarchy, so every tile on the page
      is set at the size the longest name on it can carry -- never below the
      floor.
    * **Only the lines it uses.** The layout *budgets* two lines
      (:attr:`~kidnix_shell.metrics.Metrics.tile_label_height`) so the grid
      always fits, but a page of one-word names gives the room back to the
      icon instead of leaving an empty second line under every tile.
    """
    wrap, line_height = _measurers(widget) if widget is not None else (None, line_height_px)
    wrapper = wrap or wrap_estimate
    names = [text for text in texts if text] or [""]

    # **One size that every name on the page fits the box at.** Choosing the
    # size per name and then taking the smallest was subtly wrong: a name whose
    # own fit was two lines at 18 pt can need *three* at the 23 pt the page
    # settled on, and the re-wrap at the common size never checked. "Copy the
    # lights" came out three lines tall inside a two-line box that way. So the
    # sizes are walked once, for the whole page, and a size is only accepted if
    # every name clears the width **and** the box at it.
    for points in step_points(base_pt, floor_pt):
        counts = []
        for text in names:
            lines, widest = wrapper(text, points, width)
            if widest > width:
                break
            counts.append(len(lines))
        else:
            tall = max(counts) * line_height(points)
            if height is None or tall <= height:
                return points, tall

    # Nothing fits the box, so the floor takes a third line -- the documented
    # last resort, and the one case where the tile is allowed to grow.
    floor = round(min(base_pt, floor_pt), 1)
    tallest = max(len(wrapper(text, floor, width)[0]) for text in names)
    return floor, tallest * line_height(floor)


class SpeechUI:
    """Bridges :class:`SpeechManager` to widgets.

    Owns the key -> widget registry so the manager can put the reserved
    highlight ring on whatever it is currently reading aloud, without the
    speech layer knowing anything about GTK.
    """

    def __init__(self, speech: SpeechManager) -> None:
        self.speech = speech
        self._widgets: dict[str, Gtk.Widget] = {}
        speech.on_highlight = self._on_highlight

    def register(self, key: str, widget: Gtk.Widget) -> None:
        self._widgets[key] = widget

    def unregister(self, key: str) -> None:
        self._widgets.pop(key, None)

    def forget_all(self) -> None:
        self._widgets.clear()

    def _on_highlight(self, key: str, speaking: bool) -> None:
        widget = self._widgets.get(key)
        if widget is None:
            return
        if speaking:
            widget.add_css_class("speaking")
        else:
            widget.remove_css_class("speaking")


class ChildButton(Gtk.Button):
    """A button a five-year-old can hit, hear and not double-fire."""

    def __init__(
        self,
        *,
        speak_text: str,
        on_activate: Callable[[], None] | None = None,
        speech_ui: SpeechUI | None = None,
        css_classes: tuple[str, ...] = (),
        key: str | None = None,
        size: int | None = None,
        width: int | None = None,
        height: int | None = None,
        debounce_ms: int = DEBOUNCE_MS,
        log_id: str | None = None,
    ) -> None:
        super().__init__()
        self.speak_text = speak_text
        self._on_activate = on_activate
        self._speech_ui = speech_ui
        self._debounce = debounce_ms / 1000.0
        self._last_fire = 0.0
        self.key = key or next_key("btn")
        #: What protocol P5's hover log calls this control. The key carries a
        #: run-unique counter, which is noise in a log meant to be counted by
        #: control; the stem is the stable name (and an ActivityTile overrides
        #: it with the activity's own id).
        self.log_id = log_id or _log_id_from(self.key)

        for css in css_classes:
            self.add_css_class(css)
        if size is not None:
            self.set_size_request(size, size)
        elif width is not None or height is not None:
            self.set_size_request(width or -1, height or -1)

        # The accessible name is the spoken string: one source of truth for
        # the screen reader, our own read-aloud and the UI tests.
        self.update_property([Gtk.AccessibleProperty.LABEL], [speak_text])
        self.set_can_focus(True)

        # Fire on press, from any mouse button. Capture phase + claim keeps
        # Gtk.Button's own click gesture from firing a second time; the
        # debounce below is the belt to that pair of braces.
        click = Gtk.GestureClick.new()
        click.set_button(0)  # 0 = every button, including middle and right
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", self._on_pressed)
        click.connect("released", self._on_released)
        self.add_controller(click)

        # Keyboard activation (space/enter) still arrives as "clicked".
        self.connect("clicked", lambda _b: self.fire())

        if speech_ui is not None:
            speech_ui.register(self.key, self)
            motion = Gtk.EventControllerMotion.new()
            motion.connect("enter", self._on_enter)
            motion.connect("motion", self._on_motion)
            motion.connect("leave", self._on_leave)
            self.add_controller(motion)
            focus = Gtk.EventControllerFocus.new()
            focus.connect("enter", self._on_focus)
            self.add_controller(focus)

    # -- input --

    def _on_pressed(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self.add_css_class("pressed")
        self.fire()

    def _on_released(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        self.remove_css_class("pressed")

    def fire(self) -> None:
        """Speak, then act -- once, however hard the button is hit."""
        now = time.monotonic()
        if now - self._last_fire < self._debounce:
            return
        self._last_fire = now
        if self._speech_ui is not None:
            self._speech_ui.speech.speak_activation(self.speak_text, self.key)
        if self._on_activate is not None:
            self._on_activate()

    def set_on_activate(self, callback: Callable[[], None] | None) -> None:
        self._on_activate = callback

    # -- speech --

    def _on_enter(self, _c: Gtk.EventControllerMotion, x: float, y: float) -> None:
        if self._speech_ui is not None:
            self._speech_ui.speech.hover_enter(self.key, self.speak_text, self.log_id)
            self._speech_ui.speech.hover_motion(self.key, x, y)

    def _on_motion(self, _c: Gtk.EventControllerMotion, x: float, y: float) -> None:
        """Spec 7b's settle gate: the dwell clock only runs on a still hand."""
        if self._speech_ui is not None:
            self._speech_ui.speech.hover_motion(self.key, x, y)

    def _on_leave(self, _c: Gtk.EventControllerMotion) -> None:
        if self._speech_ui is not None:
            self._speech_ui.speech.hover_leave(self.key)

    def _on_focus(self, _c: Gtk.EventControllerFocus) -> None:
        if self._speech_ui is not None:
            self._speech_ui.speech.speak_focus(self.speak_text, self.key)

    def set_speak_text(self, text: str) -> None:
        self.speak_text = text
        self.update_property([Gtk.AccessibleProperty.LABEL], [text])


def icon_image(icon: str, icon_kind: str, size: int, fallback: str = "image-missing") -> Gtk.Image:
    """Resolve a manifest icon to a Gtk.Image at ``size`` px.

    ``path`` icons come from the manifest or our bundled set; ``icon-name``
    icons come from the running icon theme, falling back to one of ours when
    the theme has never heard of ``gcompris-qt``.
    """
    image: Gtk.Image
    if icon_kind == "path" and icon:
        image = Gtk.Image.new_from_file(icon)
    else:
        display = Gdk.Display.get_default()
        theme = Gtk.IconTheme.get_for_display(display) if display else None
        if icon and theme is not None and theme.has_icon(icon):
            image = Gtk.Image.new_from_icon_name(icon)
        else:
            bundled = bundled_icon(icon) or bundled_icon(fallback)
            if bundled is not None:
                image = Gtk.Image.new_from_file(str(bundled))
            else:
                image = Gtk.Image.new_from_icon_name(fallback)
    image.set_pixel_size(size)
    return image


def data_dir() -> Path:
    return Path(__file__).parent / "data"


def bundled_icon(name: str) -> Path | None:
    """One of the shell's own representational icons, if we drew one."""
    if not name:
        return None
    candidate = data_dir() / "icons" / f"{name}.svg"
    return candidate if candidate.is_file() else None


def category_icon(category: str) -> str:
    """Fallback icon name by manifest category, so a tile is never blank."""
    return {"make": "kidnix-make", "learn": "kidnix-learn", "play": "kidnix-play"}.get(
        category, "kidnix-play"
    )


class ActivityTile(ChildButton):
    """S2: 160x160 design px (>= 40 mm), icon + label + a corner thumbnail."""

    def __init__(
        self,
        activity: object,
        metrics: Metrics,
        speech_ui: SpeechUI,
        on_activate: Callable[[], None],
        *,
        allowed: bool = True,
        denial: str = "Ask a grown-up for this one.",
        thumbnail: Path | None = None,
        extra_css: tuple[str, ...] = (),
        label_points: float | None = None,
        label_height: int | None = None,
    ) -> None:
        speak = getattr(activity, "speak_text", "")
        if not allowed:
            # Outline-only, never greyed out, and it always says why -- the
            # reason is the caller's (not allowed, or not installed).
            speak = f"{speak} {denial}"
        super().__init__(
            speak_text=speak,
            on_activate=on_activate,
            speech_ui=speech_ui,
            css_classes=("tile",) + (() if allowed else ("not-allowed",)) + extra_css,
            size=metrics.tile_size,
            key=next_key(f"tile-{getattr(activity, 'id', 'x')}"),
            # P5 counts hover utterances per *activity*, so the log carries the
            # manifest id rather than the widget's run-unique key.
            log_id=str(getattr(activity, "id", "") or "tile"),
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=TILE_SPACING_PX)
        box.set_valign(Gtk.Align.CENTER)

        # The icon takes whatever the two reserved label lines and the CSS
        # padding leave, down to a floor (metrics.tile_icon_size). Sizing it at
        # a flat 52% made the tile's *minimum* larger than the size we asked
        # for on a shrunk layout, and a grid of minimums that each overshoot is
        # how the band ended up off the top of the screen.
        label_box = metrics.tile_label_height if label_height is None else label_height
        icon_size = metrics.tile_icon_for(label_box)
        icon = icon_image(
            getattr(activity, "icon", ""),
            getattr(activity, "icon_kind", "icon-name"),
            icon_size,
            fallback=category_icon(getattr(activity, "category", "play")),
        )

        overlay = Gtk.Overlay()
        overlay.set_child(icon)
        if thumbnail is not None:
            # "Recently used tiles carry a small thumbnail of the last thing
            # made there" -- Sugarizer's resume idea, made ambient (spec S2).
            thumb = Gtk.Picture.new_for_filename(str(thumbnail))
            thumb.set_content_fit(Gtk.ContentFit.COVER)
            thumb_size = max(32, int(metrics.tile_size * 0.28))
            thumb.set_size_request(thumb_size, thumb_size)
            thumb.set_halign(Gtk.Align.END)
            thumb.set_valign(Gtk.Align.END)
            thumb.add_css_class("tile-thumb")
            overlay.add_overlay(thumb)
        box.append(overlay)

        # B4: the label is never cut. It wraps to two lines, shrinks in 1 pt
        # steps to the 18 pt floor, and only then takes a third line -- and
        # `speak_text` above is the *whole* audio_label either way, so what the
        # child hears is never the abbreviation of what they see.
        label = Gtk.Label()
        label.add_css_class("tile-label")
        self.label_fit = fit_gtk_label(
            label,
            getattr(activity, "name", ""),
            width=metrics.tile_label_width,
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=label_box,
            points=label_points,
        )
        self.label = label
        box.append(label)
        self.set_child(box)


#: What the mic button says before, during and after a recording. Short, because
#: every one of them is spoken *and* captioned.
MIC_SPEAK = "Tell me about it"
MIC_STOP_SPEAK = "Stop"
#: The quiet "again?" -- said only when a child presses a mic that already has a
#: note behind it, and only then. There is no retakes dialogue: a second
#: recording simply replaces the first (:mod:`kidnix_shell.voice`).
MIC_AGAIN_SPEAK = "Again?"


class MicButton(Gtk.Box):
    """ "Tell me about it": one press, a level meter, and no other controls.

    The button and its meter are one widget because they are one idea to the
    child -- "it is listening to me" is the meter moving inside the thing they
    just pressed. Nothing here decides anything: the screen hands it a
    :class:`kidnix_shell.voice.VoiceNote` and a directory, and the
    behaviour (twenty seconds, the auto-stop, the playback) is that class's.

    It is a **plain box, not a subclass of ChildButton**, because the meter has
    to live under the button without being part of its hit area: a 20 mm target
    has to stay 20 mm of *button*.
    """

    def __init__(
        self,
        metrics: Metrics,
        speech_ui: SpeechUI,
        on_press: Callable[[], None],
        *,
        size: int | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_halign(Gtk.Align.CENTER)
        target = size or max(metrics.min_target, metrics.design(96))

        self.button = ChildButton(
            speak_text=MIC_SPEAK,
            on_activate=on_press,
            speech_ui=speech_ui,
            css_classes=("mic",),
            size=target,
            key=next_key("mic"),
            log_id="voice-note",
        )
        self.button.set_child(icon_image("kidnix-mic", "icon-name", int(target * 0.6)))
        self.append(self.button)

        # The meter is *decoration of a state*, not a control and not a
        # measurement anybody reads: it exists so a five-year-old can tell
        # "listening" from "broken". It is hidden when nothing is recording so
        # the button does not appear to be doing something it is not.
        self.meter = Gtk.ProgressBar()
        self.meter.add_css_class("mic-level")
        self.meter.set_size_request(target, -1)
        self.meter.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
        self.meter.set_visible(False)
        self.append(self.meter)

    def set_recording(self, recording: bool) -> None:
        """Wear the state. The word on the button changes with it."""
        self.meter.set_visible(recording)
        if not recording:
            self.meter.set_fraction(0.0)
        self.button.set_speak_text(MIC_STOP_SPEAK if recording else MIC_SPEAK)
        if recording:
            self.button.add_css_class("recording")
        else:
            self.button.remove_css_class("recording")

    def set_level(self, level: float) -> None:
        self.meter.set_fraction(max(0.0, min(1.0, level)))


class PageDots(Gtk.Box):
    """Big page dots. Indicators only -- the arrows are the targets."""

    def __init__(self, metrics: Metrics) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_halign(Gtk.Align.CENTER)
        self._metrics = metrics
        self._dots: list[Gtk.Label] = []

    def set_pages(self, count: int, current: int) -> None:
        while self._dots:
            self.remove(self._dots.pop())
        if count <= 1:
            return
        for index in range(count):
            dot = Gtk.Label(label="●" if index == current else "○")
            dot.set_attributes(None)
            dot.add_css_class("quiet-line")
            dot.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
            self.append(dot)
            self._dots.append(dot)


class Pager(Gtk.Box):
    """Left arrow, page dots, right arrow. The only way to move through a list.

    SYNTHESIS A4: no free scrolling in the shell, ever.
    """

    def __init__(
        self,
        metrics: Metrics,
        speech_ui: SpeechUI,
        on_change: Callable[[int], None],
        *,
        what: str = "things",
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.set_halign(Gtk.Align.CENTER)
        self._on_change = on_change
        self.page = 0
        self.pages = 1

        arrow = max(metrics.min_target, metrics.design(96))
        self.back = ChildButton(
            speak_text=f"Back a page of {what}",
            on_activate=lambda: self.go(self.page - 1),
            speech_ui=speech_ui,
            css_classes=("pager",),
            size=arrow,
        )
        self.back.set_child(icon_image("kidnix-arrow-left", "icon-name", int(arrow * 0.6)))
        self.forward = ChildButton(
            speak_text=f"More {what}",
            on_activate=lambda: self.go(self.page + 1),
            speech_ui=speech_ui,
            css_classes=("pager",),
            size=arrow,
        )
        self.forward.set_child(icon_image("kidnix-arrow-right", "icon-name", int(arrow * 0.6)))

        self.dots = PageDots(metrics)
        self.append(self.back)
        self.append(self.dots)
        self.append(self.forward)

    def set_pages(self, count: int, page: int = 0) -> None:
        self.pages = max(1, count)
        self.page = max(0, min(page, self.pages - 1))
        self._refresh()

    def go(self, page: int) -> None:
        target = max(0, min(page, self.pages - 1))
        if target == self.page:
            return
        self.page = target
        self._refresh()
        self._on_change(self.page)

    def _refresh(self) -> None:
        self.dots.set_pages(self.pages, self.page)
        self.back.set_sensitive(self.page > 0)
        self.forward.set_sensitive(self.page < self.pages - 1)
        self.set_visible(self.pages > 1)


def big_label(
    text: str,
    css: str = "big-line",
    *,
    width: int | None = None,
    base_pt: float | None = None,
    floor_pt: float | None = None,
    points: float | None = None,
    max_lines: int = 2,
) -> Gtk.Label:
    """A child-facing line. Wraps, centres, and is never ellipsised.

    Pass ``width`` (and the point sizes that go with it) where the line has to
    live inside something of a known size -- a ritual button, a card caption.
    Without it the label keeps 08 section 3.3's 40-character measure and takes
    as many lines as it needs, which is right for a headline in open space.
    """
    label = Gtk.Label()
    label.add_css_class(css)
    if width is not None and base_pt is not None:
        fit_gtk_label(
            label,
            text,
            width=width,
            base_pt=base_pt,
            floor_pt=floor_pt if floor_pt is not None else base_pt,
            points=points,
            max_lines=max_lines,
        )
        return label
    label.set_label(text)
    label.set_wrap(True)
    label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    label.set_ellipsize(Pango.EllipsizeMode.NONE)
    label.set_justify(Gtk.Justification.CENTER)
    label.set_max_width_chars(40)  # 08 section 3.3: <= 40 chars for early readers
    return label


def spatial_stack() -> Gtk.Stack:
    """A stack whose transitions are legible as journeys, not cuts."""
    stack = Gtk.Stack()
    stack.set_transition_duration(TRANSITION_MS)
    stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
    return stack


def quiet_carousel() -> Adw.Carousel:
    """An Adw.Carousel with every free-scrolling affordance switched off.

    We want its animated page change and nothing else: children cannot scroll
    (A4) and a stray trackpad swipe must not move the page under them.
    """
    carousel = Adw.Carousel()
    carousel.set_allow_scroll_wheel(False)
    carousel.set_allow_mouse_drag(False)
    carousel.set_allow_long_swipes(False)
    carousel.set_interactive(False)
    # Nothing from the *next* page may show at the edge of this one. A sliver
    # of a tile a child cannot reach is an invitation to try.
    carousel.set_overflow(Gtk.Overflow.HIDDEN)
    return carousel


def carousel_page(child: Gtk.Widget) -> Gtk.Widget:
    """Wrap a page so it fills the carousel and its neighbours stay off-screen.

    ``Adw.Carousel`` sizes a page to its natural width and centres it, which
    lets the next page peek in beside a grid narrower than the screen.
    """
    page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    page.set_hexpand(True)
    page.set_vexpand(True)
    child.set_hexpand(True)
    page.append(child)
    return page
