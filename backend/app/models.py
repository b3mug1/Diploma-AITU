"""Initial persistence models for the registry and assignment workflow."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
    true,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LockerStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="student")


class Locker(Base):
    __tablename__ = "lockers"

    id: Mapped[int] = mapped_column(primary_key=True)
    locker_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[LockerStatus] = mapped_column(
        SqlEnum(
            LockerStatus,
            name="locker_status",
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        default=LockerStatus.AVAILABLE,
        server_default=LockerStatus.AVAILABLE.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="locker")


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        Index(
            "uq_assignments_one_active_per_locker",
            "locker_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    locker_id: Mapped[int] = mapped_column(
        ForeignKey("lockers.id", ondelete="RESTRICT"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student] = relationship(back_populates="assignments")
    locker: Mapped[Locker] = relationship(back_populates="assignments")


class Role(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"
    TECHNICIAN = "technician"


class RepairStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


def enum_column(enum_type, name):
    return SqlEnum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda cls: [item.value for item in cls],
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'student' AND student_id IS NOT NULL) OR "
            "(role != 'student' AND student_id IS NULL)",
            name="ck_user_student_role",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[Role] = mapped_column(enum_column(Role, "user_role"))
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RepairRequest(Base):
    __tablename__ = "repair_requests"
    __table_args__ = (
        Index(
            "uq_repair_active_locker",
            "locker_id",
            unique=True,
            sqlite_where=text("status IN ('open', 'assigned', 'in_progress')"),
            postgresql_where=text("status IN ('open', 'assigned', 'in_progress')"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    locker_id: Mapped[int] = mapped_column(ForeignKey("lockers.id"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    description: Mapped[str] = mapped_column(String(2000))
    status: Mapped[RepairStatus] = mapped_column(
        enum_column(RepairStatus, "repair_status"), default=RepairStatus.OPEN
    )
    resolution: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
