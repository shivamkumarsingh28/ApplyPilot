from fastapi import APIRouter

from app import __version__
from app.services.llm.factory import get_llm
from app.services.segmenter import get_segmenter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    llm = get_llm()
    return {"status": "ok", "version": __version__, "llm": {"provider": llm.name, "offline": llm.offline},
            "segmenter": get_segmenter().name}
