# Security policy

## Reporting a vulnerability

Report privately through GitHub: go to the repository's **Security** tab and choose
**Report a vulnerability**. That opens a private advisory only you and the maintainer can see.

**Please do not open a public issue for a security problem.** This plugin runs `git` operations over
a personal knowledge base, so a vulnerability here can mean someone's private notes being committed
or pushed somewhere they did not intend. A public report discloses the problem before there is a fix.

There is no response-time commitment — this is a spare-time project — but security reports are read
first and taken seriously.

## What is in scope

The plugin's job is to write to your vault and, if it is a git repository, to commit and push it.
That makes anything which causes it to write, commit, or push something it should not the primary
concern:

- **Data loss or destruction** — a vault file deleted, truncated, or overwritten in a way that
  git history cannot recover.
- **Unintended publication** — the session-end hook committing or pushing a path outside the folders
  the plugin owns, or a secret-shaped file (`.env`, `*.pem`, `*.key`, and similar) getting past the
  blocklist in `hooks/vault-push.sh`.
- **Path escape** — a workspace path, symlink, or crafted filename causing a read or write outside
  the configured vault directory.
- **Command injection** — a filename, note body, or config value that reaches a shell or `git`
  invocation as code.
- **Committing while the repository is mid-operation** — concluding a merge, rebase, or cherry-pick
  on the user's behalf, or committing onto a detached HEAD.

## What is out of scope

- **The plugin pushing your vault to your own remote.** This is the documented purpose, not a
  vulnerability. See "Vault version control" in the README for what it commits and the refusals that
  bound it.
- **Anything requiring an attacker to already have write access to your vault or your machine.**
- **Vulnerabilities in Claude Code, git, jq, or python3 themselves** — report those upstream.
- **A skill producing poor or wrong prose.** That is a bug; open a normal issue.

## Supported versions

Only the latest release is supported, and there are no backports — a fix lands on `main` and in the
next tag. If you are on an older version or a pinned commit, the first step for any report is to
update and confirm the problem still occurs.

## Handling your report

A report may need details about how your vault is laid out. Please redact note contents, file names,
and paths that are private to you — a structural description is almost always enough, and the
maintainer does not need to see your notes to diagnose a path or git bug.
