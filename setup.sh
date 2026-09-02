#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

git -C "$repo_root" submodule sync --recursive
git -C "$repo_root" submodule update --init --recursive

if [[ ! -f "$repo_root/core/.env" ]]; then
  cp "$repo_root/core/.env.example" "$repo_root/core/.env"
  echo "Created core/.env from core/.env.example."
fi

echo "Argus workspace ready. Core, services, and libs are available."
