"""Retrieval evaluation (plan step 2 / section 7).

30-question set over the sample notice: each item knows the page that must be
retrieved. Score = fraction whose expected page appears in the reranked top-3.
Run after every retrieval change; keep-vs-change decisions come from this.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.db.models import Notice
from app.services import rag

QUESTIONS: list[tuple[str, int]] = [
    ("What is the last date to apply?", 1), ("When is the closing date for applications?", 1),
    ("What is the age limit?", 1), ("How old can I be to apply?", 1),
    ("Is there age relaxation for SC candidates?", 1), ("Age relaxation for OBC?", 1),
    ("What qualification is needed?", 1), ("Do I need Class 10 to apply?", 1),
    ("What percentage is required in Class 10?", 1), ("How much is the application fee?", 2),
    ("What is the cost to apply?", 2), ("How do I pay the fee?", 2),
    ("Which documents must I upload?", 2), ("Do I need a caste certificate?", 2),
    ("What photo size is required?", 2), ("Photograph specification in pixels?", 2),
    ("Signature file size limit?", 2), ("What are the signature dimensions?", 2),
    ("What is the selection process?", 3), ("How many stages are there?", 3),
    ("What is in the physical fitness test?", 3), ("How fast must I run 1.6 km?", 3),
    ("How many pull-ups are needed?", 3), ("What is the minimum height?", 3),
    ("Is there a medical examination?", 3), ("Will documents be verified?", 3),
    ("Where must I apply?", 1), ("What is the official website?", 1),
    ("Should I keep a printed copy?", 2), ("Does the board ask for money on UPI?", 3),
]


def evaluate_retrieval(db: Session, notice: Notice) -> dict:
    t0 = time.perf_counter()
    passed, details = 0, []
    for q, expected in QUESTIONS:
        hits = rag.rerank(q, rag.retrieve(db, notice.id, q), keep=3)
        ok = expected in {h["page"] for h in hits}
        passed += ok
        details.append({"question": q, "expected_page": expected, "pages": sorted({h["page"] for h in hits}), "ok": ok})
    return {"score": round(passed / len(QUESTIONS), 3), "passed": passed, "total": len(QUESTIONS),
            "seconds": round(time.perf_counter() - t0, 2), "details": details}
