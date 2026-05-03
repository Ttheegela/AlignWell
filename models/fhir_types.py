"""
FHIR R4 Pydantic models for Epic integration.

Covers the subset of FHIR resources used by the triage workflow:
Patient, Condition, Encounter, Appointment, Slot.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ESILevel(int, Enum):
    """Emergency Severity Index — 5-level clinical triage scale (AHRQ standard)."""

    IMMEDIATE = 1       # Life-threatening; resuscitation required
    EMERGENT = 2        # High-risk situation; severe pain/distress
    URGENT = 3          # Stable but requires multiple resources
    LESS_URGENT = 4     # Stable; one resource needed
    NON_URGENT = 5      # Stable; no resources needed


class AppointmentStatus(str, Enum):
    PROPOSED = "proposed"
    BOOKED = "booked"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# FHIR sub-types
# ---------------------------------------------------------------------------


class Coding(BaseModel):
    system: str
    code: str
    display: str | None = None


class CodeableConcept(BaseModel):
    coding: list[Coding] = Field(default_factory=list)
    text: str | None = None


class HumanName(BaseModel):
    family: str
    given: list[str] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{' '.join(self.given)} {self.family}".strip()


class ContactPoint(BaseModel):
    system: str  # phone | email
    value: str
    use: str | None = None  # home | work | mobile


class Period(BaseModel):
    start: datetime | None = None
    end: datetime | None = None


# ---------------------------------------------------------------------------
# FHIR R4 Resources
# ---------------------------------------------------------------------------


class FHIRPatient(BaseModel):
    """FHIR R4 Patient resource (subset)."""

    resourceType: str = "Patient"
    id: str
    name: list[HumanName] = Field(default_factory=list)
    gender: Gender = Gender.UNKNOWN
    birthDate: str | None = None  # YYYY-MM-DD
    telecom: list[ContactPoint] = Field(default_factory=list)
    active: bool = True

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name[0].full_name
        return f"Patient/{self.id}"


class FHIRCondition(BaseModel):
    """FHIR R4 Condition resource — chief complaint or diagnosis."""

    resourceType: str = "Condition"
    id: str
    subject_id: str  # Reference to Patient.id
    code: CodeableConcept
    clinicalStatus: CodeableConcept | None = None
    severity: CodeableConcept | None = None
    onsetDateTime: datetime | None = None
    note: str | None = None  # Free-text clinical notes


class FHIRSlot(BaseModel):
    """FHIR R4 Slot — a bookable time window with a provider."""

    resourceType: str = "Slot"
    id: str
    schedule_id: str
    status: str  # free | busy | busy-unavailable
    start: datetime
    end: datetime
    specialty: CodeableConcept | None = None
    comment: str | None = None


class FHIRAppointment(BaseModel):
    """FHIR R4 Appointment — the result of a successful slot assignment."""

    resourceType: str = "Appointment"
    id: str
    status: AppointmentStatus
    patient_id: str
    slot_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    esi_level: ESILevel | None = None
    description: str | None = None
    created: datetime = Field(default_factory=datetime.utcnow)
