#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

for command_name in git docker openssl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

# Install mkcert if not present
if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert not found. Installing..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq mkcert libnss3-tools
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y mkcert
  elif command -v brew >/dev/null 2>&1; then
    brew install mkcert
  else
    echo "Cannot install mkcert automatically." >&2
    echo "Install manually: https://github.com/FiloSottile/mkcert#installation" >&2
    exit 1
  fi
  echo "mkcert installed."
fi

# Initialize mkcert CA (requires sudo on first run)
# Only run if CA doesn't exist yet
if [[ ! -d "$HOME/.local/share/mkcert" ]]; then
  mkcert -install 2>/dev/null || true
fi

git -C "$repo_root" submodule sync --recursive
git -C "$repo_root" submodule update --init --recursive

if [[ ! -f "$repo_root/argus-core/.env" ]]; then
  cp "$repo_root/argus-core/.env.example" "$repo_root/argus-core/.env"
  echo "Created argus-core/.env from argus-core/.env.example."
fi

credentials_file="$repo_root/argus-core/.env.root-credentials.txt"
if [[ ! -f "$credentials_file" ]]; then
  root_password="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"
  root_email="root@argus.local"
  {
    echo "ARGUS_ROOT_EMAIL=$root_email"
    echo "ARGUS_ROOT_PASSWORD=$root_password"
  } > "$credentials_file"
  chmod 600 "$credentials_file"
  printf 'Created local root credentials at %s.\n' "$credentials_file"
fi
root_email="$(sed -n 's/^ARGUS_ROOT_EMAIL=//p' "$credentials_file")"
root_password="$(sed -n 's/^ARGUS_ROOT_PASSWORD=//p' "$credentials_file")"
if grep -q '^DEV_ROOT_EMAIL=' "$repo_root/argus-core/.env"; then
  sed -i "s|^DEV_ROOT_EMAIL=.*|DEV_ROOT_EMAIL=$root_email|" "$repo_root/argus-core/.env"
else
  printf '\nDEV_ROOT_EMAIL=%s\n' "$root_email" >> "$repo_root/argus-core/.env"
fi
if grep -q '^DEV_ROOT_PASSWORD=' "$repo_root/argus-core/.env"; then
  sed -i "s|^DEV_ROOT_PASSWORD=.*|DEV_ROOT_PASSWORD=$root_password|" "$repo_root/argus-core/.env"
else
  printf 'DEV_ROOT_PASSWORD=%s\n' "$root_password" >> "$repo_root/argus-core/.env"
fi

hosts_file="${ARGUS_HOSTS_FILE:-/etc/hosts}"
hosts_entry="127.0.0.1 app.development.argus.com development.argus.com api.development.argus.com"
if [[ ! -f "$hosts_file" ]]; then
  echo "Hosts file not found: $hosts_file" >&2
  exit 1
fi
if ! grep -Eq '(^|[[:space:]])app\.development\.argus\.com([[:space:]]|$)' "$hosts_file" || \
  ! grep -Eq '(^|[[:space:]])development\.argus\.com([[:space:]]|$)' "$hosts_file" || \
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

# Generate development certificates (always, regardless of ARGUS_SKIP_CORE_START)
cert_dir="$repo_root/argus-core/infra/caddy/certs"
mkdir -p "$cert_dir"
if [[ ! -f "$cert_dir/cert.pem" ]] || [[ ! -f "$cert_dir/key.pem" ]]; then
  echo "Generating development certificates..."
  mkcert -cert-file "$cert_dir/cert.pem" \
          -key-file "$cert_dir/key.pem" \
          "*.development.argus.com" development.argus.com localhost 127.0.0.1
  echo "Certificates generated at $cert_dir/"
fi

if [[ "${ARGUS_SKIP_CORE_START:-0}" != 1 ]]; then
  docker compose -f "$repo_root/argus-core/compose.yaml" up -d --build
fi

# mkcert CA is trusted during mkcert -install step above
# ARGUS_SKIP_CERT_TRUST is kept for backward compatibility but no longer needed
# as mkcert handles trust automatically

echo "Argus workspace ready. Argus Core, services, and libs are available."
