"""The focus ring, for an activity. Escape is **not** ours.

The accessibility review's B1 is that the shell is operable without a pointer,
and an activity inherits the obligation: Tab and the arrow keys walk the
controls in reading order, Enter and Space press the one the ring is on, and
the ring is painted by us (``kid-focus``) as well as by GTK, because
``:focus-visible`` stops drawing on a toplevel the compositor has taken focus
away from -- and under gnome-kiosk there is always another toplevel.

The one difference from :class:`kidnix_shell.keyboard.Keyboard` is the whole
reason this is a separate class:

**Escape belongs to the shell.** Back is a band button, in a fixed position, in
another process, and it is the *only* way out of an activity by design (spec
S3). An activity that handled Escape would have invented a second way out that
is invisible, unlabelled, unspoken and impossible for a pre-reader to discover
-- and, worse, one that could mean something Back does not. So Escape is
allowed to fall through, untouched, and this class never consumes it.

The key handler is a plain method as well as a signal handler, because
synthetic input is the one thing an automated test of this cannot have: the
test drives the same entry point the compositor does.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from kidnix_shell.access import FocusRing  # noqa: E402
from kidnix_shell.keyboard import FOCUS_CLASS  # noqa: E402
from kidnix_shell.widgets import ChildButton  # noqa: E402

__all__ = ["FOCUS_CLASS", "ActivityKeyboard", "focusables"]

_NEXT = {Gdk.KEY_Tab, Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_KP_Tab}
_PREVIOUS = {Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Left, Gdk.KEY_Up}
_ACTIVATE = {Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space, Gdk.KEY_ISO_Enter}


def focusables(root: Gtk.Widget | None) -> list[Gtk.Widget]:
    """Every :class:`ChildButton` under ``root``, in the order it is drawn.

    Depth-first over GTK's own child order, which for Box, Grid and CenterBox
    is reading order. A carousel contributes only the page that is showing --
    tabbing off the edge of a page onto a control that is not on the screen is,
    to a child navigating by position, the activity losing their place.
    """
    found: list[Gtk.Widget] = []
    if root is None:
        return found

    def walk(widget: Gtk.Widget) -> None:
        child = widget.get_first_child()
        while child is not None:
            if child.get_visible():
                if isinstance(child, ChildButton):
                    found.append(child)
                elif isinstance(child, Adw.Carousel):
                    count = child.get_n_pages()
                    if count > 0:
                        index = max(0, min(count - 1, round(child.get_position())))
                        page = child.get_nth_page(index)
                        if page is not None:
                            walk(page)
                else:
                    walk(child)
            child = child.get_next_sibling()

    walk(root)
    return found


class ActivityKeyboard:
    """One ring over one window. No Escape, no chords, no modifiers."""

    def __init__(self) -> None:
        self.ring = FocusRing()
        self._root: Gtk.Widget | None = None
        self._focused: Gtk.Widget | None = None

    # -- wiring --

    def attach(self, window: Gtk.Widget) -> None:
        controller = Gtk.EventControllerKey.new()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key_pressed)
        window.add_controller(controller)

    def set_content(self, content: Gtk.Widget | None) -> list[Gtk.Widget]:
        """The visible tree. Call it whenever the activity rebuilds one."""
        self._root = content
        return self.refresh()

    def refresh(self) -> list[Gtk.Widget]:
        """Recompute the ring, dropping focus if what held it has gone."""
        order = self.ring.rebuild([], focusables(self._root))
        if self._focused is not None and self._focused not in order:
            self._clear_ring()
        return order

    # -- focus --

    @property
    def focused(self) -> Gtk.Widget | None:
        return self._focused

    def focus_first(self) -> Gtk.Widget | None:
        """Land on the first control. Free read-aloud: it speaks on focus."""
        return self._apply(self.ring.focus(self.ring.first()) or self.ring.first())

    def move(self, forward: bool = True) -> Gtk.Widget | None:
        return self._apply(self.ring.move(forward))

    def _apply(self, widget: Gtk.Widget | None) -> Gtk.Widget | None:
        if widget is None:
            return None
        self._clear_ring()
        self._focused = widget
        widget.add_css_class(FOCUS_CLASS)
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

    def key(self, keyval: int, shift: bool = False) -> bool:
        """Handle one key. Returns True only if the activity consumed it."""
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
        # Everything else -- Escape above all -- belongs to somebody else.
        return False

    def activate(self) -> bool:
        widget = self._focused
        if widget is None:
            self.focus_first()
            return True
        if isinstance(widget, ChildButton):
            widget.fire()
            return True
        return False

    def forget(self) -> None:
        """The layout was rebuilt; nothing in the old ring exists any more."""
        self._clear_ring()
        self.ring.rebuild([], [])
