"""The SDK's own sentences are translatable, and none of them is frozen.

The checkpoint-2 audit found "zero i18n in ... the SDK's own strings", and the
SDK is the one place where that costs the most: :mod:`kidnix_activity.widgets`
holds the three sentences **every** activity inherits without writing them --
the replay button's "Say it again.", and the grown-up card's title and its Done
button. Four activities ship them today, so a literal here is four literals.

No display needed and none used. This is the AST of ``widgets.py`` plus a
gettext round trip through the shell's own catalogue, which is the same
catalogue: an activity is a separate *program*, not a separate *release*
(``build_files/60-shell.sh``), so it shares the ``kidnix`` domain rather than
carrying one of its own. ADR-0012, docs/design/i18n.md.

The GTK half -- that a ``GrownUpTurn`` built with no ``title`` really says
"Your turn, grown-up" -- is in ``test_activity_sdk_widgets.py``, where there is
a window to put it in.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from kidnix_shell import i18n

SDK = Path(__file__).resolve().parents[1] / "kidnix_activity"
WIDGETS = SDK / "widgets.py"

#: The four ways to say "this string is translatable" -- the same set the
#: shell's own guard uses (``tests/test_i18n.py``), because it is the same rule.
WRAPPERS = frozenset({"_", "N_", "NP_", "ngettext"})


@pytest.fixture(autouse=True)
def _english_again() -> object:
    """Leave the process speaking en_GB, whatever this file installed.

    The catalogue is global -- it is what ``_()`` reads -- so a test that put
    Polish in force and did not put it back would fail some unrelated file
    later, unrepeatably.
    """
    yield
    i18n.install(i18n.DEFAULT_LANGUAGE)


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --- the three sentences are msgids ----------------------------------------


def marked_constants(module: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = N_("...")`` assignments, as name -> msgid."""
    found: dict[str, str] = {}
    for node in module.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and getattr(value.func, "id", "") == "N_"
            and value.args
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            found[node.targets[0].id] = value.args[0].value
    return found


def test_the_sdks_own_words_are_marked_for_extraction() -> None:
    """`N_` is the identity function, so its value proves nothing -- only the
    source does. These three are what an activity gets for free, and until
    ADR-0012 they were three bare literals."""
    constants = marked_constants(tree(WIDGETS))
    assert constants.get("REPLAY_SPEAK") == "Say it again."
    assert constants.get("GROWNUP_TITLE") == "Your turn, grown-up"
    assert constants.get("GROWNUP_DONE") == "Done"


def test_the_icon_name_is_not_a_sentence_and_is_not_marked() -> None:
    """``kidnix-ear`` is an icon name: machine vocabulary, never translated
    (docs/design/i18n.md section 6). Marking it would put a slug in front of a
    translator and invite them to change it."""
    assert "REPLAY_ICON" not in marked_constants(tree(WIDGETS))
    assert 'REPLAY_ICON = "kidnix-ear"' in WIDGETS.read_text(encoding="utf-8")


def test_nothing_is_translated_at_import_time() -> None:
    """A module-level ``_()`` freezes whichever catalogue happened to be
    installed when Python first imported the file -- which, in an activity the
    shell launched for a Welsh child, is the wrong one."""
    module = tree(WIDGETS)
    offences: list[int] = []

    def walk(node: ast.AST, inside_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                walk(child, True)
                continue
            if (
                not inside_function
                and isinstance(child, ast.Call)
                and getattr(child.func, "id", "") == "_"
            ):
                offences.append(child.lineno)
            walk(child, inside_function)

    walk(module, False)
    assert offences == []


def test_the_default_is_translated_where_the_widget_is_built() -> None:
    """``GrownUpTurn(title=...)`` defaults to ``None`` rather than to the
    msgid, so the SDK's own words are translated in ``__init__`` -- when a
    child is already sitting down -- and an activity's own sentence, already
    translated in its own catalogue entry, passes through untouched."""
    source = WIDGETS.read_text(encoding="utf-8")
    assert "title: str | None = None" in source
    assert "done_label: str | None = None" in source
    assert "title = _(GROWNUP_TITLE)" in source
    assert "done_label = _(GROWNUP_DONE)" in source


# --- no other literal in the SDK reaches a child ---------------------------

#: Calls whose string arguments are never something a child hears: logging,
#: GTK plumbing that takes names, and the CSS-class machinery.
NEVER_SPOKEN = frozenset(
    {
        "debug",
        "info",
        "warning",
        "error",
        "exception",
        "critical",
        "log",
        "add_css_class",
        "remove_css_class",
        "require_version",
        "next_key",
        "icon_image",
        "getattr",
        "setattr",
        "join",
        "split",
        "replace",
    }
)

#: What a non-sentence looks like -- chrome rather than copy. The shell's guard
#: keeps the same list for the same reason (``tests/test_i18n.py``).
NOT_A_SENTENCE = (
    re.compile(r"^$"),
    re.compile(r"^[a-z0-9][a-z0-9._-]*$"),  # a slug: css class, icon name, id
    re.compile(r"^#[0-9a-fA-F]{3,8}$"),  # a colour
    re.compile(r"^[^A-Za-z]*$"),  # punctuation, digits, whitespace
    re.compile(r"^[A-Z][A-Za-z0-9_]*$"),  # a bare identifier (__all__)
    re.compile(r"^%[-#0-9. ]*[a-zA-Z]"),  # a printf spec
    re.compile(r"^_[A-Za-z0-9_]*$"),  # a private attribute name
)


def docstrings(module: ast.Module) -> set[int]:
    """The id() of every docstring node: documentation, not interface."""
    found: set[int] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def escaped_strings(path: Path) -> list[tuple[int, str]]:
    """Every literal that is neither wrapped, nor a log line, nor chrome."""
    module = tree(path)
    exempt = docstrings(module)
    found: list[tuple[int, str]] = []

    class Walk(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
            if name in WRAPPERS:
                for argument in node.args:
                    exempt.update(id(child) for child in ast.walk(argument))
            elif name in NEVER_SPOKEN:
                exempt.update(id(child) for child in ast.walk(node))
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str) and id(node) not in exempt:
                found.append((node.lineno, node.value))

    Walk().visit(module)
    return [
        (line, text)
        for line, text in found
        if not any(shape.match(text) for shape in NOT_A_SENTENCE)
    ]


def test_no_child_facing_string_escapes_gettext() -> None:
    """The guard. Six months from now somebody adds a sentence to a widget in a
    hurry; this is what tells them, in CI, instead of a Welsh family."""
    escapes = escaped_strings(WIDGETS)
    assert not escapes, "kidnix_activity/widgets.py: " + "\n".join(
        f"  line {line}: {text!r}" for line, text in escapes
    )


def test_the_guard_can_actually_fail(tmp_path: Path) -> None:
    """A guard nobody has seen fail is a guard nobody has tested."""
    source = tmp_path / "widget.py"
    source.write_text('def build(self):\n    self.set_speak_text("All done for today?")\n')
    assert escaped_strings(source) == [(2, "All done for today?")]


# --- and the catalogue really is the shell's -------------------------------


def test_the_sdk_shares_the_shells_domain_and_catalogue() -> None:
    """One domain, one catalogue, one release. Two would be two places for the
    same word to be translated differently, and a child cannot tell which
    process drew a sentence."""
    from kidnix_activity import i18n as sdk_i18n

    assert sdk_i18n.DOMAIN == i18n.DOMAIN == "kidnix"
    assert sdk_i18n.gettext is i18n.gettext
    assert sdk_i18n._ is i18n._


def test_with_no_catalogue_the_sdk_says_exactly_what_it_always_said() -> None:
    """en_GB is the source, not a translation: with nothing installed every
    msgid comes back byte for byte, which is what it was before ADR-0012."""
    i18n.install(i18n.DEFAULT_LANGUAGE)
    constants = marked_constants(tree(WIDGETS))
    for msgid in constants.values():
        assert i18n.gettext(msgid) == msgid
