from datetime import date
from typing import Optional
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Member(Base):
    """A member of the small group."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    given_name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str] = mapped_column(String(50))
    gender: Mapped[str] = mapped_column(String(1))
    faith_status: Mapped[str] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship to attendance records
    attendance_records: Mapped[list["Attendance"]] = relationship(
        back_populates="member"
    )


class Attendance(Base):
    """Record of attendance for a member on a specific date."""

    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    date: Mapped[date] = mapped_column(Date)
    present: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship to member
    member: Mapped[Member] = relationship(back_populates="attendance_records")
