# AlignWell — Multi-Agent Clinical Triage Engine

> LangGraph-orchestrated patient triage system with FHIR R4 / Epic integration.
> Classifies urgency using the ESI 5-level clinical scale and automates slot assignment.

---

## Architecture

```
Patient Request (FHIR R4)
        │
        ▼
   ┌─────────┐
   │ Intake  │  → Parse FHIR Patient + Condition → chief complaint + vital flags
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Triage  │  → RAG against ESI guidelines (Qdrant) → ESI level 1–5
   └────┬────┘
        │
   ┌────┴──────────────────────┐
   │ ESI 1/2?                  │ ESI 3/4/5?
   ▼                           ▼
┌──────────┐          ┌──────────────┐
│Escalation│          │ Availability │ → Query Epic FHIR Slot resources
└────┬─────┘          └──────┬───────┘
     │                       │
     │                  ┌────▼──────┐
     │                  │ Scheduler │ → Book slot or waitlist
     │                  └────┬──────┘
     │                       │
     └──────────┬────────────┘
                │
           ┌────▼────────┐
           │Notification │ → Patient msg + Provider handoff + PostgreSQL audit
           └─────────────┘
```

## Stack

| Layer | Tool |
|-------|------|
| Agent orchestration | LangGraph (StateGraph) |
| LLM | Claude 3 Haiku (Anthropic API) |
| Clinical RAG | Qdrant + fastembed |
| EHR integration | FHIR R4 (Epic-compatible) |
| API | FastAPI + Pydantic v2 |
| Audit DB | PostgreSQL |
| Observability | LangSmith |
| Deploy | Docker Compose → Railway |

## Quick Start

```bash
# 1. Clone and set up env
cp .env.example .env
# Add your ANTHROPIC_API_KEY and LANGCHAIN_API_KEY

# 2. Start all services
docker compose up

# 3. Run a demo triage (scenario 1 = chest pain, scenario 2 = knee pain)
curl -X POST http://localhost:8000/demo -H "Content-Type: application/json" \
     -d '{"scenario": 1}'

# 4. API docs
open http://localhost:8000/docs
```

## Demo Scenarios

| Scenario | Patient | Complaint | Expected ESI | Action |
|----------|---------|-----------|-------------|--------|
| 1 | Anika Patel | Chest pain + diaphoresis | ESI 2 (Emergent) | Escalated |
| 2 | Carlos Rodriguez | Chronic knee pain | ESI 4 (Less Urgent) | Booked |
| 3 | Wei Chen | Fever 38.9°C | ESI 4-5 | Booked |

## Epic FHIR Integration

AlignWell uses FHIR R4 resource models throughout. To connect to a real Epic instance:

1. Register your app in the [Epic App Orchard](https://appmarket.epic.com)
2. Get your OAuth 2.0 client credentials
3. Set `EPIC_FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` in `.env`
4. Implement the real HTTP calls in `tools/fhir_client.py` — all method signatures are already defined

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## ESI Triage Scale

| Level | Name | Description | AlignWell Action |
|-------|------|-------------|-----------------|
| 1 | Immediate | Life-threatening | Escalate immediately |
| 2 | Emergent | High-risk, severe pain | Escalate immediately |
| 3 | Urgent | Stable, needs resources | Book specialist |
| 4 | Less Urgent | Stable, one resource | Book primary care |
| 5 | Non-Urgent | No resources needed | Book or waitlist |
