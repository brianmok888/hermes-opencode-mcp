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
if [[ ! -f "$DEST_DIR/SKILL.md" ]]; then
  echo "Installed skill missing: $DEST_DIR/SKILL.md" >&2
  exit 1
fi

diff -u "$EXPORT_ROOT/SKILL.md" "$DEST_DIR/SKILL.md"

if [[ -d "$EXPORT_ROOT/references" ]]; then
  if [[ ! -d "$DEST_DIR/references" ]]; then
    echo "Installed references directory missing: $DEST_DIR/references" >&2
    exit 1
  fi
  shopt -s nullglob
  for file in "$EXPORT_ROOT"/references/*.md; do
    diff -u "$file" "$DEST_DIR/references/$(basename "$file")"
  done
  shopt -u nullglob
fi

echo "Skill $SKILL_NAME is in sync"
