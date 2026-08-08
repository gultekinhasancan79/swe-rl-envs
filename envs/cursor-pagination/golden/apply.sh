#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_ROOT="$(cd "$HERE/.." && pwd)"
DEST="${1:?usage: apply.sh DEST}"

rm -rf "$DEST"
cp -r "$ENV_ROOT/repo" "$DEST"
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

(cd "$DEST" && git apply -p1 --whitespace=nowarn "$HERE/fix.patch")

echo "reference solution materialised at $DEST"
