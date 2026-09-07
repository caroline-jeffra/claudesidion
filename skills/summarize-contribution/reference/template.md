# Contribution summary — structure and section guidance

One file per project at `$OBSIDIAN_VAULT/Contributions/<project>.md`, updated in place for the
project's whole life.

## What each target usage draws from

| Usage | Sections it draws from |
|---|---|
| CV entry | **At a glance**, plus one line per major effort |
| LinkedIn update | **At a glance**, plus one **Story seed** for a post |
| 360 / performance review | **Major efforts** (Judgement calls, Outcome) and **Signals** |
| Blog post ideas | **Story seeds**, backed by the relevant effort's Judgement calls |

Every section earns its place by serving at least one of these. If a section is empty for a project,
keep the heading and name what is missing — the gap tells the next update what to collect.

## Frontmatter

Deliberately light. Enough to query across projects; not a schema to maintain.

```yaml
---
type: contribution-summary
project: <project>          # matches the Projects/<project>/ workspace folder
period: 2026-05 – present   # or a closed range once the project is done
role: <what the user actually did — omit entirely if the evidence does not settle it>
scale: ~275 commits, 60+ tickets   # order of magnitude, omit if not meaningful
efforts: [framework-upgrade, spa-migration, permissions-hardening]
skills: [migration-strategy, authorization-design, ci-cd, data-modelling, code-review]
tickets: [ACME-1614, ACME-1504]
tags: [contribution, summary, <project>]
---
```

`efforts` mirrors the Major efforts subsections. `skills` is the generic capture — record the full
range the evidence supports (technical, operational, and interpersonal), not a role-targeted subset.

## Body

### `# <Project> — Contribution summary`

One or two lines: what this document is, the period it covers, and where the evidence came from.

### `## Context`

What problem space the software exists in, what the commercial or operational stakes are, and where
the genuinely interesting engineering tension sits. **Not a feature list.** Two or three paragraphs.

A reader who has never heard of this project should finish this section able to say why the work was
hard. Sourced from the workspace `Overview.md` and decision notes, not from the code.

Rarely changes on update.

### `## Major efforts`

**Required.** Three to seven `###` subsections, one per coherent body of work. Each in this shape:

```markdown
### <Effort name>
*Owned* | *Contributed to* | *Reviewed and integrated*   ← state which, always

**Problem.** What was wrong or needed, and why it mattered to someone other than the author.

**What I did.** The actual work, concretely. Name the stack where it carries the difficulty.

**Judgement calls.** The decisions that had a defensible alternative, and why this one. The part a
reviewer or interviewer probes, and the part nothing else in the vault records.

**Outcome.** What shipped and what changed. If unfinished or abandoned, say so — an honest partial
outcome is usable; a vague one is not.
```

The ownership marker is not optional. Overstating ownership is the most damaging error this document
can contain, and it is the one a 360 review will catch. SKILL.md Step 3 carries the mapping from
git evidence (Authored / Shipped / Integrated) onto these three markers — use it rather than
picking by feel.

On update: revise a continuing effort's four fields **in place**; do not add a second paragraph
beneath the first.

### `## At a glance`

Two to four bullets, written to be lifted **verbatim** into a CV or LinkedIn entry. Bold the claim,
then substantiate it in the same bullet. Cover the whole project, not the latest period.

Each bullet must survive "so what?" — pair scope with the difficulty that made it non-trivial:

> - **Led the platform's framework modernisation alongside continuous feature delivery** — a
>   three-step major-version upgrade with no feature freeze, sequenced so every step shipped to
>   production independently and nothing needed a big-bang cutover.

Rewrite from scratch on every update. Bullets accumulating one per period is the failure mode.

### `## Detail by theme`

`###` subsections grouping everything delivered — the efforts in finer grain, plus the work that
never belonged to a named effort. Themes emerge from the evidence; typical ones include platform and
tooling, architecture, domain features, data model, testing and CI, defects and incidents, and
documentation or enablement.

Close with a `### Other work` subsection for real work too small to be an effort. Do not pad it, and
do not let it become a commit log — if a bullet would mean nothing to someone outside the project,
cut it.

On update: merge into existing themes; rewrite superseded bullets rather than contradicting them.

### `## Signals`

Evidence for claims that git alone cannot make — the section a 360 review draws on most.

- **Scope and scale** — volume, breadth of surface owned, autonomy.
- **Collaboration** — reviews given and received, cross-team work, pairing, mentoring, decisions
  driven with others.
- **Impact** — what the work enabled, numbers that moved, incidents averted or resolved.
- **Judgement under constraint** — deadline, legacy, incident, or disagreement calls, and how they
  landed. Including ones that went badly: a documented wrong call the user learned from is stronger
  review material than an unbroken record.

Mostly sourced from Step 5 (asking the user and any tracker). If a bullet has no source, cut it —
this is the section where invention is most tempting and most costly.

On update: merge, keeping the strongest evidence per claim rather than every instance.

### `## Story seeds`

Three to six one-liners: things about this project that would make a good blog post, talk, or
LinkedIn post. Each names **the tension or the surprise**, not the topic.

> - Why we kept the legacy column through the enum migration — the additive change that avoided a
>   coordinated cutover, and what it cost to carry.

"We migrated to Vue 3" is a topic, not a seed. The seed is what was counterintuitive about it.

Drop seeds once written up or gone stale; add what the new period surfaced.

### `## Timeline`

**The only append-only section.** One dated line per update — the period covered and what changed
about the user's involvement. Keeps the document's own provenance without cluttering the prose.

```markdown
- **2026-08-27** — Created; covers May–Aug 2026, the period of active development.
- **2026-11-02** — Updated through Oct 2026; SPA migration completed, permissions work handed over.
```

### `## Related notes`

Links into the workspace: `[[Overview]]`, the progress log, decisions, open threads. Keeps the
summary lean — detail stays at its source.
