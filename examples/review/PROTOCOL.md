---
name: review
description: >-
  Review a submitted change proposal against the behavior contract and
  evidence, and produce exactly one disposition outcome. Routes approval
  through `change-approved` and blocking findings through
  `change-needs-revision`.
metadata:
  origin: >-
    Adapted from tesserine/groundwork protocols/review (v2.0.0, 2026-06-11)
    and workflow-contracts/review.toml, re-expressed in the Agent Protocols
    canonical model.
protocol:
  spec: "1"
  intent: Judge a submitted change independently and record exactly one typed disposition.
  contract:
    precondition:
      - change-proposal
      - behavior-contract
      - { ref: work-unit, optional: true }
      - { ref: implementation-plan, optional: true }
      - { ref: completion-evidence, optional: true }
    postcondition:
      - { group: review-disposition, one_of: [change-approved, change-needs-revision] }
  invariants:
    - id: independence-of-the-gate
      rule: The change is judged by a context that did not produce it; the author's momentum never approves itself.
  corruption_modes:
    - id: disposition-agnostic-routing
      signal: Emitting a shared review record and asking later steps to infer approval from fields instead of routing by outcome type.
    - id: rubber-stamp-review
      signal: Approving because commands passed, without checking whether the evidence proves the contracted behavior.
    - id: semantic-shift-dismissal
      signal: Treating meaning changes as harmless cleanup without reviewing their effect on contracts, schemas, or routing.
    - id: forge-mechanic-leakage
      signal: Embedding forge-specific commands or review-tool procedure in the protocol instead of the mechanics layer.
  steps:
    - id: resolve-reviewed-version
      title: Resolve the reviewed version
      intent: Identify the change-proposal version this review judges, so later rounds can be told from earlier ones.
      applies: [orient]
      x-mechanics: [read-artifact]
      needs:
        - change-proposal
      yields: [reviewed-version]
    - id: inspect-against-contract
      title: Inspect against the contract
      intent: Evaluate scope honesty, correctness, semantic shift, and evidence quality; the contract is the measure.
      applies: [code-review]
      x-mechanics: [review]
      needs:
        - reviewed-version
        - behavior-contract
        - { ref: work-unit, optional: true }
        - { ref: implementation-plan, optional: true }
        - { ref: completion-evidence, optional: true }
      yields: [findings]
    - id: classify-findings
      title: Classify findings
      intent: Mark each finding blocking or non-blocking at the point of review.
      needs:
        - findings
      yields: [classified-findings]
    - id: emit-disposition
      title: Emit exactly one disposition
      intent: Record the judgment as exactly one typed outcome artifact; the artifact is the disposition.
      needs:
        - classified-findings
        - reviewed-version
      outcomes:
        group: review-disposition
        one_of:
          - id: approved
            when: No blocking findings remain.
            yields: [change-approved]
          - id: needs-revision
            when: At least one blocking finding remains.
            yields: [change-needs-revision]
---

# Review

Review is the judgment gate between a submitted change proposal and landing.
It is where the pipeline's one act of independent judgment about the change
happens: the proposal is examined against the behavior contract, the
work-unit, and the evidence — then the decision is recorded as exactly one
typed outcome artifact.

The protocol is not a forge operation. The `code-review` skill supplies the
evaluation discipline; this protocol supplies the routing obligation.

## Step: resolve-reviewed-version

Identify the current `change-proposal` version for this work unit. The
disposition's `against_version` names it; without that binding, later rounds
cannot be told from earlier ones.

## Step: inspect-against-contract

Evaluate the proposed change with the `code-review` skill's discipline: scope
honesty against the work-unit, correctness, semantic-shift detection,
evidence quality against the behavior contract and completion evidence,
documentation impact. The contract is the measure — a change is judged by
whether the contracted behaviors are delivered and proven, not by whether
commands passed.

## Step: classify-findings

Each observation is `blocking` or `non-blocking` at the point of review.
Blocking findings prevent approval. Non-blocking findings are recorded only
when they do not affect correctness, traceability, documentation accuracy,
or the ability to continue.

## Step: emit-disposition

The outcome artifact *is* the disposition. There is no disposition-agnostic
review record for later steps to reinterpret, and no triage step between
review and land. Downstream protocols route on the produced artifact type; a
review run that emits zero or two dispositions is invalid. In the deployed
methodology the `review-disposition` group binds to the manifest-declared
required-choice group of the same name, and the runtime enforces
exactly-one as this protocol's postcondition.

A `needs-revision` disposition does not loop inside this protocol: it
re-enters the workflow at `submit`, whose new proposal version re-opens this
gate. The revision loop is visible in the computed inter-protocol graph, not
here.

## Invariant: independence-of-the-gate

Review is the scoped pipeline's independent-judgment gate. Transition
authority lives in this typed disposition, not in per-operation approval
elsewhere (per runa's session-surface contract) — so what the gate enforces
is not a human signature but **independence from the author**: the change is
judged by a context that did not produce it. The author's own momentum must
never approve itself.

Independence is satisfied by a context separate from the one that built the
change — a fresh or separate agent context by default, the operator when
chosen. The capstone is the same typed outcome either way, and the
disposition records the reviewer identity. Who reviews is a choice; that the
reviewer is independent of the author is the invariant.

## Cross-References

- `skills/code-review/SKILL.md` defines the evaluation discipline this
  protocol applies.
- `schemas/change-approved.schema.json` and
  `schemas/change-needs-revision.schema.json` define the typed disposition
  artifacts.
- The artifact-versioned review cycle and typed disposition routing are
  explained in groundwork's
  `docs/architecture/step-2-reference-arc-design.md`.
