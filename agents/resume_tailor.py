"""
agents/resume_tailor.py
Rewrites CV experience bullets to better match the JD and gap report.

Returns a list of dicts: [{ "original": "...", "tailored": "..." }, ...]
One dict per bullet across all experience entries.

Rules baked into the prompt:
- Never fabricate technologies or outcomes not in the original bullet
- Reframe language to mirror JD keywords naturally
- Keep bullets concise (one line, action verb start)
- Boost quantified results where they already exist
"""

import json
import logging
from typing import List, Dict

from models.schemas import CandidateProfile, JobDescription, SkillGapReport
from utils.llm import get_groq_client, clean_json_response

logger = logging.getLogger(__name__)
client = get_groq_client()

SYSTEM_PROMPT = """You are an expert technical resume writer.
Your job is to rewrite resume bullets to better match a job description — without fabricating anything.

Rules:
1. Never add technologies, tools, metrics, or outcomes that aren't already implied by the original bullet.
2. Mirror the JD's language and keywords naturally — don't keyword-stuff.
3. Keep each bullet to one line, starting with a strong past-tense action verb.
4. If a bullet already has a metric (e.g. "40 percent"), keep it.
5. If a bullet is already strong and relevant, minimal changes are fine.
6. Return ONLY valid JSON — no preamble, no markdown fences.

Output format:
[
  { "original": "...", "tailored": "..." },
  ...
]
"""


def tailor_resume(
    profile: CandidateProfile,
    jd: JobDescription,
    gap_report: SkillGapReport,
) -> List[Dict[str, str]]:
    """
    Rewrites all experience bullets to align with the JD.
    Returns list of { original, tailored } dicts.
    """

    # Collect all bullets from all experience entries
    all_bullets = []
    for exp in profile.experience:
        for bullet in exp.bullets:
            all_bullets.append(bullet)

    if not all_bullets:
        logger.warning("No experience bullets found in profile — returning empty list")
        return []

    # Build gap context string
    gap_skills = [g.skill for g in gap_report.gaps]
    matched_skills = [m.skill for m in gap_report.matched]

    user_prompt = f"""Job Title: {jd.title}
Company: {jd.company}

Required Skills: {", ".join(jd.required_skills)}
Nice to Have: {", ".join(jd.nice_to_have) if jd.nice_to_have else "None listed"}

Candidate's Gap Skills (missing): {", ".join(gap_skills) if gap_skills else "None"}
Candidate's Matched Skills: {", ".join(matched_skills)}

Rewrite the following {len(all_bullets)} resume bullets to better match this role.
Where possible, naturally surface keywords like: {", ".join(jd.required_skills)}.
Do NOT fabricate. Only reframe what's already there.

Bullets to rewrite:
{json.dumps(all_bullets, indent=2)}

Return a JSON array with one object per bullet: [{{"original": "...", "tailored": "..."}}]"""

    logger.info(
        "Tailoring %d bullets for job_id=%s", len(all_bullets), jd.job_id
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=4096,
    )

    raw = clean_json_response(response.choices[0].message.content)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed for tailor_resume: %s\nRaw: %s", e, raw[:500])
        # Fallback: return original bullets untouched
        return [{"original": b, "tailored": b} for b in all_bullets]

    # Validate structure
    if not isinstance(result, list):
        logger.warning("Unexpected response shape — wrapping")
        result = [{"original": b, "tailored": b} for b in all_bullets]

    return result