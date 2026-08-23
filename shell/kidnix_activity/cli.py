"""``kidnix-activity`` -- the SDK's one command.

Two subcommands, both of which exist to be run by a person and by CI:

``new <name>``
    write the skeleton (:mod:`kidnix_activity.scaffold`).
``validate <path>...``
    check manifests, exiting non-zero on any error, so a build can gate on it
    exactly as ``kidnix-shell --validate-manifests`` does for the shipped set.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .manifest import DEFAULT_AGE_BAND, DEFAULT_CATEGORY, DEFAULT_GOAL, validate_paths
from .scaffold import scaffold

log = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_PROBLEM = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kidnix-activity",
        description="Build a kidnix activity: scaffold one, or check its manifest.",
    )
    parser.add_argument("--version", action="version", version=f"kidnix-activity {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="write the skeleton for a new activity")
    new.add_argument("name", help='what a child sees, e.g. "Clock and time"')
    new.add_argument(
        "--dir", type=Path, default=Path.cwd(), help="where to write it (default: here)"
    )
    new.add_argument("--goal", default=DEFAULT_GOAL, help="one honest line for a parent")
    new.add_argument("--category", default=DEFAULT_CATEGORY, choices=("make", "learn", "play"))
    new.add_argument("--age-band", default=DEFAULT_AGE_BAND, help='e.g. "4-5" or "6-8"')
    new.add_argument("--force", action="store_true", help="overwrite existing files")

    check = sub.add_parser("validate", help="check one or more manifests (or a directory)")
    check.add_argument("paths", nargs="+", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "new":
        return _new(args)
    return _validate(args)


def _new(args: argparse.Namespace) -> int:
    try:
        written = scaffold(
            args.name,
            args.dir,
            goal=args.goal,
            category=args.category,
            age_band=args.age_band,
            overwrite=args.force,
        )
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"kidnix-activity: {exc}", file=sys.stderr)
        return EXIT_PROBLEM
    for path in written:
        print(path)
    return EXIT_OK


def _validate(args: argparse.Namespace) -> int:
    reports = validate_paths(list(args.paths))
    if not reports:
        print("kidnix-activity: no manifests found", file=sys.stderr)
        return EXIT_PROBLEM
    problems = 0
    for report in reports:
        for line in report.lines():
            print(line, file=sys.stderr)
        if report.ok:
            print(f"{report.path}: ok")
        else:
            problems += 1
    return EXIT_PROBLEM if problems else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
