"""
Simulated Epic FHIR R4 client.

In production: swap EPIC_FHIR_BASE_URL for the real Epic sandbox or
production FHIR endpoint. All method signatures remain identical —
only the HTTP calls hit real infrastructure.

Epic FHIR sandbox: https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
"""

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta

from models.fhir_types import (
    CodeableConcept,
    Coding,
    FHIRCondition,
    FHIRPatient,
    FHIRSlot,
    Gender,
    HumanName,
)

# ---------------------------------------------------------------------------
# Demo seed data — realistic FHIR-shaped records
# ---------------------------------------------------------------------------

_DEMO_PATIENTS: list[FHIRPatient] = [
    FHIRPatient(
        id="pt-001",
        name=[HumanName(family="Patel", given=["Anika"])],
        gender=Gender.FEMALE,
        birthDate="1985-03-22",
    ),
    FHIRPatient(
        id="pt-002",
        name=[HumanName(family="Rodriguez", given=["Carlos", "M"])],
        gender=Gender.MALE,
        birthDate="1972-11-05",
    ),
    FHIRPatient(
        id="pt-003",
        name=[HumanName(family="Chen", given=["Wei"])],
        gender=Gender.MALE,
        birthDate="1998-07-14",
    ),
]

_DEMO_CONDITIONS: list[FHIRCondition] = [
    FHIRCondition(
        id="cond-001",
        subject_id="pt-001",
        code=CodeableConcept(
            coding=[Coding(system="http://snomed.info/sct", code="73595000", display="Stress")],
            text="Severe chest pain radiating to left arm, onset 30 minutes ago",
        ),
        severity=CodeableConcept(text="severe"),
        note="Patient reports diaphoresis and shortness of breath.",
    ),
    FHIRCondition(
        id="cond-002",
        subject_id="pt-002",
        code=CodeableConcept(
            coding=[Coding(system="http://snomed.info/sct", code="57676002", display="Joint pain")],
            text="Chronic knee pain, difficulty walking, requesting follow-up",
        ),
        severity=CodeableConcept(text="moderate"),
        note="No acute distress. Existing diagnosis of osteoarthritis.",
    ),
    FHIRCondition(
        id="cond-003",
        subject_id="pt-003",
        code=CodeableConcept(
            coding=[Coding(system="http://snomed.info/sct", code="386661006", display="Fever")],
            text="Fever 38.9°C, sore throat, mild fatigue for 2 days",
        ),
        severity=CodeableConcept(text="mild"),
        note="No respiratory distress. No known exposures.",
    ),
]

_SPECIALTIES = ["Emergency Medicine", "Cardiology", "Orthopedics", "Internal Medicine", "Family Medicine"]


def _generate_slots(n: int = 6) -> list[FHIRSlot]:
    """Generate realistic open appointment slots for the next 48 hours."""
    slots = []
    base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for i in range(n):
        start = base + timedelta(hours=i * 4 + 1)
        slots.append(
            FHIRSlot(
                id=f"slot-{uuid.uuid4().hex[:6]}",
                schedule_id=f"sched-{i % 3 + 1}",
                status="free",
                start=start,
                end=start + timedelta(minutes=30),
                specialty=CodeableConcept(text=_SPECIALTIES[i % len(_SPECIALTIES)]),
            )
        )
    return slots


# ---------------------------------------------------------------------------
# FHIR client (simulated — drop-in replaceable with real Epic calls)
# ---------------------------------------------------------------------------


class FHIRClient:
    """
    Wraps Epic FHIR R4 API calls.

    All methods are async-ready. In demo mode (EPIC_FHIR_BASE_URL not set
    to a real endpoint), responses are generated from local seed data.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("EPIC_FHIR_BASE_URL", "demo")
        self._demo_mode = self.base_url == "demo"

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        """Fetch Patient resource by ID from Epic FHIR R4."""
        if self._demo_mode:
            match = next((p for p in _DEMO_PATIENTS if p.id == patient_id), None)
            return match or _DEMO_PATIENTS[0]
        # Production: GET {base_url}/Patient/{patient_id}
        raise NotImplementedError("Real Epic FHIR call not yet wired")

    async def get_condition(self, condition_id: str) -> FHIRCondition:
        """Fetch Condition resource by ID from Epic FHIR R4."""
        if self._demo_mode:
            match = next((c for c in _DEMO_CONDITIONS if c.id == condition_id), None)
            return match or _DEMO_CONDITIONS[0]
        raise NotImplementedError("Real Epic FHIR call not yet wired")

    async def get_available_slots(self, specialty: str | None = None) -> list[FHIRSlot]:
        """Fetch open Slot resources from Epic FHIR R4 Schedule."""
        if self._demo_mode:
            slots = _generate_slots()
            if specialty:
                slots = [s for s in slots if specialty.lower() in (s.specialty.text or "").lower()] or slots
            return slots
        raise NotImplementedError("Real Epic FHIR call not yet wired")

    async def book_slot(self, slot_id: str, patient_id: str) -> bool:
        """Mark a Slot as busy and create an Appointment in Epic FHIR R4."""
        if self._demo_mode:
            return True  # Simulated success
        raise NotImplementedError("Real Epic FHIR call not yet wired")


# Singleton for import
fhir_client = FHIRClient()
