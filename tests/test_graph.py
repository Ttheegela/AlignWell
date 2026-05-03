"""
End-to-end tests for the AlignWell triage graph.

Runs in demo mode (no live APIs required) against pre-seeded FHIR data.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from graph.workflow import triage_graph
from models.fhir_types import (
    CodeableConcept,
    Coding,
    ESILevel,
    FHIRCondition,
    FHIRPatient,
    Gender,
    HumanName,
)
from models.state import TriageState


def _make_state(condition_text: str, severity: str, notes: str) -> TriageState:
    patient = FHIRPatient(
        id="test-pt-01",
        name=[HumanName(family="Test", given=["Patient"])],
        gender=Gender.MALE,
        birthDate="1980-01-01",
    )
    condition = FHIRCondition(
        id="test-cond-01",
        subject_id="test-pt-01",
        code=CodeableConcept(
            coding=[Coding(system="http://snomed.info/sct", code="000000", display="Test")],
            text=condition_text,
        ),
        severity=CodeableConcept(text=severity),
        note=notes,
    )
    return {
        "patient": patient,
        "condition": condition,
        "intake_summary": "",
        "chief_complaint": "",
        "vital_flags": [],
        "esi_level": None,
        "triage_reasoning": "",
        "matched_guidelines": [],
        "candidate_slots": [],
        "appointment": None,
        "scheduler_action": "",
        "patient_message": "",
        "provider_message": "",
        "requires_escalation": False,
        "error": None,
        "messages": [],
    }


@pytest.mark.asyncio
async def test_low_urgency_patient_gets_booked():
    """ESI 4-5 patient (mild cold) should be booked, not escalated."""
    state = _make_state(
        condition_text="Runny nose and mild sore throat for 2 days",
        severity="mild",
        notes="No fever, no respiratory distress, vaccinated.",
    )
    result = await triage_graph.ainvoke(state)

    assert result["esi_level"] in (ESILevel.LESS_URGENT, ESILevel.NON_URGENT)
    assert result["requires_escalation"] is False
    assert result["scheduler_action"] in ("booked", "waitlisted")
    assert result["patient_message"]
    assert result["provider_message"]


@pytest.mark.asyncio
async def test_high_urgency_patient_is_escalated():
    """ESI 1-2 patient (chest pain + diaphoresis) should trigger escalation."""
    state = _make_state(
        condition_text="Severe chest pain radiating to left arm, onset 20 minutes ago",
        severity="severe",
        notes="Patient is diaphoretic and short of breath. BP 90/60.",
    )
    result = await triage_graph.ainvoke(state)

    assert result["esi_level"] in (ESILevel.IMMEDIATE, ESILevel.EMERGENT)
    assert result["requires_escalation"] is True
    assert result["scheduler_action"] == "escalated"


@pytest.mark.asyncio
async def test_intake_populates_chief_complaint():
    """Intake agent must extract a non-empty chief complaint."""
    state = _make_state(
        condition_text="Moderate abdominal pain, 6/10 scale, 3 hours",
        severity="moderate",
        notes="No rebound tenderness. Nausea present.",
    )
    result = await triage_graph.ainvoke(state)

    assert result["chief_complaint"]
    assert result["intake_summary"]
