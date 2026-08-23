"""Every icon this activity asks for resolves to a real file.

The audit that produced this file found four names -- ``kidnix-draw``,
``kidnix-keep``, ``kidnix-word`` and ``kidnix-journal`` -- that were in no icon
theme and in none of the shell's bundled SVGs, so **five controls drew
``image-missing``**: "Draw one", "That's it", "Write it", "Post it" and the way
into the shelf. Nothing failed, nothing was logged, and the only person who
could have noticed was a four-year-old being handed the same broken glyph on
every button they had to press.

That is exactly the class of bug a test catches for nothing, so this is the
test. It reads the source rather than running the window, for the same reason
``test_i18n.py`` does: the failure is a *name that does not resolve*, and a
name is a fact about the file, not about a display.

Two kinds of name are legal here and both are checked:

* ``icon=icon("draw")`` -- one of this package's own SVGs, passed with
  ``icon_kind="path"``. Checked against :data:`ICON_DIR` on disk, and the file
  is parsed and held to ``kidnix_shell/data/icons/README.md``'s drawing rules.
* ``icon="kidnix-my-things"`` -- a **bundled** name, which
  ``kidnix_shell.widgets.icon_image`` resolves against the shell's own set
  after missing in the icon theme. Checked against that directory.
"""

from __future__ import annotations

import ast
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import SHELL_SRC

PACKAGE = Path(__file__).resolve().parents[1] / "letters_to_family"
ACTIVITY = PACKAGE / "activity.py"
ICON_DIR = PACKAGE / "icons"

#: Where ``widgets.bundled_icon`` looks. Reached by path and not by import so
#: this runs in the headless suite, which has no GTK.
SHELL_ICONS = SHELL_SRC / "kidnix_shell" / "data" / "icons"

SVG = "{http://www.w3.org/2000/svg}"

#: ``kidnix_shell/data/icons/README.md``, as the shell's own set actually uses
#: it after the 2026-08-23 icon audit.
PALETTE = frozenset(
    {
        "#0f8a8a",  # teal
        "#f06292",  # pink
        "#ffd23f",  # highlight yellow
        "#2e7d32",  # green
        "#f6c9a8",  # skin
        "#8a93b5",  # slate
        "#fbf7ef",  # cream (paper)
        "#16181d",  # ink
    }
)


def tree() -> ast.Module:
    return ast.parse(ACTIVITY.read_text(encoding="utf-8"), filename=str(ACTIVITY))


def module_constants(module: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "string"``, so ``SHELF_ICON`` can be followed."""
    found: dict[str, str] = {}
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            found[node.targets[0].id] = node.value.value
    return found


def icons_asked_for() -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """``(our own SVG stems, bundled icon names)``, with line numbers.

    Every ``icon=`` keyword in the module, however it is written: a call to the
    package's own :func:`letters_to_family.activity.icon`, a bare string, or a
    module constant holding one.
    """
    module = tree()
    constants = module_constants(module)
    ours: list[tuple[int, str]] = []
    bundled: list[tuple[int, str]] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "icon":
                continue
            value = keyword.value
            if (
                isinstance(value, ast.Call)
                and getattr(value.func, "id", "") == "icon"
                and value.args
                and isinstance(value.args[0], ast.Constant)
            ):
                ours.append((value.lineno, str(value.args[0].value)))
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                bundled.append((value.lineno, value.value))
            elif isinstance(value, ast.Name) and value.id in constants:
                bundled.append((value.lineno, constants[value.id]))
            else:  # pragma: no cover - a form nobody has written yet
                pytest.fail(f"{ACTIVITY.name}:{value.lineno}: icon= is not a name this test reads")
    return ours, bundled


# --- the check the audit wanted ---------------------------------------------


def test_the_activity_asks_for_icons_at_all() -> None:
    """A test that cannot fail is not a test: if the walk above ever stops
    finding call sites, every assertion below passes vacuously."""
    ours, bundled = icons_asked_for()
    assert len(ours) >= 3, ours
    assert len(bundled) >= 3, bundled


def test_every_icon_of_our_own_is_a_file() -> None:
    missing = [
        (line, stem)
        for line, stem in icons_asked_for()[0]
        if not (ICON_DIR / f"{stem}.svg").is_file()
    ]
    assert missing == [], f"no such file under {ICON_DIR}"


def test_every_bundled_icon_name_is_a_file() -> None:
    """The failure the audit found, in the form it took: a plausible name in
    the ``kidnix-`` namespace that no file anywhere answers to."""
    if not SHELL_ICONS.is_dir():  # pragma: no cover - running outside the checkout
        pytest.skip("the shell's bundled icons are not in this checkout")
    missing = [
        (line, name)
        for line, name in icons_asked_for()[1]
        if not (SHELL_ICONS / f"{name}.svg").is_file()
    ]
    assert missing == [], f"no such file under {SHELL_ICONS}"


def test_the_guard_would_have_caught_the_four_names_the_audit_found() -> None:
    """The four that were broken are still broken names -- nobody has quietly
    added ``kidnix-draw.svg`` to the shell and made this test tautological."""
    if not SHELL_ICONS.is_dir():  # pragma: no cover - running outside the checkout
        pytest.skip("the shell's bundled icons are not in this checkout")
    for name in ("kidnix-draw", "kidnix-keep", "kidnix-word", "kidnix-journal"):
        assert not (SHELL_ICONS / f"{name}.svg").is_file()
        assert name not in ACTIVITY.read_text(encoding="utf-8")


# --- and the drawings themselves --------------------------------------------


@pytest.mark.parametrize("path", sorted(ICON_DIR.glob("*.svg")), ids=lambda p: p.name)
def test_each_drawing_is_well_formed_and_follows_the_house_rules(path: Path) -> None:
    """``kidnix_shell/data/icons/README.md``: a 64x64 viewBox, a title, flat
    fills, and **no text element** -- no font is guaranteed on the image and a
    missing glyph would empty the icon. librsvg also refuses a whole file for a
    double hyphen inside an XML comment, which ``kidnix-finish.svg`` is on
    record as having tripped, so parsing at all is half the test."""
    root = ET.parse(path).getroot()
    assert root.tag == f"{SVG}svg"
    assert root.get("viewBox") == "0 0 64 64"
    # A declared intrinsic size of at least 120, which is what
    # `tests/image/test_icons.sh` gates every shipped SVG on: GdkPixbuf
    # rasterises at the declared size and then GTK scales the raster, so a
    # 64 px declaration on a 128 px control is a 2x upscale of a picture that
    # would have been perfect at any size. viewBox stays 64; this is an
    # attribute, not a redraw.
    assert float(root.get("width", 0)) >= 120
    assert float(root.get("height", 0)) >= 120
    assert root.find(f"{SVG}title") is not None, "an icon needs an accessible name"
    for banned in ("text", "image", "linearGradient", "radialGradient", "filter"):
        assert root.find(f".//{SVG}{banned}") is None, banned
    assert "--" not in "".join(
        node.text or "" for node in root.iter() if not isinstance(node.tag, str)
    )
    assert path.stat().st_size < 4096, "README.md: under 4 KB"


@pytest.mark.parametrize("path", sorted(ICON_DIR.glob("*.svg")), ids=lambda p: p.name)
def test_each_drawing_stays_inside_the_shipped_palette(path: Path) -> None:
    """One product, one set of colours. `#f9a825` in particular is **not** in
    it any more -- the icon audit mapped every stray amber onto the highlight
    yellow the rest of the shell uses -- and an icon that reintroduced it would
    be the only warm yellow on the screen that did not match the others."""
    used = set(re.findall(r"#[0-9a-fA-F]{6}", path.read_text(encoding="utf-8")))
    assert used <= PALETTE, sorted(used - PALETTE)
