<div align="center">

# NextSteps

### Your AI-powered career co-pilot

**Drop your CV + a job URL. Get a tailored resume, cover letter, mock interview, and skill coaching — in under 2 minutes.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-gpt--oss--120b-F55036?style=flat-square)](https://groq.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-E8A430?style=flat-square)](https://trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

[**Live Demo →**](https://nextsteps.vercel.app) · [**API Docs →**](https://nextsteps.railway.app/docs) · [**Local Setup ↓**](#quick-start)

</div>

---

## The Problem

Job hunting is broken — and everyone who's done it knows exactly how.

You find a promising role. You spend **2–3 hours** manually tailoring your resume to match the keywords. Another hour writing a cover letter that doesn't sound generic. Then you prep for interviews by guessing what they might ask, study topics you're unsure about, and send your application into the void hoping something sticks.

Multiply that by 20 applications. That's **60+ hours of mechanical, repetitive work** that should take 10 minutes.

The tools that exist today don't actually solve this. Resume builders give you pretty templates. Job boards give you more listings to scroll. AI chatbots give you generic output you still have to rewrite. None of them understand *your* CV, *this* specific job, and *the gap between the two*.

---

## What NextSteps Does

NextSteps is a multi-phase AI agent that automates the entire application pipeline — not just one piece of it.

```
You provide:  CV (PDF) + Job URL (or paste JD text)
              ↓
NextSteps:    Parses both → Finds your skill gaps → Rewrites your resume
              → Writes a company-aware cover letter → Runs a mock interview
              → Teaches you what you're missing
              ↓
You get:      A tailored application package + interview readiness
              in under 2 minutes
```

**It works because it understands context at every step.** Your CV isn't just text — it's parsed into a structured profile. The JD isn't just a page scrape — it's extracted into required vs. preferred skills. Every downstream step (resume, cover letter, interview questions) is grounded in the actual gap between *you* and *this role*.

---

## Why Not Just Use ChatGPT?

Fair question. Here's the difference:

| | ChatGPT / Generic AI | NextSteps |
|---|---|---|
| **Input** | You paste text manually | Uploads CV PDF, scrapes JD automatically |
| **Context** | Single conversation turn | Full structured profile + JD + company research |
| **Resume tailoring** | Rewrites whatever you paste | Rewrites *specific bullets* against *specific JD requirements* |
| **Cover letter** | Generic template | Grounded in real company context via Tavily |
| **Interview prep** | Generic questions | Questions weighted toward *your* gap skills, scored against *your* CV |
| **Skill gaps** | "You might want to learn Docker" | Cosine similarity + RAG retrieval, classified as STRONG / WEAK / GAP |
| **Workflow** | You do the work | End-to-end pipeline, one upload |

The gap isn't intelligence — it's **structured context**. NextSteps knows your profile, the job, the company, and exactly where you fall short. Generic AI doesn't.

---

## How It Works

NextSteps is a 4-phase pipeline (Phase 5 coming soon):

### Phase 1 — Parse & Extract
Upload your CV PDF and provide a job URL (or paste JD text directly if the site blocks scraping). Tavily fetches the full JD. `pymupdf4llm` reads and structures your CV. Groq extracts both into validated Pydantic models. Company culture is enriched with a separate Tavily search.

### Phase 2 — Skill Gap Analysis
Your CV is chunked into sections and embedded into ChromaDB using `all-MiniLM-L6-v2`. Cosine similarity is computed for each JD requirement. A two-signal classifier (similarity score + chunk-hit depth) categorises every skill as **STRONG**, **WEAK**, or **GAP** — distinguishing between skills you've demonstrated deeply and ones you've only mentioned in passing. Overall match percentage is calculated from required skills only.

### Phase 3 — Application Package
Groq rewrites your resume bullets to mirror JD keywords without fabricating experience. A company-aware cover letter is generated using the Tavily company context and streams live via SSE. Both outputs are editable, copyable, and downloadable directly from the dashboard.

### Phase 4 — Mock Interview
10 role-specific questions are generated from your gap report, weighted toward weak skills so you practice where it matters most. Each answer is scored on 3 axes — relevance, depth, and clarity — grounded against your actual CV via RAG retrieval. Exit anytime for a partial scorecard.

### Phase 5 — AI Tutor *(coming soon)*
Socratic skill tutor that teaches each gap skill through guided questions, not lectures. Includes a code coach with generated practice problems and 4-axis code review. Tavily enriches every topic with real examples and current documentation.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **LLM** | Groq `openai/gpt-oss-120b` | Best-in-class tool calling reliability + fast inference |
| **Web Intel** | Tavily | Extracts clean JD text from any career page; company research |
| **Vector DB** | ChromaDB | Persistent, local, no API cost — cosine similarity at session scale |
| **Embeddings** | SentenceTransformers `all-MiniLM-L6-v2` | Fast, accurate skill-level semantic matching |
| **Backend** | FastAPI + Uvicorn | Thin wrapper over agent functions; streaming SSE support |
| **Validation** | Pydantic v2 `extra='forbid'` | LLM hallucinations caught at the schema boundary |
| **PDF Parsing** | pymupdf4llm | Markdown-preserving extraction; retains CV structure for better LLM accuracy |
| **Frontend** | Vanilla HTML / CSS / JS | Zero build step; instant deploy; no framework overhead |
| **Deployment** | Railway + Vercel | Free tier; GitHub-connected; auto-deploy on push |

---

## Quick Start

### Prerequisites
- Python 3.12+
- `uv` (recommended) or `pip`

### 1. Clone & Install

```bash
git clone https://github.com/harshbhanu26/NextSteps.git
cd NextSteps

# Option A — uv (recommended)
uv sync

# Option B — pip
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
# .env (create in project root)
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

Get your keys free: [Groq Console](https://console.groq.com) · [Tavily Dashboard](https://app.tavily.com)

### 3. Run

```bash
python main.py
# or: uvicorn api.main:app --reload
```

Open `frontend/index.html` in your browser. API docs at `http://localhost:8000/docs`.

---

## Supported Job Sites

NextSteps uses Tavily Extract to scrape job descriptions. Some sites block automated access.

**Works ✅** — Lever, Greenhouse, Workable, Ashby, BambooHR, SmartRecruiters, company career pages

**Blocked ❌** — LinkedIn, Indeed, Naukri, Glassdoor, Monster, Shine

> **Paste JD fallback:** For blocked sites, copy the job description text and paste it directly via the "Paste JD" option on the dashboard. This sends `raw_jd_text` to `/parse` and skips Tavily entirely — the rest of the pipeline runs identically.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/parse` | CV PDF + job URL → structured profile + JD + company context |
| `POST` | `/match` | Profile + JD → skill gap report |
| `POST` | `/apply` | Gap report → tailored bullets + cover letter |
| `POST` | `/apply/stream` | Streaming cover letter (SSE) |
| `POST` | `/interview/start` | JD + gap report → 10 interview questions |
| `POST` | `/interview/answer` | Score one answer, RAG-grounded |
| `POST` | `/interview/summary` | All scored answers → session report |

`POST /parse` accepts `multipart/form-data`: `cv` (PDF), `job_url` (string), `raw_jd_text` (optional), `company_name` (optional).

---

## Project Structure

```
NextSteps/
├── agents/                     # One agent per pipeline phase
│   ├── cv_parser.py            # PDF → CandidateProfile
│   ├── jd_scraper.py           # URL → JobDescription (Tavily + bs4 fallback)
│   ├── company_research.py     # Company → context string (Tavily)
│   ├── skill_matcher.py        # Skills → SkillGapReport
│   ├── resume_tailor.py        # Bullets → tailored bullets
│   ├── cover_letter.py         # Cover letter with streaming
│   └── interviewer.py          # Questions + RAG scoring + summary
├── api/
│   ├── main.py                 # FastAPI app, CORS, router registration
│   └── routers/                # One router per phase (parse/match/apply/interview/tutor)
├── models/
│   └── schemas.py              # All Pydantic v2 models
├── prompts/                    # LLM system prompts (one file per agent)
├── rag/
│   ├── embedder.py             # SentenceTransformer singleton
│   ├── store.py                # ChromaDB operations
│   └── cv_loader.py            # CV chunking + embedding
├── utils/
│   ├── llm.py                  # Groq client + JSON parsing helpers
│   └── pii.py                  # PII stripping before LLM calls
├── frontend/
│   ├── index.html              # Landing page
│   ├── dashboard.html          # App — all 4 phases as tabs
│   ├── docs.html               # Local dev docs
│   ├── css/                    # design.css · components.css · pages.css · sidebar.css
│   ├── js/                     # state.js · navigation.js · helpers.js · phase1–4.js
│   └── assets/logo.png
├── main.py                     # Entry point
├── pyproject.toml
├── Procfile                    # Railway: uvicorn api.main:app --host 0.0.0.0 --port $PORT
└── .env
```

---

## Design Decisions

**PII-first by default.** Email is extracted locally. Phone numbers and addresses are stripped before any text reaches the LLM. Your personal data stays on your machine as much as possible.

**Graceful degradation at every step.** Tavily fails → `requests + BeautifulSoup` fallback scrapes the JD silently. Fallback fails → user pastes JD directly. The pipeline never hard-stops on a network error.

**Two-store RAG architecture.** Skills and CV text chunks live in separate ChromaDB collections per job session (`cv_skills_{job_id}` and `cv_chunks_{job_id}`). Skills collection powers Phase 2 matching; chunks collection powers Phase 4 interview scoring. `delete_session()` is called at session start to prevent cross-job contamination.

**Section-aware chunking.** CV text is split on markdown headers before character chunking. This preserves semantic boundaries between "Experience", "Education", and "Skills" sections — giving the retriever cleaner, more meaningful chunks.

**Schema as a correctness layer.** `extra='forbid'` on every Pydantic model means the moment an LLM returns a field it wasn't asked for, the pipeline throws — not silently passes bad data downstream.

**Deterministic session IDs.** `md5(url)[:12]` means re-scraping the same job URL is idempotent. Running Phase 1 twice on the same URL doesn't create duplicate ChromaDB collections.

---

## Deployment

**Backend → Railway**

```
# Procfile (repo root)
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Add `GROQ_API_KEY` and `TAVILY_API_KEY` as env vars in the Railway dashboard. Connect GitHub repo → auto-deploys on every push.

**Frontend → Vercel**

Set root directory to `frontend/`. No build step — pure static HTML. After deploying, add your Vercel URL to `allow_origins` in `api/main.py`.

---

## Roadmap

- [x] Phase 1 — CV + JD parsing with Tavily + Paste JD fallback
- [x] Phase 2 — Skill gap analysis with two-signal RAG classifier
- [x] Phase 3 — Resume tailoring + streaming cover letter generation
- [x] Phase 4 — RAG-grounded mock interview with session scoring
- [ ] Phase 5 — Socratic AI tutor + code coach
- [ ] Auth layer + multi-session persistence
- [ ] ATS keyword score on the tailored resume
- [ ] Export to PDF (resume + cover letter)

---

## License

MIT © [Harsh Bhanu](https://github.com/harshbhanu26)