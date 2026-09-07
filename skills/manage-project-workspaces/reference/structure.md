# Workspace structure contract

The **structured layout** is the only layout new workspaces are created in and the only one written
to. The **flat layout** is retired but still readable, so a skill must detect which one it is dealing
with before it reads — and, on finding a flat one, offer to migrate rather than writing to it.

## Detecting the layout

A workspace uses the **structured layout** if it contains `.vault-config.json`. Otherwise it uses
the **flat layout**.

```bash
if [ -f "$WORKSPACE/.vault-config.json" ]; then
  # structured layout
else
  # flat layout
fi
```

Never guess from the presence of a folder. `Tickets/` exists in both layouts.

---

## Flat layout (retired — read only)

The original layout. **Nothing is written to it and nothing new is created in it**; a write triggers
the migration offer in the main skill. It remains documented here because existing workspaces must
stay readable until they are migrated.

Four files in the workspace root, each stacking many entries:

- `Overview.md` — what the repo is, current focus, trackers.
- `Progress Log.md` — dated `## YYYY-MM-DD` entries, newest first.
- `Decisions.md` — stacked decision sections.
- `Open Threads.md` — `- [ ]` / `- [x]` checkboxes under `## Open` / `## Done`.

Plus `Tickets/` and `Notes/` subfolders.

Read it to answer status and "what's next" questions. **Do not write to it** — not an appended log
entry, not a ticked checkbox, not a decision. Offer the migration instead.

**Do not add `type:`, `topics:`, or `status:` frontmatter to a flat-layout workspace.** Those fields
are only read in the structured layout, and a partially-annotated flat workspace is neither layout.

---

## Structured layout (the default)

One note per fact, filed by document type, with derived metadata in frontmatter.

### Root — readable and referenceable documents only

Nothing else goes in the workspace root.

| Note | What it is | Who writes it |
| --- | --- | --- |
| `Overview.md` | What the repo is, current focus, trackers | you |
| `Progress Log.md` | One line per working day, linking to `Log/<date>.md` | you |
| `Topic Index.md` | Every topic A–Z with the notes under each | **generated — never hand-edit** |
| `Tickets Index.md` | Every ticket and the notes mentioning it | **generated — never hand-edit** |
| `Decisions Index.md` | Decisions and conventions grouped by status | **generated — never hand-edit** |
| `Threads Index.md` | Threads, most open items first | **generated — never hand-edit** |

### Folders — filed by document type

| Folder | `type:` | What belongs there |
| --- | --- | --- |
| `Tickets/` | `ticket` | Work scoped to one tracker ticket; done when it ships |
| `Epics/` | `epic` | A multi-ticket body of work tracked as such |
| `Research/` | `research` | Investigations that outlive the ticket: audits, dossiers, upgrade plans, state captures, playbooks |
| `Notes/` | `note` | Durable cross-ticket knowledge; reusable techniques |
| `Decisions/` | `decision`, `convention` | One note per decision or standing convention |
| `Threads/` | `thread` | One note per thread of unfinished work |
| `Log/` | `log` | One note per working day: `Log/YYYY-MM-DD.md` |

### Naming notes

- **Decisions and threads** — kebab-case, and **write it as a title, not a sentence**: aim for four
  to eight words that name the thing decided. `cypress-runs-only-in-docker` is right;
  `we-decided-that-cypress-should-only-ever-run-inside-docker-because` is not. Some migrated notes
  are long and truncated mid-word — those are machine-generated artifacts, not the convention to
  copy.
- **Tickets** — `<TICKET-ID> <short description>.md`, e.g. `ACME-1701 natural sort ad approvals.md`.
- **Logs** — `YYYY-MM-DD.md`, nothing else.
- **Names must be unique across the whole vault.** `[[wikilinks]]` resolve by name, so a second
  `MISSION.md` or `Index.md` anywhere makes both unreachable.

### When a ticket earns its own note

Not every ticket needs one. A ticket gets a note when there is something to say that outlives a
checkbox — findings, a plan, deferred gaps, review comments. A ticket that is just a unit of work
lives as a `- [ ]` item inside the relevant thread note. Follow what the workspace already does: if
similar tickets are thread items there, keep yours a thread item.

Choosing between the near-synonyms:

- **`ticket` vs `research`** — will this note still be useful after the ticket ships? Yes → `research`.
- **`note` vs `research`** — did it require investigation to produce? Yes → `research`. Is it a
  technique or a fact you will cite later? → `note`.
- **`decision` vs `convention`** — was it decided on a date, in response to something? → `decision`.
  Is it a standing norm with no decision event? → `convention`.

---

## Frontmatter contract

### Fields you write

| Field | Required | Values | Notes |
| --- | --- | --- | --- |
| `type` | yes | one of the `type:` values above | Must match the folder |
| `status` | yes, except `log` | see the status table | |
| `decided` | decisions | `YYYY-MM-DD` | The date the decision was made |
| `date` | logs | `YYYY-MM-DD` | Must equal the filename |
| `tickets` | when relevant | `[ACME-1234, ACME-5678]` | Every ticket the note concerns |
| `superseded_by` | superseded decisions | the superseding note's name | See "Superseding" below |
| `supersedes` | superseding decisions | the superseded note's name | |

### Fields written FOR you

**Do not write these by hand.** The `vault-maintain` SessionEnd hook derives them from content and
rewrites them on every run, so a hand-written value is overwritten.

| Field | Derived from |
| --- | --- |
| `project` | the workspace's `.vault-config.json` |
| `topics` | matching the note's text against the topic vocabulary |
| `tags` | `project` + `type` + one `topic/<name>` per topic |

You may write `topics:` explicitly when the derived guess would be wrong — a hand-written list is
respected and not overwritten. Everything else in that table is regenerated regardless.

### Fields you must NOT write — deprecated counts

Some notes migrated before this contract existed carry cached counts: `open_count`, `done_count`,
`days`, `entries`, `decisions`, `threads_open`, `open_items`, `log_days`.

**Nothing maintains them.** They were correct on the day of the migration and drift from then on —
tick one checkbox and `open_count` is a lie.

- **Never add one to a note.** Count by reading the note.
- **Never update one.** Updating implies it can be trusted, which it cannot.
- Leave existing ones alone; they will be removed. Treat them as noise, never as fact.

If you need a count, derive it at the moment you need it.

### Anything else you find

The tables above are the complete contract. A field outside them is either a deprecated count or a
leftover, and neither is a reason to add more. Do not invent fields, and do not copy an unfamiliar
one forward because a neighbouring note has it.

### Status values

These are the only legal values. A value outside this list lands the note in no index and matches no
query.

| `status` | Use on | Means |
| --- | --- | --- |
| `active` | decision, convention, thread | In force / being worked |
| `superseded` | decision | Replaced — no longer true |
| `open` | thread | Has unfinished items, not currently being worked |
| `done` | thread | Everything finished |
| `shipped` | ticket | Merged and released — the terminal state of a healthy ticket note, which is kept, not deleted |
| `reference` | note, research | Durable material, no lifecycle |
| `paused` | overview, thread | Deliberately stopped |
| `trial` | meta | An experiment being evaluated, not yet adopted |

---

## Superseding a decision

This is the point of the structured layout. When a new decision replaces an old one, **edit the old
note** — do not simply add a newer one, or both will read as current.

On the old note:

```yaml
status: superseded
superseded_by: <name of the new note>
```

and immediately under its heading:

```markdown
> [!warning] Superseded — this no longer holds
> Replaced by [[<new note>]].
>
> <One sentence on what changed and why.>
```

On the new note: `supersedes: <name of the old note>`, and a matching `> [!note]` callout.

Only record a supersession you can evidence. A wrong one is worse than none.

### When the superseded note does not exist

Common, and easy to get wrong. The user says "this replaces our old decision that X", but no note
records X — the old decision was never written down, or lives in a flat-layout workspace, or only
appears in a log entry.

**Do not fabricate a note to supersede, and do not silently drop the claim.** Both lose information.
Instead:

1. Search before concluding it is missing — `Decisions/`, then the logs, then the threads.
2. If it genuinely is not there, write the new decision **without** `supersedes:`, and state the
   replacement in its body: *"This replaces the previous practice that X, which was never recorded
   as a decision note."*
3. Tell the user in one line that you could not find a note for the superseded decision, so the link
   is prose rather than frontmatter.

The frontmatter link is for note-to-note supersession. An unwritten practice has no note, and saying
so plainly is more honest than inventing one.

---

## The two-altitude log

`Progress Log.md` in the root is an **index**: one line per working day, newest first.

```markdown
- **[[2026-08-19]]** — ACME-1656: slim pagination + billing joins landed · ACME-1656
```

The detail lives in `Log/2026-08-19.md`, which holds the full entry — what changed, why, how it was
verified, what is next.

When logging a day that already has a note, **append to that note** rather than creating a second
one, and update the index line only if the day's headline has changed.

---

## What the hook does after you write

The `vault-maintain` SessionEnd hook runs before the vault is committed. It:

1. Fills in `project`, `topics` and `tags` on any note missing them.
2. Regenerates `Topic Index.md` and `Tickets Index.md`.

It never deletes a file, never moves a file, and never edits a note body.

So you can write a note with only `type`, `status` and a body, and the topics and indexes take care
of themselves. What you must get right is `type`, `status`, the folder, and the supersession edits —
the hook cannot infer those.
