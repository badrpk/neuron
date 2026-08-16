#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/badrpk/neuron.git"
DEST="${NEURON_HOME:-$HOME/.local/share/neuron}"
BUILD="$DEST/build"

need(){ command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 2; }; }
need git
need cmake

if command -v c++ >/dev/null 2>&1; then :
elif command -v g++ >/dev/null 2>&1; then :
elif command -v clang++ >/dev/null 2>&1; then :
else echo "Missing C++17 compiler (c++, g++, or clang++)" >&2; exit 2; fi

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch origin --tags --prune
  test -z "$(git -C "$DEST" status --porcelain)" || { echo "Refusing update: $DEST has local changes" >&2; exit 3; }
  git -C "$DEST" checkout main
  git -C "$DEST" pull --ff-only origin main
else
  rm -rf "$DEST"
  git clone --branch main "$REPO" "$DEST"
fi

cmake -S "$DEST" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD" --parallel

echo "Neuron installed at $DEST"
echo "Build output: $BUILD"
