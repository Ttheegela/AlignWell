"""
AlignWell LangGraph triage workflow.

Graph topology:

  intake → triage → [escalation | availability → scheduler] → notification → END

Conditional edge after triage:
  ESI 1 or 2 → escalation node (immediate alert, skip scheduling)
  ESI 3-5    → availability → scheduler → notification
"""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from agents.availability import availability_agent
from agents.intake import intake_agent
from agents.notification import notification_agent
from agents.scheduler import scheduler_agent
from agents.triage import triage_agent
from models.fhir_types import ESILevel
from models.state import TriageState


# ---------------------------------------------------------------------------
# Escalation node — ESI 1 / 2 path
# ---------------------------------------------------------------------------


async def escalation_node(state: TriageState) -> dict:
    """
    Immediate escalation path for ESI 1 and 2 patients.

    In production: pages on-call physician via Epic notification API,
    triggers real-time bed management alert, or calls nurse station webhook.
    """
    patient = state["patient"]
    esi = state.get("esi_level")

    alert_message = (
        f"IMMEDIATE ESCALATION — {patient.display_name} | "
        f"ESI {esi.value if esi else '?'} ({esi.name if esi else 'Unknown'}) | "
        f"Chief complaint: {state.get('chief_complaint', 'N/A')} | "
        f"Flags: {', '.join(state.get('vital_flags', [])) or 'none'} | "
        f"Action required: clinical staff must attend immediately."
    )

    # In production: POST to Epic notification endpoint / paging system here
    print(f"[ESCALATION ALERT] {alert_message}")

    return {
        "scheduler_action": "escalated",
        "appointment": None,
        "messages": [AIMessage(content=alert_message)],
    }


# ---------------------------------------------------------------------------
# Routing function
# ---------------------------------------------------------------------------


def route_after_triage(state: TriageState) -> str:
    """
    Conditional edge: route ESI 1/2 to escalation, ESI 3-5 to scheduling.
    """
    if state.get("requires_escalation"):
        return "escalation"
    return "availability"


def route_after_escalation(state: TriageState) -> str:
    """Escalated patients still get a notification (for audit + messaging)."""
    return "notification"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """
    Construct and compile the AlignWell triage StateGraph.

    Returns a compiled LangGraph app ready for .ainvoke().
    """
    graph = StateGraph(TriageState)

    # Nodes
    graph.add_node("intake", intake_agent)
    graph.add_node("triage", triage_agent)
    graph.add_node("escalation", escalation_node)
    graph.add_node("availability", availability_agent)
    graph.add_node("scheduler", scheduler_agent)
    graph.add_node("notification", notification_agent)

    # Edges
    graph.set_entry_point("intake")
    graph.add_edge("intake", "triage")

    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"escalation": "escalation", "availability": "availability"},
    )

    graph.add_edge("escalation", "notification")
    graph.add_edge("availability", "scheduler")
    graph.add_edge("scheduler", "notification")
    graph.add_edge("notification", END)

    return graph.compile()


# Singleton compiled graph
triage_graph = build_graph()
