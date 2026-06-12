# The Canonical-Model Format

Status: Draft

## Purpose and Scope

This document defines the serialization of a protocol's canonical model: the
file an author touches and an editor manipulates. It specifies the document
envelope, the structured model, the body grammar that binds prose to model
elements, and the validation rules. The semantics of the model's relations
live in [notation.md](notation.md); the concepts live in
[specification.md](specification.md).

## The Document

A protocol's canonical model is **one Markdown file**: YAML frontmatter
carrying the complete structured model, and a Markdown body carrying the
substantive prose, bound to model elements by the
[anchor grammar](#the-body). This is the same envelope the
[Agent Skills](https://agentskills.io/specification) standard uses for
`SKILL.md` — structure in the header, document below — so a protocol sits
beside a skill with no new dialect, renders as a document wherever Markdown
renders, and remains one file that cannot drift against itself.

The choice follows from the format's constraints. Prose is first-class: the
body *is* prose, rendered, unescaped, owning as much room as the wisdom
needs. Structure wraps prose without burying it: the frontmatter holds every
machine-readable atom, and not one paragraph lives inside a string field it
doesn't fit. And the file round-trips: frontmatter parses to data that
validates against [the schema](../schemas/protocol.schema.json), and the
projection rules consume that data without loss.

YAML is used in its safe subset: documents MUST parse under a safe loader;
custom tags, anchors, and aliases MUST NOT be used; every prose-bearing field
is a plain string.

## The Structured Model

Top-level frontmatter fields:

| Field | Required | Contents |
| --- | --- | --- |
| `name` | yes | ≤64 characters; lowercase letters, digits, hyphens; no leading/trailing/consecutive hyphens. Names the protocol. |
| `description` | yes | ≤1024 characters; what the protocol does and when it runs. |
| `metadata` | no | Arbitrary key-value mapping for human-facing context (version, provenance). Carries no model semantics. |
| `protocol` | yes | The model itself, below. |

The `protocol` object:

| Field | Required | Contents |
| --- | --- | --- |
| `spec` | yes | The format version this document is written against. This version: `"1"`. |
| `intent` | yes | One line (≤140): the protocol's purpose. |
| `contract` | yes | Precondition and postcondition; see [The Contract](#the-contract). |
| `invariants` | no | List of `{id, rule}`; `rule` is one line (≤200) stating what must hold throughout. |
| `corruption_modes` | no | List of `{id, signal}`; `signal` is one line (≤200) naming a recognizable way the guarantee rots. |
| `steps` | yes | The step list; see [Steps](#steps). |

Unrecognized fields are rejected, except fields prefixed `x-`, which are
reserved for extensions (a binding may define them; conforming tools preserve
them).

### The Contract

```yaml
contract:
  precondition:
    - change-proposal
    - { ref: work-unit, optional: true }
  postcondition:
    - { group: review-disposition, one_of: [change-approved, change-needs-revision] }
```

- `precondition` — the artifact types that must exist and validate before the
  protocol runs. An entry is an artifact-type name, or
  `{ ref: <name>, optional: true }` for an artifact the protocol uses when
  present but does not require.
- `postcondition` — what is guaranteed after the protocol runs. An entry is
  an artifact-type name (the artifact will exist and validate), or
  `{ group: <name>, one_of: [<names>] }` (exactly one member type will exist
  and validate — a disposition).

The contract is stated here and *checked* against the steps: validation rule
V12 requires the contract to equal the fold of the steps' external data
bindings, so the explicit statement can never silently disagree with the
structure beneath it.

### Steps

A step is a leaf or a composite.

**Leaf step:**

```yaml
- id: inspect-against-contract
  title: Inspect against the contract
  intent: Evaluate scope honesty, correctness, semantic shift, and evidence quality.
  applies: [code-review]
  needs:
    - reviewed-version
    - behavior-contract
    - { ref: completion-evidence, optional: true }
  yields: [findings]
```

| Field | Required | Contents |
| --- | --- | --- |
| `id` | yes | Unique in the document; same lexical rules as `name`. |
| `title` | yes | ≤80 characters; the step's display name. |
| `intent` | yes | One line (≤140): what the step accomplishes. |
| `needs` | no | What the step consumes; entry forms below. |
| `yields` | no | Names of work products or artifact types the step produces. |
| `outcomes` | no | A typed-outcome group; see below. |
| `applies` | no | Names of skills the step applies (delegation). |

**Need entry forms:**

| Form | Meaning |
| --- | --- |
| `<name>` | Required: the step runs only when this exists. |
| `{ ref: <name>, optional: true }` | Soft: consumed when present, not waited for. |
| `{ ref: <name>, feedback: true, when: <one line> }` | Loop-back: a later step's yield re-enables this one. Does not gate first activation; the ref MUST be an internal work product; `when` is optional. |
| `{ any_of: [<names>] }` | Merge: satisfied by whichever of mutually exclusive branches ran. |

**Outcomes** — when a step's work ends in exactly one of several typed ways:

```yaml
outcomes:
  group: review-disposition
  one_of:
    - id: approved
      when: No blocking findings remain.
      yields: [change-approved]
    - id: needs-revision
      when: At least one blocking finding remains.
      yields: [change-needs-revision]
```

`group` names the choice; `one_of` lists two or more options, each with a
unique `id`, a one-line guard `when` (≤140) — the routing wisdom — and the
`yields` produced only on that branch.

**Composite step** — groups sub-steps and carries nothing else:

```yaml
- id: execute
  title: Execute
  intent: Carry the plan through to a verified result.
  steps:
    - …
```

A composite declares `id`, `title`, `intent`, and `steps` (two or more);
its data interface is wholly derived from its children. Identifiers and
work-product names are document-global: nesting deepens the view, not the
namespace.

Step order in the YAML list is **non-semantic**. Order is always derived from
the dependency graph; the list order only breaks ties in projections.

### Namespaces

Two name populations exist and MUST be disjoint (V2):

- **artifact types** — external; exactly the names appearing in the contract;
- **work products** — internal; every other name appearing in `yields`.

A bare name is therefore never ambiguous. A yield whose name appears in the
postcondition is *externally bound*: producing it is what discharges the
guarantee. A need whose name appears in the precondition consumes an external
artifact; all other needs consume work products of sibling steps.

## The Body

Everything after the frontmatter is the protocol's prose. The body is bound
to the model by headings:

- A level-2 heading of the form `## Step: <id>`, `## Invariant: <id>`, or
  `## Corruption: <id>` opens a section (running to the next level-2
  heading) attached to the named model element.
- The **preamble** — everything between the document's H1 and its first
  level-2 heading — is the protocol's narrative purpose.
- Any other level-2 heading is free protocol-level prose (cross-references,
  background), attached to no element.

The prose discipline of the
[specification](specification.md#authoring-discipline) lands here
concretely: composite steps and the protocol itself keep terse sections or
none (their one-line `intent` often suffices); outcome options carry their
wisdom in `when` and need no sections; leaf steps carry the substantive
operational prose. A leaf step MUST have an anchored body section or an
`applies` delegation (V6) — operational depth has exactly one home: written
here, or owned by a skill.

## Validation

A document is valid when the schema accepts its parsed frontmatter **and**
the structural rules hold. The split exists because a schema checks shape,
not graphs.

**Schema** ([schemas/protocol.schema.json](../schemas/protocol.schema.json),
JSON Schema 2020-12): field presence, types, lexical rules, length budgets,
and the closed field set (`x-` excepted).

**Structural rules** (MUST; checked by the reference validator,
[tools/validate.py](../tools/validate.py)):

| Rule | Statement |
| --- | --- |
| V1 | Every `id` (steps at all depths, outcome options, invariants, corruption modes) is unique in the document. |
| V2 | Artifact-type names and work-product names are disjoint. |
| V3 | Every need ref — including `any_of` members and feedback refs — resolves to a declared yield or a precondition artifact type. |
| V4 | The dependency graph with feedback needs removed is acyclic. |
| V5 | Every feedback need closes a cycle when restored, and its ref is an internal work product. A feedback mark that closes no cycle is an error, not a decoration. |
| V6 | Every leaf step has an `applies` delegation or an anchored `## Step:` body section. |
| V7 | Every anchored heading names an existing element id; no element is anchored twice. |
| V8 | Every outcome option yields at least one name; across the options of one group, externally-bound yields are distinct artifact types. |
| V9 | Each artifact type in the postcondition is yielded by exactly one step or option — or by several that lie on mutually exclusive branches of one outcome group. |
| V10 | The members of an `any_of` need originate on mutually exclusive branches; an `any_of` over concurrent producers is a race, and an error. |
| V11 | Every step lies on a path from an entry step (one whose required needs are all external) to an exit (an externally-bound yield or outcome), and every internal work product is consumed by some step. |
| V12 | The contract equals the fold of the steps: required external needs ↔ `precondition` entries; optional external needs ↔ `optional` entries; externally-bound yields and outcome groups ↔ `postcondition` entries — exactly, in both directions. |

**Step count is guidance, not validity.** The schema requires at least one
step and sets no maximum; the three-to-seven rule of the
[specification](specification.md#two-graphs) is a SHOULD. The bound is craft,
and real corpora falsify it as a hard rule: a protocol whose top level is a
dispatch among alternative operations can legitimately exceed seven, and
forcing it under an artificial composite would be shape for shape's sake.
Fewer than three suggests the process is one operation — a skill, or a
neighbor's step. The reference validator reports departures from the range as
warnings, never failures.

## Round-Trip

Two round-trips are normative:

- **Document round-trip.** Parsing a valid document and re-serializing it
  MUST preserve its semantics: the same model, the same prose bindings.
  Conforming editors preserve field order, comments, and `x-` fields they do
  not understand.
- **View round-trip.** The document projects to the derived views totally and
  faithfully, per the
  [losslessness definition](notation.md#losslessness). Views regenerate;
  they are never edited.

## Evolution

`protocol.spec` gates breaking change: a document declares the format version
it is written against, and a future version that changes semantics changes
the value. Three properties are designed in now so the next change is cheap:
list order is non-semantic (reordering is never a semantic diff), ids are the
stable join keys (prose, views, and tools address elements only by id), and
`x-` fields pass through unparsed (extensions need no fork). A richer
serialization, should one be warranted, arrives as a sibling binding of the
same abstract model — the relations and their semantics are
serialization-independent by construction
([notation](notation.md#evolution)).
