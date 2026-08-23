"""``kidnix-parent-panel``. Opens the window; also answers without one.

The three flags that do **not** need a display are the ones a build, a test and
a parent-on-the-phone need:

``--version``
    what is installed.
``--self-check``
    the panel's constants against ``kidnix_shell``'s, the machine's config
    through the panel's own validator, and whether the root helper and the
    activity manifests are where they should be. ``build_files/62-parent-panel.sh``
    runs this inside the image, where there is no display and no D-Bus, and
    fails the build on a non-zero exit.
``--dump``
    what the panel would write, to stdout, without writing it. The fastest way
    to answer "what is this app actually going to do to my machine".
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, catalogue, config_io, system
from . import validate as V


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kidnix-parent-panel",
        description="kidnix's settings for a grown-up: children, time, activities, "
        "sound, their things, and updates.",
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="check this installation without opening a window; exit non-zero on a problem",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="print the files the panel would write, without writing them",
    )
    parser.add_argument(
        "--screenshot",
        metavar="DIR",
        help="photograph every tab into DIR and quit (run under Broadway, never "
        "on a desktop -- see docs/design/parent-panel.md)",
    )
    parser.add_argument("--etc", default=str(config_io.ETC), help=argparse.SUPPRESS)
    parser.add_argument("--usr", default=str(config_io.USR), help=argparse.SUPPRESS)
    parser.add_argument(
        "--activities", default=str(catalogue.SYSTEM_ACTIVITY_DIR), help=argparse.SUPPRESS
    )
    return parser


def self_check(etc: Path, usr: Path, activities: Path, out=sys.stdout) -> int:
    """Everything that can be proved without a display. Returns an exit code."""
    failures = 0

    def report(ok: bool, what: str, detail: str = "") -> None:
        nonlocal failures
        print(
            f"  {'ok  ' if ok else 'FAIL'}  {what}{(' -- ' + detail) if detail else ''}", file=out
        )
        if not ok:
            failures += 1

    print(f"kidnix-parent-panel {__version__}", file=out)

    drift = V.cross_check_against_shell()
    report(
        not drift,
        "the panel's copy of the shell's schema is current",
        "; ".join(str(d) for d in drift),
    )

    model = config_io.load_model(etc, usr)
    known = catalogue.load(activities)
    report(
        bool(known.entries) or not activities.is_dir(),
        f"activity manifests load from {activities}",
        f"{len(known.entries)} found, {len(known.broken)} unreadable",
    )
    for path, why in known.broken:
        report(False, f"manifest {path}", why)

    problems = V.validate(model, known.ids)
    for problem in V.fatal(problems):
        report(False, "the machine's current settings", str(problem))
    if V.ok(problems):
        report(True, "the machine's current settings validate")

    # The rendered files must survive the shell's own readers. This is the same
    # round trip kidnix-config does as root, run here against what is on disk.
    from .helper import rendered, shell_round_trip

    texts = rendered(model.to_payload(), "")
    round_trip = shell_round_trip(texts, model)
    report(
        not round_trip,
        "the shell reads back what the panel would write",
        "; ".join(str(p) for p in round_trip),
    )

    for binary, why in (
        (system.CONFIG_HELPER, "writes the settings"),
        (system.EXPORT_HELPER, "copies the child's work out"),
        (system.WIPE_HELPER, "deletes the child's work"),
        (system.SET_PIN_HELPER, "changes the grown-up PIN"),
    ):
        report(system.have(binary), f"{binary} is installed ({why})")

    verify = system.signature_policy()
    print(f"  note  {verify.sentence}", file=out)

    print(f"\n{'ok' if failures == 0 else str(failures) + ' problem(s)'}", file=out)
    return 0 if failures == 0 else 1


def dump(etc: Path, usr: Path, out=sys.stdout) -> int:
    model = config_io.load_model(etc, usr)
    for name, text in (
        (config_io.PARENT_TOML, config_io.render_parent_toml(model)),
        (config_io.SESSION_TOML, config_io.render_session_toml(model)),
    ):
        print(f"# ===== {etc / name} =====", file=out)
        print(text, file=out)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    etc, usr = Path(args.etc), Path(args.usr)
    activities = Path(args.activities)

    if args.version:
        print(f"kidnix-parent-panel {__version__}")
        return 0
    if args.self_check:
        return self_check(etc, usr, activities)
    if args.dump:
        return dump(etc, usr)
    if args.screenshot:
        from .screenshots import run_screenshots

        return run_screenshots(Path(args.screenshot), etc, usr, activities)

    from .ui import run

    return run([sys.argv[0]])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["build_parser", "dump", "main", "self_check"]
