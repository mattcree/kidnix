#!/usr/bin/env python3
"""Every SVG kidnix ships must be one the child's screen can actually open.

Standard library only, no display, no container: this is the cheap half of the
icon gate and it runs in three places -- ``just lint-svg`` over the source
tree, ``tests/image/test_icons.sh`` over the built image, and by hand.

It exists because on 2026-08-23 an audit rendered all 113 first-party SVGs
through the image's own librsvg and found **five that never reach the screen**:
three of the four first-party Home tiles, one control inside Numbers, and the
wallpaper source. Nothing in CI noticed, because nothing in CI had ever asked
an SVG to load. There were two distinct failures and this file checks for both.

1. **``--`` inside an XML comment.** XML forbids a double hyphen there. libxml2
   -- under librsvg, under glycin, under GdkPixbuf -- aborts the whole document
   and GTK substitutes the Adwaita broken-image glyph. The kidnix house style
   writes an em-dash as ``--`` in prose, and these files put that prose inside
   their licence comments. It is a one-character mistake with a total effect
   and it is invisible in an editor.

2. **``<svg>`` outside the sniff window.** gdk-pixbuf and glycin look for the
   SVG signature in roughly the first 256 bytes of the file (bisected on the
   real loader: a 208-byte preamble loads, a 308-byte one does not). A long
   licence-and-provenance comment ahead of the root element is valid XML and
   still reports ``Couldn't recognize the image file format``. Put the comment
   *inside* ``<svg>``; it survives there and it is still the first thing anyone
   reading the file sees.

What this file deliberately does NOT do is rasterise. That needs librsvg and
therefore the image; ``tests/image/test_icons.sh`` does it there.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

#: gdk-pixbuf/glycin sniff the head of the file for the SVG signature. 256 is
#: the documented buffer; the bisected real-world cliff sits between 208 and
#: 308 bytes, so this is the honest number to hold the tree to.
SNIFF_WINDOW = 256

SVG_NS = "{http://www.w3.org/2000/svg}svg"


def collect(roots: list[Path], excludes: tuple[str, ...]) -> list[Path]:
    """Every ``.svg`` under *roots*, minus anything under an excluded name."""
    found: set[Path] = set()
    for root in roots:
        if root.is_file():
            found.add(root)
            continue
        for path in root.rglob("*.svg"):
            if any(part in excludes for part in path.parts):
                continue
            found.add(path)
    return sorted(found)


def check(path: Path) -> str | None:
    """Return a one-line reason this file cannot be loaded, or ``None``."""
    try:
        blob = path.read_bytes()
    except OSError as exc:  # pragma: no cover - only a broken checkout
        return f"unreadable: {exc}"
    if not blob.strip():
        return "empty file"
    try:
        root = ElementTree.fromstring(blob)
    except ElementTree.ParseError as exc:
        return f"not well-formed XML: {exc}"
    if root.tag != SVG_NS:
        return f"root element is {root.tag!r}, not an SVG"
    start = blob.find(b"<svg")
    if start < 0:
        return "no literal <svg element"
    if start >= SNIFF_WINDOW:
        return (
            f"<svg> starts at byte {start}, past the {SNIFF_WINDOW}-byte sniff "
            "window -- move the comment inside <svg>"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="skip any path with this directory name in it (repeatable)",
    )
    parser.add_argument(
        "--min",
        type=int,
        default=1,
        dest="minimum",
        help="fail if fewer than this many SVGs were found (default 1)",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    paths = collect(args.roots, tuple(args.exclude))
    failures: list[tuple[Path, str]] = []
    for path in paths:
        reason = check(path)
        if reason is not None:
            failures.append((path, reason))

    for path, reason in failures:
        print(f"  \033[31mFAIL\033[0m  {path}: {reason}", file=sys.stderr)

    if len(paths) < args.minimum:
        print(
            f"  \033[31mFAIL\033[0m  found {len(paths)} SVGs, expected at least "
            f"{args.minimum} -- did a root move?",
            file=sys.stderr,
        )
        return 1
    if failures:
        print(f"{len(failures)} of {len(paths)} SVGs cannot be loaded", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"  \033[32mPASS\033[0m  {len(paths)} SVGs parse and sniff as SVG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
