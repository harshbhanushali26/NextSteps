"""
api/routers/parse.py
POST /parse — Phase 1: CV PDF + job URL → profile + JD + company context.
 
Accepts:
  - cv:          UploadFile (PDF)
  - job_url:     str        (form field)
  - raw_jd_text: str        (optional — raw JD text, skips URL scraping)
 
Returns:
  {
    "profile":     CandidateProfile dict,
    "jd":          JobDescription dict,
    "company_ctx": str
  }
"""

import os
import tempfile
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from agents.cv_parser import parse_cv
from agents.jd_scraper import scrape_jd, _extract_with_groq, generate_job_id
from agents.company_research import company_research
from models.schemas import JobDescription

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_CV_SIZE = 10 * 1024 * 1024   # 10 MB


@router.post("")
async def parse_documents(
    cv: UploadFile = File(..., description="Candidate CV as a PDF file"),
    job_url: str   = Form(..., description="Job posting URL — any job board"),
    company_name: str = Form("", description="Optional company name — used as fallback if Groq can't extract it from JD"),
    raw_jd_text: str = Form("", description="Optional raw JD text — skips URL scraping when provided (>50 chars)"),
):
    """
    Phase 1 entry point.
    1. Validate file type, file size, and URL format.
    2. Save the uploaded PDF to a temp file (pymupdf4llm needs a path).
    3. Run cv_parser → CandidateProfile.
    4. Run jd_scraper → JobDescription (Tavily primary, bs4 fallback).
    5. Run company_research → plain-prose context string.
    6. Return all three as JSON. Temp file is always cleaned up.
    """

    # ── Validate file type ────────────────────────────────────────────────────
    if not cv.filename or not cv.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

    # ── Validate URL (must have scheme + domain) — skip if raw JD text provided
    has_raw_jd = len(raw_jd_text.strip()) >= 50
    if not has_raw_jd:
        parsed_url = urlparse(job_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise HTTPException(
                status_code=400,
                detail="job_url must be a valid HTTP/HTTPS URL with a domain.",
            )

    # ── Read file content + validate size ─────────────────────────────────────
    content = await cv.read()
    if len(content) > MAX_CV_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"CV file too large ({len(content) // (1024*1024)}MB). Maximum size is 10MB.",
        )

    tmp_path = None
    try:
        # ── Write PDF to temp file ────────────────────────────────────────────
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(content)
            tmp_path = f.name

        # ── Agent calls (your functions, unchanged) ───────────────────────────
        logger.info("Parsing CV from %s", tmp_path)
        profile = parse_cv(tmp_path)

        if has_raw_jd:
            logger.info("Using pasted JD text (%d chars)", len(raw_jd_text))
            data = _extract_with_groq(raw_jd_text.strip(), job_url)
            data["url"] = job_url
            data["job_id"] = generate_job_id(job_url + raw_jd_text[:100])
            data["raw_text"] = raw_jd_text.strip()
            jd = JobDescription.model_validate(data)
        else:
            logger.info("Scraping JD from %s", job_url)
            jd = scrape_jd(job_url)

        # ── FIX: Use user-provided company name as fallback ───────────────────
        effective_company = (jd.company or "").strip() or company_name.strip()
        if effective_company and not jd.company:
            jd.company = effective_company
            logger.info("Using user-provided company name: %s", effective_company)

        logger.info("Researching company: %s", effective_company)
        company_ctx = company_research(effective_company)

        return {
            "profile":     profile.model_dump(),
            "jd":          jd.model_dump(),
            "company_ctx": company_ctx,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Parse phase failed")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
