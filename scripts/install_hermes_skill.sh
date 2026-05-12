#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <skill-name>" >&2
  exit 2
fi

SKILL_NAME="$1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_ROOT="$REPO_ROOT/docs/hermes-skills/$SKILL_NAME"
DEST_ROOT="$HOME/.hermes/skills"

case "$SKILL_NAME" in
  hermes-telegram-topic-routing)
    DEST_DIR="$DEST_ROOT/hermes-telegram-topic-routing"
    ;;
  port-hermes-opencode-bridge-to-mcp|bootstrap-hermes-opencode-mcp-on-control-vm|prepare-opencode-target-vm|operate-hermes-opencode-mcp)
    DEST_DIR="$DEST_ROOT/devops/$SKILL_NAME"
    ;;
  install-hermes-repo-exported-skill)
    DEST_DIR="$DEST_ROOT/$SKILL_NAME"
    ;;
  *)
    echo "Unsupported skill: $SKILL_NAME" >&2
    exit 2
    ;;
esac

if [[ ! -f "$EXPORT_ROOT/SKILL.md" ]]; then
  echo "Missing exported skill: $EXPORT_ROOT/SKILL.md" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
install -m 0644 "$EXPORT_ROOT/SKILL.md" "$DEST_DIR/SKILL.md"

if [[ -d "$EXPORT_ROOT/references" ]]; then
  mkdir -p "$DEST_DIR/references"
  find "$EXPORT_ROOT/references" -maxdepth 1 -type f -name '*.md' -print0 | while IFS= read -r -d '' file; do
    install -m 0644 "$file" "$DEST_DIR/references/$(basename "$file")"
  done
fi

echo "Installed $SKILL_NAME to $DEST_DIR"
echo "Run scripts/check_hermes_skill_sync.sh $SKILL_NAME to verify drift-free install"
