#!/usr/bin/env bash
# Fetch the Kokoro-82M ONNX artefacts into a scratch directory and verify them.
#
# Spike only: these are downloaded to a scratch path, never into the image.
# The checksums below were recorded on 2026-08-23 and are what a follow-up
# build_files/ stage would pin.
set -euo pipefail

DEST="${1:?usage: fetch.sh <destination-dir>}"
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"

# sha256  size  filename
FILES=(
  "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a 325505369 kokoro-v1.0.onnx"
  "ae315a79b623f244700e4afb9246c46a26066782e049ba174bf3ba433970ee9c 114119327 kokoro-v1.0.int8.onnx"
  "f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96 163527961 kokoro-v1.0.fp16.onnx"
  "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d  28214398 voices-v1.0.bin"
)

# The Apache-2.0-labelled HF artefacts docs/spikes/tts-kokoro.md §7 actually
# recommends shipping. onnx-community's per-voice .bin is byte-for-byte the
# same array as the corresponding entry in voices-v1.0.bin above.
HF=(
  "8fbea51ea711f2af382e88c833d9e288c6dc82ce5e98421ea61c058ce21a34cb 325532232 onnx-community/Kokoro-82M-v1.0-ONNX onnx/model.onnx"
  "669fe0647f9dd04fcab92f1439a40eeb4c8b4ab1f82e4996fe3d918ce4a63b73    522240 onnx-community/Kokoro-82M-v1.0-ONNX voices/bf_emma.bin"
  "c4b235a4c1f2cd3b939fed08b899ce9385638b763f7b73a59616c4fc9bd6c9bc    522240 onnx-community/Kokoro-82M-v1.0-ONNX voices/bm_george.bin"
)

mkdir -p "$DEST" "$DEST/hf"
for entry in "${FILES[@]}"; do
  read -r sum size name <<<"$entry"
  path="$DEST/$name"
  if [[ ! -s "$path" ]]; then
    echo "==> $name ($size bytes)"
    curl -sSLf -o "$path.part" "$BASE/$name"
    mv "$path.part" "$path"
  fi
  echo "$sum  $path" | sha256sum -c -
done

for entry in "${HF[@]}"; do
  read -r sum size repo file <<<"$entry"
  path="$DEST/hf/$(basename "$file")"
  if [[ ! -s "$path" ]]; then
    echo "==> $repo/$file ($size bytes)"
    curl -sSLf -o "$path.part" "https://huggingface.co/$repo/resolve/main/$file"
    mv "$path.part" "$path"
  fi
  echo "$sum  $path" | sha256sum -c -
done

# The 114-entry phoneme vocabulary. Not pinned by hash: it is 2.3 KB of the
# model's own config and a follow-up implementer should record whatever hash
# they fetch.
[[ -s "$DEST/hf/config.json" ]] || curl -sSLf -o "$DEST/hf/config.json" \
  "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/config.json"
sha256sum "$DEST/hf/config.json"
