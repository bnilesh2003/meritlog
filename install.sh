#!/usr/bin/env bash
# Install the meritlog skill for Claude Code, or build the claude.ai upload zip.
#   ./install.sh              install/update into ~/.claude/skills/meritlog, init data home
#   ./install.sh --zip        build dist/meritlog.zip for claude.ai (Settings → Capabilities → Skills)
#   ./install.sh --uninstall  remove the skill (your data home is never touched)
# Env: CLAUDE_SKILLS_DIR (default ~/.claude/skills), MERITLOG_HOME (default ~/meritlog)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO/skills/meritlog"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/meritlog"

case "${1:-}" in
  --zip)
    mkdir -p "$REPO/dist"
    rm -f "$REPO/dist/meritlog.zip"
    (cd "$REPO/skills" && zip -qr "$REPO/dist/meritlog.zip" meritlog -x '*/__pycache__/*' '*/.installed-from')
    echo "built $REPO/dist/meritlog.zip; upload it in claude.ai: Settings → Capabilities → Skills"
    exit 0 ;;
  --uninstall)
    rm -rf "$DEST"
    echo "removed $DEST (data home untouched)"
    exit 0 ;;
  "") ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it with one of:" >&2
  echo "  brew install uv" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

# Copy to a temp dir first so a failed copy never leaves a half-installed skill.
mkdir -p "$(dirname "$DEST")"
TMP="$(mktemp -d "$(dirname "$DEST")/.meritlog.XXXXXX")"
cp -R "$SRC/." "$TMP/"
COMMIT="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"
printf 'repo: %s\ncommit: %s\ninstalled: %s\n' "$REPO" "$COMMIT" "$(date +%F)" > "$TMP/.installed-from"
rm -rf "$DEST"
mv "$TMP" "$DEST"
echo "installed skill → $DEST (commit $COMMIT)"

uv run --quiet "$DEST/scripts/meritlog.py" init
uv run --quiet "$DEST/scripts/meritlog.py" doctor
