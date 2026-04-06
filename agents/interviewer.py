"""
agents/interviewer.py
Phase 4 — Mock Interview Simulator.

Three functions consumed by api/routers/interview.py:
  - generate_questions(jd, gap_report, n) → List[str]
  - score_answer(job_id, question, answer) → dict
  - build_session_summary(job_id, scored_answers) → dict

Design:
  - Questions weighted toward gap skills (they're what the interviewer will probe)
  - Answer scoring is RAG-grounded: retrieves relevant CV chunks from ChromaDB
    so the scorer can compare the answer against what the candidate actually did
  - Three scoring axes: relevance, depth, accuracy (each 0.0–1.0)
  - Summary builds overall score + strengths/improvements list
"""

import json
import logging
from typing import List, Dict, Any

from models.schemas import JobDescription, SkillGapReport
from rag.store import get_collection
from rag.embedder import embedder      # for query embedding
from utils.llm import get_groq_client, clean_json_response

logger = logging.getLogger(__name__)
client = get_groq_client()


# ── Prompts ────────────────────────────────────────────────────────────────────

QUESTION_SYSTEM = """You are a senior technical interviewer preparing questions for a job interview.
Generate interview questions that:
- Are specific to the role and required skills
- Mix behavioural (STAR format) and technical questions
- Weight more questions toward skill gaps — these are what real interviewers probe
- Vary difficulty: some straightforward, some deep
- Sound like a real human interviewer would ask them
Return ONLY a JSON array of question strings. No numbering, no preamble, no markdown."""


SCORING_SYSTEM = """You are an expert technical interview evaluator.
Score the candidate's answer on three axes, each from 0.0 to 1.0:
- relevance:  Does the answer actually address the question asked?
- depth:      Does it show genuine understanding, or is it surface-level?
- accuracy:   Are the technical claims correct? (use the CV context to verify)

Calibration rules — apply these strictly:
- Any coherent sentence scores at least 0.15 on every axis (floor)
- Grammar errors reduce clarity by at most 0.2 — poor grammar ≠ wrong answer
- Partial answers score 0.3–0.5, not 0.0–0.1
- Only score 0.0–0.1 if the answer is completely off-topic or empty
- A vague but on-topic answer is 0.3–0.5 relevance, not 0.0

Also write 2-3 sentences of specific, actionable feedback.

Return ONLY valid JSON in this exact shape:
{
  "scores": { "relevance": 0.0, "depth": 0.0, "accuracy": 0.0 },
  "feedback": "..."
}"""

SUMMARY_SYSTEM = """You are summarising a completed mock interview session.
Given a list of scored answers, identify:
- 2-3 genuine strengths shown across the session
- 2-3 specific areas for improvement

Return ONLY valid JSON:
{
  "strengths": ["...", "..."],
  "improvements": ["...", "..."]
}"""


# ── Public functions ───────────────────────────────────────────────────────────

def generate_questions(
    jd: JobDescription,
    gap_report: SkillGapReport,
    n: int = 10,
) -> List[str]:
    """
    Generate n interview questions weighted toward gap skills.
    Roughly: 60% gap-focused, 40% general role / matched skills.
    """
    gap_skills     = [g.skill for g in gap_report.gaps]
    matched_skills = [m.skill for m in gap_report.matched]

    n_gap     = min(len(gap_skills) * 2, int(n * 0.6))
    n_general = n - n_gap

    prompt = f"""Role: {jd.title} at {jd.company}
Required skills: {", ".join(jd.required_skills)}
Candidate's matched skills: {", ".join(matched_skills) if matched_skills else "None"}
Candidate's SKILL GAPS (probe these harder): {", ".join(gap_skills) if gap_skills else "None"}

Generate exactly {n} interview questions.
- {n_gap} questions should specifically probe the gap skills: {", ".join(gap_skills)}
- {n_general} questions should cover the role broadly (matched skills, experience, behaviour)

Return a JSON array of {n} question strings."""

    logger.info("Generating %d questions for job_id=%s", n, jd.job_id)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": QUESTION_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.6,
        max_tokens=2048,
    )

    raw = clean_json_response(response.choices[0].message.content)

    try:
        questions = json.loads(raw)
        if not isinstance(questions, list):
            raise ValueError("Expected a list")
        return questions[:n]
    except Exception as e:
        logger.error("Question parse failed: %s\nRaw: %s", e, raw[:300])
        # Fallback: return generic questions
        return _fallback_questions(jd, gap_skills, n)


def score_answer(
    job_id: str,
    question: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Score one candidate answer using RAG-grounded evaluation.
    Retrieves relevant CV chunks from ChromaDB to ground the accuracy score.
    """
    # ── RAG: pull relevant CV context ─────────────────────────────────────────
    cv_context = _retrieve_cv_context(job_id, question, answer)

    prompt = f"""Question asked: {question}

Candidate's answer: {answer}

Relevant CV context (what the candidate actually did — use this to verify accuracy):
{cv_context}

Score this answer on relevance, depth, and accuracy (0.0–1.0 each).
Write 2-3 sentences of specific feedback."""

    logger.info("Scoring answer for job_id=%s | Q: %s...", job_id, question[:60])

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SCORING_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=512,
    )

    raw = clean_json_response(response.choices[0].message.content)

    try:
        result = json.loads(raw)
        # Validate shape
        if "scores" not in result or "feedback" not in result:
            raise ValueError("Missing keys")
        return result
    except Exception as e:
        logger.error("Score parse failed: %s\nRaw: %s", e, raw[:300])
        return {
            "scores":   {"relevance": 0.5, "depth": 0.5, "accuracy": 0.5},
            "feedback": "Could not parse scoring response. Please try again.",
        }


def build_session_summary(
    job_id: str,
    scored_answers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the final session report after all questions are answered.

    Returns:
      {
        "overall_score":   0.76,
        "axis_averages":   { "relevance": 0.8, "depth": 0.7, "accuracy": 0.79 },
        "strengths":       [...],
        "improvements":    [...],
        "question_scores": [ { question, answer, scores, feedback }, ... ]
      }
    """
    if not scored_answers:
        return {
            "overall_score": 0,
            "axis_averages": {},
            "strengths": [],
            "improvements": [],
            "question_scores": [],
        }

    # ── Compute averages ───────────────────────────────────────────────────────
    axes = ["relevance", "depth", "accuracy"]
    axis_totals = {a: 0.0 for a in axes}
    valid = 0

    for sa in scored_answers:
        scores = sa.get("scores", {})
        if scores:
            for a in axes:
                axis_totals[a] += scores.get(a, 0.0)
            valid += 1

    if valid:
        axis_averages = {a: round(axis_totals[a] / valid, 3) for a in axes}
        overall_score = round(sum(axis_averages.values()) / len(axes), 3)
    else:
        axis_averages = {a: 0.0 for a in axes}
        overall_score = 0.0

    # ── LLM: strengths + improvements ─────────────────────────────────────────
    summary_input = json.dumps([
        {
            "question": sa.get("question", ""),
            "answer":   sa.get("answer", ""),
            "scores":   sa.get("scores", {}),
            "feedback": sa.get("feedback", ""),
        }
        for sa in scored_answers
    ], indent=2)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user",   "content": f"Session data:\n{summary_input}"},
        ],
        temperature=0.4,
        max_tokens=512,
    )

    raw = clean_json_response(response.choices[0].message.content)

    try:
        qualitative = json.loads(raw)
        strengths    = qualitative.get("strengths", [])
        improvements = qualitative.get("improvements", [])
    except Exception as e:
        logger.error("Summary parse failed: %s", e)
        strengths    = ["Completed the full interview session"]
        improvements = ["Review feedback for each question above"]

    return {
        "overall_score":   overall_score,
        "axis_averages":   axis_averages,
        "strengths":       strengths,
        "improvements":    improvements,
        "question_scores": scored_answers,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _retrieve_cv_context(job_id: str, question: str, answer: str) -> str:
    """
    Query ChromaDB cv_chunks_{job_id} collection for relevant CV passages.
    Returns a plain-text string of the top-3 relevant chunks.
    Falls back to empty string if collection doesn't exist.
    """
    try:
        collection = get_collection(f"cv_chunks_{job_id}")
        query_text = f"{question} {answer}"

        # Embed the query
        query_embedding = embedder.embed_single(query_text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents"],
        )
        chunks = results.get("documents", [[]])[0]
        return "\n---\n".join(chunks) if chunks else "No CV context available."

    except Exception as e:
        logger.warning("RAG retrieval failed for job_id=%s: %s", job_id, e)
        return "No CV context available."



def _fallback_questions(jd: JobDescription, gap_skills: List[str], n: int) -> List[str]:
    """Emergency fallback questions if LLM/parse fails."""
    questions = [
        f"Tell me about your experience with {jd.required_skills[0] if jd.required_skills else 'this role'}.",
        f"Why are you interested in the {jd.title} position at {jd.company}?",
        "Walk me through a challenging technical problem you solved recently.",
        "How do you approach learning a new technology quickly?",
        "Describe a time you had to debug a production issue under pressure.",
    ]
    for skill in gap_skills:
        questions.append(f"You listed {skill} as an area you're developing. What have you done so far?")
    return questions[:n]