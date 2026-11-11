from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["admin", "lead", "tester", "reviewer", "writer"]
USERNAME = r"^[A-Za-z0-9_.-]{3,64}$"


class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)
    otp: str | None = Field(default=None, max_length=8)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=10, max_length=128)


class OtpIn(BaseModel):
    code: str = Field(max_length=8)


class PasswordIn(BaseModel):
    password: str = Field(max_length=256)


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: Role


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    totp_enabled: bool


class EngagementBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client: str = Field(min_length=1, max_length=200)
    scope: str = Field(default="", max_length=20000)
    start_date: date
    end_date: date
    roe_text: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai")
        return self


class EngagementIn(EngagementBase):
    pass


class EngagementUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    client: str | None = Field(default=None, min_length=1, max_length=200)
    scope: str | None = Field(default=None, max_length=20000)
    start_date: date | None = None
    end_date: date | None = None
    roe_text: str | None = Field(default=None, max_length=20000)


class MembersIn(BaseModel):
    user_ids: list[int] = Field(max_length=100)


class EngagementStatusIn(BaseModel):
    status: Literal["draft", "active", "completed"]


class FindingBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)
    impact: str = Field(default="", max_length=10000)
    recommendation: str = Field(default="", max_length=10000)
    cvss_vector: str = Field(max_length=512)
    due_date: date | None = None


class FindingIn(FindingBase):
    pass


class FindingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    impact: str | None = Field(default=None, max_length=10000)
    recommendation: str | None = Field(default=None, max_length=10000)
    cvss_vector: str | None = Field(default=None, max_length=512)
    due_date: date | None = None


class FindingStatusIn(BaseModel):
    status: Literal["open", "fixed"]  # "lulus retest" hanya dihasilkan oleh ronde retest
    notes: str = Field(default="", max_length=5000)


class TemplateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)
    impact: str = Field(default="", max_length=10000)
    recommendation: str = Field(default="", max_length=10000)
    cvss_vector: str = Field(max_length=512)


class CvssIn(BaseModel):
    vector: str = Field(max_length=512)

    @field_validator("vector")
    @classmethod
    def _strip(cls, v):
        return v.strip()


class ReviewIn(BaseModel):
    action: Literal["submit", "approve", "request_changes"]
    note: str = Field(default="", max_length=5000)


class RetestIn(BaseModel):
    result: Literal["passed", "failed", "partial"]
    tested_at: date | None = None
    notes: str = Field(default="", max_length=5000)


class NoteTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=200_000)
    make_default: bool = False


class NoteTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, max_length=200_000)


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    template_id: int | None = None


class NoteUpdate(BaseModel):
    content: str = Field(max_length=200_000)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    base_version: int = Field(ge=1)
