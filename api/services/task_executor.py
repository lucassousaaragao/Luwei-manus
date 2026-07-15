import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from api.services.task_service import (
    update_task_progress, add_task_log, create_step,
    update_step_status, create_artifact
)
from api.db_models import TaskStepStatus


def _build_llm_for_model(model_key: str, task_id: str):
    """Build an LLM instance for the requested model/provider."""
    from app.llm import LLM
    from app.config import LLMSettings, config

    provider = "default"
    model_name = None
    if model_key and "/" in model_key:
        provider, model_name = model_key.split("/", 1)
    elif model_key and model_key in config.llm:
        provider = model_key

    raw = config.llm.get(provider, config.llm["default"])
    settings = LLMSettings(
        model=model_name or raw.model,
        base_url=raw.base_url,
        api_key=raw.api_key,
        max_tokens=raw.max_tokens,
        max_input_tokens=raw.max_input_tokens,
        temperature=raw.temperature,
        api_type=raw.api_type,
        api_version=raw.api_version,
    )
    config_name = f"task_{task_id}_{provider}_{model_name or 'default'}"
    # LLM constructor expects llm_config as a dict of config_name -> LLMSettings
    return LLM(config_name=config_name, llm_config={config_name: settings, "default": settings})


async def execute_chat_task(task_id: str, emit_event) -> Dict[str, Any]:
    """
    Execute a chat task using OpenManus Manus agent.
    This is the main executor for Fase 3.
    """
    from api.database_async import get_db_context
    from sqlalchemy import select
    from api.db_models import Task, Message, Session

    # Load task
    async with get_db_context() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return {"error": "Task not found"}
        input_data = json.loads(task.input_data) if task.input_data else {}
        config = json.loads(task.config) if task.config else {}
        prompt = input_data.get("prompt", task.description or task.title)
        model = config.get("model", "default")
        mode = config.get("mode", "chat")
        speed = config.get("speed", "medium")
        session_id = task.session_id

    await update_task_progress(task_id, 5)
    await add_task_log(task_id, {"type": "info", "message": f"Starting task: {task.title}"})

    # Create a step for the chat
    step_id = await create_step(
        task_id=task_id,
        step_index=0,
        title="Executar com agente Manus",
        agent_type="manus",
        description=f"Process: {prompt[:100]}"
    )
    await update_step_status(step_id, TaskStepStatus.RUNNING)

    try:
        from app.agent.manus import Manus

        await add_task_log(task_id, {"type": "info", "message": f"Initializing Manus agent with model {model}"})
        await update_task_progress(task_id, 15)

        # Create agent with selected LLM
        llm = _build_llm_for_model(model, task_id)
        agent = await Manus.create(llm=llm)
        await add_task_log(task_id, {"type": "info", "message": "Agent initialized"})
        await update_task_progress(task_id, 25)

        await update_step_status(step_id, TaskStepStatus.RUNNING)
        await add_task_log(task_id, {"type": "info", "message": "Running agent..."})

        # Run agent
        result_text = await agent.run(prompt)
        await update_task_progress(task_id, 80)

        # Save assistant message to session
        if session_id:
            async with get_db_context() as db:
                msg = Message(
                    session_id=session_id,
                    role="assistant",
                    content=result_text or "(no output)",
                    created_at=datetime.now(timezone.utc)
                )
                db.add(msg)
                await db.commit()

        await update_task_progress(task_id, 90)
        await add_task_log(task_id, {"type": "info", "message": "Task completed"})

        # Cleanup
        try:
            await agent.cleanup()
        except Exception:
            pass

        await update_step_status(step_id, TaskStepStatus.COMPLETED, output={"text": result_text})
        return {"text": result_text, "status": "completed"}

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        await add_task_log(task_id, {"type": "error", "message": str(e), "traceback": tb})
        await update_step_status(step_id, TaskStepStatus.FAILED, error=str(e))
        raise


async def execute_research_task(task_id: str, emit_event) -> Dict[str, Any]:
    """Execute a research task (planned multi-step)"""
    await update_task_progress(task_id, 50)
    await add_task_log(task_id, {"type": "info", "message": "Research task executed (Fase 3 simple executor)"})
    return {"status": "completed", "note": "Use execute_chat_task for now"}