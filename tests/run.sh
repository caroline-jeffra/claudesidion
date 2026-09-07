#!/usr/bin/env bash
# Run every tests/test-*.sh and report a combined result.
#
# Usage:
#   tests/run.sh              # run all suites
#   tests/run.sh vault-push   # run suites whose name matches
#
# Exits non-zero if any suite fails. Tier-1 suites are expected to fail until the
# corresponding Pre-Release Plan items are fixed; that is the point of committing them first.

set -u

cd "$(dirname "$0")/.." || exit 2

filter="${1-}"
suites=()
for f in tests/test-*.sh tests/test-*.py; do
  [ -e "$f" ] || continue
  if [ -n "$filter" ]; then
    case "$f" in *"$filter"*) suites+=("$f") ;; esac
  else
    suites+=("$f")
  fi
done

if [ "${#suites[@]}" -eq 0 ]; then
  printf 'no suites matched %s\n' "${filter:-(all)}" >&2
  exit 2
fi

# Syntax-check everything first — a suite that cannot parse is a harness bug, not a finding.
rc=0
for f in tests/lib.sh "${suites[@]}"; do
  case "$f" in
    *.py) python3 -c "import ast,sys;ast.parse(open(sys.argv[1]).read())" "$f" \
            || { printf 'syntax error: %s\n' "$f" >&2; rc=2; } ;;
    *)    bash -n "$f" || { printf 'syntax error: %s\n' "$f" >&2; rc=2; } ;;
  esac
done
[ "$rc" -eq 0 ] || exit "$rc"

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S warning hooks/*.sh tests/*.sh || rc=1
else
  printf 'note: shellcheck not installed, skipping lint\n'
fi

failed=()
for f in "${suites[@]}"; do
  case "$f" in
    *.py) python3 "$f" || failed+=("$f") ;;
    *)    bash "$f"    || failed+=("$f") ;;
  esac
done

printf '\n════════════════════════════════════════\n'
if [ "${#failed[@]}" -eq 0 ]; then
  printf '\033[32mall suites passed\033[0m\n'
  exit "$rc"
fi
printf '\033[31m%d suite(s) failed:\033[0m\n' "${#failed[@]}"
for f in "${failed[@]}"; do printf '  - %s\n' "$f"; done
exit 1
