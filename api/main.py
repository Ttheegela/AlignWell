"""
AlignWell FastAPI application.

Endpoints:
  POST /triage          — run full triage workflow for a patient
  GET  /triage/{id}     — fetch audit record by ID
  GET  /health          — health check
  GET  /demo            — run a demo triage with pre-seeded patient data
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph.workflow import triage_graph
from models.fhir_types import FHIRCondition, FHIRPatient
from models.state import TriageState
from tools.audit_log import init_db
from tools.fhir_client import fhir_client


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup."""
    await init_db()
    yield


app = FastAPI(
    title="AlignWell — Multi-Agent Clinical Triage Engine",
    description=(
        "LangGraph-orchestrated triage system with FHIR R4 (Epic) integration. "
        "Classifies patient urgency using the ESI 5-level clinical scale and "
        "automates slot assignment or waitlisting."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TriageRequest(BaseModel):
    patient_id: str
    condition_id: str


class TriageResponse(BaseModel):
    patient_name: str
    esi_level: int | None
    esi_name: str | None
    triage_reasoning: str
    scheduler_action: str
    appointment_id: str | None
    appointment_start: str | None
    requires_escalation: bool
    patient_message: str
    provider_message: str


class DemoRequest(BaseModel):
    scenario: int = 1  # 1=cardiac (ESI2), 2=knee pain (ESI4), 3=fever (ESI4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "service": "alignwell-triage"}


@app.post("/triage", response_model=TriageResponse)
async def run_triage(req: TriageRequest):
    """
    Run the full AlignWell triage workflow for a patient.

    Fetches Patient + Condition from Epic FHIR, runs the LangGraph
    multi-agent pipeline, and returns the triage outcome.
    """
    patient: FHIRPatient = await fhir_client.get_patient(req.patient_id)
    condition: FHIRCondition = await fhir_client.get_condition(req.condition_id)

    initial_state: TriageState = {
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

    result: TriageState = await triage_graph.ainvoke(initial_state)

    appt = result.get("appointment")
    esi = result.get("esi_level")

    return TriageResponse(
        patient_name=patient.display_name,
        esi_level=esi.value if esi else None,
        esi_name=esi.name if esi else None,
        triage_reasoning=result.get("triage_reasoning", ""),
        scheduler_action=result.get("scheduler_action", ""),
        appointment_id=appt.id if appt else None,
        appointment_start=appt.start.isoformat() if appt and appt.start else None,
        requires_escalation=result.get("requires_escalation", False),
        patient_message=result.get("patient_message", ""),
        provider_message=result.get("provider_message", ""),
    )


@app.post("/demo", response_model=TriageResponse)
async def run_demo(req: DemoRequest):
    """
    Run a demo triage using pre-seeded patient/condition pairs.

    Scenario 1 — Chest pain (expect ESI 2, escalation)
    Scenario 2 — Knee pain (expect ESI 4, booked)
    Scenario 3 — Fever (expect ESI 4-5, booked or waitlisted)
    """
    scenario_map = {1: ("pt-001", "cond-001"), 2: ("pt-002", "cond-002"), 3: ("pt-003", "cond-003")}
    patient_id, condition_id = scenario_map.get(req.scenario, ("pt-001", "cond-001"))
    return await run_triage(TriageRequest(patient_id=patient_id, condition_id=condition_id))
