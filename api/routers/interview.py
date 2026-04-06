"""
api/routers/interview.py
Phase 4 — Interview Simulator.  Three stateless endpoints:

  POST /interview/start   — generate questions from gap report + JD
  POST /interview/answer  — score one answer (RAG-grounded)
  POST /interview/summary — final session report from all scored answers

State lives in the React frontend (list of questions + scored answers).
Each call is fully stateless on the server — history is sent in the request body.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import JobDescription, SkillGapReport
from agents.interviewer import (
    generate_questions,
    score_answer,
    build_session_summary,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────

class StartRequest(BaseModel):
    jd:         JobDescription
    gap_report: SkillGapReport
    n_questions: int = 10          # default: 10-question mock interview


class AnswerRequest(BaseModel):
    job_id:   str                  # used to look up ChromaDB collection
    question: str
    answer:   str
    question_index: int            # 0-based — used for per-question tracking


class ScoredAnswer(BaseModel):
    question:       str
    answer:         str
    scores:         dict           # { "relevance": 0.8, "depth": 0.7, "accuracy": 0.9 }
    feedback:       str
    question_index: int


class SummaryRequest(BaseModel):
    job_id:         str
    scored_answers: List[ScoredAnswer]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/start")
def start_interview(body: StartRequest):
    """
    Generate interview questions from the JD + skill gap report.
    Questions are role-specific and weighted toward gap skills.

    Returns:
      {
        "questions": ["Tell me about your experience with ...", ...],
        "job_id":    "abc123"
      }
    """
    try:
        logger.info("Generating %d questions for job_id=%s", body.n_questions, body.jd.job_id)
        questions = generate_questions(body.jd, body.gap_report, n=body.n_questions)
        return {
            "questions": questions,
            "job_id":    body.jd.job_id,
            "total":     len(questions),
        }
    except Exception as e:
        logger.exception("Interview start failed")
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")


@router.post("/answer")
def submit_answer(body: AnswerRequest):
    """
    Score one candidate answer against the question using RAG.
    ChromaDB must already be loaded (Phase 2 ran load_cv for this job_id).

    Returns:
      {
        "scores":   { "relevance": 0.8, "depth": 0.7, "accuracy": 0.9 },
        "feedback": "Your answer covered X well but missed Y...",
        "question_index": 2
      }
    """
    try:
        logger.info(
            "Scoring answer for job_id=%s, question_index=%d",
            body.job_id, body.question_index,
        )
        result = score_answer(
            job_id=body.job_id,
            question=body.question,
            answer=body.answer,
        )
        return {
            **result,                          # scores dict + feedback string
            "question_index": body.question_index,
        }
    except Exception as e:
        logger.exception("Answer scoring failed")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.post("/summary")
def get_summary(body: SummaryRequest):
    """
    Build the final session report after all questions are answered.

    Returns:
      {
        "overall_score":   0.76,
        "axis_averages":   { "relevance": 0.8, "depth": 0.7, "accuracy": 0.79 },
        "strengths":       ["Clear communication", ...],
        "improvements":    ["Go deeper on system design", ...],
        "question_scores": [ { question, scores, feedback }, ... ]
      }
    """
    try:
        logger.info(
            "Building summary for job_id=%s, %d answers",
            body.job_id, len(body.scored_answers),
        )
        scored = [a.model_dump() for a in body.scored_answers]
        summary = build_session_summary(job_id=body.job_id, scored_answers=scored)
        return summary
    except Exception as e:
        logger.exception("Summary generation failed")
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")