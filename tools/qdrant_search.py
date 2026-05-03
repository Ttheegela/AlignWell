"""
Qdrant vector search tool for clinical guideline retrieval.

Indexes ESI triage criteria so the TriageAgent can RAG against
real clinical decision support content rather than hallucinating.
"""

from __future__ import annotations

import os
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION = "esi_guidelines"
VECTOR_SIZE = 384  # fastembed default (BAAI/bge-small-en-v1.5)

# ---------------------------------------------------------------------------
# ESI clinical guideline seed documents
# ---------------------------------------------------------------------------

_ESI_GUIDELINES = [
    {
        "id": 1,
        "esi": 1,
        "text": "ESI Level 1 — Immediate. Patient requires immediate life-saving intervention. "
                "Examples: cardiac arrest, respiratory failure, unresponsive patient, active seizure, "
                "severe anaphylaxis, major trauma with hemodynamic instability.",
    },
    {
        "id": 2,
        "esi": 2,
        "text": "ESI Level 2 — Emergent. High-risk situation; patient should not wait. "
                "Examples: chest pain with diaphoresis, acute stroke symptoms (facial droop, arm weakness, slurred speech), "
                "altered mental status, severe respiratory distress, suicidal ideation with plan, "
                "signs of sepsis (fever + hypotension + tachycardia).",
    },
    {
        "id": 3,
        "esi": 3,
        "text": "ESI Level 3 — Urgent. Patient is stable but requires multiple resources. "
                "Examples: moderate abdominal pain, asthma with mild wheeze, complex lacerations requiring imaging, "
                "high fever in immunocompromised patient, fracture without neurovascular compromise.",
    },
    {
        "id": 4,
        "esi": 4,
        "text": "ESI Level 4 — Less Urgent. Patient is stable; one resource needed. "
                "Examples: urinary tract infection, ear pain, minor laceration requiring suture, "
                "sprained ankle, cough without distress, stable chronic condition follow-up.",
    },
    {
        "id": 5,
        "esi": 5,
        "text": "ESI Level 5 — Non-Urgent. Patient is stable; no resources needed. "
                "Examples: prescription refill, minor rash without systemic symptoms, routine immunization, "
                "well-child check, cold symptoms for 1-2 days with no complications.",
    },
]


class QdrantSearchTool:
    """
    Manages ESI guideline index and exposes semantic search.

    On first use, seeds the Qdrant collection if empty.
    """

    def __init__(self) -> None:
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.client = AsyncQdrantClient(url=url)
        self._seeded = False

    async def _ensure_seeded(self) -> None:
        """Seed the Qdrant collection with ESI guidelines if not already done.

        We let client.add() manage collection creation — it configures the
        fastembed-compatible vector schema automatically.  A manually-created
        collection (VectorParams) is incompatible with the fastembed add() path.
        """
        if self._seeded:
            return

        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]

        if COLLECTION not in names or (await self.client.count(collection_name=COLLECTION)).count == 0:
            texts = [g["text"] for g in _ESI_GUIDELINES]
            await self.client.add(
                collection_name=COLLECTION,
                documents=texts,
                ids=[g["id"] for g in _ESI_GUIDELINES],
                metadata=[{"esi": g["esi"]} for g in _ESI_GUIDELINES],
            )

        self._seeded = True

    async def search(self, query: str, top_k: int = 2) -> list[dict[str, Any]]:
        """
        Semantic search over ESI clinical guidelines.

        Returns a list of matching guideline dicts with 'esi' level and 'text'.
        """
        await self._ensure_seeded()

        results = await self.client.query(
            collection_name=COLLECTION,
            query_text=query,
            limit=top_k,
        )

        return [
            {
                "esi": r.metadata.get("esi"),
                "text": r.document,
                "score": r.score,
            }
            for r in results
        ]


qdrant_tool = QdrantSearchTool()
