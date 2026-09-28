#!/bin/sh
# Refuse the wald pin unless author@wald signed the tag and the tag points at the commit uv.lock installs.
#   sh arena/verify_pin.sh v0.2.0   # before a bump: is this tag signed?
#   sh arena/verify_pin.sh          # the pin as it stands: pyproject's tag, signed, at uv.lock's commit
# Run from the repo root.
set -eu
TAG=${1:-$(sed -n 's/^wald = {.*tag = "\([^"]*\)".*/\1/p' pyproject.toml)}
[ -n "$TAG" ] || { echo "no wald tag given and none pinned in pyproject.toml"; exit 1; }
SIGNERS=$(pwd)/arena/allowed_signers
DIR=$(mktemp -d)
trap 'rm -rf "$DIR"' EXIT
git clone -q --no-checkout --filter=blob:none https://github.com/gfrmin/wald "$DIR"
git -C "$DIR" -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$SIGNERS" tag -v "$TAG" > "$DIR/.tagcheck" 2>&1 || true
grep -q 'Good "git" signature for author@wald' "$DIR/.tagcheck" || { echo "tag $TAG is not signed by author@wald"; cat "$DIR/.tagcheck"; exit 1; }
SHA=$(git -C "$DIR" rev-list -n1 "$TAG")
if [ $# -eq 0 ]; then
  LOCKED=$(sed -n 's|^source = { git = "https://github.com/gfrmin/wald?tag=[^#]*#\([0-9a-f]*\)" }|\1|p' uv.lock)
  [ "$LOCKED" = "$SHA" ] || { echo "uv.lock installs wald at '$LOCKED', but signed tag $TAG is $SHA"; exit 1; }
fi
echo "wald ok: $TAG at $SHA, signed by author@wald"
