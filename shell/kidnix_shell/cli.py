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
from .activities import LoadResult, default_activity_dirs, load_activities, load_directory
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
        "--config", type=Path, help="parent config TOML to use instead of the default"
    )
    parser.add_argument("--session-config", type=Path, help="session policy TOML")
    parser.add_argument(
        "--activities", type=Path, action="append", default=[], help="extra activity directory"
    )
    parser.add_argument(
        "--windowed", action="store_true", help="do not go fullscreen (development)"
    )
    parser.add_argument("--run-seconds", type=float, help="quit after N seconds (smoke tests)")
    parser.add_argument(
        "--speech",
        choices=("auto", "speechd", "spd-say", "null"),
        default="auto",
        help="force a read-aloud backend",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser


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

    for activity in sorted(total.activities, key=lambda a: a.id):
        resume = " resumable" if activity.supports_resume else ""
        watches = len(activity.journal_watch)
        print(f"ok    {activity.id:<14} {activity.category:<6} {watches} watch dir(s){resume}")
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

    config_path = args.config or paths.parent_config
    config = ParentConfig.load(config_path)

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
        policy = SessionPolicy.demo()
        log.info("demo world in %s (%d activities, 3-minute session)", root, len(activities))
    else:
        policy = load_policy(args.session_config or paths.session_config)
        directories = default_activity_dirs(paths.data_home) + list(args.activities)
        result = load_activities(directories, home=paths.home)
        for error in result.errors:
            log.warning("ignoring manifest: %s", error)
        activities = result.activities
        if not activities:
            log.warning("no activities found in %s", [str(d) for d in directories])

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
    )
    return int(application.run([]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
