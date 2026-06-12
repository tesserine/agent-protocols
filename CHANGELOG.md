# Changelog

All notable changes to the Agent Protocols standard are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This file is the single home of the standard's version; specification
documents carry a status, never a version number.

## [0.1.0] - 2026-06-12

Initial draft of the standard.

### Added

- Core specification: the contract spine, the canonical model and derived
  views, the two graphs, the authoring discipline, and conformance
  (`spec/specification.md`).
- Notation: the typed-edge vocabulary with its grounding in the workflow
  patterns literature and Harel statecharts, and the projection rules to
  Mermaid `stateDiagram-v2` (`spec/notation.md`).
- Canonical-model format: the markdown-yaml serialization, the body anchor
  grammar, and the validation rules (`spec/canonical-model.md`,
  `schemas/protocol.schema.json`).
- Tesserine binding: the mapping onto the `runa` runtime and the `groundwork`
  methodology, including the manifest-as-projection evolution path
  (`bindings/tesserine.md`).
- Worked examples: `review` and `verify`, re-expressed from the groundwork
  methodology, with derived activity and state views (`examples/`).
- Reference tooling: instance validation and view projection
  (`tools/validate.py`, `tools/project.py`, `tools/check.sh`).
- Design for the authoring/visualization TUI (`design/tui.md`).
- Repository README: the entry point routing readers, authors, and
  implementers into the standard, with a worked excerpt and its derived view
  (`README.md`).
