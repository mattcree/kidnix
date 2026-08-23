"""Every word a child hears is translatable, and none of them is frozen.

The checkpoint-2 audit counted **zero** ``_()`` calls in this activity while
the shell had been localised for three commits (ADR-0012,
``docs/design/i18n.md``). A first-party activity is a separate *program* and
not a separate *release*: it shares the shell's ``kidnix`` domain and its
catalogue, so "localised" here means the strings are marked, extractable and
translated at the right moment -- not that this package ships a catalogue.

Three rules, and all three are AST walks rather than greps, because the thing
that goes wrong is a literal creeping back into a widget constructor:

1. nothing calls ``_()`` at module level (it would freeze whichever language
   was installed when Python first imported the file);
2. no child-facing widget in ``activity.py`` is handed a bare string literal;
3. the number words are a **table of msgids**, not an f-string -- "three and
   two make five" is composed from :data:`numbers_activity.words.NUMBER_WORDS`
   with named placeholders a translator may reorder, which is the one thing
   this activity could not have got right by accident.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

from numbers_activity import TITLE, words
from numbers_activity.i18n import HAVE_CATALOGUE, N_, _

PACKAGE = Path(__file__).resolve().parents[1] / "numbers_activity"
MODULES = sorted(PACKAGE.glob("*.py"))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --- en_GB is the source ----------------------------------------------------


def test_en_gb_is_the_source_and_not_a_translation() -> None:
    """A machine with no catalogue anywhere gets the msgid back byte for byte
    -- which *is* the English sentence. That is the property the whole design
    is arranged around (docs/design/i18n.md section 0)."""
    assert N_("How many?") == "How many?"
    assert isinstance(HAVE_CATALOGUE, bool)
    assert _(TITLE) == TITLE


def test_the_title_is_marked_for_extraction() -> None:
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
    pytest.fail("TITLE is not assigned in numbers_activity/__init__.py")


# --- the numbers themselves are a table, not arithmetic ---------------------


def test_every_number_word_is_a_msgid() -> None:
    """``str(n)`` is not a word in any language. Eleven words, eleven msgids."""
    module = tree(PACKAGE / "words.py")
    for node in ast.walk(module):
        # An annotated assignment: `NUMBER_WORDS: tuple[str, ...] = (...)`.
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "NUMBER_WORDS":
            value = node.value
            assert isinstance(value, ast.Tuple)
            assert len(value.elts) == words.MAX_NUMBER + 1
            for element in value.elts:
                assert isinstance(element, ast.Call), ast.dump(element)
                assert getattr(element.func, "id", "") == "N_"
            return
    pytest.fail("NUMBER_WORDS is not assigned in numbers_activity/words.py")


def test_the_sentence_is_composed_from_named_placeholders() -> None:
    """"Three and two make five" is a msgid with three holes in it, so a
    translator may reorder them -- or fold a number into the word beside it,
    which Polish needs (docs/design/i18n.md section 2.3)."""
    for hole in ("{shown}", "{missing}", "{total}"):
        assert hole in words.BOND_SENTENCE
    assert words.bond_sentence(3, 2, 5) == "Three and two make five."


def test_the_window_lines_are_marked_and_live_with_the_other_words() -> None:
    """A label on a button is a sentence a child reads. These are the ones the
    window owns, and they are msgids in ``words.py`` like every other line."""
    for name in (
        "LOST_LINE",
        "AGAIN_LABEL",
        "AGAIN_SPEAK",
        "MORE_LABEL",
        "MORE_SPEAK",
        "BOX_EMPTY_SPEAK",
        "BOX_FULL_SPEAK",
    ):
        assert isinstance(getattr(words, name), str)
        assert getattr(words, name).strip()


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
def test_nothing_translates_at_module_level(path: Path) -> None:
    """`_()` at module level freezes whichever language happened to be
    installed when Python first imported the file -- on a profile switch, the
    wrong one; in a test, whichever ran first. `N_()` is what module level is
    for."""
    assert module_level_calls(tree(path), "_") == []


# --- no bare literal reaches a child ----------------------------------------

#: The widgets that put words in front of a child. Every one of them takes a
#: label, a spoken string, or both.
CHILD_WIDGETS = {"Prompt", "BigButton", "GrownUpTurn", "ChildButton", "PictureTile", "NumberTile"}

#: Arguments of those widgets that are **not** copy: an icon name, a CSS class,
#: a focus-ring key. A literal in one of these is fine and always will be.
NOT_COPY = {"icon", "icon_kind", "css_classes", "key", "name", "picture"}


def bare_copy_literals(module: ast.Module) -> list[tuple[int, str]]:
    """Every non-empty string literal handed to a child-facing widget."""
    offences: list[tuple[int, str]] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
        if name in CHILD_WIDGETS:
            candidates = [
                *node.args,
                *[kw.value for kw in node.keywords if kw.arg not in NOT_COPY],
            ]
        elif name in {"speak", "set_speak_text", "set_text"}:
            candidates = list(node.args)
        else:
            continue
        for argument in candidates:
            literal = isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            if literal and argument.value:
                offences.append((argument.lineno, argument.value))
    return offences


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_no_child_facing_widget_is_handed_an_untranslatable_string(path: Path) -> None:
    """The failure mode this catches is the ordinary one: somebody adds a
    button, types the label inline, and the string is invisible to `xgettext`
    for the next six months."""
    assert bare_copy_literals(tree(path)) == []


def test_the_guard_would_catch_the_line_the_audit_found() -> None:
    """A test that cannot fail is not a test."""
    module = ast.parse('BigButton("Look", icon=str(LOOK_ICON), speak_text="Show me again.")')
    assert bare_copy_literals(module) == [(1, "Look"), (1, "Show me again.")]


# --- a msgid is not a sentence until somebody translates it ------------------


def msgid_names(module: ast.Module, *, from_modules: set[str]) -> set[str]:
    """The names in this file that hold a **msgid**: marked here, or imported
    from a module that marks them."""
    names: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "N_":
                names.add(node.targets[0].id)
        if isinstance(node, ast.ImportFrom) and node.module in from_modules:
            names.update(
                alias.asname or alias.name
                for alias in node.names
                if (alias.asname or alias.name).isupper()
            )
    return names


def unwrapped_msgids(module: ast.Module, *, from_modules: set[str]) -> list[tuple[int, str]]:
    """Every use of one of those names that is **not** inside ``_()``.

    The failure this catches is subtler than a bare literal and is the one that
    actually happened while this was being written: the constant is marked, the
    extractor sees it, the catalogue has a Welsh translation -- and the use site
    hands the widget the msgid, so the child gets English anyway. `N_` is the
    identity function, which is exactly why nothing else notices.
    """
    names = msgid_names(module, from_modules=from_modules)
    exempt: set[int] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_":
            for argument in node.args:
                exempt.update(id(child) for child in ast.walk(argument))
    found: list[tuple[int, str]] = []
    for node in ast.walk(module):
        if (
            isinstance(node, ast.Name)
            and node.id in names
            and isinstance(node.ctx, ast.Load)
            and id(node) not in exempt
        ):
            found.append((node.lineno, node.id))
        if (
            isinstance(node, ast.Attribute)
            and getattr(node.value, "id", "") == "words"
            and node.attr.isupper()
            and id(node) not in exempt
        ):
            found.append((node.lineno, f"words.{node.attr}"))
    return sorted(found)


def test_every_msgid_the_window_uses_is_translated_at_the_use_site() -> None:
    """`N_` marks; `_()` translates. A constant handed straight to a widget is
    a sentence that stays en_GB on a Welsh machine and fails nothing else."""
    module = tree(PACKAGE / "activity.py")
    assert unwrapped_msgids(module, from_modules={"words", ".words"}) == []


def test_that_guard_would_catch_the_mistake_it_is_for() -> None:
    """A test that cannot fail is not a test."""
    module = ast.parse('GREETING = N_("Hello")\ndef build(self):\n    self.say(GREETING)\n')
    assert unwrapped_msgids(module, from_modules=set()) == [(3, "GREETING")]


# --- the extractor can actually see them ------------------------------------


def test_xgettext_finds_every_child_facing_string(tmp_path: Path) -> None:
    """``shell/Justfile``'s ``po-extract`` scans ``../activities`` with this
    keyword list; this is the same run, over this package alone, so a msgid
    that would never reach ``po/kidnix.pot`` fails here instead of silently."""
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
            "--keyword=NP_:1,2",
            f"--output={pot}",
            *[str(path) for path in MODULES],
        ],
        check=True,
        capture_output=True,
    )
    extracted = pot.read_text(encoding="utf-8")
    for msgid in (
        TITLE,
        words.HOW_MANY,
        words.BOND_SENTENCE,
        words.LOST_LINE,
        words.AGAIN_LABEL,
        words.BOX_EMPTY_SPEAK,
        *words.NUMBER_WORDS,
    ):
        assert f'msgid "{msgid}"' in extracted, msgid
