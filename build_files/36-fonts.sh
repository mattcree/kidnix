#!/usr/bin/bash
# Typefaces for pre-readers and low-vision readers.
#
# Non-negotiable #4 is "pre-reader first". The default UI face on Fedora is
# Adwaita Sans/Cantarell, whose lowercase `a` is double-storey and whose `l`,
# `I` and `1` are near-identical -- exactly the confusions a five-year-old who
# is still mapping letterforms to sounds does not need.
#
#   * SIL Andika (OFL-1.1) is designed *for literacy and beginning readers*:
#     single-storey `a`, tailed `l`, distinct `I`/`l`/`1`, generous counters.
#     This is the face the child-facing shell should use.
#   * Atkinson Hyperlegible Next (OFL-1.1), from the Braille Institute, is
#     engineered for low vision by maximising letterform distinctiveness. It is
#     the fallback for any child (or parent) who needs more separation than
#     Andika gives, and the Mono cut is the one to use anywhere a child sees
#     code (Scratch-alikes, later milestones).
#
# Both are packaged in Fedora 44, so there is no build-time download, no
# checksum to babysit and no vendored binary in git -- see docs/LICENSES.md.
# If a future Fedora drops them, the fallback is a checksummed fetch from
# https://software.sil.org/andika/download/ and
# https://github.com/googlefonts/atkinson-hyperlegible; both are OFL-1.1 and
# freely redistributable inside an OS image.
#
# This stage does NOT set a default font. Which face the child's shell renders
# in belongs to the shell (shell/, ADR-0004) and to the kid dconf profile
# (40-lockdown.sh); this stage only guarantees the faces are on disk and that
# fontconfig can find them by name.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

size_before="$(rpm -qa --qf '%{SIZE}\n' | awk '{ s += $1 } END { print s + 0 }')"

PACKAGES=(
    # Andika 6.101. NOT sil-andika-compact-fonts (a tighter-spaced cut aimed at
    # print) and NOT sil-andika-new-basic-fonts (superseded by Andika 6).
    sil-andika-fonts

    # "Next" is the second-generation family; Fedora 44 no longer packages the
    # original atkinson-hyperlegible-fonts under that name.
    atkinson-hyperlegible-next-fonts
    atkinson-hyperlegible-mono-fonts
)

dnf5 -y install "${PACKAGES[@]}"

command -v fc-cache >/dev/null 2>&1 || die "fontconfig is missing; fc-cache cannot run"
command -v fc-list  >/dev/null 2>&1 || die "fontconfig is missing; fc-list cannot run"

# Build the system font cache *in the image*. Without this, fontconfig
# rebuilds per-user into ~/.cache/fontconfig on first launch of the first GTK
# app -- a visible stall on a slow laptop, repeated for every account, and one
# more thing that can fail on a read-only-ish home.
log "building the system font cache"
fc-cache --force --system-only

# fc-cache writes to /usr/lib/fontconfig/cache on Fedora, which is image-owned
# and therefore survives into the deployment. If a future fontconfig moves it
# under /var, the cache silently evaporates at install time (bootc treats /var
# as machine-local) and we would never notice -- so check.
test -d /usr/lib/fontconfig/cache || die "fontconfig did not write a cache under /usr; it would not survive into a bootc deployment"
cache_files="$(find /usr/lib/fontconfig/cache -type f | wc -l)"
(( cache_files > 0 )) || die "/usr/lib/fontconfig/cache is empty"
log "font cache: ${cache_files} files under /usr/lib/fontconfig/cache"

# Prove fontconfig can actually resolve each family by name. `rpm -q` only
# proves files landed; a font with a broken name table is invisible to every
# toolkit, which is a much more annoying way to find out.
check_family() {
    local family="$1" found
    found="$(fc-list : family | tr ',' '\n' | grep -ixF "${family}" | head -1 || true)"
    [[ -n "${found}" ]] || die "fontconfig cannot see the '${family}' family"
    log "fontconfig sees ${family}"
}

check_family "Andika"
check_family "Atkinson Hyperlegible Next"
check_family "Atkinson Hyperlegible Mono"

# And that a request for the family by name does not silently fall back to
# something else -- the classic fontconfig failure mode.
matched="$(fc-match "Andika" family 2>/dev/null | tr -d '\n')"
[[ "${matched}" == "Andika" ]] \
    || die "fc-match Andika resolved to '${matched}'; the family is shadowed"

size_after="$(rpm -qa --qf '%{SIZE}\n' | awk '{ s += $1 } END { print s + 0 }')"
awk -v a="${size_before}" -v b="${size_after}" \
    'BEGIN { printf "  -- fonts delta: %+.1f MiB installed\n", (b - a) / 1048576 }'

log "fonts installed"
