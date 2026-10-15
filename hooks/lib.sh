# shellcheck shell=bash
# Shared helpers for every dev-workbook hook: path resolution, output formats, and the warnings
# relay. Source it; it defines functions only.
# hooks/dev_workbook_paths.py is the Python twin — keep the two in step (tests check they agree).
#
# Each path resolves in the same order:
#   1. an environment variable              (DEVWB_VAULT, then the pre-3.0 OBSIDIAN_VAULT / CODE_ROOT)
#   2. ${XDG_CONFIG_HOME:-~/.config}/dev-workbook/<name>, then the pre-3.0 .../claudesidion/<name>
#   3. the legacy ~/.claude/<name> file     (obsidian-vault / code-root)
#   4. a default                             (~/ObsidianVault / ~/code)
# The config files exist because interactive profile exports do not reach hook shells. Each is
# one line; surrounding whitespace is trimmed and a leading ~ or $HOME is expanded, because a
# hand-edited "~/Vault " would otherwise resolve to a path that does not exist and silently
# disable the plugin.

# read_path_file <file> — print the file's first line, trimmed and ~-expanded; fail if empty.
read_path_file() {
  local value
  [ -f "$1" ] || return 1
  value="$(head -n1 "$1" 2>/dev/null)"
  value="${value#"${value%%[![:space:]]*}"}"   # leading whitespace
  value="${value%"${value##*[![:space:]]}"}"   # trailing whitespace
  # shellcheck disable=SC2088,SC2016  # literal '~' and '$HOME' patterns, expanded by hand
  case "$value" in
    '~') value="$HOME" ;;
    '~/'*) value="$HOME/${value#\~/}" ;;
    '$HOME') value="$HOME" ;;
    '$HOME/'*) value="$HOME/${value#\$HOME/}" ;;
  esac
  [ -n "$value" ] || return 1
  printf '%s\n' "$value"
}

# resolve_path <env value> <config name> <legacy name> <default>
resolve_path() {
  local xdg="${XDG_CONFIG_HOME:-$HOME/.config}"
  if [ -n "$1" ]; then
    printf '%s\n' "$1"
  elif read_path_file "$xdg/dev-workbook/$2"; then
    :
  elif read_path_file "$xdg/claudesidion/$2"; then
    :
  elif read_path_file "$HOME/.claude/$3"; then
    :
  else
    printf '%s\n' "$4"
  fi
}

resolve_vault() { resolve_path "${DEVWB_VAULT:-${OBSIDIAN_VAULT:-}}" vault obsidian-vault "$HOME/ObsidianVault"; }
resolve_code_root() { resolve_path "${CODE_ROOT:-}" code-root code-root "$HOME/code"; }

# ---------------------------------------------------------------- output

# emit_context <text> — session-start context for the agent, in the harness's format, chosen by
# DEVWB_FORMAT: `claude` (default) prints Claude Code's hookSpecificOutput JSON, `cursor`
# prints {"additional_context": ...}, `plain` prints the text. JSON needs jq; without it the
# hook stays silent rather than erroring.
emit_context() {
  case "${DEVWB_FORMAT:-claude}" in
    plain)
      printf '%s\n' "$1" ;;
    cursor)
      command -v jq >/dev/null 2>&1 \
        && jq -n --arg ctx "$1" '{additional_context: $ctx}' 2>/dev/null ;;
    *)
      command -v jq >/dev/null 2>&1 \
        && jq -n --arg ctx "$1" \
          '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}' 2>/dev/null ;;
  esac
  return 0
}

# can_emit — true when emit_context can produce output, so a hook can skip work it could not report.
can_emit() { [ "${DEVWB_FORMAT:-claude}" = plain ] || command -v jq >/dev/null 2>&1; }

# ---------------------------------------------------------------- warnings relay

# Session-end output is shown to no one, so a hook that has something to say at exit also
# records it here, inside the vault's .git (never committed), and the next session start
# reports it. warnings_file <vault> prints the path, or fails for a vault that is not a repo.
warnings_file() {
  local dir
  dir="$(git -C "$1" rev-parse --absolute-git-dir 2>/dev/null)" || return 1
  [ -n "$dir" ] || return 1
  printf '%s/dev-workbook-warnings\n' "$dir"
}
