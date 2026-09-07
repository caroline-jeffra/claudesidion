---
name: capture-notes
description: Creates well-formed notes in the user's Obsidian vault with YAML frontmatter, hyphenated tags, and wikilinks, placed in the right folder. Use when the user says "make a note", "capture this", "save this to my vault/Obsidian", or wants an idea, fact, or reference saved as a durable note (not repo-specific dev work — that is manage-project-workspaces).
---

# Capturing notes

Save general knowledge — ideas, facts, references — as durable notes in the user's Obsidian vault.

**Vault location:** resolve in this order — (1) the `OBSIDIAN_VAULT` environment variable, (2) the config file `~/.claude/obsidian-vault` (one line: the vault's absolute path), (3) the default `~/ObsidianVault`. If none of the three yields an existing directory, ask the user where their vault is and write the answer to `~/.claude/obsidian-vault` so every future session and hook finds it. Use the resolved absolute path (written below as `$OBSIDIAN_VAULT`) for every read/write.

This skill runs from any working directory, so always address the vault by its absolute path.
Repo-specific development work (progress logs, decisions, TODOs for a codebase) belongs to the
`manage-project-workspaces` skill, not here.

## Workflow

1. **Decide the note's title.** A concise noun phrase in Title Case, e.g. `Rate Limiting Strategies`.
   The filename is `<Title>.md` (spaces allowed — Obsidian handles them).
2. **Pick the folder** (see below). Create it under the vault if it does not exist yet.
3. **Check for an existing note** with that title in the chosen folder. If one exists, edit/append
   rather than overwriting — never clobber existing content.
4. **Write the note** using the template below.
5. **Add wikilinks** to related notes you know exist, and mention likely-related titles as
   `[[wikilinks]]` even if the target does not exist yet (a dangling link is a valid to-do).

## Vault writing style

Two rules govern all markdown written to the vault:

- **No hard line breaks inside a text block.** Each paragraph or bullet is one source line, however long; blank lines separate paragraphs. Obsidian soft-wraps to the pane width — never wrap prose to a column width.
- **ADHD-friendly prose** — clarity, not brevity: short one-idea sentences, the point stated first, visible structure (headings, bullets, **bold** key terms), and explanations spelled out rather than compressed.

## Keep vault I/O out of the transcript

Vault notes are long prose, and echoing them into the transcript buries the surrounding work. **Never
dump a note's full contents into the conversation** — not even when Claude is running verbose.

Read with targeted Bash extraction (`grep`, `sed -n`, an `awk` range) rather than pulling whole notes
into context; write with Bash appends/edits and send command output to `/dev/null`. Afterwards, report
what you wrote in one short line rather than quoting or diffing it.

## Vault git sync

**Do not run `git pull`, `git add`, `git commit`, or `git push` on the vault.** The plugin handles
that at the session boundaries: a `SessionStart` hook pulls the vault to latest once, and a
`SessionEnd` hook commits and pushes everything written during the session as a single commit. Just
write the files and move on.

If the vault is not under version control, nothing happens at all (and you should never `git init`
it). The only time to touch vault git yourself is when the user explicitly asks you to.
## Note template

```markdown
---
created: YYYY-MM-DD
tags: [tag-one, tag-two]
---

# <Title>

<The note body. Lead with the core idea in one or two sentences, then detail.>

Related: [[Another Note]], [[Some Concept]]
```

- `created`: today's date as `YYYY-MM-DD`.
- `tags`: lowercase, hyphenated, few. Reuse existing tags before inventing new ones — scan the vault
  first (`grep -rh "^tags:" <VAULT> | sort | uniq`).
- `aliases`: add only when the note has genuine alternate names (see reference).

## Folder placement

Keep the tree shallow. Folders answer "where does it live"; tags and links answer "what is it about".

- **`Notes/`** — atomic, evergreen ideas the user is thinking through (the default for original thought).
- **`Resources/`** — reference material: summaries of articles, docs, external facts to look up later.
- **`Inbox/`** — when the right home is genuinely unclear. Capture now, sort later.

Do not write into `Projects/` — that folder is owned by `manage-project-workspaces`.

## Conventions and worked examples

For the full frontmatter field list, tag-vocabulary guidance, aliases, and before/after examples,
see [reference/conventions.md](reference/conventions.md).
