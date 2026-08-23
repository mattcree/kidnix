#!/usr/bin/bash
# The four privacy/supply-chain blockers, asserted in the built image.
#
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_supply_chain.sh
#
# All four come out of docs/design/reviews/2026-08-23-safety-privacy-expert.md:
#
#   BLOCKER 3  the update channel says "ostree-image-signed" and nothing on the
#              machine verifies a signature       -> policy.json + registries.d
#   MAJOR      the journal keeps a timestamped trace of a five-year-old's
#              pointer for the life of the disk   -> journald retention cap
#   MAJOR      research instrumentation ships on  -> /etc/kidnix/research.toml
#   BLOCKER 1  the child's data has no exit       -> kidnix-export / kidnix-wipe
#
# WHAT THIS FILE CANNOT PROVE, and where it is proved instead: that an unsigned
# image is actually REFUSED. That needs a registry, a real pull and therefore a
# VM -- see docs/spikes/panel-wave-c.md §6a for the exact commands. What is
# provable here is that the policy exists, parses through skopeo's own loader,
# names the right repository and the right key, keeps the base image's own
# scopes, and is not the permissive default.
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

assert_file() { if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi; }
assert_exec() { if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi; }

assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then _report ok "$3"; else _report no "$3" "no match for /$1/ in $2"; fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local description="$1"; shift
    local output
    if output="$("$@" 2>&1)"; then
        _report ok "${description}${output:+ (${output})}"
    else
        _report no "${description}" "${output}"
    fi
}

# assert_py <description> <python source>
assert_py() {
    local description="$1" source="$2" output
    if output="$(python3 -c "${source}" 2>&1)"; then
        _report ok "${description}${output:+ (${output})}"
    else
        _report no "${description}" "${output}"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

readonly POLICY=/etc/containers/policy.json
readonly SCOPE=ghcr.io/mattcree/kidnix
readonly PUBKEY=/etc/pki/containers/kidnix.pub

# -----------------------------------------------------------------------------

section "the update channel: a signature policy that names kidnix"
assert_file "${POLICY}"
assert_file /etc/containers/registries.d/kidnix.yaml
assert_grep '^    use-sigstore-attachments: true$' /etc/containers/registries.d/kidnix.yaml \
    "sigstore attachments are looked for at all (off by default, per containers-registries.d(5))"

assert_py "policy.json is valid JSON and defaults to reject" "
import json, sys
p = json.load(open('${POLICY}'))
if p.get('default') != [{'type': 'reject'}]:
    sys.exit(f\"default is {p.get('default')}\")
"
assert_py "the ${SCOPE} scope requires a sigstore signature" "
import json, sys
p = json.load(open('${POLICY}'))
e = p['transports']['docker'].get('${SCOPE}')
if not e: sys.exit('no scope for ${SCOPE}')
if len(e) != 1: sys.exit(f'{len(e)} requirements, expected 1')
r = e[0]
if r['type'] != 'sigstoreSigned': sys.exit(f\"type {r['type']!r}\")
if r.get('keyPath') != '${PUBKEY}': sys.exit(f\"keyPath {r.get('keyPath')!r}\")
# cosign signatures carry only a repository, so matchRepository is the only
# identity rule that can accept them; the DEFAULT (matchRepoDigestOrExact)
# would reject every one and look strict while being simply broken.
if r.get('signedIdentity') != {'type': 'matchRepository'}:
    sys.exit(f\"signedIdentity {r.get('signedIdentity')!r}\")
print('sigstoreSigned + matchRepository')
"
assert_py "adding our scope did not clobber the base image's own scopes" "
import json, sys
d = json.load(open('${POLICY}'))['transports']['docker']
for scope in ('ghcr.io/ublue-os', 'registry.access.redhat.com', 'quay.io/toolbx-images'):
    if scope not in d: sys.exit(f'lost {scope}')
print(f'{len(d)} docker scopes')
"
# The real implementation, not our reading of it: skopeo loads the policy
# through containers/image, which rejects an unknown key by refusing the whole
# file -- and a refused policy.json rejects every pull on the machine,
# including bootc upgrade.
if command -v skopeo >/dev/null 2>&1; then
    output="$(skopeo --policy "${POLICY}" inspect --raw dir:/nonexistent 2>&1 || true)"
    if grep -qiE 'invalid policy|unknown key|error loading' <<<"${output}"; then
        _report no "skopeo's own loader accepts the policy" "${output}"
    else
        _report ok "skopeo's own loader accepts the policy"
    fi
fi

# The public key is expected to be ABSENT until someone runs cosign
# generate-key-pair and wires CI (docs/BUILDING.md). Absent means pulls of
# ${SCOPE} fail closed, which is the intended state -- the parent panel's
# ordering was "policy first, update button second". This is reported either
# way rather than asserted, because both states are correct at different times.
if [[ -f "${PUBKEY}" ]]; then
    if grep -q '^-----BEGIN PUBLIC KEY-----$' "${PUBKEY}" && ! grep -qi 'PRIVATE KEY' "${PUBKEY}"; then
        _report ok "${PUBKEY} is a PEM public key (updates can be verified)"
    else
        _report no "${PUBKEY} is a PEM public key" "wrong contents -- a private key must never ship"
    fi
else
    printf '  \033[33mNOTE\033[0m  %s\n' \
        "${PUBKEY} is absent: ${SCOPE} will refuse to pull. Intended until CI signs with a key."
fi

# The claim and the enforcement have to agree; the review found them disagreeing.
if grep -q 'ostree-image-signed' /usr/share/kidnix/image-info.json 2>/dev/null; then
    assert_grep "${SCOPE}" /usr/share/kidnix/image-info.json \
        "image-info.json's ostree-image-signed claim names the repo the policy covers"
fi

section "journald: a cap on what the machine remembers about a child"
assert_file /usr/lib/systemd/journald.conf.d/10-kidnix.conf
assert_grep '^MaxRetentionSec=30day$' /usr/lib/systemd/journald.conf.d/10-kidnix.conf \
    "nothing about a session survives 30 days"
assert_grep '^SystemMaxUse=200M$' /usr/lib/systemd/journald.conf.d/10-kidnix.conf \
    "the journal cannot grow past 200M"
assert_grep '^ForwardToSyslog=no$' /usr/lib/systemd/journald.conf.d/10-kidnix.conf \
    "no second copy in a syslog daemon with its own retention"
if command -v systemd-analyze >/dev/null 2>&1; then
    assert_cmd "the cap is in the EFFECTIVE journald config, not just in a file" \
        bash -c "systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -q '^MaxRetentionSec=30day$'"
fi

section "research instrumentation ships off"
assert_file /etc/kidnix/research.toml
assert_py "every switch in research.toml is false and no path is set" "
import sys, tomllib
d = tomllib.load(open('/etc/kidnix/research.toml','rb'))
r = d['research']
on = [k for k, v in r.items() if v is True]
if on: sys.exit(f'these ship ON: {on}')
if r.get('journal_path'): sys.exit('journal_path is set')
print(f\"{len([k for k,v in r.items() if v is False])} switches, all false\")
"
assert_cmd "research.toml is root-owned and not writable by the child" \
    bash -c "[[ \$(stat -c '%U %a' /etc/kidnix/research.toml) == 'root 644' ]]"

section "the parent's way in and out of the child's data"
assert_exec /usr/bin/kidnix-export
assert_exec /usr/bin/kidnix-wipe
assert_exec /usr/libexec/kidnix-parent-tools
for script in /usr/bin/kidnix-export /usr/bin/kidnix-wipe /usr/libexec/kidnix-parent-tools; do
    assert_cmd "${script} is valid bash" bash -n "${script}"
done
assert_cmd "the helper refuses to do anything without a subcommand" \
    bash -c "! /usr/libexec/kidnix-parent-tools >/dev/null 2>&1"
# Running as a non-root user with no polkit agent must fail cleanly rather than
# silently doing half a job.
assert_cmd "the helper refuses to run unprivileged" \
    bash -c "! runuser -u nobody -- /usr/libexec/kidnix-parent-tools export /tmp >/dev/null 2>&1"

assert_file /usr/share/polkit-1/actions/org.kidnix.parent-tools.policy
assert_py "the polkit action is well-formed and annotates the helper" "
import sys, xml.dom.minidom
doc = xml.dom.minidom.parse('/usr/share/polkit-1/actions/org.kidnix.parent-tools.policy')
a = doc.getElementsByTagName('action')
if len(a) != 1: sys.exit(f'{len(a)} actions')
if a[0].getAttribute('id') != 'org.kidnix.parent-tools': sys.exit(a[0].getAttribute('id'))
notes = {n.getAttribute('key'): n.firstChild.data for n in a[0].getElementsByTagName('annotate')}
# pkexec finds an action for a program by this annotation; a mismatch means it
# falls back to org.freedesktop.policykit.exec and the parent never sees the
# message this file carefully words.
if notes.get('org.freedesktop.policykit.exec.path') != '/usr/libexec/kidnix-parent-tools':
    sys.exit(f'annotated path is {notes.get(\"org.freedesktop.policykit.exec.path\")!r}')
print(a[0].getAttribute('id'))
"
assert_grep '<allow_active>auth_admin_keep</allow_active>' \
    /usr/share/polkit-1/actions/org.kidnix.parent-tools.policy \
    "a grown-up at the machine must type their own password"
assert_grep '<allow_inactive>no</allow_inactive>' \
    /usr/share/polkit-1/actions/org.kidnix.parent-tools.policy \
    "not available to a session with no seat"

# The one that matters: pkexec asks for the ANNOTATED action id, so the generic
# "org.freedesktop.policykit." denial in the kid rules does not cover this.
assert_cmd "the child may not authorise kidnix-export or kidnix-wipe" \
    /usr/libexec/kidnix-polkit-check kid org.kidnix.parent-tools NO
assert_cmd "the parent is not caught by the child's denial" \
    /usr/libexec/kidnix-polkit-check parent org.kidnix.parent-tools NOT_HANDLED

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
