"""
api/routers/apply.py
POST /apply        — Phase 3: gap report + company ctx → tailored bullets + cover letter.
POST /apply/stream — Streaming variant for cover letter only (SSE).

Accepts JSON body:
  {
    "profile":     { ...CandidateProfile... },
    "jd":          { ...JobDescription... },
    "gap_report":  { ...SkillGapReport... },
    "company_ctx": "string"
  }

Returns (non-streaming):
  {
    "tailored_bullets": [ { "original": "...", "tailored": "..." }, ... ],
    "cover_letter":     "full cover letter text"
  }
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.schemas import CandidateProfile, JobDescription, SkillGapReport
from agents.resume_tailor import tailor_resume
from agents.cover_letter import generate_cover_letter

logger = logging.getLogger(__name__)
router = APIRouter()


class ApplyRequest(BaseModel):
    profile:     CandidateProfile
    jd:          JobDescription
    gap_report:  SkillGapReport
    company_ctx: str = ""


@router.post("")
def run_apply(body: ApplyRequest):
    """
    Phase 3 — full response (tailored bullets + complete cover letter).
    Use this when you don't need streaming.
    """
    try:
        logger.info("Tailoring resume for job_id=%s", body.jd.job_id)
        tailored_bullets = tailor_resume(body.profile, body.jd, body.gap_report)

        logger.info("Generating cover letter for job_id=%s", body.jd.job_id)
        cover_letter = generate_cover_letter(
            profile=body.profile,
            jd=body.jd,
            gap_report=body.gap_report,
            company_ctx=body.company_ctx,
        )

        return {
            "tailored_bullets": tailored_bullets,   # list of {original, tailored}
            "cover_letter":     cover_letter,
        }

    except Exception as e:
        logger.exception("Apply phase failed")
        raise HTTPException(status_code=500, detail=f"Apply failed: {str(e)}")


@router.post("/stream")
def stream_cover_letter(body: ApplyRequest):
    """
    Phase 3 — streaming cover letter only (Server-Sent Events).
    The React UI calls this endpoint and reads chunks as they arrive.
    Yields text tokens one by one so the user sees the letter being written.

    Usage in React:
        const es = new EventSource('/apply/stream', { method: 'POST', body: ... })
        es.onmessage = e => appendToLetter(e.data)

    Note: Because EventSource doesn't support POST natively, the React side
    should use fetch() with a ReadableStream reader instead:

        const res = await fetch('/apply/stream', { method: 'POST', body: JSON.stringify(body) })
        const reader = res.body.getReader()
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          appendToLetter(new TextDecoder().decode(value))
        }
    """
    def token_generator():
        """
        Calls generate_cover_letter with stream=True.
        Your cover_letter.py should accept a stream kwarg and yield tokens.
        If it doesn't support streaming yet, yields the full text as one chunk.
        """
        try:
            result = generate_cover_letter(
                profile=body.profile,
                jd=body.jd,
                gap_report=body.gap_report,
                company_ctx=body.company_ctx,
                stream=True,
            )
            # If result is a generator (streaming), yield each chunk.
            # If result is a plain string (no streaming support yet), yield whole string.
            if hasattr(result, "__iter__") and not isinstance(result, str):
                for chunk in result:
                    yield chunk
            else:
                yield result
        except Exception as e:
            logger.exception("Cover letter streaming failed")
            yield f"\n\n[Error: {str(e)}]"

    return StreamingResponse(token_generator(), media_type="text/plain")