#!/usr/bin/env bash
# Compile Tailwind via the standalone CLI (no Node). Downloads a pinned binary to
# ./bin on first run, then builds static/src/app.css -> static/css/app.css.
# Used by `make css` (local) and the Dockerfile (before collectstatic).
#   WATCH=1 scripts/build_css.sh   # rebuild on change (local dev)
set -euo pipefail

TAILWIND_VERSION="${TAILWIND_VERSION:-v3.4.17}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${ROOT}/bin"
BIN="${BIN_DIR}/tailwindcss"

case "$(uname -s)" in
  Linux)  os=linux ;;
  Darwin) os=macos ;;
  *) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) arch=x64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac
asset="tailwindcss-${os}-${arch}"

if [ ! -x "${BIN}" ]; then
  mkdir -p "${BIN_DIR}"
  url="https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/${asset}"
  echo "Downloading Tailwind CLI ${TAILWIND_VERSION} (${asset})…"
  if command -v curl >/dev/null 2>&1; then
    curl -sSL --fail -o "${BIN}" "${url}"
  else
    wget -qO "${BIN}" "${url}"
  fi
  chmod +x "${BIN}"
fi

cd "${ROOT}"
args=(-i static/src/app.css -o static/css/app.css --minify)
if [ "${WATCH:-0}" = "1" ]; then
  exec "${BIN}" "${args[@]}" --watch
fi
"${BIN}" "${args[@]}"
echo "Built static/css/app.css"
