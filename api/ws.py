import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.agent_runner import AgentRunner

router = APIRouter()


@router.websocket("/ws/agent/{session_id}")
async def agent_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    runner = None
    try:
        async def send_to_ws(msg):
            await websocket.send_json(msg)

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "run":
                prompt = msg.get("prompt", "")
                runner = AgentRunner(session_id, send_to_ws)
                asyncio.create_task(runner.run(prompt))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except RuntimeError:
            pass
