"""One keyboard, two toplevels: the shell's own focus model.

**The finding this exists for.** Since v0.1.5 the band is a separate toplevel
from the content window. Tab does not cross toplevels, and
``build_files/40-lockdown.sh`` blanks all 102 mutter keybindings including
``switch-windows``. There was no ``Gtk.EventControllerKey`` anywhere in the
shell except the PIN pad, nothing called ``grab_focus()``, and the grown-up
gate's promised keyboard route was ``self.connect("clicked", lambda _b: None)``
-- a literal no-op. So Back, Undo, My Things, the Ear, the sun and the gate had
**no keyboard route at all, on any surface, ever**, and a child using a switch
or a head-pointer could not leave an activity except by waiting for the timer.

Four decisions, and the second one is the load-bearing one:

1. **One controller, both windows.** The same
   :class:`Gtk.EventControllerKey` handler is attached to the band window and
   the content window, in the capture phase, so whichever toplevel the
   compositor has focused, the key arrives here.

2. **The shell owns the focus, not GTK.** Keyboard focus is per-toplevel: only
   one of the two windows has it at a time, and ``:focus-visible`` stops
   drawing on the other -- which is precisely the half of the ring a child has
   just tabbed into. So the ring is kept here
   (:class:`~kidnix_shell.access.FocusRing`), the indicator is a CSS class the
   shell adds itself (``.kid-focus``), and **activation is dispatched by us**
   rather than by GTK's default handler. That makes Enter on Back work
   identically whether the compositor thinks the band or the content window is
   focused -- and it is why the ring is testable without synthetic input:
   :meth:`Keyboard.key` is an ordinary method a test can call.

   We do *not* call ``present()`` to move the compositor's focus with the ring.
   Presenting the content window mid-activity would raise it over the child's
   drawing, which is the one thing the band exists to avoid.

3. **Tab is one cycle, band first.** Not "Tab crosses regions, arrows move
   within one": a five-year-old, or a two-switch scan, gets one repeating
   order and the half that never changes comes first. Arrows do the same thing
   as Tab, because a child who finds the arrows should not discover a second,
   subtly different model.

4. **Escape is Back.** The same Back the band draws, with the same rules --
   including the three dead seconds on Put away. There is no other meaning of
   Escape in the shell and no dialog it has to close first.

The grown-up gate keeps its own grammar: Enter or Space *held* for three
seconds, or five presses inside three (:class:`~kidnix_shell.access.
SwitchHold`), because a switch cannot say "and keep it down".
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from .access import FocusRing  # noqa: E402
from .band import Band, HoldButton  # noqa: E402
from .widgets import ChildButton  # noqa: E402

log = logging.getLogger(__name__)

#: The class the shell paints the ring with itself. ``theme.css`` gives it the
#: same three layers as ``:focus-visible``.
FOCUS_CLASS = "kid-focus"

_NEXT = {Gdk.KEY_Tab, Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_KP_Tab}
_PREVIOUS = {Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Left, Gdk.KEY_Up}
_ACTIVATE = {Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space, Gdk.KEY_ISO_Enter}
_BACK = {Gdk.KEY_Escape, Gdk.KEY_BackSpace}


def focusables(root: Gtk.Widget | None) -> list[Gtk.Widget]:
    """Every :class:`ChildButton` under ``root``, in the order it is drawn.

    Depth-first over GTK's own child order, which for every container the
    shell uses (Box, Grid, CenterBox) is reading order.

    **A carousel contributes only the page that is showing.** Its off-screen
    pages are perfectly ordinary visible widgets as far as GTK is concerned,
    so without this a child tabbing across Home would walk off the edge of the
    page and land on a tile that is not on the screen -- which to a child
    navigating by position is the shell losing their place. The pager is how
    you change page here, exactly as it is with a pointer (A4: no free
    scrolling anywhere).
    """
    found: list[Gtk.Widget] = []
    if root is None:
        return found

    def walk(widget: Gtk.Widget) -> None:
        child = widget.get_first_child()
        while child is not None:
            if child.get_visible():
                if isinstance(child, ChildButton | HoldButton):
                    found.append(child)
                elif isinstance(child, Adw.Carousel):
                    page = current_page(child)
                    if page is not None:
                        walk(page)
                else:
                    walk(child)
            child = child.get_next_sibling()

    walk(root)
    return found


def current_page(carousel: Adw.Carousel) -> Gtk.Widget | None:
    """The page a child is actually looking at, or ``None`` if there is none."""
    count = carousel.get_n_pages()
    if count <= 0:
        return None
    index = max(0, min(count - 1, round(carousel.get_position())))
    return carousel.get_nth_page(index)


class Keyboard:
    """The shell's focus ring, its key handler, and the gate's hold.

    ``on_back`` is the shell's Back -- the same one the band's button calls --
    so Escape can never mean something Back does not.
    """

    def __init__(self, on_back: Callable[[], None]) -> None:
        self.ring = FocusRing()
        self._on_back = on_back
        self._band: Band | None = None
        self._content: Gtk.Widget | None = None
        self._focused: Gtk.Widget | None = None
        #: Set while Enter/Space is down on the grown-up gate.
        self._holding: HoldButton | None = None

    # -- wiring --

    def attach(self, window: Gtk.Widget) -> None:
        """Put the controller on a toplevel. Called for **both** windows."""
        controller = Gtk.EventControllerKey.new()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key_pressed)
        controller.connect("key-released", self._on_key_released)
        window.add_controller(controller)

    def set_surfaces(self, band: Band | None, content: Gtk.Widget | None) -> None:
        """The band and the visible screen. Called on every screen change."""
        self._band = band
        self._content = content
        self.refresh()

    def refresh(self) -> list[Gtk.Widget]:
        """Recompute the ring, keeping focus on the same widget if we can."""
        band = self._band.controls() if self._band is not None else []
        order = self.ring.rebuild(band, focusables(self._content))
        if self._focused is not None and self._focused not in order:
            self._clear_ring()
        return order

    # -- focus --

    @property
    def focused(self) -> Gtk.Widget | None:
        """What the ring is on. The test hook."""
        return self._focused

    def focus_first(self) -> Gtk.Widget | None:
        """Put focus on the screen's first control. Every ``on_enter`` does this.

        It is also free read-aloud on arrival: ``ChildButton`` speaks on focus,
        so a child who lands on "Draw" hears "Draw" without the shell saying
        anything extra.
        """
        return self._apply(self.ring.focus(self.ring.first()) or self.ring.first())

    def focus(self, widget: Gtk.Widget | None) -> Gtk.Widget | None:
        return self._apply(self.ring.focus(widget))

    def move(self, forward: bool = True) -> Gtk.Widget | None:
        return self._apply(self.ring.move(forward))

    def _apply(self, widget: Gtk.Widget | None) -> Gtk.Widget | None:
        if widget is None:
            return None
        self._clear_ring()
        self._focused = widget
        widget.add_css_class(FOCUS_CLASS)
        # Still ask GTK for focus inside the widget's own toplevel: it is what
        # makes the AT-SPI tree honest (nothing had FOCUSED after a fresh
        # Home) and what fires ChildButton's focus controller, which speaks.
        widget.grab_focus()
        return widget

    def _clear_ring(self) -> None:
        if self._focused is not None:
            self._focused.remove_css_class(FOCUS_CLASS)
        self._focused = None

    # -- keys --

    def _on_key_pressed(
        self, _c: Gtk.EventControllerKey, keyval: int, _code: int, state: Gdk.ModifierType
    ) -> bool:
        return self.key(keyval, bool(state & Gdk.ModifierType.SHIFT_MASK))

    def _on_key_released(
        self, _c: Gtk.EventControllerKey, keyval: int, _code: int, _state: Gdk.ModifierType
    ) -> None:
        if keyval in _ACTIVATE:
            self.key_released()

    def key(self, keyval: int, shift: bool = False) -> bool:
        """Handle one key. Returns True if the shell consumed it.

        A plain method, not a signal handler, because synthetic input is the
        one thing an automated test of this cannot have -- so the test drives
        the same entry point the compositor does.
        """
        if keyval in _BACK:
            self._on_back()
            return True
        if keyval == Gdk.KEY_Tab and shift:
            self.move(forward=False)
            return True
        if keyval in _NEXT:
            self.move(forward=True)
            return True
        if keyval in _PREVIOUS:
            self.move(forward=False)
            return True
        if keyval in _ACTIVATE:
            return self.activate()
        return False

    def activate(self) -> bool:
        """Enter or Space on whatever the ring is on."""
        widget = self._focused
        if widget is None:
            self.focus_first()
            return True
        if isinstance(widget, HoldButton):
            # The gate. Down starts the three seconds; up decides whether it
            # was a hold, one press of a switch pattern, or nothing.
            self._holding = widget
            return widget.key_pressed()
        if isinstance(widget, ChildButton):
            widget.fire()
            return True
        return False

    def key_released(self) -> None:
        """Enter or Space came up. Only the gate cares."""
        holding, self._holding = self._holding, None
        if holding is not None:
            holding.key_released()

    # -- lifecycle --

    def forget(self) -> None:
        """The layout was rebuilt; nothing in the old ring exists any more."""
        self._clear_ring()
        self._holding = None
        self.ring.rebuild([], [])


def names(controls: Sequence[Gtk.Widget]) -> list[str]:
    """The ring, as the strings it speaks. What the ring-order tests assert on."""
    return [str(getattr(control, "speak_text", "")) for control in controls]
