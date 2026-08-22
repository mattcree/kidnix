#!/usr/bin/bash
# Entry point for the image build. Runs each numbered stage in order so a
# failure names the stage that broke.
set -euo pipefail

BUILD_FILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BUILD_FILES_DIR

log() { printf '\n=== kidnix build: %s ===\n' "$*"; }

for stage in "${BUILD_FILES_DIR}"/[0-9][0-9]-*.sh; do
    log "$(basename "${stage}")"
    bash -euo pipefail "${stage}"
done

log "done"
