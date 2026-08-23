"""``kidnix-shell`` -- the command line.

Logging goes to stderr, which is the systemd journal in the real session
(spec section 7). There is no telemetry and nothing is written anywhere the
parent cannot read.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .activities import (
    LoadResult,
    default_activity_dirs,
    load_activities,
    load_directory,
    resolve_availability,
    resolve_shelves,
)
from .metrics import ScreenOverride, parse_screen
from .research import discover as discover_research
from .session import SessionPolicy, load_policy
from .settings import DEFAULT_PIN, ParentConfig, Paths

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
        "--set-pin",
        nargs="?",
        const="",
        metavar="PATH",
        help=(
            "set the grown-up PIN and exit. Run as root (sudo kidnix-shell --set-pin): "
            "the shell running as the child cannot write /etc/kidnix/parent.toml, and "
            "that is what keeps the PIN out of the child's hands"
        ),
    )
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
        "--start-on",
        choices=(
            "choosing",
            "next-after",
            "home",
            "shelf",
            "journal",
            "put-away",
            "goodbye",
            "resting",
            "offer",
        ),
        default="choosing",
        help=(
            "which surface to open on (development). The child always starts on "
            "Who's here?; the others drive the shell forward immediately so a "
            "--screenshot run photographs the surface you asked for rather than "
            "the chooser. 'goodbye' also picks a next-after so the ending shows "
            "the child's own choice."
        ),
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
        # Spec 7c: the one field that decides whether Put away may cover this
        # activity, so it is on the line a human reads before shipping.
        asks = f" asks ({activity.quit_grace:.0f}s)" if activity.asks_before_quitting else ""
        watches = len(activity.journal_watch)
        order = "----" if activity.order is None else f"{activity.order:>4}"
        print(
            f"ok    {order}  {activity.id:<14} {activity.name:<18} "
            f"{activity.category:<6} {watches} watch dir(s){resume}{asks}"
        )
        if not activity.goal:
            print("      (no 'goal' line -- the parent panel will have nothing to show)")
    for error in total.errors:
        print(f"ERROR {error}", file=sys.stderr)

    print(f"\n{len(total.activities)} valid, {len(total.errors)} invalid")
    return 1 if total.errors else 0


def set_pin(target: str) -> int:
    """``kidnix-shell --set-pin``: the small root helper the sheet points at.

    The grown-up sheet has a PIN pad that can *choose* a PIN, and on a real
    machine it cannot save one -- ``/etc/kidnix/parent.toml`` is root-owned,
    which is the whole reason the gate means anything. Rather than pretend to
    save, the sheet prints the command to run, and this is that command.

    Mags (forum #13, #56) is the reader: "make it ask me to choose my own four
    numbers, and let me pick them somewhere he is not looking." One prompt, no
    echo, typed twice, and it says which file it wrote.
    """
    import getpass

    from .settings import SYSTEM_CONFIG_DIR, rewrite_pin

    path = Path(target) if target else SYSTEM_CONFIG_DIR / "parent.toml"
    directory = path.parent
    if not (directory.is_dir() and os.access(directory, os.W_OK)):
        print(f"Cannot write {path}. Run this as root:\n\n    sudo kidnix-shell --set-pin\n")
        return 1
    if path.is_file() and not os.access(path, os.W_OK):
        print(f"Cannot write {path} (it is root-owned). Run:\n\n    sudo kidnix-shell --set-pin\n")
        return 1

    print(f"Setting the grown-up PIN in {path}.")
    print("Four digits. It is not echoed, and it is stored only as a hash.")
    first = getpass.getpass("New PIN: ").strip()
    if len(first) != 4 or not first.isdigit():
        print("A PIN is four digits. Nothing was changed.")
        return 1
    if first == DEFAULT_PIN:
        print(f"{DEFAULT_PIN} is the PIN every kidnix ships with. Pick another.")
        return 1
    if getpass.getpass("Type it again: ").strip() != first:
        print("Those two did not match. Nothing was changed.")
        return 1
    rewrite_pin(path, first)
    print(f"Done. {path} now has your PIN in it; the old one no longer works.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)

    paths = Paths.from_env()

    if args.validate_manifests is not None:
        return validate_manifests(args.validate_manifests, paths)

    if args.set_pin is not None:
        return set_pin(args.set_pin)

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
        # A demo shell is a developer's shell: it must not open on the "choose
        # a PIN" flow every time somebody wants to look at Home.
        config.pin_configured = True
        shelves = resolve_shelves(activities, home=root)
        # The demo allow-list is non-empty on purpose (one tile is outlined to
        # show SYNTHESIS G3), and a non-empty list is a *restriction* -- so the
        # shelf's children have to be on it or a demo shelf is six dashed
        # tiles saying "ask a grown-up".
        allowed += [child.id for children in shelves.values() for child in children]
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
        # A shelf tile's children are ordinary manifests one directory down
        # (docs/spikes/panel-wave-c.md section 2). Loaded here, once, because
        # Home has to know whether a shelf has anything on it *before* drawing
        # its tile -- a tile that opens an empty screen is a tile that lies.
        shelves = resolve_shelves(activities, home=paths.home)
        if not activities:
            log.warning("no activities found in %s", [str(d) for d in directories])
        elif not any(a.on_home for a in activities):
            log.warning("no activity on Home is installed; the child gets an empty grid")

    # Every instrument in the shell is behind this file, and it ships false
    # (spec 7d #10). Read once, here, and handed down; nothing decides for
    # itself whether it may log.
    research = discover_research()

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
        start_on=args.start_on,
        shelves=shelves,
        research=research,
    )
    return int(application.run([]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
