"""The root half of ``/usr/bin/kidnix-config``. Runs as root; trusts nothing.

``/etc/kidnix/parent.toml`` and ``/etc/kidnix/session.toml`` are root-owned
because the shell runs as the child and a child-writable session length is not
a session length. The parent panel runs as the **parent**, who is in ``wheel``
and is not root, so the panel cannot write them either. This is what can.

Four properties, and all four are the reason this is a separate program rather
than a method on the panel:

1. **It validates a second time.** :mod:`kidnix_parent_panel.validate` runs on
   the payload here, as root, after it has crossed the ``pkexec`` boundary. The
   panel's own check is a courtesy to the parent; this one is the rule.
2. **It re-reads what it is about to install, through the shell's own code.**
   The rendered TOML is parsed by ``kidnix_shell.settings.ParentConfig.load``
   and ``kidnix_shell.session.load_policy`` *before* it replaces anything, so a
   file the shell would not understand never reaches ``/etc``. That closes the
   drift the shipped ``parent.toml`` header warns about, in the one direction
   the build's own check cannot: at runtime, on a parent's machine.
3. **It writes atomically.** Write to a temporary file in the same directory,
   ``fsync``, ``chmod 0644``, ``os.replace``. A power cut during a save leaves
   either the old file or the new one, never half a PIN and a machine that will
   not let anyone in.
4. **It never touches the PIN.** The hash and salt are carried across from
   whatever is on disk *now*, not from the payload, unless the payload's hash
   is byte-identical to it. Changing a PIN is ``kidnix-set-pin``'s job, which
   demands the current one and rate-limits guesses; a config writer that could
   also set a PIN would be a way around both.

Exit codes, which :mod:`kidnix_parent_panel.system` reads:

==== =========================================================
  0  written (each file named on stdout as ``wrote <path>``)
  1  refused: not root, not wheel, or the child's account
  3  the settings were invalid; nothing was written
 64  usage
==== =========================================================
"""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import catalogue, config_io
from . import model as M
from . import validate as V

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_INVALID = 3
EXIT_USAGE = 64

#: The child's account. Named rather than inferred: this helper runs as root
#: and the one caller it must never serve is the account the whole machine is
#: fenced around.
CHILD_ACCOUNT = "kid"
ADMIN_GROUP = "wheel"


# --- who is asking --------------------------------------------------------


def calling_uid(env: dict[str, str] | None = None) -> int:
    """The uid that invoked us, however we were invoked.

    ``pkexec`` sets ``PKEXEC_UID`` and scrubs the rest of the environment, so it
    cannot be forged by the caller; ``sudo`` sets ``SUDO_UID`` the same way.
    Neither is present when a root shell runs this directly, and then the real
    uid is the answer. ``PKEXEC_UID`` is consulted first because it is the one
    an unprivileged caller comes through.
    """
    environ = os.environ if env is None else env
    for key in ("PKEXEC_UID", "SUDO_UID"):
        raw = environ.get(key, "")
        if raw.isdigit():
            return int(raw)
    return os.getuid()


def caller_name(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return ""


def is_admin(uid: int) -> bool:
    """Root, or a member of ``wheel``.

    Belt to polkit's braces. The action's default is ``auth_admin_keep`` and
    ``kid`` is denied every ``org.kidnix.`` action except ``set-pin``, so a
    non-admin should never get here -- but a helper that runs as root and
    relies entirely on somebody else's rules file is one edit away from not
    being a helper any more.
    """
    if uid == 0:
        return True
    name = caller_name(uid)
    if not name or name == CHILD_ACCOUNT:
        return False
    try:
        group = grp.getgrnam(ADMIN_GROUP)
    except KeyError:
        return False
    if name in group.gr_mem:
        return True
    try:
        return pwd.getpwnam(name).pw_gid == group.gr_gid
    except KeyError:
        return False


# --- writing --------------------------------------------------------------


def write_atomically(path: Path, text: str, mode: int = 0o644) -> None:
    """Replace ``path`` with ``text``, or leave it exactly as it was.

    The temporary file is made **in the same directory** so the final
    ``os.replace`` is a rename within one filesystem, which is the only form of
    it that is atomic. ``fsync`` on the file and then on the directory is what
    makes that survive a power cut rather than merely a crash.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    try:
        directory = os.open(str(path.parent), os.O_DIRECTORY)
    except OSError:  # pragma: no cover - a filesystem that cannot be opened
        return
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def preserve_pin(payload: dict[str, Any], parent_text: str) -> dict[str, Any]:
    """Carry the PIN across from disk, whatever the payload claims.

    A config writer that could also set a PIN would be a way around
    ``kidnix-set-pin``'s "a change costs the current PIN" rule and around its
    rate limiting. So the two lines are read off the file that exists and put
    back verbatim, and a payload that tried to supply different ones is simply
    ignored -- silently, because there is no legitimate caller for whom this is
    an error to report.
    """
    import tomllib

    try:
        current = tomllib.loads(parent_text)
    except (tomllib.TOMLDecodeError, ValueError):
        current = {}
    merged = dict(payload)
    parent = dict(merged.get("parent") or {})
    parent["pin_salt"] = str(current.get("pin_salt", ""))
    parent["pin_hash"] = str(current.get("pin_hash", ""))
    merged["parent"] = parent
    return merged


def rendered(payload: dict[str, Any], tts_text: str) -> dict[str, str]:
    """``{filename: text}`` for everything this payload would replace.

    ``tts.env`` is included only when it would actually change: rewriting a
    file byte-for-byte still bumps its mtime, and a parent who changed the
    session length should not see the read-aloud service restart.
    """
    panel = M.PanelModel.from_payload(payload)
    out = {
        config_io.PARENT_TOML: config_io.render_parent_toml(panel),
        config_io.SESSION_TOML: config_io.render_session_toml(panel),
    }
    if tts_text:
        updated = config_io.render_tts_env(tts_text, panel.sound.voice)
        if updated != tts_text:
            out[config_io.TTS_ENV] = updated
    return out


# --- the shell's own opinion of what we are about to install --------------


def shell_round_trip(texts: dict[str, str], panel: M.PanelModel) -> list[V.Problem]:
    """Parse the rendered files with ``kidnix_shell`` and check they survive.

    Read-only: nothing here writes, and ``kidnix_shell`` is imported for its
    parsers alone. If it is not installed -- a developer's laptop, a container
    without the shell -- this returns nothing rather than blocking a save, and
    ``build_files/62-parent-panel.sh`` is what guarantees the image is never in
    that state.

    What it actually asserts is small and load-bearing: the file parses, the
    session length and budget come back as the numbers that went in, and every
    active child is still a profile the shell can see. A rendering bug that
    dropped a profile would otherwise reach ``/etc`` and take a child's face
    with it.
    """
    try:
        from kidnix_shell.session import load_policy
        from kidnix_shell.settings import ParentConfig
    except ImportError:  # pragma: no cover - exercised on the image
        return []

    problems: list[V.Problem] = []
    with tempfile.TemporaryDirectory(prefix="kidnix-config-check-") as scratch:
        folder = Path(scratch)
        parent_path = folder / config_io.PARENT_TOML
        session_path = folder / config_io.SESSION_TOML
        parent_path.write_text(texts[config_io.PARENT_TOML], encoding="utf-8")
        session_path.write_text(texts[config_io.SESSION_TOML], encoding="utf-8")

        try:
            config = ParentConfig.load(parent_path)
        except Exception as exc:
            return [V.Problem("parent.toml", f"the shell could not read it back ({exc}).")]
        try:
            policy = load_policy(session_path)
        except Exception as exc:
            return [V.Problem("session.toml", f"the shell could not read it back ({exc}).")]

        expected = [c.id for c in panel.children if not c.retired]
        got = [p.id for p in config.profiles]
        if expected and got != expected:
            problems.append(
                V.Problem(
                    "parent.toml",
                    f"the shell reads the children back as {got}, not {expected}.",
                )
            )
        if config.default_session_minutes != panel.time.length_minutes:
            problems.append(
                V.Problem(
                    "parent.toml",
                    "the shell reads a different session length back than the one set.",
                )
            )
        if policy.length != panel.time.length_minutes * 60:
            problems.append(
                V.Problem("session.toml", "the shell reads a different sitting length back.")
            )
        if policy.daily_budget != panel.time.daily_budget_minutes * 60:
            problems.append(
                V.Problem("session.toml", "the shell reads a different daily total back.")
            )
        if config.access.captions != panel.sound.captions:
            problems.append(V.Problem("parent.toml", "the shell reads captions back differently."))
    return problems


# --- the command ----------------------------------------------------------


def do_apply(
    payload: dict[str, Any],
    etc: Path,
    usr: Path,
    stdout: Any,
    known_ids: frozenset[str],
) -> int:
    parent_text, _session_text, tts_text = config_io.read_files(etc, usr)
    payload = preserve_pin(payload, parent_text)

    problems = V.validate_payload(payload, known_ids)
    if not V.ok(problems):
        for problem in V.fatal(problems):
            print(str(problem), file=sys.stderr)
        return EXIT_INVALID

    panel = M.PanelModel.from_payload(payload)
    texts = rendered(payload, tts_text)
    problems = shell_round_trip(texts, panel)
    if problems:
        for problem in problems:
            print(str(problem), file=sys.stderr)
        return EXIT_INVALID

    for name, text in texts.items():
        write_atomically(etc / name, text)
        print(f"wrote {etc / name}", file=stdout)
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kidnix-config",
        description="Validate and install kidnix's parent and session settings.",
    )
    parser.add_argument(
        "command",
        choices=("apply", "show", "check"),
        help="apply: read a JSON payload on stdin and install it. "
        "show: print what is on disk now, as JSON (no privilege needed). "
        "check: say nothing and change nothing; exit 0 if this account may write.",
    )
    parser.add_argument("--etc", default=str(config_io.ETC), help=argparse.SUPPRESS)
    parser.add_argument("--usr", default=str(config_io.USR), help=argparse.SUPPRESS)
    parser.add_argument(
        "--activities",
        default=str(catalogue.SYSTEM_ACTIVITY_DIR),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    etc, usr = Path(args.etc), Path(args.usr)

    if args.command == "show":
        # Deliberately unprivileged: both files are 0644 and a parent asking
        # "what is set?" should not be asked for a password to find out.
        parent_text, session_text, tts_text = config_io.read_files(etc, usr)
        json.dump(
            config_io.payload_from_toml(parent_text, session_text, tts_text),
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
        return EXIT_OK

    uid = calling_uid()
    if not is_admin(uid):
        name = caller_name(uid) or str(uid)
        print(
            f"kidnix-config: {name} may not change this machine's settings. "
            "Run it from the grown-up's account.",
            file=sys.stderr,
        )
        return EXIT_REFUSED
    if os.geteuid() != 0:
        print(
            "kidnix-config: this half must run as root; use /usr/bin/kidnix-config, "
            "which asks polkit for it.",
            file=sys.stderr,
        )
        return EXIT_REFUSED

    if args.command == "check":
        print("ok")
        return EXIT_OK

    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError) as exc:
        print(f"kidnix-config: that is not a settings payload ({exc})", file=sys.stderr)
        return EXIT_INVALID
    if not isinstance(payload, dict):
        print("kidnix-config: that is not a settings payload", file=sys.stderr)
        return EXIT_INVALID

    known = catalogue.load(Path(args.activities)).ids
    return do_apply(payload, etc, usr, sys.stdout, known)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "EXIT_INVALID",
    "EXIT_OK",
    "EXIT_REFUSED",
    "EXIT_USAGE",
    "caller_name",
    "calling_uid",
    "do_apply",
    "is_admin",
    "main",
    "preserve_pin",
    "rendered",
    "shell_round_trip",
    "write_atomically",
]
