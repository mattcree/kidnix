"""Internationalisation: the plumbing, the guard, and one language end to end.

Three separate claims, and they fail in three different ways:

* **The plumbing** (:func:`kidnix_shell.i18n.resolve_language` and friends).
  Pure functions, so the precedence -- profile, then machine, then environment
  -- is a table and not a boot.
* **The guard** (:func:`test_no_child_facing_string_escapes_gettext`). Walks
  the AST of every file that talks to a child and fails on a literal that is
  not inside ``_()``, ``N_()``, ``NP_()`` or ``ngettext()``. This is the test
  that keeps the catalogue honest six months from now: a new sentence added to
  Home in a hurry is caught here rather than by a Welsh family.
* **The round trip** (``LANGUAGE=pl``). Compiles nothing and mocks nothing: it
  installs ``po/pl/LC_MESSAGES/kidnix.mo``, which ``just po-compile`` built
  from ``po/pl.po``, and asserts that a label comes out Polish and that the
  **plural rule in the catalogue's own header** is what chooses the noun.

en_GB is the source, not a translation, so every one of these also asserts the
thing that matters most: with no catalogue installed the shell says exactly
what it said before ADR-0012.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from kidnix_shell import i18n
from kidnix_shell.feedback import MadeSummary, count_phrase, descriptive_line
from kidnix_shell.screens.home import HOME_INTRO
from kidnix_shell.words import number_word

PACKAGE = Path(__file__).resolve().parents[1] / "kidnix_shell"
PO_DIR = Path(__file__).resolve().parents[1] / "po"


@pytest.fixture(autouse=True)
def _english_again() -> object:
    """Every test in this file leaves the shell speaking en_GB again.

    The catalogue is process-global (it is what ``_()`` reads), so a test that
    installed Polish and did not put it back would make the *next* test file
    fail somewhere unrelated and unrepeatably.
    """
    yield
    i18n.install(i18n.DEFAULT_LANGUAGE)


# --- where the language comes from ---------------------------------------


def test_the_profile_wins_over_the_machine_and_the_machine_over_the_environment() -> None:
    env = {"LANG": "en_GB.UTF-8"}
    assert i18n.resolve_language("cy", "pl", env) == "cy"
    assert i18n.resolve_language("", "pl", env) == "pl"
    assert i18n.resolve_language("", "", env) == "en_GB"
    assert i18n.resolve_language("", "", {}) == i18n.DEFAULT_LANGUAGE


def test_the_environment_is_read_in_gettexts_own_order() -> None:
    assert i18n.language_from_env({"LANGUAGE": "pl:en", "LANG": "cy"}) == "pl"
    assert i18n.language_from_env({"LC_ALL": "pl_PL.UTF-8", "LANG": "cy"}) == "pl_PL"
    # "C" is not a language a child speaks.
    assert i18n.language_from_env({"LANG": "C"}) == ""
    assert i18n.language_from_env({}) == ""


def test_a_locale_is_normalised_before_anything_looks_it_up() -> None:
    assert i18n.normalise("pl_PL.UTF-8@euro") == "pl_PL"
    assert i18n.normalise("en-GB") == "en_GB"
    assert i18n.normalise("") == ""
    assert i18n.candidates("pl_PL") == ["pl_PL", "pl"]
    assert i18n.candidates("cy") == ["cy"]


def test_the_voice_follows_the_shell_and_en_gb_is_unchanged() -> None:
    """speech-dispatcher's tag, which is what ``SET SELF LANGUAGE`` takes."""
    assert i18n.speech_language("en_GB") == "en-GB"
    assert i18n.speech_language("cy") == "cy"
    assert i18n.speech_language("pl_PL") == "pl-PL"


def test_a_language_with_no_catalogue_is_english_and_not_a_crash() -> None:
    i18n.install("xx_XX")
    assert i18n.current_language() == "xx_XX"
    assert not i18n.has_catalogue()
    assert i18n._(HOME_INTRO) == "Home. What shall we make?"


# --- the round trip, against the compiled sample catalogue ----------------

pl_catalogue = pytest.mark.skipif(
    not (PO_DIR / "pl" / "LC_MESSAGES" / "kidnix.mo").is_file(),
    reason="run `just po-compile` first (po/pl/LC_MESSAGES/kidnix.mo is missing)",
)


@pl_catalogue
def test_polish_changes_a_label_and_leaves_the_untranslated_ones_alone() -> None:
    i18n.install("pl", localedirs=[PO_DIR])
    assert i18n.has_catalogue()
    assert i18n._(HOME_INTRO) == "Dom. Co zrobimy?"
    # po/pl.po is deliberately partial: a string nobody has translated falls
    # back to the msgid, which is en_GB, per *string* and not per file.
    assert i18n._("Nothing to undo.") == "Nothing to undo."


@pl_catalogue
def test_polish_picks_the_noun_by_its_own_plural_rule() -> None:
    """Three forms, and the rule is the catalogue's, not ours.

    ``nplurals=3``: 1 takes the first form, 2-4 the second, 5+ (and 11-14) the
    third. An ``if count == 1`` could not produce this and that is the point.
    """
    i18n.install("pl", localedirs=[PO_DIR])
    assert count_phrase(1).endswith("rzecz")
    assert count_phrase(2).endswith("rzeczy")
    assert count_phrase(5).endswith("rzeczy")
    # The number in front of it is a word, in Polish, from words.py.
    assert count_phrase(2).startswith("dwa")
    assert number_word(3) == "trzy"


@pl_catalogue
def test_the_goodbye_sentence_is_reordered_by_the_catalogue() -> None:
    """Named placeholders, so a translator may move the verb. Polish does."""
    i18n.install("pl", localedirs=[PO_DIR])
    line = descriptive_line(MadeSummary(2, "drew", "picture", "pictures", colours=None))
    assert line == "Narysowałeś dwa obrazki."


@pytest.mark.skipif(
    not (PO_DIR / "cy" / "LC_MESSAGES" / "kidnix.mo").is_file(),
    reason="run `just po-compile` first",
)
def test_welsh_has_six_plural_forms_and_uses_more_than_two_of_them() -> None:
    """The reason ngettext is not optional (docs/design/i18n.md section 2)."""
    i18n.install("cy", localedirs=[PO_DIR])
    forms = {count_phrase(n).split(" ", 1)[1] for n in (1, 2, 3, 5)}
    assert len(forms) >= 3, forms


def test_english_is_byte_identical_with_the_catalogues_available() -> None:
    """The claim ADR-0012 is arranged around, asserted rather than assumed."""
    i18n.install("en_GB", localedirs=[PO_DIR])
    assert i18n._(HOME_INTRO) == "Home. What shall we make?"
    assert count_phrase(2) == "two things"
    assert descriptive_line(MadeSummary(2, "drew", "picture", "pictures", 5)) == (
        "You drew two pictures and used five colours."
    )


# --- the guard: no child-facing literal escapes gettext -------------------

#: Every file whose strings a child reads or hears. The grown-up sheet is
#: covered by the same rule in :mod:`kidnix_shell.screens` below; it is an
#: adult surface, but a Polish household's adult is a Polish adult.
GUARDED = (
    "band.py",
    "ritual.py",
    "resting.py",
    "feedback.py",
    "suggestions.py",
    "next_after.py",
    "sun.py",
    "words.py",
    *(f"screens/{path.name}" for path in sorted((PACKAGE / "screens").glob("*.py"))),
)

#: The four ways to say "this string is translatable".
WRAPPERS = frozenset({"_", "N_", "NP_", "ngettext"})

#: Calls whose string arguments are never child-facing.
NEVER_SPOKEN = frozenset(
    {
        # logging, at every level
        "debug",
        "info",
        "warning",
        "error",
        "exception",
        "critical",
        "log",
        # GTK/libadwaita plumbing that takes names, not sentences
        "add_css_class",
        "remove_css_class",
        "has_css_class",
        "require_version",
        "gi",
        "next_key",
        "icon_image",
        "getattr",
        "setattr",
        "hasattr",
        "add_named",
        "set_visible_child_name",
        "get_visible_child_name",
        "new_from_file",
        "add_controller",
        "connect",
        "set_content_fit",
        "set_icon_name",
        "compile",
        "match",
        "search",
        "startswith",
        "endswith",
        "split",
        "join",
        "strip",
        "replace",
        "get",
        "glob",
        "warns",
        "raises",
    }
)

#: What a non-sentence looks like. Anything matching one of these is chrome --
#: a CSS class, an icon name, an id, a colour, a format spec -- and is exempt.
NOT_A_SENTENCE = (
    re.compile(r"^$"),  # empty
    re.compile(r"^[a-z0-9][a-z0-9._-]*$"),  # slug: css class, id, icon name
    re.compile(r"^#[0-9a-fA-F]{3,8}$"),  # a colour
    re.compile(r"^[^A-Za-z]*$"),  # punctuation, digits, whitespace only
    re.compile(r"^[A-Z][A-Za-z0-9_]*$"),  # a bare identifier (__all__, enums)
    re.compile(r"^%[-#0-9. ]*[a-zA-Z]"),  # a printf spec
    re.compile(r"^\.[a-z][a-z0-9.-]*$"),  # a CSS selector: ".big-line"
    re.compile(r"^[a-z]+(\.[a-z-]+)+$"),  # a CSS selector: "button.ritual"
    re.compile(r"^_[A-Za-z0-9_]*$"),  # a private attribute name
    re.compile(r"^--?[a-z][a-z-]*$"),  # a command-line flag
    re.compile(r"^/[A-Za-z0-9/._-]+$"),  # an absolute path
)

#: The handful of real words that are still not sentences, per file. Anything
#: added here needs a reason on the line above it.
ALLOWED = {
    # A Pango font list, not text: these are family names on this machine.
    "band.py": {"Andika,Andika New Basic,Cantarell,Sans"},
    "screens/journal.py": {"Andika,Andika New Basic,Cantarell,Sans"},
    # Stack page names and the shell's own state tokens, which are keys in
    # `app.ShellWindow.screens` and are never shown to anybody.
    "screens/grownup.py": {
        "pin",
        "actions",
        # The command a grown-up runs, quoted verbatim inside the sentences
        # that name it. A command is not translated, ever.
        "sudo kidnix-set-pin",
        # What `kidnix-set-pin` writes on stderr when the wait, not the digits,
        # is the answer. We match on it; nobody reads it.
        "too many wrong pins",
    },
}


def _module_docstrings(tree: ast.AST) -> set[int]:
    """The id() of every docstring node, which is documentation, not UI."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def _called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


class _Escapes(ast.NodeVisitor):
    """Collect the string literals nobody marked as translatable."""

    def __init__(self, exempt: set[int]) -> None:
        self.exempt = exempt
        self.found: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = _called_name(node)
        if name in WRAPPERS:
            for argument in node.args:
                self.exempt.update(id(child) for child in ast.walk(argument))
        elif name in NEVER_SPOKEN:
            self.exempt.update(id(child) for child in ast.walk(node))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and id(node) not in self.exempt:
            self.found.append((node.lineno, node.value))


def escaped_strings(relative: str) -> list[tuple[int, str]]:
    """Every literal in ``relative`` that is neither wrapped nor obviously chrome."""
    source = (PACKAGE / relative).read_text(encoding="utf-8")
    tree = ast.parse(source)
    visitor = _Escapes(_module_docstrings(tree))
    visitor.visit(tree)
    allowed = ALLOWED.get(relative, set())
    return [
        (line, text)
        for line, text in visitor.found
        if text not in allowed and not any(shape.match(text) for shape in NOT_A_SENTENCE)
    ]


@pytest.mark.parametrize("relative", GUARDED)
def test_no_child_facing_string_escapes_gettext(relative: str) -> None:
    """A sentence a child meets must be a msgid, or a translator never sees it.

    ``_()`` translates now; ``N_()``/``NP_()`` mark a module-level constant for
    later. Anything else -- a bare ``"All done"`` handed to a widget -- is a
    string that will still be English on a Welsh machine, and the failure is
    silent everywhere except here.
    """
    escapes = escaped_strings(relative)
    assert not escapes, (
        f"{relative}: {len(escapes)} string(s) outside _()/N_()/NP_()/ngettext():\n"
        + "\n".join(f"  line {line}: {text!r}" for line, text in escapes)
    )


def test_the_guard_can_actually_fail(tmp_path: Path) -> None:
    """A guard nobody has seen fail is a guard nobody has tested."""
    source = 'def build(self):\n    self.label("All done for today?")\n'
    tree = ast.parse(source)
    visitor = _Escapes(_module_docstrings(tree))
    visitor.visit(tree)
    assert [text for _line, text in visitor.found] == ["All done for today?"]


# --- manifests carry their own translations ------------------------------


def test_a_manifest_may_carry_per_locale_names() -> None:
    """``name_cy`` beats ``name``; a manifest with neither is what it was."""
    from kidnix_shell.activities import localised

    data = {"name": "Letters & numbers", "name_cy": "Llythrennau a rhifau"}
    assert localised(data, "name", "cy") == "Llythrennau a rhifau"
    assert localised(data, "name", "cy_GB") == "Llythrennau a rhifau"
    assert localised(data, "name", "pl") == ""
    assert localised(data, "name", "en_GB") == ""
