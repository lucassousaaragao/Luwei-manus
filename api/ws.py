import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.agent_runner import AgentRunner

router = APIRouter()


@router.websocket("/ws/agent/{session_id}")
async def agent_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _task: asyncio.Task | None = None
    try:
        async def send_to_ws(msg):
            await websocket.send_json(msg)

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "run":
                if _task is not None and not _task.done():
                    _task.cancel()
                prompt = msg.get("prompt", "")
                runner = AgentRunner(session_id, send_to_ws)
                _task = asyncio.create_task(runner.run(prompt))
    except WebSocketDisconnect:
        if _task is not None and not _task.done():
            _task.cancel()
    except Exception as e:
        if _task is not None and not _task.done():
            _task.cancel()
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except RuntimeError:
            pass
