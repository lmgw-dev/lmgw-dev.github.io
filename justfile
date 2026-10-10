# The lmgw-dev site. `just` lists the recipes; README.md explains the layout.
set shell := ["bash", "-euo", "pipefail", "-c"]

zola := ".tools/zola"
lmgw_dir := env("LMGW_DIR", "../lmgw")

default:
    @just --list

# Install the pinned Zola (tools.env) into .tools/
tools:
    scripts/install-zola.sh

# Live preview on http://127.0.0.1:1111
serve: tools
    {{zola}} serve --interface 127.0.0.1 --port 1111

# Build into public/, as the Pages workflow does
build: tools
    {{zola}} build

# Build and check every link, external ones included
check: tools
    {{zola}} check

# Regenerate static/openapi.json (the complete document) and static/openapi-v1.json (the developer document) from the lmgw checkout (LMGW_DIR, default ../lmgw); check out a release tag there first
openapi:
    git -C {{lmgw_dir}} describe --tags --always
    cargo run -q -j 8 --manifest-path {{lmgw_dir}}/Cargo.toml -p lmgw-core --example openapi -- admin > static/openapi.json.new
    mv static/openapi.json.new static/openapi.json
    cargo run -q -j 8 --manifest-path {{lmgw_dir}}/Cargo.toml -p lmgw-core --example openapi > static/openapi-v1.json.new
    mv static/openapi-v1.json.new static/openapi-v1.json
    jq -r '"openapi.json: lmgw " + .info.version + ", " + (.paths | length | tostring) + " paths"' static/openapi.json
    jq -r '"openapi-v1.json: lmgw " + .info.version + ", " + (.paths | length | tostring) + " paths"' static/openapi-v1.json

# Refresh data/releases.json (lmgw) and data/releases-kai.json (Kai) from GitHub (the Pages workflow does this on every build)
releases:
    gh api repos/lmgw-dev/lmgw/releases --jq "$(cat scripts/releases.jq)" > data/releases.json.new
    mv data/releases.json.new data/releases.json
    gh api repos/lmgw-dev/kai/releases --jq "$(cat scripts/releases.jq)" > data/releases-kai.json.new
    mv data/releases-kai.json.new data/releases-kai.json
    jq -r '.[] | "lmgw " + .tag + "  " + .published' data/releases.json
    jq -r '.[] | "kai  " + .tag + "  " + .published' data/releases-kai.json

# Screenshot every page, light and dark, desktop and phone, into target/shots/ (needs `just serve` running)
shots:
    mkdir -p target/shots
    for p in "" lmgw kai docs/clients docs/api releases; do n="${p//\//-}"; n="${n:-home}"; \
      scripts/shot.py "http://127.0.0.1:1111/$p" "target/shots/$n-light.png"; \
      scripts/shot.py "http://127.0.0.1:1111/$p" "target/shots/$n-dark.png" --dark; \
      scripts/shot.py "http://127.0.0.1:1111/$p" "target/shots/$n-phone.png" --mobile --dark; \
    done
