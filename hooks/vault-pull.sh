#!/usr/bin/env bash
# SessionStart hook: pull the Obsidian vault to latest once per session (startup|resume),
# so the whole session works from the latest remote state. Paired with vault-push.sh (SessionEnd),
# which commits and pushes once at the end: the skills themselves never pull, commit, or push.
#
# Fails open on every path: if anything is missing or goes wrong, exit 0 with no output so a
# hook bug can never delay or break the session.

set -u

# Resolve the vault the same way the skills do — NOT the payload's cwd (the vault is a
# different directory from the repo the session runs in). Env var may not be exported to the
# hook's shell if it's only set in an interactive profile; the default covers the common case.
# Vault resolution: env var, then the config file ~/.claude/obsidian-vault (one line,
# the vault's absolute path), then the default. The config file exists because interactive
# profile exports do not reach hook shells.
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

stranded=""

# Need git; if absent, stay silent.
command -v git >/dev/null 2>&1 || exit 0

# Skip if the vault is not a git work tree (mirrors the skills' "skip if not a git repo").
git -C "$VAULT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

emit_context() {
  # Emit additionalContext if jq is available; otherwise stay silent (never error).
  command -v jq >/dev/null 2>&1 || return 0
  jq -n --arg ctx "$1" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}' \
    2>/dev/null || true
}

# --- Flush stranded commits ---------------------------------------------------
# The SessionEnd push hook commits locally, then pushes over the network. Session teardown can
# cancel it in the gap between the two, leaving commits that exist only on this machine — the
# exact "user believes work is backed up when it is not" failure this plugin exists to prevent.
# SessionStart has no teardown pressure, so a flush here reliably recovers whatever the last exit
# stranded. Push before the pull below: these commits are already on the branch, so sending them
# first keeps the subsequent --ff-only honest instead of racing a remote that moved on.
if [ -n "$(git -C "$VAULT" log '@{upstream}..HEAD' --oneline 2>/dev/null)" ]; then
  n="$(git -C "$VAULT" rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo some)"
  if git -C "$VAULT" push >/dev/null 2>&1; then
    stranded="Pushed ${n} vault commit(s) stranded by a previous session's cancelled exit hook."
  else
    stranded="Vault has ${n} unpushed commit(s) from a previous session and the retry failed; they remain local-only."
  fi
fi

if git -C "$VAULT" pull --ff-only >/dev/null 2>&1; then
  short="$(git -C "$VAULT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  emit_context "${stranded:+$stranded }Obsidian vault pulled to latest (${short})."
else
  emit_context "${stranded:+$stranded }Obsidian vault pull failed (offline, no remote, or non-fast-forward); working from local state."
fi

exit 0
