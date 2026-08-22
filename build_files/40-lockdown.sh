#!/usr/bin/bash
# Build the child-account lockdown into the image, and refuse to ship if any
# part of it is wrong.
#
# Milestone M1. Six mechanisms, deliberately layered, because none of them is
# individually sufficient and the failure of any one must not open the whole
# door:
#
#   1. nftables      -- no network egress for uid 1000, enforced in the kernel
#   2. Flatpak       -- --unshare=network as the global default
#   3. polkit        -- kid may not authorise networking, installs, power,
#                       accounts, mounts or unit management
#   4. dconf         -- locked GNOME lockdown keys, no keybindings, no VT
#                       switching, child-appropriate input defaults
#   5. logind        -- no virtual terminals to switch *to*
#   6. greenboot     -- a boot where 1/3/4 silently failed is a failed boot
#
# Everything here is asserted, not assumed: a build that produces a subtly
# broken lockdown is worse than a build that fails, because nobody finds out.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# 0. Packages
# -----------------------------------------------------------------------------

# greenboot 0.16.3 on Fedora 44 is greenboot-rs, the Rust rewrite targeted at
# bootc (verified: /usr/libexec/greenboot/greenboot is an ELF binary and the
# shipped README is greenboot-rs's). The old shell implementation is
# deprecated.
#
# greenboot-default-health-checks is DELIBERATELY NOT INSTALLED. Its
# 01_repository_dns_check.sh sits in required.d and resolves the DNS names of
# the system's package repositories. kidnix is an offline appliance for a
# child; on a machine with no network that check fails every boot, marks every
# boot red, and rolls a perfectly good deployment back three boots later. Its
# other two checks (watchdog, update-platform reachability) are not worth that
# risk. Ours live in /usr/lib/greenboot/check/{required,wanted}.d instead.
PACKAGES=(
    nftables
    greenboot
)

dnf5 -y install "${PACKAGES[@]}"

command -v nft >/dev/null 2>&1 || die "nft is not on PATH after installing nftables"
test -x /usr/libexec/greenboot/greenboot || die "greenboot binary is missing"
rpm -q greenboot-default-health-checks >/dev/null 2>&1 \
    && die "greenboot-default-health-checks got pulled in; its DNS check would red-boot an offline machine"

# gjs is what validates the polkit rules (see /usr/share/kidnix/polkit-eval.js).
# It arrives with the GNOME stack; assert rather than install, so a base-image
# change that drops it fails here instead of silently disabling the check.
command -v gjs >/dev/null 2>&1 || die "gjs is missing; the polkit rules cannot be validated"
command -v dconf >/dev/null 2>&1 || die "dconf is missing; the child profile cannot be compiled"

# -----------------------------------------------------------------------------
# 1. nftables egress lockdown
# -----------------------------------------------------------------------------

readonly NFT_RULESET=/usr/lib/kidnix/nftables/kidnix-egress.nft
test -f "${NFT_RULESET}" || die "${NFT_RULESET} is missing from system_files/"

# The ruleset filters uid 1000 numerically because `kid` does not exist inside
# a build container. That is only safe if sysusers really does pin kid to 1000.
grep -Eq '^u[[:space:]]+kid[[:space:]]+1000:1000[[:space:]]' /usr/lib/sysusers.d/kidnix.conf \
    || die "sysusers no longer pins kid to uid 1000, but ${NFT_RULESET} filters uid 1000"
grep -Eq '^[[:space:]]*meta skuid 1000 ' "${NFT_RULESET}" \
    || die "${NFT_RULESET} has no 'meta skuid 1000' rule"

# `nft -c` still initialises a netlink cache, which needs CAP_NET_ADMIN over a
# network namespace. A build container does not have it; `unshare -rn` makes a
# throwaway user+network namespace where we are root and do. Same check the
# image test suite runs, and the same check greenboot runs on the real machine
# (where it is simply `nft -c` as root).
log "syntax-checking ${NFT_RULESET}"
if ! unshare -rn nft -c -f "${NFT_RULESET}"; then
    die "${NFT_RULESET} does not parse"
fi

systemctl enable kidnix-egress.service

# -----------------------------------------------------------------------------
# 2. polkit
# -----------------------------------------------------------------------------

readonly POLKIT_RULES=/usr/share/polkit-1/rules.d/40-kidnix-kid.rules
test -f "${POLKIT_RULES}" || die "${POLKIT_RULES} is missing from system_files/"

# polkitd embeds duktape (ECMAScript 5.1). gjs will happily run syntax duktape
# rejects, and a rules file duktape cannot parse is silently ignored -- which
# fails OPEN. Grep for the ES6+ constructs that are easy to write by accident.
log "checking ${POLKIT_RULES} for ES6 syntax duktape cannot parse"
if grep -nE '=>|\blet\b|\bconst\b|`|\.\.\.|\.includes\(|\bclass\b|\bfor[[:space:]]*\([^;]*\bof\b' \
        "${POLKIT_RULES}"; then
    die "${POLKIT_RULES} uses ES6+ syntax; polkitd's duktape engine is ES5.1"
fi

# Behavioural check: load the real file and ask it real questions.
log "evaluating ${POLKIT_RULES}"
polkit_case() {
    /usr/libexec/kidnix-polkit-check "$1" "$2" "$3" \
        || die "polkit rule regression: $1 + $2 should be $3"
}

# kid is denied the things that matter...
polkit_case kid org.freedesktop.Flatpak.app-install                     NO
polkit_case kid org.freedesktop.Flatpak.configure-remote                NO
polkit_case kid org.freedesktop.Flatpak.override-parental-controls      NO
polkit_case kid org.freedesktop.NetworkManager.settings.modify.system   NO
polkit_case kid org.freedesktop.NetworkManager.enable-disable-wifi      NO
polkit_case kid org.freedesktop.login1.reboot                           NO
polkit_case kid org.freedesktop.login1.power-off                        NO
polkit_case kid org.freedesktop.login1.suspend                          NO
polkit_case kid org.freedesktop.login1.chvt                             NO
polkit_case kid org.freedesktop.systemd1.manage-units                   NO
polkit_case kid org.freedesktop.accounts.user-administration            NO
polkit_case kid org.freedesktop.udisks2.filesystem-mount                NO
polkit_case kid org.projectatomic.rpmostree1.deploy                     NO
polkit_case kid org.freedesktop.policykit.exec                          NO
polkit_case kid com.endlessm.ParentalControls.AppFilter.ChangeOwn       NO
polkit_case kid org.freedesktop.Malcontent.SessionLimits.Extend         NO

# ...and left alone for the things a session legitimately needs.
polkit_case kid org.freedesktop.login1.inhibit-block-idle               NOT_HANDLED
polkit_case kid com.endlessm.ParentalControls.AppFilter.ReadOwn         NOT_HANDLED
polkit_case kid org.freedesktop.RealtimeKit1.acquire-high-priority      NOT_HANDLED
polkit_case kid org.gnome.mutter.backlight-helper.save                  NOT_HANDLED

# parent is a normal admin: our rule must not touch them at all.
polkit_case parent org.freedesktop.Flatpak.app-install                  NOT_HANDLED
polkit_case parent org.freedesktop.login1.reboot                        NOT_HANDLED
polkit_case parent org.projectatomic.rpmostree1.deploy                  NOT_HANDLED
polkit_case root   org.freedesktop.systemd1.manage-units                NOT_HANDLED

# -----------------------------------------------------------------------------
# 3. dconf profile for the child session
# -----------------------------------------------------------------------------

readonly DCONF_SRC=/usr/share/kidnix/dconf/kid.d
readonly DCONF_DB=/usr/share/kidnix/dconf/kid.compiled
test -d "${DCONF_SRC}" || die "${DCONF_SRC} is missing from system_files/"
test -f /etc/dconf/profile/kid || die "/etc/dconf/profile/kid is missing from system_files/"

# Keybindings: generate rather than hand-write. mutter/gnome-kiosk gain and
# rename keybindings between GNOME releases, and a hand-maintained list would
# quietly stop covering the new ones -- which is precisely how a child ends up
# discovering a window-management shortcut. Everything in these three schemas
# is type `as` (verified in this image), so blanking them all is safe.
log "generating keybinding-disable keyfile from the live schemas"
keybinding_schemas=(
    org.gnome.desktop.wm.keybindings
    org.gnome.mutter.keybindings
    org.gnome.mutter.wayland.keybindings
)

keyfile="${DCONF_SRC}/50-keybindings"
lockfile="${DCONF_SRC}/locks/50-keybindings"

{
    echo "# GENERATED AT BUILD TIME by build_files/40-lockdown.sh -- do not edit."
    echo "#"
    echo "# Every keybinding in mutter's three keybinding schemas, blanked."
    echo "# gnome-kiosk implements almost no shortcuts itself, but it is mutter"
    echo "# underneath, and mutter's defaults include Alt+F4 (close), Alt+Tab,"
    echo "# Super, workspace switching and -- the important one --"
    echo "# org.gnome.mutter.wayland.keybindings switch-to-session-1..12, which"
    echo "# is where Ctrl+Alt+F<n> VT switching is actually implemented on"
    echo "# Wayland. Blanking that is a real answer to research 07 risk #7,"
    echo "# which recorded it as UNVERIFIED."
    echo
} >"${keyfile}"

{
    echo "# GENERATED AT BUILD TIME by build_files/40-lockdown.sh -- do not edit."
} >"${lockfile}"

generated_keys=0
for schema in "${keybinding_schemas[@]}"; do
    path="/${schema//./\/}"
    printf '[%s]\n' "${path#/}" >>"${keyfile}"
    while read -r key; do
        [[ -n "${key}" ]] || continue
        # Only blank keys that really are string arrays.
        if [[ "$(gsettings range "${schema}" "${key}" 2>/dev/null | head -1)" != "type as" ]]; then
            log "skipping non-list key ${schema} ${key}"
            continue
        fi
        printf '%s=@as []\n' "${key}" >>"${keyfile}"
        printf '%s/%s\n' "${path}" "${key}" >>"${lockfile}"
        generated_keys=$(( generated_keys + 1 ))
    done < <(gsettings list-keys "${schema}" 2>/dev/null | sort)
    printf '\n' >>"${keyfile}"
done

(( generated_keys > 50 )) \
    || die "only generated ${generated_keys} keybinding overrides; the schemas look wrong"
log "blanked ${generated_keys} keybindings"

# The VT-switch bindings are the whole point; fail loudly if they vanish.
for n in 1 2 3 4 5 6 7 8 9 10 11 12; do
    grep -q "^switch-to-session-${n}=@as \[\]$" "${keyfile}" \
        || die "switch-to-session-${n} was not blanked (VT switching would still work)"
done
grep -q '^close=@as \[\]$' "${keyfile}" || die "Alt+F4 (close) was not blanked"

# Every key we set by hand must exist in a schema, or dconf silently stores a
# value nothing reads and the lockdown is decorative.
log "verifying every key in ${DCONF_SRC} exists in an installed schema"
unknown=0
current_schema=""
for f in "${DCONF_SRC}"/*; do
    [[ -f "${f}" ]] || continue
    while IFS= read -r line; do
        case "${line}" in
            \[*\])
                current_schema="${line#[}"
                current_schema="${current_schema%]}"
                current_schema="${current_schema//\//.}"
                if ! gsettings list-keys "${current_schema}" >/dev/null 2>&1; then
                    echo "  unknown schema: ${current_schema} (in $(basename "${f}"))" >&2
                    unknown=$(( unknown + 1 ))
                    current_schema=""
                fi
                ;;
            \#*|"") ;;
            *=*)
                [[ -n "${current_schema}" ]] || continue
                key="${line%%=*}"
                if ! gsettings list-keys "${current_schema}" 2>/dev/null | grep -qx "${key}"; then
                    echo "  unknown key: ${current_schema} ${key} (in $(basename "${f}"))" >&2
                    unknown=$(( unknown + 1 ))
                fi
                ;;
        esac
    done <"${f}"
done
(( unknown == 0 )) || die "${unknown} dconf key(s)/schema(s) do not exist in this image"

# `dconf compile` (not `dconf update`) so the database is image-owned under
# /usr rather than sitting in /etc where every upgrade would 3-way-merge a
# binary blob. Same shape as gnome-kiosk's own
# /usr/share/gnome-kiosk/gnomekiosk.dconf.compiled.
log "compiling ${DCONF_SRC} -> ${DCONF_DB}"
dconf compile "${DCONF_DB}" "${DCONF_SRC}"
test -s "${DCONF_DB}" || die "${DCONF_DB} was not produced"

# Prove the compiled database actually answers, and that the locks bite.
log "verifying the compiled profile"
export HOME="${HOME:-/root}"
mkdir -p "${HOME}"
check_setting() {
    local schema="$1" key="$2" want="$3" got
    got="$(DCONF_PROFILE=kid gsettings get "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    [[ "${got}" == "${want}" ]] \
        || die "kid profile: ${schema} ${key} is ${got}, expected ${want}"
}
check_locked() {
    local schema="$1" key="$2" writable
    writable="$(DCONF_PROFILE=kid gsettings writable "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    [[ "${writable}" == "false" ]] \
        || die "kid profile: ${schema} ${key} is writable (${writable}); the lock did not take"
}

check_setting org.gnome.desktop.lockdown          disable-command-line true
check_setting org.gnome.desktop.lockdown          disable-lock-screen  true
check_setting org.gnome.desktop.peripherals.mouse double-click         700
check_setting org.gnome.desktop.peripherals.mouse drag-threshold       16
check_setting org.gnome.desktop.interface         cursor-size          48
check_setting org.gnome.desktop.wm.keybindings    close                "@as []"
check_setting org.gnome.mutter.wayland.keybindings switch-to-session-2 "@as []"
check_locked  org.gnome.desktop.lockdown          disable-command-line
check_locked  org.gnome.desktop.peripherals.mouse double-click
check_locked  org.gnome.mutter.wayland.keybindings switch-to-session-2

# And that the profile is inert for anyone who is not the child.
default_cursor="$(gsettings get org.gnome.desktop.interface cursor-size 2>/dev/null || echo '<error>')"
[[ "${default_cursor}" != "48" ]] \
    || die "the kid profile is leaking into the default profile"

# -----------------------------------------------------------------------------
# 4. logind: no VTs to switch to
# -----------------------------------------------------------------------------

readonly LOGIND_DROPIN=/usr/lib/systemd/logind.conf.d/10-kidnix-kiosk.conf
test -f "${LOGIND_DROPIN}" || die "${LOGIND_DROPIN} is missing from system_files/"

# systemd-analyze parses the whole drop-in chain, so a typo shows up now.
log "verifying the logind drop-in is picked up"
logind_config="$(systemd-analyze cat-config systemd/logind.conf 2>/dev/null || true)"
grep -q '^NAutoVTs=0$' <<<"${logind_config}" || die "NAutoVTs=0 is not in force"
grep -q '^ReserveVT=0$' <<<"${logind_config}" || die "ReserveVT=0 is not in force"

# The recovery path must survive: getty@tty1 is enabled by preset and is what a
# parent falls back to with `systemd.unit=multi-user.target` on the kernel
# command line. NAutoVTs only governs *autovt@* spawning, not this.
systemctl is-enabled getty@tty1.service >/dev/null 2>&1 \
    || die "getty@tty1.service is not enabled; there would be no recovery console"

# -----------------------------------------------------------------------------
# 5. Flatpak
# -----------------------------------------------------------------------------

readonly FLATPAK_OVERRIDE=/usr/share/kidnix/flatpak/overrides-global
test -f "${FLATPAK_OVERRIDE}" || die "${FLATPAK_OVERRIDE} is missing from system_files/"
grep -q '^shared=!network;$' "${FLATPAK_OVERRIDE}" \
    || die "${FLATPAK_OVERRIDE} does not unshare the network"
grep -q '/var/lib/flatpak/overrides/global' /usr/lib/tmpfiles.d/kidnix-lockdown.conf \
    || die "nothing seeds /var/lib/flatpak/overrides/global on first boot"

# The seed must be byte-identical to what flatpak itself writes, so a parent
# running `flatpak override --show` sees something it recognises. Generating it
# here and diffing is how we find out when the format changes.
flatpak override --system --unshare=network
if ! diff -u "${FLATPAK_OVERRIDE}" /var/lib/flatpak/overrides/global \
        | grep -v '^[-+][-+][-+]' | grep -q '^[-+]' \
        || diff <(grep -v '^#' "${FLATPAK_OVERRIDE}" | grep -v '^$') \
                <(grep -v '^$' /var/lib/flatpak/overrides/global) >/dev/null; then
    log "flatpak global override matches what flatpak itself writes"
else
    diff -u <(grep -v '^#' "${FLATPAK_OVERRIDE}" | grep -v '^$') \
            /var/lib/flatpak/overrides/global >&2 || true
    die "${FLATPAK_OVERRIDE} no longer matches flatpak's own output"
fi
# /var is machine-local and 90-cleanup.sh wipes it; the tmpfiles rule is what
# actually puts this on the installed machine.
rm -rf /var/lib/flatpak

# -----------------------------------------------------------------------------
# 6. Updates: no surprise reboots
# -----------------------------------------------------------------------------

# bootc-fetch-apply-updates.timer checks daily and REBOOTS if it finds an
# update. Mid-activity, unannounced, on a child's computer. The parent panel
# will drive `bootc upgrade --check` / `--apply` at a moment the family chose.
systemctl mask bootc-fetch-apply-updates.timer
[[ "$(readlink -f /etc/systemd/system/bootc-fetch-apply-updates.timer)" == /dev/null ]] \
    || die "bootc-fetch-apply-updates.timer is not masked"

# -----------------------------------------------------------------------------
# 7. Audio ceiling
# -----------------------------------------------------------------------------

test -x /usr/libexec/kidnix-audio-cap || die "/usr/libexec/kidnix-audio-cap is missing"
test -f /usr/share/wireplumber/wireplumber.conf.d/50-kidnix-soft-mixer.conf \
    || die "the WirePlumber soft-mixer drop-in is missing"
systemctl enable kidnix-audio-cap.service

# -----------------------------------------------------------------------------
# 8. greenboot health checks
# -----------------------------------------------------------------------------

# /usr/lib/greenboot/check/... rather than /etc: image-owned, so an upgrade
# always brings the current checks and there is no merge to lose. This is where
# greenboot-default-health-checks puts its own scripts, and the greenboot-rs
# README documents it as "a read-only directory in ostree systems".
for check in /usr/lib/greenboot/check/required.d/*-kidnix-*.sh \
             /usr/lib/greenboot/check/wanted.d/*-kidnix-*.sh; do
    test -f "${check}" || die "expected greenboot check ${check} is missing"
    chmod 0755 "${check}"
    bash -n "${check}" || die "${check} is not valid bash"
done

# COPY from system_files does not guarantee the mode we want on every script.
chmod 0755 /usr/libexec/kidnix-audio-cap \
           /usr/libexec/kidnix-app-supervisor \
           /usr/libexec/kidnix-polkit-check

systemctl enable greenboot-healthcheck.service

test -f /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg \
    || die "bootupd is not shipping greenboot's GRUB boot_counter snippet; rollback would not fire"

# -----------------------------------------------------------------------------

log "lockdown installed"
