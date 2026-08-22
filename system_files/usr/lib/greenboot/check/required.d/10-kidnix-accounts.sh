#!/usr/bin/bash
# greenboot REQUIRED check: the two accounts kidnix is built around exist.
#
# Failing a required check marks the boot RED; after GREENBOOT_MAX_BOOT_ATTEMPTS
# (3 by default) GRUB's boot_counter reaches -1 and the bootloader falls back to
# the previous deployment. So only assert things that are (a) structurally
# certain on a good boot and (b) genuinely worth rolling back an update for.
#
# systemd-sysusers creates both accounts on every boot from
# /usr/lib/sysusers.d/kidnix.conf. If that silently stopped working, the child
# could not log in at all -- exactly the "roll this update back" case.
set -uo pipefail

fail=0

for user in kid parent; do
    if ! getent passwd "${user}" >/dev/null 2>&1; then
        echo "kidnix: account '${user}' does not exist" >&2
        fail=1
    fi
done

# The egress rule matches uid 1000 numerically (see
# /usr/lib/kidnix/nftables/kidnix-egress.nft). If sysusers ever handed `kid` a
# different uid -- because an installer created the account first, say -- the
# firewall would be filtering a stranger and the child would have open network.
kid_uid="$(id -u kid 2>/dev/null || echo "")"
if [[ "${kid_uid}" != "1000" ]]; then
    echo "kidnix: kid has uid '${kid_uid}', but the egress ruleset filters uid 1000" >&2
    fail=1
fi

# kid must not have gained admin rights.
#
# The group list is captured first rather than piped into `grep -q`: under
# `set -o pipefail`, grep -q exits on the first match, the upstream command
# takes SIGPIPE, and the pipeline reports failure *because the match
# succeeded*. Capturing sidesteps it.
kid_groups="$(id -nG kid 2>/dev/null || true)"
if grep -qwE 'wheel|sudo|root' <<<"${kid_groups}"; then
    echo "kidnix: kid is in an administrative group (${kid_groups})" >&2
    fail=1
fi

exit "${fail}"
