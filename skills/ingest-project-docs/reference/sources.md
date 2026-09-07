# Ingestion sources & mapping

## Contents
- GitHub commands (gh)
- GitLab commands (glab)
- In-repo docs & temp files
- Source → workspace mapping
- Ingestion Progress Log entry template

All CLI commands run from the repo's working directory. Assume the relevant CLI is authenticated for
that repo; on a `401`/auth error, record it in the run report and continue with other sources.

## GitHub commands (gh)

```bash
# Open issues (title, number, url, labels, one-line body)
gh issue list --state open --limit 200 \
  --json number,title,url,labels,milestone,body

# Open milestones
gh api "repos/{owner}/{repo}/milestones?state=open" \
  --jq '.[] | {title, description, due_on, html_url}'

# Open PRs
gh pr list --state open --limit 200 \
  --json number,title,url,labels,isDraft,body
```

Keep only title, number, url, labels, milestone, and a one-line gist derived from `body`. Do not copy
full bodies into the vault.

## GitLab commands (glab)

```bash
# Open issues
glab issue list --output json --per-page 200

# Open issues under a milestone
glab issue list --milestone "<name>" --output json --per-page 200

# Open merge requests
glab mr list --output json --per-page 200

# Milestones (no first-class list subcommand — use the API)
glab api "projects/:id/milestones?state=active"
```

`:id` resolves to the current project. Same rule: summarize, link via each item's `web_url`.

## In-repo docs & temp files

```bash
# Tracked docs
ls README* 2>/dev/null; find docs -maxdepth 2 -name '*.md' 2>/dev/null
ls CLAUDE.md 2>/dev/null; find .claude -maxdepth 2 -type f 2>/dev/null
find . -maxdepth 2 -iregex '.*\(architecture\|adr\).*\.md' 2>/dev/null

# Temp / scratch / untracked / ignored working files
git status --porcelain --ignored | grep -E '^(\?\?|!!)'
ls TODO.md NOTES.md SCRATCH* 2>/dev/null
```

Read each doc; summarize its purpose in 1–3 bullets. For temp files, extract actionable TODOs and any
"why" context — these are often the richest undocumented source. Link docs by repo-relative path.

## Source → workspace mapping

Append/merge into the `manage-project-workspaces` files; never overwrite. Dedupe on the key shown.

| Source                     | Lands in        | Form                                                       | Dedupe key      |
|----------------------------|-----------------|-----------------------------------------------------------|-----------------|
| README intro               | Overview.md     | "What this is" bullets                                    | —               |
| Issue/PR tracker URLs      | Overview.md     | Trackers section                                          | url             |
| docs/, CLAUDE.md, .claude/ | Overview.md     | Short bullet each, linked by repo path                    | file path       |
| Open issues                | Open Threads.md | `- [ ] #<n> <title> — <gist> ([link](url))`               | issue number    |
| TODOs in temp files        | Open Threads.md | `- [ ] <action> (from <file>)`                            | action text     |
| Open PRs/MRs               | Open Threads.md | `- [ ] PR/MR !<n> <title> ([link](url))`                  | pr/mr number    |
| Milestones                 | Overview.md     | "Milestones" bullets: title, due date, link              | milestone title |
| Decisions in docs/ADRs     | Decisions.md    | one ADR entry each (decision / rationale / link)         | decision title  |
| The ingestion run itself   | Progress Log.md | one dated entry (template below)                          | date + "Ingest" |

## Ingestion Progress Log entry template

```markdown
## YYYY-MM-DD — Ingested existing project context

- **Did:** Bootstrapped workspace from existing sources.
- **Imported:** <N> open issues, <N> milestones, <N> open PRs/MRs, README + <N> docs, <N> temp files.
- **Skipped/failed:** <source + reason, or "none">.
- **Next:** Review Open Threads and set current focus in [[Overview]].
```
