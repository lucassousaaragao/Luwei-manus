import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from api.database import get_db
from api.auth import get_current_user

router = APIRouter(prefix="/api/chat")


class CreateSessionRequest(BaseModel):
    title: str = "Novo Chat"
    model: str = "default"


@router.get("/sessions")
def list_sessions(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT id, title, model, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user["id"],),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions")
def create_session(req: CreateSessionRequest, user=Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO sessions (id, user_id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user["id"], req.title, req.model, now, now),
    )
    db.commit()
    return {"id": session_id, "title": req.title, "model": req.model}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user=Depends(get_current_user)):
    db = get_db()
    session = db.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not session:
        raise HTTPException(404, "Session not found")
    messages = db.execute(
        "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    ).fetchall()
    return {"session": dict(session), "messages": [dict(m) for m in messages]}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user["id"]))
    db.commit()
    return {"ok": True}


class SendMessageRequest(BaseModel):
    content: str


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: str, req: SendMessageRequest, user=Depends(get_current_user)):
    db = get_db()
    session = db.execute(
        "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()
    if not session:
        raise HTTPException(404, "Session not found")
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
        (session_id, req.content, now),
    )
    db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
    )
    db.commit()
    return {"ok": True}
