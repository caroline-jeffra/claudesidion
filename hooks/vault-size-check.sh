#!/usr/bin/env bash
# SessionStart hook: warn when vault files approach GitHub's 50 MB push warning.
# Threshold is within 5% of that cap (>= 47.5 MB). The hook only reports; the fix is
# manual/Claude-driven per file: split markdown by date or topic, extract embedded
# base64 payloads into attachment files, or move genuinely binary blobs to Git LFS.
#
# Fails open on every path: if anything is missing or goes wrong, exit 0 with no output.

set -u

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
[ -d "$VAULT" ] || exit 0

# This hook's only output is JSON built by jq. Check for it before doing any work — a
# scan of the whole vault whose result cannot be reported is pure latency at session start.
command -v jq >/dev/null 2>&1 || exit 0

# 47.5 MB in bytes (95% of GitHub's 50 MB per-file push warning).
THRESHOLD=49807360

# Find files at/over threshold, ignoring git internals and Obsidian's own config dir.
# -print0 and read -d '' are required: a filename may contain a newline, and splitting on
# newlines turns one such file into two nonexistent paths — which produced real stderr
# noise on SessionStart (a fail-open violation) and fed filename fragments to the model.
report=""
count=0
while IFS= read -r -d '' f; do
  bytes=$(wc -c <"$f" 2>/dev/null) || continue
  mb=$((bytes / 1048576))
  # Filenames are untrusted text that ends up in additionalContext, which the model reads
  # as instructions. Strip control characters (including the newlines above) so a crafted
  # filename cannot inject line-shaped content into the report.
  safe=$(printf '%s' "$f" | tr -d '\000-\037')
  report="${report}
- ${safe} (${mb} MB)"
  count=$((count + 1))
done < <(find "$VAULT" -type f -size +${THRESHOLD}c \
  -not -path '*/.git/*' -not -path '*/.obsidian/*' -print0 2>/dev/null)
[ "$count" -gt 0 ] || exit 0

ctx="Vault size warning: the following files are within 5% of GitHub's 50 MB per-file push warning:${report}

Surface this to the user and offer to fix each file: for markdown, split it at a natural boundary (per year/month or per topic) and update wikilinks; if it is bloated by embedded base64 images or pasted data dumps, extract those into attachment files; for genuinely binary files, suggest Git LFS. Do not modify any file without the user's confirmation."

jq -n --arg ctx "$ctx" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}' \
  2>/dev/null || true

exit 0
