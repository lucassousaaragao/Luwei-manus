import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.database_async import init_db
from api.auth import router as auth_router
from api.chat import router as chat_router
from api.ws import router as ws_router
from api.models import router as models_router
from api.workspaces import router as workspaces_router
from api.mcp_routes import router as mcp_router
from api.tasks import router as tasks_router
from api.services.task_service import resume_pending_tasks

app = FastAPI(title="Luwei Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()
    # Mark interrupted tasks as failed
    await resume_pending_tasks()

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(models_router)
app.include_router(workspaces_router)
app.include_router(mcp_router)
app.include_router(tasks_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))