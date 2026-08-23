"""Every word a child hears is translatable, and none of them is frozen.

The checkpoint-2 audit counted **zero** ``_()`` calls in this activity while
the shell had been localised for three commits (ADR-0012,
``docs/design/i18n.md``). A first-party activity is a separate *program* and
not a separate *release*: it shares the shell's ``kidnix`` domain and its
catalogue, so "localised" here means the strings are marked, extractable and
translated at the right moment -- not that this package ships a catalogue.

Telling the time is the hard case in the whole product. "Half past three" is
three words in a fixed order in English and something else everywhere else --
German's *halb vier* is half past **three** while naming four -- so what is in
the catalogue is not a pile of fragments this module glues together, but one
entry per **shape** of sentence, with named holes a translator may reorder or
drop. :func:`test_the_time_is_composed_per_locale` is that claim as a test.

The rest are AST walks rather than greps, because the thing that goes wrong is
a literal creeping back into a widget constructor.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

from clock_time import TITLE, minute, routine, words
from clock_time.i18n import HAVE_CATALOGUE, N_, _

PACKAGE = Path(__file__).resolve().parents[1] / "clock_time"
MODULES = sorted(PACKAGE.glob("*.py"))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --- en_GB is the source ----------------------------------------------------


def test_en_gb_is_the_source_and_not_a_translation() -> None:
    """A machine with no catalogue anywhere gets the msgid back byte for byte
    -- which *is* the English sentence. That is the property the whole design
    is arranged around (docs/design/i18n.md section 0)."""
    assert N_("half past") == "half past"
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
    pytest.fail("TITLE is not assigned in clock_time/__init__.py")


# --- the time is a table plus a shape, never an f-string --------------------


def test_every_hour_name_is_a_msgid() -> None:
    """Twelve words, twelve catalogue entries. ``str(hour)`` is not a word in
    any language and the child never sees one anyway (01 #19)."""
    module = tree(PACKAGE / "words.py")
    for node in ast.walk(module):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "HOUR_NAMES":
            value = node.value
            assert isinstance(value, ast.Tuple)
            assert len(value.elts) == 12
            for element in value.elts:
                assert isinstance(element, ast.Call), ast.dump(element)
                assert getattr(element.func, "id", "") == "N_"
            return
    pytest.fail("HOUR_NAMES is not assigned in clock_time/words.py")


def test_the_time_is_composed_per_locale() -> None:
    """Three shapes, each one msgid with **named** holes, so a translator can
    put the hour first, drop the preposition, or say something else entirely
    for the half hour. Nothing in here concatenates two translated fragments in
    English's order."""
    assert "{hour}" in words.ON_THE_HOUR
    assert "{past}" in words.PAST_THE_HOUR and "{hour}" in words.PAST_THE_HOUR
    assert "{to}" in words.TO_THE_HOUR and "{hour}" in words.TO_THE_HOUR
    assert "{time}" in words.ABOUT
    # And the shapes are distinct msgids: a catalogue that could not tell
    # "past" from "to" could not reorder one without the other.
    assert words.PAST_THE_HOUR != words.TO_THE_HOUR

    assert words.ClockTime.of(12, 0).words() == "twelve o'clock"
    assert words.ClockTime.of(3, 30).words() == "half past three"
    assert words.ClockTime.of(7, 45).words() == "quarter to eight"
    assert words.ClockTime.of(3, 26).spoken(words.Mode.Y2) == "about twenty-five past three"


def test_the_intervals_and_the_verdicts_are_msgids() -> None:
    """The minute screen's words: three intervals, three bands, two sentences.
    The bands are the enum's own *values*, which is why they are marked where
    they are declared and translated in :attr:`Verdict.words`."""
    assert set(minute.LENGTH_WORDS) == set(minute.Length)
    assert set(minute.LENGTH_LABELS) == set(minute.Length)
    assert "{length}" in minute.PRESS_STOP
    assert "{verdict}" in minute.VERDICT_SENTENCE and "{length}" in minute.VERDICT_SENTENCE
    assert minute.Verdict.EARLY.sentence(minute.Length.MINUTE) == (
        "That was a bit early for a minute."
    )


def test_the_day_is_msgids_and_a_grown_ups_own_words_pass_through() -> None:
    """Our eight default names are translated; a name a grown-up typed into
    ``clock_time.toml`` is already in their language and comes back unchanged,
    because it is in no catalogue. Both go through the same call."""
    assert set(routine.SKY_WORDS) == set(routine.Sky)
    assert "{name}" in routine.IS_AT and "{time}" in routine.IS_AT
    assert routine.DEFAULT_ROUTINE[0].name_words == "Wake up"
    mine = routine.RoutineItem("tea", "Amser te", 17 * 60 + 30)
    assert mine.name_words == "Amser te"
    assert mine.sentence == "Amser te is at half past five."


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
#: label, a spoken string, or both. ``_big`` and ``_tile`` are this module's own
#: two constructors and they forward to the SDK's.
CHILD_WIDGETS = {
    "Prompt",
    "BigButton",
    "GrownUpTurn",
    "ChildButton",
    "PictureTile",
    "_big",
    "_tile",
}

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
    module = ast.parse('_big("Now", icon=str(ICON), speak_text="Show me the time right now.")')
    assert bare_copy_literals(module) == [(1, "Now"), (1, "Show me the time right now.")]


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
        words.OCLOCK,
        words.PAST_THE_HOUR,
        minute.PRESS_STOP,
        routine.IS_AT,
        *words.HOUR_NAMES,
        *minute.LENGTH_WORDS.values(),
        *routine.SKY_WORDS.values(),
        *[item.name for item in routine.DEFAULT_ROUTINE],
    ]
    for msgid in expected:
        assert f'msgid "{msgid}"' in extracted, msgid
