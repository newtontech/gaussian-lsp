# PR Review Workflow

Use this workflow for every open pull request before deciding whether to merge,
modify, or hold it.

## Review Lanes

Run three independent Codex subagents in parallel:

- Agent A, correctness and regression risk: inspect the PR diff, changed
  behavior, edge cases, and compatibility with existing callers.
- Agent B, tests and coverage: inspect whether tests fail before the fix,
  whether the changed paths are covered, and whether CI exercises every touched
  runtime.
- Agent C, security and maintainability: inspect input handling, dependency
  changes, security scans, config drift, and long-term maintenance risks.

The coordinating agent must wait for all three reports, then make one combined
decision. If the reports disagree, default to `modify`.

## Decision Rules

- `P1`: a correctness, security, data-loss, or CI issue that can break users or
  block a safe merge.
- `P2`: a missing-test, maintainability, dependency, or documentation issue that
  creates meaningful review or release risk.
- `merge`: CI is green, the branch is mergeable, there are no P1 or P2 findings,
  changed behavior is covered by tests, and no external approval is missing.
- `modify`: the PR has fixable defects, missing tests, CI coverage gaps,
  documentation drift, or inconsistent local reproduction steps.
- `hold`: CI fails, the PR has conflicts, intent is unclear, security risk is
  unresolved, or product judgment is required.

Pushing, merging, publishing, or changing third-party resources requires
explicit user approval.

## Record Template

```text
PR:
Title:
Base/head:
CI:
Mergeability:

Agent A recommendation:
Agent B recommendation:
Agent C recommendation:

Coordinator decision:
Reason:
Required follow-up:
```

## Baseline Records

Keep point-in-time PR status in the PR description, review comments, or a dated
maintenance note. This workflow should stay limited to reusable review rules so
it does not go stale after a PR is merged, rebased, or closed.
