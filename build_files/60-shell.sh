#!/usr/bin/bash
# Install the real kidnix activity shell (shell/ in the repo) into the image
# and wire the session units that run it.
#
# WHY A PLAIN COPY AND NOT pip:
# `kidnix-shell` is pure Python with **zero** runtime dependencies from PyPI
# (shell/pyproject.toml: PyGObject, GTK4, libadwaita and speechd all come from
# RPMs). Its build backend is hatchling, so `pip install` would need
# python3-pip *and* python3-hatchling installed into the image and then removed
# again -- two extra packages, a dnf remove that can cascade, and a build that
# reaches the network -- to produce a tree that is byte-for-byte the same as
# `cp -a kidnix_shell $purelib/`. The copy is the least fragile option, and
# every claim it makes is asserted at the bottom of this file.
#
# The one thing pip would give us for free is .dist-info metadata, so we write
# the two files of it that anything actually reads.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

SRC=/tmp/shell
[[ -d "${SRC}/kidnix_shell" ]] || die "${SRC}/kidnix_shell is missing -- the Containerfile must COPY shell/ /tmp/shell/"
[[ -d "${SRC}/kidnix_activity" ]] || die "${SRC}/kidnix_activity is missing -- the activity SDK ships with the shell"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "${SRC}/kidnix_shell/__init__.py")"
[[ -n "${VERSION}" ]] || die "could not read __version__ from ${SRC}/kidnix_shell/__init__.py"

# -----------------------------------------------------------------------------
# 1. The Python package
# -----------------------------------------------------------------------------

# sysconfig's default purelib is /usr/local/..., which on an ostree system is a
# symlink into /var and therefore NOT part of the image. Ask for the /usr
# scheme explicitly.
PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))')"
[[ "${PURELIB}" == /usr/lib/* ]] || die "refusing to install outside /usr: ${PURELIB}"
log "site-packages: ${PURELIB}"

# A developer checkout can carry __pycache__ compiled by a different Python.
# Those would be *imported* by the image's Python 3.14 if their magic happened
# to match, so they never get to travel. (.containerignore drops them too; this
# is the belt to that pair of braces.)
find "${SRC}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "${SRC}" -name '*.py[co]' -delete 2>/dev/null || true

install -d "${PURELIB}"
rm -rf "${PURELIB:?}/kidnix_shell"
cp -a "${SRC}/kidnix_shell" "${PURELIB}/kidnix_shell"

# The activity SDK (docs/design/activity-sdk.md). It lives in the same uv
# project as the shell and ships with it for one reason: a first-party activity
# is a separate *program* but not a separate *release*, and an SDK that lagged
# the shell it borrows Metrics, Journal and SpeechManager from would break
# every activity on the machine the first time one of those changed.
rm -rf "${PURELIB:?}/kidnix_activity"
cp -a "${SRC}/kidnix_activity" "${PURELIB}/kidnix_activity"

# The metadata a wheel install would have left behind. METADATA is what
# importlib.metadata.version("kidnix-shell") reads; INSTALLER is what tells a
# future maintainer that rpm/dnf does not own these files.
DISTINFO="${PURELIB}/kidnix_shell-${VERSION}.dist-info"
rm -rf "${DISTINFO}"
install -d "${DISTINFO}"
cat >"${DISTINFO}/METADATA" <<EOF
Metadata-Version: 2.1
Name: kidnix-shell
Version: ${VERSION}
Summary: kidnix activity shell -- the full-screen surface a child sees
License: Apache-2.0
Requires-Python: >=3.11
EOF
printf 'kidnix-image-build\n' >"${DISTINFO}/INSTALLER"
printf 'kidnix_shell\nkidnix_activity\n' >"${DISTINFO}/top_level.txt"

# /usr is read-only at runtime, so an image without .pyc files re-parses the
# whole shell on every start and can never cache the result. `unchecked-hash`
# invalidation keeps the .pyc valid regardless of mtimes, which is what an
# ostree commit needs.
python3 -m compileall -q -f --invalidation-mode unchecked-hash \
    "${PURELIB}/kidnix_shell" "${PURELIB}/kidnix_activity" \
    || die "byte-compiling kidnix_shell failed"

# -----------------------------------------------------------------------------
# 1b. The translation catalogues (ADR-0012, docs/design/i18n.md)
# -----------------------------------------------------------------------------
#
# One gettext domain, `kidnix`, shared by the shell and the activity SDK
# (they are one release, see above). The msgids are the en_GB strings, so a
# machine with no catalogue at all is exactly the machine it was -- which is
# also why a missing `.mo` is not a fatal error further down, and a missing
# `msgfmt` is.
#
# WHY COMPILE HERE rather than committing the `.mo`: a `.mo` is a compiled
# artefact of the `.po` beside it, and a repository that carries both has two
# sources of truth and no way to tell when they disagree. `gettext` is already
# in the image (it arrives with the KDE activity stack), so this costs one
# process per language and nothing on disk.

command -v msgfmt >/dev/null || die "msgfmt is missing (rpm: gettext) -- cannot build the kidnix translation catalogues"

LOCALE_DIR=/usr/share/locale
shopt -s nullglob
po_files=("${SRC}"/po/*.po)
shopt -u nullglob

if (( ${#po_files[@]} == 0 )); then
    log "no translation catalogues in ${SRC}/po (the image will be en_GB only)"
else
    for po in "${po_files[@]}"; do
        lang="$(basename "${po}" .po)"
        install -d "${LOCALE_DIR}/${lang}/LC_MESSAGES"
        msgfmt --check --output-file="${LOCALE_DIR}/${lang}/LC_MESSAGES/kidnix.mo" "${po}" \
            || die "msgfmt rejected ${po}"
        log "language ${lang}: $(msgfmt --statistics --output-file=/dev/null "${po}" 2>&1)"
    done
    # And the shell has to be able to *find* what we just wrote, in the
    # directory it actually looks in -- a .mo one level up from where
    # `gettext.translation()` searches is a file nobody ever reads.
    for po in "${po_files[@]}"; do
        lang="$(basename "${po}" .po)"
        [[ -f "${LOCALE_DIR}/${lang}/LC_MESSAGES/kidnix.mo" ]] \
            || die "kidnix.mo for ${lang} is not where kidnix_shell.i18n looks"
    done
    # And the shell has to be able to *load* them: a .mo the build wrote and
    # `gettext.translation()` cannot open is the failure this whole stage
    # exists to prevent, and it is invisible from the filesystem.
    languages=()
    for po in "${po_files[@]}"; do languages+=("$(basename "${po}" .po)"); done
    ( cd / && python3 -c '
import sys

from kidnix_shell import i18n

# The sample catalogues are deliberately partial (docs/design/i18n.md
# section 5), so what is asserted is that the machinery finds one -- not that
# any particular sentence is translated.
for language in sys.argv[1:]:
    i18n.install(language, localedirs=[i18n.SYSTEM_LOCALE_DIR])
    if not i18n.has_catalogue():
        sys.exit("no loadable catalogue for " + language)
# And that en_GB is still the source: no catalogue, msgids straight through.
i18n.install("en_GB", localedirs=[i18n.SYSTEM_LOCALE_DIR])
if i18n.gettext("Nothing to undo.") != "Nothing to undo.":
    sys.exit("en_GB is no longer the source language")
' "${languages[@]}" ) || die "the shell cannot load the catalogues this stage just wrote"
fi

# The one that actually matters, and it is a *negative*: en_GB has no
# catalogue and must not acquire one, because en_GB is the source. A
# /usr/share/locale/en_GB/LC_MESSAGES/kidnix.mo would mean somebody had
# translated English into English and every string now has two spellings.
[[ ! -e "${LOCALE_DIR}/en_GB/LC_MESSAGES/kidnix.mo" ]] \
    || die "en_GB is the source language and must not have a kidnix catalogue"

# -----------------------------------------------------------------------------
# 2. The entry point
# -----------------------------------------------------------------------------

# shell/pyproject.toml declares `kidnix-shell = "kidnix_shell.cli:main"`, but
# /usr/bin/kidnix-shell is already taken by the *session wrapper* GDM execs
# (system_files/usr/bin/kidnix-shell -> gnome-session --session=kidnix), so the
# application itself gets an unambiguous name. kidnix-shell.service runs this.
cat >/usr/bin/kidnix-shell-app <<'EOF'
#!/usr/bin/python3
# The `kidnix-shell` console script from shell/pyproject.toml, installed under
# a name that does not collide with the session wrapper in /usr/bin/kidnix-shell.
# Generated by build_files/60-shell.sh -- do not edit in the image.
import sys

from kidnix_shell.cli import main

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 0755 /usr/bin/kidnix-shell-app

# The SDK's own console script (shell/pyproject.toml: `kidnix-activity =
# "kidnix_activity.cli:main"`). It scaffolds a new activity and validates a
# manifest; there is no name collision, so it keeps its own.
cat >/usr/bin/kidnix-activity <<'EOF'
#!/usr/bin/python3
# The `kidnix-activity` console script from shell/pyproject.toml.
# Generated by build_files/60-shell.sh -- do not edit in the image.
import sys

from kidnix_activity.cli import main

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 0755 /usr/bin/kidnix-activity

# -----------------------------------------------------------------------------
# 3. Assert the whole thing actually works
# -----------------------------------------------------------------------------

log "verifying the install"

# Import from a directory that is definitely not the source tree, so a stray
# CWD cannot make this pass by accident.
( cd / && python3 -c 'import kidnix_shell, sys; sys.exit(0 if kidnix_shell.__file__.startswith("/usr/lib/") else 1)' ) \
    || die "kidnix_shell does not import from /usr/lib"

( cd / && python3 -m kidnix_shell --version >/dev/null ) || die "python3 -m kidnix_shell --version failed"

# The activity SDK, the same way: it imports from /usr/lib and its command runs.
( cd / && python3 -c 'import kidnix_activity, sys; sys.exit(0 if kidnix_activity.__file__.startswith("/usr/lib/") else 1)' ) \
    || die "kidnix_activity does not import from /usr/lib"
( cd / && /usr/bin/kidnix-activity --version >/dev/null ) || die "/usr/bin/kidnix-activity --version failed"

# The SDK's example activity has to validate against the SDK's own rules -- no
# network, no quit dialogue, a goal, an audio label and a picture. It is the
# one manifest in the tree that exercises them, and a build that shipped an SDK
# whose validator rejected its own example would be shipping a broken contract.
( cd / && /usr/bin/kidnix-activity validate \
    "${PURELIB}/kidnix_activity/examples/hello_draw/hello-draw.toml" >/dev/null ) \
    || die "the activity SDK's example manifest does not validate"
( cd / && /usr/bin/kidnix-shell-app --version >/dev/null ) || die "/usr/bin/kidnix-shell-app --version failed"

# The GTK side has to import too, or the session comes up to a black screen and
# a traceback in the journal that nobody sees until a child is sitting there.
# There is no display in a build container, so import the module without
# realising a window.
( cd / && python3 -c '
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: F401
import kidnix_shell.app  # noqa: F401
' ) || die "the shell cannot import GTK4/libadwaita (python3-gobject, gtk4, libadwaita)"

# Read-aloud. python3-speechd is the preferred backend; spd-say is the fallback
# (spec section 3). Missing both is a degraded-but-shippable state for a dev
# host and an unacceptable one for the image, so require the good path here.
( cd / && python3 -c 'import speechd' ) || die "python3-speechd is missing (read-aloud backend)"
command -v spd-say >/dev/null || die "spd-say is missing (read-aloud fallback)"

# Every manifest we ship must load, or Home comes up empty for a child.
( cd / && /usr/bin/kidnix-shell-app --validate-manifests /usr/share/kidnix/activities ) \
    || die "shipped activity manifests do not validate"

# ...including the shelf children, which live in a SUBdirectory (so they cannot
# leak onto Home) and are therefore not covered by the scan above. They are
# generated by 55-gcompris.sh from curated.toml, and a generator that emitted
# something the shell cannot parse would otherwise be discovered by a child
# tapping "Letters & numbers" and getting an empty screen.
for shelf_dir in /usr/share/kidnix/activities/*/; do
    [[ -d "${shelf_dir}" ]] || continue
    log "validating shelf children in ${shelf_dir}"
    ( cd / && /usr/bin/kidnix-shell-app --validate-manifests "${shelf_dir}" ) \
        || die "shelf child manifests in ${shelf_dir} do not validate"
done

# The theme and the bundled fallback icons have to have travelled with the
# package; they are loaded by path, not by import.
for asset in "${PURELIB}/kidnix_shell/theme.css" \
             "${PURELIB}/kidnix_activity/activity.css" \
             "${PURELIB}/kidnix_shell/data/icons/kidnix-make.svg"; do
    [[ -f "${asset}" ]] || die "packaged asset missing: ${asset}"
done

# -----------------------------------------------------------------------------
# 4. Session wiring
# -----------------------------------------------------------------------------
#
# The units and the .session file are shipped in system_files/; all that is
# left is to prove they are consistent with each other, because every one of
# these mistakes produces the same symptom (GDM bounces the child back to a
# greeter) and none of them is visible until boot.

SESSION_FILE=/usr/share/gnome-session/sessions/kidnix.session
DROPIN=/usr/lib/systemd/user/gnome-session@kidnix.target.d/session.conf
UNIT=/usr/lib/systemd/user/kidnix-shell.service

[[ -f "${SESSION_FILE}" ]] || die "${SESSION_FILE} is missing"
[[ -f "${DROPIN}" ]]       || die "${DROPIN} is missing"
[[ -f "${UNIT}" ]]         || die "${UNIT} is missing"

# gnome-session --session=kidnix resolves to gnome-session@kidnix.target, so
# the .session basename and the drop-in directory name must agree.
grep -q '^Name=kidnix$' "${SESSION_FILE}" || die "${SESSION_FILE} has no Name=kidnix"
grep -q '^exec /usr/bin/gnome-session --session=kidnix$' /usr/bin/kidnix-shell \
    || die "/usr/bin/kidnix-shell does not exec gnome-session --session=kidnix"

grep -q '^Requires=org.gnome.Kiosk.target$' "${DROPIN}" || die "${DROPIN} does not require the kiosk compositor"
grep -q '^Wants=kidnix-shell.service$'      "${DROPIN}" || die "${DROPIN} does not pull in kidnix-shell.service"
grep -q '^Restart=always$'                  "${UNIT}"   || die "${UNIT} is not Restart=always"
grep -q '^ExecStart=/usr/bin/kidnix-shell-app$' "${UNIT}" || die "${UNIT} does not start the shell"
# Without this the autospawned speech-dispatcher joins the shell's cgroup and
# ignores SIGTERM, turning every restart into an 11 s stall. Measured; see
# docs/spikes/session-integration.md.
grep -q '^Wants=speech-dispatcher.socket$' "${UNIT}" || die "${UNIT} does not socket-activate speech-dispatcher"
[[ -f /usr/lib/systemd/user/speech-dispatcher.socket ]] || die "speech-dispatcher ships no user socket unit"
grep -q 'ListenStream=%t/speech-dispatcher/speechd.sock' /usr/lib/systemd/user/speech-dispatcher.socket \
    || die "speech-dispatcher.socket no longer listens where python3-speechd looks"

# The units gnome-kiosk and gnome-session contribute must exist, or the target
# above resolves to nothing at all.
for unit in /usr/lib/systemd/user/org.gnome.Kiosk.target \
            /usr/lib/systemd/user/org.gnome.Kiosk@wayland.service \
            /usr/lib/systemd/user/gnome-session@.target \
            /usr/lib/systemd/user/gnome-session-initialized.target; do
    [[ -f "${unit}" ]] || die "expected unit missing from the image: ${unit}"
done

# systemd's own opinion of the unit files, which catches a typo'd directive
# that grep cannot. `verify` also resolves dependencies, and in a build
# container the units it chases (gnome-session.target and friends) are present
# but their own dependencies are not, so only complaints about OUR file are
# treated as fatal.
if command -v systemd-analyze >/dev/null 2>&1; then
    # `--user verify` needs somewhere to pretend a runtime directory is; without
    # XDG_RUNTIME_DIR it bails with "Failed to initialize manager" and verifies
    # nothing at all, silently.
    mkdir -p /tmp/kidnix-verify-runtime
    verify_out="$(XDG_RUNTIME_DIR=/tmp/kidnix-verify-runtime \
        systemd-analyze --user verify --recursive-errors=no "${UNIT}" 2>&1 || true)"
    rmdir /tmp/kidnix-verify-runtime 2>/dev/null || true
    if grep -q 'kidnix-shell.service' <<<"${verify_out}"; then
        printf '%s\n' "${verify_out}" >&2
        die "systemd-analyze rejected ${UNIT}"
    fi
    [[ -z "${verify_out}" ]] || log "systemd-analyze notes (not about our unit): ${verify_out//$'\n'/ | }"
fi

# The session policy the shell reads at start.
[[ -f /etc/kidnix/session.toml ]] || die "/etc/kidnix/session.toml is missing"
( cd / && python3 -c '
import sys, tomllib
with open("/etc/kidnix/session.toml", "rb") as fh:
    data = tomllib.load(fh)
required = {"length_minutes", "daily_budget_minutes", "ending_offer_minutes",
            "put_away_minutes", "bedtime_start", "bedtime_end"}
missing = required - set(data)
if missing:
    sys.exit("session.toml is missing keys: " + ", ".join(sorted(missing)))
' ) || die "/etc/kidnix/session.toml is not valid"

# The activity manifest directory the shell looks in
# (kidnix_shell.activities.SYSTEM_ACTIVITY_DIR).
[[ -d /usr/share/kidnix/activities ]] || die "/usr/share/kidnix/activities is missing"

rm -rf "${SRC}"

log "kidnix-shell ${VERSION} installed into ${PURELIB}"
