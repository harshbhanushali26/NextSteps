"""
agents/cover_letter.py
Generates a company-aware, human-sounding cover letter.

- Uses company_ctx (Tavily-enriched) when available
- Mirrors JD language without sounding robotic
- Highlights matched skills + addresses gaps honestly
- Supports stream=True for the /apply/stream endpoint
"""

import logging
from typing import Union, Generator

from models.schemas import CandidateProfile, JobDescription, SkillGapReport
from utils.llm import get_groq_client

logger = logging.getLogger(__name__)
client = get_groq_client()

SYSTEM_PROMPT = """You are a professional cover letter writer who specialises in tech roles.

Write cover letters that:
- Sound genuinely human — not corporate or robotic
- Open with a specific hook (not "I am writing to apply for...")
- Reference the company's actual mission/culture when context is provided
- Highlight 2-3 concrete achievements from the candidate's experience
- Address skill gaps honestly and briefly (frame as "actively developing")
- Close with a confident, forward-looking paragraph
- Stay under 350 words
- Use plain paragraphs — no bullet points, no headers

Write in first person. Do not include the date, address blocks, or "Sincerely" — just the letter body.
"""


def _build_prompt(
    profile: CandidateProfile,
    jd: JobDescription,
    gap_report: SkillGapReport,
    company_ctx: str,
) -> str:
    matched_skills = [m.skill for m in gap_report.matched]
    gap_skills     = [g.skill for g in gap_report.gaps]

    # Pick the 2 strongest experience bullets to highlight
    highlight_bullets = []
    for exp in profile.experience[:2]:
        if exp.bullets:
            highlight_bullets.append(f"{exp.role} at {exp.company}: {exp.bullets[0]}")

    company_context_section = (
        f"\nCompany context (use this to personalise):\n{company_ctx}"
        if company_ctx
        else "\nNo additional company context available — keep it general but genuine."
    )

    return f"""Candidate: {profile.name}
Role applying for: {jd.title} at {jd.company}
Location: {jd.location}

Required skills for this role: {", ".join(jd.required_skills)}
Candidate's matched skills: {", ".join(matched_skills) if matched_skills else "None"}
Candidate's skill gaps: {", ".join(gap_skills) if gap_skills else "None"}

Key achievements to highlight:
{chr(10).join(f"- {b}" for b in highlight_bullets)}
{company_context_section}

Write a cover letter body (no headers, no address block, just the paragraphs).
Keep it under 350 words. Sound like a real person, not a template."""


def generate_cover_letter(
    profile: CandidateProfile,
    jd: JobDescription,
    gap_report: SkillGapReport,
    company_ctx: str = "",
    stream: bool = False,
) -> Union[str, Generator[str, None, None]]:
    """
    Generate a cover letter.

    Args:
        stream: If True, returns a generator that yields text chunks.
                The /apply/stream endpoint uses this for live typing effect.
                If False (default), returns the full string.
    """
    prompt = _build_prompt(profile, jd, gap_report, company_ctx)

    logger.info(
        "Generating cover letter for %s → %s @ %s (stream=%s)",
        profile.name, jd.title, jd.company, stream,
    )

    if stream:
        return _stream_cover_letter(prompt)
    else:
        return _full_cover_letter(prompt)


def _full_cover_letter(prompt: str) -> str:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def _stream_cover_letter(prompt: str) -> Generator[str, None, None]:
    """
    Yields text chunks as they arrive from Groq streaming API.
    The FastAPI StreamingResponse in apply.py iterates over this.
    """
    stream = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content