# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**What a breaking change means here.** This plugin's public surface is not an API — it is the
**layout it writes into your vault** and the **behaviour of the hooks**. A major version bump means
one of: a change to the workspace folder structure or note format that existing vaults would need
migrating for; a change to which paths the session-end hook commits; or a skill trigger changing so
that a phrase that used to invoke it no longer does. New skills, new hooks and additive frontmatter
are minor.

## [Unreleased]

## [1.1.0] — 2026-09-10

### Fixed

- **Vault commits stranded by a cancelled session-end push now reach the remote.** `vault-push.sh` commits locally and then pushes over the network, and Claude Code cancels in-flight hooks during session teardown — reliably enough that the push half was being cut in the gap after the commit half succeeded. The result was the one failure this plugin exists to prevent: commits that exist only on this machine, with no error shown, while the user believes their notes are backed up. `vault-pull.sh` (SessionStart, where there is no teardown pressure) now flushes any commits ahead of the upstream before it pulls, so whatever the last exit stranded goes out at the next launch. A flush that fails is reported as `remain local-only` rather than passing silently.

### Added

- **`tests/test-vault-pull.sh`** — the SessionStart hook had no suite at all. Covers the fail-open preconditions and the flush: stranded commits are pushed and counted, a clean vault claims nothing, a local-only vault with no upstream stays quiet, and an unreachable remote reports the commits as still local rather than as flushed.

## [1.0.1] — 2026-09-07

### Fixed

- **The weekly condense reminder no longer prompts when nothing is stale.** It fired on the 7-day
  stamp alone, so a vault younger than the 3-month staleness threshold was nudged every week into a
  run that could only find nothing. The routine nudge now also confirms at least one file is old
  enough to condense. The "never been recorded" message is deliberately *not* gated — that is how
  someone first learns the routine exists.
- **`stat` platform detection.** The reminder picked BSD vs GNU `stat` with `bsd || gnu`, which does
  not work: GNU `stat` reads the BSD `%Sm` as a *filename*, writes to stderr, and still **exits 0**,
  so the fallback never ran and the check silently found nothing on Linux. It now probes `stat` once
  and tests the output rather than the exit code. Unlike the `date -v`/`date -d` pair, this failure
  mode succeeds wrongly instead of failing cleanly.


## [1.0.0] — 2026-09-07

The flat workspace layout is gone. That transition is what 1.0 was defined as, and it is complete.

### Removed

- **The flat workspace layout.** Workspaces created before 1.0 — stacked `Progress Log.md`,
  `Decisions.md` and `Open Threads.md` — are no longer created, read or written. A workspace is
  now identified solely by its `.vault-config.json`.
- **The `migrate-workspace` skill.** It existed to serve a one-time transition, and that transition
  is done. The plugin now ships five skills.

### Changed

- **A pre-1.0 workspace is reported, not guessed at.** On finding a folder with no
  `.vault-config.json`, the skills say plainly that it is unsupported and tell you to pin to
  `v0.4.x`, run `migrate-workspace`, and upgrade again. They will not read it, will not convert it,
  and will never scaffold a second workspace alongside it.
- **Wikilink conventions are now written down.** A uniquely-named note is linked bare
  (`[[a-decision-note]]`), which survives a workspace being renamed. The six per-workspace
  structural files — `Overview`, `Progress Log`, and the four generated indexes — exist once per
  workspace by design, so links to them carry the workspace prefix (`[[Takeoffs/Overview]]`)
  whenever they cross a workspace boundary. A bare link resolved against the whole vault binds to
  whichever workspace matches first and *resolves cleanly*, so it reads as healthy while pointing
  at another project's notes.

### Upgrading from 0.x

If every workspace already has a `.vault-config.json`, nothing to do. Otherwise migrate first, on
`v0.4.x`, then upgrade — 1.0 cannot convert for you.


## [0.4.0] — 2026-09-07

### Changed

- **Repo paths in `Projects/_index.md` are now machine-relative.** A row records the repo's path
  relative to that machine's code root, so one row is correct on every machine the vault syncs to.
  The root resolves as `CODE_ROOT`, then `~/.claude/code-root`, then the default `~/code` — the same
  three-tier shape as the vault path, for the same reason. A row starting with `/` is still matched
  literally, so a repo outside the root keeps working.
- **The basename fallback no longer rewrites a row whose recorded path exists on this machine.**
  Previously any path miss rewrote the row, so a repo checked out on two machines had its row
  overwritten by whichever machine ran last — producing a vault diff every session. Rewriting is now
  reserved for a repo that genuinely moved.
- **A total lookup miss no longer scaffolds.** If no row resolves and the index is non-empty, the
  code root is wrong or unset rather than the repo being new. The skill reports which root it
  resolved and stops, instead of creating a second workspace for a repo that already has one.


## [0.3.0] — 2026-09-07

### Changed

- **New workspaces are scaffolded structured.** The flat layout is retired: it is still *read*, so
  status and "what's next" questions work against an existing flat workspace unchanged, but nothing
  new is created in it and nothing is written to it.
- **A write to a flat workspace offers to migrate first.** Accept and it converts with
  `migrate-workspace` then writes; decline and it reports what it would have logged rather than
  appending to the stacked files. It never migrates without asking.
- **The folder skeleton is fixed by the contract**, not configured per workspace. New
  `.vault-config.json` files omit the `folders` key; the maintenance hook now carries the skeleton as
  a built-in default. An explicit `folders` map still overrides it, so workspaces written before this
  keep working. What stays per-project is the vocabulary: `topics`, `min_hits`, `title_weight`,
  `root_notes`.
- Templates, worked examples and the structure contract now show the structured shapes. The flat
  templates are retained and marked retired, for reading existing workspaces.

This is a step toward `1.0`, which lands when the transition is complete and the flat layout is gone.


## [0.2.0] — 2026-09-07

### Changed

- **`condense-vault`'s delete bucket is now scoped by location, not by vault layout.** It applies
  outside project workspaces — `Archived/`, `Inbox/`, `Resources/` and loose root notes. Anything
  under `Projects/<repo>/` is condensed but never deleted: a workspace note records *why* work
  happened and what it touched, which outlives the work itself.

  Previously the bucket was scoped "flat vaults only", which made it dead code in a structured
  workspace and would have made it unreachable entirely once the flat layout is retired. Ticket
  notes are no longer described as the prime delete target — in a workspace they are never deleted
  at all.


## [0.1.0] — 2026-09-07

First tagged release. The plugin has been in single-user daily use for some months; this is the
point at which it became defensible to hand to someone else.

### Added

- Six skills: `capture-notes`, `manage-project-workspaces`, `ingest-project-docs`,
  `summarize-contribution`, `condense-vault`, and `migrate-workspace`.
- Five hooks: session-start vault pull, file-size check, and condense reminder; session-end index
  maintenance and commit/push.
- Structured workspace layout — one note per fact, filed by document type, with generated Topic,
  Tickets, Threads and Decisions indexes. `migrate-workspace` converts a flat workspace to it.
- A regression suite of 122 tests across four suites, run on macOS and Linux in CI, with
  `shellcheck` and `bash -n` gating.
- MIT licence, security policy with private vulnerability reporting, and issue templates.

### Fixed

Everything below was found by four adversarial reviews on 2026-09-03 and fixed before this release.
They are listed because they describe what the plugin used to do to a vault.

- **Data loss and destructive behaviour.** The session-end hook no longer commits while a merge,
  rebase, cherry-pick or revert is in progress, or on a detached HEAD. `git add -A` was replaced
  with an allowlist of plugin-owned paths plus a blocklist of secret-shaped filenames, so a stray
  file elsewhere in the vault is never published on your behalf. Commit and push failures are now
  reported rather than exiting silently, and a failed commit unwinds the index instead of leaving
  the tree staged.
- **Frontmatter round-trip guard, symlink containment, and generated-marker checks** in the index
  maintenance hook, so it cannot write outside the vault or clobber a hand-written index.
- **Bulk deletion in `condense-vault` is gated on the vault being under version control**, since
  git history is what makes a deletion recoverable. An unversioned vault is condensed, never
  deleted from. Cloud-sync revision history is explicitly not accepted as a substitute.
- **Filename handling in the size check** — `-print0` and control-character stripping.
- **Workspace discovery** is no longer pinned to a fixed directory depth, and skips dot-directories.
- **A moved repository** is recognised by basename rather than getting a second workspace.
- **Two test fixtures depended on the developer's global git config** — the bare-remote default
  branch and `--no-identity` — so two guarantees were not actually being tested. Found by running
  the suite on Linux for the first time.

### Security

- Privacy scrub: the working tree and full git history were rewritten to remove an employer domain,
  internal hostnames, real ticket keys, and an internal system name. The repository was then rebuilt
  from a single commit so no pre-scrub object remains reachable.

[Unreleased]: https://github.com/caroline-jeffra/claudesidion/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v1.0.1
[1.0.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v1.0.0
[0.4.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v0.4.0
[0.3.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v0.3.0
[0.2.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v0.2.0
[0.1.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v0.1.0
