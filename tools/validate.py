#!/usr/bin/env python3
"""Validate canonical-model protocol documents.

Checks the parsed frontmatter against schemas/protocol.schema.json and the
structural rules V1-V12 of spec/canonical-model.md. Departures from SHOULD
guidance are reported as warnings and never fail validation.

Usage: validate.py PROTOCOL.md [PROTOCOL.md ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocol_model


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    failed = False
    for arg in argv:
        path = Path(arg)
        try:
            _, errors, warnings = protocol_model.load(path)
        except Exception as exc:  # parse failures are validation failures
            print(f"FAIL {path}: {exc}")
            failed = True
            continue
        for warning in warnings:
            print(f"warn {path}: {warning}")
        if errors:
            failed = True
            print(f"FAIL {path}")
            for error in errors:
                print(f"  {error}")
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
