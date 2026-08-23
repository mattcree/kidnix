"""Which language the child's computer speaks (ADR-0012, docs/design/i18n.md).

*docs/research/06 §4.7* is the reason this module exists and not a wish list:
**23.8% of English primary pupils have a first language other than English**
(DfE, Jan 2026 census), Polish is the largest of them (612,000 speakers,
Census 2021), and **Welsh has fallen 6.0 percentage points among 5-15 year
olds** -- kidnix's exact age group. A UK children's OS that can only be
English is a UK children's OS for three quarters of the households in it.

What this module is
===================

Plain GNU gettext, domain ``kidnix``. Nothing clever: the msgids **are** the
en_GB strings, so a machine with no ``.mo`` file anywhere gets
:class:`gettext.NullTranslations` and every sentence comes back byte-identical
to what it was before this module existed. That is the property the whole
design is arranged around -- en_GB is not a translation, it is the source.

Two ways to say "this string is translatable", and the difference matters:

``_("...")``
    Translate **now**. Right inside a function or a method, where "now" is the
    moment the sentence is shown or spoken.

``N_("...")``
    Mark for extraction, translate **later**. Right at module level, where a
    constant is built once at import time -- long before anybody knows which
    child is sitting down. The constant holds the msgid; the *use site* calls
    ``_()`` on it. This is the deferred-translation idiom from the Python
    ``gettext`` docs, and it is why ``RESTING_TITLE`` and friends are still
    module constants that a test can import and compare.

The one rule: **never** ``_()`` at module level. A module-level ``_()`` freezes
whatever language happened to be installed when Python first imported the file,
which on a profile switch is the wrong one and in a test is whatever ran first.

Where the catalogues live
=========================

``/usr/share/locale/<lang>/LC_MESSAGES/kidnix.mo`` in the image (written by
``build_files/60-shell.sh`` from ``shell/po/*.po``), and
``shell/po/<lang>/LC_MESSAGES/kidnix.mo`` in a developer checkout, so
``just po-compile && just demo`` is the whole loop. Both are searched, image
first.

Where the language comes from
=============================

In order, first non-empty wins:

1. the **active profile's** ``language`` (``[[profiles]] language = "cy"``) --
   because a bilingual household is a household where the *children* differ,
   not just the machine;
2. ``[access] language`` in ``parent.toml`` -- the machine's answer;
3. the environment (``LANGUAGE``, ``LC_ALL``, ``LC_MESSAGES``, ``LANG``);
4. :data:`DEFAULT_LANGUAGE`.

Read-aloud follows the same answer: :func:`speech_language` turns it into the
tag speech-dispatcher wants, and :mod:`kidnix_shell.speech` sends it with
``SET SELF LANGUAGE``. Captions are the text that was spoken, so they follow
for free.

**What a profile switch does.** Text strings that are already on screen do not
change by themselves -- a GTK label is a string that was built once. The shell
therefore reinstalls the catalogue and asks the window to **rebuild its
screens** when, and only when, the incoming profile's language differs from the
one in force (:meth:`kidnix_shell.app.ShellWindow._use_profile`). A
same-language switch -- which is every switch on a monolingual machine -- does
nothing at all, so the en_GB path is exactly the code it was before.
"""

from __future__ import annotations

import gettext as _gettext
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

#: The gettext domain. One catalogue for the shell and the activity SDK: they
#: are one release (see ``build_files/60-shell.sh``) and a child cannot tell
#: which process drew a sentence.
DOMAIN = "kidnix"

#: What the msgids are written in. Not a translation -- the source.
DEFAULT_LANGUAGE = "en_GB"

#: The image's catalogues.
SYSTEM_LOCALE_DIR = Path("/usr/share/locale")

#: A developer checkout's, written by ``just po-compile`` beside the ``.po``
#: files they came from. ``shell/po/pl/LC_MESSAGES/kidnix.mo``.
DEV_LOCALE_DIR = Path(__file__).resolve().parent.parent / "po"

#: Environment variables gettext itself honours, in gettext's own order.
ENV_VARS = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")

# The installed catalogue. Starts as "no catalogue", which returns every msgid
# unchanged -- i.e. en_GB -- so importing kidnix_shell without ever calling
# install() behaves exactly as it did before there was an i18n module.
_translation: _gettext.NullTranslations = _gettext.NullTranslations()
_current: str = DEFAULT_LANGUAGE


def locale_dirs() -> list[Path]:
    """Where to look for ``kidnix.mo``, image first, checkout second."""
    return [SYSTEM_LOCALE_DIR, DEV_LOCALE_DIR]


def normalise(language: str) -> str:
    """``"pl_PL.UTF-8@x"`` -> ``"pl_PL"``. Empty in, empty out."""
    text = (language or "").strip()
    for separator in (".", "@"):
        text = text.split(separator, 1)[0]
    return text.replace("-", "_")


def candidates(language: str) -> list[str]:
    """``"pl_PL"`` -> ``["pl_PL", "pl"]``: the catalogues to try, best first."""
    name = normalise(language)
    if not name:
        return []
    found = [name]
    if "_" in name:
        found.append(name.split("_", 1)[0])
    return found


def language_from_env(env: dict[str, str] | None = None) -> str:
    """The first of :data:`ENV_VARS` that says something. ``"C"`` says nothing."""
    environ = os.environ if env is None else env
    for var in ENV_VARS:
        value = normalise(environ.get(var, ""))
        # LANGUAGE is a colon-separated *list*; we want its first entry.
        value = value.split(":", 1)[0]
        if value and value not in {"C", "POSIX"}:
            return value
    return ""


def resolve_language(
    profile_language: str = "",
    access_language: str = "",
    env: dict[str, str] | None = None,
) -> str:
    """Profile, then machine, then environment, then :data:`DEFAULT_LANGUAGE`.

    Pure and total, so ``tests/test_i18n.py`` can hold the precedence without a
    display, a config file or an environment.
    """
    for value in (profile_language, access_language, language_from_env(env)):
        name = normalise(value)
        if name:
            return name
    return DEFAULT_LANGUAGE


def install(language: str = "", localedirs: list[Path] | None = None) -> str:
    """Put a catalogue in force. Returns the language actually installed.

    A language with no catalogue is **not** an error and not a warning a parent
    would understand: it falls back to the msgids, which is en_GB, which is a
    computer that works. It is logged once at INFO so the reason is in the
    journal.
    """
    global _translation, _current
    name = normalise(language) or DEFAULT_LANGUAGE
    wanted = candidates(name)
    for directory in localedirs or locale_dirs():
        try:
            _translation = _gettext.translation(DOMAIN, localedir=str(directory), languages=wanted)
        except OSError:
            continue
        _current = name
        log.info("language %s from %s", name, directory)
        return name
    _translation = _gettext.NullTranslations()
    _current = name
    if name != DEFAULT_LANGUAGE:
        log.info(
            "no %s catalogue for domain %r; using the source strings (%s)",
            name,
            DOMAIN,
            DEFAULT_LANGUAGE,
        )
    return name


def current_language() -> str:
    """What :func:`install` last put in force."""
    return _current


def has_catalogue() -> bool:
    """True when a real ``.mo`` is in force rather than the source strings."""
    return isinstance(_translation, _gettext.GNUTranslations)


def speech_language(language: str = "") -> str:
    """The tag speech-dispatcher wants: ``"en_GB"`` -> ``"en-GB"``, ``"cy"`` -> ``"cy"``.

    SSIP's ``SET SELF LANGUAGE`` takes an RFC-1766-ish tag, and
    ``python3-speechd``'s ``set_language`` passes it straight through. The
    default is ``en-GB``, unchanged from before this module existed.
    """
    parts = normalise(language or _current).split("_")
    if len(parts) >= 2 and parts[1]:
        return f"{parts[0].lower()}-{parts[1].upper()}"
    return parts[0].lower()


def gettext(message: str) -> str:
    """Translate ``message`` **now**, in the language currently installed."""
    return _translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Pick the form ``n`` needs, by the catalogue's own ``Plural-Forms``.

    Welsh has six forms and Polish has three or four; neither is expressible as
    "singular or plural", which is exactly why every counted sentence in the
    shell goes through here rather than through ``if count == 1``.
    """
    return _translation.ngettext(singular, plural, n)


def N_(message: str) -> str:
    """Mark ``message`` for extraction without translating it yet.

    For module-level constants. The value is the msgid, unchanged; the use site
    calls :func:`gettext` on it. See the module docstring.
    """
    return message


def NP_(singular: str, plural: str) -> tuple[str, str]:
    """Mark a **plural pair** for extraction without translating it yet.

    The module-level companion to :func:`ngettext`, and the reason it exists is
    mechanical: ``xgettext`` builds a ``msgid_plural`` entry only when it can
    see both strings *in the call*, and a constant declared at module level is
    not in any call. ``NP_("{count} thing", "{count} things")`` is a call it
    can see, and it returns the pair unchanged for the use site to hand to
    :func:`ngettext`::

        THINGS = NP_("{count} thing", "{count} things")
        ...
        ngettext(*THINGS, count).format(count=word)

    Without it the two strings land in the catalogue as two *singular* entries
    and Welsh's six forms have nowhere to live.
    """
    return (singular, plural)


#: The conventional short name. It is a *function that looks up the installed
#: catalogue at call time*, so rebinding the catalogue (a profile switch, a
#: test) changes what it returns without anything re-importing.
_ = gettext

__all__ = [
    "DEFAULT_LANGUAGE",
    "DEV_LOCALE_DIR",
    "DOMAIN",
    "N_",
    "SYSTEM_LOCALE_DIR",
    "_",
    "candidates",
    "current_language",
    "gettext",
    "has_catalogue",
    "install",
    "language_from_env",
    "locale_dirs",
    "ngettext",
    "normalise",
    "resolve_language",
    "speech_language",
]
