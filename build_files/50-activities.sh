#!/usr/bin/bash
# Install the first-wave child activities.
#
# RPM-first, deliberately. Fedora 44 packages every activity on the v0.1
# shortlist except TurboWarp, so the "how do we get Flatpaks into an immutable
# image" problem (docs/research/07 §4 item 3, the highest-risk unknown) simply
# does not apply to the apps a five-year-old will actually open. RPMs land in
# /usr, are covered by `bootc upgrade`/rollback, need no first-boot network and
# no /var write, and are signed by Fedora. Flatpak stays as the escape hatch for
# the handful of things Fedora does not ship -- see 'first-boot Flatpaks' below
# and docs/spikes/activities-packaging.md for the measurements behind all this.
set -euo pipefail

# --- 1. packages -------------------------------------------------------------

ACTIVITY_PACKAGES=(
    # The anchor. Ages 2-10, ~190 activities, AGPL-3.0. Voices/words/music are
    # NOT in the RPM -- they are fetched from cdn.kde.org at runtime, which a
    # no-egress child session cannot do. Section 2 below bakes them in.
    gcompris-qt

    # Best-in-class 4-8 drawing program, and the clearest "making over
    # consuming" activity we ship. Stamps are a separate 193 MiB and are most
    # of what makes it fun for a pre-reader, so they are not optional.
    tuxpaint
    tuxpaint-stamps

    # Potato-head dress-up. Speaks every part name aloud in the chosen locale,
    # needs no reading at all -- the single best 4-6 activity in the KDE set.
    ktuberling

    # Simon-says. Pure memory, no text, no failure state worth crying over.
    blinken

    # Alphabet/phonics with recorded human audio. Directly serves "pre-reader
    # first" and it is only ~48 MiB once KF6 is already paid for.
    klettres

    # Mini-golf. Mouse-precision practice dressed up as a game; 5+.
    kolf

    # Platformer. The one "play" activity in the first wave, PEGI 3 / OARS
    # cartoon-violence-mild. 240 MiB is the price of the music and sprites.
    supertux

    # Arithmetic drill for the top of the age band (6-8). Cheap once its SDL
    # deps are in -- but see FLUIDSYNTH_SOUNDFONT_EXCLUDE below.
    tuxmath

    # kiwix-serve, for the offline library. The ZIM content itself is NOT
    # shipped here (Simple Wikipedia mini alone is 450 MB); the parent adds it.
    # kiwix-desktop is deliberately skipped: it drags 438 MiB of Qt5, and the
    # shell will render the library through its own view instead.
    kiwix-tools

    # TTS baseline for pre-readers. Both are already in base-main today; listing
    # them makes that a build-time contract rather than an accident we inherit.
    espeak-ng
    speech-dispatcher-espeak-ng
)

# tuxmath Recommends: fluid-soundfont-gm, a 142 MiB General MIDI soundfont --
# 9x the size of tuxmath itself -- purely for its background music. Weak deps
# are otherwise left on across this image on purpose (see 00-packages.sh); this
# is the one measured exception, and it is a size decision, not a taste one.
FLUIDSYNTH_SOUNDFONT_EXCLUDE="--exclude=fluid-soundfont-gm"

dnf5 -y install "${FLUIDSYNTH_SOUNDFONT_EXCLUDE}" "${ACTIVITY_PACKAGES[@]}"

# --- 2. GCompris offline assets ----------------------------------------------
#
# GCompris ships no voices, no word images and no background music in the RPM;
# DownloadManager fetches them from https://cdn.kde.org/gcompris/data3/ on first
# run. A child session has no network, so we pre-seed them at build time.
#
# Where they go, read out of the upstream source (src/core/DownloadManager.cpp,
# getSystemResourcePaths(), verified against master on 2026-08-22):
#
#   QCoreApplication::applicationDirPath() + "/" + GCOMPRIS_DATA_FOLDER + "/rcc/"
#
# GCOMPRIS_DATA_FOLDER is "../${CMAKE_INSTALL_DATADIR}/gcompris-qt" (config.h.in
# + CMakeLists.txt), and applicationDirPath() is /usr/bin, so the system-wide
# search root is /usr/share/gcompris-qt/rcc/ -- corroborated by the RPM already
# installing translations to /usr/share/gcompris-qt/translations.
#
# Under that root the app looks for <root>/data3/<subdir>/<file>.rcc, and it will
# only look at all if it can first parse <root>/data3/<subdir>/Contents --
# initializeAssets() populates its resource map exclusively from those index
# files. So the Contents files are load-bearing, not documentation.
#
# Licence: GCompris code is AGPL-3.0-only; the voice recordings, word images and
# background music in these .rcc bundles are the project's own assets, released
# under CC-BY-SA-4.0 / GPL-3.0-or-later. Redistributable in an image. Recorded
# here per AGENTS.md §5 ("bundled content/voices must be redistributable").

GCOMPRIS_CDN="https://cdn.kde.org/gcompris/data3"
GCOMPRIS_RCC_ROOT="/usr/share/gcompris-qt/rcc/data3"

# subdir|filename|md5 -- pinned, so a CDN rotation is an explicit reviewed bump
# rather than a silent content change under a child's OS. The md5s are upstream's
# own, taken from the matching data3/<subdir>/Contents on 2026-08-22.
#
# en_GB is the primary (this is a UK household); en_US is the fallback GCompris
# picks when the system locale is "C" (ApplicationInfo::getVoicesLocale()).
GCOMPRIS_ASSETS=(
    "voices-ogg|voices-en_GB-2026-07-28-15-07-14.rcc|efde411f1af5d708a3b74e12bfa9fed0"
    "voices-ogg|voices-en_US-2026-07-28-15-07-14.rcc|3c3f72d484a35fc6665535dbec7da93a"
    "words|words-webp-2022-04-10-21-14-15.rcc|d8bd7a3f2f24971a86f484f5751f46e1"
    "backgroundMusic|backgroundMusic-ogg-2024-03-19-11-10-30.rcc|121469ac175a40d5f13cecceceb8549e"
)

for asset in "${GCOMPRIS_ASSETS[@]}"; do
    IFS='|' read -r subdir filename md5 <<<"${asset}"
    target_dir="${GCOMPRIS_RCC_ROOT}/${subdir}"
    mkdir -p "${target_dir}"

    echo "==> gcompris asset: ${subdir}/${filename}"
    curl -fsSL --retry 3 --retry-delay 2 \
        -o "${target_dir}/${filename}" \
        "${GCOMPRIS_CDN}/${subdir}/${filename}"

    got="$(md5sum "${target_dir}/${filename}" | cut -d' ' -f1)"
    if [[ "${got}" != "${md5}" ]]; then
        echo "checksum mismatch for ${subdir}/${filename}: want ${md5}, got ${got}" >&2
        exit 1
    fi

    # DownloadManager::parseContents() wants md5sum(1) output format, and it
    # rejects the whole file if any line does not split into exactly two fields.
    # We write our own index rather than shipping upstream's, so GCompris is
    # never told about a locale whose .rcc is not actually on disk.
    printf '%s  %s\n' "${md5}" "${filename}" >>"${target_dir}/Contents"
done

# A default settings file for the child. GCompris reads
# $XDG_CONFIG_HOME/gcompris/gcompris-qt.conf (src/core/main.cpp), which is
# per-user and therefore cannot be shipped read-only in /usr -- the shell or the
# first-boot unit has to copy this into the kid's home. Parked here so the
# values are reviewed and version-controlled rather than invented at seed time.
install -d /usr/share/kidnix/activities
cat >/usr/share/kidnix/activities/gcompris-qt.conf.default <<'EOF'
; Seeded into ~/.config/gcompris/gcompris-qt.conf for the kid account.
; Rationale in docs/spikes/activities-packaging.md.
[General]
locale=en_GB.UTF-8
enableAudioVoices=true
enableAudioEffects=true
fullscreen=true
; No network in the child session: never try, never show a download dialog.
[Admin]
enableAutomaticDownloads=false
downloadServerUrl=https://cdn.kde.org/gcompris
EOF

# --- 3. Tux Paint, configured for a five-year-old ----------------------------
#
# Written here rather than dropped in system_files/ because the tuxpaint RPM
# owns /etc/tuxpaint/tuxpaint.conf as a %config file and would clobber (or
# .rpmsave) an overlay copy during the dnf transaction above.
#
# Syntax is key=value, one per line; every option corresponds to a
# --long-option in tuxpaint(1).
install -d /etc/tuxpaint
cat >/etc/tuxpaint/tuxpaint.conf <<'EOF'
# kidnix system-wide Tux Paint configuration.
# Rationale for every line: docs/spikes/activities-packaging.md.

# The shell owns the screen; Tux Paint should fill it at the panel's own
# resolution rather than making the compositor rescale a guessed mode.
fullscreen=native

# Sound is not decoration for a pre-reader -- it is half the feedback.
sound=yes

# Stamps are the reason a four-year-old stays with Tux Paint.
stamps=yes

# A child cannot answer "overwrite the old version?". Always make a new file,
# so nothing a child made can be destroyed by saving again.
saveovernew=yes

# ...and never ask "do you want to save?" on the way out. Quitting saves.
autosave=yes

# Tux Paint refuses to start twice within 30 seconds. In a kiosk where the shell
# may relaunch an activity after a crash, that is a mysterious dead button.
nolockfile=yes

# Quit stays available: the shell has to be able to close an activity, and a
# child needs a way out that is not "ask a grown-up to reboot".
quit=yes
EOF

# --- 4. first-boot Flatpaks (secondary path) ---------------------------------
#
# For the small set of activities Fedora does not package -- today just
# TurboWarp, our offline Scratch. This is option (a) from the spike doc: a
# retrying first-boot unit that installs from Flathub. It needs the network
# once, on the parent's setup pass, and is harmless if the machine is offline
# (the timer simply retries and the shell hides activities whose exec is
# missing). Options (b) sideload-repo and (c) a /usr installation are analysed
# in the spike doc; neither is implemented.
#
# NOTE for the lockdown implementer: these Flatpaks must get
# `flatpak override --system --unshare=network <id>` once installed. TurboWarp
# is fully offline-capable and must not be allowed to phone home.
systemctl enable kidnix-flatpaks-firstboot.timer

# --- 5. assertions -----------------------------------------------------------
#
# A silent upstream rename should fail the build here, not at a child's first
# boot. Same contract as 00-packages.sh.
for binary in /usr/bin/gcompris-qt /usr/bin/tuxpaint /usr/bin/ktuberling \
              /usr/bin/blinken /usr/bin/klettres /usr/bin/kolf \
              /usr/bin/supertux2 /usr/bin/tuxmath /usr/bin/kiwix-serve \
              /usr/bin/espeak-ng /usr/libexec/kidnix-flatpak-firstboot; do
    test -x "${binary}" || { echo "missing expected binary: ${binary}" >&2; exit 1; }
done

# Qt apps must talk Wayland natively rather than falling through XWayland.
rpm -q qt6-qtwayland >/dev/null || {
    echo "qt6-qtwayland missing: Qt activities would run under XWayland" >&2
    exit 1
}

# Every manifest must name a real executable, or the shell will show a tile that
# does nothing. python3 is in base-main, so tomllib is available at build time.
python3 - <<'PY'
import pathlib, shutil, sys, tomllib

failed = False
manifests = sorted(pathlib.Path("/usr/share/kidnix/activities").glob("*.toml"))
if not manifests:
    sys.exit("no activity manifests found")

for path in manifests:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not data.get("enabled", True):
        continue
    program = data["exec"][0]
    if shutil.which(program) is None:
        print(f"{path.name}: exec {program!r} is not on PATH", file=sys.stderr)
        failed = True

print(f"validated {len(manifests)} activity manifests")
sys.exit(1 if failed else 0)
PY
