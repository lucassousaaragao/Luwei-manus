import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database_async import get_db
from api.auth import get_current_user
from api.permissions import verify_workspace_access, verify_org_access
from api.db_models import Session, Message, Workspace, WorkspaceMember, UserRole

router = APIRouter(prefix="/api/chat")


class CreateSessionRequest(BaseModel):
    title: str = "Novo Chat"
    model: str = "default"
    mode: str = "chat"
    speed: str = "medium"
    workspace_id: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    mode: Optional[str] = None
    speed: Optional[str] = None


@router.get("/sessions")
async def list_sessions(
    workspace_id: Optional[str] = None,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Session)
        .where(Session.user_id == user["id"], Session.organization_id == user["org_id"])
        .order_by(desc(Session.updated_at))
    )
    if workspace_id:
        query = query.where(Session.workspace_id == workspace_id)
    result = await db.execute(query)
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "model": s.model,
            "mode": s.mode,
            "speed": s.speed,
            "workspace_id": s.workspace_id,
            "organization_id": s.organization_id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in sessions
    ]


@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if req.workspace_id:
        has_access = await verify_workspace_access(db, req.workspace_id, user["id"])
        if not has_access:
            raise HTTPException(403, "No access to workspace")

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session = Session(
        id=session_id,
        user_id=user["id"],
        workspace_id=req.workspace_id,
        organization_id=user["org_id"],
        title=req.title,
        model=req.model,
        mode=req.mode,
        speed=req.speed,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    await db.flush()
    return {
        "id": session.id,
        "title": session.title,
        "model": session.model,
        "mode": session.mode,
        "speed": session.speed,
        "workspace_id": session.workspace_id,
        "organization_id": session.organization_id,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user["id"],
            Session.organization_id == user["org_id"],
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    messages_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    return {
        "session": {
            "id": session.id,
            "title": session.title,
            "model": session.model,
            "mode": session.mode,
            "speed": session.speed,
            "workspace_id": session.workspace_id,
            "organization_id": session.organization_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata_,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    req: UpdateSessionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user["id"],
            Session.organization_id == user["org_id"],
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    updates = {}
    if req.title is not None:
        updates["title"] = req.title
    if req.model is not None:
        updates["model"] = req.model
    if req.mode is not None:
        updates["mode"] = req.mode
    if req.speed is not None:
        updates["speed"] = req.speed
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        for k, v in updates.items():
            setattr(session, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user["id"],
            Session.organization_id == user["org_id"],
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    await db.execute(delete(Message).where(Message.session_id == session_id))
    await db.delete(session)
    await db.commit()
    return {"ok": True}


class SendMessageRequest(BaseModel):
    content: str


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    req: SendMessageRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user["id"],
            Session.organization_id == user["org_id"],
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    now = datetime.now(timezone.utc)
    message = Message(session_id=session_id, role="user", content=req.content, created_at=now)
    db.add(message)
    session.updated_at = now
    await db.commit()
    return {"ok": True}