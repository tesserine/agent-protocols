---
name: verify
description: >-
  Gate completion claims with fresh verification evidence and a
  documentation-impact review. Fires after implementation, before the work
  is packaged for review. No claim of complete, fixed, or passing without
  running the verification and reading the output — evidence before
  assertions, always.
metadata:
  origin: >-
    Adapted from tesserine/groundwork protocols/verify (v2.0.0, 2026-06-11)
    and workflow-contracts/verify.toml, re-expressed in the Agent Protocols
    canonical model. The repair loop, present in the prose but absent from
    the TOML graph, is modeled here explicitly.
protocol:
  spec: "1"
  intent: Gate completion claims with fresh evidence and an honest record of coverage and documentation impact.
  contract:
    precondition:
      - behavior-contract
      - test-evidence
      - work-unit
      - { ref: implementation-plan, optional: true }
    postcondition:
      - completion-evidence
  invariants:
    - id: evidence-before-claims
      rule: No completion claim without fresh verification evidence; confidence is not evidence, and a previous run is not evidence.
    - id: honest-evidence
      rule: Evidence records what is, not what is hoped; gaps and failures are recorded as gaps and failures.
  corruption_modes:
    - id: performative-verification
      signal: Running the command without reading the output; if the output did not change your understanding, you did not verify.
    - id: partial-verification
      signal: One test file standing in for the suite, or the linter standing in for the build; partial evidence supports only partial claims.
    - id: stale-evidence
      signal: Citing output from before the last code change.
    - id: claim-first
      signal: Deciding the work is done, then selecting evidence to confirm it; evidence determines the claim, never the reverse.
    - id: drift-tolerance
      signal: Documentation known stale but recorded as accurate, or deferred without a tracking work-unit.
  steps:
    - id: identify-the-gate
      title: Identify the gate
      intent: Name what proves completion — the full verification command and the criterion coverage that must hold.
      applies: [orient, contract]
      x-mechanics: [read-artifact]
      needs:
        - behavior-contract
        - work-unit
        - { ref: implementation-plan, optional: true }
      yields: [verification-gate]
    - id: run-fresh
      title: Run fresh
      intent: Execute the full command and read the entire output — exit code, failure count, all of it.
      applies: [contract]
      x-mechanics: [run-test]
      needs:
        - verification-gate
        - ref: increment-fix
          feedback: true
          when: A repaired increment makes all earlier output stale; the gate re-runs fresh.
      yields: [verification-output]
    - id: assess-coverage
      title: Assess coverage
      intent: Join criteria, scenarios, and results, and determine honestly what the evidence shows.
      applies: [contract]
      x-mechanics: [read-artifact]
      needs:
        - verification-output
        - test-evidence
        - behavior-contract
        - work-unit
      outcomes:
        group: gate-result
        one_of:
          - id: assessed
            when: The evidence is assessable; coverage is recorded honestly — covered, partial, or uncovered alike.
            yields: [coverage-assessment]
          - id: defect-found
            when: Verification surfaced a failure to repair in this increment; root cause before any fix.
            yields: [failure-finding]
    - id: repair-increment
      title: Repair the increment
      intent: Root-cause the failure, fix this increment with cycle discipline, and send the gate back around.
      applies: [debug]
      needs:
        - failure-finding
      yields: [increment-fix]
    - id: review-documentation-impact
      title: Review documentation impact
      intent: Map the change to the documents that claim to describe it, and record the impact.
      applies: [orient]
      x-mechanics: [inspect-worktree]
      needs:
        - coverage-assessment
      yields: [documentation-impact]
    - id: deliver-completion-evidence
      title: Deliver completion-evidence
      intent: Record criterion coverage and documentation impact as the completion-evidence artifact.
      needs:
        - coverage-assessment
        - documentation-impact
      yields: [completion-evidence]
---

# Verify

Evidence before claims, always.

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

This protocol owns the aggregate gate — the moment before "done." Per-test
cycle evidence (each test watched failing, then passing) belongs to
`implement`. Completion here means: the contract's scenarios pass, the
work-unit's criteria are covered, and the documentation still tells the
truth.

## Step: identify-the-gate

From the behavior contract and the work-unit's acceptance criteria, name
what proves completion: the full verification command (test suite, build,
linter as applicable) and the criterion-coverage that must hold.

## Step: run-fresh

Execute the full command. Read the entire output; check the exit code; count
the failures. Output from any earlier run is stale the moment code changed.

## Step: assess-coverage

Join criteria × scenarios × results: for every acceptance criterion, which
scenarios cover it and do their tests pass? Record honestly whatever the
evidence shows — covered, partial, or uncovered. An honest gap is not a
detour into repair: it ships in the evidence, where review will see it.

## Step: repair-increment

If verification surfaces a failure, stop and invoke `debug` — root cause
before fixes. A fix to this work-unit's own increment applies `implement`'s
cycle discipline (failing test first, minimal change); then the gate re-runs
fresh from `run-fresh`, because the fix made every earlier output stale.

## Step: review-documentation-impact

Map the change to the documents that claim to describe it; classify each as
accurate, drifted, missing, or obsolete; update what the change touched in
the same change; file follow-up work-units for anything deeper.

## Step: deliver-completion-evidence

Record the criterion coverage (per criterion: status, covering scenarios,
failures) and the documentation impact (updated, verified accurate,
follow-ups filed) as the `completion-evidence` artifact, delivered through
the executing runtime's recording surface.

## Invariant: evidence-before-claims

If the verification command was not run fresh, in this protocol, the claim
has no basis. Confidence is not evidence; a previous run is not evidence; a
partial check supports only a partial claim.

## Invariant: honest-evidence

The evidence is honest, not aspirational: gaps and failures are recorded as
gaps and failures. Review consumes this evidence and blocks on it — an
uncovered criterion shipped to review is a blocking finding, not a secret.

## Cross-References

- `implement` (protocol): owns per-cycle evidence; this protocol owns the
  aggregate gate.
- `contract` (skill): coverage is reported behavior-first — scenarios and
  criteria, not just command exit codes.
- `debug` (skill): fires on any failure surfaced here, before any fix.
- `submit` (protocol): consumes this evidence — work is packaged for review
  only after the gate has run.
- `orient` (skill): carries the always-on documentation-writing discipline
  that this protocol's review step audits.
- Recognition signals, claim-by-claim requirements, and the rationalization
  table live in groundwork's `protocols/verify/references/gate-patterns.md`;
  the documentation-review method in
  `protocols/verify/references/documentation-review.md`.
