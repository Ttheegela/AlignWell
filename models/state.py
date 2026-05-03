"""
LangGraph TypedDict state shared across all agents in the triage workflow.

Every agent reads from and writes to this state. Fields are additive —
each agent enriches the state and passes it to the next node.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from models.fhir_types import (
    ESILevel,
    FHIRAppointment,
    FHIRCondition,
    FHIRPatient,
    FHIRSlot,
)


class TriageState(TypedDict):
    """Full state object flowing through the AlignWell triage graph."""

    # --- Input ---
    patient: FHIRPatient
    condition: FHIRCondition

    # --- Intake agent output ---
    intake_summary: str          # Structured plain-English intake summary
    chief_complaint: str         # Extracted chief complaint text
    vital_flags: list[str]       # Any flagged vitals or red-flag symptoms

    # --- Triage agent output ---
    esi_level: ESILevel | None   # Classified urgency level (1–5)
    triage_reasoning: str        # LLM chain-of-thought for the ESI decision
    matched_guidelines: list[str]  # RAG-retrieved ESI criteria that matched

    # --- Availability agent output ---
    candidate_slots: list[FHIRSlot]   # Open slots matching ESI-appropriate specialty

    # --- Scheduler agent output ---
    appointment: FHIRAppointment | None  # Final booked or waitlisted appointment
    scheduler_action: str               # "booked" | "waitlisted" | "escalated"

    # --- Notification agent output ---
    patient_message: str    # Patient-facing confirmation / waitlist notice
    provider_message: str   # Provider-facing handoff summary

    # --- Control flow ---
    requires_escalation: bool  # True if ESI 1 or 2 — triggers immediate alert path
    error: str | None          # Populated if any agent fails; triggers error handler

    # --- Audit ---
    messages: Annotated[list[Any], add_messages]  # LangGraph message history
