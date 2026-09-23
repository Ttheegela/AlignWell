"""
Safety / verification stub for AlignWell triage state.

Pure Python — no LangGraph import required. Callers can wire
`verify_triage` as a node later (see UPGRADE_V1.md).
"""

from __future__ import annotations

from typing import Any

# Keys treated as obvious PHI for redaction in this stub.
_PHI_KEYS = frozenset({"name", "ssn", "mrn"})


def verify_triage(state: dict) -> dict:
    """
    Verify a triage state dict and return a shallow merge with `verification`.

    Rules (stub, not clinical CDS):
      - Strip/redact obvious PHI keys (name, ssn, mrn) → phi_redacted=True
      - esi_level must be in 1..5 else safe=False, block_reason="invalid_esi"
      - ESI 1 or 2 requires escalation=True else safe=False
    """
    if not isinstance(state, dict):
        raise TypeError("state must be a dict")

    out: dict[str, Any] = dict(state)
    phi_redacted = False

    for key in list(out.keys()):
        if key.lower() in _PHI_KEYS:
            out.pop(key, None)
            phi_redacted = True

    # Also redact nested patient-ish dicts when present
    patient = out.get("patient")
    if isinstance(patient, dict):
        cleaned = dict(patient)
        for key in list(cleaned.keys()):
            if key.lower() in _PHI_KEYS:
                cleaned.pop(key, None)
                phi_redacted = True
        out["patient"] = cleaned

    safe = True
    block_reason: str | None = None

    raw_esi = out.get("esi_level")
    try:
        esi = int(raw_esi) if raw_esi is not None else None
    except (TypeError, ValueError):
        esi = None

    if esi is None or esi not in (1, 2, 3, 4, 5):
        safe = False
        block_reason = "invalid_esi"
    elif esi in (1, 2):
        escalation = out.get("escalation")
        if escalation is not True:
            safe = False
            block_reason = "esi_1_2_requires_escalation"

    out["verification"] = {
        "safe": safe,
        "block_reason": block_reason,
        "phi_redacted": phi_redacted,
    }
    return out


__all__ = ["verify_triage"]
