#!/usr/bin/env bash
# Convergence harness for the Agent Protocols repository.
#
# Runs the mechanical convergence checks: example validation, view
# derivation, Mermaid render pre-check, relative-link resolution, the
# runtime-agnosticism sweep of the standard core, and the single-home
# version check. The Mermaid pre-check renders via kroki.io; the
# authoritative render check for the standard is GitHub's own renderer,
# inspected after push.
set -u
cd "$(dirname "$0")/.."

PY=.venv/bin/python
fail=0

note() { printf '\n== %s ==\n' "$1"; }

note "examples validate (schema + V1-V12)"
$PY tools/validate.py examples/review/PROTOCOL.md examples/verify/PROTOCOL.md || fail=1

note "views derive (regenerate + compare, determinism)"
$PY tools/project.py --check examples/review examples/verify || fail=1

note "mermaid blocks render (kroki.io pre-check)"
$PY - <<'EOF' || fail=1
import pathlib, re, sys, urllib.request

blocks = []
for path in sorted(pathlib.Path(".").rglob("*.md")):
    if ".venv" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    for i, block in enumerate(re.findall(r"```mermaid\n(.*?)```", text, re.S)):
        blocks.append((f"{path}#{i + 1}", block))
bad = 0
for name, block in blocks:
    req = urllib.request.Request(
        "https://kroki.io/mermaid/svg",
        data=block.encode("utf-8"),
        headers={
            "Content-Type": "text/plain",
            "User-Agent": "agent-protocols-check/0.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read(200)
            ok = resp.status == 200 and b"<svg" in body
    except Exception as exc:
        print(f"RENDER FAIL {name}: {exc}")
        bad += 1
        continue
    print(("RENDER OK   " if ok else "RENDER FAIL ") + name)
    bad += 0 if ok else 1
print(f"{len(blocks) - bad}/{len(blocks)} mermaid blocks rendered")
sys.exit(1 if bad else 0)
EOF

note "relative links resolve (files and anchors)"
$PY - <<'EOF' || fail=1
import pathlib, re, sys

def anchors(text):
    out = set()
    for heading in re.findall(r"^#{1,6} +(.+?)\s*$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).strip().replace(" ", "-")
        out.add(slug)
    return out

docs = {}
for path in sorted(pathlib.Path(".").rglob("*.md")):
    if ".venv" in path.parts:
        continue
    docs[path] = path.read_text(encoding="utf-8")

bad = 0
for path, text in docs.items():
    for label, target in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        ref, _, anchor = target.partition("#")
        dest = (path.parent / ref).resolve() if ref else path.resolve()
        if not dest.exists():
            print(f"LINK FAIL {path}: ({target}) — no such file")
            bad += 1
            continue
        if anchor and dest.suffix == ".md":
            dest_text = dest.read_text(encoding="utf-8")
            if anchor not in anchors(dest_text):
                print(f"LINK FAIL {path}: ({target}) — no such anchor")
                bad += 1
print(f"link sweep: {bad} failures")
sys.exit(1 if bad else 0)
EOF

note "standard core is runtime-agnostic"
hits=$(grep -niE 'runa|groundwork|tesserine|manifest' spec/*.md | grep -v 'bindings/tesserine\.md' || true)
if [ -n "$hits" ]; then
  echo "unmarked reference-implementation mentions in spec/:"
  echo "$hits"
  fail=1
else
  echo "spec/ clean (reference-implementation mentions only via bindings/ links)"
fi

note "version has a single home (CHANGELOG.md)"
hits=$(grep -rn --include='*.md' '0\.1\.0' . | grep -v '^\./CHANGELOG.md' | grep -v '\.venv' | grep -v '0\.3\.0' || true)
if [ -n "$hits" ]; then
  echo "version strings outside CHANGELOG.md:"
  echo "$hits"
  fail=1
else
  echo "version stated only in CHANGELOG.md"
fi

if [ "$fail" -eq 0 ]; then
  printf '\nALL CHECKS PASSED\n'
else
  printf '\nCHECKS FAILED\n'
fi
exit $fail
