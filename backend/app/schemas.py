"""API request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import LockerStatus, RepairStatus, Role


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_code: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)


class StudentRead(StudentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class LockerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
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


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=128)


class UserCreate(Login):
    password: str = Field(min_length=12, max_length=128)
    role: Role
    student_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def linked_student(self):
        if (self.role == Role.STUDENT) != (self.student_id is not None):
            raise ValueError("Only student accounts must have a student_id")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: Role
    student_id: int | None
    is_active: bool


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class RepairCreate(BaseModel):
    locker_id: int = Field(gt=0)
    description: str = Field(min_length=5, max_length=2000)

    @field_validator("description")
    @classmethod
    def trim_description(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Provide a meaningful description")
        return value.strip()


class RepairAssign(BaseModel):
    technician_id: int = Field(gt=0)


class RepairTransition(BaseModel):
    status: RepairStatus
    resolution: str | None = Field(default=None, max_length=2000)


class RepairRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    locker_id: int
    reporter_id: int
    technician_id: int | None
    description: str
    status: RepairStatus
    resolution: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
