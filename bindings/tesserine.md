# The Tesserine Binding

Status: Draft

## Purpose and Scope

This document maps the Agent Protocols standard onto its reference
implementation: the Tesserine ecosystem, where the
[`runa`](https://github.com/tesserine/runa) runtime executes protocols and
the [`groundwork`](https://github.com/tesserine/groundwork) methodology
authors them. It is a map, not a mirror: for everything runtime-owned, the
[runa interface contract](https://github.com/tesserine/runa/blob/main/docs/interface-contract.md)
is authoritative, and this document links to it rather than restating it.
Nothing in the [standard core](../spec/specification.md) depends on this
binding; a different runtime binds with a sibling document beside this one.

## The Mapping

| Standard concept | Tesserine construct |
| --- | --- |
| Protocol document | `protocols/{name}/PROTOCOL.md` — the runtime's methodology layout convention. runa already loads this exact file as the protocol's instruction text, so the canonical model rides the vehicle the runtime reads; no second file exists to drift. |
| Artifact | Artifact type with a JSON Schema at `schemas/{name}.schema.json`, validated by the runtime on production. |
| Precondition | The protocol's `requires` declaration (required entries) and `accepts` declaration (optional entries). *When* the protocol runs is a separate, runtime-owned concern: trigger conditions, declared per protocol and evaluated by runa. |
| Postcondition | The protocol's `produces` declaration plus schema validation. **This is where the guarantee gets its teeth:** runa fails a protocol whose declared outputs are missing or invalid, and completion requires the declared evidence. The standard states the contract; runa enforces it. |
| Disposition (outcome group) | `required_output_choices` — a named group of which exactly one member type must be produced and validate. Identical semantics; the canonical model's `outcomes` group binds to the group of the same name. |
| Work product | No runtime counterpart, by design. Work products are intra-protocol; runa sees only artifacts. A step structure invisible to the runtime is the standard's own layer. |
| Delegation (`applies`) | groundwork's skill population — agent-managed disciplines packaged in the [Agent Skills](https://agentskills.io) envelope, invoked by judgment rather than declared to the runtime. |
| Invariant | An honest gap: invariants are stated in the canonical model and carried in methodology prose, but the runtime does not yet enforce them mechanically. Recorded here as a binding gap, not papered over. |
| Inter-protocol graph | Computed by runa from the protocols' declarations — never authored. Rendered diagrams of it follow the [inter-protocol profile](../spec/notation.md#rendering-the-inter-protocol-graph) and are marked computed. |

### Binding extension fields

This binding defines one extension field on leaf steps:

- `x-mechanics: [<handles>]` — the forge-neutral mechanic handles the step
  uses (groundwork's mechanics layer). Mechanics are operational plumbing,
  not cognition, which is why they ride an extension field rather than the
  standard core.

## Manifest Authority: the Transitional State and the Target

groundwork declares its protocols to runa in a manifest (`manifest.toml`):
artifact types, per-protocol `requires`/`accepts`/`produces`/
`may_produce`/`required_output_choices`, and triggers. The canonical model of
each protocol states a contract and step-level data bindings that fold up to
the same facts.

**In principle, the per-protocol declarations of the manifest are a
runtime-facing projection of the canonical documents** — a view, exactly as
the activity and state views are views: derivable, regenerable, never
independently authoritative. One protocol, one home for its truth
([Single Home](https://github.com/pentaxis93/principles)); the manifest's
proper role is the rendering of that truth in the runtime's input format.

**The transitional state (this version).** runa reads a hand-maintained
manifest today, and rearchitecting that read surface is out of this
standard's scope. For as long as the manifest is hand-maintained, this
binding therefore inverts the authority locally: the manifest is
authoritative for the inter-protocol declarations, and each canonical
document MUST agree with it. Agreement is machine-checked, not
hand-maintained — validation rule
[V12](../spec/canonical-model.md#validation) extends under this binding to a
**manifest convergence check**: the fold of the document's step bindings
(precondition ↔ `requires`/`accepts`; externally-bound yields and outcome
groups ↔ `produces`/`required_output_choices`) must match the manifest entry
of the same name, exactly. Drift between the two surfaces is a validation
failure, not a discovery someone makes later. This state is tolerable only
because it is checked; it remains a named contradiction of the standard's own
one-model principle, which is why it is transitional and not the design.

**The target state (declared).** The manifest's per-protocol declarations are
*generated* from the canonical documents, the same way views are generated —
one projection run, one diff gate. At that point the V12 manifest check
collapses from a convergence check between two authored surfaces into an
ordinary projection check (regenerate and compare, as
[`tools/project.py --check`](../tools/project.py) already does for views),
and the authority inversion disappears. The migration is cheap by
construction — the fold V12 checks today *is* the projection the generator
will emit tomorrow — which is the point of declaring the target now
([Evolvability](https://github.com/pentaxis93/principles)). Sequencing that
migration (the generator, runa's read surface, groundwork's adoption) is
ecosystem governance, owned by its ADR process, not by this document.

## Succession: workflow-contracts

Before this standard, groundwork carried each protocol in two files: prose in
`protocols/{name}/PROTOCOL.md` and a separate TOML graph in
`workflow-contracts/{name}.toml` (nodes, conditional edges, typed terminals).
The two drifted in practice — the observed state of `review` was four prose
steps and four corruption modes beside two TOML nodes and three differently
worded corruption modes — which is the disease the canonical model exists to
cure. The correspondence for migration:

| workflow-contract construct | Canonical model |
| --- | --- |
| `[[nodes]]` with `intent` | steps with `intent` |
| `disciplines` on a node | `applies` on a leaf step |
| `mechanics` on a node | `x-mechanics` on a leaf step |
| `[[edges]]` with `case`/`default` conditions | derived: an `outcomes` group and the branches' data flow |
| `[[edges]]` with `always` | derived: sequence from `needs`/`yields` |
| `[[terminals]]` with `artifact_produced` | externally-bound yields or outcome options |
| `failure_modes`, `corruption_modes` | `corruption_modes` (one home, beside the prose they describe) |

Whether and when groundwork retires `workflow-contracts/` is groundwork's
decision, recorded in its own ADR process; this document records only that
the canonical model subsumes the encoding.

## The Worked Binding

[`examples/review`](../examples/review/PROTOCOL.md) in this repository is
groundwork's `review` protocol re-expressed in the canonical model. As
deployed in groundwork, its contract binds to the manifest entry of the same
name: precondition `change-proposal`, `behavior-contract` (required) with
`work-unit`, `implementation-plan`, `completion-evidence` (optional);
postcondition the `review-disposition` group — exactly one of
`change-approved` or `change-needs-revision`, each with a JSON Schema the
runtime validates. The disposition is the transition authority of the scoped
pipeline (per runa's
[session-surface contract](https://github.com/tesserine/runa/blob/main/docs/session-surface-contract.md)):
downstream protocols route on the produced artifact type, and the
needs-revision path re-enters at `submit` — visible as the loop-back in the
computed inter-protocol graph, not as an intra-protocol edge.

A corpus note for the standard's step-count guidance: groundwork's protocols
run four to seven steps at top level, and one (`decompose`) is a dispatch
among seven alternative operations whose faithful model exceeds seven
top-level nodes — the substrate evidence for why the three-to-seven rule is a
[SHOULD, not a schema bound](../spec/canonical-model.md#validation).
