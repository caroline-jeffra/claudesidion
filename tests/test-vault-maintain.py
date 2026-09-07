#!/usr/bin/env python3
"""Regression tests for hooks/vault_maintain.py.

Cases marked [T1.x] correspond to Pre-Release Plan tier-1 items. Run directly:

    python3 tests/test-vault-maintain.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS))

import vault_maintain as vm  # noqa: E402


def run_maintain(vault: Path) -> None:
    """Invoke the hook's entry point the way the real hook does (argv-driven)."""
    argv = sys.argv
    sys.argv = ["vault_maintain.py", str(vault)]
    try:
        vm.main()
    finally:
        sys.argv = argv

PASS = 0
FAIL: list[str] = []


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  \033[32mok\033[0m   {name}")


def bad(name: str, detail: str = "") -> None:
    FAIL.append(name)
    print(f"  \033[31mFAIL\033[0m {name}")
    if detail:
        print(f"       {detail}")


def check(cond: bool, name: str, detail: str = "") -> None:
    ok(name) if cond else bad(name, detail)


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


# ---------------------------------------------------------------------------
section("[T1.4] Frontmatter must round-trip or the note is left alone")
# ---------------------------------------------------------------------------

# Each of these is YAML the hand-rolled parser cannot represent. The rule is not
# "parse it correctly" — it is "notice you cannot, and do not rewrite the file".
LOSSY = {
    "nested mapping": "nested:\n  key: value\n  deep:\n    more: 1\n",
    "block scalar": "multiline: |\n  line one\n  line two\n",
    "folded scalar": "description: >\n  folded text here\n",
    "comment line": "# a comment worth keeping\nkey: val\n",
    "nested list of maps": "items:\n  - name: a\n    id: 1\n",
}

for label, raw in LOSSY.items():
    check(
        not vm.frontmatter_roundtrips(raw),
        f"[T1.4] {label}: detected as not round-tripping",
        f"parser claims it can represent {raw!r}",
    )

SAFE = {
    "inline list": "tags: [a, b]\ntype: note\n",
    "block list": "tags:\n  - a\n  - b\n",
    "plain scalars": "type: decision\nstatus: active\n",
    "quoted colon": 'title: "a: b"\ntype: note\n',
    "empty then block list": "topics:\n  - one\n",
}

for label, raw in SAFE.items():
    check(
        vm.frontmatter_roundtrips(raw),
        f"[T1.4] {label}: recognised as safe to rewrite",
        "guard is too strict; this shape is representable",
    )

# ---------------------------------------------------------------------------
section("[T1.4] End to end: a lossy note survives a maintenance run")
# ---------------------------------------------------------------------------

tmp = Path(tempfile.mkdtemp(prefix="claudesidion-vm-tests."))
try:
    ws = tmp / "Projects" / "Demo"
    (ws / "Notes").mkdir(parents=True)
    (ws / ".vault-config.json").write_text(
        '{"project":"demo","folders":{"note":"Notes"},"topics":{},'
        '"root_notes":[],"index_types":[],"generated_types":["index"]}',
        encoding="utf-8",
    )

    lossy = ws / "Notes" / "has-nested.md"
    lossy_text = (
        "---\n"
        "type: note\n"
        "status: reference\n"
        "dataview:\n"
        "  table: true\n"
        "  columns:\n"
        "    - file\n"
        "---\n\n"
        "# Nested\n\nBody text.\n"
    )
    lossy.write_text(lossy_text, encoding="utf-8")

    plain = ws / "Notes" / "plain.md"
    plain.write_text(
        "---\ntype: note\nstatus: reference\n---\n\n# Plain\n\nBody.\n", encoding="utf-8"
    )

    run_maintain(tmp)

    check(
        lossy.read_text(encoding="utf-8") == lossy_text,
        "[T1.4] note with nested frontmatter is byte-identical after a run",
        "the maintenance pass rewrote a note it could not represent",
    )
    check(
        "dataview" in lossy.read_text(encoding="utf-8"),
        "[T1.4] nested key survived",
    )
    check(
        "tags:" in plain.read_text(encoding="utf-8"),
        "[T1.4] a representable note is still maintained normally",
        "the guard is suppressing legitimate work",
    )

    # ---------------------------------------------------------------------
    section("[T1.5] Writes must stay inside the workspace")
    # ---------------------------------------------------------------------

    outside = tmp / "outside.md"
    outside_text = "---\ntype: note\nstatus: reference\n---\n\n# Outside\n"
    outside.write_text(outside_text, encoding="utf-8")
    link = ws / "Notes" / "linked.md"
    try:
        link.symlink_to(outside)
        run_maintain(tmp)
        check(
            outside.read_text(encoding="utf-8") == outside_text,
            "[T1.5] file outside the vault reached via symlink is not rewritten",
            "the maintenance pass followed a symlink out of the workspace",
        )
    except OSError:
        ok("[T1.5] symlink test skipped (unsupported on this filesystem)")

    # ---------------------------------------------------------------------
    section("[T1.6] Generated indexes must not clobber hand-written files")
    # ---------------------------------------------------------------------

    hand = ws / "Topic Index.md"
    hand_text = "# Topic Index\n\nMy own carefully curated links.\n"
    hand.write_text(hand_text, encoding="utf-8")
    run_maintain(tmp)
    check(
        hand.read_text(encoding="utf-8") == hand_text,
        "[T1.6] pre-existing Topic Index.md without the generated marker is preserved",
        "the hook overwrote a file the user wrote by hand",
    )

    # The refusal must say WHICH workspace: index filenames repeat across workspaces, so a
    # bare filename in a multi-workspace run cannot be traced back to a directory.
    import io, contextlib
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        run_maintain(tmp)
    msg = err.getvalue()
    check(
        "Demo" in msg and "Topic Index.md" in msg,
        "[T1.6] the refusal names the workspace, not just the file",
        f"stderr was: {msg!r}",
    )
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
section("[T2.1] Threads and Decisions indexes are generated")
# ---------------------------------------------------------------------------

tmp2 = Path(tempfile.mkdtemp(prefix="claudesidion-vm-t21."))
try:
    ws = tmp2 / "Projects" / "Demo"
    for folder in ("Threads", "Decisions", "Notes"):
        (ws / folder).mkdir(parents=True)
    (ws / ".vault-config.json").write_text(
        '{"project":"demo","folders":{"thread":"Threads","decision":"Decisions",'
        '"convention":"Decisions","note":"Notes"},"topics":{},'
        '"root_notes":[],"index_types":[],"generated_types":["index"]}',
        encoding="utf-8",
    )

    (ws / "Threads" / "Flaky deploys.md").write_text(
        "---\ntype: thread\nstatus: open\n---\n\n# Flaky deploys\n\n"
        "- [ ] one\n- [x] two\n- [ ] three\n",
        encoding="utf-8",
    )
    (ws / "Threads" / "Old cleanup.md").write_text(
        "---\ntype: thread\nstatus: done\n---\n\n# Old cleanup\n\n- [x] all done\n",
        encoding="utf-8",
    )
    (ws / "Decisions" / "Use Postgres.md").write_text(
        "---\ntype: decision\nstatus: active\ntickets: [ACME-1234, ACME-5678]\n---\n\n# Use Postgres\n",
        encoding="utf-8",
    )
    (ws / "Decisions" / "Use MySQL.md").write_text(
        "---\ntype: decision\nstatus: superseded\n---\n\n# Use MySQL\n",
        encoding="utf-8",
    )
    (ws / "Decisions" / "Trunk based.md").write_text(
        "---\ntype: convention\nstatus: active\n---\n\n# Trunk based\n",
        encoding="utf-8",
    )

    run_maintain(tmp2)

    threads_idx = ws / "Threads Index.md"
    dec_idx = ws / "Decisions Index.md"

    check(threads_idx.is_file(), "[T2.1] Threads Index.md is created")
    check(dec_idx.is_file(), "[T2.1] Decisions Index.md is created")

    if threads_idx.is_file():
        t = threads_idx.read_text(encoding="utf-8")
        check(vm.GENERATED_MARKER in t, "[T2.1] Threads Index carries the generated marker")
        check("Flaky deploys" in t, "[T2.1] Threads Index lists an open thread")
        check("Old cleanup" in t, "[T2.1] Threads Index lists a done thread")
        check("2" in t, "[T2.1] Threads Index reports an open count",
              "expected the 2 unchecked boxes of 'Flaky deploys' to be counted")

    if dec_idx.is_file():
        d = dec_idx.read_text(encoding="utf-8")
        check(vm.GENERATED_MARKER in d, "[T2.1] Decisions Index carries the generated marker")
        check("Use Postgres" in d, "[T2.1] Decisions Index lists an active decision")
        check("Use MySQL" in d, "[T2.1] Decisions Index lists a superseded decision")
        check("Trunk based" in d, "[T2.1] Decisions Index lists conventions too")
        # Ticket references are the one piece of a decision's context that is not in its
        # title; dropping them loses the link back to the work that prompted it.
        check("ACME-1234" in d and "ACME-5678" in d,
              "[T2.1] Decisions Index carries ticket references",
              "tickets: frontmatter was not surfaced in the index")

    # The indexes are themselves generated: they must not be swept into their own listing,
    # nor have their frontmatter rewritten by the metadata pass on the next run.
    before = (threads_idx.read_text(encoding="utf-8") if threads_idx.is_file() else "")
    run_maintain(tmp2)
    after = (threads_idx.read_text(encoding="utf-8") if threads_idx.is_file() else "")
    check(before == after, "[T2.1] a second run is a no-op on Threads Index",
          "the two writers are fighting over this file")

    # T1.6 protection must extend to the new indexes.
    hand = ws / "Decisions Index.md"
    hand.write_text("# Decisions Index\n\nHand written.\n", encoding="utf-8")
    run_maintain(tmp2)
    check(
        hand.read_text(encoding="utf-8") == "# Decisions Index\n\nHand written.\n",
        "[T2.1] an un-marked Decisions Index.md is not clobbered",
    )
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ---------------------------------------------------------------------------
section("[T2.9] Workspace discovery is not pinned to one depth")
# ---------------------------------------------------------------------------

tmp3 = Path(tempfile.mkdtemp(prefix="claudesidion-vm-t29."))
try:
    CFG = ('{"project":"%s","folders":{"note":"Notes"},"topics":{},'
           '"root_notes":[],"index_types":[],"generated_types":["index"]}')

    # One workspace at each plausible depth, including the documented depth 2.
    places = {
        "root":   tmp3,
        "d1":     tmp3 / "Solo",
        "d2":     tmp3 / "Projects" / "Demo",
        "d3":     tmp3 / "Projects" / "Clients" / "Deep",
    }
    for name, ws in places.items():
        (ws / "Notes").mkdir(parents=True, exist_ok=True)
        (ws / ".vault-config.json").write_text(CFG % name, encoding="utf-8")
        (ws / "Notes" / "a.md").write_text(
            "---\ntype: note\nstatus: reference\n---\n\n# A\n", encoding="utf-8"
        )

    found = set(vm.find_workspaces(tmp3))
    for name, ws in places.items():
        check(ws in found, f"[T2.9] workspace at {name} is discovered",
              f"find_workspaces missed {ws}")

    # A nested workspace must not be claimed by its parent: the outer one owns its own
    # notes only, or the inner workspace's notes get indexed twice under two projects.
    check(
        len(found) == len(places),
        "[T2.9] each config yields exactly one workspace",
        f"expected {len(places)}, got {len(found)}: {sorted(map(str, found))}",
    )

    # .git and other dot-directories must never be walked.
    (tmp3 / ".git" / "hooks").mkdir(parents=True)
    (tmp3 / ".git" / "hooks" / ".vault-config.json").write_text(CFG % "git", encoding="utf-8")
    (tmp3 / ".obsidian").mkdir(exist_ok=True)
    (tmp3 / ".obsidian" / ".vault-config.json").write_text(CFG % "obs", encoding="utf-8")
    found2 = set(vm.find_workspaces(tmp3))
    check(
        not any(".git" in p.parts or ".obsidian" in p.parts for p in found2),
        "[T2.9] dot-directories are not searched",
        f"walked into a dot-directory: {sorted(map(str, found2))}",
    )
finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# ---------------------------------------------------------------------------
section("Folder skeleton is fixed by the contract, not by config")
# ---------------------------------------------------------------------------

# New workspaces omit "folders" entirely: the skeleton is fixed by the workspace
# contract. If the default went missing, a note in Log/ with no declared type: would
# stop being inferred as a log, and every doctype tag would silently disappear.
tmp4 = Path(tempfile.mkdtemp(prefix="claudesidion-vm-tests."))
try:
    ws = tmp4 / "Projects" / "Demo"
    (ws / "Log").mkdir(parents=True)
    (ws / "Decisions").mkdir(parents=True)
    # No "folders" key at all — exactly what scaffolding now writes.
    (ws / ".vault-config.json").write_text(
        json.dumps({"project": "demo", "topics": {}}), encoding="utf-8"
    )
    cfg = vm.Config.load(ws / ".vault-config.json")

    check(cfg.folders != {}, "folders defaults when the key is absent",
          "config with no folders key produced an empty map")
    check(cfg.doctype_for_folder("Log") == "log",
          "Log/ still infers type log", f"got {cfg.doctype_for_folder('Log')!r}")
    check(cfg.doctype_for_folder("Decisions") == "decision",
          "Decisions/ still infers type decision",
          f"got {cfg.doctype_for_folder('Decisions')!r}")
    check(cfg.doctype_for_folder("Threads") == "thread",
          "Threads/ still infers type thread",
          f"got {cfg.doctype_for_folder('Threads')!r}")

    # An explicit folders map must still win, so pre-contract workspaces keep working.
    (ws / ".vault-config.json").write_text(
        json.dumps({"project": "demo", "topics": {}, "folders": {"log": "Journal"}}),
        encoding="utf-8",
    )
    cfg2 = vm.Config.load(ws / ".vault-config.json")
    check(cfg2.doctype_for_folder("Journal") == "log",
          "an explicit folders map still overrides the default",
          f"got {cfg2.doctype_for_folder('Journal')!r}")
finally:
    shutil.rmtree(tmp4, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
if not FAIL:
    print(f"\033[32m{PASS} passed\033[0m")
    sys.exit(0)
print(f"\033[31m{len(FAIL)} failed\033[0m, {PASS} passed")
for n in FAIL:
    print(f"  - {n}")
sys.exit(1)
