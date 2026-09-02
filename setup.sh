#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

git -C "$repo_root" submodule sync --recursive
git -C "$repo_root" submodule update --init --recursive

if [[ ! -f "$repo_root/argus-core/.env" ]]; then
  cp "$repo_root/argus-core/.env.example" "$repo_root/argus-core/.env"
  echo "Created argus-core/.env from argus-core/.env.example."
fi

echo "Argus workspace ready. Argus Core, services, and libs are available."
