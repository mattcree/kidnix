"""theme.css, checked with arithmetic rather than with an opinion.

Two of the CCI audit's findings (2026-08-22) were things nobody had *computed*:

* **06 #25 / 03 #31.** ``.not-allowed`` drew its dashed border in
  ``rgba(0, 0, 0, 0.18)``, which composites to ``#cecbc4`` on ``@kid-paper``:
  **1.5:1**. That border is the whole of SYNTHESIS G3's "ask a grown-up"
  affordance -- the tile has no fill, so there is nothing else carrying it --
  and 1.5:1 is a clear WCAG 1.4.11 failure.
* **06 #20.** The grown-up sheet asked for ``"Atkinson Hyperlegible"`` while
  the image installs the family ``"Atkinson Hyperlegible Next"``. The names do
  not match, so the sheet silently fell back to Cantarell and the only way to
  notice was to diff ``theme.css`` against ``build_files/36-fonts.sh``.

So this module reads the literal values out of ``theme.css`` and recomputes
both. No display, no GTK, no screenshot: WCAG relative luminance is arithmetic
and a font family list is a string.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from kidnix_shell.settings import PROFILE_COLOURS

THEME = Path(__file__).resolve().parents[1] / "kidnix_shell" / "theme.css"

#: WCAG 2.2 SC 1.4.11 -- user interface components and graphical objects.
NON_TEXT_MIN = 3.0
#: WCAG 2.2 SC 1.4.3 (AA) for text. 08 section 3.4 prefers 4.5 for the band.
TEXT_MIN = 4.5
#: 06 #25 asks for 7:1 on child-facing body text, which is AAA.
CHILD_TEXT_MIN = 7.0


# --- WCAG arithmetic -------------------------------------------------------


def _channel(value: int) -> float:
    srgb = value / 255.0
    return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4


def rgb(colour: str) -> tuple[int, int, int]:
    """``#rrggbb`` (or ``#rgb``) to a triple. Raises on anything else."""
    text = colour.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        raise ValueError(f"{colour!r} is not a hex colour")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def luminance(colour: str) -> float:
    red, green, blue = rgb(colour)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast(first: str, second: str) -> float:
    """WCAG relative-luminance contrast ratio, 1.0 to 21.0."""
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# --- reading theme.css -----------------------------------------------------


def css() -> str:
    """The stylesheet with comments removed -- they hold braces and prose."""
    return re.sub(r"/\*.*?\*/", "", THEME.read_text(encoding="utf-8"), flags=re.S)


def colours() -> dict[str, str]:
    """Every ``@define-color`` in the stylesheet."""
    return {
        name: value.strip()
        for name, value in re.findall(r"@define-color\s+([\w-]+)\s+([^;]+);", css())
    }


def selectors_of(prelude: str) -> list[str]:
    """The selector list out of the text between one ``}`` and the next ``{``.

    Everything up to the last ``;`` is the previous ``@define-color`` run, not
    a selector, so it is dropped.
    """
    _, _, tail = prelude.rpartition(";")
    return [s.strip() for s in tail.replace("\n", " ").split(",") if s.strip()]


def block(selector: str) -> str:
    """The declarations of the rule whose selector list contains ``selector``."""
    for match in re.finditer(r"([^{}]*)\{([^{}]*)\}", css()):
        if selector in selectors_of(match.group(1)):
            return match.group(2)
    raise AssertionError(f"no rule for {selector!r} in theme.css")


def declaration(selector: str, prop: str) -> str:
    """One property's value from one rule."""
    match = re.search(rf"(?<![\w-]){re.escape(prop)}\s*:\s*([^;]+);", block(selector))
    assert match is not None, f"{selector!r} declares no {prop!r}"
    return match.group(1).strip()


def resolved(value: str) -> str:
    """Turn ``@kid-edge`` into the hex it is defined as."""
    value = value.strip()
    return colours()[value[1:]] if value.startswith("@") else value


def border_colour(selector: str) -> str:
    """The colour out of a ``border: 4px dashed @kid-edge-strong`` shorthand."""
    for prop in ("border-color", "border"):
        try:
            value = declaration(selector, prop)
        except AssertionError:
            continue
        token = value.split()[-1]
        return resolved(token)
    raise AssertionError(f"{selector!r} declares no border colour")


# --- the palette itself ----------------------------------------------------


def test_every_edge_colour_is_a_computable_literal() -> None:
    """No ``rgba(0, 0, 0, 0.18)``: a ratio you cannot compute is one nobody did."""
    for name in ("kid-edge", "kid-edge-strong"):
        assert rgb(colours()[name])


def test_the_ordinary_edge_clears_three_to_one_on_paper_and_on_hover() -> None:
    """A tile's fill *is* the page's paper, so the border is its only boundary."""
    palette = colours()
    edge = palette["kid-edge"]
    assert contrast(edge, palette["kid-paper"]) >= NON_TEXT_MIN
    assert contrast(edge, "#ffffff") >= NON_TEXT_MIN  # button.tile:hover


def test_the_strong_edge_clears_three_to_one_with_room_to_spare() -> None:
    palette = colours()
    assert contrast(palette["kid-edge-strong"], palette["kid-paper"]) >= 5.0


# --- 06 #25: the not-allowed tile, which is the whole G3 affordance --------


def test_the_not_allowed_border_clears_three_to_one() -> None:
    """The audit's 1.5:1. This is the assertion that keeps it fixed."""
    palette = colours()
    edge = border_colour("button.tile.not-allowed")
    assert contrast(edge, palette["kid-paper"]) >= NON_TEXT_MIN, edge


def test_the_not_allowed_tile_has_no_fill_of_its_own() -> None:
    """Which is *why* the border has to carry 3:1 -- there is nothing else."""
    assert declaration("button.tile.not-allowed", "background-color") == "transparent"


def test_the_not_allowed_tile_is_outlined_not_greyed_out() -> None:
    """08 section 3.4c: never grey out. Grey survives neither greyscale nor CVD."""
    declarations = block("button.tile.not-allowed")
    assert "dashed" in declarations
    assert "opacity" not in declarations


def test_the_all_done_tile_border_clears_three_to_one_both_ways() -> None:
    palette = colours()
    edge = border_colour("button.tile.all-done")
    fill = declaration("button.tile.all-done", "background-color")
    assert contrast(edge, fill) >= NON_TEXT_MIN
    assert contrast(edge, palette["kid-paper"]) >= NON_TEXT_MIN


# --- 08 section 3.4: the band ---------------------------------------------


def test_band_button_text_clears_four_and_a_half_to_one() -> None:
    """The label and the icon inside a band button, against the button."""
    ink = resolved(declaration(".band button", "color"))
    paper = resolved(declaration(".band button", "background-color"))
    assert contrast(ink, paper) >= TEXT_MIN
    assert contrast(ink, paper) >= CHILD_TEXT_MIN  # and comfortably AAA


def test_a_band_button_stands_out_from_the_band_in_every_profile_colour() -> None:
    """The button's own boundary. ``@kid-primary`` is replaced at runtime by
    the active child's colour (``theme.dynamic_css``), so all four have to hold.
    """
    paper = resolved(declaration(".band button", "background-color"))
    for primary, _secondary in PROFILE_COLOURS:
        assert contrast(paper, primary) >= NON_TEXT_MIN, primary


def test_a_pressed_band_button_is_still_the_same_paper() -> None:
    """Nothing in the press state may drop the button's contrast."""
    assert contrast(resolved(declaration(".band button:hover", "background-color")), "#0f8a8a") >= (
        NON_TEXT_MIN
    )


# --- text everywhere else -------------------------------------------------


def test_child_facing_body_text_clears_seven_to_one() -> None:
    """06 #25 asks for AAA on the text a pre-reader is trying to decode."""
    palette = colours()
    assert contrast(palette["kid-ink"], palette["kid-paper"]) >= CHILD_TEXT_MIN


def test_the_sleeping_screen_is_dark_and_still_legible() -> None:
    ink = declaration(".sleeping", "color")
    paper = declaration(".sleeping", "background-color")
    assert contrast(ink, paper) >= CHILD_TEXT_MIN


def test_the_pin_error_line_clears_four_and_a_half_to_one() -> None:
    palette = colours()
    assert contrast(declaration(".pin-error", "color"), palette["kid-paper"]) >= TEXT_MIN


# --- the reserved highlight ------------------------------------------------


def test_the_reserved_highlight_never_travels_without_an_edge() -> None:
    """@kid-highlight is 1.35:1 on paper -- legible as colour, not as an edge.

    Rather than spend the one reserved colour (08 section 3.4b) on a darker
    yellow, the focus and speaking rings take the control's border to full ink
    while they are up, so the *indicator* has a 16.6:1 boundary on both sides
    of the yellow even though the yellow itself does not.
    """
    palette = colours()
    assert contrast(palette["kid-highlight"], palette["kid-paper"]) < NON_TEXT_MIN
    for selector in (".speaking", ":focus-visible"):
        edge = resolved(declaration(selector, "border-color"))
        assert contrast(edge, palette["kid-paper"]) >= NON_TEXT_MIN, selector


def test_the_highlight_is_still_the_only_reserved_colour() -> None:
    """One colour, a handful of uses, all of them "the thing you can touch now".

    ``.band button.offer.kid-new`` is the newest, and it is the most literal:
    three seconds of ring on the two ending choices as they arrive in the band,
    which is the one moment in the product that is exactly what the reserved
    colour is reserved for (08 section 3.4, forum #55).
    """
    body = css()
    users = re.findall(r"([^{}]*)\{[^{}]*@kid-highlight[^{}]*\}", body)
    names = {name for group in users for name in selectors_of(group)}
    assert names == {
        ".speaking",
        ":focus-visible",
        "button:focus-visible",
        ".tile:focus-visible",
        ".hold-progress progress",
        ".band button.offer.kid-new",
    }


# --- 06 #19, #20: the two faces the image actually ships ------------------


def test_the_child_face_asks_for_andika_with_fallbacks() -> None:
    family = declaration("window.kidnix", "font-family")
    assert '"Andika"' in family
    assert '"Cantarell"' in family
    assert family.rstrip().endswith("sans-serif")


def test_the_grownup_sheet_asks_for_the_family_the_image_installs() -> None:
    """build_files/36-fonts.sh installs `atkinson-hyperlegible-next-fonts`.

    Its family name is "Atkinson Hyperlegible Next". Asking for "Atkinson
    Hyperlegible" alone matched nothing on the image and fell back silently.
    """
    family = declaration(".grownup", "font-family")
    assert '"Atkinson Hyperlegible Next"' in family
    assert '"Atkinson Hyperlegible"' in family
    assert family.index('"Atkinson Hyperlegible Next"') < family.index('"Cantarell"')
    assert family.rstrip().endswith("sans-serif")


@pytest.mark.parametrize("selector", ["window.kidnix", ".grownup", ".pin-pad button"])
def test_no_font_stack_ends_without_a_generic(selector: str) -> None:
    """A stack whose last entry is a family name can resolve to nothing."""
    family = declaration(selector, "font-family").rstrip()
    assert family.split(",")[-1].strip() in {"sans-serif", "serif", "monospace"}


def test_the_shipped_font_packages_still_match_the_stylesheet() -> None:
    """The other half of the 06 #20 bug: the image and the CSS must agree."""
    fonts_sh = Path(__file__).resolve().parents[2] / "build_files" / "36-fonts.sh"
    if not fonts_sh.is_file():  # pragma: no cover - outside the checkout
        pytest.skip("running outside the kidnix checkout")
    installed = fonts_sh.read_text(encoding="utf-8")
    for family in ("Andika", "Atkinson Hyperlegible Next"):
        assert f'check_family "{family}"' in installed, family
        assert f'"{family}"' in css(), family
