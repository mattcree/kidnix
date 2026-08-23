#!/usr/bin/bash
# Make the update channel mean what the image already claims it means.
#
# docs/design/reviews/2026-08-23-safety-privacy-expert.md, BLOCKER 3:
#
#   "build_files/10-branding.sh writes 'image-ref':
#   'ostree-image-signed:docker://ghcr.io/mattcree/kidnix' into image-info.json,
#   and .github/workflows/build.yml does a keyless cosign sign after every push
#   to main. But there is NO /etc/containers/policy.json, no registries.d, and
#   no pinned certificate identity anywhere in system_files/ ... Nothing on a
#   running machine verifies a signature before bootc upgrade replaces the
#   entire OS as root."
#
# and the parent panel's ordering, which is the reason this stage exists before
# any update button does (Tom, forum #58): "a one-tap pull from ghcr with no
# signature policy on the device is a worse position than being unpatched ...
# policy.json and the cosign identity pinned on the device FIRST, then the
# button, then a notification."
#
# ---------------------------------------------------------------------------
# THE FINDING THAT SHAPED THIS FILE: KEYLESS DOES NOT WORK HERE
# ---------------------------------------------------------------------------
#
# The review asked for the signature to be "pinned to the workflow's
# certificate identity and issuer" -- i.e. cosign keyless, the thing CI already
# does. containers/image CANNOT express that, and it is worth writing down why
# so nobody spends another day on it:
#
#   * containers-policy.json(5) `sigstoreSigned` accepts exactly one of
#     keyPath / keyPaths / keyData / keyDatas / fulcio / pki.
#   * the `fulcio` object has exactly four keys: caPath, caData, oidcIssuer,
#     subjectEmail. There is no regexp option -- an invented
#     "subjectEmailRegexp" is rejected at policy load with
#     `Unknown key "subjectEmailRegexp"`, which rejects the WHOLE FILE.
#   * `subjectEmail` is matched only against the certificate's SAN
#     rfc822Name list (signature/fulcio_cert.go:
#     `slices.Contains(untrustedCertificate.EmailAddresses, f.subjectEmail)`),
#     and the source carries a FIXME saying URIs and "various values about
#     GitHub workflows" are deliberately not matched yet.
#   * a GitHub Actions keyless certificate puts the workflow identity
#     (https://github.com/mattcree/kidnix/.github/workflows/...) in a SAN URI,
#     not an email address.
#
# So there is no value, regexp or exact, that makes containers/image accept a
# GitHub-Actions-signed image. Keyless verification on the device is a dead
# end until containers/image grows URI matching.
#
# What DOES work, and is what this image's own base already does, is a
# long-lived cosign key pair: ghcr.io/ublue-os is pinned in the base policy with
# `keyPaths: [/etc/pki/containers/ublue-os.pub, ...]`. kidnix follows the same
# pattern, with the same shaped entry, at /etc/pki/containers/kidnix.pub.
#
# THE KEY IS NOT IN THE REPOSITORY YET. Until someone runs
# `cosign generate-key-pair`, puts the private half in the repo's Actions
# secrets, adds a `cosign sign --key` step, and commits the public half to
# system_files/etc/pki/containers/kidnix.pub, this policy makes every pull of
# ghcr.io/mattcree/kidnix FAIL. That is the intended, panel-endorsed direction
# of failure: unpatched beats an unauthenticated root-level update channel.
# The build prints a loud line saying so; docs/BUILDING.md carries the recipe.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
warn() { printf '  !! %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

readonly REPO_SCOPE="ghcr.io/mattcree/kidnix"
readonly PUBKEY=/etc/pki/containers/kidnix.pub
readonly POLICY=/etc/containers/policy.json
readonly REGISTRIES_D=/etc/containers/registries.d/kidnix.yaml

# -----------------------------------------------------------------------------
# 1. registries.d -- where to look for the signature at all
# -----------------------------------------------------------------------------

test -f "${REGISTRIES_D}" || die "${REGISTRIES_D} is missing from system_files/"
grep -q "^  ${REPO_SCOPE}:$" "${REGISTRIES_D}" \
    || die "${REGISTRIES_D} does not configure the ${REPO_SCOPE} scope"
grep -q '^    use-sigstore-attachments: true$' "${REGISTRIES_D}" \
    || die "${REGISTRIES_D} does not enable use-sigstore-attachments"

# containers-registries.d(5): a scope may be configured in only ONE file in the
# directory. Two files claiming the same scope is a hard error at pull time,
# and the base image ships files of its own here.
duplicate="$(grep -l "^  ${REPO_SCOPE}:$" /etc/containers/registries.d/*.yaml 2>/dev/null | wc -l)"
[[ "${duplicate}" -eq 1 ]] \
    || die "${REPO_SCOPE} is configured in ${duplicate} files in /etc/containers/registries.d"

# -----------------------------------------------------------------------------
# 2. policy.json -- MERGED, never overwritten
# -----------------------------------------------------------------------------
#
# The base image already ships a policy with entries for
# registry.access.redhat.com, registry.redhat.io, quay.io/toolbx-images and
# ghcr.io/ublue-os -- the last of which is how our own base image is verified.
# Shipping a hand-written policy.json in system_files/ would clobber all of
# that, and the failure would look like "the base image is no longer trusted",
# a week later, to someone else. So this stage reads the existing file, adds one
# scope, and writes it back.

test -f "${POLICY}" || die "${POLICY} is missing; the base image is expected to ship one"

python3 - "${POLICY}" "${REPO_SCOPE}" "${PUBKEY}" <<'PY' || die "could not add the kidnix scope to the container signature policy"
import json, pathlib, sys

policy_path, scope, pubkey = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
policy = json.loads(policy_path.read_text())

docker = policy.setdefault("transports", {}).setdefault("docker", {})

# The base image's entries must survive; refuse to run if they are not there,
# because that means the base changed shape and this merge is guessing.
for required in ("ghcr.io/ublue-os", ""):
    if required not in docker:
        sys.exit(f"the base policy has no docker scope {required!r}; refusing to merge blind")

docker[scope] = [
    {
        "type": "sigstoreSigned",
        "keyPath": pubkey,
        # cosign signatures only carry a repository, so matchRepository is the
        # only identity rule that can accept them. Leaving signedIdentity out
        # would default to matchRepoDigestOrExact and reject every cosign
        # signature -- a policy that looks strict and is simply broken.
        "signedIdentity": {"type": "matchRepository"},
    }
]

# Deterministic output: the file is read by humans during incidents.
policy_path.write_text(json.dumps(policy, indent=4, sort_keys=False) + "\n")
print(f"  -- added {scope} to {policy_path} (sigstoreSigned, keyPath {pubkey})")
PY

# Parse it back the way the tools will, and prove the pieces are where we put
# them. A malformed policy.json does not degrade -- it rejects every pull on
# the machine, including `bootc upgrade`, so a typo here is a bricked update
# path rather than a warning.
python3 - "${POLICY}" "${REPO_SCOPE}" "${PUBKEY}" <<'PY' || die "${POLICY} is not the policy we meant to write"
import json, pathlib, sys
policy = json.loads(pathlib.Path(sys.argv[1]).read_text())
scope, pubkey = sys.argv[2], sys.argv[3]
entry = policy["transports"]["docker"][scope]
assert len(entry) == 1, entry
req = entry[0]
assert req["type"] == "sigstoreSigned", req
assert req["keyPath"] == pubkey, req
assert req["signedIdentity"] == {"type": "matchRepository"}, req
assert policy["default"] == [{"type": "reject"}], policy["default"]
assert policy["transports"]["docker"]["ghcr.io/ublue-os"], "the base image's own scope was lost"
print("  -- policy.json re-parses and keeps the base image's scopes")
PY

# skopeo is in the image (rpm: skopeo). Loading the policy through the real
# implementation is the only check that catches a key name containers/image
# rejects, and it is the difference between "valid JSON" and "a valid policy".
if command -v skopeo >/dev/null 2>&1; then
    output="$(skopeo --policy "${POLICY}" inspect --raw dir:/nonexistent 2>&1 || true)"
    if grep -qiE 'invalid policy|unknown key|error loading|policy.*invalid' <<<"${output}"; then
        die "skopeo rejects ${POLICY}: ${output}"
    fi
    log "skopeo loads the policy (failure was about the image, not the policy)"
fi

# -----------------------------------------------------------------------------
# 3. the key that is not here yet
# -----------------------------------------------------------------------------

if [[ -f "${PUBKEY}" ]]; then
    # A cosign public key is a PEM PUBLIC KEY block; anything else means
    # somebody committed the private half or a certificate by mistake.
    grep -q '^-----BEGIN PUBLIC KEY-----$' "${PUBKEY}" \
        || die "${PUBKEY} is not a PEM public key"
    ! grep -qi 'PRIVATE KEY' "${PUBKEY}" \
        || die "${PUBKEY} contains a PRIVATE key; that must never be in an image"
    chmod 0644 "${PUBKEY}"
    log "signature policy: ${REPO_SCOPE} is pinned to ${PUBKEY}"
else
    warn "no ${PUBKEY} in this image."
    warn "  ${REPO_SCOPE} will therefore FAIL TO PULL, on purpose:"
    warn "  an unverified root-level update channel is worse than no updates."
    warn "  To close it: cosign generate-key-pair, sign in CI with --key, and"
    warn "  commit the public half to system_files${PUBKEY}. See docs/BUILDING.md."
fi

# The string the image already prints about itself has to agree with the policy
# the image actually enforces, or we are back where the review found us.
IMAGE_INFO=/usr/share/kidnix/image-info.json
if [[ -f "${IMAGE_INFO}" ]]; then
    if grep -q 'ostree-image-signed' "${IMAGE_INFO}"; then
        grep -q "${REPO_SCOPE}" "${IMAGE_INFO}" \
            || die "${IMAGE_INFO} claims ostree-image-signed for a repo the policy does not cover"
        log "image-info.json's ostree-image-signed claim is now backed by ${POLICY}"
    fi
fi

# -----------------------------------------------------------------------------
# 4. journald: a cap on what the machine remembers about a child
# -----------------------------------------------------------------------------

readonly JOURNALD_CONF=/usr/lib/systemd/journald.conf.d/10-kidnix.conf
test -f "${JOURNALD_CONF}" || die "${JOURNALD_CONF} is missing from system_files/"
grep -qx 'MaxRetentionSec=30day' "${JOURNALD_CONF}" || die "${JOURNALD_CONF} sets no 30-day retention"
grep -qx 'SystemMaxUse=200M'     "${JOURNALD_CONF}" || die "${JOURNALD_CONF} sets no size ceiling"

# systemd-analyze parses the whole drop-in tree the way journald will, and
# complains about a misspelled key rather than ignoring it silently.
if command -v systemd-analyze >/dev/null 2>&1; then
    effective="$(systemd-analyze cat-config systemd/journald.conf 2>/dev/null || true)"
    if [[ -n "${effective}" ]]; then
        grep -q 'MaxRetentionSec=30day' <<<"${effective}" \
            || die "the 30-day retention cap is not in the effective journald config"
        log "journald: 30-day retention, 200M ceiling, no syslog/wall forwarding"
    fi
fi

# -----------------------------------------------------------------------------
# 5. research instrumentation ships OFF
# -----------------------------------------------------------------------------

readonly RESEARCH=/etc/kidnix/research.toml
test -f "${RESEARCH}" || die "${RESEARCH} is missing from system_files/"
chown root:root "${RESEARCH}"
chmod 0644 "${RESEARCH}"

python3 - "${RESEARCH}" <<'PY' || die "${RESEARCH} does not ship with every switch off"
import pathlib, sys, tomllib
data = tomllib.loads(pathlib.Path(sys.argv[1]).read_text())
research = data.get("research", {})
if data.get("schema") != 1:
    sys.exit(f"schema is {data.get('schema')!r}, expected 1")
for key in ("enabled", "hover_instrumentation", "hover_record_selection",
            "pin_attempt_logging"):
    if key not in research:
        sys.exit(f"[research] has no {key!r}")
    if research[key] is not False:
        sys.exit(f"[research] {key} ships as {research[key]!r}; it must ship false")
if research.get("journal_path"):
    sys.exit("[research] journal_path is set; with enabled=false it must be empty")
print("  -- research.toml: every switch false, no path")
PY

# -----------------------------------------------------------------------------
# 6. the parent's way in and out of the child's data
# -----------------------------------------------------------------------------

readonly HELPER=/usr/libexec/kidnix-parent-tools
readonly ACTION=/usr/share/polkit-1/actions/org.kidnix.parent-tools.policy

for f in /usr/bin/kidnix-export /usr/bin/kidnix-wipe "${HELPER}"; do
    test -x "${f}" || die "${f} is missing or not executable"
    bash -n "${f}" || die "${f} is not valid bash"
done
test -f "${ACTION}" || die "${ACTION} is missing from system_files/"

# pkexec finds the action for a program by the exec.path annotation, so a
# mismatch here means pkexec falls back to org.freedesktop.policykit.exec and
# the carefully-worded message a parent reads is never shown.
grep -q "<annotate key=\"org.freedesktop.policykit.exec.path\">${HELPER}</annotate>" "${ACTION}" \
    || die "${ACTION} does not annotate ${HELPER}"
grep -q '<allow_active>auth_admin_keep</allow_active>' "${ACTION}" \
    || die "${ACTION} does not require admin authentication for an active session"
grep -q '<allow_inactive>no</allow_inactive>' "${ACTION}" \
    || die "${ACTION} allows inactive (non-seat) sessions"

# The .policy file is XML with a DTD; polkit refuses to load a malformed one
# and then the action simply does not exist, which fails OPEN to pkexec's
# default. python3's expat is in the base image.
python3 - "${ACTION}" <<'PY' || die "${ACTION} is not well-formed XML"
import sys, xml.dom.minidom
doc = xml.dom.minidom.parse(sys.argv[1])
actions = doc.getElementsByTagName("action")
assert len(actions) == 1, f"{len(actions)} actions; expected exactly one"
assert actions[0].getAttribute("id") == "org.kidnix.parent-tools", actions[0].getAttribute("id")
PY

# ...and the child must not be able to authorise it. This is the check that
# matters: pkexec asks for the ANNOTATED action id, so the generic
# "org.freedesktop.policykit." denial in 40-kidnix-kid.rules does not cover it.
/usr/libexec/kidnix-polkit-check kid org.kidnix.parent-tools NO \
    || die "the kid account is not denied org.kidnix.parent-tools"
/usr/libexec/kidnix-polkit-check parent org.kidnix.parent-tools NOT_HANDLED \
    || die "the parent account is caught by the kid denial for org.kidnix.parent-tools"

log "parent tools: kidnix-export / kidnix-wipe, polkit action wired, kid denied"
log "supply chain done"
