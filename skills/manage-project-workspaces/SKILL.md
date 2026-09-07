---
name: manage-project-workspaces
description: Maintains a per-repository workspace in the user's Obsidian vault as the source of truth for ongoing development work — overview, dated progress log, decisions/ADRs, and open threads. Use when the user asks what to work on next or where a body of work stands — "what's the next task", "what should I work on", "where did we leave off", "what were we doing on this" — as well as "log progress", "record what we did", "record this decision", "track open threads". Consult this vault before an issue tracker (Jira/GitHub/GitLab) for next-work questions. Not for "what's the status" in the git sense — uncommitted changes, branch state and diffs come from git, not from here.
---

# Managing project workspaces

Keep a durable, per-repo workspace in the user's Obsidian vault so ongoing development work has one
findable home — simpler than scattering context across ticket trackers, issues, and code comments.

**Vault location:** resolve in this order — (1) the `OBSIDIAN_VAULT` environment variable, (2) the config file `~/.claude/obsidian-vault` (one line: the vault's path — whitespace is trimmed and a leading `~/` or `$HOME/` is expanded), (3) the default `~/ObsidianVault`. If none of the three yields an existing directory, ask the user where their vault is and write the answer to `~/.claude/obsidian-vault` so every future session and hook finds it. Use the resolved absolute path (written below as `$OBSIDIAN_VAULT`) for every read/write.

You typically run this skill while the user's working directory is *a different repo*. Always address
the vault by its absolute path; derive the current repo from the working directory, not the vault.

## Step 0 — Ensure the vault-level files exist (once per vault)

Two files live at the **vault root**, not inside any workspace:

- `$OBSIDIAN_VAULT/Projects/_index.md` — the repo → workspace map (see Step 1).
- `$OBSIDIAN_VAULT/Tasks Archive.md` — the human-friendly day-by-day summary (see
  "Maintaining the Tasks Archive" below). Create it from the template in
  [reference/templates.md](reference/templates.md).

**Ask before the first write to a vault that already has content in it.** A question like
"what should I work on" is a request to *read*; it is not consent to create folders in a
directory the user may have been curating for years, and `Projects/` is a common enough name
that theirs may already mean something else.

Decide with one check — does the vault contain notes this plugin did not put there?

```bash
# Any markdown outside the paths this plugin owns?
find "$OBSIDIAN_VAULT" -name '*.md' -not -path '*/.git/*' \
  -not -path "$OBSIDIAN_VAULT/Projects/*" \
  -not -path "$OBSIDIAN_VAULT/Resources/*" \
  -not -path "$OBSIDIAN_VAULT/Contributions/*" \
  -not -path "$OBSIDIAN_VAULT/Archived/*" | head -5
```

- **Empty vault, or nothing but this plugin's own folders** → create the two files without asking.
  There is nothing to disturb, and prompting on an empty vault is noise.
- **Existing notes, or a `Projects/` folder this plugin did not create** → stop and ask once,
  naming exactly what you would create and where:

  > This vault has notes in it already. To track work per repo I'd create
  > `Projects/_index.md` and `Tasks Archive.md` at the vault root. Create them?

  If they decline, answer their question from what you can read and do not write anything. Do not
  re-ask in the same session.

The same applies in Step 2: scaffolding a **workspace** into an existing `Projects/` folder is a
first write to space the user may already be using. Name the folder you are about to create and
confirm, unless this plugin created `Projects/` itself.

Once either file exists, this step is done and never asks again.

## Step 1 — Locate the workspace

The vault holds an index that maps each repo to its workspace folder, by a path **relative to this machine's code root**:
`$OBSIDIAN_VAULT/Projects/_index.md`

**`_index.md` is the only way to choose a workspace.** Never pick one by browsing `Projects/` or by
grepping for a term — a trial or archived copy can look more relevant than the live workspace,
because it is the one that has been reorganised. Read the index first, every time.

1. Determine the current repo's absolute path: `git rev-parse --show-toplevel` (fall back to the cwd
   if not a git repo). Call its basename `<repo>`.

   **Resolve the code root**, which is what index rows are relative to: the `CODE_ROOT` environment
   variable, then `~/.claude/code-root` (one line, whitespace trimmed, leading `~/` or `$HOME/`
   expanded), then the default `~/code`.

2. Read `_index.md` and match. Rows hold paths **relative to the code root**; a row starting with
   `/` is absolute and matched literally. See "Paths are machine-relative" in
   [reference/templates.md](reference/templates.md).
   - **Path match** → use the workspace it names.
   - **No path match** → fall back to **basename**. On a single match, check whether that row's
     recorded path exists on this machine. If it does **not**, the repo moved: confirm and update
     the row. If it **does**, you are simply on a different machine — use the workspace and
     **change nothing**. Rewriting there is what makes rows ping-pong between machines.
   - **Several basename matches** → ask which. Do not guess.
   - **No match at all, and the index has rows** → **stop.** Every relative row missing at once
     means the code root is wrong or unset, not that this is a new repo. Say which root you
     resolved and where it came from, and do not scaffold — a second workspace for an existing repo
     is the split-brain this index exists to prevent.
   - **No match, and the index is empty** → genuinely new. Scaffold (Step 2) and add a row.
   - **`_index.md` missing** → create it with the header from
     [reference/templates.md](reference/templates.md), then scaffold — subject to the Step 0
     consent gate if this is the first write to a vault that already has content.

3. **Check for a trial workspace.** `_index.md` may carry a `## Trial workspaces` section listing a
   second, not-yet-adopted workspace for the same repo. If the repo you matched appears there:
   - The **main table's row is authoritative**. Write there, not to the trial.
   - Say so in one line — "note that `<trial>` also exists as a trial copy; writing to the live
     workspace" — so the user can redirect you if they meant the trial.
   - **Never write to both.** Two workspaces receiving the same entry is exactly the split-brain the
     trial section exists to prevent.

   Write to a trial workspace only when the user names it explicitly.

## Step 1b — Detect the layout (do this before any write)

```bash
if [ -f "$WORKSPACE/.vault-config.json" ]; then echo structured; else echo flat; fi
```

- **Structured** — one note per fact, filed by document type, with `type:`/`status:` frontmatter and
  generated indexes. **This is the only layout that is written to**, and the only one new workspaces
  are created in.
- **Flat** — the retired original: `Progress Log.md`, `Decisions.md`, `Open Threads.md` each stack
  many entries. Still **readable**, so status and "what's next" questions work against one. A write
  to a flat workspace triggers the migration offer in "Flat workspaces" under Step 2 — never an
  append to the stacked files.

The full contract — folders, frontmatter fields, legal `status` values, how to supersede a decision —
is in [reference/structure.md](reference/structure.md). **Read it before writing.**

Reading differs between layouts and is marked **(flat)** or **(structured)** below. Writing does not:
there is one write path, and it targets a structured workspace.

## Step 2 — Scaffold a workspace (first use for a repo only)

**New workspaces are always structured.** The flat layout is retired: it is still *read* (see
"Flat workspaces" below), but nothing new is created in it and nothing is written to it.

To scaffold:

1. Create `$OBSIDIAN_VAULT/Projects/<repo>/` and, inside it, the folders from
   [reference/structure.md](reference/structure.md): `Tickets/`, `Epics/`, `Research/`, `Notes/`,
   `Decisions/`, `Threads/`, `Log/`. **Create each on first use, never empty** — an empty folder is
   noise in the sidebar and tells the reader nothing.
2. Create `Overview.md` from the template in [reference/templates.md](reference/templates.md) — what
   the repo is, current focus, the absolute repo path, links to external trackers.
3. Create `Progress Log.md` as a **one-line-per-day index**, not a stack of entries. The detail lives
   in `Log/<date>.md`.
4. Write `.vault-config.json` — this file is what marks the workspace structured; nothing else does.
   A new workspace has no content to derive topics from, so start with `"topics": {}` and add them as
   subjects emerge. The indexes work from day one; the Topic Index is simply empty until there are
   topics.

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

The folder skeleton is **fixed by the contract**, not configured here — every workspace uses the same
folder names and the same document types, and skills may rely on that. What stays per-project is the
**vocabulary**: `topics`, `min_hits`, `title_weight`, and optionally `root_notes`.

5. Add the row to `_index.md`. Record the repo's path **relative to the code root** (just `<repo>` for a repo sitting directly in it); use an absolute path only for a repo outside the root.

**Growing the topic vocabulary.** Add a topic once three or four notes would carry it — earlier and
it is noise, later and the index has a gap. Each topic needs specific patterns; one matching a common
English word tags half the workspace and makes the index useless. After editing `.vault-config.json`,
the next session-end hook run re-derives topics across every note.

### Flat workspaces

The flat layout (stacked `Progress Log.md`, `Decisions.md`, `Open Threads.md`) is retired. Existing
ones are still **readable** — status and "what's next" questions work against them unchanged — but
they are never created and never written to.

**When a write is about to land in a flat workspace, offer to migrate it first:**

> This workspace still uses the old flat layout. Migrate it to the structured layout now? It is a
> one-time conversion and I will log the progress afterwards either way.

- **Yes** → run `migrate-workspace`, then write into the migrated workspace as normal.
- **No** → do not write. Say what you would have logged, in the transcript, so nothing is lost, and
  offer again next time. Do not append to the flat files.

Never migrate without asking. The conversion rewrites a user's notes, and the plugin does not do
that unprompted — the same rule that governs `condense-vault`'s deletions and first-run scaffolding.

## Step 3 — Read before you write

Before acting on a task or answering "what's the status", read the workspace's current state. This is
the context that would otherwise be lost.

- **(flat)** — `Overview.md`, `Open Threads.md`, and the most recent entries of `Progress Log.md`.
- **(structured)** — `Overview.md`, `Threads Index.md` (which names the open threads and their
  counts), and the newest lines of `Progress Log.md`, following the top one or two dates into
  `Log/<date>.md` for the detail.

## Answering "what's next" / status questions

First, check the question is the one this skill answers. "What's the status of this repo" usually
means **git** — branch, uncommitted changes, whether it is pushed. Answer that from git and stop.
This skill is for *where the work stands*: what to pick up next, what was decided, what is
unfinished. If it is ambiguous, the cheapest resolution is to answer the git question and offer the
other: "on `main`, clean, 2 commits ahead — want the work-in-progress picture from the vault too?"

For a genuine next-work question the vault is the source of truth — check it **before** any issue
tracker (`glab`/`gh`) or planning doc:

1. Locate the workspace (Step 1). If the repo has **no** workspace yet, say so and offer to bootstrap
   it with `ingest-project-docs` — do not silently fall back to the tracker.
2. Read the queued work, then `Overview.md` "current focus", then the latest log entry (its
   **Next:** line is usually the direct answer).
   - **(flat)** — `Open Threads.md`, then the top `## YYYY-MM-DD` section of `Progress Log.md`.
   - **(structured)** — `Threads Index.md` and the threads it flags for pick-up, then the newest
     `Log/<date>.md`. `Topic Index.md` answers "what do we have on X" directly.
3. Answer from that. Prioritize: the current-focus area first, then open threads, then a stated **Next**.
4. Only consult the tracker as a *supplement* — to enrich an item or if the vault is genuinely silent —
   and mention that you're going beyond the vault when you do.

**Check the workspace is current before trusting it over a tracker.** That preference is earned by a
workspace someone has been keeping up; it is wrong for one that is empty or months behind, where
deferring to it means answering from stale information and calling it the source of truth. Compare
the newest `Progress Log.md` date against the repo's last commit date:

- **Workspace within a few days of the last commit** → proceed as above; it is current.
- **Workspace materially behind the repo** (say a week or more of commits it does not mention) →
  say so in one line, answer from the vault *and* the recent commits together, and offer to log the
  gap: "the workspace was last updated 2026-08-12 and there are 23 commits since — here's what it
  has, plus what the commits show; want me to bring it up to date?"
- **Workspace exists but is effectively empty** (a scaffold with no logged work) → say so and answer
  from git and the tracker, rather than reporting that there is nothing to do.

## Step 4 — Write back (on trigger only)

This step runs only when one of the triggers in "When to log progress" below fires — an explicit
request, or the user closing out the session. It is not something to do as work happens.

Golden rule: **never overwrite existing content.** Read the file, then append or edit in place.
Create a file (with its header) only if it is absent.

### Flat workspace? Offer to migrate, then write

Writes never land in a flat workspace. Offer the migration described in "Flat workspaces" above; on
a yes, migrate and then write as below. On a no, report what you would have logged in the transcript
and write nothing.

### Write one note per fact

Read [reference/structure.md](reference/structure.md) first. In short:

- **The day's log** — write or append to `Log/YYYY-MM-DD.md` (`type: log`, `date:` matching the
  filename). Then add or update that day's one-line entry in the root `Progress Log.md`, newest
  first. Never append a dated entry to the root `Progress Log.md` itself — it is an index.
- **A decision** — a **new note** in `Decisions/`, named for the decision in kebab-case, with
  `type: decision`, `status: active`, `decided: YYYY-MM-DD`, and `tickets:`. Never append to a
  `Decisions.md` — in this layout that file does not exist and must not be created.
- **Superseding a decision** — when the new decision replaces an old one, **edit the old note**: set
  `status: superseded`, add `superseded_by:`, and put a `> [!warning]` callout under its heading.
  Add the matching `supersedes:` and `> [!note]` callout on the new one. Skipping this is the single
  failure this layout exists to prevent — both notes then read as current.
- **A thread** — one note per thread in `Threads/`, `type: thread`. Tick `- [x]` inside it as items
  finish; set `status: done` when nothing is left.
- **Overview** — update "current focus" as in the flat layout.
- **Never create** `Decisions.md`, `Open Threads.md`, or a dated section inside the root
  `Progress Log.md`. Those are flat-layout files; creating them here produces two contradictory
  sources of truth in one workspace.

**Do not hand-write `project:`, `topics:` or `tags:`.** The `vault-maintain` SessionEnd hook derives
them and rewrites them anyway. Write `type`, `status`, the dates and the body; the hook fills in the
rest and regenerates `Topic Index.md` and `Tickets Index.md` before the vault is committed. Write
`topics:` explicitly only when you know the derived guess would be wrong — a hand-written list is
respected.

**Never hand-edit `Topic Index.md` or `Tickets Index.md`.** They are generated; edits are lost.

Cross-link between notes and to general `[[notes]]` (from the `capture-notes` skill) so the
workspace stays navigable in Obsidian's graph.

## When the vault contradicts these instructions

The vault is older than this skill and does not always match it. When they disagree, **say so in one
line and keep going** — do not silently pick one, and do not stop and interrogate the user over
something small.

- **Two workspaces claim the same repo** → write to the one in `_index.md`'s main table; mention the
  trial exists. (Step 1.)
- **The superseded decision has no note** → record the replacement in prose, not frontmatter, and say
  you did. (See [reference/structure.md](reference/structure.md).)
- **An existing file breaks the format this skill documents** → follow the documented format for what
  you add. Do not reformat what is already there; a logging pass is not a cleanup pass.
- **A note carries frontmatter this contract does not list** → leave it, do not copy it forward.
- **The workspace is `status: paused` but the user is doing work in it** → log the work and ask
  whether to un-pause. Do not change project status on your own initiative.

Stop and ask only when writing would **destroy or contradict** something — never merely because the
vault is untidy.

## Maintaining the Tasks Archive

`$OBSIDIAN_VAULT/Tasks Archive.md` is the quick-reference the user scans before a personal update
meeting: **one line per working day**, condensed enough to take in at a glance months later. It is
the thin layer above the per-repo `Progress Log.md` files, never a replacement for them.

**Append today's row when the session is closed out**, alongside the Progress Log entry — on the
same triggers as everything else in "When to log progress" below, never mid-session.

### Structure

Newest year first (`# 2026`), and within it newest month first (`## Aug 2026`). Each month has a
projects header above its table, then the table itself:

```markdown
## Aug 2026

### Month's Projects
[[portal.example.com/Overview|portal.example.com]], [[home-budgeter/Overview|home-budgeter]]

| Date | Tasks |
| ---- | ----- |
| 5    | ...   |
```

- **Exactly two columns** — `Date` and `Tasks`, nothing more. Never widen the table.
- **Date column** — the bare day number, nothing else. Days with no work get no row.
- **Month's Projects** — every project touched that month, most-active first. These are the only
  links that should point at a project `Overview`.
- **New month** → add a new `## <Mon YYYY>` section above the previous one, with its own projects
  header and table. Add the projects header entry the first time a project appears that month.

### Writing a row

Rows are **terse by design** — the archive is scanned, not read. One short clause per project touched
that day, **three to four words each**, comma-separated, at a very high level. The detail belongs in
that project's `Progress Log`; do not restage it here.

- Name the project when the clause needs the context (`home-budgeter Phase 0 landed`), and carry a
  ticket number only where it *is* the shortest identifier (`ACME-1763 Laravel 13 planned`).
- Bold a genuine milestone — a release, an epic completing (`**ACME-1504 ready for review**`).
- Several projects in one day → one clause each, project named first so they stay separable.

**No links inside table cells.** A wikilink's alias pipe breaks the table row into phantom columns
unless escaped as `\|`, and the links crowd out the few words the cell is meant to carry. Project
links belong in the `Month's Projects` line above the table, which is the one place they go.

Write it as a cell that renders in one line, e.g.:

```markdown
| 19 | ACME-1656 billing joins landed, home-budgeter deployed |
| 12 | **ACME-1763 done — Laravel 10→13 climb complete** |
```

### Which day a session books under

Book work under the date it **started**. A session that runs past midnight still belongs to the day
it began, so it appends to that day's row rather than opening a new one. If a row for the day already
exists, extend it — never add a second row for the same date.

## When to log progress

Progress logging is **not** continuous. Do not append Progress Log entries, Decisions, Open Threads
updates, or Tasks Archive rows mid-session as work happens — that noise interrupts the actual coding
work. Write to the vault only on one of these two triggers:

- **The user explicitly asks** — "log progress", "record what we did", "record this decision",
  "update the vault", "note this down".
- **The user says to close out the session** — "close out the session", "wrap up", "we're done for
  the day", "end of session", or an equivalent.

When one of those fires, do the whole write in one pass: append the Progress Log entry, update Open
Threads and Decisions as needed, and append the day's row to [[Tasks Archive]] (see "Maintaining the
Tasks Archive" above).

Reading the vault is unrestricted — read it freely whenever you need context (Step 3, and the
"what's next" flow). The restriction is on *writes*.

Keep each write incremental — the golden rule above ("never overwrite; append or edit in place")
governs *how*.

## Keep vault I/O out of the transcript

Vault notes are long prose. Echoing their full text into the transcript buries the actual coding work
the user is trying to follow, so **never dump a vault file's contents into the conversation** — not
even when the user has Claude running verbose.

- **Reading** — prefer targeted Bash extraction over reading whole files: `grep`, `sed -n '1,40p'`,
  or an `awk` range that pulls just the section you need (the latest `## YYYY-MM-DD` entry, the
  unchecked `- [ ]` lines, the "current focus" paragraph). Read a whole file only when you genuinely
  need all of it.
- **Writing** — append and edit with Bash (`cat >> … <<'EOF'`, `sed -i''`, a small `python3` script)
  and send any command output to `/dev/null`. A successful write needs no output at all.
- **Reporting** — after writing, say what you did in one short line ("logged today's progress and the
  archive row"), not by quoting or re-printing what was written. Never print a diff of the note.
- **Verification** — if you must confirm a write landed, check cheaply (`tail -n 3`, a `grep -c`), not
  by re-reading the file into context.

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

- Dates: `YYYY-MM-DD`. Tags (if used in frontmatter): lowercase, hyphenated.
- The vault links *out* to Jira/GitHub/GitLab; it does not push changes back to them.

## Templates and worked examples

Index-note format, the four file templates, and worked progress/decision entries are in
[reference/templates.md](reference/templates.md).
