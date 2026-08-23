"""Every word a child hears is translatable, and none of them is frozen.

The checkpoint-2 audit counted **zero** ``_()`` calls in this activity three
commits after the shell was localised (ADR-0012, ``docs/design/i18n.md``). A
first-party activity is a separate *program* and not a separate *release*: it
shares the shell's ``kidnix`` domain and its catalogue, so "localised" here
means the strings are marked, extractable and translated at the right moment --
not that this package ships a catalogue of its own.

Three rules, and all three are AST walks rather than greps, because the thing
that goes wrong is a literal creeping back into a widget constructor:

1. the msgids and ``data/parent_text.toml`` say the same words;
2. nothing calls ``_()`` at module level (it would freeze whichever language
   was installed when Python first imported the file);
3. no child-facing widget is handed a bare string literal.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

from sounds_and_words import TITLE
from sounds_and_words.i18n import HAVE_CATALOGUE, N_, _
from sounds_and_words.text import CHILD_LINES, FIND_IT

PACKAGE = Path(__file__).resolve().parents[1] / "sounds_and_words"
MODULES = sorted(PACKAGE.glob("*.py"))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --- the msgids and the corpus agree ----------------------------------------


def test_every_child_line_in_the_corpus_is_a_msgid(corpus):
    """`parent_text.toml` is data, so `xgettext` cannot see it. `CHILD_LINES`
    is where the extractor finds the same words, and this is what stops the
    two drifting apart."""
    assert set(corpus.parent_text["child"]) == set(CHILD_LINES)


def test_the_msgids_are_the_words_the_corpus_actually_ships(corpus):
    for key, msgid in CHILD_LINES.items():
        assert corpus.parent_text["child"][key] == msgid, key


def test_the_corpus_line_the_audit_changed_no_longer_ends_in_a_grapheme(corpus):
    assert corpus.parent_text["child"]["find_it"] == FIND_IT
    assert FIND_IT.endswith("…")


def test_the_title_is_marked_for_extraction():
    """`N_` is the identity function, so this cannot be proved by its value --
    only by reading the source."""
    module = tree(PACKAGE / "__init__.py")
    for node in ast.walk(module):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TITLE" for t in node.targets
        ):
            assert isinstance(node.value, ast.Call)
            assert getattr(node.value.func, "id", "") == "N_"
            return
    pytest.fail("TITLE is not assigned in sounds_and_words/__init__.py")


def test_en_gb_is_the_source_and_not_a_translation():
    """A machine with no catalogue anywhere gets the msgid back byte for byte
    -- which *is* the English sentence. That is the property the whole design
    is arranged around (docs/design/i18n.md section 0)."""
    assert N_("Find the one that says…") == "Find the one that says…"
    assert isinstance(HAVE_CATALOGUE, bool)
    assert _(TITLE) == TITLE


# --- nothing is translated at import time -----------------------------------


def module_level_calls(module: ast.Module, name: str) -> list[int]:
    """Line numbers where ``name(...)`` is called outside any function."""
    found: list[int] = []

    def walk(node: ast.AST, inside_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                walk(child, True)
                continue
            if (
                not inside_function
                and isinstance(child, ast.Call)
                and getattr(child.func, "id", "") == name
            ):
                found.append(child.lineno)
            walk(child, inside_function)

    walk(module, False)
    return found


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_nothing_translates_at_module_level(path):
    """`_()` at module level freezes whichever language happened to be
    installed when Python first imported the file -- on a profile switch, the
    wrong one; in a test, whichever ran first. `N_()` is what module level is
    for."""
    assert module_level_calls(tree(path), "_") == []


# --- no bare literal reaches a child ----------------------------------------

#: The widgets that put words in front of a child. Every one of them takes a
#: label, a spoken string, or both.
CHILD_WIDGETS = {"Prompt", "BigButton", "GrownUpTurn", "ChildButton"}

#: Arguments of those widgets that are **not** copy: an icon name, a CSS class,
#: a focus-ring key. A literal in one of these is fine and always will be.
NOT_COPY = {"icon", "icon_kind", "css_classes", "key", "name"}


def bare_copy_literals(module: ast.Module) -> list[tuple[int, str]]:
    """Every non-empty string literal handed to a child-facing widget."""
    offences: list[tuple[int, str]] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
        if name in CHILD_WIDGETS:
            candidates = list(node.args) + [kw.value for kw in node.keywords if kw.arg not in NOT_COPY]
        elif name == "_icon_button":
            # (window, icon, label, speak, on_activate) -- the icon is a file
            # name, the two after it are what a child reads and hears.
            candidates = list(node.args[2:4])
        else:
            continue
        for argument in candidates:
            literal = isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            if literal and argument.value:
                offences.append((argument.lineno, argument.value))
    return offences


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_no_child_facing_widget_is_handed_an_untranslatable_string(path):
    """The failure mode this catches is the ordinary one: somebody adds a
    button, types the label inline, and the string is invisible to `xgettext`
    for the next six months."""
    assert bare_copy_literals(tree(path)) == []


def test_the_guard_would_catch_the_line_the_audit_found():
    """A test that cannot fail is not a test."""
    module = ast.parse('Prompt("Find the one that says k.", speech=s, area=a)')
    assert bare_copy_literals(module) == [(1, "Find the one that says k.")]


# --- the extractor can actually see them ------------------------------------


def test_xgettext_finds_every_child_facing_string(tmp_path):
    """The audit's ninth item was not only "wrap the strings" -- it was that
    `shell/Justfile`'s `po-extract` does not scan `activities/` at all, so a
    wrapped string would still never reach a catalogue. This proves our half:
    the strings are extractable with the shell's own keyword list. The other
    half is one line in the shell's Justfile (docs/design/sounds-and-words.md
    section 15), which this package may not edit."""
    xgettext = shutil.which("xgettext")
    if xgettext is None:  # pragma: no cover - gettext is on the image
        pytest.skip("gettext is not installed here")
    pot = tmp_path / "kidnix.pot"
    subprocess.run(
        [
            xgettext,
            "--language=Python",
            "--from-code=UTF-8",
            "--keyword=_",
            "--keyword=N_",
            "--keyword=ngettext:1,2",
            f"--output={pot}",
            *[str(path) for path in MODULES],
        ],
        check=True,
        capture_output=True,
    )
    extracted = pot.read_text(encoding="utf-8")
    for msgid in [*CHILD_LINES.values(), TITLE]:
        assert f'msgid "{msgid}"' in extracted, msgid
