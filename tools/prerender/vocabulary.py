"""What the shell says, enumerated from the shell rather than kept beside it.

``docs/spikes/tts-kokoro.md`` §7.1 asks for exactly this and says why: a list of
strings maintained *next to* the code is a list that goes stale on the first
commit nobody thinks about, and the symptom -- one label that suddenly changes
voice mid-session -- is inaudible to every test that only asks whether something
was said. So the vocabulary is derived, three ways, and the build stage fails if
the derivation finds nothing.

Where the strings come from
---------------------------

1. **The gettext catalogue.** Every ``_()``/``N_()``/``NP_()``/``ngettext()``
   literal in ``kidnix_shell`` and ``kidnix_activity``, read out of the Python
   source with :mod:`ast` rather than out of ``po/kidnix.pot``. The ``.pot`` is
   a *snapshot* and was measurably stale on 2026-08-23 (twelve marked literals
   in ``resting.py``, including the whole weekday table, were missing from it);
   an AST walk cannot be. The ``.pot`` is still read when it is there, and its
   msgids are unioned in, because a literal that has left the source but is
   still in a shipped catalogue is a string a translated profile can produce.

2. **The activity manifests.** ``name``, ``audio_label`` and the two
   ``shelf_group_*`` keys out of ``/usr/share/kidnix/activities/*.toml`` and
   the GCompris shelf's ``curated.toml``. These are *not* gettext strings --
   ``docs/design/i18n.md`` §4 gives manifests per-locale suffix keys instead --
   so nothing in the catalogue would ever have found them, and they are the
   labels a child hovers most.

3. **Two closed-set expansions**, and only two. The rule for a ``{placeholder}``
   is skip it, because a template's fillings are open in general and a clip for
   a sentence nobody can utter is dead weight. Two templates are exceptions
   because their fillings are *closed sets defined in the shell's own
   module-level constants*, and both are sentences a child hears constantly:

       "Ready to {phrase}?"                  x 8 next_after phrases
       "... Back {day}."                     x 7 weekday words

   Both are expanded by importing the module and reading the tuple, so a new
   next_after option or a renamed weekday cannot leave a clip behind.

Everything else with a ``{`` in it is left to the runtime backend
(``shell/kidnix_shell/speech.py``), which is the current behaviour and
therefore a silent, working fallback rather than a failure.

Language
--------

**en_GB only, on purpose.** Kokoro v1.0 has no Welsh and no Polish voice at
all, and rendering a Welsh msgstr with a British English voice would mispronounce
the very letters ADR-0012 exists to get right. ``prerendered.py`` keys its
lookup on the *current* speech language, so a Welsh profile finds no index and
goes to Piper/espeak-ng for everything -- which is exactly what it does today.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import tomllib

#: gettext call names whose first (and for plurals, second) argument is a msgid.
#: Matches the ``xgettext`` keywords in ``shell/Justfile``'s ``po-extract``.
SINGULAR_KEYWORDS = frozenset({"_", "N_", "gettext"})
PLURAL_KEYWORDS = frozenset({"NP_", "ngettext"})

#: The manifest keys the shell can hand to :meth:`SpeechManager.speak`.
#: ``Activity.speak_text`` is ``audio_label or name``; ``ShelfGroup.speak_text``
#: is the same over the two ``shelf_group_*`` keys. ``goal`` is grown-up prose
#: on the grown-up sheet and is never spoken to the child, so it is not here.
MANIFEST_SPOKEN_KEYS = ("name", "audio_label", "shelf_group_name", "shelf_group_audio_label")

#: A string with one of these in it is a template, not an utterance.
PLACEHOLDER = re.compile(r"[{}]")

#: Nothing shorter than this is worth a file, and an empty msgid is the
#: catalogue header.
MIN_LENGTH = 1

#: A hard ceiling on any one clip's text. Kokoro's style table is 510 rows and
#: a string past ~400 characters cannot be rendered in one pass; the shell has
#: nothing that long, so this is a tripwire, not a splitter.
MAX_LENGTH = 400


@dataclass
class Vocabulary:
    """The strings to render, and where each of them came from."""

    #: text -> the sources that asked for it, for the build log and the index.
    entries: dict[str, set[str]] = field(default_factory=dict)
    #: Strings deliberately left to the runtime backend, with the reason.
    skipped: dict[str, str] = field(default_factory=dict)

    def add(self, text: str, source: str) -> None:
        text = (text or "").strip()
        if len(text) < MIN_LENGTH:
            return
        if PLACEHOLDER.search(text):
            # The constraint, as written: a template goes to Piper.
            self.skipped.setdefault(text, "placeholder")
            return
        if len(text) > MAX_LENGTH:
            self.skipped.setdefault(text, "too long")
            return
        self.entries.setdefault(text, set()).add(source)

    @property
    def texts(self) -> list[str]:
        """Sorted, so a rebuild of the same tree renders the same list."""
        return sorted(self.entries)


# --- 1. the catalogue, from the source ---------------------------------------


def _literal(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def msgids_in_source(source: str) -> list[str]:
    """Every literal msgid in one Python file.

    Handles the four keywords ``shell/Justfile``'s ``po-extract`` passes to
    ``xgettext``. A call whose argument is a name rather than a literal is
    skipped silently: it is a *use* of a msgid marked somewhere else, and that
    somewhere else is in this same walk.
    """
    found: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name in SINGULAR_KEYWORDS and node.args:
            text = _literal(node.args[0])
            if text is not None:
                found.append(text)
        elif name in PLURAL_KEYWORDS and len(node.args) >= 2:
            for argument in node.args[:2]:
                text = _literal(argument)
                if text is not None:
                    found.append(text)
    return found


def from_python(roots: list[Path], vocabulary: Vocabulary) -> int:
    count = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for text in msgids_in_source(path.read_text(encoding="utf-8")):
                vocabulary.add(text, "catalogue")
                count += 1
    return count


#: ``msgid "..."`` and its continuation lines, in a .po/.pot file.
_MSGID = re.compile(r'^msgid(?:_plural)?\s+"(.*)"\s*$')
_CONTINUATION = re.compile(r'^"(.*)"\s*$')


def from_pot(path: Path, vocabulary: Vocabulary) -> int:
    """Union in a ``.pot``'s msgids. Belt to the AST walk's braces."""
    if not path.is_file():
        return 0
    count = 0
    current: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        head = _MSGID.match(line)
        if head is not None:
            if current is not None:
                vocabulary.add(_unescape("".join(current)), "catalogue")
                count += 1
            current = [head.group(1)]
            continue
        tail = _CONTINUATION.match(line)
        if tail is not None and current is not None:
            current.append(tail.group(1))
            continue
        if current is not None:
            vocabulary.add(_unescape("".join(current)), "catalogue")
            count += 1
            current = None
    if current is not None:
        vocabulary.add(_unescape("".join(current)), "catalogue")
        count += 1
    return count


def _unescape(text: str) -> str:
    return text.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


# --- 2. the activity manifests -----------------------------------------------


def from_manifests(directories: list[Path], vocabulary: Vocabulary) -> int:
    """``name``/``audio_label`` out of every manifest and every shelf child.

    Read with :mod:`tomllib` rather than through
    :func:`kidnix_shell.activities.load_activities`, because the loader filters
    on whether the program is actually installed and the build stage runs
    before some of them are. A tile whose activity is missing costs one clip.
    """
    count = 0
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.toml")):
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                continue
            count += _from_manifest_table(data, path.name, vocabulary)
            # curated.toml holds `[[groups]]` and `[[activities]]`; a plain
            # manifest holds neither and this loop does nothing.
            for key in ("groups", "activities"):
                for entry in data.get(key, []) or []:
                    if isinstance(entry, dict):
                        count += _from_manifest_table(entry, path.name, vocabulary)
    return count


def _from_manifest_table(data: dict, source: str, vocabulary: Vocabulary) -> int:
    count = 0
    for key in MANIFEST_SPOKEN_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            vocabulary.add(value, f"manifest:{source}")
            count += 1
    return count


# --- 3. the two closed-set expansions ----------------------------------------


def from_shell_constants(vocabulary: Vocabulary) -> int:
    """Import the shell and read its own tuples. Never guesses at a value.

    Both imports are headless -- ``next_after`` and ``resting`` are pure logic
    with no ``gi`` in them, which ``shell/tests/`` already relies on. If the
    shell is not importable (a developer running this outside the image and
    outside the checkout) the expansions are skipped and the build stage says
    so, rather than falling back to a hardcoded list that could drift.
    """
    count = 0
    try:
        from kidnix_shell import next_after as next_after_module
        from kidnix_shell import resting as resting_module
    except ImportError:
        return 0

    # "Ready to go outside?" and its seven siblings. `ready_line` is the
    # property the screen actually speaks, so the expansion is the shell's own
    # code rather than our copy of its format string. The "Not sure" option is
    # excluded by its own `skips`: it has no phrase, so its `ready_line` is
    # the ungrammatical "Ready to not sure?", and Goodbye asks the question of
    # a destination rather than of the way out of being asked.
    for option in next_after_module.DEFAULT_NEXT_AFTER:
        if option.skips:
            continue
        line = option.ready_line
        if line:
            vocabulary.add(line, "next_after")
            count += 1

    # "... Back on Saturday." Both templates, over the seven weekday words.
    # The `after tea` and `tomorrow` phrasings are whole msgids of their own
    # and were already collected by the AST walk.
    for template in (resting_module.RESTING_ON_DAY, resting_module.OUT_OF_HOURS_ON_DAY):
        for day in resting_module.WEEKDAY_WORDS:
            vocabulary.add(template.format(day=day), "resting")
            count += 1
    return count


# --- 4. bare numbers ---------------------------------------------------------

#: 0-20 as digits. The *words* ("nothing", "one" ... "twenty") are
#: ``N_``-marked in ``kidnix_shell/words.py`` and arrive with the catalogue;
#: these are the other spelling. ``feedback.count_phrase`` falls through to
#: ``str(count)`` above its "lots of" ceiling, and a number is the one thing a
#: five-year-old's ear is least forgiving about, so 21 clips of ~3 kB buy the
#: whole range rather than leave the tail to espeak-ng.
MAX_NUMBER = 20


def from_numbers(vocabulary: Vocabulary) -> int:
    for value in range(MAX_NUMBER + 1):
        vocabulary.add(str(value), "number")
    return MAX_NUMBER + 1


# --- assembly ----------------------------------------------------------------


def collect(
    *,
    python_roots: list[Path],
    pot: Path | None = None,
    manifest_dirs: list[Path] | None = None,
    numbers: bool = True,
) -> Vocabulary:
    vocabulary = Vocabulary()
    from_python(python_roots, vocabulary)
    if pot is not None:
        from_pot(pot, vocabulary)
    if manifest_dirs:
        from_manifests(manifest_dirs, vocabulary)
    from_shell_constants(vocabulary)
    if numbers:
        from_numbers(vocabulary)
    return vocabulary
