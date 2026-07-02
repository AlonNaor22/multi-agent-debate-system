import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import debates, websocket
from api.services.debate_service import debate_service
from config import CORS_ORIGINS, AVAILABLE_STYLES
from messages import API_KEY_MISSING, STYLE_CONFIG_INVALID
from src.prompts import validate_styles, StyleConfigError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown: require an API key, validate the style config,
    create the DB schema, and run the background session sweeper.

    Refusing to start without ``ANTHROPIC_API_KEY`` fails fast and loud rather
    than letting the first debate die mid-stream. Likewise, validating that
    every ``AVAILABLE_STYLES`` entry has a matching ``PRO_STYLES``/
    ``CON_STYLES`` prompt here means a misconfigured env override is rejected
    at boot instead of raising deep inside a live debate. ``init_db`` is
    idempotent, so creating the table on every boot is safe. The sweeper task
    evicts orphan debate sessions (created via POST but never driven by a
    WebSocket) once they exceed ``SESSION_TTL_SECONDS``; it's cancelled
    cleanly on shutdown.
    """
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(API_KEY_MISSING, file=sys.stderr)
        sys.exit(1)
    try:
        validate_styles(AVAILABLE_STYLES)
    except StyleConfigError as error:
        print(STYLE_CONFIG_INVALID.format(error=error), file=sys.stderr)
        sys.exit(1)
    # Create the debates table on startup if it isn't there yet (idempotent).
    from api.db import init_db
    init_db()
    sweeper_task = asyncio.create_task(debate_service.run_session_sweeper())
    logger.info("API startup complete")
    try:
        yield
    finally:
        sweeper_task.cancel()
        with suppress(asyncio.CancelledError):
            await sweeper_task
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
