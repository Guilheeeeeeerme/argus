#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

for command_name in git docker; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

git -C "$repo_root" submodule sync --recursive
git -C "$repo_root" submodule update --init --recursive

if [[ ! -f "$repo_root/argus-core/.env" ]]; then
  cp "$repo_root/argus-core/.env.example" "$repo_root/argus-core/.env"
  echo "Created argus-core/.env from argus-core/.env.example."
fi

hosts_file="${ARGUS_HOSTS_FILE:-/etc/hosts}"
hosts_entry="127.0.0.1 development.argus.com api.development.argus.com"
if [[ ! -f "$hosts_file" ]]; then
  echo "Hosts file not found: $hosts_file" >&2
  exit 1
fi
if ! grep -Eq '(^|[[:space:]])development\.argus\.com([[:space:]]|$)' "$hosts_file" || \
  ! grep -Eq '(^|[[:space:]])api\.development\.argus\.com([[:space:]]|$)' "$hosts_file"; then
  if [[ -w "$hosts_file" ]]; then
    printf '%s\n' "$hosts_entry" >> "$hosts_file"
  elif command -v sudo >/dev/null 2>&1; then
    printf '%s\n' "$hosts_entry" | sudo tee -a "$hosts_file" >/dev/null
  else
    echo "Cannot update $hosts_file; run setup with permission to edit it." >&2
    exit 1
  fi
  echo "Added Argus development hostnames to $hosts_file."
fi

if [[ "${ARGUS_SKIP_CORE_START:-0}" != 1 ]]; then
  docker compose -f "$repo_root/argus-core/compose.yaml" up -d --build
fi

if [[ "${ARGUS_SKIP_CERT_TRUST:-0}" != 1 ]]; then
  cert_file="$(mktemp)"
  trap 'rm -f "$cert_file"' EXIT
  if ! docker exec argus-dev-gateway cat /data/caddy/pki/authorities/local/root.crt > "$cert_file"; then
    echo "Could not read the Caddy local CA certificate from argus-dev-gateway." >&2
    exit 1
  fi

  cert_target="/usr/local/share/ca-certificates/argus-development.crt"
  if [[ -w "$(dirname "$cert_target")" ]]; then
    cp "$cert_file" "$cert_target"
  elif command -v sudo >/dev/null 2>&1; then
    sudo cp "$cert_file" "$cert_target"
  else
    echo "Cannot install the Argus CA certificate; sudo is required." >&2
    exit 1
  fi

  if command -v update-ca-certificates >/dev/null 2>&1; then
    if [[ -w /etc/ssl/certs ]]; then
      update-ca-certificates >/dev/null
    else
      sudo update-ca-certificates >/dev/null
    fi
  elif command -v update-ca-trust >/dev/null 2>&1; then
    if [[ -w /etc/pki/ca-trust/source/anchors ]]; then
      update-ca-trust
    else
      sudo update-ca-trust
    fi
  else
    echo "No supported CA trust update command found." >&2
    exit 1
  fi
  echo "Trusted the Argus development CA certificate."
fi

echo "Argus workspace ready. Argus Core, services, and libs are available."
