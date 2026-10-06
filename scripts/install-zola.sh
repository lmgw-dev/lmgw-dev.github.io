#!/usr/bin/env bash
# Put the Zola from tools.env into .tools/zola, checking its hash. Usage: scripts/install-zola.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source tools.env
if [[ -x .tools/zola ]] && [[ "$(.tools/zola --version)" == "zola $ZOLA_VERSION" ]]; then exit 0; fi
mkdir -p .tools
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
curl -fsSL -o "$tmp" \
    "https://github.com/getzola/zola/releases/download/v$ZOLA_VERSION/zola-v$ZOLA_VERSION-x86_64-unknown-linux-musl.tar.gz"
echo "$ZOLA_SHA256  $tmp" | sha256sum -c --quiet
tar -xzf "$tmp" -C .tools zola
echo "installed $(.tools/zola --version) into .tools/"
