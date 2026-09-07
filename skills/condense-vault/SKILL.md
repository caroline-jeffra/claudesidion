---
name: condense-vault
description: Weekly cleanup routine for the user's Obsidian vault — condenses stale content (untouched >3 months) down to bullet points and deletes completed/merged work older than that (especially ticket notes). Use when the user says "condense the vault", "clean up the vault", "run the vault cleanup", or when a SessionStart reminder from this plugin says the weekly condense run is due.
---

# Condensing the vault

Keep the vault lean: old content earns its place only in condensed form, and records of finished
work eventually go away entirely. This is a routine, not a per-note judgement call — run it over the
whole vault in one pass.

**Vault location:** resolve in this order — (1) the `OBSIDIAN_VAULT` environment variable, (2) the config file `~/.claude/obsidian-vault` (one line: the vault's absolute path), (3) the default `~/ObsidianVault`. If none of the three yields an existing directory, ask the user where their vault is and write the answer to `~/.claude/obsidian-vault` so every future session and hook finds it. Use the resolved absolute path (written below as `$OBSIDIAN_VAULT`) for every read/write.

## Step 1 — Find stale content

**Stale = last modified more than 3 months ago.** When the vault is versioned, use the last commit
date per file (`git -C "$OBSIDIAN_VAULT" log -1 --format=%ad --date=short -- "<file>"`); otherwise
use filesystem mtime. A fast way to list candidates in a versioned vault:

```bash
cd "$OBSIDIAN_VAULT" && cutoff=$(date -v-3m +%Y-%m-%d 2>/dev/null || date -d '-3 months' +%Y-%m-%d) \
  && git -c core.quotepath=off ls-files '*.md' | while IFS= read -r f; do
  d=$(git log -1 --format=%ad --date=short -- "$f")
  [ "$(printf '%s\n%s\n' "$d" "$cutoff" | sort | head -n1)" = "$d" ] && [ "$d" != "$cutoff" ] \
    && printf '%s\t%s\n' "$d" "$f"
done
```

Two portability notes baked into that snippet: string `<` comparison inside `[ ]` is bash-only (it breaks under zsh — compare via `sort` instead), and `core.quotepath=off` is required or filenames with non-ASCII characters (em-dashes, arrows) come out quoted and their dates come back empty.

Scan `Notes/`, `Resources/`, `Inbox/`, and `Projects/`. Never touch `.obsidian/`, attachments, or
non-markdown files.

**Never condense or delete anything under `Contributions/`.** Those are living career summaries
maintained by `summarize-contribution` — one per project, updated in place over a project's whole
life. Staleness there is expected and meaningful: a project that ended two years ago has a summary
nobody has touched since, and that is the finished document, not neglect. Condensing one would
destroy the prose it exists to hold.

## Step 2 — Sort each stale file into one of three buckets

1. **Delete** — records of work that is finished: ticket notes whose ticket is done/closed, notes
   about a PR/MR that merged, workspace files for shipped-and-forgotten efforts. Signals: frontmatter
   `status: done|closed|merged|complete|shipped`, a title or body naming a ticket/PR explicitly
   marked merged or complete, every checkbox checked with no forward-looking content. Ticket notes
   are the prime target. When the note names a ticket/PR but its state is not recorded in the note,
   you may check the tracker (`gh`/`glab`/Jira link) read-only; if the state still can't be
   established, condense instead of deleting.

   **This bucket applies to flat vaults only.** In a structured workspace (one containing
   `.vault-config.json`) `shipped` is the *normal terminal status* of a ticket note, not a signal
   that it is disposable — see below.
2. **Condense** — everything else that is stale: reduce verbose prose to terse bullet points.
3. **Leave alone** — stale files that are already terse (roughly: mostly bullets already, or under
   ~15 lines of body), and anything that is a living index (`_index.md`, `MEMORY`-style indexes,
   `Overview.md` files).

If genuinely unsure between delete and condense, condense — the next run can delete it once the
signal is clearer.

### Structured workspaces need extra care

A workspace containing `.vault-config.json` uses the structured layout (see
[manage-project-workspaces/reference/structure.md](../manage-project-workspaces/reference/structure.md)).
In those workspaces:

- **Never delete a note with `type: ticket`, whatever its status.** In the structured layout
  `shipped` is what a ticket note *becomes* when the work lands — it is the terminal state of a
  healthy note, not a marker of one that has outlived its use. The note exists precisely to outlive
  the ticket: it holds why the work was done and what it touched, long after the tracker issue is
  closed and often after the tracker itself is gone. `Tickets Index.md` is regenerated from these
  notes, so deleting them also silently rewrites the index. Condense a stale shipped ticket; never
  remove it.
- **Never delete a note with `type: decision` or `type: convention`**, whatever its status. A
  `status: superseded` decision is not finished work — it is the record of what was true before, and
  the thing that stops a stale claim being read as current. Condense it if it is stale; never remove
  it.
- **Never delete or condense a generated index** — `Topic Index.md`, `Tickets Index.md`,
  `Decisions Index.md`, `Threads Index.md`, or the root `Progress Log.md`. They are
  rebuilt from the notes and carry no original content. Condensing one just gets overwritten;
  deleting one loses nothing but produces confusing churn.
- **Never delete `.vault-config.json`.** Removing it silently reverts the workspace to the flat
  layout in every skill's eyes.
- `Log/<date>.md` notes are ordinary content: condense old ones, but deleting a day's log deletes
  the only record of that day.

`status: reference` means "durable material, no lifecycle" — it is never a delete signal.

## Step 3 — Condense

Rewrite the note body as bullet points, keeping:

- the YAML frontmatter (update nothing in it except adding `condensed: YYYY-MM-DD`),
- the title heading,
- every `[[wikilink]]` and external URL that carries information (fold them into the bullets),
- the facts — names, numbers, decisions, conclusions.

Drop: narrative prose, restated context, hedging, worked examples, anything recoverable from a
linked source. A good condensed note is the bullet list you'd want when the topic resurfaces in a
year. Target well under half the original length; a long note may become five bullets.

**Project workspaces** (`Projects/<repo>/`) get entry-level treatment instead of whole-file:
- `Progress Log.md` — collapse each stale dated entry to one or two bullets; merge runs of stale
  entries about the same effort into a single summary entry spanning the date range. Entries about
  merged/completed work older than 3 months are removed entirely.
- `Decisions.md` — keep every decision, but condense stale rationale to a line each.
- `Open Threads.md` — remove checked items older than 3 months; keep every open item.

Rewrites also apply the vault writing style: **no hard line breaks inside a text block** (each bullet or paragraph is one source line — Obsidian soft-wraps, so unwrap any hard-wrapped prose you touch), and **ADHD-friendly prose** — clarity, not brevity: short one-idea sentences, the point stated first, visible structure. Condensed bullets should still be full, readable sentences, not telegraphic fragments.

## Step 4 — Delete

**Deletion requires a recycle bin. Check for one before deleting anything.**

The safety of this whole routine rests on one claim: a wrongly deleted note is recoverable from
the vault's git history. That claim is only true when the vault is a git repository with the
deletions committed. It is **false** for a vault that is not versioned, and this skill explicitly
supports those (Step 1 falls back to file mtimes for exactly that case).

So, before deleting:

```bash
git -C "$OBSIDIAN_VAULT" rev-parse --is-inside-work-tree >/dev/null 2>&1 && echo versioned || echo unversioned
```

- **Versioned** → proceed. Deletions go in as a dedicated commit (Step 5), so `git revert` or
  `git checkout <sha>^ -- <path>` brings any note back.
- **Unversioned** → **do not delete anything.** Condense the bucket-1 files instead — down to a
  single line each if they are truly finished — and tell the user plainly: *"this vault is not
  under version control, so I condensed rather than deleted; deleting would be unrecoverable."*
  Offer `git init` as the fix. A cloud-synced vault (Drive, iCloud, Dropbox) does **not** count:
  per-file revision history is not the same as a commit you can revert, and it will not restore a
  file the sync has already propagated as deleted.

Also require a **clean working tree** before a versioned run. If the vault has uncommitted changes,
commit or stash them first — otherwise the "recoverable deletion commit" arrives mixed with the
user's unrelated in-progress edits, and recovering one deleted note means untangling it from work
that has nothing to do with this run.

Then delete the bucket-1 files outright with `git rm`. After deleting, grep the vault for
`[[wikilinks]]` to the deleted notes and remove or unlink those references so no dangling links
remain (a mention in a condensed summary line is fine as plain text).

## Step 5 — Stamp, commit, report

1. Write the run date (`YYYY-MM-DD`) to `$OBSIDIAN_VAULT/.condense-last-run` (plain text, one line).
   The plugin's SessionStart reminder reads this to know when the next weekly run is due.
2. If versioned, commit and push everything as one commit. This is the one skill that commits its
   own work: the run deletes files in bulk, and a dedicated commit keeps that recoverable instead
   of folding it into the generic session commit the `SessionEnd` hook makes.

```bash
git -C "$OBSIDIAN_VAULT" add -A \
  && git -C "$OBSIDIAN_VAULT" commit -m "condense vault: <N> condensed, <M> deleted" \
  && git -C "$OBSIDIAN_VAULT" push
```

   The message is a **single line with no body and no attribution** — no `Co-Authored-By`, no
   `Generated with` trailer. Pass exactly one `-m` flag and never a heredoc. Commit on the current
   branch; do **not** create branches. If `push` fails (no remote, offline, auth), leave the commit
   in place and tell the user; do not retry in a loop.

3. Report to the user: files deleted (with one-line reasons), files condensed (with rough size
   before → after), and anything skipped as unclear.
