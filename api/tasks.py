import json
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select

from api.database_async import get_db, get_db_context
from api.auth import get_current_user
from api.permissions import verify_workspace_access
from api.db_models import Task, TaskStatus
from api.services.task_service import (
    create_task, start_task_async, cancel_task, is_task_running,
    list_user_tasks, get_task_detail, resume_pending_tasks
)
from api.services.task_executor import execute_chat_task, execute_research_task

router = APIRouter(prefix="/api/tasks")


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    prompt: str = ""
    model: str = "default"
    mode: str = "chat"
    speed: str = "medium"
    workspace_id: Optional[str] = None
    session_id: Optional[str] = None
    type: str = "chat"  # chat, research, planning


@router.post("")
async def create_new_task(
    req: CreateTaskRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Create and start a new task"""
    if req.workspace_id:
        has_access = await verify_workspace_access(db, req.workspace_id, user["id"])
        if not has_access:
            raise HTTPException(403, "No access to workspace")

    config = {
        "model": req.model,
        "mode": req.mode,
        "speed": req.speed,
    }
    input_data = {
        "prompt": req.prompt or req.description or req.title,
        "type": req.type,
    }

    task_id = await create_task(
        organization_id=user["org_id"],
        workspace_id=req.workspace_id,
        session_id=req.session_id,
        created_by=user["id"],
        title=req.title,
        description=req.description,
        input_data=input_data,
        config=config,
    )

    # Choose executor
    executor = execute_chat_task if req.type == "chat" else execute_research_task
    await start_task_async(task_id, executor)

    return {"id": task_id, "status": "pending"}


@router.get("")
async def list_tasks(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List tasks for the current user"""
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(400, "Invalid status")
    return await list_user_tasks(user["id"], user["org_id"], workspace_id, status_enum)


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    user=Depends(get_current_user),
):
    """Get full task detail with steps and artifacts"""
    detail = await get_task_detail(task_id, user["id"], user["org_id"])
    if not detail:
        raise HTTPException(404, "Task not found")
    detail["is_running"] = is_task_running(task_id)
    return detail


@router.post("/{task_id}/cancel")
async def cancel_task_endpoint(
    task_id: str,
    user=Depends(get_current_user),
):
    """Cancel a running task"""
    # Verify ownership
    detail = await get_task_detail(task_id, user["id"], user["org_id"])
    if not detail:
        raise HTTPException(404, "Task not found")
    if not detail.get("is_running"):
        raise HTTPException(400, "Task is not running")
    cancelled = cancel_task(task_id)
    return {"ok": True, "cancelled": cancelled}


@router.post("/resume-pending")
async def resume_tasks_endpoint(
    user=Depends(get_current_user),
):
    """Mark all pending tasks as failed (called on server startup)"""
    n = await resume_pending_tasks()
    return {"resumed": n}


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    user=Depends(get_current_user),
):
    """Retry a failed or cancelled task"""
    async with get_db_context() as db:
        result = await db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.organization_id == user["org_id"],
                Task.created_by == user["id"]
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(404, "Task not found")
        if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise HTTPException(400, "Only failed or cancelled tasks can be retried")
        task.status = TaskStatus.PENDING
        task.error = None
        await db.commit()

    # Read input from stored data
    config = json.loads(task.config) if task.config else {}
    executor = execute_chat_task
    await start_task_async(task_id, executor)
    return {"id": task_id, "status": "pending"}
