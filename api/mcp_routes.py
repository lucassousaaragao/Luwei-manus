import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.database_async import get_db
from api.auth import get_current_user
from api.dependencies import verify_workspace_access
from api.db_models import McpConfig, Workspace, UserRole

router = APIRouter(prefix="/api/mcp")


class CreateMcpRequest(BaseModel):
    workspace_id: str
    name: str
    type: str = "stdio"
    command: str = ""
    url: str = ""
    args: List[str] = []


class UpdateMcpRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    command: Optional[str] = None
    url: Optional[str] = None
    args: Optional[List[str]] = None
    enabled: Optional[bool] = None


@router.get("/configs")
async def list_mcp_configs(
    workspace_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, workspace_id, user["id"])
    if not has_access:
        raise HTTPException(403, "No access to workspace")

    result = await db.execute(
        select(McpConfig).where(McpConfig.workspace_id == workspace_id)
    )
    configs = result.scalars().all()
    return [
        {
            "id": c.id,
            "workspace_id": c.workspace_id,
            "name": c.name,
            "type": c.type,
            "command": c.command,
            "url": c.url,
            "args": json.loads(c.args) if c.args else [],
            "env": json.loads(c.env) if c.env else {},
            "enabled": c.enabled,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in configs
    ]


@router.post("/configs")
async def create_mcp_config(
    req: CreateMcpRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    has_access = await verify_workspace_access(db, req.workspace_id, user["id"])
    if not has_access:
        raise HTTPException(403, "No access to workspace")

    mid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    cfg = McpConfig(
        id=mid,
        workspace_id=req.workspace_id,
        name=req.name,
        type=req.type,
        command=req.command,
        url=req.url,
        args=json.dumps(req.args),
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    db.add(cfg)
    await db.commit()
    return {"id": mid, **req.model_dump()}


@router.put("/configs/{config_id}")
async def update_mcp_config(
    config_id: str,
    req: UpdateMcpRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(McpConfig).where(McpConfig.id == config_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "MCP config not found")

    has_access = await verify_workspace_access(db, cfg.workspace_id, user["id"])
    if not has_access:
        raise HTTPException(403, "No access to workspace")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.type is not None:
        updates["type"] = req.type
    if req.command is not None:
        updates["command"] = req.command
    if req.url is not None:
        updates["url"] = req.url
    if req.args is not None:
        updates["args"] = json.dumps(req.args)
    if req.enabled is not None:
        updates["enabled"] = req.enabled
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        for k, v in updates.items():
            setattr(cfg, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/configs/{config_id}")
async def delete_mcp_config(
    config_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(McpConfig).where(McpConfig.id == config_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "MCP config not found")

    has_access = await verify_workspace_access(db, cfg.workspace_id, user["id"])
    if not has_access:
        raise HTTPException(403, "No access to workspace")

    await db.delete(cfg)
    await db.commit()
    return {"ok": True}