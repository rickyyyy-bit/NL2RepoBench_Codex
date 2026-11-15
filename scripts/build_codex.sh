#!/usr/bin/env bash
set -euo pipefail
version="${1:-0.167.2}"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo 'Supply an exact Codex CLI version, for example 0.167.2.' >&2
    exit 2
fi
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
tag="nl2repobench-codex:$version"
if docker image inspect "$tag" >/dev/null 2>&1; then
    echo "Image already exists: $tag (left unchanged)."
    exit 0
fi
docker build --file "$repo_root/docker/codex.Dockerfile" --build-arg "CODEX_VERSION=$version" --tag "$tag" "$repo_root/docker"
