"""
api/routers/match.py
POST /match — Phase 2: CandidateProfile + JobDescription → SkillGapReport.

Also triggers CV chunking into ChromaDB (rag/cv_loader.py).

Accepts JSON body:
  {
    "profile":  { ...CandidateProfile fields... },
    "jd":       { ...JobDescription fields... }
  }

Returns:
  { ...SkillGapReport fields... }
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import CandidateProfile, JobDescription, SkillGapReport
from agents.skill_matcher import match_skills
from rag.cv_loader import load_cv

logger = logging.getLogger(__name__)
router = APIRouter()


class MatchRequest(BaseModel):
    profile: CandidateProfile
    jd: JobDescription


@router.post("", response_model=SkillGapReport)
def run_match(body: MatchRequest):
    """
    Phase 2 entry point.
    1. Load CV text into ChromaDB (cv_loader.load_cv).
       This chunks the raw_text and builds skill embeddings for the session.
    2. Run skill_matcher → SkillGapReport.
    3. Return the report as JSON.
    """
    try:
        # Load CV into ChromaDB — creates cv_chunks_{job_id} + cv_skills_{job_id}
        logger.info("Loading CV into ChromaDB for job_id=%s", body.jd.job_id)
        load_cv(body.profile, body.jd.job_id)

        logger.info("Running skill matcher for job_id=%s", body.jd.job_id)
        report: SkillGapReport = match_skills(body.profile, body.jd)

        return report

    except Exception as e:
        logger.exception("Match phase failed")
        raise HTTPException(status_code=500, detail=f"Match failed: {str(e)}")