"""Small shared widgets. Nothing here holds state.

The panel is almost entirely stock libadwaita rows on purpose -- a parent who
has used GNOME Settings should not have to learn a second idiom to change a
bedtime. These four helpers are the exceptions, and each exists because a
stock row cannot say the thing that has to be said: which child a row is about
(colour and shape together, never colour alone), what an activity actually
looks like on the child's screen, and which sentences are notes rather than
labels.
"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from .. import catalogue  # noqa: E402
from .. import model as M  # noqa: E402

#: One place for the sizes, so a change is one edit rather than nine.
SWATCH = 22
ICON = 32
AVATAR = 40


def identity_badge(child: M.Child, size: int = AVATAR) -> Gtk.Widget:
    """A child's colour pair **and** their shape, in one small widget.

    Never the colour on its own. Two of the four shipped palettes used to
    simulate to the same colour under deuteranopia, and about 8% of boys are
    colour-blind with most of them not knowing -- so the silhouette is not
    decoration, it is the half of "whose computer is this" that survives.
    """
    overlay = Gtk.Overlay()
    swatch = Gtk.DrawingArea()
    swatch.set_size_request(size, size)
    swatch.add_css_class("kidnix-swatch")
    primary = _rgba(child.colour_primary)
    secondary = _rgba(child.colour_secondary)

    def draw(_area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        radius = min(width, height) / 2.0
        cr.arc(width / 2.0, height / 2.0, radius, 0, 6.2832)
        cr.set_source_rgb(primary.red, primary.green, primary.blue)
        cr.fill()
        cr.arc(width / 2.0, height / 2.0, radius, 0.7854, 3.9270)
        cr.line_to(width / 2.0, height / 2.0)
        cr.set_source_rgb(secondary.red, secondary.green, secondary.blue)
        cr.fill()

    swatch.set_draw_func(draw)
    overlay.set_child(swatch)

    badge = badge_image(child.badge, max(12, size // 2))
    badge.set_halign(Gtk.Align.END)
    badge.set_valign(Gtk.Align.END)
    overlay.add_overlay(badge)
    overlay.set_tooltip_text(f"{child.colour_primary} with the {child.badge} shape")
    return overlay


def badge_image(badge: str, size: int = 16) -> Gtk.Widget:
    path = shell_icon(f"kidnix-badge-{badge}")
    if path is None:
        label = Gtk.Label(label=badge[:1].upper())
        label.add_css_class("dim-label")
        return label
    return image_from(path, size)


def activity_image(entry: catalogue.Entry, size: int = ICON) -> Gtk.Widget:
    """The picture the child sees on Home, at parent size.

    Falling back the same way the shell does -- manifest path, then one of the
    shell's own drawings, then the category picture -- so that a parent
    comparing this list with their child's screen sees the same thing. When two
    rows show the same picture, that is the icon fallback the review filed as a
    blocker, and it is worth a parent being able to see it too.
    """
    path = catalogue.icon_path(entry)
    if path is not None:
        return image_from(path, size)
    image = Gtk.Image.new_from_icon_name(entry.icon or "application-x-executable")
    image.set_pixel_size(size)
    return image


def image_from(path: Path, size: int) -> Gtk.Image:
    """An SVG at a real pixel size.

    ``Gtk.Image.new_from_file`` on an SVG renders it at its intrinsic size and
    then scales the result, which on a 24 px icon drawn at 512 is fine and on
    one drawn at 16 is a smear. Loading through ``GdkPixbuf`` at the size we
    want makes librsvg rasterise at that size instead.
    """
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(path), size, size)
        image = Gtk.Image.new_from_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
    except Exception:
        image = Gtk.Image.new_from_file(str(path))
    image.set_pixel_size(size)
    return image


def shell_icon(name: str) -> Path | None:
    folder = catalogue.shell_icon_dir()
    if folder is None:
        return None
    candidate = folder / f"{name}.svg"
    return candidate if candidate.is_file() else None


def escape(text: str) -> str:
    """Text that is about to be used where libadwaita expects Pango markup.

    Group titles and descriptions are markup; a child called "Jack & Jill" or
    an activity called "Letters & numbers" would otherwise make GTK log a parse
    error and draw nothing at all.
    """
    return GLib.markup_escape_text(str(text))


def plain(row: Adw.PreferencesRow, title: str = "", subtitle: str = "") -> Adw.PreferencesRow:
    """Say that this row's title and subtitle are TEXT, not Pango markup.

    libadwaita parses row titles as markup by default, so an activity called
    "Letters & numbers" or a child called "Jack & Jill" makes GTK log a parse
    error and draw nothing at all. Every row in this app whose text came from a
    manifest, a config file or a parent's keyboard goes through here.

    The title has to be set **after** ``use-markup`` goes false -- the parse
    happens when the property is set, so a row constructed with
    ``Adw.ActionRow(title=...)`` has already failed by the time anything else
    runs. Hence the two optional arguments: build the row empty, then come
    here.
    """
    row.set_use_markup(False)
    if title:
        row.set_title(title)
    if subtitle and hasattr(row, "set_subtitle"):
        row.set_subtitle(subtitle)
    return row


def note(text: str, *, warning: bool = False) -> Gtk.Widget:
    """A paragraph under a group: an explanation, not a label.

    The panel has a lot of these because most of its settings have a *reason*,
    and the parents' review was unambiguous that the reasons belong where the
    setting is rather than in a config file's comments ("the best argument the
    project has, in a file no parent will open").
    """
    label = Gtk.Label(label=text)
    label.set_wrap(True)
    label.set_xalign(0.0)
    label.set_margin_start(6)
    label.set_margin_end(6)
    label.set_margin_top(2)
    label.set_margin_bottom(6)
    label.add_css_class("kidnix-note")
    label.add_css_class("warning" if warning else "dim-label")
    return label


def note_row(text: str, *, warning: bool = False) -> Adw.PreferencesRow:
    """The same paragraph, when it has to live *inside* a group's list."""
    row = Adw.PreferencesRow()
    row.set_activatable(False)
    row.set_child(note(text, warning=warning))
    return row


def button(label: str, css: str = "", tooltip: str = "") -> Gtk.Button:
    widget = Gtk.Button(label=label)
    widget.set_valign(Gtk.Align.CENTER)
    if css:
        widget.add_css_class(css)
    if tooltip:
        widget.set_tooltip_text(tooltip)
    return widget


def icon_button(icon: str, tooltip: str, css: str = "flat") -> Gtk.Button:
    widget = Gtk.Button()
    widget.set_icon_name(icon)
    widget.set_valign(Gtk.Align.CENTER)
    widget.set_tooltip_text(tooltip)
    if css:
        widget.add_css_class(css)
    return widget


def _rgba(colour: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if not rgba.parse(colour):
        rgba.parse("#888888")
    return rgba


__all__ = [
    "AVATAR",
    "ICON",
    "SWATCH",
    "activity_image",
    "badge_image",
    "button",
    "escape",
    "icon_button",
    "identity_badge",
    "image_from",
    "note",
    "note_row",
    "plain",
    "shell_icon",
]
