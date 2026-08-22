#!/usr/bin/bash
# The licence gate. AGENTS.md §5: "Bundled content/fonts/voices must be
# redistributable; record licences."
#
#   just licenses          # full run, with docs/LICENSES.md mounted
#   just test-image licen   # the in-image half only
#
# kidnix ships as one OS image, so everything inside it is something we
# REDISTRIBUTE. Two populations, checked differently:
#
#   RPM content   -- Fedora's licensing policy already forbids non-redistributable
#                    packages in the main repositories, and every package carries
#                    a %{LICENSE}. We screen those against a denylist rather than
#                    re-audit 1,600 packages.
#   vendored content -- the downloads build_files/ makes by hand (Piper, the
#                    voice models, the GCompris .rcc bundles). Nothing but us
#                    records where these came from, so they get a manifest:
#                    /usr/share/kidnix/THIRD-PARTY.tsv, cross-checked here
#                    against the filesystem and against docs/LICENSES.md.
#
# docs/LICENSES.md open question #4 ("this table is hand-maintained, which means
# it will drift") is what this file closes.
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

ok() { _report ok "$1"; }
no() { _report no "$1" "${2:-}"; }
note() { printf '  \033[33mNOTE\033[0m  %s\n' "$1"; }
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

readonly MANIFEST=/usr/share/kidnix/THIRD-PARTY.tsv
# Mounted by `just licenses`; absent under a plain `just test-image`, where the
# repository is not in the container.
readonly LEDGER=/docs/LICENSES.md

# Licences that may never appear anywhere in the image. "NonCommercial" is the
# one that actually bites: docs/LICENSES.md §6 records that the `semaine` Piper
# voice was rejected for being CC-BY-NC-SA-4.0, and nothing should be able to
# reintroduce that class of asset without this test going red.
readonly DENY_RE='NonCommercial|CC-BY-NC|CC BY-NC|-NC-|Proprietary|Commercial use prohibited|Redistributable, no modification permitted, no commercial'

# Known, reviewed exceptions to the denylist scan. Each needs a reason.
#
#   LicenseRef-Callaway-Redistributable-no-modification-permitted
#       Fedora's tag for hardware firmware blobs (linux-firmware and the
#       per-vendor splits). Redistribution IS permitted -- that is the whole
#       point of the tag -- only modification is not, which costs us nothing
#       because we ship them byte-for-byte. Without them a laptop has no Wi-Fi
#       and no GPU, so this is not a removable dependency.
readonly ALLOWED_LICENSE_REFS=(
    "LicenseRef-Callaway-Redistributable-no-modification-permitted"
)

# Licences a manifest row is allowed to declare. A new one is a decision, so it
# gets made in a review rather than in a download.
readonly ALLOWED_MANIFEST_LICENCES=(
    MIT Apache-2.0 BSD-3-Clause OFL-1.1
    CC-BY-SA-4.0 CC-BY-4.0 CC0-1.0 public-domain
    GPL-2.0-or-later GPL-3.0-or-later LGPL-2.1-or-later AGPL-3.0-only
)

# Trees that hold vendored, non-RPM content. Anything here without a manifest
# row is an unrecorded redistribution, which is the failure this whole file
# exists to catch.
readonly VENDORED_TREES=(
    /usr/lib/kidnix/piper
    /usr/share/kidnix/voices
    /usr/share/gcompris-qt/rcc/data3
    /usr/share/backgrounds/kidnix
)

printf '\033[1mkidnix licence gate\033[0m -- %s\n' "$(sed -n 's/^PRETTY_NAME="\(.*\)"$/\1/p' /usr/lib/os-release)"

# -----------------------------------------------------------------------------
section "1. the manifest itself"
# -----------------------------------------------------------------------------

if [[ -f "${MANIFEST}" ]]; then
    ok "the image ships ${MANIFEST}"
else
    no "the image ships ${MANIFEST}" \
        "missing -- if system_files/ has it, the image predates it: run 'just build'"
    printf '\n\033[1m==> %d passed, %d failed\033[0m\n' "${pass}" "$(( fail ))"
    exit 1
fi

# Rows, with comments and blanks dropped. Everything below reads this.
mapfile -t rows < <(grep -vE '^[[:space:]]*(#|$)' "${MANIFEST}")

if (( ${#rows[@]} >= 10 )); then
    ok "the manifest has ${#rows[@]} rows"
else
    no "the manifest has rows" "only ${#rows[@]}; the vendored tree is bigger than that"
fi

malformed=()
for row in "${rows[@]}"; do
    IFS=$'\t' read -r path licence source origin <<<"${row}"
    if [[ -z "${path}" || -z "${licence}" || -z "${source}" || -z "${origin}" \
          || "${path}" != /* || "${source}" != http* ]]; then
        malformed+=("${row}")
    fi
done
if (( ${#malformed[@]} == 0 )); then
    ok "every row is path<TAB>licence<TAB>source<TAB>origin, absolute path, URL source"
else
    no "every row is well-formed" "${#malformed[@]} bad row(s): ${malformed[0]}"
fi

# -----------------------------------------------------------------------------
section "2. the manifest agrees with the filesystem"
# -----------------------------------------------------------------------------

missing_files=()
while IFS=$'\t' read -r path _licence _source _origin; do
    [[ -e "${path}" ]] || missing_files+=("${path}")
done < <(printf '%s\n' "${rows[@]}")
if (( ${#missing_files[@]} == 0 )); then
    ok "every manifest path exists in the image (${#rows[@]} files)"
else
    no "every manifest path exists in the image" \
        "${#missing_files[@]} missing: ${missing_files[*]:0:3}"
fi

# ...and the harder direction. A download that forgets its row is exactly the
# drift docs/LICENSES.md open question #4 predicted.
unrecorded=()
for tree in "${VENDORED_TREES[@]}"; do
    [[ -d "${tree}" ]] || continue
    while read -r found; do
        # Symlinks are aliases for a file that has its own row (the piper
        # sonames), and `Contents` is an index this build writes itself.
        [[ -L "${found}" ]] && continue
        [[ "${found##*/}" == "Contents" ]] && continue
        grep -qF "${found}"$'\t' "${MANIFEST}" || unrecorded+=("${found}")
    done < <(find "${tree}" -type f -o -type l | sort)
done
if (( ${#unrecorded[@]} == 0 )); then
    ok "no vendored file is missing from the manifest (${#VENDORED_TREES[@]} trees swept)"
else
    no "no vendored file is missing from the manifest" \
        "${#unrecorded[@]} unrecorded: ${unrecorded[*]:0:3}"
fi

# A row for an RPM-owned file means we are recording something Fedora already
# records, which is how a manifest becomes noise nobody reads.
double_recorded=()
while IFS=$'\t' read -r path _licence _source origin; do
    [[ "${origin}" == vendored ]] || continue
    rpm -qf "${path}" >/dev/null 2>&1 && double_recorded+=("${path}")
done < <(printf '%s\n' "${rows[@]}")
if (( ${#double_recorded[@]} == 0 )); then
    ok "no vendored row duplicates a file an RPM already owns"
else
    no "no vendored row duplicates a file an RPM already owns" "${double_recorded[*]:0:3}"
fi

# -----------------------------------------------------------------------------
section "3. the licences themselves"
# -----------------------------------------------------------------------------

bad_manifest_licence=()
while IFS=$'\t' read -r path licence _source _origin; do
    allowed=no
    for candidate in "${ALLOWED_MANIFEST_LICENCES[@]}"; do
        [[ "${licence}" == "${candidate}" ]] && allowed=yes
    done
    [[ "${allowed}" == yes ]] || bad_manifest_licence+=("${path}=${licence}")
done < <(printf '%s\n' "${rows[@]}")
if (( ${#bad_manifest_licence[@]} == 0 )); then
    ok "every manifest licence is on the reviewed allow-list"
else
    no "every manifest licence is on the reviewed allow-list" "${bad_manifest_licence[*]:0:3}"
fi

if grep -qEi "${DENY_RE}" "${MANIFEST}"; then
    no "no manifest row is non-commercial or proprietary" \
        "$(grep -Ei "${DENY_RE}" "${MANIFEST}" | head -1)"
else
    ok "no manifest row is non-commercial or proprietary"
fi

# The RPM population. `sort -u` over ~1,600 packages is ~450 distinct strings.
mapfile -t rpm_licences < <(rpm -qa --qf '%{LICENSE}\n' | sort -u)
printf '  ...  %d distinct RPM licence strings across %d packages\n' \
    "${#rpm_licences[@]}" "$(rpm -qa | wc -l)"

offending=()
for licence in "${rpm_licences[@]}"; do
    grep -qEi "${DENY_RE}" <<<"${licence}" || continue
    allowed=no
    for ref in "${ALLOWED_LICENSE_REFS[@]}"; do
        [[ "${licence}" == *"${ref}"* ]] && allowed=yes
    done
    [[ "${allowed}" == yes ]] || offending+=("${licence}")
done
if (( ${#offending[@]} == 0 )); then
    ok "no RPM licence is non-commercial or proprietary (denylist, ${#ALLOWED_LICENSE_REFS[@]} reviewed exception(s))"
else
    no "no RPM licence is non-commercial or proprietary" "${offending[*]:0:2}"
    for licence in "${offending[@]}"; do
        printf '         %s: %s\n' "${licence}" \
            "$(rpm -qa --qf '%{NAME} %{LICENSE}\n' | awk -v l="${licence}" '$0 ~ l {printf "%s ", $1}')"
    done
fi

# The exceptions must still be real. An allow-list entry nothing matches is a
# stale entry, and a stale allow-list is how the next one gets waved through.
# NOT `printf ... | grep -qF`: under `set -o pipefail`, grep -q exits the instant
# it matches, printf takes SIGPIPE, and the pipeline reports failure BECAUSE the
# string was found. Same trap build_files/40-lockdown.sh documents.
stale=()
for ref in "${ALLOWED_LICENSE_REFS[@]}"; do
    seen=no
    for licence in "${rpm_licences[@]}"; do
        [[ "${licence}" == *"${ref}"* ]] && { seen=yes; break; }
    done
    [[ "${seen}" == yes ]] || stale+=("${ref}")
done
if (( ${#stale[@]} == 0 )); then
    ok "every allow-listed licence exception still matches a real package"
else
    no "every allow-listed licence exception still matches a real package" \
        "unused, delete them: ${stale[*]}"
fi

# -----------------------------------------------------------------------------
section "4. the obligations we took on, and the one we refused"
# -----------------------------------------------------------------------------

# Piper is "yes, with notice": MIT, so we must carry the licence text ourselves
# because no RPM does it for us.
for text in LICENSE.piper.md LICENSE.piper-phonemize.md LICENSE.onnxruntime; do
    if [[ -s "/usr/share/licenses/kidnix-piper/${text}" ]]; then
        ok "the vendored MIT text ships: /usr/share/licenses/kidnix-piper/${text}"
    else
        no "the vendored MIT text ships: /usr/share/licenses/kidnix-piper/${text}" "missing or empty"
    fi
done

# The voice licence is stated in the model's own card and nowhere else, so the
# card is the evidence and it has to travel with the model.
for card in /usr/share/kidnix/voices/*.MODEL_CARD; do
    [[ -s "${card}" ]] || continue
    if grep -qi 'public domain' "${card}"; then
        ok "$(basename "${card}") still states public domain"
    else
        no "$(basename "${card}") still states public domain" "$(head -3 "${card}" | tr '\n' ' ')"
    fi
done

# docs/LICENSES.md §6: upstream's piper tarball bundles a prebuilt GPL-3.0
# espeak-ng, and shipping someone else's prebuilt GPL binary means owing its
# corresponding source. build_files/65-tts.sh deletes it. If it ever comes back,
# kidnix has silently acquired a source-distribution obligation.
gpl_leak=()
for candidate in /usr/lib/kidnix/piper/libespeak-ng.so* /usr/lib/kidnix/piper/espeak-ng-data; do
    [[ -e "${candidate}" ]] && gpl_leak+=("${candidate}")
done
if (( ${#gpl_leak[@]} == 0 )); then
    ok "no prebuilt GPL espeak-ng is vendored (we link Fedora's, and owe no source)"
else
    no "no prebuilt GPL espeak-ng is vendored" "${gpl_leak[*]}"
fi

# -----------------------------------------------------------------------------
section "5. the manifest agrees with docs/LICENSES.md"
# -----------------------------------------------------------------------------

if [[ -f "${LEDGER}" ]]; then
    unledgered=()
    while IFS=$'\t' read -r path _licence _source _origin; do
        # The ledger is prose: it names the exact file where that reads well
        # and the containing directory where it does not. Either satisfies it.
        grep -qF "${path}" "${LEDGER}" && continue
        grep -qF "$(dirname "${path}")/" "${LEDGER}" && continue
        unledgered+=("${path}")
    done < <(printf '%s\n' "${rows[@]}")
    if (( ${#unledgered[@]} == 0 )); then
        ok "every manifest path is accounted for in docs/LICENSES.md"
    else
        no "every manifest path is accounted for in docs/LICENSES.md" \
            "${#unledgered[@]} unrecorded: ${unledgered[*]:0:3}"
    fi

    if grep -qF "THIRD-PARTY.tsv" "${LEDGER}"; then
        ok "docs/LICENSES.md points at its machine-readable half"
    else
        no "docs/LICENSES.md points at its machine-readable half" \
            "no mention of THIRD-PARTY.tsv; the two halves will drift apart"
    fi
else
    note "docs/LICENSES.md is not mounted, so the ledger cross-check did not run."
    note "Run \`just licenses\` for the full gate; \`just test-image\` covers the rest."
fi

# -----------------------------------------------------------------------------
printf '\n\033[1m==> %d passed, %d failed\033[0m\n' "${pass}" "${fail}"
(( fail == 0 )) || exit 1
exit 0
