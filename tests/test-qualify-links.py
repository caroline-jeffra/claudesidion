#!/usr/bin/env python3
"""Tests for scripts/qualify_links.py — qualifying ambiguous wikilinks with their workspace path.

    python3 tests/test-qualify-links.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qualify_links as ql  # noqa: E402

PASS = 0
FAIL: list[str] = []


def check(cond: bool, name: str, detail: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"  \033[32mok\033[0m   {name}")
    else:
        FAIL.append(name)
        print(f"  \033[31mFAIL\033[0m {name}")
        if detail:
            print(f"       {detail}")


def section(t: str) -> None:
    print(f"\n\033[1m{t}\033[0m")


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


tmp = Path(tempfile.mkdtemp(prefix="claudesidion-ql-tests."))
try:
    v = tmp / "vault"
    for proj in ("Alpha", "Beta"):
        w = v / "Projects" / proj
        write(w / ".vault-config.json", json.dumps({"project": proj.lower(), "topics": {}}))
        write(w / "Overview.md", f"# {proj}\n")
        write(w / "Log" / "2026-10-01.md", "# day\n")
    a = v / "Projects" / "Alpha"
    write(a / "Log" / "2026-10-02.md", "# only Alpha\n")
    write(a / "Notes" / "Shared.md", "# Alpha shared\n")
    write(a / "Notes" / "Shared2.md", "# placeholder\n")
    write(v / "Projects" / "Beta" / "Notes" / "Shared.md", "# Beta shared\n")
    progress = (
        "# Progress\n\n"
        "- **[[2026-10-01]]** — bare\n"
        "- [[2026-10-01|that day]] and [[2026-10-01#Did]] and [[Log/2026-10-01]]\n"
        "- [[2026-10-02]] is unique; [[Alpha/Log/2026-10-01|ok]] is already qualified\n"
        "- [[Overview]] and ![[2026-10-01]] and `[[2026-10-01]]` in code\n"
        "| day | [[2026-10-01]] |\n"
        "```\n[[2026-10-01]]\n```\n"
    )
    write(a / "ProgressLog.md", progress)
    write(v / "Resources" / "Loose.md", "[[2026-10-01]] outside any workspace\n")
    write(v / "Archived" / "Projects" / "Old" / ".vault-config.json", "{}")

    section("Dry run")
    links, files, left = ql.qualify(v, dry_run=True)
    check(links > 0 and (a / "ProgressLog.md").read_text() == progress,
          "reports counts and writes nothing", f"{links} links")

    section("Each ambiguous link becomes its own workspace's note")
    links, files, left = ql.qualify(v)
    out = (a / "ProgressLog.md").read_text()
    check("- **[[Alpha/Log/2026-10-01|2026-10-01]]** — bare" in out, "bare link keeps its display text", out)
    check("[[Alpha/Log/2026-10-01|that day]]" in out, "an existing alias is kept")
    check("[[Alpha/Log/2026-10-01#Did|2026-10-01#Did]]" in out, "a heading link keeps its heading")
    check("[[Alpha/Log/2026-10-01|Log/2026-10-01]]" in out, "a partly qualified link is completed")
    check("[[2026-10-02]] is unique" in out, "a unique link is untouched")
    check("[[Alpha/Log/2026-10-01|ok]]" in out, "an already-qualified link is untouched")
    check("[[Alpha/Overview|Overview]]" in out, "a structural file is qualified")
    check("![[2026-10-01]]" in out, "embeds are untouched")
    check("`[[2026-10-01]]`" in out and "```\n[[2026-10-01]]\n```" in out, "code is untouched")
    check("| day | [[Alpha/Log/2026-10-01]] |" in out, "no alias is added inside a table", out)
    check((v / "Resources/Loose.md").read_text().startswith("[[2026-10-01]]"),
          "notes outside a workspace are untouched")
    check(not left, "nothing left unresolved", str(left))

    section("A second run changes nothing")
    links, files, left = ql.qualify(v)
    check(links == 0 and files == 0, "idempotent", f"{links} links in {files} files")

    section("No single home candidate is reported, not guessed")
    write(v / "Projects" / "Beta" / "Threads" / "Elsewhere.md", "[[Shared]] [[2026-10-02]]\n")
    write(v / "Projects" / "Gamma" / ".vault-config.json", json.dumps({"project": "g", "topics": {}}))
    write(v / "Projects" / "Gamma" / "Note.md", "[[Shared]]\n")
    links, files, left = ql.qualify(v)
    beta = (v / "Projects/Beta/Threads/Elsewhere.md").read_text()
    check("[[Beta/Notes/Shared|Shared]]" in beta, "a duplicate name resolves to the home workspace's copy", beta)
    check((v / "Projects/Gamma/Note.md").read_text() == "[[Shared]]\n"
          and any("Gamma/Note.md: [[Shared]]" in x for x in left),
          "a link with no copy in its own workspace is reported and left alone", str(left))

    section("CLI")
    rc = ql.main(["--vault", str(tmp / "nowhere")])
    check(rc == 2, "a missing vault exits 2", str(rc))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if not FAIL:
    print(f"\033[32m{PASS} passed\033[0m")
    sys.exit(0)
print(f"\033[31m{len(FAIL)} failed\033[0m, {PASS} passed")
for n in FAIL:
    print(f"  - {n}")
sys.exit(1)
