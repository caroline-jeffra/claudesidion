# Note conventions

## Contents
- Writing style
- Frontmatter fields
- Tag vocabulary
- Wikilinks
- Filenames
- Before / after examples

## Writing style

These rules apply to **every markdown file written into the vault**, by any skill.

**No hard line breaks inside a text block.** Each paragraph and each bullet is a single source line, however long; separate paragraphs with a blank line. Obsidian soft-wraps to the pane width, so hard-wrapped lines (the 80/100-column habit from code) produce ragged, uncomfortable reading there. Never wrap prose to a column width.

**ADHD-friendly writing.** This is about clarity, not brevity — do not compress notes into terse fragments:

- Short, well-formed sentences: one idea per sentence, active voice, concrete words.
- Front-load the point: the first sentence of a note or section says what it's about; explanation follows.
- Make structure visible: headings for topics, bullets for enumerable things, **bold** for the key term a scanning eye should catch. No walls of text — break any paragraph carrying more than one thought.
- Explain, don't allude: spell out the "why" in plain words instead of gesturing at it. A reader with no momentum should be able to pick the note up cold.

## Frontmatter fields

| Field     | Required | Format                        | Notes                                             |
|-----------|----------|-------------------------------|---------------------------------------------------|
| `created` | yes      | `YYYY-MM-DD`                  | Today's date when the note is first written.      |
| `tags`    | yes      | `[a-list, of-tags]`           | Lowercase, hyphenated. Prefer few, reused tags.   |
| `aliases` | no       | `[Alternate Name, Acronym]`   | Only for genuine alternate names the user'd type. |
| `updated` | no       | `YYYY-MM-DD`                  | Add when materially revising an old note.         |

Keep frontmatter minimal. Do not add fields the vault does not already use — extra metadata that
nothing reads is noise.

**Exception — structured project workspaces.** A workspace containing `.vault-config.json` uses a
larger, specified set of fields (`type`, `status`, `topics`, `tickets`, and others) which *are* read:
by the `vault-maintain` hook and by the generated indexes. That contract is defined in
[manage-project-workspaces/reference/structure.md](../../manage-project-workspaces/reference/structure.md).
The rule above still holds everywhere else in the vault, including `Notes/`, `Resources/` and
`Inbox/`, and in flat-layout workspaces.

## Tag vocabulary

- Lowercase, hyphenated, singular where natural: `machine-learning`, `api-design`, `book`.
- Reuse before inventing. List what already exists before adding a tag:
  ```bash
  grep -rhA20 "^tags:" "$OBSIDIAN_VAULT" --include="*.md" \
    | grep -oE "[a-z0-9-]+" | sort | uniq -c | sort -rn
  ```
- 1–4 tags per note is plenty. Tags group notes across folders; they are not a filing cabinet.

## Wikilinks

- Link liberally: `[[Note Title]]`. This is how the vault becomes navigable.
- Link to notes that do not exist yet — a dangling `[[link]]` is a valid "write this later" marker
  and shows up in Obsidian's unresolved-links view.
- Prefer linking over duplicating: reference `[[Rate Limiting Strategies]]` instead of restating it.
- Use display text when the flow needs it: `[[Rate Limiting Strategies|rate limiting]]`.

## Filenames

- `<Title>.md`, Title Case, spaces allowed (Obsidian resolves `[[Title]]` to the file).
- No dates in general-note filenames (dates live in frontmatter). Dated filenames are for logs, which
  are the `manage-project-workspaces` skill's job.

## Before / after examples

**Bad (vague, no structure):**
```markdown
some thoughts on caching. use redis maybe. TTL important.
```

**Good:**
```markdown
---
created: 2026-07-10
tags: [caching, system-design]
---

# Cache Invalidation Approaches

Cache invalidation is the hard part of caching. Three common strategies: **TTL expiry**, **write-through**, and **explicit purge** on mutation. TTL is the simplest, but it serves stale data within the expiry window.

Related: [[Rate Limiting Strategies]], [[Redis]]
```

**Reference note (summarizing an external source):**
```markdown
---
created: 2026-07-10
tags: [book, productivity]
aliases: [GTD]
---

# Getting Things Done

Core idea: capture everything into a trusted system, then process each item into a concrete next action. A weekly review is what keeps the system trustworthy.

Source: David Allen, *Getting Things Done*.

Related: [[Inbox Zero]]
```
