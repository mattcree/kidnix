#!/usr/bin/bash
# Brand the image as kidnix.
#
# We follow the Bluefin convention exactly: ID becomes the image name and
# ID_LIKE="fedora" keeps everything that switches on distro (dnf, rpm-ostree,
# Flatpak remotes, ublue's own tooling, third-party install scripts) working.
# Setting NAME/PRETTY_NAME without ID_LIKE is what actually breaks tooling.
set -euo pipefail

VERSION="${KIDNIX_VERSION:-0.0.0}"
PRETTY_VERSION="${KIDNIX_PRETTY_VERSION:-${VERSION}}"

OS_RELEASE=/usr/lib/os-release
FEDORA_VERSION_ID="$(sed -n 's/^VERSION_ID=//p' "${OS_RELEASE}")"

# /etc/os-release is a symlink to this file; edit in place so both agree.
sed -i \
    -e 's|^NAME=.*|NAME="kidnix"|' \
    -e "s|^PRETTY_NAME=.*|PRETTY_NAME=\"kidnix (Version: ${PRETTY_VERSION})\"|" \
    -e 's|^ID=fedora|ID=kidnix\nID_LIKE="fedora"|' \
    -e 's|^DEFAULT_HOSTNAME=.*|DEFAULT_HOSTNAME="kidnix"|' \
    -e 's|^HOME_URL=.*|HOME_URL="https://github.com/mattcree/kidnix"|' \
    -e 's|^DOCUMENTATION_URL=.*|DOCUMENTATION_URL="https://github.com/mattcree/kidnix"|' \
    -e 's|^SUPPORT_URL=.*|SUPPORT_URL="https://github.com/mattcree/kidnix/issues"|' \
    -e 's|^BUG_REPORT_URL=.*|BUG_REPORT_URL="https://github.com/mattcree/kidnix/issues"|' \
    -e 's|^CPE_NAME=.*|CPE_NAME="cpe:/o:mattcree:kidnix:'"${FEDORA_VERSION_ID}"'"|' \
    "${OS_RELEASE}"

cat >>"${OS_RELEASE}" <<EOF
VARIANT="kidnix"
VARIANT_ID=kidnix
IMAGE_ID="kidnix"
IMAGE_VERSION="${VERSION}"
EOF

# Machine-readable version for scripts and the image test suite.
printf '%s\n' "${VERSION}" >/usr/share/kidnix/VERSION

# Mirrors ublue's image-info.json so ublue-flavoured tooling can introspect us.
cat >/usr/share/kidnix/image-info.json <<EOF
{
  "image-name": "kidnix",
  "image-flavor": "main",
  "image-vendor": "mattcree",
  "image-ref": "ostree-image-signed:docker://ghcr.io/mattcree/kidnix",
  "image-tag": "latest",
  "base-image-name": "base-main",
  "fedora-version": "${FEDORA_VERSION_ID}",
  "kidnix-version": "${VERSION}"
}
EOF

grep -q '^ID=kidnix$' "${OS_RELEASE}"
grep -q '^ID_LIKE="fedora"$' "${OS_RELEASE}"
