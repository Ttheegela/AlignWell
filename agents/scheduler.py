"""
SchedulerAgent — assigns the best available slot or places patient on waitlist.

Decision logic:
  - If candidate slots exist → book the earliest one
  - If no slots → waitlist the patient
  - If ESI 1/2 → this agent is bypassed (escalation path handles directly)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from models.fhir_types import AppointmentStatus, ESILevel, FHIRAppointment
from models.state import TriageState
from tools.fhir_client import fhir_client


async def scheduler_agent(state: TriageState) -> dict:
    """
    Book the earliest suitable slot or waitlist the patient.

    Reads: candidate_slots, patient, esi_level
    Writes: appointment, scheduler_action
    """
    slots = state.get("candidate_slots", [])
    patient = state["patient"]
    esi = state.get("esi_level") or ESILevel.URGENT

    if slots:
        # Pick earliest slot
        best = min(slots, key=lambda s: s.start)
        success = await fhir_client.book_slot(best.id, patient.id)

        if success:
            appointment = FHIRAppointment(
                id=f"appt-{uuid.uuid4().hex[:8]}",
                status=AppointmentStatus.BOOKED,
                patient_id=patient.id,
                slot_id=best.id,
                start=best.start,
                end=best.end,
                esi_level=esi,
                description=state.get("chief_complaint", ""),
            )
            return {"appointment": appointment, "scheduler_action": "booked"}

    # No slots available → waitlist
    appointment = FHIRAppointment(
        id=f"appt-{uuid.uuid4().hex[:8]}",
        status=AppointmentStatus.WAITLISTED,
        patient_id=patient.id,
        slot_id=None,
        esi_level=esi,
        description=state.get("chief_complaint", ""),
    )
    return {"appointment": appointment, "scheduler_action": "waitlisted"}
