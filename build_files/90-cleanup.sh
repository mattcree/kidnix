#!/usr/bin/bash
# Shrink the layer and satisfy `bootc container lint`, which rejects images
# carrying content in /var (it is machine-local and thrown away at install).
set -euo pipefail

dnf5 clean all

# /var/log and friends get repopulated by rpm scriptlets during install.
rm -rf /var/cache/* /var/log/* /var/tmp/* /tmp/* || true

# rpmdb lives at /usr/lib/sysimage/rpm on atomic Fedora; /var/lib/rpm is a
# compatibility symlink and must survive.
find /var -mindepth 1 -maxdepth 1 ! -name 'lib' ! -name 'home' -exec rm -rf {} + || true
find /var/lib -mindepth 1 -maxdepth 1 ! -name 'rpm' ! -name 'alternatives' -exec rm -rf {} + || true
