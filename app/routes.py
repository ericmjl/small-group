from datetime import date
from typing import Annotated
from fastapi import Depends, Form, Request
from sqlalchemy.orm import Session

from . import app, templates
from .database import get_db
from .models import Member, Attendance
from app.group_divider import divide_into_groups, GroupMember, MemberRole
from app.models import Member as DBMember


@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page showing all members and attendance."""
    members = db.query(Member).filter(Member.active == True).all()
    today = date.today()

    # Get today's attendance records
    attendance_records = db.query(Attendance).filter(Attendance.date == today).all()

    # Convert to dictionary for easy lookup
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.get("/inactive")
async def inactive_members(request: Request, db: Session = Depends(get_db)):
    """Page showing inactive members."""
    members = db.query(Member).filter(Member.active == False).all()
    return templates.TemplateResponse(
        "inactive_members.html",
        {
            "request": request,
            "members": members,
        },
    )


@app.post("/members/add")
async def add_member(
    request: Request,
    given_name: Annotated[str, Form()],
    surname: Annotated[str, Form()],
    gender: Annotated[str, Form()],
    faith_status: Annotated[str, Form()],
    role: Annotated[str, Form()],
    education_status: Annotated[str, Form()],
    notes: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
):
    """Add a new member."""
    member = Member(
        given_name=given_name,
        surname=surname,
        gender=gender,
        faith_status=faith_status,
        role=role,
        education_status=education_status,
        notes=notes,
    )
    db.add(member)
    db.commit()

    members = db.query(Member).filter(Member.active == True).all()
    today = date.today()

    # Get today's attendance records
    attendance_records = db.query(Attendance).filter(Attendance.date == today).all()

    # Convert to dictionary for easy lookup
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_list.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.put("/members/{member_id}/update")
async def update_member(
    request: Request,
    member_id: int,
    given_name: Annotated[str, Form()],
    surname: Annotated[str, Form()],
    gender: Annotated[str, Form()],
    faith_status: Annotated[str, Form()],
    role: Annotated[str, Form()],
    education_status: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    """Update a member's information."""
    member = db.query(Member).filter(Member.id == member_id).first()
    member.given_name = given_name
    member.surname = surname
    member.gender = gender
    member.faith_status = faith_status
    member.role = role
    member.education_status = education_status
    db.commit()

    members = db.query(Member).filter(Member.active == True).all()
    today = date.today()

    # Get today's attendance records
    attendance_records = db.query(Attendance).filter(Attendance.date == today).all()

    # Convert to dictionary for easy lookup
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_list.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.post("/members/{member_id}/toggle-active")
async def toggle_member_active(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db),
):
    """Toggle member active status."""
    member = db.query(Member).filter(Member.id == member_id).first()
    member.active = not member.active
    db.commit()

    members = db.query(Member).filter(Member.active == True).all()
    today = date.today()

    # Get today's attendance records
    attendance_records = db.query(Attendance).filter(Attendance.date == today).all()

    # Convert to dictionary for easy lookup
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_list.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.post("/attendance/record")
async def record_attendance(
    request: Request,
    member_id: Annotated[int, Form()],
    attendance_date: Annotated[date, Form()],
    present: Annotated[bool, Form()],
    notes: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
):
    """Record attendance for a member."""
    # Check if attendance record already exists
    attendance = (
        db.query(Attendance)
        .filter(
            Attendance.member_id == member_id,
            Attendance.date == attendance_date,
        )
        .first()
    )

    if attendance:
        attendance.present = present
        attendance.notes = notes
    else:
        attendance = Attendance(
            member_id=member_id,
            date=attendance_date,
            present=present,
            notes=notes,
        )
        db.add(attendance)

    db.commit()
    return {"status": "success"}


@app.delete("/members/{member_id}")
async def delete_member(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db),
):
    """Permanently delete a member from the database."""
    # First delete all attendance records
    db.query(Attendance).filter(Attendance.member_id == member_id).delete()
    # Then delete the member
    db.query(Member).filter(Member.id == member_id).delete()
    db.commit()

    # Return updated inactive members list
    members = db.query(Member).filter(Member.active == False).all()
    return templates.TemplateResponse(
        "partials/inactive_member_list.html",
        {
            "request": request,
            "members": members,
        },
    )


@app.post("/divide-groups")
async def divide_groups(request: Request):
    """Handle group division request."""
    try:
        db = next(get_db())
        members = db.query(DBMember).all()

        # Get today's attendance records
        today = date.today()
        attendance_records = (
            db.query(Attendance)
            .filter(
                Attendance.date == today,
                Attendance.present == True,  # Only get members marked as present
            )
            .all()
        )

        # Get set of present member IDs
        present_members = {record.member_id for record in attendance_records}

        if not present_members:
            raise ValueError("No members are marked as present today.")

        # Convert DB members to our GroupMember class - ONLY for present members
        group_members = [
            GroupMember(
                id=m.id,
                name=f"{m.surname}{m.given_name}",
                role=MemberRole.from_db_role(m.role),
                gender=m.gender,
                faith_status=m.faith_status,
                is_graduated=m.education_status == "graduated",
                is_present=True,  # All members in this list are present
            )
            for m in members
            if m.active and m.id in present_members  # Only include present members
        ]

        if len(group_members) < 4:
            raise ValueError(
                "Not enough present members to form groups (minimum 4 required)"
            )

        # Calculate initial number of groups based on present members only
        present_count = len(group_members)  # All members in group_members are present
        leader_count = sum(
            1
            for m in group_members
            if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
        )

        if leader_count == 0:
            raise ValueError("Cannot create groups: no leaders are present today")

        # Initial estimate: aim for 5-6 people per group
        target_group_size = 6
        initial_num_groups = max(present_count // target_group_size, 2)

        # Adjust for leader availability
        num_groups = min(initial_num_groups, leader_count)

        # Divide into groups
        groups = divide_into_groups(group_members, num_groups)

        return templates.TemplateResponse(
            "partials/group_divisions.html", {"request": request, "groups": groups}
        )
    except ValueError as e:
        # Return an error message if constraints cannot be satisfied
        return templates.TemplateResponse(
            "partials/group_divisions.html",
            {"request": request, "error": str(e)},
        )


@app.get("/debug/members")
async def debug_members(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint to show all members in database."""
    all_members = db.query(Member).all()
    active_members = db.query(Member).filter(Member.active == True).all()

    return {
        "total_members": len(all_members),
        "active_members": len(active_members),
        "members": [
            {"id": m.id, "name": f"{m.surname}{m.given_name}", "active": m.active}
            for m in all_members
        ],
    }
