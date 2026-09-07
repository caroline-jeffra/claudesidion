#!/usr/bin/env bash
# SessionStart hook: remind that the weekly vault condense run (condense-vault skill) is due
# when the last run was more than 7 days ago (or has never happened). The skill stamps
# $VAULT/.condense-last-run with YYYY-MM-DD on every run.
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
routine=""
VAULT="${VAULT:-$HOME/ObsidianVault}"
[ -d "$VAULT" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

STAMP="$VAULT/.condense-last-run"
cutoff="$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '-7 days' +%Y-%m-%d 2>/dev/null)" || exit 0

if [ -f "$STAMP" ]; then
  last="$(head -n1 "$STAMP" 2>/dev/null | tr -cd '0-9-')"
  # Malformed stamp or recent enough: stay silent.
  case "$last" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) [ "$last" \< "$cutoff" ] || exit 0 ;;
    *) exit 0 ;;
  esac
  ctx="The weekly vault condense run is due (last run: ${last}). Mention this to the user and offer to run the condense-vault skill; do not start it unprompted."
  routine=yes
else
  ctx="The weekly vault condense run has never been recorded. Mention this to the user and offer to run the condense-vault skill; do not start it unprompted."
  routine=""
fi

# A due stamp is necessary but not sufficient for the ROUTINE weekly nudge: if nothing is
# old enough to condense, prompting produces a run that finds nothing. That happened weekly
# on a vault younger than the 3-month threshold.
#
# This gate deliberately does not apply when the run has NEVER been recorded. That message
# is how someone first learns the routine exists, and suppressing it on a young vault means
# they never hear about it at all.
#
# Bounded on purpose: `head -1` stops at the first hit, so this costs one match, not a full
# walk, and it never runs `git log` per file the way the skill itself does. Fails open — any
# error here means we simply do not prompt.
stale_cutoff="$(date -v-3m +%Y-%m-%d 2>/dev/null || date -d '-3 months' +%Y-%m-%d 2>/dev/null)"
if [ -n "$routine" ] && [ -n "$stale_cutoff" ]; then
  found=""
  # Oldest mtime in the vault. BSD and GNU `stat` take different flags — and crucially GNU
  # `stat` does NOT fail on the BSD form: it reads `%Sm` as a filename, writes an error to
  # stderr, and still exits 0. So `bsd || gnu` silently keeps the empty BSD result on Linux.
  # Pick by probing `stat` once on a known file and testing the OUTPUT, never the exit code.
  probe="$(stat -f '%Sm' -t '%Y-%m-%d' "$VAULT" 2>/dev/null)"
  case "$probe" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) stat_fmt=bsd ;;
    *) stat_fmt=gnu ;;
  esac

  if [ "$stat_fmt" = bsd ]; then
    oldest="$(find "$VAULT" -name '*.md' -not -path '*/.git/*' -not -path '*/.obsidian/*' \
      -exec stat -f '%Sm' -t '%Y-%m-%d' {} + 2>/dev/null | sort | head -n1)"
  else
    oldest="$(find "$VAULT" -name '*.md' -not -path '*/.git/*' -not -path '*/.obsidian/*' \
      -exec stat -c '%y' {} + 2>/dev/null | cut -d' ' -f1 | sort | head -n1)"
  fi

  case "$oldest" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])
      [ "$(printf '%s\n%s\n' "$oldest" "$stale_cutoff" | sort | head -n1)" = "$oldest" ] \
        && [ "$oldest" != "$stale_cutoff" ] && found=yes ;;
  esac
  [ -n "$found" ] || exit 0
fi

jq -n --arg ctx "$ctx" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}' \
  2>/dev/null || true

exit 0
