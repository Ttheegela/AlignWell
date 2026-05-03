"""
NotificationAgent — final node in the graph.

Generates:
1. Patient-facing message (plain language confirmation or waitlist notice)
2. Provider-facing handoff summary (clinical, structured)
3. Writes the full audit record to PostgreSQL
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from models.fhir_types import AppointmentStatus, ESILevel
from models.state import TriageState
from tools.audit_log import log_triage_outcome

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.2)

_PATIENT_SYSTEM = """You are a patient communication specialist at a hospital.
Write a clear, compassionate, non-clinical message for the patient.
Keep it under 100 words. No medical jargon."""

_PROVIDER_SYSTEM = """You are a clinical handoff documentation agent.
Write a concise provider-facing triage summary. Include: ESI level, chief complaint,
key flags, and next action. Clinical language. Under 80 words."""


async def notification_agent(state: TriageState) -> dict:
    """
    Generate patient + provider messages and persist audit record.

    Reads: appointment, scheduler_action, esi_level, chief_complaint, patient
    Writes: patient_message, provider_message
    """
    appt = state.get("appointment")
    patient = state["patient"]
    esi = state.get("esi_level")
    action = state.get("scheduler_action", "unknown")

    # --- Patient message ---
    if appt and appt.status == AppointmentStatus.BOOKED:
        patient_ctx = (
            f"Patient {patient.display_name} has been booked for an appointment "
            f"on {appt.start.strftime('%A %B %d at %I:%M %p') if appt.start else 'TBD'}. "
            f"Reason: {state.get('chief_complaint', '')}."
        )
        patient_action = "booked"
    elif action == "escalated":
        patient_ctx = (
            f"Patient {patient.display_name} has been flagged as high-priority (ESI {esi.value if esi else '?'}). "
            f"Clinical staff have been alerted immediately."
        )
        patient_action = "escalated"
    else:
        patient_ctx = (
            f"Patient {patient.display_name} has been added to the waitlist. "
            f"Reason: {state.get('chief_complaint', '')}. We will contact you when a slot opens."
        )
        patient_action = "waitlisted"

    patient_resp = await _llm.ainvoke(
        [SystemMessage(content=_PATIENT_SYSTEM), HumanMessage(content=patient_ctx)]
    )

    # --- Provider message ---
    provider_ctx = (
        f"Patient: {patient.display_name} | ESI: {esi.value if esi else 'N/A'} ({esi.name if esi else 'Unknown'}) | "
        f"Chief complaint: {state.get('chief_complaint', 'N/A')} | "
        f"Flags: {', '.join(state.get('vital_flags', [])) or 'none'} | "
        f"Action: {action} | Appointment ID: {appt.id if appt else 'N/A'}"
    )

    provider_resp = await _llm.ainvoke(
        [SystemMessage(content=_PROVIDER_SYSTEM), HumanMessage(content=provider_ctx)]
    )

    # --- Audit log ---
    condition = state.get("condition")
    await log_triage_outcome(
        patient_id=patient.id,
        condition_id=condition.id if condition else "unknown",
        chief_complaint=state.get("chief_complaint", ""),
        esi_level=esi,
        triage_reasoning=state.get("triage_reasoning", ""),
        scheduler_action=action,
        slot_id=appt.slot_id if appt else None,
        appointment_id=appt.id if appt else None,
        requires_escalation=state.get("requires_escalation", False),
        error=state.get("error"),
    )

    return {
        "patient_message": patient_resp.content,
        "provider_message": provider_resp.content,
        "messages": [patient_resp, provider_resp],
    }
