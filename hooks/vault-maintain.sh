#!/usr/bin/env bash
# SessionEnd hook: refresh derived metadata and regenerate indexes for any vault
# workspace that opts in with a `.vault-config.json`.
#
# Runs BEFORE vault-push.sh so the regenerated indexes are committed in the same
# commit as the notes that changed them.
#
# This never deletes or moves a file and never edits a note body — it only fills
# in derived frontmatter and rewrites generated index notes. See
# hooks/vault_maintain.py for the guarantees.
#
# Fails open on every path: if anything is missing or goes wrong, exit 0 with no
# output so a hook bug can never break the user's session teardown.

set -u

# Vault resolution: env var, then the config file ~/.claude/obsidian-vault (one line, the vault's
# absolute path), then the default. The config file exists because interactive profile exports do
# not reach hook shells.
VAULT="${OBSIDIAN_VAULT:-}"
if [ -z "$VAULT" ] && [ -f "$HOME/.claude/obsidian-vault" ]; then
  VAULT="$(head -n1 "$HOME/.claude/obsidian-vault" 2>/dev/null)"
  # Trim surrounding whitespace, then expand a leading ~ or $HOME. A config file is
  # hand-edited, so "~/Documents/Vault" and a stray trailing space are both likely — and
  # both would otherwise resolve to a path that does not exist, silently disabling the
  # plugin with no diagnostic. Only a leading ~ is expanded; a literal ~ elsewhere in a
  # path is left alone.
  VAULT="${VAULT#"${VAULT%%[![:space:]]*}"}"   # leading whitespace
  VAULT="${VAULT%"${VAULT##*[![:space:]]}"}"   # trailing whitespace
  # shellcheck disable=SC2088  # literal '~' match patterns, expanded by hand just below
  case "$VAULT" in
    '~') VAULT="$HOME" ;;
    '~/'*) VAULT="$HOME/${VAULT#\~/}" ;;
    '$HOME') VAULT="$HOME" ;;
    '$HOME/'*) VAULT="$HOME/${VAULT#\$HOME/}" ;;
  esac
fi
VAULT="${VAULT:-$HOME/ObsidianVault}"
[ -d "$VAULT" ] || exit 0

# Python 3 is required. If it is absent, do nothing rather than failing loudly —
# the vault stays valid, the indexes are simply not refreshed this session.
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
[ -n "$PY" ] || exit 0

SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/hooks/vault_maintain.py"
[ -f "$SCRIPT" ] || exit 0

# The script fails open internally too; the redirect and `|| true` are belt and
# braces so a crash can never block the session-end push that follows.
"$PY" "$SCRIPT" "$VAULT" 2>/dev/null || true

exit 0
