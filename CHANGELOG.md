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

[Unreleased]: https://github.com/caroline-jeffra/claudesidion/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v0.2.0
[0.1.0]: https://github.com/caroline-jeffra/claudesidion/releases/tag/v0.1.0
