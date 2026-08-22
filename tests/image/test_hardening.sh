#!/usr/bin/bash
# Static assertions about the hardening pass (build_files/70-hardening.sh).
#
#   just test-image hardening
#   podman run --rm -v ./tests/image:/tests:ro,z --entrypoint /bin/bash \
#       localhost/kidnix:latest /tests/test_hardening.sh
#
# Same shape and helpers as test_image.sh / test_lockdown.sh: runs INSIDE the
# built container, rootless, no VM, a couple of seconds.
#
# What it proves: things that were supposed to leave have left, things that
# were supposed to stay have stayed, the masks resolve to /dev/null, the
# wallpaper is a real image the dconf default actually points at, and the
# shipped parent.toml loads through the shell's own settings code.
#
# What it CANNOT prove, because nothing here is booted: that a masked unit
# stays masked after `systemctl daemon-reload` on a real machine, that GNOME
# renders the wallpaper, or that sshd starts. Those belong to tests/boot/ and
# to docs/spikes/hardening.md section 7.
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

# assert_rpm <name>
assert_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report ok "package $1 is installed"
    else
        _report no "package $1 is installed" "not installed"
    fi
}

# assert_no_rpm <name> <why>
assert_no_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report no "package $1 is absent" "$2"
    else
        _report ok "package $1 is absent ($2)"
    fi
}

# assert_absent <path>
assert_absent() {
    if [[ ! -e "$1" ]]; then _report ok "absent $1"; else _report no "absent $1" "should not exist"; fi
}

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_eq <description> <expected> <actual>
assert_eq() {
    if [[ "$2" == "$3" ]]; then _report ok "$1"; else _report no "$1" "expected '$2', got '$3'"; fi
}

# assert_masked <unit> <why>
assert_masked() {
    local target
    target="$(readlink -f "/etc/systemd/system/$1" 2>/dev/null || true)"
    if [[ "${target}" == /dev/null ]]; then
        _report ok "masked $1 ($2)"
    else
        _report no "masked $1" "$1 points at '${target:-nothing}', expected /dev/null"
    fi
}

# assert_enabled <unit> <why it must stay>
assert_enabled() {
    local state
    state="$(systemctl is-enabled "$1" 2>/dev/null || true)"
    if [[ "${state}" == enabled ]]; then
        _report ok "still enabled: $1 ($2)"
    else
        _report no "still enabled: $1" "is '${state:-unknown}'"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# -----------------------------------------------------------------------------
section "no web browser anywhere in the image"
# -----------------------------------------------------------------------------
# ADR-0005: "no web browser" is a property of the machine, not of the child's
# session. base-main ships Firefox; 70-hardening.sh takes it back out.

assert_no_rpm firefox           "base-main ships it; ADR-0005 removes it (328 MiB)"
assert_no_rpm firefox-langpacks "goes with firefox"
assert_no_rpm epiphany          "GNOME Web is still a web browser"
assert_no_rpm chromium          "so is chromium"
assert_no_rpm yelp              "the help browser embeds a web engine"

assert_absent /usr/bin/firefox
assert_absent /usr/lib64/firefox
assert_absent /usr/share/applications/org.mozilla.firefox.desktop

# The property stated directly rather than by package name: no desktop entry
# in this image claims to be a browser or to handle http(s).
browsers="$(grep -lE '^(Categories=.*WebBrowser|MimeType=.*x-scheme-handler/https?)' \
    /usr/share/applications/*.desktop 2>/dev/null || true)"
assert_eq "no .desktop declares itself a web browser or an http handler" "" "${browsers}"

# Fedora's static mimeapps.list named firefox as the default http handler.
# With firefox gone those lines are dangling and 70-hardening.sh deletes them.
dangling="$(grep -rilE 'firefox|mozilla' /usr/share/applications/ 2>/dev/null || true)"
assert_eq "nothing in /usr/share/applications still names firefox" "" "${dangling}"

# The other way a browser could arrive: on first boot, from Flathub.
flatpak_browsers="$(grep -vE '^[[:space:]]*(#|$)' /usr/share/kidnix/flatpaks.txt 2>/dev/null \
    | grep -icE 'firefox|chrom|browser|epiphany' || true)"
assert_eq "flatpaks.txt lists no browser" "0" "${flatpak_browsers}"

# -----------------------------------------------------------------------------
section "network-facing services that arrived as weak dependencies"
# -----------------------------------------------------------------------------

assert_no_rpm gnome-remote-desktop "an RDP/VNC server on a child's machine"
assert_no_rpm rygel                "a UPnP/DLNA media server that announces itself on the LAN"
assert_no_rpm cups-browsed         "the network printer-discovery daemon behind CVE-2024-4717x"
assert_no_rpm gnome-tour           "a first-login slideshow nobody here wants"
assert_no_rpm gnome-color-manager  "display calibration for photographers"
assert_no_rpm gnome-user-share     "no file sharing out of the child's home"

assert_absent /usr/lib/systemd/system/gnome-remote-desktop.service
assert_absent /usr/lib/systemd/system/cups-browsed.service
assert_absent /etc/cups/cups-browsed.conf.rpmsave

# rpm's %postun does not userdel, so a removed service leaves its account in
# /etc/passwd -- which bootc lint flags, and which /etc's 3-way merge would
# carry across every future upgrade. 70-hardening.sh reaps them.
for account in gnome-remote-desktop rygel; do
    if getent passwd "${account}" >/dev/null 2>&1; then
        _report no "no leftover ${account} account" "still in /etc/passwd"
    else
        _report ok "no leftover ${account} account in /etc/passwd"
    fi
    if grep -q "^${account}:" /etc/shadow 2>/dev/null; then
        _report no "no leftover ${account} entry in /etc/shadow" "still there"
    else
        _report ok "no leftover ${account} entry in /etc/shadow"
    fi
done

# Kept, on purpose, each for a reason recorded in docs/spikes/hardening.md
# section 3. Asserting the KEEPS is what makes the removals reviewable: a
# future "tidy-up" that deletes printing or the boot test's way into the VM
# should fail here, loudly.
assert_rpm cups            # printing is a feature: a child's drawing on paper
assert_rpm avahi           # mDNS, which is how driverless printers are found
assert_rpm openssh-server  # `bcvk ephemeral ssh` is how `just test-boot` works
assert_rpm bluez           # bluetooth mice and keyboards on refurbished laptops

# -----------------------------------------------------------------------------
section "masked units"
# -----------------------------------------------------------------------------

assert_masked rpm-ostreed-automatic.timer   "updates must be a family's decision, not a timer's"
assert_masked flatpak-system-update.timer   "no activity changing shape mid-session"
assert_masked rpm-ostree-countme.timer      "zero telemetry (non-negotiable 5)"
assert_masked dnf-makecache.timer           "nothing on the running machine installs RPMs"
assert_masked unbound-anchor.timer          "unbound is not this machine's resolver"
assert_masked ModemManager.service          "no WWAN; it probes every serial device at boot"
assert_masked pcscd.socket                  "no smartcards"
assert_masked sssd.service                  "no enterprise identity; sss is not in nsswitch"
assert_masked sssd-kcm.socket               "no Kerberos"
assert_masked fedora-atomic-desktop-appstream-cache-refresh.service \
                                            "no software centre to keep a catalogue for"
# 40-lockdown.sh's mask, re-asserted here because it belongs to the same story.
assert_masked bootc-fetch-apply-updates.timer "it reboots the machine to apply updates"

# The user-level one: ublue's user preset enables it for every account,
# including the child's, so without a --global mask a background Flatpak
# update runs inside the kid session.
user_mask="$(readlink -f /etc/systemd/user/flatpak-user-update.timer 2>/dev/null || true)"
assert_eq "flatpak-user-update.timer is masked for every user" "/dev/null" "${user_mask}"

# sss really is absent from nsswitch, which is why masking sssd is safe.
if grep -Eq '^(passwd|group):.*\bsss\b' /etc/nsswitch.conf; then
    _report no "nsswitch does not consult sssd" "sss is in /etc/nsswitch.conf but sssd is masked"
else
    _report ok "nsswitch does not consult sssd (so masking it changes no lookup)"
fi

# -----------------------------------------------------------------------------
section "what the masks must NOT have taken with them"
# -----------------------------------------------------------------------------

assert_enabled gdm.service                  "no display manager, no kidnix"
assert_enabled NetworkManager.service       "the parent has to be able to join wifi"
assert_enabled systemd-resolved.service     "DNS"
assert_enabled chronyd.service              "a wrong clock breaks TLS and the session timer"
assert_enabled firewalld.service            "kidnix-egress coexists with it, it does not replace it"
assert_enabled sshd.service                 "just test-boot reaches the VM over it"
assert_enabled kidnix-egress.service        "the child's no-network rule"
assert_enabled kidnix-audio-cap.service     "the volume ceiling"
assert_enabled kidnix-boot-report.service   "the boot probe"
assert_enabled greenboot-healthcheck.service "rollback on a bad boot"
assert_enabled flatpak-add-fedora-repos.service "adds Flathub, which TurboWarp's first boot needs"
assert_enabled avahi-daemon.service         "printer discovery, deliberately kept"
assert_enabled cups.socket                  "printing, deliberately kept"

# -----------------------------------------------------------------------------
section "sshd is kept, but trimmed"
# -----------------------------------------------------------------------------

assert_file /etc/ssh/sshd_config.d/10-kidnix.conf
assert_grep '^DenyUsers kid$' /etc/ssh/sshd_config.d/10-kidnix.conf \
    "the child's account is not reachable over the network"
assert_grep '^PasswordAuthentication no$' /etc/ssh/sshd_config.d/10-kidnix.conf \
    "key authentication only"
assert_grep '^X11Forwarding no$' /etc/ssh/sshd_config.d/10-kidnix.conf \
    "no X11 forwarding (there is no X on this image)"
# The drop-in only wins because sshd takes the first value it sees and the
# Include is the first line of sshd_config. If that ever stops being true the
# whole file becomes decoration.
assert_grep '^Include /etc/ssh/sshd_config\.d/\*\.conf' /etc/ssh/sshd_config \
    "sshd_config includes the drop-in directory"
first_include="$(grep -nE '^[[:space:]]*[A-Za-z]' /etc/ssh/sshd_config | head -1)"
case "${first_include}" in
    *Include*) _report ok "the drop-in directory is sshd_config's FIRST directive" ;;
    *) _report no "the drop-in directory is sshd_config's FIRST directive" "got '${first_include}'" ;;
esac

# -----------------------------------------------------------------------------
section "one kidnix wallpaper instead of 38 MiB of stock ones"
# -----------------------------------------------------------------------------

assert_no_rpm gnome-backgrounds "37.8 MiB, 60% of the parent desktop's whole cost"
assert_absent /usr/share/backgrounds/gnome/adwaita-l.jxl

assert_file /usr/share/backgrounds/kidnix/default.png
assert_file /usr/share/backgrounds/kidnix/default.svg
assert_file /usr/share/gnome-background-properties/kidnix.xml

sig="$(head -c 8 /usr/share/backgrounds/kidnix/default.png | od -An -tx1 | tr -d ' \n')"
assert_eq "the wallpaper is a real PNG" "89504e470d0a1a0a" "${sig}"

png_w="$(( 0x$(dd if=/usr/share/backgrounds/kidnix/default.png bs=1 skip=16 count=4 \
    2>/dev/null | od -An -tx1 | tr -d ' \n') ))"
png_h="$(( 0x$(dd if=/usr/share/backgrounds/kidnix/default.png bs=1 skip=20 count=4 \
    2>/dev/null | od -An -tx1 | tr -d ' \n') ))"
if (( png_w >= 1920 && png_h >= 1080 )); then
    _report ok "the wallpaper is ${png_w}x${png_h}"
else
    _report no "the wallpaper is big enough" "${png_w}x${png_h}"
fi

# It has to be small, or removing gnome-backgrounds bought nothing.
png_kib="$(( $(stat -c %s /usr/share/backgrounds/kidnix/default.png) / 1024 ))"
if (( png_kib < 1024 )); then
    _report ok "the wallpaper is ${png_kib} KiB (was 37.8 MiB of stock wallpapers)"
else
    _report no "the wallpaper is under 1 MiB" "${png_kib} KiB"
fi

assert_grep '/usr/share/backgrounds/kidnix/default\.png' \
    /usr/share/gnome-background-properties/kidnix.xml \
    "Settings -> Appearance can offer the kidnix wallpaper"

# -----------------------------------------------------------------------------
section "the parent's dconf default points at it"
# -----------------------------------------------------------------------------

assert_file /etc/dconf/db/local.d/10-kidnix-background
assert_grep '^system-db:local$' /etc/dconf/profile/user \
    "the stock user profile reads system-db:local, so the default reaches the parent"

if [[ -s /etc/dconf/db/local ]]; then
    _report ok "the local dconf database was compiled at build time"
else
    _report no "the local dconf database was compiled at build time" "/etc/dconf/db/local is missing or empty"
fi

# Read it back out of the compiled binary rather than trusting the keyfile. A
# profile with only a file-db needs no D-Bus and no writable user database.
profile="$(mktemp)"
printf 'file-db:/etc/dconf/db/local\n' > "${profile}"
bg="$(DCONF_PROFILE="${profile}" dconf read /org/gnome/desktop/background/picture-uri 2>/dev/null || true)"
rm -f "${profile}"
assert_eq "the compiled dconf default is the kidnix wallpaper" \
    "'file:///usr/share/backgrounds/kidnix/default.png'" "${bg}"

# The child must NOT get it from here: their session runs with
# DCONF_PROFILE=kid, whose profile never reads system-db:local.
if grep -q 'system-db:local' /etc/dconf/profile/kid 2>/dev/null; then
    _report no "the kid profile does not read system-db:local" "it does; parent defaults would leak into the kiosk"
else
    _report ok "the kid profile does not read system-db:local (no leak into the kiosk)"
fi

# -----------------------------------------------------------------------------
section "parent.toml ships, in both places, identically"
# -----------------------------------------------------------------------------

assert_file /etc/kidnix/parent.toml
assert_file /usr/share/kidnix/parent.toml

if cmp -s /etc/kidnix/parent.toml /usr/share/kidnix/parent.toml; then
    _report ok "the /etc copy and the /usr/share fallback are identical"
else
    _report no "the /etc copy and the /usr/share fallback are identical" "they differ"
fi

# 0644 root:root: the shell runs as `kid` and must READ the PIN hash to check
# a PIN, but must never be able to rewrite it.
assert_eq "/etc/kidnix/parent.toml is 0644 root:root" "644 root root" \
    "$(stat -c '%a %U %G' /etc/kidnix/parent.toml 2>/dev/null || true)"
assert_eq "/usr/share/kidnix/parent.toml is 0644 root:root" "644 root root" \
    "$(stat -c '%a %U %G' /usr/share/kidnix/parent.toml 2>/dev/null || true)"

# The PIN is a hash, never the PIN.
if grep -Eq '^pin[_a-z]* *= *"?1234"?' /etc/kidnix/parent.toml; then
    _report no "the PIN is stored as a hash, not in the clear" "found a literal 1234"
else
    _report ok "the PIN is stored as a hash, not in the clear"
fi
assert_grep '^pin_salt = "[0-9a-f]{32}"$' /etc/kidnix/parent.toml "pin_salt is a 16-byte hex salt"
assert_grep '^pin_hash = "[0-9a-f]{64}"$' /etc/kidnix/parent.toml "pin_hash is a SHA-256-sized digest"

# The assertion that actually pins the schema: load the shipped file through
# the shell's own code, which 60-shell.sh installed into site-packages.
if python3 - <<'PY' >/dev/null 2>&1
from pathlib import Path

from kidnix_shell.settings import DEFAULT_PIN, ParentConfig

config = ParentConfig.load(Path("/etc/kidnix/parent.toml"))
assert config.check_pin(DEFAULT_PIN)
assert not config.check_pin("0000")
assert config.default_session_minutes == 25
assert config.allowed_activity_ids is None
assert [p.id for p in config.profiles] == ["child"]
PY
then
    _report ok "the shipped parent.toml loads through kidnix_shell.settings and its PIN verifies"
else
    _report no "the shipped parent.toml loads through kidnix_shell.settings and its PIN verifies" \
        "ParentConfig.load rejected it, or the key names have drifted"
fi

# -----------------------------------------------------------------------------
section "the image did not lose anything load-bearing"
# -----------------------------------------------------------------------------

for pkg in gdm gnome-shell gnome-session gnome-control-center gnome-kiosk \
           nautilus ptyxis malcontent; do
    assert_rpm "${pkg}"
done
assert_file /usr/share/wayland-sessions/gnome.desktop
assert_file /usr/share/wayland-sessions/kidnix-shell.desktop

# -----------------------------------------------------------------------------
printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
(( fail == 0 ))
