---
name: ingest-project-docs
description: Ingests an existing project's documentation and tracker context into the user's Obsidian vault workspace — open issues and milestones, open PRs/MRs, in-repo docs (README, docs/, CLAUDE.md, .claude/), and temp/scratch files — summarizing each and linking back to the source. Use when starting to track a repo in the vault, or when the user says "ingest this project", "pull in the docs/issues", "bootstrap the workspace", or "import existing context".
---

# Ingesting project docs

Bootstrap a repo's Obsidian workspace from context that already exists — issues, milestones, PRs/MRs,
in-repo docs, and stray working files — so the vault starts as a real source of truth instead of empty.

**Vault location:** resolve in this order — (1) the `OBSIDIAN_VAULT` environment variable, (2) the config file `~/.claude/obsidian-vault` (one line: the vault's absolute path), (3) the default `~/ObsidianVault`. If none of the three yields an existing directory, ask the user where their vault is and write the answer to `~/.claude/obsidian-vault` so every future session and hook finds it. Use the resolved absolute path (written below as `$OBSIDIAN_VAULT`) for every read/write.

This skill **feeds** the `manage-project-workspaces` structure; it does not invent a new layout.
Read that skill's conventions if unsure where something lands.

## Principles

- **Summarize + link back.** Condense each source into a few lines and link to the original
  (issue/PR URL, or repo-relative file path). The vault stays lean; detail stays at the source.
- **Never clobber.** Read existing workspace files first; append or merge. Ingestion runs may repeat —
  do not duplicate entries already present (match on issue number / file path / title).
- **Report gaps, don't guess.** If a source is unavailable (e.g. a tracker call fails auth), note it
  in the run summary rather than silently skipping it.

## Workflow

Copy this checklist and track progress:

```
Ingest progress:
- [ ] Step 1: Locate/scaffold the workspace
- [ ] Step 2: Detect the forge (GitHub vs GitLab)
- [ ] Step 3: Pull tracker context (issues, milestones, PRs/MRs)
- [ ] Step 4: Gather in-repo docs and temp files
- [ ] Step 5: Map into the workspace
- [ ] Step 6: Report the run
```

**Step 1 — Locate/scaffold the workspace.**
Use `manage-project-workspaces`: find the repo in
`$OBSIDIAN_VAULT/Projects/_index.md`, or scaffold `Projects/<repo>/` and add a row.

**Step 2 — Detect the forge.**
Inspect `git remote -v`. A `github.com` remote → use `gh`. A `gitlab.com` or self-hosted GitLab
remote → use `glab`. If both, ingest from both. Assume the relevant CLI is authenticated; if a call
returns `401`/auth error, record it in the run report and continue with other sources.
Exact commands: see [reference/sources.md](reference/sources.md).

**Step 3 — Pull tracker context.**
Open issues, open milestones, and open PRs/MRs. Keep title, number, URL, labels, and a one-line gist.

**Step 4 — Gather in-repo docs and temp files.**
- Docs: `README*`, `docs/`, `CLAUDE.md`, `.claude/` (agents/skills/commands), any `ARCHITECTURE`/`ADR` files.
- Temp/scratch: untracked or gitignored working files, `TODO.md`, `NOTES.md`, scratchpads
  (`git status --porcelain --ignored` finds them). These are often the richest undocumented context.

**Step 5 — Map into the workspace** (append/merge, never overwrite).

Ingestion always writes, so it always targets a structured workspace — which a newly scaffolded one
is. If the workspace exists but has no `.vault-config.json`, it predates 1.0 and is unsupported:
say so, and write nothing.

See
[manage-project-workspaces/reference/structure.md](../manage-project-workspaces/reference/structure.md)
for the full contract.
- **Overview.md** — seed "What this is" from the README's intro; set trackers (issue/PR URLs); fold in `docs/`/`CLAUDE.md` highlights as short bullets with links.
- **Threads** — one note per thread of work in `Threads/` (`type: thread`, `status: open`), its open
  issues as `- [ ]` items inside. Group related issues into one thread rather than making a note per
  issue.
- **The day's log** — write `Log/YYYY-MM-DD.md` with the ingestion summary, then add its one-line
  entry to the root `Progress Log.md`.
- **Decisions** — one note per decision in `Decisions/` (`type: decision`, `status: active`,
  `decided:`), not a stacked `Decisions.md`.
- Write only `type`, `status` and the dates. The `vault-maintain` hook derives `project`, `topics`
  and `tags`, and regenerates the indexes.

Full mapping table and templates: [reference/sources.md](reference/sources.md).

**Step 6 — Report the run.**
Tell the user what was ingested, per source, with counts (e.g. "12 open issues, 3 milestones, 2 open
PRs, README + 4 docs, 1 TODO.md"), and list any source that failed (auth, missing, empty).

## Vault writing style

Two rules govern all markdown written to the vault:

- **No hard line breaks inside a text block.** Each paragraph or bullet is one source line, however long; blank lines separate paragraphs. Obsidian soft-wraps to the pane width — never wrap prose to a column width.
- **ADHD-friendly prose** — clarity, not brevity: short one-idea sentences, the point stated first, visible structure (headings, bullets, **bold** key terms), and explanations spelled out rather than compressed.

## Vault git sync

**Do not run `git pull`, `git add`, `git commit`, or `git push` on the vault.** The plugin handles
that at the session boundaries: a `SessionStart` hook pulls the vault to latest once, and a
`SessionEnd` hook commits and pushes everything written during the session as a single commit. Just
write the files and move on.

If the vault is not under version control, nothing happens at all (and you should never `git init`
it). The only time to touch vault git yourself is when the user explicitly asks you to.
## Conventions

Dates `YYYY-MM-DD`; tags lowercase-hyphenated; link with `[[wikilinks]]` inside the vault and normal
markdown links out to issues/PRs. The vault links *out* to trackers — it does not push back to them.
