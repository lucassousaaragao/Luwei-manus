import asyncio
from app.agent.manus import Manus
from app.logger import logger


class AgentRunner:
    def __init__(self, session_id: str, callback):
        self.session_id = session_id
        self.callback = callback

    async def run(self, prompt: str):
        agent = None
        try:
            await self.callback({"type": "status", "data": "starting"})
            agent = await Manus.create()
            await self.callback({"type": "status", "data": "thinking"})
            result = await agent.run(prompt)
            await self.callback({"type": "result", "data": result})
            await self.callback({"type": "status", "data": "done"})
        except Exception as e:
            logger.error(f"AgentRunner error for session {self.session_id}: {e}")
            await self.callback({"type": "error", "data": str(e)})
        finally:
            if agent is not None:
                try:
                    await agent.cleanup()
                except Exception as e:
                    logger.error(f"Cleanup error for session {self.session_id}: {e}")
