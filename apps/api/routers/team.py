"""Team router — member invites, roles, and management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import TeamMember, User

router = APIRouter(tags=["team"])


class InviteRequest(BaseModel):
    email: str
    role: str = "member"


class RoleUpdateRequest(BaseModel):
    role: str


@router.get("")
async def list_team_members(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all team members in the organization."""
    result = await db.execute(
        select(TeamMember).where(TeamMember.org_id == auth.org_id)
        .order_by(TeamMember.invited_at.desc())
    )
    members = result.scalars().all()

    member_list = []
    for m in members:
        user = None
        if m.user_id:
            user = (await db.execute(select(User).where(User.id == m.user_id))).scalar_one_or_none()

        member_list.append({
            "id": str(m.id),
            "email": m.email,
            "role": m.role,
            "status": m.status,
            "full_name": user.full_name if user else None,
            "avatar_url": user.avatar_url if user else None,
            "invited_at": m.invited_at.isoformat() if m.invited_at else None,
            "accepted_at": m.accepted_at.isoformat() if m.accepted_at else None,
        })

    # Also include the current user's own record
    current_user = (await db.execute(select(User).where(User.id == auth.user_id))).scalar_one_or_none()
    owner_entry = {
        "id": str(auth.user_id),
        "email": auth.email,
        "role": auth.role,
        "status": "active",
        "full_name": current_user.full_name if current_user else None,
        "avatar_url": current_user.avatar_url if current_user else None,
        "is_self": True,
    }
    return {"members": [owner_entry] + member_list, "total": 1 + len(member_list)}


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: InviteRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new team member by email."""
    if auth.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can invite members")

    valid_roles = ("admin", "member", "viewer")
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(valid_roles)}")

    existing = (await db.execute(
        select(TeamMember).where(
            TeamMember.org_id == auth.org_id,
            TeamMember.email == data.email.lower(),
        )
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="This email has already been invited")

    member = TeamMember(
        org_id=auth.org_id,
        email=data.email.lower(),
        role=data.role,
        status="pending",
        invited_by=auth.user_id,
        invited_at=datetime.now(timezone.utc),
    )
    db.add(member)
    await db.commit()

    return {
        "id": str(member.id),
        "email": member.email,
        "role": member.role,
        "status": "pending",
        "message": f"Invitation sent to {member.email}",
    }


@router.patch("/{member_id}/role")
async def update_member_role(
    member_id: UUID,
    data: RoleUpdateRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role."""
    if auth.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can change roles")

    member = (await db.execute(
        select(TeamMember).where(TeamMember.id == member_id, TeamMember.org_id == auth.org_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    member.role = data.role
    await db.commit()
    return {"success": True, "role": data.role}


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a team member from the organization."""
    if auth.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can remove members")

    member = (await db.execute(
        select(TeamMember).where(TeamMember.id == member_id, TeamMember.org_id == auth.org_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    await db.delete(member)
    await db.commit()
