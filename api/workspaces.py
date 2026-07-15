import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.database_async import get_db
from api.auth import get_current_user
from api.permissions import verify_workspace_access
from api.db_models import Workspace, WorkspaceMember, UserRole

router = APIRouter(prefix="/api/workspaces")


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str = ""
    image_url: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


@router.get("")
async def list_workspaces(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from api.auth import get_user_workspaces
    return await get_user_workspaces(db, user["id"], user["org_id"])


@router.post("")
async def create_workspace(
    req: CreateWorkspaceRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    wid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    ws = Workspace(
        id=wid,
        organization_id=user["org_id"],
        name=req.name,
        description=req.description,
        image_url=req.image_url,
        color=req.color,
        icon=req.icon,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(ws)
    await db.flush()

    wm = WorkspaceMember(workspace_id=wid, user_id=user["id"], role=UserRole.OWNER)
    db.add(wm)
    await db.commit()

    return {"id": wid, "name": req.name, "description": req.description, "image_url": req.image_url, "color": req.color, "icon": req.icon}


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.organization_id == user["org_id"],
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Workspace not found")

    has_access = await verify_workspace_access(db, workspace_id, user["id"])
    if not has_access:
        raise HTTPException(403, "No access to workspace")

    return {
        "id": ws.id,
        "organization_id": ws.organization_id,
        "name": ws.name,
        "description": ws.description,
        "image_url": ws.image_url,
        "color": ws.color,
        "icon": ws.icon,
        "settings": ws.settings,
        "created_by": ws.created_by,
        "created_at": ws.created_at,
        "updated_at": ws.updated_at,
    }


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    req: UpdateWorkspaceRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"], [UserRole.OWNER, UserRole.ADMIN])
    if not has_access:
        raise HTTPException(403, "No permission to update workspace")

    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Workspace not found")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.image_url is not None:
        updates["image_url"] = req.image_url
    if req.color is not None:
        updates["color"] = req.color
    if req.icon is not None:
        updates["icon"] = req.icon
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        for k, v in updates.items():
            setattr(ws, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"], [UserRole.OWNER])
    if not has_access:
        raise HTTPException(403, "Only owner can delete workspace")

    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Workspace not found")

    await db.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id))
    await db.delete(ws)
    await db.commit()
    return {"ok": True}


@router.post("/{workspace_id}/members")
async def add_workspace_member(
    workspace_id: str,
    email: str,
    role: str = "member",
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"], [UserRole.OWNER, UserRole.ADMIN])
    if not has_access:
        raise HTTPException(403, "No permission to add members")

    from api.db_models import User
    result = await db.execute(select(User).where(User.email == email))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(404, "User not found")

    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "User already member")

    try:
        member_role = UserRole(role)
    except ValueError:
        raise HTTPException(400, "Invalid role")

    wm = WorkspaceMember(workspace_id=workspace_id, user_id=target_user.id, role=member_role)
    db.add(wm)
    await db.commit()
    return {"ok": True}


@router.delete("/{workspace_id}/members/{user_id}")
async def remove_workspace_member(
    workspace_id: str,
    user_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"], [UserRole.OWNER, UserRole.ADMIN])
    if not has_access:
        raise HTTPException(403, "No permission to remove members")

    if user_id == user["id"]:
        raise HTTPException(400, "Cannot remove yourself")

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    wm = result.scalar_one_or_none()
    if not wm:
        raise HTTPException(404, "Member not found")

    if wm.role == UserRole.OWNER:
        raise HTTPException(400, "Cannot remove owner")

    await db.delete(wm)
    await db.commit()
    return {"ok": True}


@router.get("/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"])
    if not has_access:
        raise HTTPException(403, "No access to workspace")

    from api.db_models import User
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    members = []
    for wm, u in result:
        members.append({
            "user_id": u.id,
            "email": u.email,
            "name": u.name,
            "avatar_url": u.avatar_url,
            "role": wm.role.value,
            "joined_at": wm.joined_at,
        })
    return members