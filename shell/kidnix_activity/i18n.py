"""The activity SDK's view of the shell's translation machinery.

A first-party activity is a separate *program* and not a separate *release*
(``build_files/60-shell.sh``), so it shares the shell's gettext domain and its
catalogue rather than shipping one of its own: a child cannot tell which
process drew a sentence, and two catalogues would be two places for the same
word to be translated differently.

Everything here is a re-export of :mod:`kidnix_shell.i18n`. Use it the same
way::

    from kidnix_activity.i18n import _, N_, ngettext

    TITLE = N_("Draw something")            # module level: mark only
    button.set_label(_("Start again"))      # in a method: translate now

An activity process is started by the shell with the language already chosen
(``LANG``/``LANGUAGE`` in its environment -- see
:mod:`kidnix_shell.launcher`), so :func:`install` normally has nothing to do
beyond picking the catalogue up. Call it once at start-up anyway; it is cheap
and it makes a standalone ``python3 -m my_activity`` behave like the real
thing.

**Not translated here:** the manifest. ``name``/``audio_label`` in a
``*.toml`` are content, not code, and get per-locale keys instead --
``name_cy``, ``audio_label_pl`` -- read by the manifest loader
(:func:`kidnix_shell.activities.localised`). See docs/design/i18n.md §4.
"""

from __future__ import annotations

from kidnix_shell.i18n import (
    DEFAULT_LANGUAGE,
    DOMAIN,
    N_,
    _,
    current_language,
    gettext,
    install,
    ngettext,
    resolve_language,
    speech_language,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "DOMAIN",
    "N_",
    "_",
    "current_language",
    "gettext",
    "install",
    "ngettext",
    "resolve_language",
    "speech_language",
]
