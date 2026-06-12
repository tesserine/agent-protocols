# The Protocol Workbench — TUI Design

Status: Design only. This document is informative; the requirements live in
the work-unit issue filed against this repository. Nothing here is built yet,
and building it is a separately governed step.

## Purpose and Scope

A Linux-native terminal tool for working with canonical-model protocol
documents: see a protocol in every representation at once, edit it through
any of them, and persist exactly one thing — the canonical model. The design
exists to prove two properties before any code does: that the derived-views
guardrail of the
[specification](../spec/specification.md#one-canonical-model-derived-views)
can be enforced *by construction* rather than by discipline, and that the
view layer separates from the model cleanly enough that a later GUI or web
front end is cheap.

Out of scope: authoring the inter-protocol graph (runtime-owned; at most a
read-only render), conformance checking beyond schema and structural
validation, and any non-terminal front end (designed *for*, not designed
*here*).

## Stack

**Rust, with [ratatui](https://ratatui.rs) over crossterm.** The reference
runtime (`runa`) is Rust: the ecosystem's contributors, toolchain, and review
muscle are already there, and — decisively — the model layer this tool needs
(a lossless canonical-model parser/serializer with validation) is exactly the
crate a future GUI, a CI gate, or the runtime itself will want. Writing that
layer in any other language strands the most reusable artifact of the
project inside its least reusable shell. Go/bubbletea and Python/textual were
considered and rejected on that single ground; both are fine TUI stacks, and
neither leaves behind a model crate the ecosystem can link.

## Architecture: three layers, dependency-clean

```text
+----------------------------------------------------------+
|  workbench (binary)        ratatui; owns no protocol state |
+-----------------------------+------------------------------+
|  projection (lib crate)     pure fns; no mutation API      |
+-----------------------------+------------------------------+
|  model (lib crate)          parse/serialize/validate/edit  |
+----------------------------------------------------------+
```

**The model crate** owns the canonical-model document:

- *Lossless parse and serialize* per the format's
  [round-trip rules](../spec/canonical-model.md#round-trip): frontmatter
  field order, comments, body bytes, and unknown `x-` fields survive a
  load/save cycle untouched. Internally this means a concrete-syntax-aware
  YAML layer, not a load-to-plain-data one.
- *Validation*: the schema plus structural rules V1–V12, with errors
  addressed to elements (step id, option id, section anchor), not byte
  offsets alone.
- *Element identity*: every node and edge of the model is addressable by a
  stable `ElementId` (step ids, `(group, option)` pairs, invariant and
  corruption ids, need entries by `(step, ref)`). Ids are the join keys of
  the whole design — selection, projection, and editing all speak them.
- *Edit operations*: a closed command enum (`SetIntent`, `AddNeed`,
  `RemoveStep`, `BindSectionProse`, …) with `apply` and `invert`, giving
  undo/redo and a single choke point where every mutation re-validates.

**The projection crate** depends only on the model crate and exports pure
functions: canonical model → activity-view structure, → state-view structure
(model plus an optional artifact snapshot), → Mermaid text. It implements the
[projection rules](../spec/notation.md#projection-rules) and nothing else.
It has **no mutation API**: view structures carry `ElementId`s and display
data, and there is no setter to call. This is the derived-views guardrail
made unviolable by construction — a view cannot become a source of truth
because the type system gives it no pen. Parity with the reference projector
(`tools/project.py`) over the same documents is a test-suite obligation, so
the two implementations of the projection rules check each other.

**The workbench binary** renders projections and routes input. It owns zero
protocol state: its entire world is (document, selection, dirty flag,
validation report), all read from the model crate.

## The workbench

One protocol open at a time, four synchronized representations, each a pane
or tab:

| Pane | Shows | Backed by |
| --- | --- | --- |
| Model | the structured tree: contract, invariants, corruption modes, steps with needs/yields/outcomes | model crate |
| Activity | the activity view, laid out as a navigable graph | projection crate |
| State | the state view: same topology, status-classed (baseline without a snapshot; live with one) | projection crate |
| Raw | the serialized document, read-only, scrolled to the selection | model crate |

Plus a **contract inspector** — precondition, postcondition, invariants —
permanently reachable (the contract is the protocol's identity; it is never
more than one keypress away), and a status bar carrying validation state,
dirty flag, and the current element's id.

**Selection is element identity.** Selecting a node or edge anywhere —
keyboard in any pane, mouse where the terminal reports it — resolves to an
`ElementId`, and every pane re-cursors to its rendering of that element. The
panes are four lenses over one selection, which is what makes them feel like
one document rather than four.

**Every mouse action has a keyboard equivalent.** The tool runs in a plain
terminal with no graphical environment and no mouse support degraded to
nothing worse than navigation by keys.

## The edit loop

```text
input → resolve ElementId → build Command → model.apply()
      → re-validate → re-project all panes → render
```

Edits initiate from any pane — including the derived views: *edit through a
view* means the view's selection names the element and the edit dispatches a
model command; the view itself is regenerated on the next frame, never
patched. Short fields (titles, one-line intents, guards) edit inline in the
Model pane. The raw pane takes no edits; it is the serialization made
visible, and the place where an invalid-on-open document remains usable.

**Prose edits leave the terminal.** Body sections, preambles, and any field
the author wants room for open in `$EDITOR`: suspend the TUI, write the
text to a tempfile, exec the editor, read it back on exit, re-validate,
resume. A validation failure (a body edit that breaks an anchor, say) shows
the error and offers re-edit or discard — never a silent save.

**Save writes one file.** Serialization goes through the model crate's
lossless writer; an open-then-save with no edits is byte-identical. If
committed views exist beside the document (`views/`), save offers to
regenerate them — the TUI equivalent of `tools/project.py`, and the only way
view files ever change.

**Invalid documents degrade, not die.** A file that fails validation on open
is shown in the raw pane with its error report; structured editing unlocks
when the document parses, fully when it validates. The tool is most needed
exactly when the document is broken.

## Separability

What a later GUI or web front end reuses, by layer:

| Layer | Reused | Notes |
| --- | --- | --- |
| model crate | wholly | parse/serialize/validate/commands are UI-free |
| projection crate | wholly | pure structure-to-structure; Mermaid text output feeds any renderer |
| selection/edit-loop design | as a pattern | ElementId-based selection and command dispatch port directly |
| workbench binary | not at all | ratatui rendering and key/mouse routing are the only throwaway |

Both library crates carry headless test suites (round-trip corpus,
validation fixtures, projection parity against `tools/project.py`); the
binary adds only interaction tests. The cheap-next-change property is the
point: the standard's
[evolution posture](../spec/canonical-model.md#evolution) for documents is
mirrored here for tooling.
