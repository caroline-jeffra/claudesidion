# Workspace templates

## Contents
- Index note (`Projects/_index.md`)
- Overview.md
- Progress Log.md
- `.vault-config.json`
- Worked examples

## Index note (`Projects/_index.md`)

Maps each repo to its workspace folder. Header + one row per repo:

```markdown
---
created: YYYY-MM-DD
tags: [index]
---

# Project Workspaces

| Repo path | Workspace |
|-----------|-----------|
| some-repo | [[Some-Repo/Home\|Some-Repo]] |
| /opt/src/odd-one | [[Odd-One/Home\|Odd-One]] |
```

### Paths are machine-relative

The vault syncs between machines, and an absolute path is only ever correct on one of them. So a
row's path is recorded **relative to that machine's code root**.

**Resolving the code root**, in order: the `CODE_ROOT` environment variable, then
`~/.claude/code-root` (one line, the root's path — whitespace trimmed, a leading `~/` or `$HOME/`
expanded), then the default `~/code`. This is deliberately the same three-tier shape as the vault
path, for the same reason: profile exports do not reach hook shells.

- **A relative row** (`some-repo`, `nested/some-repo`) resolves against the root. This is the normal
  form and what you write when adding a repo.
- **An absolute row** (`/opt/src/odd-one`) is matched literally, and is the escape hatch for a repo
  that does not live under the root. Never rewrite one into a relative path.

When adding a repo, take `git rev-parse --show-toplevel`; if it sits under the resolved root, record
the path **relative to the root**, otherwise record it absolute.

### Matching is two-stage

1. **Path match** — resolve each row (relative rows against the root, absolute rows as-is) and
   compare against the repo's absolute path.
2. **No match** → compare the repo's **basename** against each row's basename and the workspace
   names.
   - **Exactly one basename match** → check whether that row's recorded path resolves to something
     that **exists on this machine**.
     - **It does not exist** → the repo moved. Confirm in one line — "`app` is indexed at
       `code/app`, which is not here — same repo, moved?" — and on confirmation update the row.
     - **It does exist** → do **not** rewrite the row. You are on a different machine from the one
       that wrote it, or looking at a second checkout; rewriting is how the row ends up
       ping-ponging between machines on every sync. Use the workspace and change nothing.
   - **Several basename matches** → ask which, listing them. Do not guess.
   - **No basename match** → genuinely new. Scaffold and append a row.

### Never scaffold on a total miss

If **no row resolves at all** and the index is not empty, the code root is wrong or unset — every
relative row misses at once. That is a configuration problem, not a new repo.

Say so, name the root you resolved and where it came from, and **stop**. Do not scaffold: creating a
workspace here is exactly the split-brain this index exists to prevent, and it is unrecoverable
without a manual merge.

## Overview.md

```markdown
---
type: overview
status: active
---

# <repo>

**Repo path:** `/absolute/path/to/repo`

**Current focus:** <one line — what the work is right now>

## What this is
<A few sentences: what the codebase does, why the user is working on it.>

## Trackers
- Jira: <url or n/a>
- GitHub/GitLab: <url or n/a>

## Map
- [[Progress Log]] · [[Topic Index]] · [[Decisions Index]] · [[Threads Index]]
- `Decisions/` · `Threads/` · `Log/` · `Tickets/` · `Research/` · `Notes/`
```

## Progress Log.md

In a structured workspace this is an **index**: one line per working day, newest first. The detail
lives in `Log/YYYY-MM-DD.md`. Never append a dated section to this file.

```markdown
---
type: log-index
status: reference
---

# Progress Log — <repo>

One line per working day. Detail lives in the dated note.

```

Each line, newest first:

```markdown
- **[[YYYY-MM-DD]]** — <one-line summary of the day>
```

And the day's note itself, `Log/YYYY-MM-DD.md`:

```markdown
---
type: log
date: YYYY-MM-DD
---

# YYYY-MM-DD

- **Did:** <what changed>
- **Learned:** <what you now know that you did not before>
- **Next:** <the next step>
- **Links:** [[a-decision-note]], PR <url>
```

## `.vault-config.json`

Written at scaffold time; this file is what marks a workspace structured.

```json
{
  "project": "<short-slug>",
  "generated_types": ["index", "log-index"],
  "index_types": ["index", "log-index", "overview", "meta", "glossary", "summary"],
  "min_hits": 3,
  "title_weight": 4,
  "topics": {}
}
```

The folder skeleton is fixed by the contract and is not configured here. What varies per project is
the vocabulary: `topics`, `min_hits`, `title_weight`, and optionally `root_notes`.

## Worked examples

**A day's log** — `Log/2026-07-10.md`, with its one-line entry added to the root `Progress Log.md`:
```markdown
---
type: log
date: 2026-07-10
---

# 2026-07-10

- **Did:** Added Redis-backed rate limiter to the API gateway.
- **Learned:** Bursty clients were exhausting the DB connection pool; the limiter is the fix, not more pool headroom.
- **Next:** Load-test the 429 path and tune the window.
- **Links:** [[use-token-bucket-over-fixed-window]], PR #142
```

**A decision** — `Decisions/use-token-bucket-over-fixed-window.md`, one note per decision:
```markdown
---
type: decision
status: active
decided: 2026-07-10
---

# Use token-bucket over fixed-window

**Decision.** Rate limiting uses a token-bucket algorithm.

**Rationale.** Smooths bursts without the boundary spikes fixed-window allows.

**Alternatives considered.** Fixed-window — simpler, but double-rate at window edges. Leaky-bucket — rejected, no burst allowance the product wants.

**From:** [[2026-07-10]]
```

## `Tasks Archive.md` (vault root — create once per vault)

Lives at `$OBSIDIAN_VAULT/Tasks Archive.md`, not inside a workspace. Seed it with the frontmatter and
intro only; months and rows get appended as work happens.

```markdown
---
created: <YYYY-MM-DD>
tags: [index, archive]
---

# Tasks Archive

One line per working day, newest year first. This is the quick-reference for personal update meetings — scan a month, recall what you shipped.

Rows are deliberately **terse**: one short clause per project touched that day, three to four words each, at a very high level. No links inside table cells — the `Month's Projects` line above each table is where the project links live, and all detail lives in each project's `Progress Log`.

# <YYYY>

## <Mon YYYY>

### Month's Projects
[[<project>/Overview|<project>]]

| Date | Tasks |
| ---- | ----- |
| <d>  | <one 3–4 word clause per project touched, comma-separated, no links> |
```
