# api/workspaces.py
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from api.database import get_db
from api.auth import get_current_user

router = APIRouter(prefix="/api/workspaces")


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str = ""


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("")
def list_workspaces(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT id, name, description, created_at FROM workspaces WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_workspace(req: CreateWorkspaceRequest, user=Depends(get_current_user)):
    wid = str(uuid.uuid4())
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO workspaces (id, user_id, name, description, created_at) VALUES (?, ?, ?, ?, ?)",
        (wid, user["id"], req.name, req.description, now),
    )
    db.commit()
    return {"id": wid, "name": req.name, "description": req.description}


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, user=Depends(get_current_user)):
    db = get_db()
    ws = db.execute(
        "SELECT * FROM workspaces WHERE id = ? AND user_id = ?",
        (workspace_id, user["id"]),
    ).fetchone()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return dict(ws)


@router.put("/{workspace_id}")
def update_workspace(workspace_id: str, req: UpdateWorkspaceRequest, user=Depends(get_current_user)):
    db = get_db()
    ws = db.execute(
        "SELECT id FROM workspaces WHERE id = ? AND user_id = ?",
        (workspace_id, user["id"]),
    ).fetchone()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    updates = {}
    if req.name is not None: updates["name"] = req.name
    if req.description is not None: updates["description"] = req.description
    if updates:
        db.execute(
            f"UPDATE workspaces SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
            (*updates.values(), workspace_id),
        )
        db.commit()
    return {"ok": True}


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str, user=Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM mcp_configs WHERE workspace_id = ?", (workspace_id,))
    db.execute("UPDATE sessions SET workspace_id = NULL WHERE workspace_id = ? AND user_id = ?", (workspace_id, user["id"]))
    db.execute("DELETE FROM workspaces WHERE id = ? AND user_id = ?", (workspace_id, user["id"]))
    db.commit()
    return {"ok": True}
