#!/usr/bin/bash
# Hardening pass: take things OUT of the image.
#
# Every other stage adds. This one is the counterweight, and it runs last
# (before 90-cleanup.sh) so it can see everything the earlier stages and their
# weak dependencies dragged in. Three jobs:
#
#   1. remove software a child's computer must not contain (a web browser) and
#      software nothing on it will ever use but the network can reach
#      (gnome-remote-desktop, rygel, cups-browsed);
#   2. mask units that phone home, update themselves, or reboot the machine on
#      their own schedule -- AGENTS.md non-negotiables 1, 5 and 8;
#   3. replace 38 MiB of stock wallpaper with one kidnix wallpaper, and ship
#      the parent's config defaults.
#
# Rules for editing this file:
#
#   * every removal and every mask carries a one-line reason IN THE TABLE, and
#     the full reasoning lives in docs/spikes/hardening.md. A mask with no
#     reason is indistinguishable from a mask added by mistake, and in two
#     years nobody will dare remove it.
#   * assert what you removed is gone AND that what must survive survived. The
#     dangerous failure mode here is not "the mask did not apply", it is "the
#     removal took gdm with it and the build still passed".
#
# What this stage deliberately does NOT do is listed in
# docs/spikes/hardening.md section 3 with the evidence: avahi, cups, sshd,
# bluetooth and gnome-online-accounts all stay, three of them because removing
# them costs more than it buys and one of them (goa) because dnf takes gdm,
# gnome-shell and gnome-control-center with it.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

size_before="$(rpm -qa --qf '%{SIZE}\n' | awk '{ s += $1 } END { print s + 0 }')"
count_before="$(rpm -qa | wc -l)"

# -----------------------------------------------------------------------------
# 1. Removals
# -----------------------------------------------------------------------------
#
# Reasons, in the order the packages appear below:
#
#   firefox, firefox-langpacks
#       base-main ships it. ADR-0005: "no web browser" is a property of the
#       MACHINE, not of the child's session. A browser in the image is the
#       residual hole if a child ever reaches the parent's desktop, and it is
#       328 MiB of the largest attack surface in desktop software. The parent
#       has other devices.
#   gnome-remote-desktop
#       An RDP/VNC server. It arrived as a Recommends of gnome-shell. On a
#       machine whose entire premise is that the child cannot reach the
#       network, a service that lets the network reach the machine is the
#       exact inverse of the design.
#   rygel
#       A UPnP/DLNA media server: announces itself on the LAN and serves
#       files. Same provenance, same objection, and kidnix has no media
#       library to share.
#   cups-browsed
#       NOT cups. cups-browsed is the separate daemon that listens for printer
#       announcements on the network and creates queues from them -- the
#       component behind the 2024 CUPS remote-code-execution family
#       (CVE-2024-47076/47175/47176/47177). Printing keeps working without it;
#       what stops working is printers appearing by magic, which a parent can
#       do by hand once in Settings.
#   gnome-tour
#       A slideshow that autostarts on first login to explain GNOME. The
#       parent gets a stock desktop, not a guided tour, and the child must
#       never see it at all.
#   gnome-color-manager
#       Colour-profile calibration tooling for photographers. Nothing here
#       calibrates a display.
#   gnome-backgrounds
#       37.8 MiB of stock wallpaper, ~60% of the entire parent-desktop stage
#       (docs/spikes/parent-desktop.md section 1). Replaced by one kidnix
#       wallpaper in section 3 below.
#
# `dnf5 remove` refuses to break dependencies, so if any of these is load-
# bearing this line fails the build rather than silently gutting GNOME. That
# is why the list is not `--nodeps` and never should be.

REMOVE=(
    firefox
    firefox-langpacks
    gnome-remote-desktop
    rygel
    cups-browsed
    gnome-tour
    gnome-color-manager
    gnome-backgrounds
)

# Only ask for what is actually installed: base images change, and a stage
# that fails because something was ALREADY absent is a stage people delete.
present=()
for pkg in "${REMOVE[@]}"; do
    if rpm -q "${pkg}" >/dev/null 2>&1; then present+=("${pkg}"); fi
done
if (( ${#present[@]} )); then
    log "removing ${#present[@]} packages: ${present[*]}"
    dnf5 -y remove "${present[@]}"
else
    log "nothing to remove (all already absent)"
fi

for pkg in "${REMOVE[@]}" epiphany chromium konqueror falkon midori \
           gnome-user-share gnome-software; do
    ! rpm -q "${pkg}" >/dev/null 2>&1 || die "${pkg} is still installed after the hardening removal"
done

# ...and the things that MUST have survived it. This is the assertion that
# matters: `dnf5 remove` happily takes gdm with gnome-online-accounts, and a
# build that quietly shipped an image with no display manager would pass every
# other test in tests/image/.
for pkg in gdm gnome-shell gnome-session gnome-control-center gnome-kiosk \
           nautilus ptyxis malcontent cups; do
    rpm -q "${pkg}" >/dev/null 2>&1 || die "${pkg} was removed as a dependency; the hardening removal is too aggressive"
done

# -----------------------------------------------------------------------------
# 1b. What rpm leaves behind
# -----------------------------------------------------------------------------

# firefox's %ghost/config dirs survive the erase as empty trees. `rmdir -p`
# would be neater but the tree is three levels of empty directories.
rm -rf /usr/lib64/firefox /usr/lib/firefox /etc/firefox /usr/lib64/mozilla
# cups-browsed's config is %config, so rpm renames rather than deletes it.
rm -f /etc/cups/cups-browsed.conf.rpmsave

# Service accounts outlive their package: rpm's %postun deliberately does not
# call userdel, because a removed package may be reinstalled and files on disk
# may still be owned by that uid. Nothing here will be reinstalled, and an
# account with a home directory that does not exist is exactly what `bootc
# container lint` flags ("/etc/passwd entry without corresponding systemd
# sysusers.d") -- a real finding, since /etc/passwd is 3-way merged and this
# ghost would follow the machine across every future upgrade.
for account in gnome-remote-desktop rygel; do
    if getent passwd "${account}" >/dev/null 2>&1; then
        userdel -f "${account}" >/dev/null 2>&1 || true
        log "removed the leftover ${account} service account"
    fi
    if getent group "${account}" >/dev/null 2>&1; then
        groupdel -f "${account}" >/dev/null 2>&1 || true
    fi
    # userdel(8) leaves /etc/shadow and /etc/gshadow alone in some failure
    # modes; make the outcome the assertion rather than the command.
    sed -i "/^${account}:/d" /etc/shadow /etc/gshadow 2>/dev/null || true
    ! getent passwd "${account}" >/dev/null 2>&1 || die "${account} is still in /etc/passwd"
    ! getent group "${account}" >/dev/null 2>&1 || die "${account} is still in /etc/group"
done

# Fedora's static /usr/share/applications/mimeapps.list still names
# org.mozilla.firefox.desktop as the handler for http, https, text/html and
# xhtml. With firefox gone those are dangling: an activity that calls
# xdg-open("https://...") gets a broken handler instead of nothing, and the
# GNOME "Default Applications" panel shows a browser that is not there.
# Deleting the four lines is the smallest honest fix. It does mean `rpm -V`
# reports mimeapps.list as modified; that is recorded in the spike doc.
for list in /usr/share/applications/mimeapps.list \
            /usr/share/applications/gnome-mimeapps.list; do
    [[ -f "${list}" ]] || continue
    sed -i -E '/^[^=]+=.*(firefox|mozilla)/Id' "${list}"
done
if grep -rilE 'firefox|mozilla' /usr/share/applications/ >/dev/null 2>&1; then
    die "something in /usr/share/applications still references firefox"
fi

# The actual property we care about, stated directly rather than by package
# name: nothing in this image declares itself a web browser.
browsers="$(grep -lE '^(Categories=.*WebBrowser|MimeType=.*x-scheme-handler/https?)' \
    /usr/share/applications/*.desktop 2>/dev/null || true)"
[[ -z "${browsers}" ]] || die "a browser .desktop survived the removal: ${browsers}"
for binary in /usr/bin/firefox /usr/bin/epiphany /usr/bin/chromium-browser \
              /usr/bin/chromium /usr/bin/google-chrome; do
    [[ ! -e "${binary}" ]] || die "${binary} exists; this image is supposed to have no browser"
done

# The Flatpak list is the other way a browser could arrive, on first boot,
# after every test in tests/image/ has already passed.
readonly FLATPAKS=/usr/share/kidnix/flatpaks.txt
if [[ -f "${FLATPAKS}" ]]; then
    if grep -vE '^[[:space:]]*(#|$)' "${FLATPAKS}" \
        | grep -iE 'firefox|chrom|browser|epiphany|webkit' >/dev/null 2>&1; then
        die "${FLATPAKS} lists a browser; see ADR-0005"
    fi
fi

# -----------------------------------------------------------------------------
# 2. Masked units
# -----------------------------------------------------------------------------
#
# `systemctl mask` (a symlink to /dev/null in /etc) rather than removing the
# packages, because most of these units come from packages that also provide
# something we want, and because a mask is one `systemctl unmask` away from
# being undone by a parent who disagrees. Same mechanism 40-lockdown.sh
# already uses for bootc-fetch-apply-updates.timer.
#
# Nothing here is masked because it is "unnecessary". The test is narrower:
# does this unit reach the network on its own schedule, change the machine on
# its own schedule, or exist only to serve software kidnix deliberately does
# not ship?

MASK_UNITS=(
    # --- updates that happen without a grown-up asking for them ---
    # Stages and applies an rpm-ostree update on a timer. kidnix updates are
    # atomic and rollbackable precisely so a family can choose their moment;
    # doing it automatically throws that property away. The parent panel will
    # drive `bootc upgrade`. (bootc-fetch-apply-updates.timer, the bootc-side
    # equivalent that also REBOOTS, is masked by 40-lockdown.sh.)
    rpm-ostreed-automatic.timer
    # Updates every installed Flatpak in the background. A child's activity
    # changing shape mid-session, or a 400 MB download starting on a metered
    # phone hotspot, are both things that must be a decision.
    flatpak-system-update.timer

    # --- unsolicited network traffic ---
    # DNF's "count me" telemetry: a weekly HTTPS request to Fedora's mirrors
    # carrying a coarse age bucket for this machine. It is deliberately
    # privacy-preserving and it is still an unrequested outbound connection
    # from a five-year-old's computer. Non-negotiable 5 is unconditional.
    rpm-ostree-countme.timer
    # Downloads repository metadata on a timer. This image is built from a
    # Containerfile and updated as a whole; nothing on the running machine
    # installs RPMs, so the metadata is only ever bandwidth.
    dnf-makecache.timer
    # Fetches the DNSSEC root trust anchor daily -- for unbound, which is not
    # installed and is not this machine's resolver (systemd-resolved is).
    unbound-anchor.timer

    # --- daemons for hardware and software kidnix does not have ---
    # Probes every serial device at boot looking for a cellular modem, then
    # sits on D-Bus managing WWAN. kidnix targets refurbished laptops on home
    # wifi; NetworkManager handles those without it.
    ModemManager.service
    # Smartcard daemon. No smartcards, and authselect has already disabled
    # smartcard authentication in the greeter (/etc/dconf/db/distro.d).
    pcscd.socket
    # Enterprise identity (LDAP/AD/Kerberos). /etc/nsswitch.conf on this image
    # is `files altfiles systemd` -- `sss` is not in it, so nothing can even
    # consult sssd. It has no config either, so its ConditionPathExists
    # already keeps it from starting; masking it says so out loud.
    sssd.service
    sssd-kcm.socket
    # Rebuilds the AppStream software-catalogue cache at every boot, for the
    # software centre this image deliberately does not have (ADR-0005).
    fedora-atomic-desktop-appstream-cache-refresh.service
)

for unit in "${MASK_UNITS[@]}"; do
    systemctl mask "${unit}" >/dev/null 2>&1 || die "could not mask ${unit}"
    [[ "$(readlink -f "/etc/systemd/system/${unit}")" == /dev/null ]] \
        || die "${unit} did not end up masked"
done
log "masked ${#MASK_UNITS[@]} system units"

# The per-user counterpart of flatpak-system-update.timer. ublue's user preset
# enables it for every account, including the child's -- so without this a
# background Flatpak update runs inside the kid session. `--global` masks it
# for all users at once (/etc/systemd/user/...).
systemctl --global mask flatpak-user-update.timer >/dev/null 2>&1 \
    || die "could not mask the user-level flatpak-user-update.timer"
[[ "$(readlink -f /etc/systemd/user/flatpak-user-update.timer)" == /dev/null ]] \
    || die "flatpak-user-update.timer did not end up masked"

# The other half of the assertion, and the more important one: masking is a
# blunt instrument and this list is edited by people in a hurry. If any of
# these stops being enabled, the machine does not boot into kidnix any more.
for unit in gdm.service NetworkManager.service systemd-resolved.service \
            chronyd.service sshd.service firewalld.service \
            kidnix-egress.service kidnix-boot-report.service \
            kidnix-audio-cap.service greenboot-healthcheck.service \
            flatpak-add-fedora-repos.service; do
    state="$(systemctl is-enabled "${unit}" 2>/dev/null || true)"
    [[ "${state}" == enabled ]] \
        || die "${unit} is '${state}', expected 'enabled' -- a mask above went too far"
done

# sshd stays on and stays reachable (bcvk's `ephemeral ssh` is how
# `just test-boot` gets into the VM), but its surface is trimmed. See the
# drop-in for the whole argument.
readonly SSHD_DROPIN=/etc/ssh/sshd_config.d/10-kidnix.conf
test -f "${SSHD_DROPIN}" || die "${SSHD_DROPIN} is missing from system_files/"
chmod 0600 "${SSHD_DROPIN}"
grep -q '^DenyUsers kid$' "${SSHD_DROPIN}" || die "${SSHD_DROPIN} does not deny the child account"
# `sshd -t` is a real parse of the whole include tree, which is the only way to
# find out that a keyword was misspelled before a machine refuses to start
# sshd on first boot. It insists on a host key, and an image has none (they are
# generated per machine at first boot), so lend it a throwaway one.
if [[ -x /usr/sbin/sshd ]]; then
    ssh-keygen -q -t ed25519 -N '' -f /tmp/kidnix-sshd-test-key
    /usr/sbin/sshd -t -f /etc/ssh/sshd_config -h /tmp/kidnix-sshd-test-key \
        || die "sshd rejects its configuration with the kidnix drop-in"
    rm -f /tmp/kidnix-sshd-test-key /tmp/kidnix-sshd-test-key.pub
    log "sshd config parses with the kidnix drop-in"
fi

# -----------------------------------------------------------------------------
# 3. One wallpaper
# -----------------------------------------------------------------------------
#
# gnome-backgrounds is gone (section 1) and GNOME's compiled-in default
# picture-uri pointed into it, so without the dconf default below a parent's
# first login is a grey rectangle.

readonly WALLPAPER=/usr/share/backgrounds/kidnix/default.png
test -f "${WALLPAPER}" || die "${WALLPAPER} is missing from system_files/"
test -f /usr/share/backgrounds/kidnix/default.svg \
    || die "the wallpaper's SVG source is missing from system_files/"

# A PNG, and the right shape. `file` is not installed in the base image, so
# read the header directly: 8-byte signature, then IHDR's big-endian width and
# height. A truncated or misconverted image is otherwise invisible until a
# human logs in.
png_sig="$(head -c 8 "${WALLPAPER}" | od -An -tx1 | tr -d ' \n')"
[[ "${png_sig}" == "89504e470d0a1a0a" ]] || die "${WALLPAPER} is not a PNG (signature ${png_sig})"
png_w="$(( 0x$(dd if="${WALLPAPER}" bs=1 skip=16 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n') ))"
png_h="$(( 0x$(dd if="${WALLPAPER}" bs=1 skip=20 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n') ))"
(( png_w >= 1920 && png_h >= 1080 )) \
    || die "${WALLPAPER} is ${png_w}x${png_h}; too small for the panels kidnix targets"
log "wallpaper: ${png_w}x${png_h}, $(( $(stat -c %s "${WALLPAPER}") / 1024 )) KiB"

readonly BG_PROPS=/usr/share/gnome-background-properties/kidnix.xml
test -f "${BG_PROPS}" || die "${BG_PROPS} is missing from system_files/"
grep -q "${WALLPAPER}" "${BG_PROPS}" || die "${BG_PROPS} does not point at ${WALLPAPER}"

# The default itself, for the parent's session only. See the keyfile's header
# for why /etc/dconf/db/local.d reaches the parent and cannot reach the child.
readonly BG_KEYFILE=/etc/dconf/db/local.d/10-kidnix-background
test -f "${BG_KEYFILE}" || die "${BG_KEYFILE} is missing from system_files/"
grep -q '^user-db:user$' /etc/dconf/profile/user \
    || die "/etc/dconf/profile/user is not the stock Fedora profile; the background default may not reach the parent"
grep -q '^system-db:local$' /etc/dconf/profile/user \
    || die "/etc/dconf/profile/user does not read system-db:local; ${BG_KEYFILE} would be dead weight"

dconf update || die "dconf update failed; the parent would have no wallpaper default"
test -s /etc/dconf/db/local || die "dconf update produced no /etc/dconf/db/local"

# Read the value back out of the compiled database rather than trusting that
# `dconf update` did what the keyfile said. A profile containing only a
# file-db is enough to read, and needs no D-Bus.
printf 'file-db:/etc/dconf/db/local\n' > /tmp/kidnix-bg-profile
bg_uri="$(DCONF_PROFILE=/tmp/kidnix-bg-profile dconf read /org/gnome/desktop/background/picture-uri)"
rm -f /tmp/kidnix-bg-profile
[[ "${bg_uri}" == "'file://${WALLPAPER}'" ]] \
    || die "the compiled dconf default is ${bg_uri}, expected 'file://${WALLPAPER}'"

# No dconf default we ship may still point into the package that is not in the
# image. Comment lines are skipped on purpose -- the keyfile's own header
# explains what the old default was, and quoting a path is not setting one.
# (GNOME's *compiled-in* schema default still names it; that is upstream's
# file, and overriding it is precisely what the keyfile above is for.)
if grep -rhE '^[[:space:]]*[^#[:space:]].*/usr/share/backgrounds/gnome/' \
        /etc/dconf/db/*.d 2>/dev/null | grep -q .; then
    die "a dconf default still points into the removed gnome-backgrounds"
fi

# -----------------------------------------------------------------------------
# 4. parent.toml
# -----------------------------------------------------------------------------
#
# Two byte-identical copies: /usr/share is the image-owned fallback,
# /etc is the machine's editable copy (3-way merged by bootc).
# kidnix_shell.settings.Paths.parent_config prefers /etc.

readonly PARENT_ETC=/etc/kidnix/parent.toml
readonly PARENT_USR=/usr/share/kidnix/parent.toml

for f in "${PARENT_ETC}" "${PARENT_USR}"; do
    test -f "${f}" || die "${f} is missing from system_files/"
    # World-readable on purpose: the shell runs as `kid` and must be able to
    # READ the PIN hash to check a PIN. Root-owned so the child cannot write
    # it. A PBKDF2 hash is not a secret from the account it protects -- the
    # protection is that 200000 rounds make guessing expensive, not that the
    # hash is hidden.
    chown root:root "${f}"
    chmod 0644 "${f}"
done
cmp -s "${PARENT_ETC}" "${PARENT_USR}" \
    || die "${PARENT_ETC} and ${PARENT_USR} differ; they are meant to ship identical"

# Parse the shipped file THROUGH the shell's own code, which 60-shell.sh has
# already installed into site-packages. This is the only check that actually
# pins the key names: rename a field in settings.py without updating the TOML
# and the build stops here instead of a child meeting a broken grown-up gate.
python3 - "${PARENT_ETC}" <<'PY' || die "the shipped parent.toml does not load through kidnix_shell.settings"
import sys
from pathlib import Path

from kidnix_shell.settings import ParentConfig

path = Path(sys.argv[1])
config = ParentConfig.load(path)

assert config.path == path, f"loaded from {config.path}"

# **THE SHIPPED FILE HAS NO PIN, AND THE SHELL TREATS THAT AS "MUST SET ONE".**
#
# Inverted on 2026-08-23 (spec 7d #11). This used to assert that the shipped
# hash verified 1234 -- which was true, and was the blocker: `is_default` is
# only ever set when NO pin_hash is found, so shipping one suppressed the very
# warning that would have told a parent their gate was open (forum #44, #56).
#
# Both halves are asserted, because either one alone can pass while the gate is
# open: the *file* must carry no hash, and the *shell* must answer that by
# demanding a new PIN before anything else in the grown-up sheet.
raw = path.read_text(encoding="utf-8")
offenders = [
    line
    for line in raw.splitlines()
    if line.strip().startswith(("pin_hash", "pin_salt")) and "=" in line
]
assert not offenders, f"the shipped parent.toml carries a PIN: {offenders}"
assert config.must_set_pin, "the shell does not treat the shipped file as 'no PIN set'"
assert config.is_default, "a file with no PIN must flag is_default so the warning appears"
assert config.default_session_minutes == 25, config.default_session_minutes
# Empty *or* absent both mean "every activity is allowed"
# (ParentConfig.is_allowed); the shipped file states the empty list so a
# parent editing it can see the key. A non-empty one would hide activities.
assert not config.allowed_activity_ids, "shipping a non-empty allow-list hides activities by default"
assert config.is_allowed("tuxpaint"), "the shipped config must allow every installed activity"
assert [p.id for p in config.profiles] == ["child"], [p.id for p in config.profiles]
assert config.profiles[0].name == "Me", config.profiles[0].name
print(f"  -- parent.toml loads: no PIN yet (the gate will ask for one), "
      f"{config.default_session_minutes} min, {len(config.profiles)} profile(s)")
PY

# And report the path the shell will actually take, rather than assuming it.
# Deliberately NOT fatal: which file wins is settings.py's decision, and it is
# being changed under us (docs/spikes/session-integration.md open question 2 --
# the child must be able to *write* a new PIN, and cannot write /etc). Shipping
# both copies is what makes any of its plausible answers work; this line is how
# the build log says which one it picked today.
python3 - <<'PY' || true
from kidnix_shell.settings import Paths

resolved = Paths.from_env({"HOME": "/var/home/kid"}).parent_config
expected = "/etc/kidnix/parent.toml"
note = "" if str(resolved) == expected else f"  (NOTE: not {expected})"
print(f"  -- Paths.parent_config resolves to {resolved}{note}")
PY

# -----------------------------------------------------------------------------
# 5. Report the delta
# -----------------------------------------------------------------------------

size_after="$(rpm -qa --qf '%{SIZE}\n' | awk '{ s += $1 } END { print s + 0 }')"
count_after="$(rpm -qa | wc -l)"

awk -v a="${size_before}" -v b="${size_after}" \
    -v ca="${count_before}" -v cb="${count_after}" \
    'BEGIN { printf "  -- hardening delta: %+d packages, %+.1f MiB installed\n", cb - ca, (b - a) / 1048576 }'

# The audit that docs/spikes/hardening.md section 5 records. Printing it on
# every build is what stops the doc going stale: a new enabled unit appearing
# in a base-image bump is visible in the build log the day it lands.
log "units still enabled after hardening:"
systemctl list-unit-files --state=enabled --no-pager --no-legend 2>/dev/null \
    | awk '{ printf "       %s\n", $1 }' || true

log "hardening done"
