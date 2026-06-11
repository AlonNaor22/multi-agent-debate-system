import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import debates, websocket
from config import CORS_ORIGINS
from messages import API_KEY_MISSING

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown: require an API key, then create the DB schema.

    Refusing to start without ``ANTHROPIC_API_KEY`` fails fast and loud rather
    than letting the first debate die mid-stream. ``init_db`` is idempotent, so
    creating the table on every boot is safe.
    """
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(API_KEY_MISSING, file=sys.stderr)
        sys.exit(1)
    # Create the debates table on startup if it isn't there yet (idempotent).
    from api.db import init_db
    init_db()
    logger.info("API startup complete")
    yield
    logger.info("API shutdown")


app = FastAPI(
    lifespan=lifespan,
    title="Multi-Agent Debate System API",
    description="API for running AI-powered debates between multiple agents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    # Single source of truth in config.py; override with the CORS_ORIGINS env var
    # (comma-separated). Was previously read here with a different default.
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(debates.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Service banner pointing at the interactive API docs."""
    return {"message": "Multi-Agent Debate System API", "docs": "/docs"}


@app.get("/health")
async def health():
    """Liveness probe (used by the Docker healthcheck)."""
    return {"status": "healthy"}
