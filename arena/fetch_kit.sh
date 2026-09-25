#!/bin/sh
# Fetch the kit (gfrmin/wald-charter's laws/) at the locked tag into arena/charter/, refusing unless author@wald
# signed the tag and it names the locked commit. Mirrors wald's cage/fetch_charter.sh. Run from the repo root.
set -eu
. arena/kit.lock
SIGNERS=$(pwd)/arena/allowed_signers
rm -rf arena/charter
git clone -q https://github.com/gfrmin/wald-charter arena/charter
cd arena/charter
git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$SIGNERS" tag -v "$TAG" > .tagcheck 2>&1 || true
grep -q 'Good "git" signature for author@wald' .tagcheck || { echo "tag $TAG is not signed by author@wald"; cat .tagcheck; exit 1; }
[ "$(git rev-list -n1 "$TAG")" = "$SHA" ] || { echo "tag $TAG does not point at the locked commit $SHA"; exit 1; }
git checkout -q "$SHA"
echo "kit ok: $TAG at $SHA, signed by author@wald"
