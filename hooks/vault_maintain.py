#!/usr/bin/env python3
"""Maintain a project workspace's derived metadata and indexes.

This is a MAINTENANCE tool, not a migration tool. It runs on every session end
against a workspace that already has the right shape, and it is deliberately
constrained:

  * It NEVER deletes a file, moves a file, or edits a note's body.
  * It only rewrites index notes, and only the frontmatter of ordinary notes.
  * Every write is compare-before-write, so a no-op run touches nothing.
  * It fails open: any unexpected error exits 0 with a message on stderr, so a
    bug here can never break a session or block the vault push.

What it does, per workspace:
  1. Reads every note's frontmatter.
  2. Fills in derived fields on notes that lack them — `type` (inferred from
     the folder the note is in), `topics` (matched from the workspace's topic
     vocabulary), and the derived `topic/*` / doctype tags.
  3. Regenerates the index notes from what it found.

A workspace opts in by containing a `.vault-config.json`. Workspaces without
one are ignored entirely, so this is safe to run across a mixed vault where
most projects still use the old flat layout.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- frontmatter

FM_START = "---\n"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (raw_frontmatter, body). Raw is '' when there is none."""
    if not text.startswith(FM_START):
        return "", text
    end = text.find("\n---\n", len(FM_START) - 1)
    if end == -1:
        return "", text
    return text[len(FM_START) : end + 1], text[end + 5 :]


def parse_frontmatter(raw: str) -> dict[str, object]:
    """Minimal YAML-subset parser covering inline lists AND block lists.

    Block lists matter: Obsidian's own property editor writes them, so a parser
    that only understands `[a, b]` silently drops tags the user added by hand.
    """
    out: dict[str, object] = {}
    key: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        block = re.match(r"^\s+-\s*(.*)$", line)
        if block and key:
            out.setdefault(key, [])
            if isinstance(out[key], list):
                out[key].append(_scalar(block.group(1)))
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest == "":
            out[key] = []          # a block list may follow
        elif rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            out[key] = [_scalar(x) for x in _split_inline(inner)] if inner else []
        else:
            out[key] = _scalar(rest)
    return out


def _split_inline(s: str) -> list[str]:
    """Split an inline list on commas that are not inside quotes."""
    parts, buf, quote = [], [], ""
    for ch in s:
        if quote:
            if ch == quote:
                quote = ""
            buf.append(ch)
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _scalar(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


# YAML 1.1 words that must be quoted or they stop being strings.
_YAML_RESERVED = {
    "true", "false", "yes", "no", "on", "off", "null", "none", "~",
    "y", "n",
}


def emit_scalar(value: str) -> str:
    """Quote a scalar whenever an unquoted form would change its meaning."""
    v = str(value)
    if v == "":
        return '""'
    if v.lower() in _YAML_RESERVED:
        return f'"{v}"'
    # A plain integer or decimal is left unquoted — these are real numeric fields
    # (counts, totals) and quoting them would change their type on every run.
    # Anything number-ish but not a clean number (leading zeros, underscores,
    # exponents, versions like 1.2.3) is quoted so it stays a string.
    if re.fullmatch(r"-?\d+(\.\d+)?", v) and not re.fullmatch(r"-?0\d+", v):
        return v
    if re.search(r"[:#\[\]{},&*?|<>=!%@`\"']", v) or v[0] in "-?%@`":
        esc = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{esc}"'
    return v


def _normalise_fm(raw: str) -> list[str]:
    """Comparable form of a frontmatter block: non-empty lines, trailing space stripped."""
    return [ln.rstrip() for ln in raw.strip().splitlines() if ln.strip()]


def frontmatter_roundtrips(raw: str) -> bool:
    """True when parse -> emit reproduces this frontmatter without losing anything.

    The parser here is a deliberately small YAML subset, which is fine for reading but
    dangerous for writing: `emit_frontmatter` writes back only what `parse_frontmatter`
    understood, so anything it could not represent is silently deleted from the user's
    file. Nested mappings vanish entirely; `key: |` block scalars keep the key and lose
    the body; comments disappear.

    Rather than grow the parser to cover all of YAML — where the next unhandled shape is
    always one plugin away — we check whether a round trip is faithful and decline to
    rewrite the note when it is not. A note the hook cannot represent is a note the hook
    has no business editing.
    """
    parsed = parse_frontmatter(raw)
    emitted = emit_frontmatter(parsed)
    # emit_frontmatter brackets its output with --- markers; compare only the fields.
    body = emitted.strip()
    if body.startswith("---"):
        body = body[3:]
    if body.endswith("---"):
        body = body[:-3]

    original = _normalise_fm(raw)
    produced = _normalise_fm(body)

    # A block list legitimately re-emits as an inline list, so compare semantically:
    # re-parse what we produced and require the same key/value mapping, AND require that
    # every source line is accounted for by some key we captured.
    if parse_frontmatter(body) != parsed:
        return False

    # Every non-empty source line must belong to a key we understood. A comment, a nested
    # mapping's child, or a block scalar's body will not, and that is the signal.
    known_keys = set(parsed)
    for line in original:
        stripped = line.strip()
        if stripped.startswith("#"):
            return False                       # comments are dropped by the emitter
        if stripped.startswith("- "):
            continue                           # block-list item, represented as a list
        key = line.split(":", 1)[0].strip()
        if line.startswith((" ", "\t")):
            return False                       # indented non-list line: nested structure
        if key not in known_keys:
            return False
        value = line.split(":", 1)[1].strip() if ":" in line else ""
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            return False                       # block scalar: body would be lost
    return True


def emit_frontmatter(fields: dict[str, object]) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, list):
            # Newlines inside a value would produce structurally invalid YAML.
            items = [emit_scalar(str(x).replace("\n", " ")) for x in v]
            lines.append(f"{k}: [{', '.join(items)}]")
        else:
            lines.append(f"{k}: {emit_scalar(str(v).replace(chr(10), ' '))}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------- config


@dataclass
class Config:
    project: str
    folders: dict[str, str]                  # doctype -> folder name
    root_notes: set[str]
    index_types: set[str]
    topics: dict[str, dict]                  # slug -> {name, gloss, patterns}
    generated_types: set[str] = field(default_factory=set)
    min_hits: int = 3
    title_weight: int = 4

    @classmethod
    def load(cls, path: Path) -> "Config":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            project=raw["project"],
            folders=raw.get("folders", {}),
            root_notes=set(raw.get("root_notes", [])),
            index_types=set(raw.get("index_types", [])),
            topics=raw.get("topics", {}),
            generated_types=set(raw.get("generated_types", ["index", "log-index"])),
            min_hits=raw.get("min_hits", 3),
            title_weight=raw.get("title_weight", 4),
        )

    def doctype_for_folder(self, folder: str) -> str | None:
        for doctype, name in self.folders.items():
            if name == folder:
                return doctype
        return None


# ---------------------------------------------------------------- topics


def score_topic(text: str, patterns: list[str], head: str, title_weight: int) -> int:
    total = 0
    for p in patterns:
        try:
            total += len(re.findall(p, text, re.I))
            total += title_weight * len(re.findall(p, head, re.I))
        except re.error:
            continue           # a bad pattern in config must not kill the run
    return total


def topics_for(cfg: Config, title: str, body: str, limit: int = 6) -> list[str]:
    head = title + "\n" + "\n".join(body.splitlines()[:12])
    text = title + "\n" + body
    scored = [
        (slug, score_topic(text, spec.get("patterns", []), head, cfg.title_weight))
        for slug, spec in cfg.topics.items()
    ]
    kept = sorted(
        [(s, n) for s, n in scored if n >= cfg.min_hits],
        key=lambda x: (-x[1], x[0]),
    )
    return sorted(s for s, _ in kept[:limit])


# ---------------------------------------------------------------- notes


@dataclass
class Note:
    path: Path
    name: str
    meta: dict[str, object]
    body: str
    doctype: str
    raw_fm: str = ""
    topics: list[str] = field(default_factory=list)
    changed: bool = False


def as_list(v: object) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if v in (None, ""):
        return []
    return [str(v)]


def collect(root: Path, cfg: Config) -> list[Note]:
    notes: list[Note] = []
    try:
        root_real = root.resolve()
    except OSError:
        return notes
    for p in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        # Never follow a link out of the workspace. rglob traverses symlinked files and
        # directories, so without this the pass will happily rewrite a file elsewhere on
        # disk — Obsidian users symlink shared folders between vaults routinely.
        if p.is_symlink():
            continue
        try:
            if not p.resolve().is_relative_to(root_real):
                continue
        except (OSError, ValueError):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        raw, body = split_frontmatter(text)
        meta = parse_frontmatter(raw)

        declared = str(meta.get("type", "") or "")
        folder = p.parent.name if p.parent != root else ""
        inferred = cfg.doctype_for_folder(folder) if folder else None
        # A declared type wins; otherwise infer from location. Root notes with
        # no declared type are left alone rather than guessed at.
        doctype = declared or inferred or ""

        notes.append(Note(p, p.stem, meta, body, doctype, raw_fm=raw))
    return notes


def refresh_metadata(notes: list[Note], cfg: Config) -> list[str]:
    """Fill derived frontmatter. Returns human-readable descriptions of changes."""
    changes: list[str] = []
    # Files this run regenerates wholesale. Touching their frontmatter here as
    # well makes the two writers fight: the builder adds its own fields, this
    # pass strips them as unknown, and every run reports a change forever.
    generated_files = {
        "Topic Index.md", "Tickets Index.md",
        "Threads Index.md", "Decisions Index.md",
    }

    for n in notes:
        if not n.doctype or n.path.name in generated_files:
            continue
        fields = dict(n.meta)
        before = dict(n.meta)

        fields["type"] = n.doctype
        fields["project"] = cfg.project

        # Generated indexes describe the workspace rather than a subject, so they
        # carry no topics. Other non-filed notes (a glossary, a summary) ARE
        # content and keep theirs.
        if n.doctype in cfg.generated_types:
            n.topics = []
            fields.pop("topics", None)
        else:
            existing = as_list(n.meta.get("topics"))
            # Respect a hand-curated topic list; only derive when absent.
            n.topics = existing or topics_for(cfg, n.name, n.body)
            # Drop topics that are no longer in the vocabulary.
            n.topics = [t for t in n.topics if t in cfg.topics]
            if n.topics:
                fields["topics"] = n.topics
            else:
                fields.pop("topics", None)

        # Derived tags are rebuilt from scratch each run so a renamed, merged or
        # retired topic never leaves a stale tag behind. Hand-added tags survive.
        derived = set(cfg.folders) | set(cfg.index_types) | {cfg.project}
        kept = [
            t
            for t in as_list(n.meta.get("tags"))
            if not t.startswith("topic/") and t not in derived
        ]
        tags = sorted(set(kept) | {cfg.project, n.doctype} | {f"topic/{t}" for t in n.topics})
        fields["tags"] = tags

        # T1.4: never rewrite a note whose frontmatter this parser cannot represent.
        # Doing so deletes whatever it did not understand — nested mappings, block
        # scalars, comments — from the user's file, with no backup and no signal.
        # Skipping means the note goes unmaintained, which is strictly better than
        # silently damaged.
        if fields != before and n.raw_fm and not frontmatter_roundtrips(n.raw_fm):
            changes.append(
                f"{n.path.name}: SKIPPED — frontmatter uses YAML this tool cannot "
                f"rewrite safely (nested keys, block scalars or comments); left untouched"
            )
            n.meta = before
            continue

        if fields != before:
            new_text = emit_frontmatter(fields) + "\n\n" + n.body.strip() + "\n"
            try:
                current = n.path.read_text(encoding="utf-8")
            except OSError:
                continue
            if new_text != current:
                n.path.write_text(new_text, encoding="utf-8")
                n.changed = True
                added = sorted(set(fields) - set(before))
                changes.append(
                    f"{n.path.name}: "
                    + (f"added {', '.join(added)}" if added else "updated frontmatter")
                )
        n.meta = fields
    return changes


# ---------------------------------------------------------------- indexes

TYPE_PLURAL = {
    "ticket": ("Ticket", "Tickets"),
    "epic": ("Epic", "Epics"),
    "research": ("Research", "Research"),
    "note": ("Note", "Notes"),
    "decision": ("Decision", "Decisions"),
    "convention": ("Convention", "Conventions"),
    "thread": ("Thread", "Threads"),
    "log": ("Log day", "Log days"),
}
TYPE_RANK = {
    "research": 0, "epic": 1, "ticket": 2, "note": 3,
    "decision": 4, "convention": 5, "thread": 6, "log": 7,
}


def label(doctype: str, n: int) -> str:
    pair = TYPE_PLURAL.get(doctype)
    if not pair:
        return doctype.replace("-", " ").title()
    return pair[1] if n != 1 else pair[0]


# Every generated index carries this marker. Its presence is what licenses an overwrite:
# a file at the same path WITHOUT it was written by someone, not by this tool.
GENERATED_MARKER = "_Generated —"


def write_if_changed(path: Path, content: str) -> bool:
    """Write a generated file, refusing to clobber one this tool did not author.

    T1.6: the index filenames are ordinary names a user may already have used. Overwriting
    a hand-written `Topic Index.md` destroys it with no backup — and the warning that edits
    are overwritten only appears in the file *after* it has already been overwritten.
    """
    content = content.rstrip() + "\n"
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                return False
            if GENERATED_MARKER not in existing:
                # Name the workspace, not just the file. Index filenames repeat across
                # workspaces, so a bare "Threads Index.md exists" in a multi-workspace run
                # is unattributable — the reader cannot tell which one to go and look at.
                print(
                    f"vault-maintain: {path.parent.name}: {path.name} exists and was not "
                    f"generated by this tool — not overwriting. Move or rename it to let "
                    f"the index generate.",
                    file=sys.stderr,
                )
                return False
    except OSError:
        pass
    path.write_text(content, encoding="utf-8")
    return True


def build_topic_index(root: Path, cfg: Config, notes: list[Note]) -> bool:
    by_topic: dict[str, list[Note]] = defaultdict(list)
    for n in notes:
        if n.doctype in cfg.generated_types:
            continue
        for t in n.topics:
            by_topic[t].append(n)

    lines = [
        emit_frontmatter(
            {
                "type": "index",
                "project": cfg.project,
                "tags": ["index", cfg.project],
                "topics_covered": len(by_topic),
            }
        ),
        "",
        "# Topic Index",
        "",
        "Every topic covered in this workspace, A–Z. Follow a topic to the notes "
        "that cover it. A note appears under each of its topics.",
        "",
        "Topics are also `topic/<name>` tags, so Obsidian's tag pane and search "
        "work on them directly.",
        "",
        "_Generated — edits here are overwritten. Change the topic vocabulary in "
        "`.vault-config.json`._",
        "",
    ]

    # A workspace can be structured before it has any topics — a new one starts
    # with an empty vocabulary and grows it. Say so, rather than rendering a
    # heading with nothing under it and looking broken.
    if not by_topic:
        lines += [
            "## No topics yet",
            "",
            "This workspace has no topic vocabulary defined, so there is nothing to index yet.",
            "",
            "Add topics to `.vault-config.json` once three or four notes would share one — "
            "earlier than that and a topic is noise. The next session-end run picks them up and "
            "fills this page in.",
        ]
        return write_if_changed(root / "Topic Index.md", "\n".join(lines))

    ordered = sorted(by_topic, key=lambda s: cfg.topics[s]["name"].lower())
    letters = sorted({cfg.topics[s]["name"][0].upper() for s in ordered})
    lines.append(" · ".join(f"[[#{l}]]" for l in letters))
    lines.append("")

    current = ""
    for slug in ordered:
        spec = cfg.topics[slug]
        letter = spec["name"][0].upper()
        if letter != current:
            current = letter
            lines += [f"## {letter}", ""]

        group = by_topic[slug]
        lines += [f"### {spec['name']}", ""]
        if spec.get("gloss"):
            lines += [f"*{spec['gloss']}*", ""]
        lines += [f"Tag: `#topic/{slug}` — {len(group)} notes", ""]

        buckets: dict[str, list[Note]] = defaultdict(list)
        for n in group:
            buckets[n.doctype].append(n)

        for doctype in sorted(buckets, key=lambda d: TYPE_RANK.get(d, 9)):
            items = sorted(buckets[doctype], key=lambda n: n.name.lower())
            if doctype == "log":
                days = " · ".join(
                    f"[[{n.name}]]" for n in sorted(items, key=lambda x: x.name, reverse=True)
                )
                lines += [f"**Log days** ({len(items)}) — {days}", ""]
                continue
            lines += [f"**{label(doctype, len(items))}** ({len(items)})", ""]
            lines += [f"- [[{n.name}]]" for n in items]
            lines.append("")

    return write_if_changed(root / "Topic Index.md", "\n".join(lines))


def build_ticket_index(root: Path, cfg: Config, notes: list[Note]) -> bool:
    pattern = re.compile(r"^([A-Z]{2,}-\d+)\b")
    by_ticket: dict[str, list[Note]] = defaultdict(list)
    for n in notes:
        if n.doctype in cfg.generated_types:
            continue
        for t in as_list(n.meta.get("tickets")):
            by_ticket[t].append(n)

    owned: dict[str, Note] = {}
    for n in notes:
        m = pattern.match(n.name)
        if m:
            prev = owned.get(m.group(1))
            if prev is None or len(n.name) < len(prev.name):
                owned[m.group(1)] = n

    lines = [
        emit_frontmatter(
            {"type": "index", "project": cfg.project, "tags": ["index", cfg.project]}
        ),
        "",
        "# Tickets Index",
        "",
        "Every ticket mentioned in this workspace, and the notes that mention it. "
        "A ticket with its own note is shown in bold.",
        "",
        "_Generated — edits here are overwritten._",
        "",
    ]

    def sort_key(t: str) -> tuple:
        digits = re.sub(r"\D", "", t)
        return (-int(digits) if digits else 0, t)

    for t in sorted(by_ticket, key=sort_key):
        uniq = {n.name: n for n in by_ticket[t]}.values()
        group = sorted(uniq, key=lambda n: (TYPE_RANK.get(n.doctype, 9), n.name.lower()))
        own = owned.get(t)
        head = f"**[[{own.name}|{t}]]**" if own else f"`{t}`"
        refs = [n for n in group if n is not own]
        docs = [n for n in refs if n.doctype != "log"]
        logs = [n for n in refs if n.doctype == "log"]
        bits = [f"[[{n.name}]]" for n in docs[:6]]
        if logs:
            bits.append(f"{len(logs)} log day{'s' if len(logs) != 1 else ''}")
        lines.append(f"- {head}" + (" — " + ", ".join(bits) if bits else ""))

    return write_if_changed(root / "Tickets Index.md", "\n".join(lines))


def link(n: Note) -> str:
    """A wikilink carrying a readable display title.

    Note names are slugs, so a bare `[[slug]]` renders as `bert-9534-lefty-offers-...`.
    Where the note has a title, use `[[slug|Title]]` so the index reads as prose.
    """
    title = str(n.meta.get("title", "") or "").strip()
    if not title:
        for line in n.body.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
    return f"[[{n.name}|{title}]]" if title and title != n.name else f"[[{n.name}]]"


def open_items(n: Note) -> int:
    """Count unchecked task boxes in a note's body.

    A thread's whole purpose is the work still outstanding, so the index leads with that
    number. Checked boxes and prose are ignored; a thread with no boxes reports zero.
    """
    return len(re.findall(r"^\s*[-*]\s+\[ \]", n.body, re.MULTILINE))


def build_thread_index(root: Path, cfg: Config, notes: list[Note]) -> bool:
    """Threads, open work first.

    This is the file `manage-project-workspaces` reads first to answer "what's next", so
    ordering is the feature: threads with outstanding items come first, most-open first,
    and finished threads sink to a separate section.
    """
    threads = [n for n in notes if n.doctype == "thread"]

    live, finished = [], []
    for n in threads:
        (finished if str(n.meta.get("status", "")).lower() == "done" else live).append(n)

    live.sort(key=lambda n: (-open_items(n), n.name.lower()))
    finished.sort(key=lambda n: n.name.lower())

    lines = [
        emit_frontmatter(
            {"type": "index", "project": cfg.project, "tags": ["index", cfg.project]}
        ),
        "",
        "# Threads Index",
        "",
        "Every thread of unfinished work, most open items first.",
        "",
        "_Generated — edits here are overwritten._",
        "",
    ]

    if not threads:
        lines.append("_No threads yet._")
        return write_if_changed(root / "Threads Index.md", "\n".join(lines))

    if live:
        lines.append("## Open")
        lines.append("")
        for n in live:
            count = open_items(n)
            head = f"**{count} open**" if count else f"_{n.meta.get('status', 'open')}_"
            lines.append(f"- {head} — {link(n)}")
        lines.append("")

    if finished:
        lines.append("## Closed")
        lines.append("")
        lines += [f"- {link(n)}" for n in finished]
        lines.append("")

    return write_if_changed(root / "Threads Index.md", "\n".join(lines))


def build_decision_index(root: Path, cfg: Config, notes: list[Note]) -> bool:
    """Decisions and conventions, grouped by whether they are still in force.

    Superseded decisions are listed, never hidden: the record of what was true before is
    what stops a stale claim being read as current.
    """
    items = [n for n in notes if n.doctype in ("decision", "convention")]


    lines = [
        emit_frontmatter(
            {"type": "index", "project": cfg.project, "tags": ["index", cfg.project]}
        ),
        "",
        "# Decisions Index",
        "",
        "Every decision and standing convention, grouped by status.",
        "",
        "_Generated — edits here are overwritten._",
        "",
    ]

    if not items:
        lines.append("_No decisions recorded yet._")
        return write_if_changed(root / "Decisions Index.md", "\n".join(lines))

    decisions = [n for n in items if n.doctype == "decision"]
    conventions = [n for n in items if n.doctype == "convention"]

    def when(n: Note) -> str:
        for key in ("decided", "date", "created"):
            v = n.meta.get(key)
            if v:
                return str(v)[:10]
        return ""

    if decisions:
        lines.append("## Dated decisions")
        lines.append("")
        # Newest first; undated decisions sort to the end rather than pretending to a date.
        for n in sorted(decisions, key=lambda n: (when(n) == "", when(n)), reverse=True):
            d = when(n)
            stamp = f"`{d}` " if d else ""
            tail = " _(superseded)_" if str(n.meta.get("status", "")).lower() == "superseded" else ""
            # The tickets a decision came out of are context its title does not carry, and
            # the only link back to the work that prompted it.
            tickets = as_list(n.meta.get("tickets"))
            refs = f" · {', '.join(tickets)}" if tickets else ""
            lines.append(f"- {stamp}{link(n)}{tail}{refs}")
        lines.append("")

    if conventions:
        lines.append("## Standing conventions")
        lines.append("")
        for n in sorted(conventions, key=lambda n: n.name.lower()):
            tail = " _(superseded)_" if str(n.meta.get("status", "")).lower() == "superseded" else ""
            lines.append(f"- {link(n)}{tail}")
        lines.append("")

    return write_if_changed(root / "Decisions Index.md", "\n".join(lines))


# ---------------------------------------------------------------- main


def maintain(root: Path) -> list[str]:
    cfg_path = root / ".vault-config.json"
    if not cfg_path.is_file():
        return []
    cfg = Config.load(cfg_path)

    notes = collect(root, cfg)
    if not notes:
        return []

    messages = refresh_metadata(notes, cfg)
    if build_topic_index(root, cfg, notes):
        messages.append("Topic Index.md regenerated")
    if build_ticket_index(root, cfg, notes):
        messages.append("Tickets Index.md regenerated")
    if build_thread_index(root, cfg, notes):
        messages.append("Threads Index.md regenerated")
    if build_decision_index(root, cfg, notes):
        messages.append("Decisions Index.md regenerated")
    return messages


# How deep to look for workspaces. `Projects/<name>/` is depth 2 and the documented layout;
# the extra levels cover a vault organised by client or team, and the root covers a vault that
# is itself a single workspace. Bounded so a vault with a large attachment tree is not walked
# in full on every session start.
MAX_WORKSPACE_DEPTH = 4


def find_workspaces(vault: Path) -> list[Path]:
    """Every directory holding a .vault-config.json, from the vault root down.

    Walks rather than globbing one depth: a config at the root, at depth 1, or nested under an
    organising folder was previously ignored in silence, which looks exactly like the hook
    being broken. Dot-directories are skipped — `.git` and `.obsidian` are not workspaces, and
    the old `*/*/` glob happily matched `.git/hooks/.vault-config.json`.

    A workspace found inside another is still reported: its config is an explicit statement
    that it is a workspace, and `collect()` scopes each one to its own tree.
    """
    found: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        if (d / ".vault-config.json").is_file():
            found.append(d)
        if depth >= MAX_WORKSPACE_DEPTH:
            return
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for child in entries:
            if child.name.startswith("."):
                continue
            # is_dir() follows symlinks; a link out of the vault is not ours to maintain.
            if child.is_symlink() or not child.is_dir():
                continue
            walk(child, depth + 1)

    walk(vault, 0)
    return sorted(found)


def main() -> int:
    vault = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if vault is None or not vault.is_dir():
        print("usage: vault_maintain.py <vault-path>", file=sys.stderr)
        return 0                      # fail open

    total: list[str] = []
    for ws in find_workspaces(vault):
        try:
            msgs = maintain(ws)
        except Exception as exc:                       # noqa: BLE001 - fail open
            print(f"vault-maintain: {ws.name}: {exc}", file=sys.stderr)
            continue
        total += [f"{ws.name}: {m}" for m in msgs]

    if total:
        print(f"vault-maintain: {len(total)} update(s)")
        for m in total[:20]:
            print(f"  {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
