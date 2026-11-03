import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Qualification = Literal["below_10th", "10th", "12th", "diploma", "graduate", "postgraduate", "doctorate"]

# Custom fields may NOT shadow a built-in field, and may never hold ID/payment
# data: the extension refuses to fill such fields, so storing them helps no one
# and only adds risk.
RESERVED_KEYS = {
    "full_name", "first_name", "last_name", "father_name", "mother_name", "dob", "gender", "category",
    "nationality", "email", "phone", "alternate_phone", "address_line", "correspondence_address",
    "city", "district", "state", "pincode", "qualification",
    "qualification_year", "percentage", "board_10", "qualification_year_10", "percentage_10",
    "percentage_graduation", "identification_mark", "ex_serviceman", "pwd",
    "ex_servicemen_ward", "extra_fields",
}
SENSITIVE_WORDS = re.compile(
    r"aadhaar|aadhar|passport|pan\b|card|cvv|otp|password|pin\b|account|ifsc|bank|ssn|social security", re.I)
_KEY = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


class ExtraField(BaseModel):
    """One user-created profile field: they name it, choose its type, and fill it.

    `key` is derived from the label at creation (slug); the frontend sends the
    finished object. Values stay strings except numbers, which are stored as numbers.
    """

    key: str = Field(min_length=2, max_length=41)
    label: str = Field(min_length=2, max_length=80)
    type: Literal["text", "number", "date", "select"] = "text"
    options: list[str] = Field(default_factory=list, max_length=20)
    value: str | float | None = None

    @field_validator("key")
    @classmethod
    def _key(cls, v):
        v = (v or "").strip().lower()
        if not _KEY.match(v) or v in RESERVED_KEYS or SENSITIVE_WORDS.search(v):
            raise ValueError("invalid or reserved field key")
        return v

    @field_validator("label")
    @classmethod
    def _label(cls, v):
        v = (v or "").strip()
        if SENSITIVE_WORDS.search(v):
            raise ValueError("this kind of information is not stored in the profile")
        return v

    @field_validator("value")
    @classmethod
    def _value(cls, v, info):
        if v in (None, ""):
            return None
        t = (info.data or {}).get("type", "text")
        if t == "number":
            try:
                return float(v)
            except (TypeError, ValueError):
                raise ValueError("value must be a number") from None
        if t == "date":
            date.fromisoformat(str(v))  # raises -> 422
        if t == "select" and info.data.get("options") and str(v) not in info.data["options"]:
            raise ValueError("value must be one of the options")
        return str(v)[:300]


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
    alternate_phone: str | None = Field(default=None, max_length=20)
    address_line: str | None = Field(default=None, max_length=300)
    correspondence_address: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=12)
    qualification: Qualification | None = None
    qualification_year: int | None = Field(default=None, ge=1950, le=2100)
    percentage: float | None = Field(default=None, ge=0, le=100)
    # Per-level education details used by SSC/UPSC-style forms (the SSC sample
    # asks for 10th board/year/% separately from graduation %/year).
    board_10: str | None = Field(default=None, max_length=120)
    qualification_year_10: int | None = Field(default=None, ge=1950, le=2100)
    percentage_10: float | None = Field(default=None, ge=0, le=100)
    percentage_graduation: float | None = Field(default=None, ge=0, le=100)
    identification_mark: str | None = Field(default=None, max_length=200)
    ex_serviceman: bool | None = None
    pwd: bool | None = None
    ex_servicemen_ward: bool = False
    extra_fields: list[ExtraField] = Field(default_factory=list, max_length=30)

    @field_validator("extra_fields")
    @classmethod
    def _extra_unique(cls, v):
        keys = [f.key for f in v or []]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate custom field key")
        return v

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
