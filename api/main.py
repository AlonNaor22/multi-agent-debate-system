import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import debates, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. Add it to your .env file.",
            file=sys.stderr,
        )
        sys.exit(1)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Multi-Agent Debate System API",
    description="API for running AI-powered debates between multiple agents",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(debates.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {"message": "Multi-Agent Debate System API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
