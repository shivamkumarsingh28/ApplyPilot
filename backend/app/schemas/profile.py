from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Qualification = Literal["below_10th", "10th", "12th", "diploma", "graduate", "postgraduate", "doctorate"]


class ProfileData(BaseModel):
    """Everything the autofill and eligibility engines can use.

    We deliberately do NOT collect national ID, passport or payment numbers. They
    are the most sensitive data and the extension refuses to fill such fields anyway.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    father_name: str | None = Field(default=None, max_length=200)
    mother_name: str | None = Field(default=None, max_length=200)
    dob: str | None = None  # ISO date, YYYY-MM-DD
    gender: Literal["male", "female", "other"] | None = None
    category: str | None = Field(default=None, max_length=30)  # general, obc, sc, st, ews ...
    nationality: str | None = Field(default=None, max_length=60)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    address_line: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=12)
    qualification: Qualification | None = None
    qualification_year: int | None = Field(default=None, ge=1950, le=2100)
    percentage: float | None = Field(default=None, ge=0, le=100)
    ex_servicemen_ward: bool = False

    @field_validator("dob")
    @classmethod
    def _dob(cls, v):
        if v in (None, ""):
            return None
        date.fromisoformat(v)  # raises ValueError -> 422
        return v

    @field_validator("category")
    @classmethod
    def _category(cls, v):
        return v.strip().lower() if v else v
