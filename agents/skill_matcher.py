"""
skill_matcher.py
================
Matches candidate skills against job requirements using ChromaDB cosine
similarity and produces a SkillGapReport with actionable recommendations.

Pipeline:
    1. Batch embed required_skills and nice_to_have from JobDescription
    2. Query cv_skills_{job_id} ChromaDB collection per skill
    3. Threshold 0.7 — above = matched, below = gap
    4. Calculate overall match % from required skills only
    5. Light Groq call to generate actionable recommendations from gaps

Assumes cv_skills_{job_id} is already populated by rag/cv_loader.py.

Public API:
    match_skills(profile, jd) -> SkillGapReport
"""

import logging

from rag.embedder import embedder
from rag.store import query_skills
from rag.store import query_skills, get_collection
from models.schemas import SkillMatch, SkillGapReport, CandidateProfile, JobDescription
from prompts.skill_matcher_prompt import SKILL_MATCHER_SYSTEM_PROMPT
from utils.llm import get_groq_client, parse_json_response

logger = logging.getLogger(__name__)

groq_client = get_groq_client()


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _embed_and_match(skills: list[str], category: str, job_id: str) -> tuple[list[SkillMatch], list[SkillMatch]]:
    """
    Batch embed JD skills and match each against candidate skills in ChromaDB.

    Embeds all skills in a single generate_embeddings() call for efficiency,
    then queries cv_skills_{job_id} once per skill to find the best candidate
    match. Builds a SkillMatch object per skill and splits into matched/gaps
    based on the 0.7 cosine similarity threshold.

    Args:
        skills:   List of skill strings from JobDescription (required or nice_to_have).
        category: Either "required" or "nice_to_have" — tagged on each SkillMatch.
        job_id:   Job session identifier for ChromaDB collection lookup.

    Returns:
        Tuple of (matched, gaps) — both List[SkillMatch].
    """

    if not skills:
        return [], []

    embeddings, shape, count = embedder.generate_embeddings(skills)

    matched = []
    gaps    = []

    for skill, embed in zip(skills, embeddings):
        result = query_skills(job_id, embed)[0]
        # is_gap = result["score"] < 0.7
        best_score = min(float(result["score"]), 1.0)

            # For long descriptive JD phrases (>5 words), also query cv_chunks
        # These match better against full CV sentences than against skill keywords
        if len(skill.split()) > 5:
            try:
                chunk_collection = get_collection(f"cv_chunks_{job_id}")
                chunk_results = chunk_collection.query(
                    query_embeddings=[embed],
                    n_results=2,
                    include=["documents", "distances"],
                )
                distances = chunk_results.get("distances", [[]])[0]
                if distances:
                    # ChromaDB returns L2 distance — convert to similarity
                    chunk_score = max(0.0, 1.0 - (distances[0] / 2.0))
                    best_score = min(max(best_score, chunk_score), 1.0)
            except Exception as e:
                logger.debug("cv_chunks query failed for '%s': %s", skill[:40], e)

        is_gap = best_score < 0.35
        skill_match = SkillMatch(
            skill=skill,
            matched_to=result["document"] if not is_gap else None,
            score=best_score,
            is_gap=is_gap,
            category=category,
        )

        # skill_match = SkillMatch(
        #     skill=skill,
        #     matched_to=result["document"] if not is_gap else None,
        #     score=min(float(result["score"]), 1.0),     # ← clamp to max 1.0
        #     is_gap=is_gap,
        #     category=category,
        # )

        if is_gap:
            gaps.append(skill_match)
        else:
            matched.append(skill_match)

    return matched, gaps


def _calculate_match_pct(matched: list[SkillMatch], total_required: int) -> float:
    """
    Calculate overall match percentage based on required skills only.

    Nice-to-have skills are excluded — missing them does not penalize
    the candidate's score.

    Args:
        matched:        List of matched required SkillMatch objects.
        total_required: Total number of required skills in the JobDescription.

    Returns:
        Match percentage as float between 0.0 and 100.0.
        Returns 0.0 if total_required is zero to avoid division by zero.
    """
    return 0.0 if total_required == 0 else (len(matched) / total_required) * 100


def _get_recommendations(candidate_skills: list[str], gaps: list[SkillMatch]) -> list[str] | None:
    """
    Generate actionable learning recommendations for gap skills via Groq.

    Sends candidate's existing skills alongside gap skill names so Groq
    can suggest bridges — e.g. "You know Python, learn Airflow via X".
    Returns a parsed JSON array of recommendation strings.

    Args:
        candidate_skills: List of skill strings from CandidateProfile.
        gaps:             List of SkillMatch objects where is_gap=True.

    Returns:
        List of recommendation strings, or None if Groq call fails.
    """
    if not gaps:
        return None

    gap_names = [g.skill for g in gaps]

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": SKILL_MATCHER_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Candidate Skills: {candidate_skills}\n"
                    f"Gaps: {gap_names}\n\n"
                    "For each gap, suggest how the candidate can bridge it using their existing skills "
                    "as a foundation. Frame recommendations as: 'You already know X — use it to learn Y via Z.' "
                    "Be specific and actionable. Return a JSON array of recommendation strings."
                )},
            ],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()
        return parse_json_response(raw)

    except Exception as e:
        logger.warning(f"Groq recommendations failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def match_skills(profile: CandidateProfile, jd: JobDescription) -> SkillGapReport:
    """
    Orchestrate the full skill matching pipeline for a candidate and job.

    Embeds and matches required and nice_to_have skills separately so
    category is tracked per skill. Calculates match percentage from
    required skills only. Generates Groq recommendations from required
    gaps using candidate's existing skills as context.

    Args:
        profile: Validated CandidateProfile from cv_parser.py.
        jd:      Validated JobDescription from jd_scraper.py.

    Returns:
        SkillGapReport with matched skills, gaps, match percentage,
        and actionable recommendations.
    """

    # Guard: if JD has no required skills, return early with a clear message
    if not jd.required_skills and not jd.nice_to_have:
        logger.warning("JD has no required_skills or nice_to_have — returning empty report")
        return SkillGapReport(
            job_id=jd.job_id,
            candidate_name=profile.name,
            overall_match_pct=0.0,
            matched=[],
            gaps=[],
            recommendations=[
                "No skills were detected in the job description. "
                "This usually means Tavily could not fetch enough text from the URL, "
                "or the JD page uses heavy JavaScript rendering. Try a different job URL "
                "(direct company career page or Lever/Greenhouse/Workable link)."
            ],
        )

    required_matched, required_gaps = _embed_and_match(jd.required_skills, "required", jd.job_id)
    nice_matched, nice_gaps         = _embed_and_match(jd.nice_to_have, "nice_to_have", jd.job_id)

    match_pct      = _calculate_match_pct(required_matched, len(jd.required_skills))
    recommendations = _get_recommendations(profile.skills, required_gaps)

    return SkillGapReport(
        job_id=jd.job_id,
        candidate_name=profile.name,
        overall_match_pct=match_pct,
        matched=required_matched + nice_matched,
        gaps=required_gaps + nice_gaps,
        recommendations=recommendations,
    )