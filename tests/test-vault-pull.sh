#!/usr/bin/env bash
# Regression tests for hooks/vault-pull.sh (SessionStart).
#
# The flush cases cover the failure this hook exists to backstop: vault-push.sh commits
# locally and then pushes, and session teardown can cancel it in the gap, stranding commits
# on this machine only. SessionStart has no teardown pressure, so the flush here is what
# actually gets them to the remote.

. "$(dirname "$0")/lib.sh"

printf '\033[1mvault-pull.sh\033[0m\n'

# strand <vault> <n> — make n local commits that the remote does not have.
strand() {
  local v="$1" n="$2" i
  for ((i = 1; i <= n; i++)); do
    printf 'stranded %s\n' "$i" >> "$v/Projects/note.md"
    gitq "$v" commit -qam "stranded $i"
  done
}

unpushed_ct() { git -C "$1" rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo 0; }

# ---------------------------------------------------------------------------
section 'Fail-open on missing preconditions'
# ---------------------------------------------------------------------------

run_hook_no_vault vault-pull.sh
assert_eq 0 "$HOOK_RC" 'no vault configured: exit 0'

run_hook vault-pull.sh "$TEST_TMP/does-not-exist"
assert_eq 0 "$HOOK_RC" 'vault path absent: exit 0'
assert_empty "$HOOK_OUT" 'vault path absent: silent'

v="$(build_vault pull-plain --no-git)"
run_hook vault-pull.sh "$v"
assert_eq 0 "$HOOK_RC" 'vault not a git repo: exit 0'
assert_empty "$HOOK_OUT" 'vault not a git repo: silent'

# ---------------------------------------------------------------------------
section 'Flushing commits stranded by a cancelled SessionEnd push'
# ---------------------------------------------------------------------------

v="$(build_vault pull-stranded)"
strand "$v" 2
assert_eq 2 "$(unpushed_ct "$v")" 'fixture: two commits are unpushed'
run_hook vault-pull.sh "$v"
assert_eq 0 "$HOOK_RC" 'stranded commits: exit 0'
assert_eq 0 "$(unpushed_ct "$v")" 'stranded commits are pushed to the remote'
assert_contains "$HOOK_OUT" 'stranded' 'the flush is reported, not silent'
assert_contains "$HOOK_OUT" '2' 'the report names how many commits were flushed'

v="$(build_vault pull-clean)"
run_hook vault-pull.sh "$v"
assert_eq 0 "$HOOK_RC" 'nothing stranded: exit 0'
assert_not_contains "$HOOK_OUT" 'stranded' 'nothing stranded: no flush claimed'
assert_contains "$HOOK_OUT" 'pulled to latest' 'nothing stranded: still reports the pull'

# A local-only vault has no upstream at all. The flush must not claim anything, and must not
# turn a legitimate offline vault into an error.
v="$(build_vault pull-noremote --no-remote)"
run_hook vault-pull.sh "$v"
assert_eq 0 "$HOOK_RC" 'no remote: exit 0'
assert_not_contains "$HOOK_OUT" 'stranded' 'no remote: no flush claimed'

# An unreachable remote must be reported as still-local, never as flushed — the whole point is
# that the user learns their notes are not backed up.
v="$(build_vault pull-deadremote)"
strand "$v" 1
gitq "$v" remote set-url origin "$TEST_TMP/no-such-remote.git"
run_hook vault-pull.sh "$v"
assert_eq 0 "$HOOK_RC" 'unreachable remote: exit 0'
assert_eq 1 "$(unpushed_ct "$v")" 'unreachable remote: commit stays local'
assert_contains "$HOOK_OUT" 'remain local-only' 'unreachable remote: reported as not backed up'

finish
