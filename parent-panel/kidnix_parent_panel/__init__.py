"""kidnix parent panel -- the grown-up's app, on the grown-up's own desktop.

ADR-0005 put the parent on a **stock GNOME session**, so this is an ordinary
libadwaita application with adult typography and adult density: nothing here is
read aloud, nothing is 20 mm across, and nothing is a picture where a word will
do. The child's shell and this app share a machine and a config file and
nothing else.

The 2026-08-23 parent panel review is the whole brief. Four parents were shown
the same material and all four stopped at the same wall -- *"and then what do I
press?"* -- and all four found the answer was a TOML file. The top ask was "a
parent panel, even a bad one"; the second was two children on one machine; the
third a switch that keeps the grid the same and turns the sound down in one
place; the fourth a way out for the child's work; the fifth an install-and-
update story. This app is those five, in that order, in six tabs.

**Everything it changes goes through one root helper.** ``/etc/kidnix/parent.toml``
and ``/etc/kidnix/session.toml`` are root-owned on purpose -- a child-writable
PIN is not a PIN, and a child-writable session length is not a session length --
and the parent panel runs as the *parent*, who is in ``wheel`` but is not root.
So the panel never writes those files itself: it hands a JSON payload to
``/usr/bin/kidnix-config`` through ``pkexec`` (polkit action
``org.kidnix.parent-config``, wheel only, ``kid`` denied by the existing
``org.kidnix.`` prefix rule), and that helper validates the payload a second
time before it replaces anything.

Layering, deliberately:

* :mod:`~kidnix_parent_panel.model` -- pure dataclasses. No GTK, no filesystem.
* :mod:`~kidnix_parent_panel.validate` -- pure rules. Returns problems; never
  raises, never repairs silently.
* :mod:`~kidnix_parent_panel.config_io` -- renders TOML and the tts env file,
  reads them back. Pure functions over strings and dicts.
* :mod:`~kidnix_parent_panel.catalogue` -- what activities exist on this
  machine, read from ``/usr/share/kidnix/activities``.
* :mod:`~kidnix_parent_panel.system` -- every subprocess the panel runs, behind
  an injectable runner so the tests never fork anything.
* :mod:`~kidnix_parent_panel.helper` -- the root half of ``kidnix-config``.
* :mod:`~kidnix_parent_panel.ui` -- GTK. The only part that needs a display.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
