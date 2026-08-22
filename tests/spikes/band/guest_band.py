#!/usr/bin/python3
"""A stand-in for the kidnix band: one small, unmistakable GTK4 window.

Throwaway. This exists so the band-over-activity spike can test the *window
role* (a short, wide, always-above strip) without waiting for the real shell to
be split into a band window and a content window. It is deliberately dumb: a
solid colour, a big label, and nothing that could resize it.

Run in the guest as the kid user. The app id is what
``window-config.ini``'s ``match-class`` matches on: mutter sets a Wayland
window's ``wm_class`` from ``xdg_toplevel.set_app_id``, which GTK takes from
the ``GtkApplication`` id.
"""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

APP_ID = sys.argv[1] if len(sys.argv) > 1 else "org.kidnix.BandProto"
HEIGHT = int(sys.argv[2]) if len(sys.argv) > 2 else 96
COLOUR = sys.argv[3] if len(sys.argv) > 3 else "#0f8a8a"
LABEL = sys.argv[4] if len(sys.argv) > 4 else "BAND"
#: The window TITLE is what window-config.ini matches on: both shell windows
#: share one app id, so only the title can tell the band from the content.
TITLE = sys.argv[5] if len(sys.argv) > 5 else "kidnix band"

CSS = f"""
window.band {{ background: {COLOUR}; }}
label.band {{ color: #ffffff; font-size: 34px; font-weight: bold; }}
"""


def on_activate(app: Gtk.Application) -> None:
    window = Gtk.ApplicationWindow(application=app)
    window.add_css_class("band")
    window.set_decorated(False)
    window.set_title(TITLE)
    # A tiny natural size: mutter will move_resize_frame us to whatever
    # window-config.ini asks for, and a GTK window never shrinks below its own
    # minimum. Keeping the minimum small is the whole point -- the real shell's
    # band must do the same or the compositor cannot make it 96 px tall.
    window.set_default_size(1280, HEIGHT)
    label = Gtk.Label(label=LABEL)
    label.add_css_class("band")
    label.set_vexpand(True)
    window.set_child(label)

    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    window.present()


#: Optional second window, created from the SAME process once this file
#: appears. It has to be the same process: two processes sharing a
#: GtkApplication id do not get two windows, the second just re-activates the
#: first (which is what the shell will be doing anyway -- one process, one
#: GtkApplication, two toplevels that differ only by title).
TRIGGER = "/tmp/kidnix-make-content"


def add_window(app: Gtk.Application, title: str, height: int, colour: str, label: str) -> None:
    window = Gtk.ApplicationWindow(application=app)
    window.set_decorated(False)
    window.set_title(title)
    window.set_default_size(1280, height)
    provider = Gtk.CssProvider()
    provider.load_from_data(f"window.w-{abs(hash(title))} {{ background: {colour}; }}".encode())
    window.add_css_class(f"w-{abs(hash(title))}")
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    lbl = Gtk.Label(label=label)
    lbl.add_css_class("band")
    lbl.set_vexpand(True)
    window.set_child(lbl)
    window.present()


def main() -> int:
    app = Gtk.Application(application_id=APP_ID)
    app.connect("activate", on_activate)

    def poll() -> bool:
        import os

        if os.path.exists(TRIGGER):
            os.unlink(TRIGGER)
            add_window(app, "kidnix content", 704, "#c8b48c", "SHELL CONTENT (Home)")
            return False
        return True

    from gi.repository import GLib

    GLib.timeout_add(500, poll)
    return app.run([])


if __name__ == "__main__":
    raise SystemExit(main())
