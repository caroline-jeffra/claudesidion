---
name: migrate-workspace
description: Converts one project workspace in the user's Obsidian vault from the flat layout (stacked Progress Log.md, Decisions.md, Open Threads.md) to the structured layout (one note per fact, filed by document type, with generated topic and ticket indexes). Use when the user says "migrate this workspace", "convert this project to the new structure", "restructure the vault for this repo", or when a flat workspace has grown too large to navigate.
---

# Migrating a workspace to the structured layout

Converts one workspace from the flat layout to the structured one. Migrate **one project at a time**,
and only when the flat layout has actually become the problem.

**Vault location:** resolve in this order — (1) the `OBSIDIAN_VAULT` environment variable, (2) the config file `~/.claude/obsidian-vault` (one line: the vault's absolute path), (3) the default `~/ObsidianVault`. If none of the three yields an existing directory, ask the user where their vault is and write the answer to `~/.claude/obsidian-vault`. Use the resolved absolute path (written below as `$OBSIDIAN_VAULT`) for every read/write.

Read [manage-project-workspaces/reference/structure.md](../manage-project-workspaces/reference/structure.md)
before starting. It defines the target layout, and this skill's whole job is to produce it.

## When NOT to migrate

Say so and stop if any of these hold. The flat layout is the right default and most workspaces should
stay on it.

- The stacked files are small — under a few hundred lines total. Splitting three short files into
  forty notes makes things harder to find, not easier.
- The workspace is a handful of notes. There is nothing to index.
- The user wants "the whole vault migrated". Migrate one project, let them live with it, and let them
  ask for the next.

The signals that migration **is** warranted: `Decisions.md` stacking dozens of entries, a
`Progress Log.md` in the high hundreds of lines, decisions that supersede each other, or the user
saying they cannot find things.

As a rough gauge, add up `Decisions.md` + `Open Threads.md` + `Progress Log.md`:

- **under ~300 lines** — stay flat.
- **~300–600 lines** — borderline; migrate only if there is another signal, such as supersession.
- **over ~600 lines** — migrate.

### The user can overrule this

The threshold is advice, not a gate. If the user has heard the recommendation and still wants the
migration — or says the workspace is about to grow fast, which the line count cannot see — **do it**.

State the size finding in one line, say the workspace would normally stay flat, then proceed. Do not
refuse twice, and do not make them argue for it.

A workspace that is small *today* but about to be worked heavily is a legitimate reason to migrate
early: it is far cheaper to convert 200 lines than 2,000, and every note written afterwards lands in
the right shape.

## Step 0 — Safety

**The source workspace is never modified.** Build the new structure alongside it and leave the
original in place until the user confirms the result. They delete the original; you do not.

1. Confirm the vault is a git repo and note whether it is clean:
   `git -C "$OBSIDIAN_VAULT" status --porcelain`. If it is dirty, say so — a dirty tree makes it
   harder to see what the migration changed.
2. Choose the destination name with the user. A migrated `portal.example.com` became `Portal`.
3. Never `rm -rf` anything. Never move the original.

## Step 1 — Survey before converting

Do not start splitting until you know what is there. Report these to the user:

```bash
W="$OBSIDIAN_VAULT/Projects/<name>"
wc -l "$W"/*.md                                    # how big are the stacked files
grep -cE '^## ' "$W/Decisions.md"                  # how many decisions
grep -cE '^## 20' "$W/Progress Log.md"             # how many dated entries
grep -c '^- \[ \]' "$W/Open Threads.md"            # unfinished items
grep -c '^- \[x\]' "$W/Open Threads.md"            # finished items
find "$W" -name '*.md' | wc -l                     # total notes
```

Then look for **supersession**, which is the thing this layout exists to fix:

```bash
grep -rniE 'supersede|reverses|no longer|overrides|instead of the|changed from' "$W" --include='*.md'
```

Every hit is a candidate pair. You will need them in Step 4.

## Step 2 — Build the topic vocabulary

Topics are project-specific. A vocabulary copied from another project is worthless.

1. Extract candidate terms from the workspace's own content — recurring subsystem names, ticket
   prefixes, product areas, technologies.
2. Propose 12–20 topics to the user, each with a short gloss, and get them confirmed. Fewer than ~10
   is too coarse to be useful; more than ~25 and each topic holds too little.
3. Every topic needs **specific** match patterns. A pattern that matches a common English word tags
   half the vault and makes the index useless.
4. **Verify before committing to them**: score every note and check the distribution. A topic landing
   on more than about a third of notes is too broad; one landing on a single note should be folded
   into a neighbour or dropped. Aim for a mean of 2–4 topics per note.

Write the result to `<destination>/.vault-config.json`:

```json
{
  "project": "<short-slug>",
  "folders": {
    "ticket": "Tickets", "epic": "Epics", "research": "Research", "note": "Notes",
    "decision": "Decisions", "convention": "Decisions", "thread": "Threads", "log": "Log"
  },
  "generated_types": ["index", "log-index"],
  "index_types": ["index", "log-index", "overview", "meta", "glossary", "summary"],
  "min_hits": 3,
  "title_weight": 4,
  "topics": {
    "<slug>": {
      "name": "<Display Name>",
      "gloss": "<one line: what this topic covers>",
      "patterns": ["<regex>", "<regex>"]
    }
  }
}
```

This file is what marks the workspace as structured. Nothing else does.

## Step 3 — Split the stacked files

Write a script for this rather than doing it by hand — it is mechanical, and a script can be checked
and re-run. Keep it in `<destination>/.migration/` so the conversion is reproducible.

- **`Decisions.md`** → one note per `## ` section in `Decisions/`. Filename is the decision title in
  kebab-case. Extract the date from the heading into `decided:`. A heading that names a standing norm
  rather than a dated choice becomes `type: convention`.
- **`Open Threads.md`** → one note per `## ` section in `Threads/`, checkboxes preserved inside.
  `status: open` when it has unfinished items, `done` when it does not.
- **`Progress Log.md`** → one note per date in `Log/YYYY-MM-DD.md`, with **all** of that day's
  entries inside it. Then rebuild the root `Progress Log.md` as a one-line-per-day index. On a day
  with several entries, prefer a session-close or summary entry for the headline.
- **`Tickets/` and `Notes/`** → refile by document type. An audit, dossier, upgrade plan, state
  capture or playbook is `research` even when named for a ticket; a deferred-gaps or bug note stays
  `ticket`. Assets (CSVs, images) follow the note that owns them.
- **Preserve prose exactly.** Reformatting bodies during a structural migration makes it impossible
  to tell a conversion bug from an edit.

## Step 4 — Record supersession

Work through the candidate pairs from Step 1. For each pair the source text **explicitly** supports:

- On the superseded note: `status: superseded`, `superseded_by: <new note name>`, and a
  `> [!warning] Superseded — this no longer holds` callout under the heading quoting the evidence.
- On the superseding note: `supersedes: <old note name>` and a matching `> [!note]` callout.

**Only encode supersession the source states.** A wrong supersession marks a live decision dead,
which is worse than leaving both undifferentiated. If the text merely hints, leave it and tell the
user which pairs you skipped so they can confirm them.

## Step 5 — Verify, and show the evidence

A migration that loses content silently is worse than none. Check all of these and report the
numbers:

- **No prose lost.** Compare the word multiset of each source file against its split output. Only
  structural tokens — heading dates, rewritten link targets — should differ. Report any prose loss
  explicitly rather than rounding it away.
- **No new broken links.** Collect every `[[wikilink]]` in the output and resolve it. Compare against
  the links already broken in the source, and report only the ones the migration caused.
- **File parity.** Every ticket note, working note and asset present before is present after.
- **Frontmatter coverage.** Every note has frontmatter, a legal `type`, and a legal `status`.
- **Ambiguous names.** Note names must be unique — `[[wikilinks]]` are name-based and a duplicate
  stem resolves unpredictably.

Run the maintenance hook once to fill in derived metadata and build the indexes:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/hooks/vault_maintain.py" "$OBSIDIAN_VAULT"
```

## Step 6 — Register and report

1. Add or update the workspace's row in `$OBSIDIAN_VAULT/Projects/_index.md` so the other skills find
   it. **A migrated workspace that is not in `_index.md` is invisible** — every session will keep
   using the old directory.
2. Tell the user: what was created (counts per folder), what the verification found, which
   supersession pairs you encoded and which you skipped, and that the original is untouched and
   theirs to delete.
3. Leave the original in place. Do not offer to delete it in the same pass.

## Vault writing style

Two rules govern all markdown written to the vault:

- **No hard line breaks inside a text block.** Each paragraph or bullet is one source line, however long; blank lines separate paragraphs. Obsidian soft-wraps to the pane width — never wrap prose to a column width.
- **ADHD-friendly prose** — clarity, not brevity: short one-idea sentences, the point stated first, visible structure (headings, bullets, **bold** key terms), and explanations spelled out rather than compressed.

## Keep vault I/O out of the transcript

A migration touches every note in a workspace. **Never dump note contents into the conversation** —
report counts and differences, not text. Verification output should be numbers and names, not bodies.

## Vault git sync

**Do not run `git pull`, `git add`, `git commit`, or `git push` on the vault.** The plugin handles
that at the session boundaries. Just write the files and move on.

A migration is a large change, so it is worth telling the user it will land in the session-end commit
and that they may want to review it in Obsidian first.
