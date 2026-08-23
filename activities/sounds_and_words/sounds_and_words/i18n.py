"""Translation for this activity, and why it is not a plain re-export.

kidnix has **one** gettext domain (``kidnix``) and one catalogue, because a
child cannot tell which process drew a sentence and two catalogues would be two
places for the same word to be translated differently. So the real machinery is
:mod:`kidnix_shell.i18n`, re-exported by the SDK as
:mod:`kidnix_activity.i18n`, and this module is a two-line wrapper around that.

The two lines are the point. **The pure half of this package must import with
no SDK installed at all** -- ``tests/test_sdk.py`` runs
``python -c "import sounds_and_words"`` in a subprocess that has neither
``kidnix_activity`` on its path nor ``gi`` in its ``sys.modules``, and that is
the CI floor for the guarantee this activity carries (never show a child an
untaught grapheme). A hard ``from kidnix_activity.i18n import _`` in
:mod:`sounds_and_words.summary` or :mod:`sounds_and_words.phonemes` would make
the corpus half of the activity depend on the window half, which is the exact
split ``docs/design/activity-sdk.md`` section 2 asks for.

So: the SDK's ``_`` when there is an SDK, and the identity function when there
is not. en_GB is not a translation, it is the source (``docs/design/i18n.md``
section 0), so the fallback is not a degraded mode -- it returns the msgid,
which *is* the English sentence, byte for byte.

Use it the way the SDK asks (ADR-0012):

``_("...")``
    Translate **now**, inside a function or method, at the moment the sentence
    is shown or spoken.

``N_("...")``
    Mark for extraction and translate **later**. Module-level constants only.
    Never ``_()`` at module level: it would freeze whichever language happened
    to be installed at import time.

``xgettext`` sees the calls either way -- it reads source, not imports -- so
extraction does not care which branch a given machine took. See
``docs/design/sounds-and-words.md`` section 15 for how the strings in here
reach ``shell/po/kidnix.pot``.
"""

from __future__ import annotations

from typing import Any

__all__ = ["HAVE_CATALOGUE", "N_", "_", "gettext", "install", "ngettext"]

try:  # pragma: no cover - which branch runs depends on what is installed
    from kidnix_activity.i18n import (  # type: ignore[assignment]
        N_,
        _,
        gettext,
        install,
        ngettext,
    )

    #: Is a real catalogue reachable? Reported once at start-up so that a
    #: machine speaking English *because the SDK was missing* is a visible fact
    #: rather than a silent one.
    HAVE_CATALOGUE = True
except ImportError:  # pragma: no cover - the SDK-less CI floor

    def gettext(message: str) -> str:
        """The msgid, which in en_GB is already the sentence."""
        return message

    def _(message: str) -> str:
        """Translate now."""
        return gettext(message)

    def N_(message: str) -> str:
        """Mark for extraction; do not translate yet."""
        return message

    def ngettext(singular: str, plural: str, n: int) -> str:
        """English's own plural rule, which is the msgids' rule."""
        return singular if n == 1 else plural

    def install(*_args: Any, **_kwargs: Any) -> None:
        """Nothing to install without a catalogue."""
        return None

    HAVE_CATALOGUE = False
