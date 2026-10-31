# ADR-006 - gitleaks as the pre-commit secret scanner

- Status: Accepted (2026-10-30)

## Context

SEC-35 requires a secret scanner in pre-commit that blocks commits with secrets, and SEC-22 requires reviewing the
tool first. The repository will be public on GitHub (phase 7), where a leaked key stays in the history.

Review (2026-10-30, from the repository): gitleaks, MIT license, about 30 500 stars, with an official pre-commit
hook (`id: gitleaks`). Its README says the project is feature complete and will receive only security patches, while
its maintainer moves to a new project.

## Decision

Use the official gitleaks pre-commit hook, pinned to an exact `rev` (SEC-40). The exact version is recorded in spec
000 when it is installed, and spec 000 checks that the hook runs on the development computer.

## Rejected alternatives

- **No local scanner, only GitHub secret scanning:** GitHub detects the secret after the push, when it is already
  public; the local hook stops it before the commit.
- **A newer tool from the same maintainer:** less proven; it can replace gitleaks in a future ADR if gitleaks stops
  receiving security patches.

## Consequences

- Every commit is scanned before it exists.
- gitleaks being in maintenance mode is acceptable for a stable job; it is reviewed again in phase 7.

## Affected governing rules

`security-rules.md` SEC-21, SEC-22, SEC-35, SEC-40.
