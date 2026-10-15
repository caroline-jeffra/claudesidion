#!/usr/bin/env bash
# Tests for the shared path resolvers (hooks/lib.sh and its Python twin,
# hooks/claudesidion_paths.py) and for the bin/claudesidion command that skills call.

. "$(dirname "$0")/lib.sh"

printf '\033[1mpaths and the claudesidion command\033[0m\n'

CLI="$REPO_ROOT/bin/claudesidion"
# macOS's $TMPDIR ends in "/", so TEST_TMP holds a "//" that Python collapses and bash keeps.
TEST_TMP="$(python3 -c 'import os, sys; print(os.path.normpath(sys.argv[1]))' "$TEST_TMP")"

# in_home <home> <env assignments...> -- <command...> — run with an isolated HOME and no
# inherited OBSIDIAN_VAULT / CODE_ROOT / XDG_CONFIG_HOME.
in_home() {
  local home="$1"; shift
  local assigns=()
  while [ "$1" != "--" ]; do assigns+=("$1"); shift; done
  shift
  env -u OBSIDIAN_VAULT -u CODE_ROOT -u XDG_CONFIG_HOME HOME="$home" ${assigns[@]+"${assigns[@]}"} "$@"
}

sh_vault() { in_home "$1" "${@:2}" -- bash -c ". '$HOOKS/lib.sh'; resolve_vault"; }
sh_root()  { in_home "$1" "${@:2}" -- bash -c ". '$HOOKS/lib.sh'; resolve_code_root"; }
py_vault() { in_home "$1" "${@:2}" -- python3 "$CLI" vault-path; }
py_root()  { in_home "$1" "${@:2}" -- python3 "$CLI" code-root; }

# check_both <name> <want> <home> [env...] — shell and Python must both resolve to want.
check_both() {
  local name="$1" want="$2"; shift 2
  assert_eq "$want" "$(sh_vault "$@")" "shell: $name"
  assert_eq "$want" "$(py_vault "$@")" "python: $name"
}

# ---------------------------------------------------------------------------
section 'Vault path: env, then XDG config, then legacy ~/.claude, then default'
# ---------------------------------------------------------------------------

h="$TEST_TMP/h-default"; mkdir -p "$h"
check_both 'nothing configured: default' "$h/ObsidianVault" "$h"

h="$TEST_TMP/h-legacy"; mkdir -p "$h/.claude"
printf '%s\n' "$h/LegacyVault" > "$h/.claude/obsidian-vault"
check_both 'legacy file is still read' "$h/LegacyVault" "$h"

mkdir -p "$h/.config/claudesidion"
printf '%s\n' "$h/XdgVault" > "$h/.config/claudesidion/vault"
check_both 'XDG file wins over legacy' "$h/XdgVault" "$h"

check_both 'env var wins over both' "/env/vault" "$h" OBSIDIAN_VAULT=/env/vault

mkdir -p "$TEST_TMP/xdg/claudesidion"
printf '%s\n' "$TEST_TMP/CustomXdg" > "$TEST_TMP/xdg/claudesidion/vault"
check_both '$XDG_CONFIG_HOME is honoured' "$TEST_TMP/CustomXdg" "$h" XDG_CONFIG_HOME="$TEST_TMP/xdg"

h="$TEST_TMP/h-tilde"; mkdir -p "$h/.config/claudesidion"
printf '  ~/Notes/Vault  \n' > "$h/.config/claudesidion/vault"
check_both 'whitespace trimmed, leading ~ expanded' "$h/Notes/Vault" "$h"
# shellcheck disable=SC2016  # a literal $HOME is what the config file holds
printf '$HOME/V\n' > "$h/.config/claudesidion/vault"
check_both 'leading $HOME expanded' "$h/V" "$h"

h="$TEST_TMP/h-blank"; mkdir -p "$h/.config/claudesidion" "$h/.claude"
printf '   \n' > "$h/.config/claudesidion/vault"
printf '%s\n' "$h/LegacyVault" > "$h/.claude/obsidian-vault"
check_both 'a blank XDG file falls through to legacy' "$h/LegacyVault" "$h"

# ---------------------------------------------------------------------------
section 'Code root resolves the same way'
# ---------------------------------------------------------------------------

h="$TEST_TMP/h-root"; mkdir -p "$h/.claude"
assert_eq "$h/code" "$(sh_root "$h")" 'shell: default code root'
assert_eq "$h/code" "$(py_root "$h")" 'python: default code root'
# shellcheck disable=SC2088  # a literal ~ is what the config file holds
printf '~/src\n' > "$h/.claude/code-root"
assert_eq "$h/src" "$(sh_root "$h")" 'shell: legacy code-root file'
assert_eq "$h/src" "$(py_root "$h")" 'python: legacy code-root file'
mkdir -p "$h/.config/claudesidion"
# shellcheck disable=SC2088  # a literal ~ is what the config file holds
printf '~/projects\n' > "$h/.config/claudesidion/code-root"
assert_eq "$h/projects" "$(sh_root "$h")" 'shell: XDG code-root wins'
assert_eq "$h/projects" "$(py_root "$h")" 'python: XDG code-root wins'
assert_eq "/env/root" "$(py_root "$h" CODE_ROOT=/env/root)" 'python: CODE_ROOT wins'

# ---------------------------------------------------------------------------
section 'Hooks use the shared resolver'
# ---------------------------------------------------------------------------

h="$TEST_TMP/h-hook"; mkdir -p "$h/.config/claudesidion"
v="$(build_vault paths-hook)"
printf '%s\n' "$v" > "$h/.config/claudesidion/vault"
out="$(in_home "$h" -- bash "$HOOKS/vault-pull.sh" 2>&1)"
assert_contains "$out" 'pulled to latest' 'vault-pull finds the vault from the XDG config file'

# ---------------------------------------------------------------------------
section 'The claudesidion command'
# ---------------------------------------------------------------------------

assert_contains "$(python3 "$CLI" --help)" 'claudesidion rename' '--help lists the commands'
python3 "$CLI" no-such-command >/dev/null 2>&1
assert_eq 2 "$?" 'an unknown command exits 2'

v="$TEST_TMP/cli-vault"
mkdir -p "$v/Projects/Alpha/Notes"
printf '{"project": "alpha", "topics": {}}\n' > "$v/Projects/Alpha/.vault-config.json"
printf -- '---\ntype: note\nstatus: reference\n---\n\n# Old name\n' > "$v/Projects/Alpha/Notes/old-name.md"
printf -- '---\ntype: note\nstatus: reference\n---\n\n# Linker\n\nSee [[old-name]].\n' \
  > "$v/Projects/Alpha/Notes/Linker.md"

assert_contains "$(python3 "$CLI" lint --vault "$v")" 'bad-name' 'lint --vault reports findings'
assert_eq "$(python3 "$CLI" lint --vault "$v" --count)" \
  "$(in_home "$TEST_TMP" OBSIDIAN_VAULT="$v" -- python3 "$CLI" lint --count)" \
  'lint finds the vault without --vault'

python3 "$CLI" rename --vault "$v" Projects/Alpha/Notes/old-name.md Projects/Alpha/Notes/OldName.md >/dev/null
assert_file_exists "$v/Projects/Alpha/Notes/OldName.md" 'rename moves the note'
assert_contains "$(cat "$v/Projects/Alpha/Notes/Linker.md")" '[[OldName]]' 'rename rewrites links'

python3 "$CLI" maintain --vault "$v" >/dev/null
assert_file_exists "$v/Projects/Alpha/TopicIndex.md" 'maintain regenerates indexes'

# Through a symlink on PATH, the way a standalone skill install reaches it.
mkdir -p "$TEST_TMP/bin"
ln -s "$CLI" "$TEST_TMP/bin/claudesidion"
assert_eq "$(python3 "$CLI" lint --vault "$v" --count)" \
  "$(PATH="$TEST_TMP/bin:$PATH" claudesidion lint --vault "$v" --count)" \
  'works through a symlink on PATH'

# ---------------------------------------------------------------------------
section 'claudesidion start / end: the session hooks for any harness'
# ---------------------------------------------------------------------------

cs() { in_home "$TEST_TMP" OBSIDIAN_VAULT="$1" -- python3 "$CLI" "${@:2}"; }

v="$(build_vault cli-session)"
printf 'left behind\n' >> "$v/Projects/Note.md"
out="$(cs "$v" start --format plain)"
assert_contains "$out" 'not yet committed' 'start commits what an earlier session left'
assert_contains "$out" 'Vault pulled to latest' 'start pulls'
assert_eq "" "$(gitq "$v" status --porcelain -- Projects/Note.md)" 'start leaves the leftovers committed'

out="$(cs "$v" start)"
assert_eq 1 "$(printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(int("additionalContext" in d["hookSpecificOutput"]))' 2>/dev/null)" \
  'start defaults to one Claude Code JSON object'
out="$(cs "$v" start --format=cursor)"
assert_eq 1 "$(printf '%s' "$out" | python3 -c 'import json,sys; print(int("additional_context" in json.load(sys.stdin)))' 2>/dev/null)" \
  'start --format=cursor prints one additional_context object'
cs "$v" start --format bogus >/dev/null 2>&1
assert_eq 2 "$?" 'an unknown format exits 2'

printf 'written this session\n' >> "$v/Projects/Note.md"
cs "$v" end >/dev/null
assert_eq "" "$(gitq "$v" status --porcelain -- Projects)" 'end commits the session'
assert_eq 0 "$(git -C "$v" rev-list --count '@{upstream}..HEAD')" 'end pushes'

finish
