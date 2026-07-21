"""Dream Studio platform backend.

One backend, every game. Run locally:
    uvicorn app.main:app --reload --port 8000

Production (Coolify): build from Dockerfile, set JWT_SECRET and DATABASE_URL,
health check /v1/health. Set SEED_ON_START=1 to (re)apply seed.py's game
catalog + remote configs on boot — seeding is config-as-code and idempotent.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routes import router

app = FastAPI(title="Dream Studio Platform", version="0.2.0")
app.include_router(router)

# Godot native clients don't need CORS, but future HTML5/web builds do.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    if os.environ.get("SEED_ON_START") == "1":
        import seed  # repo-root module; available in the Docker image

        seed.main()
