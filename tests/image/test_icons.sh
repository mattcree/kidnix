#!/usr/bin/bash
# Every picture kidnix ships must LOAD. Runs INSIDE the built container:
#
#   just test-image icons
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_icons.sh
#
# Why this file exists. On 2026-08-23 an audit rasterised all 113 first-party
# SVGs through the image's own librsvg and found five that never reach the
# screen at all: the Sounds & words, Numbers and Letters tiles on Home, the
# "Again" control inside Numbers, and the wallpaper source. Three of the four
# first-party tiles a child sees on the shelf were an Adwaita broken-image
# glyph, and had been for weeks. Every gate in CI was green, because no gate
# had ever asked an SVG to open: `build_files/64-first-party-activities.sh`
# checked that the icon file EXISTED and contained the string "<svg", the
# manifest validators checked that the path resolved, and the shell's own
# suite mocks GdkPixbuf. A file can satisfy all of that and still be a
# broken-image glyph on the child's shelf.
#
# The two failures were different and this file checks for both, plus a third:
#
#   1. ` -- ` inside an XML comment. Forbidden by XML; libxml2 (under librsvg,
#      under glycin, under GdkPixbuf) rejects the whole document. Four files.
#      Checked by tests/image/svg_wellformed.py, which is stdlib-only and also
#      runs on the source tree as `just lint-svg`.
#   2. `<svg>` past the loader's sniff window (~256 bytes) behind a long
#      licence comment: valid XML, "Couldn't recognize the image file format".
#      One file. Same checker.
#   3. Anything else librsvg refuses, which needs librsvg and therefore needs
#      to be here. See RENDERING below for which binary does it and why.
#
# What it cannot prove: that any of these are the RIGHT picture, that they read
# at 48 px, or that GTK ever draws one. The first two are the contact sheets in
# the audit; the third is tests/boot and tests/e2e.
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

# assert_py <description> <python source>
assert_py() {
    local description="$1"; shift
    local output
    if output="$(python3 -c "$1" 2>&1)"; then
        _report ok "${description}${output:+ (${output})}"
    else
        _report no "${description}" "${output}"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))' 2>/dev/null)"

# Where kidnix keeps pictures. Two overlay trees plus the Python packages: the
# shell's bundled set, and one directory of drawings per first-party activity.
readonly SHARE=/usr/share/kidnix
readonly WALLPAPER=/usr/share/backgrounds/kidnix

#: The site-packages directories that are allowed to ship SVGs. This is an
#: allow-list and not a glob on purpose -- a NEW activity that ships drawings
#: must be added here, and until it is, the count check below fails loudly
#: rather than letting a whole new icon set past ungated.
PACKAGES=(kidnix_shell kidnix_activity kidnix_parent_panel
          sounds_and_words clock_time numbers_activity letters_to_family)

roots=("${SHARE}" "${WALLPAPER}")
for package in "${PACKAGES[@]}"; do
    [[ -d "${PURELIB}/${package}" ]] && roots+=("${PURELIB}/${package}")
done

#: 113 first-party SVGs at the time of writing, four of which are installed
#: twice (an activity's own `icon.svg` is also copied to
#: /usr/share/kidnix/icons/<tile>.svg), so 117 paths. A floor, not an equality:
#: adding a drawing must not need this file edited, losing a directory must.
readonly SVG_FLOOR=110

# -----------------------------------------------------------------------------
section "what is here"

svgs=()
while IFS= read -r line; do svgs+=("${line}"); done < <(
    find "${roots[@]}" -type f -name '*.svg' 2>/dev/null | sort
)

if (( ${#svgs[@]} >= SVG_FLOOR )); then
    _report ok "${#svgs[@]} shipped SVGs found under ${#roots[@]} roots"
else
    _report no "at least ${SVG_FLOOR} shipped SVGs" "found ${#svgs[@]}"
fi

# A package that starts shipping drawings without being added to PACKAGES would
# otherwise be tested by nothing at all. This is the tripwire for that.
assert_py "no site-packages directory ships SVGs outside the allow-list" "
import pathlib, sys
allowed = set('${PACKAGES[*]}'.split())
purelib = pathlib.Path('${PURELIB}')
stray = sorted({p.relative_to(purelib).parts[0] for p in purelib.rglob('*.svg')} - allowed)
if stray: sys.exit('these ship SVGs and are not in PACKAGES: ' + ', '.join(stray))
print(f'{len(allowed)} allowed, none stray')
"

# -----------------------------------------------------------------------------
section "XML, and the loader's sniff window"

# The cheap half, shared verbatim with `just lint-svg` over the source tree.
checker=/tests/svg_wellformed.py
[[ -f "${checker}" ]] || checker="$(dirname "${BASH_SOURCE[0]}")/svg_wellformed.py"
if output="$(python3 "${checker}" "${roots[@]}" --min "${SVG_FLOOR}" -q 2>&1)"; then
    _report ok "every shipped SVG parses as XML and sniffs as an SVG"
else
    _report no "every shipped SVG parses as XML and sniffs as an SVG" "${output}"
fi

# -----------------------------------------------------------------------------
section "librsvg actually rasterises every one of them"

# RENDERING: which binary, and why not the obvious one.
#
# The obvious one is GdkPixbuf, which is what `kidnix_shell.widgets.icon_image`
# calls. It does not work here. Fedora's gdk-pixbuf delegates SVG to glycin
# (/usr/libexec/glycin-loaders/2+/glycin-svg), glycin sandboxes each load in
# `bwrap --unshare-all`, and bwrap cannot mount devpts inside a rootless podman
# container: every load fails with "Loader process exited early with status
# '1'" no matter what the file contains. It needs --privileged, which a test in
# CI should not want. (On the real bootc system bwrap works and GdkPixbuf is
# fine -- this is a container artefact, not a product defect. Anyone debugging
# a phantom "all icons broken" should read this paragraph first.)
#
# So: ImageMagick, which this image already has, and which is linked against
# **the same librsvg** -- `magick -list format` reports "SVG rw+ (RSVG 2.62.3)",
# the exact library version glycin loads. Same parser, same renderer, same
# verdict on a malformed file; only the sandbox differs. Both broken classes
# above were reproduced through it before this test was written.
readonly RENDER_PX=128

if command -v magick >/dev/null 2>&1; then
    _report ok "ImageMagick is here (librsvg: $(magick -list format 2>/dev/null | awk '/^ *SVG /{print $NF}' | tr -d '()'))"
else
    _report no "ImageMagick is here" "no magick binary; nothing can rasterise"
fi

assert_py "every shipped SVG renders through librsvg, and none renders blank" "
import pathlib, subprocess, sys, tempfile
from PIL import Image

paths = [pathlib.Path(p) for p in '''$(printf '%s\n' "${svgs[@]}")'''.split()]
broken, blank = [], []
with tempfile.TemporaryDirectory() as tmp:
    out = pathlib.Path(tmp) / 'out.png'
    for path in paths:
        done = subprocess.run(
            ['magick', '-background', 'none', str(path),
             '-resize', '${RENDER_PX}x${RENDER_PX}', str(out)],
            capture_output=True,
        )
        if done.returncode or not out.exists():
            broken.append(f'{path}: {done.stderr.decode().strip().splitlines()[:1]}')
            continue
        image = Image.open(out).convert('RGBA')
        mask = image.getchannel('A').point(lambda a: 255 if a > 24 else 0)
        opaque = mask.histogram()[255]
        # 0.5%: the thinnest thing in the set is clock-icons/length-half at
        # 15% ink, so this only ever catches a file that draws nothing.
        if opaque < 0.005 * image.width * image.height:
            blank.append(f'{path}: {opaque} opaque px of {image.width * image.height}')
        out.unlink(missing_ok=True)
if broken: sys.exit(f'{len(broken)} did not render:\n  ' + '\n  '.join(broken))
if blank: sys.exit(f'{len(blank)} rendered blank:\n  ' + '\n  '.join(blank))
print(f'{len(paths)} rasterised at ${RENDER_PX} px, all with ink on them')
"

# -----------------------------------------------------------------------------
section "the four Home tiles a child actually presses"

# Named, not globbed. These are the ones that were broken, they are the first
# thing on the first screen, and a regression here must say which tile.
for tile in sounds-and-words numbers letters clock-time; do
    icon="${SHARE}/icons/${tile}.svg"
    if [[ -f "${icon}" ]] && magick -background none "${icon}" -resize 72x72 png:/dev/null 2>/dev/null; then
        _report ok "the ${tile} tile draws"
    else
        _report no "the ${tile} tile draws" "${icon} does not load at tile size"
    fi
done

# -----------------------------------------------------------------------------
section "the size the file declares"

# `Gtk.Image.new_from_file` rasterises at the SVG's intrinsic size and then
# SCALES that bitmap: the Goodbye screen asks for 152 px and the shell's icons
# used to declare 64, a 2.4x upscale of an image librsvg would have drawn
# perfectly at any size. The declared width/height is the only lever that does
# not touch shell code, so the bundled sets declare 128 and the activities'
# own drawings 120. viewBox is untouched; this is an attribute, not a redraw.
assert_py "no shipped SVG declares an intrinsic size below 120 px" "
import pathlib, re, sys
import xml.etree.ElementTree as ElementTree
paths = [pathlib.Path(p) for p in '''$(printf '%s\n' "${svgs[@]}")'''.split()]
small = []
for path in paths:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError:
        continue  # already reported, in full, by the XML section above
    width, height = root.get('width', ''), root.get('height', '')
    if not width or not height:
        small.append(f'{path}: no width/height at all'); continue
    numbers = [float(re.sub(r'[^0-9.]', '', v) or 0) for v in (width, height)]
    # The wallpaper is 2560 wide; a drawing meant for a 152 px slot is not.
    if min(numbers) < 120:
        small.append(f'{path}: {width}x{height}')
if small: sys.exit(f'{len(small)} declare too small a raster:\n  ' + '\n  '.join(small))
print(f'{len(paths)} declare 120 px or more')
"

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
