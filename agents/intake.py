"""
IntakeAgent — first node in the triage graph.

Receives raw FHIR Patient + Condition resources and produces:
- A structured plain-English intake summary
- Extracted chief complaint text
- A list of vital flags or red-flag symptoms detected in the condition notes
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from models.state import TriageState

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

_SYSTEM = """You are a clinical intake specialist agent in a hospital triage system.
Your job is to parse structured FHIR patient data and extract:
1. A concise intake summary (2-3 sentences)
2. The chief complaint (one sentence)
3. Any red-flag symptoms or vital concerns present in the notes (list of strings)

Be precise and clinical. Do not add information not present in the input.
Output format — respond with exactly this JSON structure:
{
  "intake_summary": "...",
  "chief_complaint": "...",
  "vital_flags": ["...", "..."]
}"""


async def intake_agent(state: TriageState) -> dict:
    """
    Parse FHIR Patient + Condition into structured intake fields.

    Reads: state.patient, state.condition
    Writes: intake_summary, chief_complaint, vital_flags
    """
    patient = state["patient"]
    condition = state["condition"]

    prompt = f"""Patient: {patient.display_name}, DOB: {patient.birthDate}, Gender: {patient.gender.value}
Chief complaint (FHIR Condition text): {condition.code.text}
Severity: {condition.severity.text if condition.severity else 'not specified'}
Clinical notes: {condition.note or 'none'}"""

    response = await _llm.ainvoke(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]
    )

    import json
    try:
        parsed = json.loads(response.content)
    except Exception:
        # Fallback: graceful degradation if LLM output is malformed
        parsed = {
            "intake_summary": condition.code.text or "No summary available",
            "chief_complaint": condition.code.text or "Unknown",
            "vital_flags": [],
        }

    return {
        "intake_summary": parsed.get("intake_summary", ""),
        "chief_complaint": parsed.get("chief_complaint", ""),
        "vital_flags": parsed.get("vital_flags", []),
        "messages": [response],
    }
