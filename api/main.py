from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.database import init_db

app = FastAPI(title="Luwei Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


from api.auth import router as auth_router
from api.chat import router as chat_router
from api.ws import router as ws_router
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ws_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
