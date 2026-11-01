from datetime import datetime

from pydantic import BaseModel, Field


class NoticeOut(BaseModel):
    id: int
    title: str
    source_filename: str
    structured: dict
    scam_report: dict
    created_at: datetime
    apply_link: str | None = None
    doc_type: str | None = None
    shared: bool = False
    trust: str = "private"


class NoticeListItem(BaseModel):
    id: int
    title: str
    last_date: str | None
    scam_level: str | None
    created_at: datetime


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class AskOut(BaseModel):
    answer: str
    mode: str
    citations: list[dict]
