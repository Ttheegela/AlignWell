"""
TriageAgent — classifies patient urgency using the ESI 5-level scale.

Uses RAG against Qdrant-indexed ESI clinical guidelines to ground the
LLM's decision in real clinical criteria rather than free-form reasoning.

ESI 1 or 2 → sets requires_escalation = True → graph routes to escalation path.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from models.fhir_types import ESILevel
from models.state import TriageState
from tools.qdrant_search import qdrant_tool

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

_SYSTEM = """You are a clinical triage nurse agent using the Emergency Severity Index (ESI).

You will receive:
- A patient intake summary and chief complaint
- Relevant ESI clinical guidelines retrieved from a clinical knowledge base
- Any red-flag vital signs or symptoms

Your job: assign the correct ESI level (1–5) and explain your reasoning citing the guidelines.

Output format — respond with exactly this JSON:
{
  "esi_level": <integer 1-5>,
  "triage_reasoning": "<1-2 sentence clinical justification referencing the guidelines>"
}"""


async def triage_agent(state: TriageState) -> dict:
    """
    Classify ESI urgency level using RAG-grounded clinical reasoning.

    Reads: chief_complaint, intake_summary, vital_flags
    Writes: esi_level, triage_reasoning, matched_guidelines, requires_escalation
    """
    # Retrieve relevant ESI guidelines for the chief complaint
    query = f"{state['chief_complaint']} {' '.join(state['vital_flags'])}"
    guidelines = await qdrant_tool.search(query, top_k=2)
    guideline_text = "\n\n".join(g["text"] for g in guidelines)

    prompt = f"""Patient intake summary: {state['intake_summary']}
Chief complaint: {state['chief_complaint']}
Red-flag symptoms: {', '.join(state['vital_flags']) or 'none'}

Relevant ESI guidelines:
{guideline_text}"""

    response = await _llm.ainvoke(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]
    )

    import json, re
    try:
        raw = response.content.strip()
        # Strip markdown code fences if present: ```json ... ``` or ``` ... ```
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        esi = ESILevel(int(parsed["esi_level"]))
        reasoning = parsed.get("triage_reasoning", "")
    except Exception:
        esi = ESILevel.URGENT  # Safe default
        reasoning = "Could not parse triage response; defaulted to ESI 3 (Urgent)."

    return {
        "esi_level": esi,
        "triage_reasoning": reasoning,
        "matched_guidelines": [g["text"][:120] + "..." for g in guidelines],
        "requires_escalation": esi in (ESILevel.IMMEDIATE, ESILevel.EMERGENT),
        "messages": [response],
    }
