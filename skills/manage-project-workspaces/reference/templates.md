# Workspace templates

## Contents
- Index note (`Projects/_index.md`)
- Overview.md
- Progress Log.md
- Decisions.md
- Open Threads.md
- Worked examples

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
created: YYYY-MM-DD
tags: [project]
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
- [[Progress Log]]
- [[Decisions]]
- [[Open Threads]]
```

## Progress Log.md

```markdown
---
created: YYYY-MM-DD
tags: [project, log]
---

# Progress Log — <repo>

<!-- Newest entries at the top. -->
```

Each entry:

```markdown
## YYYY-MM-DD

- **Did:** <what changed>
- **Why:** <reason / context>
- **Next:** <the next step>
- **Links:** [[Decisions#<anchor>]], PR <url>
```

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

**A progress entry:**
```markdown
## 2026-07-10

- **Did:** Added Redis-backed rate limiter to the API gateway.
- **Why:** Bursty clients were exhausting the DB connection pool.
- **Next:** Load-test the 429 path and tune the window.
- **Links:** [[Decisions#2026-07-10 — Use token-bucket over fixed-window]], PR #142
```

**A decision entry:**
```markdown
## 2026-07-10 — Use token-bucket over fixed-window

- **Decision:** Rate limiting uses a token-bucket algorithm.
- **Rationale:** Smooths bursts without the boundary spikes fixed-window allows.
- **Alternatives:** Fixed-window (simpler, but double-rate at window edges); leaky-bucket (rejected — no burst allowance the product wants).
- **From:** [[Progress Log#2026-07-10]]
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
