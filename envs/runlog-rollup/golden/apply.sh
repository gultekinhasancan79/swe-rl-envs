#!/usr/bin/env bash
#
# Materialise the reference solution into a scratch directory that verify.sh
# can score, without touching the pristine repo/ that ships to the candidate.
#
#   golden/apply.sh /tmp/golden-candidate
#
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_ROOT="$(cd "$HERE/.." && pwd)"
DEST="${1:?usage: apply.sh DEST}"

rm -rf "$DEST"
cp -r "$ENV_ROOT/repo" "$DEST"
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

# `git apply` is used here purely as a standalone patch applier; DEST is not a
# git repository. The patch is rooted at the repo, so -p1 strips the a/ prefix.
(cd "$DEST" && git apply -p1 --whitespace=nowarn "$HERE/fix.patch")

echo "reference solution materialised at $DEST"
