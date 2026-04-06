"""
utils/pii.py

PII extraction and removal for CV text before LLM processing.

Only professional content (skills, experience, education) reaches
the Groq API. Email is extracted locally and merged back into the
CandidateProfile after the LLM call. Phone and address are 
stripped and permanently discarded.

Functions:
    extract_email(md_cv) → str | None
    clean_text(md_cv)    → str
"""

import re


def extract_email(md_cv: str) -> str | None:
    """
    Extract the first email address found in the CV text.

    Args:
        md_cv (str): The CV content in Markdown format.

    Returns:
        str | None: The first email address found, or None if no email is detected.
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, md_cv)

    return emails[0] if emails else None


def clean_text(md_cv) -> str:
    """
    Remove sensitive personal information (PII) from CV Markdown text.

    This function performs multiple cleaning steps:
    1. Removes email addresses
    2. Removes phone numbers (international + Indian 10-digit formats)
    3. Removes address-related lines containing street keywords or PIN/zip codes

    The goal is to create a privacy-safe version of the CV that can be safely
    sent to LLMs without exposing personal contact or location details.

    Args:
        md_cv (str): Raw CV content in Markdown format.

    Returns:
        str: Cleaned CV text with PII redacted/removed.
    """

    text = md_cv
    street_keywords = ["street", "road", "avenue", "lane", "nagar", "sector", "plot", 
        "flat", "floor", "block", "society", "colony", "phase", 
        "near", "opp", "opposite", "behind", "beside"]

    indian_pin = r'\b[1-9][0-9]{5}\b'       # 6-digit Indian PIN code
    us_zip = r'\b[0-9]{5}\b'                # 5-digit US ZIP codes

    # Step 1 — remove email
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)

    # Step 2 — remove phone (two passes)
    # Pattern A — international:
    text = re.sub(r'\+?[0-9]{1,4}[\s\-\.]?(\([0-9]{1,4}\))?[\s\-\.]?[0-9]{4,6}[\s\-\.]?[0-9]{3,6}', '', text)

    # Pattern B — Indian 10-digit:
    text = re.sub(r'\b[6-9][0-9]{9}\b', '', text)

    # Step 3 — remove address lines
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            cleaned_lines.append(line)
            continue

        # check pin/zip
        if re.search(indian_pin, line) or re.search(us_zip, line):
            continue
        # check street keywords — only on short lines
        if len(line) < 80 and any(kw in line.lower() for kw in street_keywords):
            continue

        cleaned_lines.append(line)

    cleaned_text = '\n'.join(cleaned_lines)
    return cleaned_text.strip()
