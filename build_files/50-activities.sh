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

# GCompris' per-user settings file used to be drafted here, in a heredoc, and
# it was WRONG in a way that produced no error anywhere: it wrote a literal
# [General] group, which QSettings reserves for top-level keys and therefore
# ignores in full, and it put enableAutomaticDownloads under [Admin], where
# GCompris never looks. Every line of it silently did nothing.
#
# The reviewed file now lives in the overlay at
# system_files/usr/share/kidnix/gcompris/gcompris-qt.conf, is written in the
# [%General] dialect QSettings actually reads, and is seeded into the child's
# home by /usr/lib/tmpfiles.d/kidnix-gcompris.conf. build_files/55-gcompris.sh
# validates it against curated.toml AND round-trips it through a real GCompris
# run. The old path stays as a symlink to it (55-gcompris.sh section 2) so
# nothing that knew the old name breaks.
#
# docs/spikes/gcompris-curation.md §6 asked for this heredoc to be deleted
# outright and left the call to whoever owns this file. Deleted.
install -d /usr/share/kidnix/activities

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

# British English. Tux Paint does not read LANG for its own UI strings the way
# a gettext-only program does -- it has its own language table, and the token
# it wants is a NAME, not a POSIX locale ("british" or "british-english"; run
# `tuxpaint --lang help` to see the list). Without this the status bar reads
# "Pick a COLOR and a brush shape to draw with." on a UK five-year-old's
# machine, which is the exact screenshot the 2026-08-23 early-years-teacher
# review used to open its locale BLOCKER.
lang=british-english

# The largest button Tux Paint will draw. --buttonsize takes 24-192 and
# defaults to 48, "suitable for displays with 96 to 120dpi pixel density"
# (tuxpaint(1)); 96 is double that and still inside the range on every panel
# kidnix targets.
#
# WHY 96 AND NOT 192: buttonsize scales the tool columns, and Tux Paint lays
# those out in a fixed grid down the left and right of the canvas. At 192 the
# columns eat most of a 1366x768 laptop screen and there is nothing left to
# draw on. 96 doubles every target without taking the canvas away.
#
# WHAT THIS IS FOR. The early-years-teacher review made Tux Paint's own quit
# dialogue a BLOCKER: "a green tick and a pink cross around 20 px ... against
# our own numbers (18 mm floor; a four-year-old hits 16 px 43% of the time) it
# is the smallest and most consequential target we ship", and it is the target
# the whole Put-away ritual depends on. tuxpaint(1) describes --buttonsize as
# adjusting "the size of the buttons in Tux Paint's user interface", and the
# quit prompt's tick and cross are buttons in that interface -- so this should
# raise them. THAT IS AN INFERENCE FROM THE MAN PAGE, NOT A MEASUREMENT: it
# needs one screenshot of the quit prompt at 1366x768 with a ruler on it.
# tests/image/test_activities.sh asserts the option exists and the
# value is set; the millimetre measurement at 1366x768 is still owed, and is
# recorded as owed in docs/spikes/panel-wave-c.md §5.
buttonsize=96

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

# Quit stays available, and this is now a MEASURED decision rather than a taste
# one -- shell v0.1.5 tried `noquit=yes` and it had to be reverted.
#
# Tux Paint does catch SIGTERM (SDL turns it into SDL_QUIT), but it answers it
# by putting its OWN "Do you really want to quit?" on screen -- a green tick and
# a pink cross, two large targets -- and waiting for an answer. Only then does
# `autosave=yes` write the picture. There is no option anywhere in tuxpaint(1)
# to skip that prompt.
#
# So with `noquit=yes` the quit request is swallowed entirely: the band's Back
# does nothing at all, and whatever the shell does next (a SIGKILL after the
# autosave grace) destroys the child's drawing. Verified in the VM on
# 2026-08-22: SIGTERM and SIGINT are both caught and both ignored under
# `noquit`, SIGHUP kills without saving, and `~/.tuxpaint/saved` stays empty.
#
# With `quit=yes` the band's Back reaches the child as Tux Paint's own tick and
# cross, they answer it, and the drawing is saved. ADR-0010 #5 therefore
# stands: the dialogue stays for now, and retiring it needs a way to close a
# Wayland client's window that we do not have (gnome-kiosk exposes no window
# D-Bus API and there is no input-injection path in the child's session).
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

# Every manifest must parse, carry the whole schema, and -- for the RPM-backed
# ones -- name an executable that actually exists. Otherwise the shell shows a
# tile that does nothing, which for a pre-reader is indistinguishable from the
# computer being broken. python3 is in base-main, so tomllib is free here.
python3 - <<'PY'
import pathlib, shutil, sys, tomllib

REQUIRED = {
    "schema": int, "id": str, "name": str, "audio_label": str, "icon": str,
    "exec": list, "category": str, "age_min": int, "age_max": int,
    "oars_rating": str, "network_required": bool, "source": str,
    "package": str, "licence": str, "journal_watch": list,
    "wayland_native": bool, "notes": str,
}
CATEGORIES = {"make", "learn", "play"}
SOURCES = {"rpm", "flatpak"}

failed = False
manifests = sorted(pathlib.Path("/usr/share/kidnix/activities").glob("*.toml"))
if not manifests:
    sys.exit("no activity manifests found")

for path in manifests:
    def bad(message):
        global failed
        print(f"{path.name}: {message}", file=sys.stderr)
        failed = True

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    for key, kind in REQUIRED.items():
        if key not in data:
            bad(f"missing required key {key!r}")
        elif not isinstance(data[key], kind):
            bad(f"{key!r} should be {kind.__name__}, got {type(data[key]).__name__}")

    if data.get("id") != path.stem:
        bad(f"id {data.get('id')!r} does not match filename")
    if data.get("category") not in CATEGORIES:
        bad(f"category {data.get('category')!r} not in {sorted(CATEGORIES)}")
    if data.get("source") not in SOURCES:
        bad(f"source {data.get('source')!r} not in {sorted(SOURCES)}")
    if data.get("network_required") is True:
        bad("network_required=true: the child session has no egress")

    # Only RPM activities are in the image at build time; Flatpak ones arrive on
    # a later, online boot and the shell checks for them at runtime.
    if data.get("source") == "rpm":
        program = data["exec"][0]
        if shutil.which(program) is None:
            bad(f"exec {program!r} is not on PATH")

print(f"validated {len(manifests)} activity manifests")
sys.exit(1 if failed else 0)
PY
