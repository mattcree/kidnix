"""Every word a child hears is translatable, and none of them is frozen.

The checkpoint-2 audit counted **zero** ``_()`` calls in this activity while
the shell had been localised for three commits (ADR-0012,
``docs/design/i18n.md``). A first-party activity is a separate *program* and
not a separate *release*: it shares the shell's ``kidnix`` domain and its
catalogue, so "localised" here means the strings are marked, extractable and
translated at the right moment -- not that this package ships a catalogue.

The letter is the case where the difference between *our* words and *theirs*
actually matters, and there are three kinds of string in here:

1. **ours** -- the prompts, the labels, the card's "for Grandad". Msgids;
2. **a person's** -- a recipient's name, a sender's name, the words the child
   typed. Never translated, and they go into a **named** placeholder so a
   translator may put the name where their language puts it;
3. **machine vocabulary** -- ``STATUS_WAITING`` and friends, which are written
   into ``letter.json`` and the outbox manifest. Translating a *stored* status
   would make a file mean different things on two machines, which is the one
   thing a folder a grown-up posts from must not do (docs/design/i18n.md
   section 6).
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from letters_to_family import TITLE, draw, journal_read, letter, scribble, words
from letters_to_family.i18n import HAVE_CATALOGUE, N_, _

PACKAGE = Path(__file__).resolve().parents[1] / "letters_to_family"
MODULES = sorted(PACKAGE.glob("*.py"))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --- en_GB is the source ----------------------------------------------------


def test_en_gb_is_the_source_and_not_a_translation() -> None:
    """A machine with no catalogue anywhere gets the msgid back byte for byte
    -- which *is* the English sentence. That is the property the whole design
    is arranged around (docs/design/i18n.md section 0)."""
    assert N_("Post it") == "Post it"
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
    pytest.fail("TITLE is not assigned in letters_to_family/__init__.py")


# --- every fixed line is a msgid --------------------------------------------


def test_every_line_in_words_is_marked() -> None:
    """``words.py`` is the one file a translator has to read top to bottom, so
    every constant in it is an ``N_()`` call and none of them is a bare
    string."""
    module = tree(PACKAGE / "words.py")
    bare: list[str] = []
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        name = getattr(node.targets[0], "id", "")
        if not name.isupper() or name == "__all__":
            continue
        marked = isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "N_"
        if not marked:
            bare.append(name)
    assert bare == []


def test_the_name_of_a_person_goes_in_a_named_placeholder() -> None:
    """A recipient is never translated and never concatenated: their name goes
    where the catalogue's own sentence puts it."""
    for msgid in (words.YOUR_LETTER_FOR, words.POSTED_LINE, words.FROM_LINE, letter.LETTER_FOR):
        assert "{name}" in msgid
    assert "{name}" in draw.FOR_NAME
    assert words.posted_line("Grandad") == "Posted! A grown-up will send it to Grandad."
    assert words.reply_line("Nanna") == "A letter from Nanna."


def test_the_crayons_and_the_fallbacks_are_msgids() -> None:
    """Everything else a child hears: the three crayon names, the word for a
    picture nobody titled, and who a letter is for when we do not know."""
    assert scribble.COLOUR_NAMES == ("Teal", "Pink", "Black")
    assert scribble.COLOURS[0].speak_text == "Teal"
    assert journal_read.SOMETHING_I_MADE == "A thing I made"
    assert letter.letter_title(None) == "A letter for someone"


def test_a_stored_status_is_not_translated() -> None:
    """``letter.json`` and the outbox manifest are read by whoever opens the
    folder next, possibly on another machine. A status that changed language
    with the child's profile would be a file that means two things."""
    source = (PACKAGE / "letter.py").read_text(encoding="utf-8")
    for name in ("STATUS_WAITING", "STATUS_UNPOSTED"):
        line = next(row for row in source.splitlines() if row.startswith(f"{name} = "))
        assert "N_(" not in line and "_(" not in line, line


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
CHILD_WIDGETS = {"Prompt", "BigButton", "GrownUpTurn", "ChildButton", "PictureTile"}

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
        elif name in {"speak", "set_speak_text", "_set_prompt"}:
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
    module = ast.parse('BigButton("Undo", icon="kidnix-undo", speak_text="Take the last line off.")')
    assert bare_copy_literals(module) == [(1, "Undo"), (1, "Take the last line off.")]


# --- and the rules that were already here still hold ------------------------


def test_no_line_promises_a_reply_or_praises_a_child() -> None:
    """The rules ``tests/test_words.py`` holds every line to, re-checked over
    the lines i18n added -- a new msgid is a new sentence, and a new sentence
    is where "Well done!" gets in."""
    banned = ("well done", "brilliant", "clever", "star", "soon", "tomorrow")
    for line in words.all_lines():
        lowered = line.lower()
        for word in banned:
            assert not re.search(rf"(?<![a-z]){word}(?![a-z])", lowered), (word, line)
        assert not re.search(r"\d", line), line


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
    assert unwrapped_msgids(module, from_modules=set()) == []


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
    expected = [
        TITLE,
        words.WHO_FOR,
        words.POST_IT,
        words.UNDO_LABEL,
        words.LISTEN_SPEAK,
        words.POSTED_LINE,
        letter.LETTER_FOR,
        letter.SOMEONE,
        draw.FOR_NAME,
        journal_read.SOMETHING_I_MADE,
        *scribble.COLOUR_NAMES,
    ]
    for msgid in expected:
        assert f'msgid "{msgid}"' in extracted, msgid
