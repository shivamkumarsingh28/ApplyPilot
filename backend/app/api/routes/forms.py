from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.ratelimit import limit
from app.db.models import User
from app.db.session import get_db
from app.schemas.forms import MapIn
from app.services.form_mapper import map_fields
from app.services.profile_store import load_profile

router = APIRouter(prefix="/forms", tags=["forms"])


@router.post("/map", dependencies=[Depends(limit("ai"))])
def map_form(body: MapIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fields = [f.model_dump() for f in body.fields]
    mappings = map_fields(fields, load_profile(db, user))
    filled = sum(1 for m in mappings if m["value"] is not None)
    return {"mappings": mappings, "summary": {"total": len(mappings), "filled": filled,
                                                "needs_review": sum(1 for m in mappings if m["needs_review"] and not m["skipped"])}}
