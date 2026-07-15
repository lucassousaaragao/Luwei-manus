# api/models.py
import tomllib
from pathlib import Path
from fastapi import APIRouter, Depends
from api.auth import get_current_user

router = APIRouter(prefix="/api/models")

MODELS_CATALOG = {
    "default": {"name": "Padrão (DeepSeek)", "provider": "config", "models": ["deepseek-chat"]},
    "deepseek": {"name": "DeepSeek", "provider": "deepseek", "models": ["deepseek-chat", "deepseek-reasoner"]},
    "opencode": {"name": "OpenCode Go", "provider": "opencode", "models": ["claude-sonnet-4-20250514", "claude-haiku-4-20250514"]},
    "kimi": {"name": "KIMI (Moonshot)", "provider": "kimi", "models": ["moonshot-v1-8k", "moonshot-v1-32k"]},
    "zai": {"name": "GLM (Z.AI)", "provider": "zai", "models": ["glm-4", "glm-4-plus", "glm-4v"]},
    "openai": {"name": "OpenAI", "provider": "openai", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]},
    "gemini": {"name": "Google Gemini", "provider": "gemini", "models": ["gemini-2.0-flash", "gemini-2.0-pro"]},
}

@router.get("")
def list_models(user=Depends(get_current_user)):
    return MODELS_CATALOG

@router.get("/providers")
def list_providers(user=Depends(get_current_user)):
    config_path = Path(__file__).parent.parent / "config" / "config.toml"
    providers = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        llm_config = data.get("llm", {})
        for key, val in llm_config.items():
            if isinstance(val, dict):
                providers[key] = {
                    "model": val.get("model", ""),
                    "base_url": val.get("base_url", ""),
                }
    return providers
