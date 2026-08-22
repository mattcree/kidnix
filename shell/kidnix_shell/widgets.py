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
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from .metrics import Metrics  # noqa: E402
from .speech import SpeechManager  # noqa: E402

#: SYNTHESIS A3. Long enough to swallow a burst, short enough that two
#: deliberate presses still read as two.
DEBOUNCE_MS = 150

#: 08 section 3.5: spatial transitions 350-450 ms so the journey is legible.
TRANSITION_MS = 400

_KEY_COUNTER = [0]


def next_key(prefix: str) -> str:
    _KEY_COUNTER[0] += 1
    return f"{prefix}-{_KEY_COUNTER[0]}"


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
    ) -> None:
        super().__init__()
        self.speak_text = speak_text
        self._on_activate = on_activate
        self._speech_ui = speech_ui
        self._debounce = debounce_ms / 1000.0
        self._last_fire = 0.0
        self.key = key or next_key("btn")

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

    def _on_enter(self, _c: Gtk.EventControllerMotion, _x: float, _y: float) -> None:
        if self._speech_ui is not None:
            self._speech_ui.speech.hover_enter(self.key, self.speak_text)

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
        thumbnail: Path | None = None,
    ) -> None:
        speak = getattr(activity, "speak_text", "")
        if not allowed:
            speak = f"{speak} Ask a grown-up for this one."
        super().__init__(
            speak_text=speak,
            on_activate=on_activate,
            speech_ui=speech_ui,
            css_classes=("tile",) + (() if allowed else ("not-allowed",)),
            size=metrics.tile_size,
            key=next_key(f"tile-{getattr(activity, 'id', 'x')}"),
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)

        icon_size = int(metrics.tile_size * 0.52)
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

        label = Gtk.Label(label=getattr(activity, "name", ""))
        label.add_css_class("tile-label")
        label.set_size_request(-1, metrics.tile_label_height)
        label.set_ellipsize(3)  # Pango.EllipsizeMode.END
        label.set_max_width_chars(12)
        box.append(label)
        self.set_child(box)


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


def big_label(text: str, css: str = "big-line") -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.add_css_class(css)
    label.set_wrap(True)
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
    return carousel
