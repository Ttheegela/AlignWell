"""Offline ESI accuracy harness — no API key required."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "esi_cases.json"
OUT = Path(__file__).resolve().parent / "out"


def load_cases():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def naive_keyword_predictor(case: dict) -> int:
    text = (case.get("complaint") or "").lower()
    if any(k in text for k in ("anaphylaxis", "airway", "unresponsive", "cardiac arrest")):
        return 1
    if any(k in text for k in ("chest pain", "diaphoresis", "unstable", "severe abdominal")):
        return 2
    if any(k in text for k in ("fracture", "needs resources")):
        return 3
    if any(k in text for k in ("knee", "fever", "chronic")):
        return 4
    return 5


def run(predict=None) -> dict:
    predict = predict or naive_keyword_predictor
    cases = load_cases()
    hits = 0
    details = []
    for c in cases:
        got = int(predict(c))
        exp = int(c["expected_esi"])
        ok = got == exp
        hits += int(ok)
        details.append({"id": c["id"], "expected": exp, "got": got, "ok": ok})
    n = len(cases) or 1
    score = {"accuracy": round(hits / n, 3), "n": n, "hits": hits, "details": details}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "last_score.json").write_text(json.dumps(score, indent=2), encoding="utf-8")
    return score


if __name__ == "__main__":
    s = run()
    print(json.dumps(s, indent=2))
