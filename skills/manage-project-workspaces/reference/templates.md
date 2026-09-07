# Workspace templates

## Contents
- Index note (`Projects/_index.md`)
- Overview.md
- Progress Log.md
- `.vault-config.json`
- Decisions.md / Open Threads.md — **retired flat templates, kept for reading existing workspaces**
- Worked examples

New workspaces are scaffolded **structured** (see
[structure.md](structure.md)). The flat templates below are retained only so existing flat
workspaces stay readable until they are migrated; do not create a new workspace from them.

## Index note (`Projects/_index.md`)

Maps each repo's absolute path to its workspace folder. Header + one row per repo:

```markdown
---
created: YYYY-MM-DD
tags: [index]
---

# Project Workspaces

| Repo path | Workspace |
|-----------|-----------|
| /absolute/path/to/some-repo | [[some-repo/Overview\|some-repo]] |
```

When adding a repo, append a row recording the absolute path from `git rev-parse --show-toplevel`.

**Matching is two-stage, because absolute paths do not survive.** The vault syncs between machines
and repos get moved; `/Users/ada/code/app` on one machine is `/home/ada/src/app` on another. Treating
a path miss as "no workspace" scaffolds a *second* workspace for a repo that already has one — the
split-brain this index exists to prevent.

1. **Exact absolute path match** → use it.
2. **No match** → compare the repo's **basename** against the basename of each indexed path, and
   against the workspace names.
   - **Exactly one basename match** → almost certainly the same repo, moved. Say so and confirm in
     one line: "`app` is indexed at `/home/ada/src/app`, which no longer exists — same repo, moved?"
     On confirmation, **update the existing row's path** and carry on. Never create a second row.
   - **Several basename matches** → ask which, listing them. Do not guess.
   - **No basename match** → genuinely new. Scaffold and append a row.

The one thing never to do is scaffold silently after a path miss when a basename match exists.

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

## Retired flat templates

The two templates below build the stacked files of the **flat** layout. They are retired: new
workspaces never use them. They remain documented so an existing flat workspace can still be read.

## Decisions.md

```markdown
---
created: YYYY-MM-DD
tags: [project, decisions]
---

# Decisions — <repo>
```

Each entry:

```markdown
## YYYY-MM-DD — <short decision title>

- **Decision:** <what was decided>
- **Rationale:** <why>
- **Alternatives:** <what was considered and rejected>
- **From:** [[Progress Log#YYYY-MM-DD]]
```

## Open Threads.md

```markdown
---
created: YYYY-MM-DD
tags: [project, todo]
---

# Open Threads — <repo>

## Open
- [ ] <blocker / question / next action>

## Done
- [x] <resolved item — kept for history>
```

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
