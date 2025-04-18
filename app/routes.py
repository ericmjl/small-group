from datetime import date
from typing import Annotated
from fastapi import Depends, Form, Request, responses
from sqlalchemy.orm import Session
from pypinyin import lazy_pinyin, Style
from sqlalchemy import or_
from loguru import logger
import json
from fastapi.responses import PlainTextResponse

from . import app, templates
from .database import get_db
from .models import Member, Attendance
from app.group_divider import (
    divide_into_groups,
    GroupMember,
    MemberRole,
    balance_gender_in_groups,
)
from app.models import Member as DBMember

# Global variable to store the current groups
current_groups = None


def get_pinyin(text: str) -> str:
    """Get pinyin for Chinese text.

    :param text: Chinese text
    :return: Pinyin string
    """
    return "".join(lazy_pinyin(text, style=Style.NORMAL))


@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page showing all members and attendance."""
    global current_groups
    members = db.query(Member).filter(Member.active == True).all()
    today = date.today()

    # Get today's attendance records
    attendance_records = db.query(Attendance).filter(Attendance.date == today).all()

    # Convert to dictionary for easy lookup
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    # Get present member IDs for group division
    present_members = {
        record.member_id for record in attendance_records if record.present
    }

    # Initialize groups as None
    groups = None

    try:
        if present_members:
            # Convert DB members to GroupMember class - ONLY for present members
            group_members = [
                GroupMember(
                    id=m.id,
                    surname=m.surname,
                    given_name=m.given_name,
                    role=MemberRole.from_db_role(m.role),
                    gender=m.gender,
                    faith_status=m.faith_status,
                    education_status=m.education_status,
                    is_graduated=m.education_status == "graduated",
                    is_present=True,
                    prep_attended=m.prep_attended,
                )
                for m in members
                if m.id in present_members
            ]

            if len(group_members) >= 4:
                # Calculate initial number of groups based on present members
                present_count = len(group_members)
                leader_count = sum(
                    1
                    for m in group_members
                    if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
                )

                if leader_count > 0:
                    # Initial estimate: aim for 5-6 people per group
                    target_group_size = 6
                    initial_num_groups = max(present_count // target_group_size, 2)

                    # Adjust for leader availability
                    num_groups = min(initial_num_groups, leader_count)

                    # Divide into groups - initial proposal without gender balancing
                    groups = divide_into_groups(
                        group_members, num_groups, max_iterations=0
                    )

                    # Store the current groups globally
                    current_groups = groups

    except ValueError as e:
        logger.warning(f"Could not create initial groups: {e}")

    return request.app.state.templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
            "groups": groups,
        },
    )


@app.get("/inactive")
async def inactive_members(request: Request, db: Session = Depends(get_db)):
    """Page showing inactive members."""
    members = db.query(Member).filter(Member.active == False).all()
    return request.app.state.templates.TemplateResponse(
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

    return request.app.state.templates.TemplateResponse(
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

    return request.app.state.templates.TemplateResponse(
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

    return request.app.state.templates.TemplateResponse(
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
    attendance_date: Annotated[str, Form()],
    present: Annotated[str, Form()],
    notes: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
):
    """Record attendance for a member."""
    # Debug log the incoming data
    form_data = await request.form()
    logger.debug(f"Received form data: {dict(form_data)}")
    logger.debug(f"Processing attendance for member {member_id}, present: {present}")

    # Convert string date to date object
    attendance_date = date.fromisoformat(attendance_date)

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
        logger.debug(f"Updating existing attendance record for member {member_id}")
        attendance.present = present == "true"
        attendance.notes = notes
    else:
        logger.debug(f"Creating new attendance record for member {member_id}")
        attendance = Attendance(
            member_id=member_id,
            date=attendance_date,
            present=present == "true",
            notes=notes,
        )
        db.add(attendance)

    db.commit()
    return responses.Response(
        status_code=204
    )  # No content needed as checkbox handles its own state


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
    return request.app.state.templates.TemplateResponse(
        "partials/inactive_member_list.html",
        {
            "request": request,
            "members": members,
        },
    )


@app.post("/divide-groups")
async def divide_groups(request: Request):
    """Handle group division request."""
    global current_groups
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
                surname=m.surname,
                given_name=m.given_name,
                role=MemberRole.from_db_role(m.role),
                gender=m.gender,
                faith_status=m.faith_status,
                education_status=m.education_status,
                is_graduated=m.education_status == "graduated",
                is_present=True,  # All members in this list are present
                prep_attended=m.prep_attended,
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

        # Store the current groups globally
        current_groups = groups

        return request.app.state.templates.TemplateResponse(
            "partials/group_divisions.html", {"request": request, "groups": groups}
        )
    except ValueError as e:
        # Return an error message if constraints cannot be satisfied
        return request.app.state.templates.TemplateResponse(
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


@app.post("/members/search")
async def search_members(
    request: Request, query: Annotated[str, Form()], db: Session = Depends(get_db)
):
    """Search members by name (supports Chinese and pinyin)."""
    logger.debug(f"Search query: {query}")

    # Get all active members
    members = db.query(Member).filter(Member.active == True).all()

    if not query:
        filtered_members = members
    else:
        # Convert query to pinyin if it contains Chinese characters
        query_pinyin = get_pinyin(query.lower())
        logger.debug(f"Query pinyin: {query_pinyin}")

        # Filter members based on query
        filtered_members = []
        for member in members:
            full_name = f"{member.surname}{member.given_name}"
            name_pinyin = get_pinyin(full_name.lower())
            logger.debug(f"Member {full_name} pinyin: {name_pinyin}")

            # Match against Chinese name or pinyin
            if query.lower() in full_name.lower() or query_pinyin in name_pinyin:
                filtered_members.append(member)

    logger.debug(f"Found {len(filtered_members)} matches")

    # Get today's attendance for filtered members
    today = date.today()
    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.date == today,
            Attendance.member_id.in_([m.id for m in filtered_members]),
        )
        .all()
    )

    # Convert to dictionary for easy lookup
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_table_body.html",
        {
            "request": request,
            "members": filtered_members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.post("/attendance/select-all")
async def select_all_attendance(
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark all active members as present for today."""
    today = date.today()
    members = db.query(Member).filter_by(active=True).all()

    # Create or update attendance records for all members
    for member in members:
        attendance = (
            db.query(Attendance).filter_by(member_id=member.id, date=today).first()
        )
        if attendance:
            attendance.present = True
        else:
            attendance = Attendance(
                member_id=member.id,
                date=today,
                present=True,
            )
            db.add(attendance)
    db.commit()

    # Get updated data for table only
    members = db.query(Member).filter_by(active=True).all()
    attendance_records = db.query(Attendance).filter_by(date=today).all()
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_table_body.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.post("/attendance/unselect-all")
async def unselect_all_attendance(
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark all active members as absent for today."""
    today = date.today()
    members = db.query(Member).filter_by(active=True).all()

    # Create or update attendance records for all members
    for member in members:
        attendance = (
            db.query(Attendance).filter_by(member_id=member.id, date=today).first()
        )
        if attendance:
            attendance.present = False
        else:
            attendance = Attendance(
                member_id=member.id,
                date=today,
                present=False,
            )
            db.add(attendance)
    db.commit()

    return templates.TemplateResponse(
        "partials/member_table_body.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": {
                record.member_id: {"present": False, "notes": ""}
                for record in db.query(Attendance).filter_by(date=today).all()
            },
        },
    )


@app.post("/groups/generate")
async def generate_groups(
    request: Request,
    target_size: int = Form(7),  # Default to 7 if not provided
    db: Session = Depends(get_db),
):
    """Generate groups based on current attendance and target size, with gender balancing."""
    global current_groups
    today = date.today()
    members = db.query(Member).filter_by(active=True).all()
    attendance_records = db.query(Attendance).filter_by(date=today).all()

    # Get present member IDs for group division
    present_members = {
        record.member_id for record in attendance_records if record.present
    }
    groups = None

    try:
        if present_members:
            logger.info(f"Generating groups for {len(present_members)} present members")
            # Convert DB members to GroupMember class - ONLY for present members
            group_members = [
                GroupMember(
                    id=m.id,
                    surname=m.surname,
                    given_name=m.given_name,
                    role=MemberRole.from_db_role(m.role),
                    gender=m.gender,
                    faith_status=m.faith_status,
                    education_status=m.education_status,
                    is_graduated=m.education_status == "graduated",
                    is_present=True,
                    prep_attended=m.prep_attended,
                )
                for m in members
                if m.id in present_members
            ]

            if len(group_members) >= 4:
                # Calculate initial number of groups based on target size
                present_count = len(group_members)
                num_groups = max(1, (present_count + target_size - 1) // target_size)
                logger.info(
                    f"Will create {num_groups} groups with target size {target_size}"
                )

                # Stage 1: Initial group division without gender balancing
                logger.info("Stage 1: Initial group division")
                initial_groups = divide_into_groups(
                    group_members,
                    num_groups,
                    max_iterations=0,
                    target_size=target_size,  # Pass target_size parameter
                )

                # Stage 2: Apply gender balancing using Metropolis-Hastings
                logger.info("Stage 2: Starting gender balancing")
                groups = balance_gender_in_groups(
                    initial_groups,
                    max_iterations=10_000,
                    target_size=target_size,  # Pass target_size parameter
                )
                logger.info("Gender balancing complete")

                # Store the current groups globally
                current_groups = groups

    except ValueError as e:
        logger.warning(f"Could not create groups: {e}")
    except Exception as e:
        logger.exception("Unexpected error during group generation")

    return templates.TemplateResponse(
        "partials/group_divisions.html",
        {
            "request": request,
            "groups": groups,
            "error": None if groups else "Not enough members or leaders for groups",
        },
    )


@app.post("/members/{member_id}/prep")
async def update_prep_attendance(
    request: Request,
    member_id: int,
    prep_attended: Annotated[bool, Form()],
    db: Session = Depends(get_db),
):
    """Update prep attendance status for a member."""
    member = db.query(Member).filter(Member.id == member_id).first()
    member.prep_attended = prep_attended
    db.commit()
    return responses.Response(
        status_code=204
    )  # No content needed as checkbox handles its own state


@app.post("/members/prep/select-all")
async def select_all_prep(
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark all active members as having done prep."""
    members = db.query(Member).filter_by(active=True).all()
    for member in members:
        member.prep_attended = True
    db.commit()

    today = date.today()
    attendance_records = db.query(Attendance).filter_by(date=today).all()
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_table_body.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.post("/members/prep/unselect-all")
async def unselect_all_prep(
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark all active members as not having done prep."""
    members = db.query(Member).filter_by(active=True).all()
    for member in members:
        member.prep_attended = False
    db.commit()

    today = date.today()
    attendance_records = db.query(Attendance).filter_by(date=today).all()
    attendance = {
        record.member_id: {"present": record.present, "notes": record.notes}
        for record in attendance_records
    }

    return templates.TemplateResponse(
        "partials/member_table_body.html",
        {
            "request": request,
            "members": members,
            "today": today,
            "attendance": attendance,
        },
    )


@app.get("/groups/markdown", response_class=PlainTextResponse)
async def get_groups_markdown(request: Request, db: Session = Depends(get_db)):
    """Generate markdown text for the current group divisions."""
    global current_groups
    today = date.today()

    markdown_text = f"# 小組分組 {today.strftime('%Y-%m-%d')}\n\n"

    try:
        # Use the globally stored groups instead of regenerating them
        if current_groups:
            # Generate markdown text from the current groups
            for i, group in enumerate(current_groups, 1):
                markdown_text += f"## 第 {i} 組\n\n"

                # List members
                for member in group.members:
                    # Use the same emoji as in the screenshot
                    emoji_map = {"M": "👨", "F": "👩"}
                    gender_symbol = emoji_map.get(member.gender, "")
                    name = f"{member.surname}{member.given_name}"

                    # Add role and education status
                    role_text = ""
                    if member.role == MemberRole.FACILITATOR:
                        role_text = "同工"
                    elif member.role == MemberRole.COUNSELOR:
                        role_text = "輔導"

                    edu_text = ""
                    if member.education_status == "graduate":
                        edu_text = "研究生"
                    elif member.education_status == "graduated":
                        edu_text = "已畢業"
                    elif member.education_status == "undergraduate":
                        edu_text = "本科生"

                    # Format the status text to match the UI
                    status_parts = []
                    if role_text:
                        status_parts.append(role_text)
                    if edu_text:
                        status_parts.append(edu_text)

                    status = f" ({', '.join(status_parts)})" if status_parts else ""

                    # Add prep attendance marker
                    prep = " ✓預查" if member.prep_attended else ""

                    markdown_text += f"- {gender_symbol} {name}{status}{prep}\n"

                markdown_text += "\n"
        else:
            # If no groups are stored, inform the user
            markdown_text += (
                "No groups have been generated yet. Please generate groups first."
            )
    except Exception as e:
        logger.exception("Error generating markdown")
        markdown_text += f"Error generating group divisions: {str(e)}"

    return markdown_text
