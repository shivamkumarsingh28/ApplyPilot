"""Run the 30-question retrieval evaluation against the sample notice.

Usage: python scripts/evaluate.py   (from backend/, offline mock model is fine)
Prints score + timing so keep-vs-change decisions are measured, not guessed.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.models import Notice, User  # noqa: E402,F401
from app.db.session import get_engine, init_db  # noqa: E402
from app.services.evaluation import evaluate_retrieval  # noqa: E402
from app.services.notice_service import build_notice  # noqa: E402


def main() -> None:
    init_db()
    db = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)()
    user = db.query(User).first()
    if user is None:
        user = User(email="eval@local", password_hash="x", full_name="Eval")
        db.add(user)
        db.commit()
        db.refresh(user)
    text = (Path(__file__).resolve().parents[2] / "samples" / "sample_notice.txt").read_text().replace("\\f", "\f")
    t0 = time.perf_counter()
    notice = build_notice(db, user, text.split("\f"), "sample_notice.txt", "", add_to_tracker=False)
    ingest_s = time.perf_counter() - t0
    result = evaluate_retrieval(db, notice)
    print(f"ingest_seconds={ingest_s:.2f} eval_seconds={result['seconds']}")
    print(f"SCORE {result['passed']}/{result['total']} = {result['score']}")
    for d in result["details"]:
        if not d["ok"]:
            print(f"  MISS page {d['expected_page']}: {d['question']} -> {d['pages']}")


if __name__ == "__main__":
    main()
