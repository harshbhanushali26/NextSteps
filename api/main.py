"""
NextSteps API — main.py
FastAPI app: CORS setup + all 5 phase routers mounted.
Run: uvicorn api.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api.routers import parse, match, apply, interview #, tutor

app = FastAPI(
    title="NextSteps API",
    description="AI career automation — CV parsing, skill matching, resume tailoring, interview simulation, tutoring.",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Add your Vercel URL here once deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",      # VS Code Live Server
        "http://127.0.0.1:5500",      # same, explicit IP
        "http://localhost:5173",       # Vite dev server
        "http://localhost:3000",       # fallback
        "https://nextsteps.vercel.app",  # production — update with real URL
        "http://127.0.0.1:5501", 
        "http://localhost:5501",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(parse.router,     prefix="/parse",     tags=["Phase 1 — Parse"])
app.include_router(match.router,     prefix="/match",     tags=["Phase 2 — Match"])
app.include_router(apply.router,     prefix="/apply",     tags=["Phase 3 — Apply"])
app.include_router(interview.router, prefix="/interview", tags=["Phase 4 — Interview"])
# app.include_router(tutor.router,     prefix="/tutor",     tags=["Phase 5 — Tutor"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "NextSteps API v1"}