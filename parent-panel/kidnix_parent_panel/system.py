"""Every command the panel runs, and every answer it parses.

Two halves, split so the interesting one is testable:

* **pure parsers** -- ``bootc status --format=json`` into something with named
  fields, ``bootc upgrade --check`` into "there is / is not an update", and
  ``/etc/containers/policy.json`` into "would this machine accept an image at
  all". These are functions over text and are what the tests exercise.
* **a thin runner** -- one callable that forks. The panel is handed one; the
  tests are handed a fake, and nothing in ``parent-panel/tests`` ever starts a
  process.

**Nothing here is a metric.** The Updates tab shows what version is booted and
whether one is waiting, and the Their-things tab runs the export and wipe
helpers. There is no time-on-device chart, no session history, no "your child
opened Draw 14 times" -- SYNTHESIS G1 says the parent's controls set the shape
of the sandbox and get out of the way, and G4's "see, export and delete" is
their drawings, not a dashboard about them.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

#: Where the merged signature policy lives (``build_files/75-supply-chain.sh``
#: merges kidnix's scope into the base image's file rather than replacing it,
#: so the base's own trust survives).
POLICY_JSON = Path("/etc/containers/policy.json")
#: The cosign public key that policy names. Its **presence** is the difference
#: between "this machine can take an update" and "every pull fails closed".
SIGNING_KEY = Path("/etc/pki/containers/kidnix.pub")
#: The repository kidnix images are published to.
IMAGE_REPO = "ghcr.io/mattcree/kidnix"

CONFIG_HELPER = "/usr/bin/kidnix-config"
EXPORT_HELPER = "/usr/bin/kidnix-export"
WIPE_HELPER = "/usr/bin/kidnix-wipe"
SET_PIN_HELPER = "/usr/bin/kidnix-set-pin"


@dataclass(frozen=True)
class Completed:
    """What a runner gives back. A subset of ``CompletedProcess``, by value."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def message(self) -> str:
        """The most useful line to show a parent, whichever stream it is on."""
        for stream in (self.stderr, self.stdout):
            text = stream.strip()
            if text:
                return text.splitlines()[-1]
        return ""


Runner = Callable[..., Completed]


def run(argv: Sequence[str], stdin: str | None = None, timeout: int = 120) -> Completed:
    """The real runner. The only place in the panel that forks.

    Never raises: a missing binary, a timeout and a non-zero exit all come back
    as a :class:`Completed` with something a parent can read in ``stderr``. The
    panel's job when a helper fails is to say what failed, not to disappear.
    """
    try:
        proc = subprocess.run(
            list(argv),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return Completed(127, "", f"{argv[0]} is not on this machine")
    except subprocess.TimeoutExpired:
        return Completed(124, "", f"{argv[0]} took longer than {timeout} seconds and was stopped")
    except OSError as exc:  # pragma: no cover - a broken exec environment
        return Completed(1, "", str(exc))
    return Completed(proc.returncode, proc.stdout or "", proc.stderr or "")


def have(binary: str) -> bool:
    return shutil.which(binary) is not None or Path(binary).is_file()


# --- writing the config through the root helper ---------------------------


@dataclass(frozen=True)
class ApplyResult:
    """What came back from ``kidnix-config apply``."""

    ok: bool
    #: The files it says it replaced.
    written: tuple[str, ...] = ()
    #: One sentence for the parent. Empty when everything worked.
    message: str = ""
    #: True when polkit refused or was dismissed -- a different sentence from a
    #: validation failure, because the fix is different (try again and type the
    #: password, versus fix the setting).
    refused: bool = False


#: ``kidnix-config``'s exit codes, and the panel's half of that contract.
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_INVALID = 3
EXIT_USAGE = 64
#: What ``pkexec`` itself returns when the dialogue is dismissed or the
#: authorisation is refused (pkexec(1)).
EXIT_PKEXEC_DISMISSED = 126
EXIT_PKEXEC_NOT_AUTHORISED = 127


def apply_settings(payload: dict[str, Any], runner: Runner = run) -> ApplyResult:
    """Hand the payload to ``kidnix-config`` and read the verdict.

    The payload travels on **stdin**, never in ``argv``: an argument is visible
    in ``/proc`` to every process on the machine, and while none of these
    settings is a secret, the same pipe carries the PIN hash across.
    """
    text = json.dumps(payload, sort_keys=True)
    result = runner([CONFIG_HELPER, "apply"], stdin=text, timeout=60)
    return _apply_result(result)


def _apply_result(result: Completed) -> ApplyResult:
    if result.returncode == EXIT_OK:
        written = tuple(
            line.split(" ", 1)[1].strip()
            for line in result.stdout.splitlines()
            if line.startswith("wrote ")
        )
        return ApplyResult(True, written, "")
    if result.returncode in (EXIT_PKEXEC_DISMISSED, EXIT_PKEXEC_NOT_AUTHORISED):
        return ApplyResult(
            False,
            (),
            "Nothing was changed: the machine asked for your password and did not get it.",
            refused=True,
        )
    if result.returncode == EXIT_INVALID:
        return ApplyResult(False, (), result.message or "Those settings were refused.")
    return ApplyResult(False, (), result.message or f"kidnix-config exited {result.returncode}.")


# --- their things ---------------------------------------------------------


def export_to(destination: Path | None, runner: Runner = run) -> Completed:
    """``kidnix-export [DEST]``. Polkit asks for the **parent's** password.

    The archive it writes is owned by the parent and mode 0600, and it holds
    everything: the Journal, the drawings, the voice notes. This is the "way
    out for the child's work" three of four parents arrived at on their own.
    """
    argv = [EXPORT_HELPER]
    if destination is not None:
        argv.append(str(destination))
    return runner(argv, timeout=600)


def wipe(runner: Runner = run) -> Completed:
    """``kidnix-wipe --yes``. **Only** ever called after the panel's own two
    confirmations, the second of which makes the parent type the word."""
    return runner([WIPE_HELPER, "--yes"], timeout=300)


# NOT HERE: a "what would be deleted" probe. Running kidnix-wipe to produce a
# listing means a polkit prompt in front of a parent who has pressed the FIRST
# of two confirmations, and teaching somebody to type their password at a
# dialogue headed "delete everything" is the habit not to teach. The panel's
# first confirmation says what goes, in words, from what
# /usr/libexec/kidnix-parent-tools actually removes.


def open_with_desktop(path: Path, runner: Runner = run) -> Completed:
    """``xdg-open``. Files for a folder, the image viewer (and its Print item)
    for a PNG. The panel does not embed a file manager or a print dialogue;
    GNOME has both and the parent already knows them."""
    return runner(["xdg-open", str(path)], timeout=20)


# --- the PIN --------------------------------------------------------------


def set_pin(new_pin: str, current_pin: str, runner: Runner = run) -> Completed:
    """``kidnix-set-pin --stdin``: line 1 the new PIN, line 2 the current one.

    Both on stdin, never in ``argv`` and never in the environment
    (``docs/spikes/pin-flow.md``). The exit codes are the contract: 0 written,
    3 the current PIN did not match or too many tries, 4 a PIN is set and none
    was proved, 1 refused, 64 usage.
    """
    return runner([SET_PIN_HELPER, "--stdin"], stdin=f"{new_pin}\n{current_pin}\n", timeout=60)


PIN_MESSAGES = {
    0: "",
    1: "The machine refused to change the PIN.",
    3: "That is not the current PIN. Nothing was changed.",
    4: "This machine already has a PIN. Type the current one as well.",
    64: "The panel asked for the PIN change in a way the helper did not understand.",
    126: "Nothing was changed: the machine asked for your password and did not get it.",
    127: "Nothing was changed: the machine asked for your password and did not get it.",
}


def pin_message(result: Completed) -> str:
    """One sentence for a PIN attempt. Never echoes a digit or a length."""
    if result.returncode in PIN_MESSAGES:
        return PIN_MESSAGES[result.returncode]
    return result.message or f"kidnix-set-pin exited {result.returncode}."


def pin_is_four_digits(pin: str) -> bool:
    return len(pin) == 4 and pin.isdigit() and pin.isascii()


#: The PIN every kidnix used to ship with, refused by the helper and refused
#: here so the panel can say why before the parent types it twice.
REFUSED_PIN = "1234"


# --- updates --------------------------------------------------------------


@dataclass(frozen=True)
class BootcStatus:
    """What is booted, and what would be rolled back to."""

    booted_image: str = ""
    booted_digest: str = ""
    booted_version: str = ""
    rollback_image: str = ""
    rollback_version: str = ""
    staged_image: str = ""
    available: bool = False
    raw_ok: bool = True

    @property
    def can_roll_back(self) -> bool:
        return bool(self.rollback_image)

    @property
    def short_digest(self) -> str:
        digest = self.booted_digest
        return digest.split(":", 1)[-1][:12] if digest else ""


def parse_bootc_status(text: str) -> BootcStatus:
    """``bootc status --format=json``, defensively.

    ``rollback_test.py`` already notes that this schema "is bootc's to change",
    so every field is fetched by a chain of ``.get`` and a shape this code has
    never seen produces an empty :class:`BootcStatus` with ``raw_ok`` false --
    which the tab renders as "this machine could not say", not as a crash and
    not as "you are up to date".
    """
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return BootcStatus(raw_ok=False)
    if not isinstance(data, dict):
        return BootcStatus(raw_ok=False)
    status = data.get("status") if isinstance(data.get("status"), dict) else data

    booted = _image_of(status.get("booted"))
    rollback = _image_of(status.get("rollback"))
    staged = _image_of(status.get("staged"))
    return BootcStatus(
        booted_image=booted[0],
        booted_digest=booted[1],
        booted_version=booted[2],
        rollback_image=rollback[0],
        rollback_version=rollback[2],
        staged_image=staged[0],
        available=bool(staged[0]),
        raw_ok=True,
    )


def _image_of(entry: Any) -> tuple[str, str, str]:
    """``(ref, digest, version)`` out of one deployment entry."""
    if not isinstance(entry, dict):
        return ("", "", "")
    image = entry.get("image") if isinstance(entry.get("image"), dict) else {}
    inner = image.get("image") if isinstance(image.get("image"), dict) else {}
    ref = str(inner.get("image", "")) if inner else str(image.get("image", "") or "")
    digest = str(image.get("imageDigest", "") or "")
    version = str(entry.get("version", "") or image.get("version", "") or "")
    return (ref, digest, version)


@dataclass(frozen=True)
class UpdateCheck:
    """The answer to "is there anything waiting?"."""

    available: bool
    detail: str = ""
    failed: bool = False

    @property
    def sentence(self) -> str:
        if self.failed:
            return f"The machine could not check: {self.detail}"
        if self.available:
            return f"There is an update waiting.{(' ' + self.detail) if self.detail else ''}"
        return "This machine is up to date."


def parse_upgrade_check(result: Completed) -> UpdateCheck:
    """``bootc upgrade --check``.

    bootc says "No changes in ..." when there is nothing, and prints the new
    image when there is. A non-zero exit is *not* "no update": on a machine
    whose signature policy has no key it means the pull was refused, which is
    the fail-closed behaviour and has to be reported as a failure, not as
    reassurance.
    """
    text = (result.stdout + "\n" + result.stderr).strip()
    if not result.ok:
        return UpdateCheck(False, _first_useful_line(text) or "no reason given", failed=True)
    lowered = text.lower()
    if "no changes" in lowered or "no update" in lowered:
        return UpdateCheck(False, "")
    if not text:
        return UpdateCheck(False, "")
    return UpdateCheck(True, _first_useful_line(text))


def _first_useful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def check_for_updates(runner: Runner = run) -> UpdateCheck:
    return parse_upgrade_check(
        runner(["pkexec", "/usr/sbin/bootc", "upgrade", "--check"], timeout=180)
    )


def bootc_status(runner: Runner = run) -> BootcStatus:
    result = runner(["/usr/sbin/bootc", "status", "--format=json"], timeout=60)
    if not result.ok:
        # bootc status needs root on some deployments; ask politely once.
        result = runner(["pkexec", "/usr/sbin/bootc", "status", "--format=json"], timeout=120)
    if not result.ok:
        return BootcStatus(raw_ok=False)
    return parse_bootc_status(result.stdout)


def upgrade(runner: Runner = run) -> Completed:
    """``bootc upgrade``. Staged, never applied under a running child.

    bootc writes the new deployment and it takes effect at the **next boot**,
    which is exactly the promise PARENTS.md makes: nothing reboots overnight
    and nothing changes under your child without you.
    """
    return runner(["pkexec", "/usr/sbin/bootc", "upgrade"], timeout=1800)


def rollback(runner: Runner = run) -> Completed:
    return runner(["pkexec", "/usr/sbin/bootc", "rollback"], timeout=300)


# --- would this machine accept an image at all? ---------------------------


@dataclass(frozen=True)
class VerifyResult:
    """Whether the signature policy would actually verify an update.

    The panel review reordered Tom's update ask around exactly this: "an update
    button that pulls from ghcr with no signature policy on the device is a
    worse position than being unpatched. Policy and pinned identity first,
    button second." So the button is *behind* this check, and the check's
    sentence is shown whether it passes or fails.
    """

    verified: bool
    #: The public key the policy names, and whether it is on this machine.
    key_path: str = ""
    key_present: bool = False
    scope: str = ""
    reason: str = ""

    @property
    def sentence(self) -> str:
        if self.verified:
            return (
                f"Updates are checked against {self.key_path} before anything is "
                f"installed. An image signed by anyone else is refused."
            )
        return f"Updates are NOT verifiable on this machine: {self.reason}"


def parse_signature_policy(
    policy_text: str,
    repo: str = IMAGE_REPO,
    key_exists: Callable[[str], bool] | None = None,
) -> VerifyResult:
    """Read ``policy.json`` and say, in words, whether an update would verify.

    Looks for the most precise ``docker`` scope covering ``repo`` -- the way
    containers-policy.json(5) itself resolves one -- and requires it to be
    ``sigstoreSigned`` with a ``keyPath`` that exists. A scope of
    ``insecureAcceptAnything`` is reported as unverified even though pulls
    would succeed, because "it works" and "it is checked" are different
    sentences and only one of them is what a parent is being told.
    """
    exists = key_exists if key_exists is not None else (lambda p: Path(p).is_file())
    try:
        policy = json.loads(policy_text)
    except (ValueError, TypeError):
        return VerifyResult(False, reason="the machine's signature policy could not be read.")
    transports = policy.get("transports") if isinstance(policy, dict) else None
    docker = transports.get("docker") if isinstance(transports, dict) else None
    if not isinstance(docker, dict):
        return VerifyResult(
            False, reason="the machine's signature policy names no registries at all."
        )

    scope = _most_precise_scope(docker, repo)
    if scope is None:
        return VerifyResult(
            False,
            reason=f"nothing in the signature policy covers {repo}, so an update would "
            "be pulled without being checked.",
        )
    requirements = docker.get(scope)
    if not isinstance(requirements, list) or not requirements:
        return VerifyResult(False, scope=scope, reason=f"the rule for {scope} is empty.")

    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        if requirement.get("type") != "sigstoreSigned":
            continue
        key_path = str(requirement.get("keyPath", ""))
        if not key_path:
            return VerifyResult(
                False,
                scope=scope,
                reason=f"the rule for {scope} asks for a signature but names no key.",
            )
        if not exists(key_path):
            return VerifyResult(
                False,
                key_path=key_path,
                scope=scope,
                reason=f"the signing key {key_path} is not on this machine, so every "
                "update is refused. That is the safe direction, but it does mean "
                "this machine cannot be updated until the key is installed.",
            )
        return VerifyResult(True, key_path=key_path, key_present=True, scope=scope)

    kinds = ", ".join(sorted({str(r.get("type")) for r in requirements if isinstance(r, dict)}))
    return VerifyResult(
        False,
        scope=scope,
        reason=f"{scope} is set to '{kinds}', which accepts an image without checking "
        "who signed it.",
    )


def _most_precise_scope(docker: dict[str, Any], repo: str) -> str | None:
    """containers-policy.json(5): the longest matching scope wins, and only
    that one is consulted."""
    candidates = [
        scope
        for scope in docker
        if repo == scope or repo.startswith(scope + "/") or repo.startswith(scope + ":")
    ]
    if not candidates:
        # A bare-registry scope such as "ghcr.io" still covers the repo.
        registry = repo.split("/", 1)[0]
        candidates = [scope for scope in docker if scope == registry]
    if not candidates:
        return None
    return max(candidates, key=len)


def signature_policy(policy_path: Path = POLICY_JSON, repo: str = IMAGE_REPO) -> VerifyResult:
    try:
        text = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        return VerifyResult(False, reason=f"{policy_path} could not be read ({exc.strerror}).")
    return parse_signature_policy(text, repo)


__all__ = [
    "CONFIG_HELPER",
    "EXPORT_HELPER",
    "IMAGE_REPO",
    "POLICY_JSON",
    "REFUSED_PIN",
    "SET_PIN_HELPER",
    "SIGNING_KEY",
    "WIPE_HELPER",
    "ApplyResult",
    "BootcStatus",
    "Completed",
    "Runner",
    "UpdateCheck",
    "VerifyResult",
    "apply_settings",
    "bootc_status",
    "check_for_updates",
    "export_to",
    "have",
    "open_with_desktop",
    "parse_bootc_status",
    "parse_signature_policy",
    "parse_upgrade_check",
    "pin_is_four_digits",
    "pin_message",
    "rollback",
    "run",
    "set_pin",
    "signature_policy",
    "upgrade",
    "wipe",
]
