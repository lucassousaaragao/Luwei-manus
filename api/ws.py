import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from api.auth import decode_token
from api.services.task_service import (
    create_task, start_task_async, subscribe_task, unsubscribe_task,
    is_task_running, cancel_task, TaskEvent
)
from api.services.task_executor import execute_chat_task, execute_research_task

router = APIRouter()


async def _get_user_from_token(token: str):
    if not token:
        return None
    try:
        return decode_token(token)
    except Exception:
        return None


@router.websocket("/ws/agent/{session_id}")
async def agent_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(default=""),
):
    user = await _get_user_from_token(token)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    current_task_id: str | None = None

    async def send_to_ws(event):
        try:
            await websocket.send_json({
                "type": event.type,
                "task_id": event.task_id,
                "data": event.data,
            })
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "run":
                if current_task_id and is_task_running(current_task_id):
                    cancel_task(current_task_id)
                    unsubscribe_task(current_task_id, send_to_ws)

                prompt = msg.get("prompt", "")
                model = msg.get("model", "default")
                mode = msg.get("mode", "chat")
                speed = msg.get("speed", "medium")
                task_type = msg.get("task_type", "chat")

                # Create task
                task_id = await create_task(
                    organization_id=user["org_id"],
                    workspace_id=None,  # Can be extended if needed
                    session_id=session_id,
                    created_by=user["id"],
                    title=prompt[:60] or "Task",
                    description=prompt,
                    input_data={"prompt": prompt, "type": task_type},
                    config={"model": model, "mode": mode, "speed": speed},
                )
                current_task_id = task_id

                # Subscribe and send initial event
                subscribe_task(task_id, send_to_ws)
                await send_to_ws(TaskEvent(task_id, "status", {"status": "pending", "task_id": task_id}))

                # Start task
                executor = execute_chat_task if task_type == "chat" else execute_research_task
                await start_task_async(task_id, executor)
                await send_to_ws(TaskEvent(task_id, "status", {"status": "running", "task_id": task_id}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except RuntimeError:
            pass
    finally:
        if current_task_id:
            # Do not cancel the task on disconnect; let it run in the background
            unsubscribe_task(current_task_id, send_to_ws)
