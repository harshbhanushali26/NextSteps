"""
agents/cv_parser.py

Converts a CV PDF into a structured CandidateProfile.

Pipeline:
    PDF → pymupdf4llm (Markdown) → pii.clean_text (PII stripped)
    → Groq gpt-oss-120b (JSON extraction) → CandidateProfile

PII handling:
    Email is extracted locally before the Groq call and merged
    back after. Phone and address are stripped and discarded.
    Only professional content reaches the LLM.

Functions:
    parse_cv(resume_file_path) → CandidateProfile
"""
import pymupdf4llm

from models.schemas import CandidateProfile
from utils.pii import extract_email, clean_text
from utils.llm import get_groq_client, parse_json_response
from prompts.cv_parser_prompt import CV_PARSER_SYSTEM_PROMPT

client = get_groq_client()


def parse_cv(resume_file_path: str):
    """
    Parse a CV PDF into a structured CandidateProfile.

    Extracts email locally, strips all PII, sends cleaned markdown
    to Groq for JSON extraction, validates against CandidateProfile
    schema, then merges email and raw_text back in.

    Args:
        resume_file_path (str): Absolute or relative path to the CV PDF.

    Returns:
        CandidateProfile: Fully validated structured profile.

    Raises:
        RuntimeError: If pymupdf4llm fails to read the PDF.
        ValidationError: If Groq response doesn't match the schema.
        json.JSONDecodeError: If Groq returns malformed JSON.
    """
    
    # Data Extraction
    try:
        md_text = pymupdf4llm.to_markdown(resume_file_path)
    except Exception as e:
        raise RuntimeError(f"PDF to Markdown failed: {e}")

    email = extract_email(md_text)

    clean_md = clean_text(md_text)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": CV_PARSER_SYSTEM_PROMPT},
            {"role": "user", "content": clean_md}        # cleaned markdown
        ],
        temperature=0.0
    )

    # Parse into Pydantic model
    data = parse_json_response(response.choices[0].message.content)
    data["email"] = email
    data["raw_text"] = clean_md
    profile = CandidateProfile.model_validate(data)

    return profile





