<!-- DERIVED VIEW — do not edit. Generated from ../PROTOCOL.md by tools/project.py; regenerate with: .venv/bin/python tools/project.py examples/review -->

# review — activity view

```mermaid
stateDiagram-v2
  %% protocol: review — derived from the canonical model
  state "Resolve the reviewed version" as resolve_reviewed_version
  note right of resolve_reviewed_version : applies skill orient
  state "Inspect against the contract" as inspect_against_contract
  note right of inspect_against_contract : applies skill code-review
  state "Classify findings" as classify_findings
  state "Emit exactly one disposition" as emit_disposition
  state review_disposition <<choice>>
  [*] --> resolve_reviewed_version : requires change-proposal, behavior-contract — optionally work-unit, implementation-plan, completion-evidence
  resolve_reviewed_version --> inspect_against_contract : reviewed-version
  inspect_against_contract --> classify_findings : findings
  classify_findings --> emit_disposition : classified-findings
  emit_disposition --> review_disposition
  review_disposition --> [*] : No blocking findings remain. — produces change-approved
  review_disposition --> [*] : At least one blocking finding remains. — produces change-needs-revision
```
