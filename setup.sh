#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

git -C "$repo_root" submodule sync --recursive
git -C "$repo_root" submodule update --init --recursive

echo "Argus workspace ready. Core, services, and libs are available."
