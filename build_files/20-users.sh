#!/usr/bin/bash
# Validate the declarative account setup shipped in system_files/.
#
# TRADE-OFF, on purpose: we do NOT run useradd at build time.
#
# In a bootc image /etc is 3-way-merged on every upgrade and /var is not
# shipped at all. Baking users into the image's /etc/passwd means every
# upgrade re-litigates that merge against whatever the machine has done since
# (password changes, group edits), and the home directories still would not
# exist because /var is machine-local. So:
#
#   * systemd-sysusers  (/usr/lib/sysusers.d/kidnix.conf)  creates the accounts
#     on every boot, idempotently, and skips any name that already exists --
#     which is what makes it safe to ALSO let bootc-image-builder or an
#     installer create `parent` with a password.
#   * systemd-tmpfiles  (/usr/lib/tmpfiles.d/kidnix.conf)  creates /var/home/*
#     and seeds it from /etc/skel. sysusers is ordered Before tmpfiles-setup,
#     so the owners exist by the time the directories are made.
#
# Neither can set a password. `kid` is passwordless-login by design (GDM
# autologin); `parent` gets its password from the installer / disk_config.
set -euo pipefail

test -f /usr/lib/sysusers.d/kidnix.conf
test -f /usr/lib/tmpfiles.d/kidnix.conf

# --cat-config parses every fragment and errors on a malformed line, so this
# catches a typo now rather than as a missing user on first boot.
systemd-sysusers --cat-config >/dev/null
systemd-tmpfiles --cat-config >/dev/null

# `parent` needs sudo. wheel is already NOPASSWD-free (password required),
# which is what we want for a parent account.
grep -Eq '^m[[:space:]]+parent[[:space:]]+wheel[[:space:]]*$' /usr/lib/sysusers.d/kidnix.conf
