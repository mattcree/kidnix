#!/usr/bin/env python3
"""Check that the venv can see the system GTK stack. Run by `just setup`.

PyGObject, GTK4, libadwaita and speechd come from the system, not from PyPI --
see README.md. If this fails, the venv was created without
--system-site-packages, or the packages are not installed.
"""

from __future__ import annotations

import sys


def main() -> int:
    problems: list[str] = []

    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gtk

        print(
            f"GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}, "
            f"libadwaita {Adw.get_major_version()}.{Adw.get_minor_version()}."
            f"{Adw.get_micro_version()}"
        )
    except Exception as exc:
        problems.append(f"PyGObject / GTK4 / libadwaita: {exc}")

    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf  # noqa: F401

        print("GdkPixbuf: yes (journal thumbnails)")
    except Exception:
        print("GdkPixbuf: no -- the Journal will fall back to activity icons")

    try:
        import speechd  # noqa: F401

        print("speechd bindings: yes")
    except Exception:
        import shutil

        if shutil.which("spd-say"):
            print("speechd bindings: no, but spd-say is present (fallback backend)")
        else:
            print("speechd bindings: no, spd-say: no -- read-aloud will be silent")

    if problems:
        print("\n".join(problems), file=sys.stderr)
        print(
            "\nCreate the venv with --system-site-packages, and on Fedora:\n"
            "  sudo dnf install python3-gobject gtk4 libadwaita python3-speechd",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
