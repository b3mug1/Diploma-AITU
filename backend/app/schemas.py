"""API request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import LockerStatus


class StudentCreate(BaseModel):
    student_code: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)


class StudentRead(StudentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class LockerCreate(BaseModel):
    locker_number: str = Field(min_length=1, max_length=64)
    location: str | None = Field(default=None, max_length=200)


class LockerStatusUpdate(BaseModel):
    status: LockerStatus


class LockerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    locker_number: str
    location: str | None
    status: LockerStatus
    created_at: datetime


class AssignmentCreate(BaseModel):
    student_id: int = Field(gt=0)
    locker_id: int = Field(gt=0)


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    locker_id: int
    started_at: datetime
    ended_at: datetime | None
