import asyncio
import json
import uuid
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

from sqlalchemy import select, desc
from api.db_models import (
    Task, TaskStep, TaskRun, Artifact, Approval,
    TaskStatus, TaskStepStatus, TaskRunStatus, ApprovalStatus
)
from api.database_async import get_db_context


# Registry of running tasks (in-memory)
_running_tasks: Dict[str, asyncio.Task] = {}
# Registry of task progress callbacks (for WebSocket)
_task_subscribers: Dict[str, List[Callable]] = {}


class TaskEvent:
    def __init__(self, task_id: str, type: str, data: Any):
        self.task_id = task_id
        self.type = type
        self.data = data

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "type": self.type,
            "data": self.data,
        }


async def emit_event(event: TaskEvent):
    """Notify all subscribers of a task event"""
    if event.task_id in _task_subscribers:
        for callback in _task_subscribers[event.task_id]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                print(f"Subscriber error: {e}")


def subscribe_task(task_id: str, callback: Callable):
    """Subscribe to task events"""
    if task_id not in _task_subscribers:
        _task_subscribers[task_id] = []
    _task_subscribers[task_id].append(callback)


def unsubscribe_task(task_id: str, callback: Callable):
    """Unsubscribe from task events"""
    if task_id in _task_subscribers and callback in _task_subscribers[task_id]:
        _task_subscribers[task_id].remove(callback)
        if not _task_subscribers[task_id]:
            del _task_subscribers[task_id]


def is_task_running(task_id: str) -> bool:
    """Check if a task is currently running"""
    return task_id in _running_tasks and not _running_tasks[task_id].done()


def cancel_task(task_id: str) -> bool:
    """Cancel a running task"""
    if task_id in _running_tasks and not _running_tasks[task_id].done():
        _running_tasks[task_id].cancel()
        return True
    return False


async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status from database"""
    async with get_db_context() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status.value if task.status else None,
            "progress": task.progress,
            "error": task.error,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }


async def create_task(
    organization_id: str,
    workspace_id: Optional[str],
    session_id: Optional[str],
    created_by: int,
    title: str,
    description: str = "",
    input_data: Optional[Dict] = None,
    config: Optional[Dict] = None,
) -> str:
    """Create a new task in the database"""
    task_id = str(uuid.uuid4())
    async with get_db_context() as db:
        task = Task(
            id=task_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            session_id=session_id,
            created_by=created_by,
            title=title,
            description=description,
            input_data=json.dumps(input_data) if input_data else None,
            config=json.dumps(config) if config else None,
            status=TaskStatus.PENDING,
        )
        db.add(task)
        await db.commit()
    return task_id


async def start_task_async(task_id: str, executor: Callable):
    """Start a task asynchronously in the background"""
    run_id = str(uuid.uuid4())
    async with get_db_context() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        run = TaskRun(
            id=run_id,
            task_id=task_id,
            status=TaskRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            logs=json.dumps([{"type": "info", "message": "Task run started"}]),
        )
        db.add(run)
        await db.commit()

    # Create background task
    async_task = asyncio.create_task(_run_task(task_id, executor))
    _running_tasks[task_id] = async_task


async def _run_task(task_id: str, executor: Callable):
    """Run task with status tracking"""
    try:
        result = await executor(task_id, emit_event)
        # Mark as completed
        async with get_db_context() as db:
            result_db = await db.execute(select(Task).where(Task.id == task_id))
            task = result_db.scalar_one_or_none()
            if task:
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.completed_at = datetime.now(timezone.utc)
                if result:
                    task.result = json.dumps(result) if not isinstance(result, str) else result
                await db.commit()
            # Update latest run
            run_result = await db.execute(select(TaskRun).where(TaskRun.task_id == task_id).order_by(desc(TaskRun.created_at)).limit(1))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = TaskRunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
        await emit_event(TaskEvent(task_id, "status", {"status": "completed", "progress": 100}))
    except asyncio.CancelledError:
        async with get_db_context() as db:
            result_db = await db.execute(select(Task).where(Task.id == task_id))
            task = result_db.scalar_one_or_none()
            if task:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
            run_result = await db.execute(select(TaskRun).where(TaskRun.task_id == task_id).order_by(desc(TaskRun.created_at)).limit(1))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = TaskRunStatus.CANCELLED
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
        await emit_event(TaskEvent(task_id, "status", {"status": "cancelled"}))
    except Exception as e:
        tb = traceback.format_exc()
        async with get_db_context() as db:
            result_db = await db.execute(select(Task).where(Task.id == task_id))
            task = result_db.scalar_one_or_none()
            if task:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
            run_result = await db.execute(select(TaskRun).where(TaskRun.task_id == task_id).order_by(desc(TaskRun.created_at)).limit(1))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = TaskRunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                run.error = str(e)
                await db.commit()
        await emit_event(TaskEvent(task_id, "error", {"error": str(e), "traceback": tb}))
    finally:
        if task_id in _running_tasks:
            del _running_tasks[task_id]


async def update_task_progress(task_id: str, progress: int, status: Optional[TaskStatus] = None):
    """Update task progress"""
    async with get_db_context() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.progress = max(0, min(100, progress))
            if status:
                task.status = status
            await db.commit()
    await emit_event(TaskEvent(task_id, "progress", {"progress": progress, "status": status.value if status else None}))


async def add_task_log(task_id: str, log_entry: Dict[str, Any]):
    """Append a log entry to the task's current run"""
    async with get_db_context() as db:
        result = await db.execute(
            select(TaskRun).where(TaskRun.task_id == task_id).order_by(desc(TaskRun.created_at)).limit(1)
        )
        run = result.scalar_one_or_none()
        if run:
            logs = json.loads(run.logs) if run.logs else []
            logs.append(log_entry)
            run.logs = json.dumps(logs)
            await db.commit()
    await emit_event(TaskEvent(task_id, "log", log_entry))


async def create_step(
    task_id: str,
    step_index: int,
    title: str,
    agent_type: Optional[str] = None,
    description: str = "",
) -> str:
    """Create a task step"""
    step_id = str(uuid.uuid4())
    async with get_db_context() as db:
        step = TaskStep(
            id=step_id,
            task_id=task_id,
            step_index=step_index,
            title=title,
            description=description,
            agent_type=agent_type,
            status=TaskStepStatus.PENDING,
        )
        db.add(step)
        await db.commit()
    return step_id


async def update_step_status(step_id: str, status: TaskStepStatus, output: Optional[Dict] = None, error: Optional[str] = None):
    """Update step status"""
    async with get_db_context() as db:
        result = await db.execute(select(TaskStep).where(TaskStep.id == step_id))
        step = result.scalar_one_or_none()
        if step:
            step.status = status
            if status == TaskStepStatus.RUNNING:
                step.started_at = datetime.now(timezone.utc)
            elif status in (TaskStepStatus.COMPLETED, TaskStepStatus.FAILED, TaskStepStatus.SKIPPED):
                step.completed_at = datetime.now(timezone.utc)
            if output:
                step.output_data = json.dumps(output)
            if error:
                step.error = error
            await db.commit()
    await emit_event(TaskEvent(step_id, "step_status", {"status": status.value, "output": output, "error": error}))


async def create_artifact(
    task_id: str,
    name: str,
    type: str,
    mime_type: str,
    size: int,
    storage_path: str,
    storage_provider: str = "local",
    step_id: Optional[str] = None,
    is_final: bool = False,
    metadata: Optional[Dict] = None,
) -> str:
    """Create artifact record"""
    artifact_id = str(uuid.uuid4())
    async with get_db_context() as db:
        artifact = Artifact(
            id=artifact_id,
            task_id=task_id,
            step_id=step_id,
            created_by=0,  # system
            name=name,
            type=type,
            mime_type=mime_type,
            size=size,
            storage_path=storage_path,
            storage_provider=storage_provider,
            is_final=is_final,
            metadata_=json.dumps(metadata) if metadata else None,
        )
        db.add(artifact)
        await db.commit()
    await emit_event(TaskEvent(task_id, "artifact", {"id": artifact_id, "name": name, "type": type, "size": size}))
    return artifact_id


async def list_user_tasks(
    user_id: int,
    org_id: str,
    workspace_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List tasks for a user"""
    async with get_db_context() as db:
        query = select(Task).where(
            Task.organization_id == org_id,
            Task.created_by == user_id,
        ).order_by(desc(Task.created_at)).limit(limit)
        if workspace_id:
            query = query.where(Task.workspace_id == workspace_id)
        if status:
            query = query.where(Task.status == status)
        result = await db.execute(query)
        tasks = result.scalars().all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status.value if t.status else None,
                "progress": t.progress,
                "workspace_id": t.workspace_id,
                "session_id": t.session_id,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "error": t.error,
            }
            for t in tasks
        ]


async def get_task_detail(task_id: str, user_id: int, org_id: str) -> Optional[Dict[str, Any]]:
    """Get full task detail with steps and artifacts"""
    async with get_db_context() as db:
        result = await db.execute(select(Task).where(Task.id == task_id, Task.organization_id == org_id, Task.created_by == user_id))
        task = result.scalar_one_or_none()
        if not task:
            return None
        # Steps
        steps_result = await db.execute(
            select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.step_index)
        )
        steps = steps_result.scalars().all()
        # Artifacts
        artifacts_result = await db.execute(
            select(Artifact).where(Artifact.task_id == task_id).order_by(Artifact.created_at)
        )
        artifacts = artifacts_result.scalars().all()
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value if task.status else None,
            "progress": task.progress,
            "config": json.loads(task.config) if task.config else None,
            "input_data": json.loads(task.input_data) if task.input_data else None,
            "result": json.loads(task.result) if task.result and task.result.startswith("{") else task.result,
            "error": task.error,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "steps": [
                {
                    "id": s.id,
                    "index": s.step_index,
                    "title": s.title,
                    "description": s.description,
                    "agent_type": s.agent_type,
                    "status": s.status.value if s.status else None,
                    "output": json.loads(s.output_data) if s.output_data else None,
                    "error": s.error,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in steps
            ],
            "artifacts": [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.type,
                    "mime_type": a.mime_type,
                    "size": a.size,
                    "is_final": a.is_final,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in artifacts
            ],
        }


async def resume_pending_tasks():
    """Resume any tasks that were running when the server restarted"""
    async with get_db_context() as db:
        result = await db.execute(
            select(Task).where(Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING]))
        )
        tasks = result.scalars().all()
        for task in tasks:
            # Mark as failed since we lost the in-memory state
            task.status = TaskStatus.FAILED
            task.error = "Server restarted, task interrupted. Please retry."
        await db.commit()
        return len(tasks)