#!/usr/bin/bash
# Install the kidnix parent panel (parent-panel/ in the repo) into the image.
#
# The same shape and the same argument as 60-shell.sh: a plain copy into the
# /usr site-packages rather than a pip install, because the package has ZERO
# runtime dependencies from PyPI (PyGObject, GTK4 and libadwaita all come from
# RPMs) and `pip install` would need python3-pip and python3-hatchling in the
# image and then removed again to produce a tree byte-for-byte identical to
# `cp -a`. Read the header of 60-shell.sh for the whole reasoning; it has not
# changed for this package.
#
# What lands where:
#
#   ${PURELIB}/kidnix_parent_panel/      the package, byte-compiled
#   /usr/bin/kidnix-parent-panel         the launcher (shipped in system_files)
#   /usr/bin/kidnix-config               the root helper (shipped, wheel-only)
#   /usr/share/polkit-1/actions/org.kidnix.parent-config.policy   (shipped)
#   /usr/share/applications/kidnix-parent-panel.desktop           (shipped)
#
# This stage runs AFTER 60-shell.sh on purpose: the panel imports
# `kidnix_shell` read-only, to validate what it is about to write against the
# reader that will read it, and the verification at the bottom of this file
# proves that import works from /usr rather than from a source tree.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

SRC=/tmp/parent-panel
[[ -d "${SRC}/kidnix_parent_panel" ]] \
    || die "${SRC}/kidnix_parent_panel is missing -- the Containerfile must COPY parent-panel/ /tmp/parent-panel/"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "${SRC}/kidnix_parent_panel/__init__.py")"
[[ -n "${VERSION}" ]] || die "could not read __version__ from ${SRC}/kidnix_parent_panel/__init__.py"

# -----------------------------------------------------------------------------
# 1. The Python package
# -----------------------------------------------------------------------------

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))')"
[[ "${PURELIB}" == /usr/lib/* ]] || die "refusing to install outside /usr: ${PURELIB}"
log "site-packages: ${PURELIB}"

# A developer checkout carries a uv venv and caches compiled by another Python.
# .containerignore drops them; this is the belt to that pair of braces.
rm -rf "${SRC}/.venv" "${SRC}/tests"
find "${SRC}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "${SRC}" -name '*.py[co]' -delete 2>/dev/null || true

install -d "${PURELIB}"
rm -rf "${PURELIB:?}/kidnix_parent_panel"
cp -a "${SRC}/kidnix_parent_panel" "${PURELIB}/kidnix_parent_panel"

DISTINFO="${PURELIB}/kidnix_parent_panel-${VERSION}.dist-info"
rm -rf "${DISTINFO}"
install -d "${DISTINFO}"
cat >"${DISTINFO}/METADATA" <<EOF
Metadata-Version: 2.1
Name: kidnix-parent-panel
Version: ${VERSION}
Summary: kidnix parent panel -- the grown-up's settings app
License: Apache-2.0
Requires-Python: >=3.11
EOF
printf 'kidnix-image-build\n' >"${DISTINFO}/INSTALLER"
printf 'kidnix_parent_panel\n' >"${DISTINFO}/top_level.txt"

# /usr is read-only at runtime, so an image without .pyc files re-parses the
# whole package on every start and can never cache the result.
python3 -m compileall -q -f --invalidation-mode unchecked-hash \
    "${PURELIB}/kidnix_parent_panel" \
    || die "byte-compiling kidnix_parent_panel failed"

# -----------------------------------------------------------------------------
# 2. Assert the whole thing actually works
# -----------------------------------------------------------------------------

log "verifying the install"

# Import from a directory that is definitely not the source tree.
( cd / && python3 -c 'import kidnix_parent_panel, sys; sys.exit(0 if kidnix_parent_panel.__file__.startswith("/usr/lib/") else 1)' ) \
    || die "kidnix_parent_panel does not import from /usr/lib"

( cd / && /usr/bin/kidnix-parent-panel --version >/dev/null ) \
    || die "/usr/bin/kidnix-parent-panel --version failed"

# The GTK side has to import, or a parent clicking the launcher gets a
# traceback on a desktop and no window. There is no display in a build
# container, so import the modules without realising anything.
( cd / && python3 -c '
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: F401
import kidnix_parent_panel.ui.app          # noqa: F401
import kidnix_parent_panel.ui.children     # noqa: F401
import kidnix_parent_panel.ui.timing       # noqa: F401
import kidnix_parent_panel.ui.activities   # noqa: F401
import kidnix_parent_panel.ui.sound        # noqa: F401
import kidnix_parent_panel.ui.things       # noqa: F401
import kidnix_parent_panel.ui.family       # noqa: F401
import kidnix_parent_panel.ui.updates      # noqa: F401
' ) || die "the parent panel cannot import GTK4/libadwaita or one of its pages"

# The stylesheet is loaded by path, not by import, so it has to have travelled.
[[ -f "${PURELIB}/kidnix_parent_panel/ui/style.css" ]] \
    || die "packaged asset missing: ${PURELIB}/kidnix_parent_panel/ui/style.css"

# THE DRIFT TRIPWIRE. The panel keeps its own copy of a handful of the shell's
# constants (colour pairs, badges, the session bounds, the speech rate) so that
# its pure layer imports nothing. A copy rots; this compares it against
# kidnix_shell and fails the build if the two have parted company. It is the
# reason 62 runs after 60.
( cd / && python3 -c '
import sys
from kidnix_parent_panel.validate import cross_check_against_shell
import kidnix_shell  # noqa: F401  -- must be importable, or the check is a no-op
drift = cross_check_against_shell()
if drift:
    sys.exit("the panel and kidnix_shell disagree: " + "; ".join(str(d) for d in drift))
' ) || die "the parent panel has drifted from kidnix_shell's schema"

# The panel's own self-check, against the machine's real files. It validates
# /etc/kidnix, loads every activity manifest, renders what it would write and
# parses that back through the shell's own readers.
( cd / && /usr/bin/kidnix-parent-panel --self-check ) \
    || die "kidnix-parent-panel --self-check failed on the built image"

# What the panel would write must be what the shell reads. --dump prints both
# files; parse them the way the shell does, from a scratch copy, so this never
# touches /etc.
( cd / && python3 - <<'PY' ) || die "what the panel would write does not parse"
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

dumped = subprocess.run(
    ["/usr/bin/kidnix-parent-panel", "--dump"], capture_output=True, text=True, check=True
).stdout
files = {}
current = None
for line in dumped.splitlines():
    if line.startswith("# ===== ") and line.endswith(" ====="):
        current = Path(line.strip("# =")).name
        files[current] = []
    elif current:
        files[current].append(line)
if set(files) != {"parent.toml", "session.toml"}:
    sys.exit(f"--dump produced {sorted(files)}")

with tempfile.TemporaryDirectory() as scratch:
    folder = Path(scratch)
    for name, lines in files.items():
        (folder / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        tomllib.loads((folder / name).read_text(encoding="utf-8"))
    from kidnix_shell.session import load_policy
    from kidnix_shell.settings import ParentConfig

    config = ParentConfig.load(folder / "parent.toml")
    policy = load_policy(folder / "session.toml")
    assert config.profiles, "the panel would write a parent.toml with no children"
    assert policy.length > 0, "the panel would write a session.toml with no length"
    # The shipped machine has no PIN and the panel must not invent one: a file
    # with a hash in it is a file that says a grown-up chose a PIN.
    raw = tomllib.loads((folder / "parent.toml").read_text(encoding="utf-8"))
    assert not raw.get("pin_hash"), "the panel would write a PIN into a machine that has none"
print("  -- the panel's output loads through kidnix_shell")
PY

# -----------------------------------------------------------------------------
# 3. The helper, its action, and the launcher
# -----------------------------------------------------------------------------

for path in /usr/bin/kidnix-parent-panel /usr/bin/kidnix-config; do
    [[ -x "${path}" ]] || die "${path} is missing or not executable"
    bash -n "${path}" || die "${path} is not valid bash"
done

POLICY=/usr/share/polkit-1/actions/org.kidnix.parent-config.policy
[[ -f "${POLICY}" ]] || die "${POLICY} is missing"
python3 - "${POLICY}" <<'PY' || die "the parent-config polkit action is not what it should be"
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
actions = root.findall("action")
if len(actions) != 1 or actions[0].get("id") != "org.kidnix.parent-config":
    sys.exit("expected exactly one action, org.kidnix.parent-config")
action = actions[0]
defaults = action.find("defaults")
wanted = {"allow_any": "no", "allow_inactive": "no", "allow_active": "auth_admin_keep"}
for key, value in wanted.items():
    got = defaults.findtext(key)
    if got != value:
        sys.exit(f"{key} is {got!r}, expected {value!r}")
paths = [
    a.text
    for a in action.findall("annotate")
    if a.get("key") == "org.freedesktop.policykit.exec.path"
]
if paths != ["/usr/bin/kidnix-config"]:
    sys.exit(f"exec.path is {paths}, expected /usr/bin/kidnix-config")
PY

# THE ONE THING THAT MUST NEVER BE TRUE: the child's account may not authorise
# this action. 40-kidnix-kid.rules denies the whole "org.kidnix." prefix and
# carves out exactly ONE id; parent-config must not be in that carve-out.
RULES=/usr/share/polkit-1/rules.d/40-kidnix-kid.rules
[[ -f "${RULES}" ]] || die "${RULES} is missing"
grep -q '"org.kidnix."' "${RULES}" || die "${RULES} no longer denies the org.kidnix. prefix"
if grep -q 'org.kidnix.parent-config' "${RULES}"; then
    die "40-kidnix-kid.rules names org.kidnix.parent-config -- the child must never be able to change the session policy"
fi

DESKTOP=/usr/share/applications/kidnix-parent-panel.desktop
[[ -f "${DESKTOP}" ]] || die "${DESKTOP} is missing"
grep -q '^Terminal=false$' "${DESKTOP}" || die "${DESKTOP} still opens a terminal (it was a placeholder once)"
grep -q '^Exec=/usr/bin/kidnix-parent-panel$' "${DESKTOP}" || die "${DESKTOP} does not launch the panel"
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "${DESKTOP}" || die "${DESKTOP} is not a valid desktop entry"
fi

# kidnix-config's own probe: the module is importable and answers `show`
# without any privilege at all.
( cd / && /usr/bin/kidnix-config show >/dev/null ) || die "kidnix-config show failed"

rm -rf "${SRC}"

log "kidnix-parent-panel ${VERSION} installed into ${PURELIB}"
