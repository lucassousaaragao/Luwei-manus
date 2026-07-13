# api/mcp_routes.py
import uuid
import json
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from api.database import get_db
from api.auth import get_current_user

router = APIRouter(prefix="/api/mcp")


class CreateMcpRequest(BaseModel):
    workspace_id: str
    name: str
    type: str = "stdio"
    command: str = ""
    url: str = ""
    args: list[str] = []


class UpdateMcpRequest(BaseModel):
    name: str | None = None
    type: str | None = None
    command: str | None = None
    url: str | None = None
    args: list[str] | None = None
    enabled: bool | None = None


@router.get("/configs")
def list_mcp_configs(workspace_id: str, user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM mcp_configs WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/configs")
def create_mcp_config(req: CreateMcpRequest, user=Depends(get_current_user)):
    mid = str(uuid.uuid4())
    db = get_db()
    db.execute(
        "INSERT INTO mcp_configs (id, workspace_id, name, type, command, url, args) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (mid, req.workspace_id, req.name, req.type, req.command, req.url, json.dumps(req.args)),
    )
    db.commit()
    return {"id": mid, **req.model_dump()}


@router.put("/configs/{config_id}")
def update_mcp_config(config_id: str, req: UpdateMcpRequest, user=Depends(get_current_user)):
    db = get_db()
    existing = db.execute("SELECT id FROM mcp_configs WHERE id = ?", (config_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "MCP config not found")
    updates = {}
    if req.name is not None: updates["name"] = req.name
    if req.type is not None: updates["type"] = req.type
    if req.command is not None: updates["command"] = req.command
    if req.url is not None: updates["url"] = req.url
    if req.args is not None: updates["args"] = json.dumps(req.args)
    if req.enabled is not None: updates["enabled"] = 1 if req.enabled else 0
    if updates:
        db.execute(
            f"UPDATE mcp_configs SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
            (*updates.values(), config_id),
        )
        db.commit()
    return {"ok": True}


@router.delete("/configs/{config_id}")
def delete_mcp_config(config_id: str, user=Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM mcp_configs WHERE id = ?", (config_id,))
    db.commit()
    return {"ok": True}
