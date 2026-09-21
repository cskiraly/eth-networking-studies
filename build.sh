#!/bin/bash
# Build the two binaries the shadow-crosscheck cells ran: Shadow 3.3.0 with the three local
# patches, and the node test binary from the Prysm research snapshot. Run from this directory
# after `git submodule update --init`. Shadow's own build needs its documented dependencies
# (https://shadow.github.io/docs/guide/install_dependencies.html); the node needs Go and cgo.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)

# 1. Shadow, patched. The published records carry the version string
#    "Shadow 3.3.0 — v3.3.0-0-g5a05740ba-dirty": upstream 5a05740ba plus these patches.
cd "$here/shadow"
git diff --quiet || { echo "shadow/ has local changes; reset it or apply the patches by hand" >&2; exit 1; }
for p in "$here"/shadow-patches/*.patch; do git apply "$p"; done
./setup build --clean
./setup install              # installs to ~/.local/bin/shadow, which the lab's shadowrun.sh runs by default
~/.local/bin/shadow --version

# 2. The node. Shadow interposes with LD_PRELOAD, so the binary must be dynamically linked.
#    prysm/go.mod replaces eth-networking-lab with ../eth-networking-lab, the sibling checkout.
cd "$here/prysm"
mkdir -p "$here/bin"
CGO_ENABLED=1 go test -c -ldflags=-linkmode=external -o "$here/bin/segshadow.test" ./beacon-chain/p2p/segmentintegrationtest
git rev-parse HEAD > "$here/bin/segshadow.test.commit"   # extract.py records it in every result
ldd "$here/bin/segshadow.test" | head -1
sha256sum "$here/bin/segshadow.test"
echo "the published cells ran a binary with sha256 8d07d183d3b9c2c31393d05f7262d5ea29f8bd73d30e83d6e12f8a87ea263b88,"
echo "built on Debian 12 (glibc 2.36) with Go 1.26; a different toolchain gives a different hash and the same program."
