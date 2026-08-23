#!/usr/bin/bash
# Run the kidnix shell demo under GTK's Broadway backend and take a screenshot,
# without opening any window on the developer's desktop (AGENTS.md §5).
# Usage: tools/shell-demo-headless.sh <WxH@dpi> <out.png> [extra kidnix-shell args]
set -euo pipefail
screen="${1:?screen, e.g. 1280x800@102}"
out="${2:?output png}"
shift 2
mkdir -p "$(dirname "${out}")"
port=$((8100 + RANDOM % 800))
disp=":$((port - 8000))"
gtk4-broadwayd -p "${port}" "${disp}" >/dev/null 2>&1 &
bd=$!
trap 'kill "${bd}" 2>/dev/null || true' EXIT
sleep 0.5
out_abs="$(realpath -m "${out}")"
cd "$(dirname "$0")/../shell"
KIDNIX_SPEECH=off GDK_BACKEND=broadway BROADWAY_DISPLAY="${disp}" \
    uv run kidnix-shell --demo --screen "${screen}" --screenshot "${out_abs}" "$@"
echo "==> ${out_abs}"
