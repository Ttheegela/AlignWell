"""Safety / verification node stub for AlignWell triage graph.

Pure Python — no LangGraph import required. Wire into graph/workflow.py later.
"""
from __future__ import annotations

PHI_KEYS = ("name", "ssn", "mrn", "date_of_birth", "phone", "email", "address")


def verify_triage(state: dict) -> dict:
    """Validate ESI + escalation; redact obvious PHI keys; return verification block."""
    out = dict(state or {})
    phi_redacted = False
    for key in list(out.keys()):
        if key.lower() in PHI_KEYS or key.lower().endswith("_name"):
            out.pop(key, None)
            phi_redacted = True

    esi = out.get("esi_level")
    safe = True
    block_reason = None
    try:
        esi_i = int(esi)
    except (TypeError, ValueError):
        esi_i = None
    if esi_i is None or esi_i not in (1, 2, 3, 4, 5):
        safe = False
        block_reason = "invalid_esi"
    elif esi_i in (1, 2) and not out.get("escalation"):
        safe = False
        block_reason = "esi_1_2_requires_escalation"

    out["verification"] = {
        "safe": safe,
        "block_reason": block_reason,
        "phi_redacted": phi_redacted,
        "esi_level": esi_i,
    }
    out["safe"] = safe
    return out
