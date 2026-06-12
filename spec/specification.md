# The Agent Protocols Specification

Status: Draft

## Purpose and Scope

This document defines what a protocol is, the contract that makes it
guaranteed, the canonical model in which it is authored, the views derived
from that model, and the discipline by which it is written. It is the
standard's core and is runtime-agnostic: it specifies the encoding of
cognitive protocols for agents, not the behavior of any runtime that executes
them.

Out of scope here: the typed-edge vocabulary and projection rules
([notation](notation.md)), the serialization format and its validation
([canonical model](canonical-model.md)), and everything a runtime owns —
artifact storage, triggering, scheduling, and enforcement mechanics. A
*binding* maps this standard onto a concrete runtime; the reference
implementation is bound by [bindings/tesserine.md](../bindings/tesserine.md).

The key words MUST, MUST NOT, REQUIRED, SHALL, SHOULD, SHOULD NOT,
RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as
described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) when, and only when, they
appear in all capitals.

## Definitions

**Protocol.** A repeatable cognitive process encoded as a contracted
transformation: it consumes artifacts that satisfy its precondition, performs
a bounded piece of work, and guarantees artifacts that satisfy its
postcondition. A protocol is a contracted node in a workflow graph.

**Skill.** An uncontracted, cross-cutting capability: a discipline an agent
applies wherever its trigger conditions arise, with no guaranteed inputs or
outputs and no fixed position in any workflow. Skills are packaged under the
[Agent Skills](https://agentskills.io) standard.

The line between protocol and skill is *semantics, not packaging*. Both may
ship in the same install-time envelope; what distinguishes them is that a
protocol carries a contract and occupies a position in a graph, while a skill
carries neither. A process that cannot state a precondition and postcondition
is not a protocol; a capability that is consulted from many unrelated points
in a workflow is not a step.

**Artifact.** A work product with a name and a machine-checkable contract
(a schema). Artifacts are the medium of every protocol contract.

**Step.** A constituent of a protocol: one node of its internal graph. A step
is either a *leaf* (it carries operational substance directly or delegates to
a skill) or a *composite* (it decomposes into sub-steps).

**Work product.** A named intermediate result produced by a step and consumed
by other steps within the same protocol. Work products are internal; artifacts
are external. The protocol's contract speaks only of artifacts.

**Canonical model.** The single authoritative representation of a protocol:
its contract, its steps, their data dependencies, outcomes, compositions, and
delegations, together with the protocol's prose. Defined structurally in
[canonical-model.md](canonical-model.md).

**Derived view.** A representation computed from the canonical model — a
diagram, a state report, an ordering. Views are projections; they are never
authored and never authoritative.

**Disposition.** A typed outcome: when a protocol's work can end in more than
one way, each way is a distinct artifact type, and exactly one is produced.
Routing on a disposition's *type* — not on fields inside a shared record — is
what makes branching legible to both readers and machines.

## The Contract

A protocol is guaranteed because it carries a contract, in the sense of
design by contract (Meyer):

- **Precondition** — the artifacts that must exist and validate before the
  protocol may run.
- **Postcondition** — the artifacts guaranteed to exist and validate after it
  runs. Where the protocol ends in a disposition, the postcondition names the
  outcome group and guarantees exactly one member is produced.
- **Invariant** — the named rules the protocol must not violate at any point
  during execution.

Every protocol document MUST state its precondition, postcondition, and
invariants explicitly. The postcondition is the guarantee, and it is not a
slogan: it is stated in terms of artifacts whose schemas can be checked, so
that an executing runtime can refuse to call a run complete while a declared
output is missing or invalid. The contract is what turns "this protocol
produces a review" from a description into a commitment — evidence decides
the claim (principle:
[Verifiable Completion](https://github.com/pentaxis93/principles)).

Enforcement is a runtime property. This standard defines the contract's
*statement*; a binding names the machinery that gives it teeth. A protocol
whose postcondition no runtime checks is still a conforming document — but it
is only guaranteed where it is enforced.

## One Canonical Model, Derived Views

Each protocol has exactly one authoritative representation: its canonical
model. Every other representation is a projection.

**Authoring is declarative, in data flow.** The author states what each step
needs, what it yields, and what it delegates. Execution order is derived from
those dependencies and MUST NOT be authored by hand: steps whose data
dependencies chain are sequential, steps with no dependency path between them
are concurrent, typed outcomes branch, and declared feedback dependencies
loop. The author who writes order directly is duplicating information the
dependencies already carry — and creating the first opportunity for the two
to disagree.

**Views derive.** From the canonical model the following are projected:

- the **activity view** — what happens first, what next, where the process
  branches and loops; the view for *understanding* a protocol;
- the **state view** — what condition a run of the protocol is in, derived
  from which of its declared outputs exist; the view for *monitoring* one.

Projection is total and faithful: every validating canonical model projects
to every view, and every element of a view is the image of a canonical
element under the published [projection rules](notation.md#projection-rules).

**Views are never independently authoritative.** A derived representation
MUST be regenerable from the canonical model and MUST be marked as derived. A
representation that can be edited as a standalone source of truth is a drift
factory: it recreates, inside one protocol, the divergence this standard
exists to cure. Tools MAY let a user edit *through* a view, but the edit MUST
land in the canonical model and the view MUST be re-derived from it. There is
one home for each protocol's truth (principle:
[Single Home](https://github.com/pentaxis93/principles)).

## Two Graphs

A protocol system is one continuous typed graph read at two resolutions, and
composition is the zoom between them.

**The inter-protocol graph** relates protocols to each other through the
artifacts they consume and produce. Where a runtime executes the protocols,
this graph is *computed* by the runtime from the protocols' declared
contracts — it is runtime-owned, and this standard does not redefine it. The
standard's notation [renders](notation.md#rendering-the-inter-protocol-graph)
the computed graph; a hand-drawn inter-protocol diagram asserts nothing.

**The intra-protocol graph** relates the steps within one protocol. It is
owned by this standard, and promoting it from prose to a declarative model is
the standard's central contribution. At the top level a protocol SHOULD
comprise three to seven steps — few enough to hold in the head at a glance.
A process with fewer than three steps is usually a single operation (consider
a skill, or a step of a neighboring protocol); a process needing more than
seven usually contains a seam, and composition is the pressure valve: a step
*decomposes into* sub-steps, and at the deepest level a step *applies a
skill*, delegating a field of mastery rather than inlining it. Delegation
divides ownership cleanly — the step owns what must be true, the skill owns
how it becomes true (principle:
[Sovereignty](https://github.com/pentaxis93/principles)).

Both graphs are written in one typed-edge vocabulary of four families —
control flow, composition, delegation, and data — defined and grounded in
[notation.md](notation.md#the-typed-edge-vocabulary). The vocabulary is as
small as the routing it must carry, and no larger (principle:
[Parsimony](https://github.com/pentaxis93/principles)).

## Authoring Discipline

Prose is the irreducible floor of a protocol — the nature of an elementary
operation can only be explained, and capturing that explanation is the entire
point of writing the protocol down. The discipline is not less prose; it is
prose in its place. Prose is distributed across the whole structure, and its
length scales inversely with abstraction height:

- **The protocol and its composite steps** carry terse prose: purpose,
  contract, the "why this shape" that is not recoverable from the children.
  Terseness here is load-bearing — it is what keeps the skeleton runnable in
  the head.
- **Typed edges** — outcome options and feedback dependencies — carry
  one-line guards: *why this branch, when this loop*. Routing wisdom is
  frequently where the hardest-won mastery lives, and one line is the size at
  which it stays sharp.
- **Leaf steps** carry the substantive operational prose — as much as the
  operation requires and no more — or delegate to a skill, in which case the
  depth lives in the skill (its own home, consulted not copied) and the leaf
  holds only its thin contract and the delegation.

This distribution is how a structure carries decades of wisdom without
re-growing the wall of text, and how the document serves its reader at every
altitude (principle:
[Transmission](https://github.com/pentaxis93/principles)).

Two further practices are RECOMMENDED:

- **Corruption modes.** Name the ways the protocol's guarantee rots — each as
  an identifier plus a one-line signal. Corruption modes are the invariants'
  negative space: where an invariant says what must hold, a corruption mode
  names a recognizable way it fails in practice.
- **Explicit delegation over inlining.** When a leaf's operational prose
  begins to teach a reusable discipline, extract the discipline to a skill
  and delegate. The protocol keeps its shape; the mastery gains a home where
  every protocol can consult it.

## Conformance

A **conforming protocol document**:

1. MUST validate against the canonical-model schema
   ([schemas/protocol.schema.json](../schemas/protocol.schema.json)) and
   satisfy the structural validation rules of
   [canonical-model.md](canonical-model.md#validation);
2. MUST state its contract — precondition, postcondition, invariants — as
   required by [The Contract](#the-contract);
3. MUST NOT author execution order, and MUST mark any committed derived view
   as derived;
4. SHOULD follow the [Authoring Discipline](#authoring-discipline).

A **conforming tool** reads and writes canonical models without loss,
projects views only by the published
[projection rules](notation.md#projection-rules), and never persists a view
as a source of truth.

Machine enforcement in this version of the standard is deliberately minimal:
schema validation plus the structural rules — enough to make the model's
shape trustworthy. A conformance linter for the authoring discipline (prose
budgets, distribution checks) is explicitly out of scope for this version and
belongs to a later iteration. The guarantee itself does not wait on either:
its teeth come from whatever runtime enforces the contract at execution time,
as each binding records.

## References

- Bertrand Meyer, *Object-Oriented Software Construction* — design by
  contract: precondition, postcondition, invariant.
- W.M.P. van der Aalst, A.H.M. ter Hofstede, B. Kiepuszewski, A.P. Barros,
  "Workflow Patterns," *Distributed and Parallel Databases* 14, 5–51 (2003) —
  the control-flow pattern catalog grounding the edge vocabulary.
- David Harel, "Statecharts: a visual formalism for complex systems,"
  *Science of Computer Programming* 8, 231–274 (1987) — hierarchical states
  grounding the composition model.
- [pentaxis93/principles](https://github.com/pentaxis93/principles) — the
  principles corpus this standard reasons from.
- [Agent Skills](https://agentskills.io/specification) — the sibling standard
  for skill packaging.
- [bindings/tesserine.md](../bindings/tesserine.md) — the reference
  implementation's binding.
