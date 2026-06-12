#!/usr/bin/env python3
"""Project canonical-model protocol documents to their derived views.

Implements the projection rules of spec/notation.md: the activity view and
the state view, both Mermaid stateDiagram-v2, written to views/activity.md
and views/state.md beside the protocol document. Projection is
deterministic: the same canonical model yields byte-identical views.

The state view emitted here is the baseline (no run in progress): every step
pending. Live status is computed by an executing runtime or editor from the
same projection with an artifact snapshot as second input.

Usage:
  project.py DIR [DIR ...]          regenerate views in DIR/views/
  project.py --check DIR [DIR ...]  regenerate and diff against committed views
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocol_model as pm

BANNER = (
    "<!-- DERIVED VIEW — do not edit. Generated from ../PROTOCOL.md by "
    "tools/project.py; regenerate with: .venv/bin/python tools/project.py {dir} -->"
)

STATE_CLASSES = [
    "classDef complete fill:#1a7f37,color:#fff",
    "classDef active fill:#bf8700,color:#fff",
    "classDef pending fill:#57606a,color:#fff",
]


def mangle(identifier: str, taken: dict[str, str]) -> str:
    mangled = identifier.replace("-", "_")
    if taken.get(mangled, identifier) != identifier:
        raise ValueError(f"mangled-id collision: '{identifier}' vs '{taken[mangled]}'")
    taken[mangled] = identifier
    return mangled


def one_line(text: str) -> str:
    """Sanitize prose for a Mermaid label: collapse whitespace and replace
    semicolons, which are statement separators in the rendering dialect
    (spec/notation.md, Mermaid Rendering)."""
    return " ".join(text.split()).replace(";", ",")


def project(doc: pm.Document) -> dict[str, str]:
    """Returns {'activity': mermaid, 'state': mermaid}."""
    taken: dict[str, str] = {}
    sid = {s.id: mangle(s.id, taken) for s in doc.flat}
    gid = {s.group: mangle(s.group, taken) for s in doc.flat if s.group}

    edges = pm.build_edges(doc)
    reduced = pm.transitive_reduction(edges)
    feedback = [e for e in edges if e.feedback]
    ext_out = pm.external_outputs(doc)
    by_id = {s.id: s for s in doc.flat}

    lines: list[str] = ["stateDiagram-v2"]
    lines.append(f"  %% protocol: {doc.name} — derived from the canonical model")

    def declare(steps: list[pm.Step], indent: str) -> None:
        for step in steps:
            if step.children:
                lines.append(f'{indent}state "{step.title}" as {sid[step.id]} {{')
                # children with no reduced edge arriving from a sibling
                sibling_ids = {c.id for c in step.children}
                internal_entries = [
                    c
                    for c in step.children
                    if not any(
                        e.dst == c.id and e.src in sibling_ids for e in reduced
                    )
                ]
                declare(step.children, indent + "  ")
                for child in internal_entries:
                    lines.append(f"{indent}  [*] --> {sid[child.id]}")
                lines.append(f"{indent}}}")
            else:
                lines.append(f'{indent}state "{step.title}" as {sid[step.id]}')
                if step.applies:
                    label = "skill" if len(step.applies) == 1 else "skills"
                    lines.append(
                        f"{indent}note right of {sid[step.id]} : "
                        f"applies {label} {', '.join(step.applies)}"
                    )
            if step.group:
                lines.append(f"{indent}state {gid[step.group]} <<choice>>")

    declare(doc.steps, "  ")

    # Fork/join synthesis: a fork where the reduced graph fans out of a step
    # through plain edges; a join where plain edges fan in from sources that
    # are not mutually exclusive (exclusive sources are a simple merge and
    # need no pseudostate).
    tags = pm.branch_tags(doc, edges)
    plain_out: dict[str, list[pm.Edge]] = {}
    plain_in: dict[str, list[pm.Edge]] = {}
    for edge in reduced:
        if edge.option is None:
            plain_out.setdefault(edge.src, []).append(edge)
            plain_in.setdefault(edge.dst, []).append(edge)
    forks = {s for s, outs in plain_out.items() if len(outs) > 1}
    joins = set()
    for dst, ins in plain_in.items():
        if len(ins) < 2:
            continue
        sources = [e.src for e in ins]
        exclusive = all(
            pm.mutually_exclusive(tags[a], tags[b])
            for i, a in enumerate(sources)
            for b in sources[i + 1 :]
        )
        if not exclusive:
            joins.add(dst)
    fork_id = {s: mangle(f"{s}-fork", taken) for s in sorted(forks, key=lambda s: by_id[s].order)}
    join_id = {s: mangle(f"{s}-join", taken) for s in sorted(joins, key=lambda s: by_id[s].order)}
    for s, fid in fork_id.items():
        lines.append(f"  state {fid} <<fork>>")
    for s, jid in join_id.items():
        lines.append(f"  state {jid} <<join>>")

    def src_of(edge: pm.Edge) -> str:
        return fork_id.get(edge.src, sid[edge.src])

    def dst_of(edge: pm.Edge) -> str:
        return join_id.get(edge.dst, sid[edge.dst])

    entries = pm.entry_steps(doc)
    if len(entries) == 1:
        label = "requires " + ", ".join(doc.pre_required)
        if doc.pre_optional:
            label += " — optionally " + ", ".join(doc.pre_optional)
        lines.append(f"  [*] --> {sid[entries[0].id]} : {label}")
    else:
        pre_names = set(doc.pre_required)
        for entry in entries:
            externals = []
            for need in entry.needs:
                for ref in need.refs():
                    if ref in pre_names and ref not in externals:
                        externals.append(ref)
            label = "requires " + ", ".join(externals) if externals else "start"
            lines.append(f"  [*] --> {sid[entry.id]} : {label}")

    for step in doc.flat:
        if step.id in forks:
            lines.append(f"  {sid[step.id]} --> {fork_id[step.id]}")
        for edge in reduced:
            if edge.src == step.id and edge.option is None:
                lines.append(
                    f"  {src_of(edge)} --> {dst_of(edge)} : "
                    + ", ".join(edge.products)
                )
        if step.group:
            lines.append(f"  {sid[step.id]} --> {gid[step.group]}")
            for option in step.options:
                when = one_line(option.when)
                for edge in reduced:
                    if (
                        edge.src == step.id
                        and edge.option == (step.group, option.id)
                    ):
                        lines.append(
                            f"  {gid[step.group]} --> {dst_of(edge)} : {when}"
                        )
                produced = [n for n in option.yields if n in ext_out]
                if produced:
                    lines.append(
                        f"  {gid[step.group]} --> [*] : {when} — produces "
                        + ", ".join(produced)
                    )
        produced = [n for n in step.yields if n in ext_out]
        if produced:
            lines.append(
                f"  {sid[step.id]} --> [*] : produces " + ", ".join(produced)
            )
    for step_id, jid in join_id.items():
        lines.append(f"  {jid} --> {sid[step_id]}")

    for edge in sorted(
        feedback, key=lambda e: (by_id[e.src].order, by_id[e.dst].order)
    ):
        label = one_line(edge.when) if edge.when else ", ".join(edge.products)
        lines.append(f"  {sid[edge.src]} --> {sid[edge.dst]} : {label}")

    activity = "\n".join(lines)

    state_lines = list(lines)
    state_lines.append("  %% status: baseline — no run in progress")
    for cls in STATE_CLASSES:
        state_lines.append(f"  {cls}")
    for step in doc.flat:
        state_lines.append(f"  class {sid[step.id]} pending")
    state = "\n".join(state_lines)

    return {"activity": activity, "state": state}


def view_file(doc: pm.Document, kind: str, mermaid: str, rel_dir: str) -> str:
    title = {"activity": "activity view", "state": "state view"}[kind]
    return (
        BANNER.format(dir=rel_dir)
        + f"\n\n# {doc.name} — {title}\n\n```mermaid\n{mermaid}\n```\n"
    )


def run(directory: Path, check: bool) -> list[str]:
    problems: list[str] = []
    path = directory / "PROTOCOL.md"
    doc, errors, _ = pm.load(path)
    if errors:
        return [f"{path}: not valid; projection requires a valid model"] + [
            f"  {e}" for e in errors
        ]
    views_a = project(doc)
    views_b = project(doc)
    if views_a != views_b:
        problems.append(f"{path}: projection is not deterministic")
    try:
        rel_dir = directory.resolve().relative_to(pm.REPO_ROOT)
    except ValueError:
        rel_dir = directory
    views_dir = directory / "views"
    for kind, mermaid in views_a.items():
        content = view_file(doc, kind, mermaid, str(rel_dir))
        target = views_dir / f"{kind}.md"
        if check:
            on_disk = target.read_text(encoding="utf-8") if target.exists() else None
            if on_disk != content:
                problems.append(
                    f"{target}: committed view differs from regeneration "
                    "(views derive; edit the canonical model and regenerate)"
                )
            else:
                print(f"OK   {target}")
        else:
            views_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print(f"wrote {target}")
    return problems


def main(argv: list[str]) -> int:
    check = "--check" in argv
    dirs = [Path(a) for a in argv if a != "--check"]
    if not dirs:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    problems: list[str] = []
    for directory in dirs:
        problems.extend(run(directory, check))
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
