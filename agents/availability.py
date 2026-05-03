"""
AvailabilityAgent — queries Epic FHIR for open slots appropriate to ESI level.

Maps ESI level to specialty priority and retrieves candidate slots:
  ESI 1-2 → Emergency Medicine (escalation path handles, this agent is bypassed)
  ESI 3   → Internal Medicine / specialty based on complaint
  ESI 4-5 → Family Medicine / primary care
"""

from __future__ import annotations

from models.fhir_types import ESILevel, FHIRSlot
from models.state import TriageState
from tools.fhir_client import fhir_client

_ESI_SPECIALTY_MAP = {
    ESILevel.URGENT: "Internal Medicine",
    ESILevel.LESS_URGENT: "Family Medicine",
    ESILevel.NON_URGENT: "Family Medicine",
}


async def availability_agent(state: TriageState) -> dict:
    """
    Fetch open slots from Epic FHIR matching the patient's ESI level.

    Reads: esi_level
    Writes: candidate_slots
    """
    esi = state.get("esi_level") or ESILevel.URGENT
    specialty = _ESI_SPECIALTY_MAP.get(esi, "Internal Medicine")

    slots: list[FHIRSlot] = await fhir_client.get_available_slots(specialty=specialty)
    # Return up to 3 candidates for the scheduler to choose from
    return {"candidate_slots": slots[:3]}
