"""
models/schemas.py

Pydantic v2 data models for NextSteps career agent.

All models use ConfigDict with extra='forbid' — any field returned
by the LLM that is not defined here will raise a ValidationError immediately,
preventing silent data corruption.

Classes:
    WorkExperience   — single job entry from a CV
    CandidateProfile — complete parsed CV
    JobDescription   — parsed job posting
    SkillMatch       — single skill comparison result
    SkillGapReport   — full gap analysis between CV and JD
    JobSession       — carries all state across all 5 phases
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Annotated, Dict, Any, Literal
from datetime import date


class WorkExperience(BaseModel):
    """Represents a single work experience entry in a candidate's CV."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    company: Annotated[str, Field(..., description="Name of the company")]
    role: Annotated[str, Field(..., description="Job title / role held")]
    duration: Annotated[str, Field(..., description="Duration of employment (e.g., 'Jan 2022 - Present', '2.5 years')")]
    start_date: Annotated[Optional[date], Field(None, description="Start date if available")]
    end_date: Annotated[Optional[date], Field(None, description="End date if available")]
    bullets: Annotated[
        List[str],
        Field(
            default_factory=list,
            description="List of key responsibilities, achievements, and projects (bullet points)"
        )
    ]


class CandidateProfile(BaseModel):
    """Complete structured representation of a candidate's resume/CV."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    name: Annotated[str, Field(..., description="Full name of the candidate")]
    email: Annotated[Optional[str], Field(..., description="Professional email address")]
    # location: Annotated[Optional[str], Field(None, description="Current location / city")]

    skills: Annotated[
        List[str],
        Field(default_factory=list, description="List of technical and soft skills")
    ]

    experience: Annotated[
        List[WorkExperience],
        Field(default_factory=list, description="Professional work experience")
    ]

    education: Annotated[
        List[str],
        Field(default_factory=list, description="Educational qualifications (degree, institution, year)")
    ]

    raw_text: Annotated[
        str,
        Field(..., description="Original full text of the CV for RAG/retrieval purposes")
    ]


class JobDescription(BaseModel):
    """Structured representation of a job posting."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    job_id: Annotated[str, Field(..., description="Unique identifier for the job")]
    title: Annotated[str, Field(..., description="Job title")]
    company: Annotated[str, Field(..., description="Hiring company name")]
    location: Annotated[Optional[str], Field(None, description="Job location")]

    required_skills: Annotated[
        List[str],
        Field(default_factory=list, description="Must-have skills and qualifications")
    ]

    nice_to_have: Annotated[
        List[str],
        Field(default_factory=list, description="Preferred but not mandatory skills")
    ]

    responsibilities: Annotated[
        List[str],
        Field(default_factory=list, description="Key responsibilities of the role")
    ]

    url: Annotated[Optional[str], Field(None, description="Original job posting URL")]

    skills_extraction_warning: bool = False

    raw_text: Annotated[
        str,
        Field(..., description="Full original job description text for RAG")
    ]


class SkillMatch(BaseModel):
    """Detailed matching result for a single skill."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    skill: Annotated[str, Field(..., description="Skill name from the job description")]
    matched_to: Annotated[Optional[str], Field(None, description="Corresponding skill from candidate's profile (if different)")]
    score: Annotated[
        float,
        Field(..., ge=0.0, le=1.0, description="Match confidence score between 0.0 and 1.0")
    ]
    is_gap: Annotated[
        bool,
        Field(..., description="True if this skill is considered a gap (score < 0.7)")
    ]
    category: Annotated[
        Literal["required", "nice_to_have"],
        Field(..., description="Whether this skill is a hard requirement or nice to have")
    ]


class SkillGapReport(BaseModel):
    """Final skill gap analysis report between candidate and job."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    job_id: Annotated[str, Field(..., description="ID of the job being matched against")]
    candidate_name: Annotated[Optional[str], Field(None, description="Name of the candidate")]

    overall_match_pct: Annotated[
        float,
        Field(..., ge=0.0, le=100.0, description="Overall match percentage based on required skills only (0-100)")
    ]

    matched: Annotated[
        List[SkillMatch],
        Field(default_factory=list, description="Skills that were successfully matched")
    ]

    gaps: Annotated[
        List[SkillMatch],
        Field(default_factory=list, description="Skills missing or weak in candidate's profile (is_gap=True)")
    ]

    recommendations: Annotated[
        Optional[List[str]],
        Field(None, description="Actionable recommendations to close the gaps")
    ]


class JobSession(BaseModel):
    """
    Carries all state across all 5 phases.
    Replaces DependencyState from finance-agent.
    Stored in FastAPI request body / React state.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    job_id: Annotated[str, Field(default="", description="Unique job identifier")]

    # Phase 1 outputs
    profile:     Optional[CandidateProfile] = None
    jd:          Optional[JobDescription]   = None
    company_ctx: Annotated[str, Field(default="", description="Tavily company context, empty string if unavailable")]

    # Phase 2 outputs
    gap_report:  Optional[SkillGapReport]   = None

    # Phase 3 outputs
    tailored_bullets: Annotated[
        Optional[Dict[str, Any]],
        Field(None, description="Rewritten resume bullets keyed by role/company")
    ] = None
    cover_letter: Optional[str] = None

    # Phase 4 outputs
    interview_questions: Annotated[
        Optional[List[str]],
        Field(None, description="Generated interview questions")
    ] = None
    interview_scores: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(None, description="Per-answer scores from interview phase")
    ] = None

    # Phase 5 outputs
    study_plan: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(None, description="Per-gap-skill study plan")
    ] = None


