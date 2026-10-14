#!/usr/bin/env python3
"""Rename or move one vault note and rewrite every reference to it, vault-wide.

Used by `condense-vault` to fix `bad-name`, `legacy-name`, `dup-name` and `root-stray` findings.
Renaming a note by hand leaves every [[link]] to it broken, and a rename that rewrites only links
leaves `supersedes:` frontmatter pointing at a name that no longer exists. This does both.

    rename_note.py [--vault PATH] [--dry-run] "<old vault-relative path>" "<new vault-relative path>"

What it rewrites, in every note outside `Archived/` and dot-directories:

  * `[[Old]]`, `[[Old|alias]]`, `[[Old\\|alias]]` (inside a table), `[[Old#heading]]`, and the
    path-qualified forms `[[Folder/Old` that point at the renamed note.
  * `supersedes:` / `superseded_by:` frontmatter naming the note — scalar, inline list or block list.

Two rules keep it from rewriting links that meant a different note:

  * A link is rewritten only when it names the renamed note: its target is the end of that note's
    path (`[[Old]]`, `[[Log/Old]]`, `[[Alpha/Log/Old]]`), or its path is the note's folder or
    workspace (`[[Alpha/Old]]`).
  * If that target also names another note, the link is rewritten only inside the renamed note's
    own workspace (`Projects/<name>/`); elsewhere it may mean the other one.

Every rewritten link uses the shortest path that names the moved note and no other — bare when the
new name is unique, `[[Alpha/Log/2026-10-01]]` when it is not.

The file is moved with `git mv` when git tracks it, a plain move otherwise. Concurrent callers
are serialised with a lock, so parallel runs never interleave read-modify-write on one note.
Fails closed: a missing source or an existing target changes nothing.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))

from vault_maintain import shortest_ref, suffix_counts  # noqa: E402

SUPERSESSION_KEYS = ("supersedes", "superseded_by")


def resolve_vault(explicit: str | None) -> Path | None:
    """Same order as the hooks: --vault, $OBSIDIAN_VAULT, ~/.claude/obsidian-vault, default."""
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT", "").strip()
    if env:
        return Path(env).expanduser()
    cfg = Path.home() / ".claude" / "obsidian-vault"
    if cfg.is_file():
        line = cfg.read_text(encoding="utf-8").splitlines()[:1]
        if line and line[0].strip():
            raw = line[0].strip()
            if raw.startswith("$HOME"):
                raw = str(Path.home()) + raw[len("$HOME"):]
            return Path(raw).expanduser()
    return Path.home() / "ObsidianVault"


def is_versioned(vault: Path) -> bool:
    r = subprocess.run(["git", "-C", str(vault), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def is_tracked(vault: Path, rel: str) -> bool:
    """`git mv` refuses an untracked file — after the links are already rewritten — so check first."""
    r = subprocess.run(["git", "-C", str(vault), "ls-files", "--error-unmatch", "--", rel],
                       capture_output=True, text=True)
    return r.returncode == 0


def notes(vault: Path):
    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts) or rel.parts[0] == "Archived":
            continue
        if p.is_symlink():
            continue
        yield p, rel


def workspace_of(rel: Path) -> Path | None:
    return Path(*rel.parts[:2]) if rel.parts[0] == "Projects" and len(rel.parts) > 2 else None


def rewrite_supersession(text: str, old: str, new: str) -> str:
    """Rewrite the old name inside supersedes/superseded_by values, in any YAML list shape."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return text
    lines, key = m.group(1).split("\n"), None
    token = re.compile(r"(?<![\w-])" + re.escape(old) + r"(?![\w-])")
    for i, line in enumerate(lines):
        km = re.match(r"^([A-Za-z_][\w-]*):(.*)$", line)
        if km:
            key = km.group(1)
            if key in SUPERSESSION_KEYS:
                lines[i] = f"{key}:" + token.sub(new, km.group(2))
        elif key in SUPERSESSION_KEYS and re.match(r"^\s*-\s", line):
            lines[i] = token.sub(new, line)
    return "---\n" + "\n".join(lines) + "\n---\n" + text[m.end():]


def rename(vault: Path, old: str, new: str, dry_run: bool = False) -> tuple[int, int]:
    """Returns (links rewritten, files changed). Raises ValueError on a refused rename."""
    src, dst = vault / old, vault / new
    if not src.is_file():
        raise ValueError(f"no such note: {old}")
    if dst.exists():
        raise ValueError(f"target already exists: {new}")
    if dst.suffix != ".md":
        raise ValueError(f"target must be a .md file: {new}")

    old_name, new_name = src.stem, dst.stem
    rel = Path(old)
    ws = workspace_of(rel)
    shared = any(p != src for p in vault.rglob(src.name)
                 if not any(x.startswith(".") for x in p.relative_to(vault).parts))

    # Every note the vault's links can resolve to — Archived/ included, since links still reach it.
    paths = {
        r.with_suffix("").as_posix()
        for r in (p.relative_to(vault) for p in vault.rglob("*.md"))
        if not any(x.startswith(".") for x in r.parts)
    }
    old_rel, new_rel = rel.with_suffix("").as_posix(), Path(new).with_suffix("").as_posix()
    new_ref = shortest_ref(new_rel, suffix_counts((paths - {old_rel}) | {new_rel}))

    def named_by(target: str) -> list[str]:
        t = target.lower()
        return [p for p in paths if p.lower() == t or p.lower().endswith("/" + t)]

    # Path prefixes that can only mean this note: its own folder, and its workspace root.
    folders = [str(rel.parent)] + ([str(ws)] if ws else [])
    prefixes = set()
    for f in folders:
        if f and f != ".":
            prefixes.add(f + "/")
            prefixes.add(f.replace("Projects/", "", 1) + "/")

    link = re.compile(r"\[\[((?:[^\[\]|#\n]*/)?)" + re.escape(old_name) + r"(?=\]\]|\||\\\||#)")
    links = files = 0
    pending: list[tuple[Path, str]] = []
    for p, r in notes(vault):
        in_ws = ws is not None and r.is_relative_to(ws)
        text = p.read_text(encoding="utf-8")

        def sub(m: re.Match) -> str:
            nonlocal links
            pre = m.group(1)
            if pre not in prefixes:
                # Resolve the link the way a viewer does: by the end of the note's path. A
                # `[[Log/x]]` written in another workspace means that workspace's log, not this one.
                hits = named_by(pre + old_name)
                if old_rel not in hits or (len(hits) > 1 and not in_ws):
                    return m.group(0)
            links += 1
            return "[[" + new_ref

        out = link.sub(sub, text)
        if not shared or in_ws:
            out = rewrite_supersession(out, old_name, new_name)
        if out != text:
            files += 1
            pending.append((p, out))

    if dry_run:
        return links, files
    for p, out in pending:
        p.write_text(out, encoding="utf-8")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if is_versioned(vault) and is_tracked(vault, old):
        subprocess.run(["git", "-C", str(vault), "mv", old, new], check=True, capture_output=True)
    else:
        src.rename(dst)
    return links, files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--vault")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("old")
    ap.add_argument("new")
    a = ap.parse_args(argv)

    vault = resolve_vault(a.vault)
    if vault is None or not vault.is_dir():
        print(f"rename_note: vault not found: {vault}", file=sys.stderr)
        return 2
    vault = vault.resolve()
    key = hashlib.sha1(str(vault).encode()).hexdigest()[:12]
    with open(Path(tempfile.gettempdir()) / f"claudesidion-rename-{key}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            links, files = rename(vault, a.old, a.new, a.dry_run)
        except ValueError as exc:
            print(f"rename_note: {exc}", file=sys.stderr)
            return 1
    verb = "would rewrite" if a.dry_run else "rewrote"
    print(f"{a.old} -> {a.new}: {verb} {links} link(s) in {files} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
