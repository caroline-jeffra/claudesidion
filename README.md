# claudesidion

Claude Code skills that turn an [Obsidian](https://obsidian.md) vault into a durable, cross-project
home for your work — notes, per-repo workspaces, and imported project context.

## Skills

| Skill | What it does |
|-------|--------------|
| **capture-notes** | Saves general knowledge (ideas, facts, references) as well-formed notes with frontmatter, tags, and wikilinks, in the right folder (`Notes/`, `Resources/`, `Inbox/`). |
| **manage-project-workspaces** | Maintains a per-repo workspace (`Projects/<repo>/`) as the source of truth for "what's next" / "where did we leave off", checked before any issue tracker. One note per fact, filed by type into `Log/`, `Decisions/`, `Threads/`, `Tickets/`, `Research/` and `Notes/`, with generated indexes on top. |
| **ingest-project-docs** | Bootstraps a repo's workspace from context that already exists: open issues/milestones/PRs (GitHub `gh` / GitLab `glab`), in-repo docs (README, `docs/`, `CLAUDE.md`, `.claude/`), and scratch files. |
| **summarize-contribution** | Writes or updates a career-facing summary of your contribution to a project, one file per project in `Contributions/`. Evidence comes from git history (identity discovery, authored vs. shipped vs. integrated), the project workspace, and any tracker you have CLI access to. Structured around the project's major efforts, with liftable text for CV, LinkedIn, 360 reviews, and blog topics. Updates integrate into the existing text rather than appending. |
| **condense-vault** | Weekly cleanup: condenses stale content (untouched >3 months) down to bullet points. Outside the project workspaces — in `Archived/`, `Inbox/`, `Resources/` and loose root notes — it also deletes records of finished work. **Project workspaces are condensed but never deleted from**; a workspace note records why work happened, which outlives the work itself. Deletes only when the vault is a git repository, since git history is what makes a deletion recoverable; an unversioned vault gets condensed instead. |
| **migrate-workspace** | Converts one project workspace from the retired flat layout (stacked `Progress Log.md`, `Decisions.md`, `Open Threads.md`) to the structured layout. A one-time transition tool — see "Workspace layouts" below. |

## Prerequisites

- **macOS or Linux.** The hooks are bash scripts; Windows is supported only under WSL, which is untested.
- **`git`** — for vault version control. Optional: without it the sync hooks do nothing and `condense-vault` condenses rather than deletes.
- **`jq`** — used by the hooks to read hook input.
- **`python3`** — required by the `SessionEnd` maintenance hook. Without it that hook exits silently and indexes are simply not refreshed.
- **[Obsidian](https://obsidian.md)** itself is optional. The vault is plain markdown on disk; Obsidian is just the nicest way to read it.

## Setup

### 1. Point at your vault

Skills and hooks resolve the vault path in this order:

1. the `OBSIDIAN_VAULT` environment variable,
2. the config file `~/.claude/obsidian-vault` — one line containing the vault's path.
   Surrounding whitespace is trimmed, and a leading `~/` or `$HOME/` is expanded,
3. the default `~/ObsidianVault`.

**The config file is the recommended way to set it**, because shell-profile exports don't reach
hook shells or non-interactive sessions:

```bash
echo "$HOME/path/to/your/vault" > ~/.claude/obsidian-vault
```

The vault can have any name, anywhere on disk (create it first if you don't have one — an empty
folder Obsidian opens works fine). If none of the three locations yields an existing directory, the
skills ask where your vault is and write the answer to the config file for you; the hooks stay
silent until it's set.

### 2. Install the plugin

**As a plugin marketplace** (recommended):

```
/plugin marketplace add caroline-jeffra/claudesidion
/plugin install claudesidion
```

This is the only path that installs the **hooks** as well as the skills.

**Or clone and symlink the skills** into your user skills directory:

```bash
git clone https://github.com/caroline-jeffra/claudesidion.git ~/code/claudesidion
mkdir -p ~/.claude/skills
for s in ~/code/claudesidion/skills/*/; do
  ln -s "$s" ~/.claude/skills/
done
```

> [!warning]
> **The symlink path installs no hooks.** You get the skills, but not the vault git sync, the
> file-size check, the condense reminder, or the index maintenance — every hook described under
> "Keeping the vault current across a session" is absent. Nothing warns you about this; the skills
> simply work and the vault is never committed or pushed on your behalf. Use the marketplace install
> unless you specifically want skills-only.

### Getting updates

Claude Code does **not** auto-pull marketplace plugins — the marketplace is cached as a git clone and
stays put until you refresh it. After new commits land here, on each machine run:

```
/plugin marketplace update claudesidion
/reload-plugins
```

`/plugin marketplace update` fetches the latest commits (`/plugin update` alone does not `git fetch`
first and will report "already at latest"); `/reload-plugins` applies them to the current session
without a restart.

Updates are **gated on the version number**, not on new commits: the `version` field in
`plugin.json` is what the marketplace compares against, so you receive a change once that field is
bumped and a release is cut, rather than on every push to `main`.

## Versioning

This project follows [semantic versioning](https://semver.org). Releases are tagged `vX.Y.Z` and
described in [CHANGELOG.md](CHANGELOG.md).

The public surface being versioned is **not an API** — it is the layout the plugin writes into your
vault and the behaviour of its hooks. So a **major** bump means one of: the workspace structure or
note format changed in a way existing vaults need migrating for; the set of paths the session-end
hook commits changed; or a skill trigger changed so a phrase that used to invoke it no longer does.
New skills, new hooks and additive frontmatter are **minor**.

While the version is `0.x`, **expect breaking changes to the vault layout** between minor versions.
The structured layout in particular is young, and `migrate-workspace` exists because the first such
change has already happened once.

Each release is tagged `vX.Y.Z` in git, and the `version` field in `plugin.json` is bumped to match.
Since updates are version-gated, a commit that does not bump the version does not reach installed
users — which means the changelog and the tag describe exactly what any given update contains.

If an update still isn't reflected after the above, the marketplace cache can be cleared with
`rm -rf ~/.claude/plugins/cache` followed by reinstalling.

## Usage

Once installed and your vault path is set, the skills activate from natural requests in any repo:

- "make a note …" / "capture this" → **capture-notes**
- "what's next" / "where did we leave off" / "log progress" / "record this decision" → **manage-project-workspaces**
- "ingest this project" / "bootstrap the workspace" → **ingest-project-docs**
- "summarize my contribution" / "write a CV summary for this project" / "what should I put on my CV" → **summarize-contribution**
- "condense the vault" / "run the vault cleanup" → **condense-vault**
- "migrate this workspace" / "convert this project to the new structure" → **migrate-workspace**

The vault links *out* to Jira/GitHub/GitLab; it never pushes changes back to them.

### Writing style

Everything written to the vault follows two rules. First, **no hard line breaks inside a text block** — each paragraph or bullet is one source line, because Obsidian soft-wraps and hard-wrapped prose reads badly there. Second, **ADHD-friendly prose** — clarity, not brevity: short one-idea sentences, the point stated first, visible structure (headings, bullets, bold key terms), and explanations spelled out rather than compressed. The `condense-vault` skill also reformats hard-wrapped files it touches to this style.

### Workspace layouts

Every **new** workspace is created in the **structured** layout: one note per fact, filed by document type into `Log/`, `Decisions/`, `Threads/`, `Tickets/`, `Research/` and `Notes/`, with `type:`/`status:` frontmatter and generated Topic, Tickets, Decisions and Threads indexes. A `.vault-config.json` in the workspace folder is what marks it structured.

The **flat** layout — `Progress Log.md`, `Decisions.md` and `Open Threads.md` each stacking many entries — is the retired original. Existing flat workspaces stay **readable**, so status and "what's next" questions work against one unchanged, but nothing new is created in it and nothing is written to it.

When a write is about to land in a flat workspace, the skill **offers to migrate it first**. Accept and it converts with `migrate-workspace` and then writes; decline and it tells you what it would have logged instead of appending to the stacked files. It never migrates without asking.

The folder skeleton is **fixed** — every structured workspace uses the same folder names and document types, so the skills can rely on them. What varies per project is the vocabulary in `.vault-config.json`: the `topics` map and the index tuning (`min_hits`, `title_weight`, `root_notes`).

### Vault version control

> [!important]
> **This plugin commits and pushes your vault on your behalf.** If your vault is a git repository
> with a remote, work you do in a session is committed and pushed to that remote when the session
> ends, without a further prompt. That is the point of the plugin — but it means anything written
> into an owned folder leaves your machine. Read this section before installing if your vault holds
> anything you would not want pushed, and note the path-allowlist and secret-filename refusals below
> that bound what gets committed.

If your vault is itself a git repository, the plugin syncs it **at the session boundaries, not on
every write**: a `SessionStart` hook pulls it (`git pull --ff-only`) once as the session begins, and a
`SessionEnd` hook commits the session's work as one commit and pushes it. The skills themselves never
touch vault git — they just write files.

**What gets committed, and what does not.** The push hook does *not* `git add -A`. It commits only
paths the plugin's conventions own — `Projects/`, `Resources/`, `Contributions/`, and the root
`Home.md`, `Tasks Archive.md`, `Work Planning.md` — so a stray file elsewhere in the vault is never
published on your behalf. Two further refusals, each reported on stdout rather than done silently:

- **Secret-shaped filenames** (`.env`, `*.pem`, `*.key`, `id_rsa`, `.npmrc`, and similar) are never
  committed, even inside an owned folder. That blocklist cannot be complete, so copy
  [`assets/vault-gitignore`](assets/vault-gitignore) to your vault root as its `.gitignore`.
- **Anything outside those folders** is left uncommitted and named in the hook's output, so you can
  decide what to do with it. `Archived/` is the deliberate exception: it holds retired material the
  plugin does not maintain, so changes there are neither committed nor mentioned.

**When the hook declines entirely.** If the vault has a merge, rebase, cherry-pick or revert in
progress, has unresolved conflicts, or is on a detached HEAD, the hook commits nothing and says why.
Committing in those states would conclude an operation you were in the middle of, or write to a
commit that no branch can reach.

The session commit message is a single short line with no body and no attribution trailer, made on the
current branch (no branching). If the vault is not under version control, both hooks do nothing (they
never run `git init` for you), and a failed pull or push (no remote, offline, auth, conflicts) leaves
the local state and any commit in place rather than erroring.

The one exception is `condense-vault`, which makes its own commit: that run deletes files in bulk, so
it gets a dedicated, recoverable commit rather than being folded into the generic session commit.

### The Tasks Archive

`Tasks Archive.md` at the vault root is a human-friendly, day-by-day summary — **one line per working
day**, newest month first, with a per-month list of the projects touched. It is the quick-reference to
scan before a personal update meeting, months after the fact; the per-repo `Progress Log.md` files
remain the detailed record beneath it.

Rows are **terse by design** — two columns (`Date` and `Tasks`), and one short clause per project
touched that day, three to four words each, at a very high level. A ticket number appears only where
it is the shortest identifier. Links stay out of the table cells: an unescaped wikilink alias pipe
breaks the row into phantom columns, and the links crowd out the few words the cell should carry, so
the per-month `Month's Projects` line carries them instead.

The file is created as part of initial setup on first use against a vault, and appended to at session
close.

### Keeping the vault current across a session

The plugin bundles hooks for the vault's git sync, its start-of-session health checks, and its index
maintenance. No hook writes *progress* — Progress Log entries, decisions and threads are written only
when you ask or say to close out the session (see "When progress gets logged" below). One hook does
write to the vault, though: the `SessionEnd` maintenance hook rewrites derived frontmatter and
regenerates index notes, described below.

- **On session start** (`SessionStart`) — if the vault is versioned, it's pulled (`git pull --ff-only`)
  once as the session begins (and on resume), so the whole session starts from the latest remote
  state. This is the only pull — the skills no longer pull per write.
- **On session start, file-size check** (`SessionStart`) — GitHub warns on files over 50 MB per file
  (and hard-rejects at 100 MB). The hook scans the vault for files within 5% of the warning cap
  (≥ 47.5 MB) and surfaces them so they can be dealt with before a push degrades or fails. The
  remedy is per file and always confirmed with you first: split oversized markdown at a natural
  boundary (per year/month or per topic, updating wikilinks), extract embedded base64 images or
  pasted data dumps into attachment files, or move genuinely binary files to Git LFS.
- **On session start, condense reminder** (`SessionStart`) — the `condense-vault` skill stamps
  `.condense-last-run` in the vault on every run; when that stamp is missing or more than 7 days
  old, this hook reminds Claude to offer the weekly condense run (it only offers — the run never
  starts unprompted).
- **On session end, index maintenance** (`SessionEnd`) — for each workspace that opts in with a
  `.vault-config.json`, this hook fills in derived frontmatter (`project`, `topics`, `tags`) and
  regenerates the Topic, Tickets, Threads and Decisions indexes. It runs *before* the push, so
  regenerated indexes land in the same commit as the notes that changed them. It never deletes or
  moves a file and never edits a note body. Generated indexes carry a `_Generated —` marker and an
  index without that marker is left alone, so a hand-written one is never clobbered; hand-written
  `topics:` are likewise respected. Requires `python3` — without it the hook exits silently.

- **On session end** (`SessionEnd`) — if the vault is versioned and the plugin's own folders have
  pending changes, they're committed as one commit and pushed. This is the counterpart to the
  session-start pull, and it's the only place the vault is pushed; if an earlier push failed, it also
  retries any unpushed commits. It commits a selected path list rather than everything in the vault,
  and refuses outright while a merge or rebase is in progress or HEAD is detached — see
  "Vault version control" above.

### When progress gets logged

`manage-project-workspaces` writes to the vault on exactly two triggers:

- **You ask** — "log progress", "record this decision", "update the vault".
- **You close out the session** — "close out the session", "wrap up", "we're done for the day".

On either trigger it does the whole write in one pass: the Progress Log entry, any Open Threads and
Decisions updates, and the day's row in `Tasks Archive.md`. Nothing is written mid-session while you
work, and no hook nags for it — earlier versions reminded on every `Stop` (i.e. every turn), which
interrupted the coding work it was meant to record. Reading the vault is unrestricted.

Vault reads and writes are also kept out of the transcript: notes are extracted with targeted
`grep`/`sed` rather than read whole, writes are silent, and Claude reports what it wrote in a line
instead of echoing the note — so vault I/O doesn't bury your actual work, even in verbose mode.

All hooks **fail open** — if the vault path is unset, it's not a git repo, or anything goes wrong,
they exit silently and never block or error a turn. They activate automatically once the plugin is
installed via the marketplace; no configuration beyond the vault path is needed.

## Support and bug reports

This is a personal project, maintained in spare time. Issues are read, but there is **no
response-time commitment and no guarantee that any given bug gets fixed**. Bug reports are still
genuinely useful — the plugin was built by one person against one vault, so most of what is wrong
with it is only visible from a vault laid out differently.

- **Found a bug?** [Open an issue](https://github.com/caroline-jeffra/claudesidion/issues/new/choose).
  The template asks for the commit SHA, how you installed it, and any hook output; those three
  usually settle it.
- **Security problem** — data loss, a secret getting committed, anything written outside your vault?
  Report it privately via the **Security** tab, not a public issue. See [SECURITY.md](SECURITY.md).
- **Pull requests** are welcome but may sit for a while. For anything beyond a small fix, open an
  issue first so the design is agreed before you spend the time.

Two things worth knowing before reporting: the marketplace installs from the branch rather than a
tag, so please give the **commit SHA** as well as the version, and the **symlink install path
installs no hooks**, which accounts for a good share of "the hooks never run" reports.
