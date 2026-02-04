from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import debates, websocket

app = FastAPI(
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
