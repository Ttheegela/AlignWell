# AlignWell Upgrade Scaffold (v1)

Honest inventory of what landed on branch `upgrade/v1-scaffold`.  
**Not production clinical decision support.** No fake metrics, no CDS Hooks / SMART / OpenFDA implementations yet.

## Landed

| Path | Status | Notes |
|------|--------|-------|
| `graph/safety_node.py` | Stub, importable | `verify_triage(state: dict) -> dict` — PHI key strip (`name`/`ssn`/`mrn`), ESI 1–5 check, ESI 1/2 requires `escalation=True`. Pure Python (no LangGraph import). |
| `tests/fixtures/esi_cases.json` | Offline fixtures | 7 cases aligned to README demos (chest pain ESI2, knee ESI4, fever ESI4, plus arrest/laceration/abdomen/SOB). |
| `evals/esi_harness.py` | Runnable offline | Loads fixtures; accepts callable `predict` or canned predictions dict; naive keyword demo predictor; writes `evals/out/last_score.json`. |
| `evals/out/` | Dir + `.gitkeep` | Score artifact written on harness run. |
| `README.md` | Updated | Short “Upgrade scaffold (v1)” section. |
| `graph/workflow.py` | Comment only | Optional call-site note for `verify_triage` — **not** wired into the StateGraph (avoids breaking `TriageState` / async agent contracts). |

## Intentionally not implemented

- CDS Hooks endpoints / cards
- SMART-on-FHIR launch / auth
- OpenFDA drug–interaction tool
- LangGraph node registration for `safety_node`
- Any claim of validated ESI model accuracy beyond the offline keyword demo

## How to run the offline eval

```bash
python evals/esi_harness.py
```

## Suggested next hooks (not in this PR)

1. Wire `verify_triage` after `triage` in `build_graph()` once state keys (`esi_level`, `escalation`/`requires_escalation`, PHI fields) are normalized.
2. CDS Hooks stub service under `api/` returning informational cards only.
3. SMART-on-FHIR app registration docs + token exchange stub.
4. OpenFDA label / interaction lookup behind `tools/` with hard rate limits and no PHI egress.

## Constraints honored

- No secrets committed
- No production CDS performance claims
- Stubs importable / harness runnable without API keys
