from __future__ import annotations

## uvicorn app.main:app --reload

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.env import load_env_file

load_env_file()

from app.core.constants import CONTRACT_VERSION
from app.core.exceptions import request_validation_exception_handler
from app.routers.auth import router as auth_router
from app.routers.github import router as github_router
from app.routers.projects import router as projects_router
from app.routers.sessions import router as sessions_router
from app.routers.uploads import router as uploads_router

app = FastAPI(title="Sketch-to-Cloud API", version=CONTRACT_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(github_router)
app.include_router(projects_router)
app.include_router(sessions_router)
app.include_router(uploads_router)
