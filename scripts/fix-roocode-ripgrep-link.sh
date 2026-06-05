#!/usr/bin/env bash
set -euo pipefail

# Roo Code 3.54.0 expects VS Code's ripgrep at older package paths.
# Recent VS Code versions place it under @vscode/ripgrep-universal instead.
# This script creates compatibility symlinks from the old paths to the current rg.

APP_ROOT="/Applications/Visual Studio Code.app/Contents/Resources/app"

if [[ ! -d "$APP_ROOT" ]]; then
  echo "ERROR: VS Code app root not found: $APP_ROOT" >&2
  exit 1
fi

case "$(uname -m)" in
  arm64)
    PLATFORM="darwin-arm64"
    ;;
  x86_64)
    PLATFORM="darwin-x64"
    ;;
  *)
    PLATFORM=""
    ;;
esac

CANDIDATES=()
if [[ -n "$PLATFORM" ]]; then
  CANDIDATES+=("$APP_ROOT/node_modules/@vscode/ripgrep-universal/bin/$PLATFORM/rg")
fi
CANDIDATES+=(
  "$APP_ROOT/node_modules/@vscode/ripgrep-universal/bin/darwin-arm64/rg"
  "$APP_ROOT/node_modules/@vscode/ripgrep-universal/bin/darwin-x64/rg"
  "/opt/homebrew/bin/rg"
  "/usr/local/bin/rg"
)

SRC=""
for candidate in "${CANDIDATES[@]}"; do
  if [[ -x "$candidate" ]]; then
    SRC="$candidate"
    break
  fi
done

if [[ -z "$SRC" ]]; then
  echo "ERROR: Could not find an executable ripgrep binary." >&2
  echo "Install ripgrep with: brew install ripgrep" >&2
  exit 1
fi

TARGETS=(
  "$APP_ROOT/node_modules/@vscode/ripgrep/bin/rg"
  "$APP_ROOT/node_modules/vscode-ripgrep/bin/rg"
  "$APP_ROOT/node_modules.asar.unpacked/@vscode/ripgrep/bin/rg"
  "$APP_ROOT/node_modules.asar.unpacked/vscode-ripgrep/bin/rg"
)

echo "Using ripgrep source: $SRC"
"$SRC" --version | head -n 1

for target in "${TARGETS[@]}"; do
  target_dir="$(dirname "$target")"
  mkdir -p "$target_dir"

  if [[ -e "$target" && ! -L "$target" ]]; then
    backup="$target.backup.$(date +%Y%m%d%H%M%S)"
    echo "Existing non-symlink found, moving to: $backup"
    mv "$target" "$backup"
  fi

  ln -sfn "$SRC" "$target"
  echo "Linked: $target -> $SRC"
done

echo "Done. Restart VS Code completely, then rerun Roo Code indexing."

