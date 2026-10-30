from datetime import datetime

from pydantic import BaseModel

DOCUMENT_KINDS = ["photo", "signature", "marksheet_10", "marksheet_12", "degree", "caste_certificate",
                  "domicile", "id_proof", "birth_certificate", "other"]


class DocumentOut(BaseModel):
    id: int
    kind: str
    filename: str
    mime: str
    size: int
    created_at: datetime
