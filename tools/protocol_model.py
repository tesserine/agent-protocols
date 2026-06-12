"""Shared model layer for the Agent Protocols reference tools.

Parses a canonical-model document (spec/canonical-model.md), checks the
structural validation rules V1-V12, and computes the dependency graph the
projections consume.

Boundary note: this module implements exactly the schema validation and
structural rules of the specification. It is not a conformance linter for
the authoring discipline; that is explicitly out of scope for this version
of the standard.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "protocol.schema.json"

SECTION_RE = re.compile(r"^## (Step|Invariant|Corruption): (\S+)\s*$", re.M)


@dataclass
class Need:
    ref: str | None
    kind: str  # required | optional | feedback | any_of
    when: str | None = None
    members: tuple[str, ...] = ()

    def refs(self) -> tuple[str, ...]:
        return self.members if self.kind == "any_of" else (self.ref,)


@dataclass
class Option:
    id: str
    when: str
    yields: tuple[str, ...]


@dataclass
class Step:
    id: str
    title: str
    intent: str
    needs: list[Need] = field(default_factory=list)
    yields: tuple[str, ...] = ()
    group: str | None = None
    options: list[Option] = field(default_factory=list)
    applies: tuple[str, ...] = ()
    children: list["Step"] = field(default_factory=list)
    order: int = 0

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def all_yields(self) -> set[str]:
        out = set(self.yields)
        for option in self.options:
            out.update(option.yields)
        return out


@dataclass
class Edge:
    src: str
    dst: str
    products: tuple[str, ...]
    option: tuple[str, str] | None = None  # (group, option id)
    feedback: bool = False
    when: str | None = None


@dataclass
class Document:
    path: Path
    front: dict
    body: str
    sections: list[tuple[str, str]]  # (kind, id) in document order

    # populated by build_model
    name: str = ""
    steps: list[Step] = field(default_factory=list)  # top level
    flat: list[Step] = field(default_factory=list)  # all depths, doc order
    pre_required: list[str] = field(default_factory=list)
    pre_optional: list[str] = field(default_factory=list)
    post_direct: list[str] = field(default_factory=list)
    post_groups: dict[str, tuple[str, ...]] = field(default_factory=dict)
    invariant_ids: list[str] = field(default_factory=list)
    corruption_ids: list[str] = field(default_factory=list)


def parse_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: no YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{path}: unterminated YAML frontmatter")
    front = yaml.safe_load(text[4:end])
    body = text[end + 5 :]
    sections = [(m.group(1), m.group(2)) for m in SECTION_RE.finditer(body)]
    return Document(path=path, front=front, body=body, sections=sections)


def schema_errors(front: dict) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(front), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"schema: {where}: {err.message}")
    return errors


def _parse_need(raw) -> Need:
    if isinstance(raw, str):
        return Need(ref=raw, kind="required")
    if "any_of" in raw:
        return Need(ref=None, kind="any_of", members=tuple(raw["any_of"]))
    if raw.get("feedback"):
        return Need(ref=raw["ref"], kind="feedback", when=raw.get("when"))
    return Need(ref=raw["ref"], kind="optional")


def _parse_step(raw, counter) -> Step:
    step = Step(
        id=raw["id"],
        title=raw["title"],
        intent=raw["intent"],
        order=next(counter),
    )
    if "steps" in raw:
        step.children = [_parse_step(child, counter) for child in raw["steps"]]
        return step
    step.needs = [_parse_need(n) for n in raw.get("needs", [])]
    step.yields = tuple(raw.get("yields", []))
    step.applies = tuple(raw.get("applies", []))
    outcomes = raw.get("outcomes")
    if outcomes:
        step.group = outcomes["group"]
        step.options = [
            Option(id=o["id"], when=o["when"], yields=tuple(o["yields"]))
            for o in outcomes["one_of"]
        ]
    return step


def build_model(doc: Document) -> Document:
    front = doc.front
    protocol = front["protocol"]
    doc.name = front["name"]
    counter = iter(range(10_000))
    doc.steps = [_parse_step(s, counter) for s in protocol["steps"]]

    def flatten(steps):
        for s in steps:
            yield s
            yield from flatten(s.children)

    doc.flat = list(flatten(doc.steps))

    for entry in protocol["contract"]["precondition"]:
        if isinstance(entry, str):
            doc.pre_required.append(entry)
        else:
            doc.pre_optional.append(entry["ref"])
    for entry in protocol["contract"]["postcondition"]:
        if isinstance(entry, str):
            doc.post_direct.append(entry)
        else:
            doc.post_groups[entry["group"]] = tuple(entry["one_of"])

    doc.invariant_ids = [i["id"] for i in protocol.get("invariants", [])]
    doc.corruption_ids = [c["id"] for c in protocol.get("corruption_modes", [])]
    return doc


def contract_names(doc: Document) -> set[str]:
    names = set(doc.pre_required) | set(doc.pre_optional) | set(doc.post_direct)
    for members in doc.post_groups.values():
        names.update(members)
    return names


def external_outputs(doc: Document) -> set[str]:
    names = set(doc.post_direct)
    for members in doc.post_groups.values():
        names.update(members)
    return names


def producers(doc: Document) -> dict[str, list[tuple[Step, Option | None]]]:
    """Map of yielded name -> [(step, option-or-None)]."""
    out: dict[str, list[tuple[Step, Option | None]]] = {}
    for step in doc.flat:
        for name in step.yields:
            out.setdefault(name, []).append((step, None))
        for option in step.options:
            for name in option.yields:
                out.setdefault(name, []).append((step, option))
    return out


def build_edges(doc: Document) -> list[Edge]:
    """Data edges between steps, including feedback edges."""
    prod = producers(doc)
    by_id = {s.id: s for s in doc.flat}
    edges: dict[tuple[str, str, bool], Edge] = {}
    feedback_edges: list[Edge] = []
    for step in doc.flat:
        for need in step.needs:
            for ref in need.refs():
                for src, option in prod.get(ref, []):
                    if src.id == step.id:
                        continue
                    if need.kind == "feedback":
                        feedback_edges.append(
                            Edge(
                                src=src.id,
                                dst=step.id,
                                products=(ref,),
                                option=(src.group, option.id) if option else None,
                                feedback=True,
                                when=need.when,
                            )
                        )
                        continue
                    key = (src.id, step.id, option.id if option else "")
                    if key in edges:
                        edges[key] = Edge(
                            src=src.id,
                            dst=step.id,
                            products=tuple(sorted(set(edges[key].products) | {ref})),
                            option=edges[key].option,
                        )
                    else:
                        edges[key] = Edge(
                            src=src.id,
                            dst=step.id,
                            products=(ref,),
                            option=(src.group, option.id) if option else None,
                        )
    ordered = sorted(
        edges.values(), key=lambda e: (by_id[e.src].order, by_id[e.dst].order)
    )
    return ordered + feedback_edges


def forward_edges(edges: list[Edge]) -> list[Edge]:
    return [e for e in edges if not e.feedback]


def adjacency(edges: list[Edge]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for e in edges:
        adj.setdefault(e.src, set()).add(e.dst)
    return adj


def has_path(adj: dict[str, set[str]], src: str, dst: str, skip_direct=False) -> bool:
    seen = set()
    stack = []
    for nxt in adj.get(src, ()):
        if skip_direct and nxt == dst:
            continue
        stack.append(nxt)
    while stack:
        node = stack.pop()
        if node == dst:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adj.get(node, ()))
    return False


def find_cycle(doc: Document, edges: list[Edge]) -> list[str] | None:
    """Kahn's algorithm over non-feedback edges; returns cycle nodes or None."""
    nodes = [s.id for s in doc.flat]
    indeg = {n: 0 for n in nodes}
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for e in forward_edges(edges):
        if e.dst not in adj[e.src]:
            adj[e.src].add(e.dst)
            indeg[e.dst] += 1
    queue = [n for n in nodes if indeg[n] == 0]
    seen = 0
    while queue:
        node = queue.pop()
        seen += 1
        for nxt in adj[node]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if seen == len(nodes):
        return None
    return sorted(n for n in nodes if indeg[n] > 0)


def branch_tags(doc: Document, edges: list[Edge]) -> dict[str, set[tuple[str, str]]]:
    """For each step, the set of (group, option) branches it lies on."""
    tags: dict[str, set[tuple[str, str]]] = {s.id: set() for s in doc.flat}
    fwd = forward_edges(edges)
    changed = True
    while changed:
        changed = False
        for e in fwd:
            new = set(tags[e.src])
            if e.option:
                new.add(e.option)
            if not new <= tags[e.dst]:
                tags[e.dst].update(new)
                changed = True
    return tags


def mutually_exclusive(
    tags_a: set[tuple[str, str]], tags_b: set[tuple[str, str]]
) -> bool:
    groups_a = {g: o for g, o in tags_a}
    return any(g in groups_a and groups_a[g] != o for g, o in tags_b)


def transitive_reduction(edges: list[Edge]) -> list[Edge]:
    fwd = forward_edges(edges)
    adj = adjacency(fwd)
    kept = []
    for e in fwd:
        if has_path(adj, e.src, e.dst, skip_direct=True):
            continue
        kept.append(e)
    return kept


def entry_steps(doc: Document) -> list[Step]:
    externals = contract_names(doc)
    prod = producers(doc)
    entries = []
    for step in doc.flat:
        if not step.is_leaf:
            continue
        gated = False
        for need in step.needs:
            if need.kind in ("optional", "feedback"):
                continue
            for ref in need.refs():
                if ref not in externals and ref in prod:
                    gated = True
        if not gated:
            entries.append(step)
    return entries


def validate_structure(doc: Document) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) for rules V1-V12 of spec/canonical-model.md."""
    errors: list[str] = []
    warnings: list[str] = []

    # V1 — id uniqueness across steps, options, invariants, corruption modes.
    ids: list[str] = [s.id for s in doc.flat]
    for s in doc.flat:
        ids.extend(o.id for o in s.options)
    ids.extend(doc.invariant_ids)
    ids.extend(doc.corruption_ids)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"V1: duplicate ids: {', '.join(dupes)}")

    externals = contract_names(doc)
    ext_out = external_outputs(doc)
    pre_names = set(doc.pre_required) | set(doc.pre_optional)
    prod = producers(doc)

    # V2 — namespace disjointness: a yield is externally bound (postcondition)
    # or internal; yielding a precondition-only name collides the namespaces.
    for step in doc.flat:
        for name in sorted(step.all_yields()):
            if name in pre_names and name not in ext_out:
                errors.append(
                    f"V2: step '{step.id}' yields '{name}', which is a "
                    "precondition artifact type, not a work product"
                )

    # V3 — every need ref resolves.
    resolvable = set(prod) | pre_names
    for step in doc.flat:
        for need in step.needs:
            for ref in need.refs():
                if ref not in resolvable:
                    errors.append(
                        f"V3: step '{step.id}' needs '{ref}', which nothing "
                        "yields and the precondition does not provide"
                    )

    edges = build_edges(doc)

    # V4 — acyclic without feedback edges.
    cycle = find_cycle(doc, edges)
    if cycle:
        errors.append(
            "V4: dependency cycle (excluding feedback needs) through: "
            + ", ".join(cycle)
        )
        return errors, warnings  # graph rules below assume a DAG

    fwd_adj = adjacency(forward_edges(edges))

    # V5 — every feedback need closes a cycle and refs a work product.
    for step in doc.flat:
        for need in step.needs:
            if need.kind != "feedback":
                continue
            if need.ref in externals:
                errors.append(
                    f"V5: feedback need '{need.ref}' on step '{step.id}' "
                    "refs an artifact type; feedback refs are work products"
                )
            for src, _ in prod.get(need.ref, []):
                if not has_path(fwd_adj, step.id, src.id):
                    errors.append(
                        f"V5: feedback need '{need.ref}' on step '{step.id}' "
                        f"closes no cycle: '{src.id}' is not downstream of it"
                    )

    # V6 — every leaf has a delegation or an anchored body section.
    sections = set(doc.sections)
    for step in doc.flat:
        if step.is_leaf and not step.applies and ("Step", step.id) not in sections:
            errors.append(
                f"V6: leaf step '{step.id}' has neither `applies` nor a "
                f"`## Step: {step.id}` body section"
            )

    # V7 — anchored headings bind existing ids, none twice.
    step_ids = {s.id for s in doc.flat}
    targets = {
        "Step": step_ids,
        "Invariant": set(doc.invariant_ids),
        "Corruption": set(doc.corruption_ids),
    }
    seen_sections: set[tuple[str, str]] = set()
    for kind, sid in doc.sections:
        if sid not in targets[kind]:
            errors.append(f"V7: section '## {kind}: {sid}' names no declared element")
        if (kind, sid) in seen_sections:
            errors.append(f"V7: element '{sid}' is anchored by two sections")
        seen_sections.add((kind, sid))

    # V8 — option yields nonempty (schema) and externally distinct per group.
    for step in doc.flat:
        if not step.options:
            continue
        seen_ext: dict[str, str] = {}
        for option in step.options:
            for name in option.yields:
                if name in ext_out:
                    if name in seen_ext:
                        errors.append(
                            f"V8: outcome group '{step.group}': options "
                            f"'{seen_ext[name]}' and '{option.id}' both yield "
                            f"externally-bound '{name}'"
                        )
                    seen_ext[name] = option.id

    tags = branch_tags(doc, edges)

    def producer_exclusive(a: tuple[Step, Option | None], b: tuple[Step, Option | None]) -> bool:
        tags_a = set(tags[a[0].id])
        tags_b = set(tags[b[0].id])
        if a[1] is not None:
            tags_a.add((a[0].group, a[1].id))
        if b[1] is not None:
            tags_b.add((b[0].group, b[1].id))
        return mutually_exclusive(tags_a, tags_b)

    # V9 — single producer per postcondition artifact, or exclusive producers.
    for name in sorted(ext_out):
        who = prod.get(name, [])
        if len(who) <= 1:
            continue
        for i, a in enumerate(who):
            for b in who[i + 1 :]:
                if not producer_exclusive(a, b):
                    errors.append(
                        f"V9: '{name}' is produced by '{a[0].id}' and "
                        f"'{b[0].id}', which are not mutually exclusive"
                    )

    # V10 — any_of members originate on mutually exclusive branches.
    for step in doc.flat:
        for need in step.needs:
            if need.kind != "any_of":
                continue
            member_producers = [prod.get(m, []) for m in need.members]
            for i, group_a in enumerate(member_producers):
                for group_b in member_producers[i + 1 :]:
                    for a in group_a:
                        for b in group_b:
                            if not producer_exclusive(a, b):
                                errors.append(
                                    f"V10: any_of on step '{step.id}': "
                                    f"producers '{a[0].id}' and '{b[0].id}' "
                                    "are not mutually exclusive — a race"
                                )

    # V11 — reachability entry-to-exit; every work product consumed.
    entries = {s.id for s in entry_steps(doc)}
    exits = set()
    for step in doc.flat:
        if set(step.yields) & ext_out:
            exits.add(step.id)
        for option in step.options:
            if set(option.yields) & ext_out:
                exits.add(step.id)
    all_adj = adjacency(edges)  # feedback included for reachability
    reachable = set(entries)
    stack = list(entries)
    while stack:
        node = stack.pop()
        for nxt in all_adj.get(node, ()):
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    rev: dict[str, set[str]] = {}
    for e in edges:
        rev.setdefault(e.dst, set()).add(e.src)
    coreachable = set(exits)
    stack = list(exits)
    while stack:
        node = stack.pop()
        for nxt in rev.get(node, ()):
            if nxt not in coreachable:
                coreachable.add(nxt)
                stack.append(nxt)
    for step in doc.flat:
        if not step.is_leaf:
            continue
        if step.id not in reachable:
            errors.append(f"V11: step '{step.id}' is unreachable from any entry step")
        if step.id not in coreachable:
            errors.append(f"V11: step '{step.id}' reaches no exit")
    consumed = set()
    for step in doc.flat:
        for need in step.needs:
            consumed.update(need.refs())
    for name in sorted(set(prod) - ext_out):
        if name not in consumed:
            errors.append(f"V11: work product '{name}' is yielded but never consumed")

    # V12 — the contract equals the fold of the steps.
    used_required: set[str] = set()
    used_optional: set[str] = set()
    for step in doc.flat:
        for need in step.needs:
            for ref in need.refs():
                if ref in pre_names:
                    if need.kind == "optional":
                        used_optional.add(ref)
                    elif need.kind != "feedback":
                        used_required.add(ref)
    used_optional -= used_required
    if used_required != set(doc.pre_required):
        errors.append(
            "V12: precondition (required) does not equal the fold of required "
            f"external needs: contract {sorted(doc.pre_required)} vs fold "
            f"{sorted(used_required)}"
        )
    if used_optional != set(doc.pre_optional):
        errors.append(
            "V12: precondition (optional) does not equal the fold of optional "
            f"external needs: contract {sorted(doc.pre_optional)} vs fold "
            f"{sorted(used_optional)}"
        )
    plain_external_yields = set()
    for step in doc.flat:
        plain_external_yields.update(set(step.yields) & ext_out)
    if plain_external_yields != set(doc.post_direct):
        errors.append(
            "V12: postcondition does not equal the fold of externally-bound "
            f"yields: contract {sorted(doc.post_direct)} vs fold "
            f"{sorted(plain_external_yields)}"
        )
    step_groups = {s.group: s for s in doc.flat if s.group}
    if set(step_groups) != set(doc.post_groups):
        # groups with only internal yields are intra-protocol and not folded
        folded = {
            g: s
            for g, s in step_groups.items()
            if any(set(o.yields) & ext_out for o in s.options)
        }
        if set(folded) != set(doc.post_groups):
            errors.append(
                "V12: postcondition outcome groups "
                f"{sorted(doc.post_groups)} do not equal the externally-bound "
                f"groups of the steps {sorted(folded)}"
            )
        step_groups = folded
    for group, members in doc.post_groups.items():
        step = step_groups.get(group)
        if step is None:
            continue
        union: set[str] = set()
        for option in step.options:
            bound = set(option.yields) & set(members)
            if len(bound) != 1:
                errors.append(
                    f"V12: option '{option.id}' of group '{group}' yields "
                    f"{len(bound)} members of the group; exactly one required"
                )
            union.update(bound)
        if union != set(members):
            errors.append(
                f"V12: group '{group}' members {sorted(members)} do not equal "
                f"the union of its options' bound yields {sorted(union)}"
            )

    # Guidance (SHOULD, never a failure): the three-to-seven rule.
    top = len(doc.steps)
    if not 3 <= top <= 7:
        warnings.append(
            f"step-count guidance: {top} top-level steps; the specification "
            "recommends three to seven (SHOULD)"
        )

    return errors, warnings


def load(path: Path) -> tuple[Document, list[str], list[str]]:
    """Parse, schema-check, and structurally validate a document."""
    doc = parse_document(path)
    errors = schema_errors(doc.front)
    if errors:
        return doc, errors, []
    build_model(doc)
    struct_errors, warnings = validate_structure(doc)
    return doc, struct_errors, warnings
