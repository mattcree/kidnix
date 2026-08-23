#!/usr/bin/bash
# Static assertions about the activity payload. Runs INSIDE the container, same
# shape and same helpers as test_image.sh:
#
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_activities.sh
#
# What it can prove: the right packages are installed, the binaries a manifest
# points at exist, GCompris' offline voice bundles are on disk in the layout its
# DownloadManager searches, Tux Paint's system config says what we think it says,
# and the first-boot Flatpak unit is wired up.
#
# What it cannot prove: that GCompris actually *speaks* using those bundles, or
# that any of these apps render on Wayland. Both need a running session --
# tests/boot/, or a human with a child. See docs/spikes/activities-packaging.md.
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

# assert_file <path>
assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

# assert_exec <path>
assert_exec() {
    if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi
}

# assert_rpm <name>
assert_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report ok "package $1 ($(rpm -q --qf '%{VERSION}-%{RELEASE}' "$1"))"
    else
        _report no "package $1" "not installed"
    fi
}

# assert_no_rpm <name> <why>
assert_no_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report no "package $1 absent" "$2"
    else
        _report ok "package $1 absent ($2)"
    fi
}

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local description="$1"; shift
    if "$@" >/dev/null 2>&1; then _report ok "${description}"; else _report no "${description}"; fi
}

# assert_nonempty_file <path> <min-bytes> <description>
assert_nonempty_file() {
    local size
    size="$(stat -c '%s' "$1" 2>/dev/null || echo 0)"
    if [[ "${size}" -ge "$2" ]]; then
        _report ok "$3 ($(numfmt --to=iec "${size}"))"
    else
        _report no "$3" "got ${size} bytes, want >= $2"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

readonly GCOMPRIS_RCC_ROOT=/usr/share/gcompris-qt/rcc/data3
readonly ACTIVITY_DIR=/usr/share/kidnix/activities

# -----------------------------------------------------------------------------

section "activity packages (RPM-first: everything a child opens is in /usr)"
for pkg in gcompris-qt tuxpaint tuxpaint-stamps ktuberling blinken klettres \
           kolf supertux tuxmath kiwix-tools espeak-ng speech-dispatcher-espeak-ng; do
    assert_rpm "${pkg}"
done
# Qt activities must speak Wayland directly rather than falling into XWayland.
assert_rpm qt6-qtwayland
# 142 MiB of General MIDI soundfont, pulled in as a tuxmath Recommends purely
# for background music. Excluded deliberately; see 50-activities.sh.
assert_no_rpm fluid-soundfont-gm "142 MiB weak dep excluded on purpose"
# Would drag 438 MiB of Qt5 for a UI a child should never see; we ship
# kiwix-serve and let the shell be the viewer.
assert_no_rpm kiwix-desktop "kiwix-serve + shell viewer instead"

section "activity binaries (a manifest must never point at nothing)"
for binary in /usr/bin/gcompris-qt /usr/bin/tuxpaint /usr/bin/ktuberling \
              /usr/bin/blinken /usr/bin/klettres /usr/bin/kolf \
              /usr/bin/supertux2 /usr/bin/tuxmath /usr/bin/kiwix-serve \
              /usr/bin/espeak-ng; do
    assert_exec "${binary}"
done

section "GCompris offline assets (the anchor app is mute without these)"
# Layout comes from DownloadManager::getSystemResourcePaths() + initializeAssets():
# <applicationDirPath>/../share/gcompris-qt/rcc/ + data3/<subdir>/{Contents,*.rcc}
for subdir in voices-ogg words backgroundMusic; do
    if [[ -d "${GCOMPRIS_RCC_ROOT}/${subdir}" ]]; then
        _report ok "asset dir ${GCOMPRIS_RCC_ROOT}/${subdir}"
    else
        _report no "asset dir ${GCOMPRIS_RCC_ROOT}/${subdir}" "missing"
    fi
    # initializeAssets() will not even look for an .rcc unless it can parse the
    # sibling Contents index first, so this file is load-bearing.
    assert_file "${GCOMPRIS_RCC_ROOT}/${subdir}/Contents"
done

# en_GB is the primary voice; en_US is what GCompris falls back to when the
# system locale is "C" (ApplicationInfo::getVoicesLocale()).
assert_cmd "en_GB voice bundle present" \
    bash -c "compgen -G '${GCOMPRIS_RCC_ROOT}/voices-ogg/voices-en_GB-*.rcc'"
assert_cmd "en_US voice bundle present" \
    bash -c "compgen -G '${GCOMPRIS_RCC_ROOT}/voices-ogg/voices-en_US-*.rcc'"
assert_cmd "word-image bundle present" \
    bash -c "compgen -G '${GCOMPRIS_RCC_ROOT}/words/words-*.rcc'"
assert_cmd "background-music bundle present" \
    bash -c "compgen -G '${GCOMPRIS_RCC_ROOT}/backgroundMusic/backgroundMusic-ogg-*.rcc'"

# A truncated download would leave a small file that still "exists".
shopt -s nullglob
voices=( "${GCOMPRIS_RCC_ROOT}"/voices-ogg/voices-en_GB-*.rcc )
shopt -u nullglob
if [[ "${#voices[@]}" -gt 0 ]]; then
    assert_nonempty_file "${voices[0]}" 10000000 "en_GB voice bundle is a real bundle"
else
    _report no "en_GB voice bundle is a real bundle" "no file to measure"
fi

# parseContents() rejects the whole index if any line is not exactly
# "<md5>  <filename>", and every filename it lists must be on disk or GCompris
# registers an empty path.
assert_cmd "Contents indexes are md5sum format and match the files on disk" \
    python3 -c "
import pathlib, sys
root = pathlib.Path('${GCOMPRIS_RCC_ROOT}')
seen = 0
for contents in root.glob('*/Contents'):
    for line in contents.read_text().splitlines():
        parts = line.split()
        if len(parts) != 2:
            sys.exit(f'{contents}: bad line {line!r}')
        digest, name = parts
        if len(digest) != 32 or not (contents.parent / name).is_file():
            sys.exit(f'{contents}: {name} missing or digest malformed')
        seen += 1
sys.exit(0 if seen >= 4 else f'only {seen} indexed assets')
"

assert_file /usr/share/kidnix/activities/gcompris-qt.conf.default
assert_grep '^enableAutomaticDownloads=false$' \
    /usr/share/kidnix/activities/gcompris-qt.conf.default \
    "GCompris default config disables runtime downloads"

section "Tux Paint, configured for a five-year-old"
assert_file /etc/tuxpaint/tuxpaint.conf
assert_grep '^fullscreen=native$'  /etc/tuxpaint/tuxpaint.conf "tuxpaint runs fullscreen at native resolution"
assert_grep '^sound=yes$'          /etc/tuxpaint/tuxpaint.conf "tuxpaint sound on (half the feedback for a pre-reader)"
assert_grep '^stamps=yes$'         /etc/tuxpaint/tuxpaint.conf "tuxpaint stamps enabled"
assert_grep '^saveovernew=yes$'    /etc/tuxpaint/tuxpaint.conf "tuxpaint never overwrites a child's earlier drawing"
assert_grep '^autosave=yes$'       /etc/tuxpaint/tuxpaint.conf "tuxpaint never asks a pre-reader whether to save"
assert_grep '^nolockfile=yes$'     /etc/tuxpaint/tuxpaint.conf "tuxpaint can be relaunched within 30s (kiosk restarts)"
# Quitting must stay possible, and `quit=yes` specifically: Tux Paint answers
# the shell's SIGTERM with its own picture-coded "really quit?" prompt, and
# `noquit=yes` swallows the request entirely -- so Back would do nothing and the
# SIGKILL that follows would destroy the drawing. Measured in the VM; see the
# comment in build_files/50-activities.sh.
assert_grep '^quit=yes$'           /etc/tuxpaint/tuxpaint.conf "Back must reach Tux Paint's own tick-and-cross prompt"
assert_rpm tuxpaint-stamps

section "activity manifests"
assert_cmd "manifest directory exists" test -d "${ACTIVITY_DIR}"
for id in tuxpaint gcompris ktuberling blinken klettres kolf supertux tuxmath kiwix turbowarp; do
    assert_file "${ACTIVITY_DIR}/${id}.toml"
done
assert_cmd "every manifest parses as TOML and carries the full schema" \
    python3 -c "
import pathlib, shutil, sys, tomllib
required = {'schema','id','name','audio_label','icon','exec','category','age_min',
            'age_max','oars_rating','network_required','source','package','licence',
            'journal_watch','wayland_native','notes'}
paths = sorted(pathlib.Path('${ACTIVITY_DIR}').glob('*.toml'))
if len(paths) < 10:
    sys.exit(f'only {len(paths)} manifests')
for path in paths:
    data = tomllib.loads(path.read_text())
    missing = required - set(data)
    if missing:
        sys.exit(f'{path.name}: missing {sorted(missing)}')
    if data['id'] != path.stem:
        sys.exit(f'{path.name}: id {data[\"id\"]!r} != filename')
    if data['category'] not in {'make','learn','play'}:
        sys.exit(f'{path.name}: bad category {data[\"category\"]!r}')
    if data['network_required']:
        sys.exit(f'{path.name}: network_required=true, but the child has no egress')
    if data['source'] == 'rpm' and shutil.which(data['exec'][0]) is None:
        sys.exit(f'{path.name}: exec {data[\"exec\"][0]!r} not on PATH')
"
# Every non-passive category must be represented, or the shell's 'make / learn /
# play' grouping has an empty shelf.
assert_cmd "all three categories are populated" \
    python3 -c "
import pathlib, tomllib, sys
cats = {tomllib.loads(p.read_text())['category']
        for p in pathlib.Path('${ACTIVITY_DIR}').glob('*.toml')}
sys.exit(0 if cats == {'make','learn','play'} else f'categories: {sorted(cats)}')
"

section "what the tiles claim (2026-08-23 panel)"
# Every one of these is a shipped sentence a parent reads, and each was found
# to be untrue by the expert panel. They are assertions and not prose because
# "the tile names are the marketing, not the docs" (early-years teacher).

# KLettres was called "Letter sounds", which is a phonics claim, while its own
# notes admitted nobody had checked whether the en_GB recordings are letter
# names or phonemes. They are NAMES: after trimming silence at -40 dBFS the
# shipped clips carry 0.33-0.71 s of continuous speech (t=0.36, p=0.39,
# b=0.56, w=0.71) and an isolated plosive phoneme is a 0.1-0.2 s burst.
# Method and full numbers in docs/spikes/panel-wave-c.md §3.
assert_grep '^name = "Letter names"$' "${ACTIVITY_DIR}/klettres.toml" \
    "KLettres says what it actually does: letter NAMES"
# The tile NAME and the SPOKEN LABEL are the whole claim a parent and a child
# ever see -- "the tile names are the marketing, not the docs". Neither may
# mention sounds or phonics. (The goal line may, and must, say what it is NOT.)
assert_cmd "no tile name or spoken label claims sounds or phonics" \
    python3 -c "
import pathlib, sys, tomllib
bad = []
for p in sorted(pathlib.Path('${ACTIVITY_DIR}').glob('*.toml')):
    d = tomllib.loads(p.read_text())
    for field in ('name', 'audio_label'):
        text = d.get(field, '').lower()
        if 'phonic' in text or 'letter sound' in text:
            bad.append(f'{p.name}: {field} = {d[field]!r}')
if bad: sys.exit('; '.join(bad))
print(f'{len(list(pathlib.Path(\"${ACTIVITY_DIR}\").glob(\"*.toml\")))} manifests')
"
assert_cmd "the KLettres goal says out loud that it is not phonics" \
    python3 -c "
import pathlib, sys, tomllib
g = tomllib.loads(pathlib.Path('${ACTIVITY_DIR}/klettres.toml').read_text())['goal'].lower()
if 'name' not in g: sys.exit('the goal does not say the voice gives letter NAMES')
if 'not its phonics sound' not in g: sys.exit('the goal does not disclaim phonics')
"

# TuxMath and SuperTux both have scores and a game-over, which contradicts
# principle E1 ("no points, no scores, no levels"). The teacher: "A Reception
# child hitting GAME OVER on a machine whose premise is 'you cannot fail here'
# is a tonal break that will produce the first week's tears." Overlap
# semantics mean age_min=7 removes them from a 4-6 profile entirely.
assert_cmd "the two activities that can be LOST are out of the 4-6 band" \
    python3 -c "
import pathlib, sys, tomllib
bad = []
for name in ('tuxmath', 'supertux'):
    d = tomllib.loads(pathlib.Path('${ACTIVITY_DIR}/%s.toml' % name).read_text())
    if d['age_min'] < 7: bad.append(f\"{name}: age_min={d['age_min']}\")
    if 'game over' not in d['goal'].lower() and 'lost' not in d['goal'].lower():
        bad.append(f'{name}: goal does not say it can be lost')
if bad: sys.exit('; '.join(bad))
print('tuxmath 7+, supertux 7+')
"
# ...and the corollary a four-year-old actually experiences: what IS left.
assert_cmd "a 4-5 year old still has activities after the age gate" \
    python3 -c "
import pathlib, sys, tomllib
def shown(d):
    lo, hi = d.get('age_min'), d.get('age_max')
    return not ((hi is not None and hi < 4) or (lo is not None and lo > 5))
left = [tomllib.loads(p.read_text())['id']
        for p in pathlib.Path('${ACTIVITY_DIR}').glob('*.toml')
        if shown(tomllib.loads(p.read_text()))]
if len(left) < 6: sys.exit(f'only {len(left)} tiles for a 4-5 year old: {left}')
print(f'{len(left)} tiles: {\" \".join(sorted(left))}')
"

# The GCompris tile shipped `goal = \"About 190 small learning games. Not
# curated yet -- some are pitched well above five.\"` while 18 reviewed EYFS/KS1
# mappings sat unreachable. The goal must now describe the shelf that exists.
assert_cmd "the GCompris tile's goal describes the 18, not the 198" \
    python3 -c "
import pathlib, sys, tomllib
d = tomllib.loads(pathlib.Path('${ACTIVITY_DIR}/gcompris.toml').read_text())
g = d['goal'].lower()
if 'not curated' in g: sys.exit('still says it is not curated')
if 'eighteen' not in g and '18' not in g: sys.exit(f'goal does not say how many: {d[\"goal\"]!r}')
if 'hidden' not in g: sys.exit('goal does not say the rest are hidden')
print(d['goal'])
"

section "Tux Paint: the targets a four-year-old has to hit"
# The Put-away ritual ends at Tux Paint's OWN tick and cross, which the
# early-years teacher measured at "around 20 px ... the smallest and most
# consequential target we ship" against an 18 mm floor. --buttonsize is the
# only lever the config file has; 96 is double the default and inside the
# documented 24-192 range.
assert_grep '^buttonsize=96$' /etc/tuxpaint/tuxpaint.conf \
    "tuxpaint buttons are 96 px, double the 48 px default"
assert_cmd "tuxpaint really does accept --buttonsize in that range" \
    bash -c "tuxpaint --help 2>&1 | grep -q -- '--buttonsize=N (24-192; default=48)'"
# NOT asserted, and owed: that this also scales the quit prompt's tick and
# cross. tuxpaint(1) says --buttonsize adjusts "the size of the buttons in Tux
# Paint's user interface" and the prompt's tick and cross are buttons in that
# interface, but nobody has put a ruler on a screen. See panel-wave-c.md §5.

section "first-boot Flatpaks (secondary path, for what Fedora does not package)"
assert_file /usr/share/kidnix/flatpaks.txt
assert_grep '^org\.turbowarp\.TurboWarp$' /usr/share/kidnix/flatpaks.txt "TurboWarp is on the first-boot list"
assert_exec /usr/libexec/kidnix-flatpak-firstboot
assert_file /usr/lib/systemd/system/kidnix-flatpaks-firstboot.service
assert_file /usr/lib/systemd/system/kidnix-flatpaks-firstboot.timer
if [[ -L /etc/systemd/system/timers.target.wants/kidnix-flatpaks-firstboot.timer ]]; then
    _report ok "unit enabled: kidnix-flatpaks-firstboot.timer"
else
    _report no "unit enabled: kidnix-flatpaks-firstboot.timer" "no enablement symlink"
fi
# Offline is the normal state for this machine; the unit must not go red for it.
assert_grep '^SuccessExitStatus=0 75$' \
    /usr/lib/systemd/system/kidnix-flatpaks-firstboot.service \
    "offline first boot is a success, not a failed unit"
assert_rpm flatpak

section "bootc hygiene for the activity payload"
# Activities must live in /usr, which bootc ships and can roll back. Anything a
# build stage wrote under /var would be silently discarded at install time.
if [[ -z "$(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -print -quit 2>/dev/null)" ]]; then
    _report ok "/var carries no activity content"
else
    _report no "/var carries no activity content" \
        "found: $(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -printf '%f ' 2>/dev/null)"
fi

# Informational, not an assertion: what the activities actually cost.
printf '\n\033[1mactivity payload size\033[0m\n'
for pkg in gcompris-qt tuxpaint tuxpaint-stamps ktuberling blinken klettres \
           kolf supertux tuxmath kiwix-tools; do
    printf '  %-20s %s\n' "${pkg}" \
        "$(rpm -q --qf '%{SIZE}' "${pkg}" 2>/dev/null | numfmt --to=iec 2>/dev/null || echo '-')"
done
printf '  %-20s %s\n' "gcompris assets" \
    "$(du -sh "${GCOMPRIS_RCC_ROOT}" 2>/dev/null | cut -f1 || echo '-')"

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
