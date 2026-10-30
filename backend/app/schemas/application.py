from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["planned", "in_progress", "submitted", "closed"]


class ApplicationIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    notice_id: int | None = None
    status: Status = "planned"
    deadline: date | None = None
    notes: str = Field(default="", max_length=4000)


class ApplicationPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: Status | None = None
    deadline: date | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ApplicationOut(BaseModel):
    id: int
    title: str
    notice_id: int | None
    status: str
    deadline: date | None
    notes: str
    created_at: datetime
    days_left: int | None = None
