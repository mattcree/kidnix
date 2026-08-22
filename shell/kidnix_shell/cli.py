"""``kidnix-shell`` -- the command line.

Logging goes to stderr, which is the systemd journal in the real session
(spec section 7). There is no telemetry and nothing is written anywhere the
parent cannot read.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .activities import (
    LoadResult,
    default_activity_dirs,
    load_activities,
    load_directory,
    resolve_availability,
)
from .metrics import ScreenOverride, parse_screen
from .session import SessionPolicy, load_policy
from .settings import ParentConfig, Paths

log = logging.getLogger("kidnix_shell")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kidnix-shell",
        description="The kidnix activity shell.",
    )
    parser.add_argument("--version", action="version", version=f"kidnix-shell {__version__}")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="fake activities and a three-minute session, for demos and CI",
    )
    parser.add_argument(
        "--validate-manifests",
        nargs="?",
        const="",
        metavar="DIR",
        help="check activity manifests and exit non-zero if any are invalid",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help=(
            "parent config TOML to use instead of the root-owned one "
            "(development only: the shell never reads the child's own config)"
        ),
    )
    parser.add_argument("--session-config", type=Path, help="session policy TOML")
    parser.add_argument(
        "--activities", type=Path, action="append", default=[], help="extra activity directory"
    )
    parser.add_argument(
        "--windowed", action="store_true", help="do not go fullscreen (development)"
    )
    parser.add_argument(
        "--screen",
        type=screen_override,
        metavar="WxH[@DPI]",
        help=(
            "pretend the monitor is this size and density, e.g. 1280x800@102 -- "
            "the way to see on a big desktop what a small panel gets"
        ),
    )
    parser.add_argument(
        "--generate-earcons",
        nargs="?",
        const="",
        metavar="DIR",
        help="write the four generated earcons and exit (used at image build)",
    )
    parser.add_argument("--run-seconds", type=float, help="quit after N seconds (smoke tests)")
    parser.add_argument(
        "--screenshot",
        type=Path,
        metavar="PATH",
        help="write a PNG of the shell's own window before quitting (development)",
    )
    parser.add_argument(
        "--speech",
        choices=("auto", "speechd", "spd-say", "null"),
        default="auto",
        help="force a read-aloud backend",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser


def screen_override(text: str) -> ScreenOverride:
    """argparse type for ``--screen``."""
    try:
        return parse_screen(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def validate_manifests(directory: str, paths: Paths) -> int:
    """CI gate: report every manifest and exit non-zero on any schema error."""
    directories = [Path(directory)] if directory else default_activity_dirs(paths.data_home)

    total = LoadResult()
    for one in directories:
        result = load_directory(one, home=paths.home)
        total.activities.extend(result.activities)
        total.errors.extend(result.errors)
        if not one.is_dir():
            print(f"  (no such directory: {one})")

    # Home order, not alphabetical: this listing is also how a human checks
    # that the grid comes out the way they meant it to.
    for activity in sorted(total.activities, key=lambda a: a.sort_key):
        resume = " resumable" if activity.supports_resume else ""
        watches = len(activity.journal_watch)
        order = "----" if activity.order is None else f"{activity.order:>4}"
        print(
            f"ok    {order}  {activity.id:<14} {activity.name:<18} "
            f"{activity.category:<6} {watches} watch dir(s){resume}"
        )
        if not activity.goal:
            print("      (no 'goal' line -- the parent panel will have nothing to show)")
    for error in total.errors:
        print(f"ERROR {error}", file=sys.stderr)

    print(f"\n{len(total.activities)} valid, {len(total.errors)} invalid")
    return 1 if total.errors else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)

    paths = Paths.from_env()

    if args.validate_manifests is not None:
        return validate_manifests(args.validate_manifests, paths)

    if args.generate_earcons is not None:
        from .sound import generate, package_sounds_dir

        directory = Path(args.generate_earcons) if args.generate_earcons else package_sounds_dir()
        for path in generate(directory):
            print(f"wrote {path}")
        return 0

    # The parent config is read only from root-owned locations; --config is a
    # developer naming a file, and is the only other path we will ever read.
    config = ParentConfig.discover(args.config)

    if args.demo:
        from .demo import build_demo_world

        root, activities, allowed = build_demo_world()
        # Keep the demo entirely inside its own directory: the journal, the
        # usage state and the parent config all live there and nothing touches
        # the real ones.
        paths = Paths(
            home=root,
            data_home=root / "data",
            config_home=root / "config",
            cache_home=root / "cache",
            state_home=root / "state",
            runtime_dir=paths.runtime_dir,
        )
        config.allowed_activity_ids = allowed
        config.path = paths.config_home / "kidnix" / "parent.toml"
        config.read_only = False
        policy = SessionPolicy.demo()
        log.info("demo world in %s (%d activities, 3-minute session)", root, len(activities))
    else:
        policy = load_policy(args.session_config or paths.session_config)
        directories = default_activity_dirs(paths.data_home) + list(args.activities)
        result = load_activities(directories, home=paths.home)
        for error in result.errors:
            log.warning("ignoring manifest: %s", error)
        # One PATH lookup (and at most one `flatpak info`) per program, at
        # startup, so Home never draws a tile for something that cannot run.
        activities = resolve_availability(result.activities)
        if not activities:
            log.warning("no activities found in %s", [str(d) for d in directories])
        elif not any(a.on_home for a in activities):
            log.warning("no activity on Home is installed; the child gets an empty grid")

    from .app import ShellApplication

    application = ShellApplication(
        paths=paths,
        config=config,
        policy=policy,
        activities=activities,
        demo=args.demo,
        fullscreen=not args.windowed,
        speech_backend=None if args.speech == "auto" else args.speech,
        run_seconds=args.run_seconds,
        screen=args.screen,
        screenshot=args.screenshot,
    )
    return int(application.run([]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
