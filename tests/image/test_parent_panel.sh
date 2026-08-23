#!/usr/bin/bash
# Static assertions about the kidnix parent panel and its root helper.
#
#   just test-image parent_panel
#   podman run --rm -v ./tests/image:/tests:ro,z --entrypoint /bin/bash \
#       localhost/kidnix:latest /tests/test_parent_panel.sh
#
# Same shape and helpers as test_parent.sh: runs INSIDE the built container,
# rootless, a couple of seconds.
#
# What it proves: the panel is installed as a Python package under /usr and
# imports from there; its launcher and desktop entry are real and no longer a
# placeholder; the root helper exists, is wheel-only by polkit, and the CHILD
# is still refused it; the panel's copy of the shell's schema has not drifted;
# and what the panel would write parses back through the shell's own readers.
#
# What it cannot prove: that pkexec actually prompts, that polkitd loads the
# rules file, or that a parent's password works -- all three need a live D-Bus
# and a seat, i.e. a booted machine.
set -uo pipefail

pass=0
fail=0

_report() {
    local status="$1" name="$2" detail="${3:-}"
    if [[ "${status}" == ok ]]; then
        printf '  \033[32mPASS\033[0m  %s\n' "${name}"
        pass=$(( pass + 1 ))
    else
        printf '  \033[31mFAIL\033[0m  %s%s\n' "${name}" "${detail:+ -- ${detail}}"
        fail=$(( fail + 1 ))
    fi
}

assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

assert_exec() {
    if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi
}

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_no_grep <regex> <file> <description>
assert_no_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report no "$3" "unexpected match for /$1/ in $2"
    else
        _report ok "$3"
    fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then _report ok "${desc}"; else _report no "${desc}" "$* failed"; fi
}

# assert_out <description> <expected-substring> <command...>
assert_out() {
    local desc="$1" want="$2"; shift 2
    local got
    got="$("$@" 2>&1)"
    if [[ "${got}" == *"${want}"* ]]; then
        _report ok "${desc}"
    else
        _report no "${desc}" "expected '${want}' in output"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))')"

# -----------------------------------------------------------------------------

section "the panel is installed as a Python package under /usr"
assert_file "${PURELIB}/kidnix_parent_panel/__init__.py"
assert_file "${PURELIB}/kidnix_parent_panel/ui/style.css"
assert_cmd "kidnix_parent_panel imports from /usr/lib" \
    python3 -c 'import kidnix_parent_panel, sys; sys.exit(0 if kidnix_parent_panel.__file__.startswith("/usr/lib/") else 1)'
# The .pyc files matter: /usr is read-only at runtime, so without them the
# whole package is re-parsed on every launch and the result can never be cached.
if [[ -n "$(find "${PURELIB}/kidnix_parent_panel" -name '*.pyc' -print -quit 2>/dev/null)" ]]; then
    _report ok "the package is byte-compiled"
else
    _report no "the package is byte-compiled" "no .pyc under ${PURELIB}/kidnix_parent_panel"
fi
# Tests must not travel into an OS image.
if [[ ! -d "${PURELIB}/kidnix_parent_panel/tests" ]]; then
    _report ok "the panel's own tests did not travel into the image"
else
    _report no "the panel's own tests did not travel into the image"
fi

section "the launcher, and that it is no longer a placeholder"
assert_exec /usr/bin/kidnix-parent-panel
assert_cmd "the launcher is valid bash" bash -n /usr/bin/kidnix-parent-panel
assert_no_grep 'Not built yet' /usr/bin/kidnix-parent-panel \
    "the launcher no longer says 'not built yet'"
assert_out "kidnix-parent-panel --version answers" "kidnix-parent-panel" \
    /usr/bin/kidnix-parent-panel --version
assert_file /usr/share/applications/kidnix-parent-panel.desktop
assert_grep '^Exec=/usr/bin/kidnix-parent-panel$' \
    /usr/share/applications/kidnix-parent-panel.desktop "the launcher execs the panel"
assert_grep '^Terminal=false$' /usr/share/applications/kidnix-parent-panel.desktop \
    "the launcher opens a window, not a terminal"
if command -v desktop-file-validate >/dev/null 2>&1; then
    assert_cmd "the launcher is a valid desktop entry" \
        desktop-file-validate /usr/share/applications/kidnix-parent-panel.desktop
fi
# The panel must never inherit the child's dconf profile (test_parent.sh checks
# the same thing; it is cheap and it is the sort of line that gets pasted in).
assert_no_grep 'DCONF_PROFILE' /usr/bin/kidnix-parent-panel \
    "the panel does not inherit the child's dconf profile"

section "the panel can actually build a window"
# No display in a container, so import the GTK modules without realising one.
assert_cmd "every page imports against GTK4 and libadwaita" python3 -c '
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
'

section "the root helper"
assert_exec /usr/bin/kidnix-config
assert_cmd "kidnix-config is valid bash" bash -n /usr/bin/kidnix-config
# `show` is deliberately unprivileged: "what is set?" is not a secret and both
# files are 0644.
assert_out "kidnix-config show works with no privilege at all" '"schema": 1' \
    /usr/bin/kidnix-config show
assert_cmd "kidnix-config show emits valid JSON" \
    bash -c '/usr/bin/kidnix-config show | python3 -c "import json,sys; json.load(sys.stdin)"'
# An unknown command must not reach the root half.
if /usr/bin/kidnix-config wipe-everything >/dev/null 2>&1; then
    _report no "kidnix-config refuses a command it does not know"
else
    _report ok "kidnix-config refuses a command it does not know"
fi

section "the polkit action, and that the child is still refused it"
POLICY=/usr/share/polkit-1/actions/org.kidnix.parent-config.policy
assert_file "${POLICY}"
assert_cmd "the action file is well-formed XML" \
    python3 -c 'import sys,xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' "${POLICY}"
assert_cmd "it registers exactly org.kidnix.parent-config, wheel-only, on kidnix-config" \
    python3 - "${POLICY}" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
actions = root.findall("action")
assert len(actions) == 1, actions
action = actions[0]
assert action.get("id") == "org.kidnix.parent-config", action.get("id")
defaults = action.find("defaults")
assert defaults.findtext("allow_any") == "no"
assert defaults.findtext("allow_inactive") == "no"
assert defaults.findtext("allow_active") == "auth_admin_keep"
paths = [
    a.text for a in action.findall("annotate")
    if a.get("key") == "org.freedesktop.policykit.exec.path"
]
assert paths == ["/usr/bin/kidnix-config"], paths
PY

RULES=/usr/share/polkit-1/rules.d/40-kidnix-kid.rules
assert_file "${RULES}"
assert_grep '"org\.kidnix\."' "${RULES}" "the child is denied the whole org.kidnix. prefix"
# THE LINE THAT MUST NEVER APPEAR. The rules file carves exactly one id out of
# that prefix (org.kidnix.set-pin, so a fresh machine's first PIN can be set
# from the only session it shows). Adding this one would let a five-year-old
# lengthen their own session and empty their own bedtime.
assert_no_grep 'org\.kidnix\.parent-config' "${RULES}" \
    "the child's account is NOT granted org.kidnix.parent-config"
# The dry-run checker agrees, where it ships.
if [[ -x /usr/bin/kidnix-polkit-check ]]; then
    if /usr/bin/kidnix-polkit-check kid org.kidnix.parent-config 2>&1 | grep -qi 'deny\|no'; then
        _report ok "kidnix-polkit-check says kid is denied org.kidnix.parent-config"
    else
        _report no "kidnix-polkit-check says kid is denied org.kidnix.parent-config"
    fi
fi

section "the panel agrees with the shell it writes for"
assert_cmd "the panel's copy of the shell's schema has not drifted" python3 -c '
import sys
import kidnix_shell  # noqa: F401
from kidnix_parent_panel.validate import cross_check_against_shell
drift = cross_check_against_shell()
sys.exit("; ".join(str(d) for d in drift) if drift else 0)
'
assert_cmd "kidnix-parent-panel --self-check passes on this image" \
    /usr/bin/kidnix-parent-panel --self-check
assert_cmd "what the panel would write parses through kidnix_shell" python3 - <<'PY'
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from kidnix_shell.session import load_policy
from kidnix_shell.settings import ParentConfig

dumped = subprocess.run(
    ["/usr/bin/kidnix-parent-panel", "--dump"], capture_output=True, text=True, check=True
).stdout
files, current = {}, None
for line in dumped.splitlines():
    if line.startswith("# ===== ") and line.endswith(" ====="):
        current = Path(line.strip("# =")).name
        files[current] = []
    elif current:
        files[current].append(line)
assert set(files) == {"parent.toml", "session.toml"}, sorted(files)

with tempfile.TemporaryDirectory() as scratch:
    folder = Path(scratch)
    for name, lines in files.items():
        (folder / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    config = ParentConfig.load(folder / "parent.toml")
    policy = load_policy(folder / "session.toml")
    assert config.profiles, "no children"
    assert policy.length > 0, "no sitting length"
    raw = tomllib.loads((folder / "parent.toml").read_text(encoding="utf-8"))
    assert not raw.get("pin_hash"), "the panel would invent a PIN"
sys.exit(0)
PY

section "the config the panel reads is where it expects it"
assert_file /etc/kidnix/parent.toml
assert_file /etc/kidnix/session.toml
assert_file /etc/kidnix/tts.env
assert_cmd "the panel loads this machine's real settings" python3 -c '
from kidnix_parent_panel.config_io import load_model
from kidnix_parent_panel.validate import fatal, validate
import sys
problems = fatal(validate(load_model()))
sys.exit("; ".join(str(p) for p in problems) if problems else 0)
'
assert_cmd "the panel lists this machine's activities" python3 -c '
import sys
from kidnix_parent_panel import catalogue
found = catalogue.load()
sys.exit(0 if len(found.entries) >= 5 and not found.broken else 1)
'
# The helpers the Their-things tab drives.
for helper in /usr/bin/kidnix-export /usr/bin/kidnix-wipe /usr/bin/kidnix-set-pin; do
    assert_exec "${helper}"
done

section "no surveillance surface"
# SYNTHESIS G1: the parent's controls set the shape of the sandbox and get out
# of the way, and review section 5 lists "a parent surveillance dashboard"
# among the things nobody asked for. The tripwire is the absence of the THING,
# not of the word -- the panel says "no analytics" in its own honest page, so
# grepping for the word would fail on the sentence that makes the promise.
#
# A time-on-device chart would have to read the child's own counters. Nothing
# in the panel may name them.
if grep -rqE 'usage\.toml|progress\.toml|sessions_completed|journal_root' \
        "${PURELIB}/kidnix_parent_panel" 2>/dev/null; then
    _report no "the panel never reads the child's usage or progress counters" \
        "one of those names appears in the source"
else
    _report ok "the panel never reads the child's usage or progress counters"
fi
# ...nor draw one.
if grep -rqE '\b(matplotlib|pyplot|Chart|Histogram|plot_)\b' \
        "${PURELIB}/kidnix_parent_panel" 2>/dev/null; then
    _report no "the panel draws no charts" "a plotting name appears in the source"
else
    _report ok "the panel draws no charts"
fi
# Nothing in the panel may reach the network. Every remote thing it does is a
# subprocess (bootc), which is where the signature policy applies.
if grep -rqE '\b(urllib|requests|http\.client|socket\.socket|aiohttp|ssl)\b' \
        "${PURELIB}/kidnix_parent_panel" 2>/dev/null; then
    _report no "the panel opens no network connections" "a networking module is named"
else
    _report ok "the panel opens no network connections"
fi
# The one promise the honest page makes that the panel could break by itself.
assert_cmd "the honest page still carries all seven claims" python3 -c '
import sys
from kidnix_parent_panel.ui.updates import WHAT_IT_SENDS
sys.exit(0 if len(WHAT_IT_SENDS) >= 7 else 1)
'

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
