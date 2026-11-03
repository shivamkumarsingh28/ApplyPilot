from fastapi import APIRouter

from app import __version__
from app.services.llm.factory import get_llm
from app.services.segmenter import get_segmenter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    llm = get_llm()
    from app.core.config import get_settings
    from app.services.embeddings import embedding_model_name

    s = get_settings()
    out = {"status": "ok", "version": __version__,
           "llm": {"provider": llm.name, "offline": llm.offline, "model": s.meta_model if llm.name == "meta" else None},
           "embeddings": embedding_model_name(),
           "segmenter": get_segmenter().name}
    if llm.name == "meta":
        # One cheap live probe so an invalid/expired key is visible, not silent.
        try:
            llm.chat([{"role": "user", "content": "Reply OK"}], max_tokens=10)
            out["llm"]["api_status"] = "ok"
        except Exception as exc:
            out["llm"]["api_status"] = "error"
            out["llm"]["detail"] = str(exc)[:300]
    return out
