#!/usr/bin/bash
# greenboot REQUIRED check: the child's network lockdown is actually loaded.
#
# docs/research/07-linux-stack.md §2.8 calls this out specifically: "a boot
# where the network lockdown silently failed should be treated as a *failed
# boot* and rolled back." AGENTS.md non-negotiable #5 is not a best-effort
# setting; if it is not in force, this deployment is not kidnix.
set -uo pipefail

readonly RULESET=/usr/lib/kidnix/nftables/kidnix-egress.nft
readonly TABLE='inet kidnix_egress'

if [[ ! -r "${RULESET}" ]]; then
    echo "kidnix: ${RULESET} is missing" >&2
    exit 1
fi

if ! command -v nft >/dev/null 2>&1; then
    echo "kidnix: nft is not installed" >&2
    exit 1
fi

# The file must still parse. This is the `nft -c` the spec asks for, and here
# it runs as root on a real kernel, so no namespace trickery is needed.
if ! nft -c -f "${RULESET}" >/dev/null 2>&1; then
    echo "kidnix: ${RULESET} does not parse" >&2
    nft -c -f "${RULESET}" >&2 || true
    exit 1
fi

# ...and it must be LOADED, not merely valid. Captured rather than piped into
# `grep -q`: with `set -o pipefail`, grep -q exits on its first match, nft takes
# SIGPIPE, and the pipeline reports failure precisely when the rule was found.
# TABLE is deliberately two words (address family + table name), so it must
# stay unquoted here.
# shellcheck disable=SC2086
loaded="$(nft list table ${TABLE} 2>/dev/null || true)"

if [[ -z "${loaded}" ]]; then
    echo "kidnix: table ${TABLE} is not loaded -- the child has network egress" >&2
    systemctl status kidnix-egress.service --no-pager --lines=20 >&2 2>/dev/null || true
    exit 1
fi

# ...and it must still contain a rule that stops uid 1000.
if ! grep -Eq 'skuid 1000 .*(reject|drop)' <<<"${loaded}"; then
    echo "kidnix: table ${TABLE} is loaded but has no reject rule for uid 1000" >&2
    printf '%s\n' "${loaded}" >&2
    exit 1
fi

exit 0
